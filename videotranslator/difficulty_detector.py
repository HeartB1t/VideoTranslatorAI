"""Pre-flight difficulty estimator for the dubbing pipeline.

The pipeline applies ``ffmpeg atempo`` (or Rubber Band) to compress TTS
audio that overshoots the Whisper segment slot. When the source video
already pushes near the target language reading-speed limit (e.g. fast
comedy, dense newsreader), even an ideal translation cannot fit and the
final dub sounds audibly accelerated.

This module estimates the *expected* P90 of ``pre_stretch_ratio`` from
segment text length and slot duration BEFORE running TTS+stretch. The
formula:

    expected_ratio_i = (src_chars_i * expansion_factor)
                       / (slot_s_i * cps_target_lang)

``cps_target_lang`` is the natural reading speed in the target language
(see ``videotranslator.ollama_length_control._CHARS_PER_SECOND_BY_LANG``).
``expansion_factor`` is the language pair expansion ratio (e.g. EN->IT
~= 1.25; IT->EN ~= 0.80).

The output is purely advisory: the pipeline runs unchanged regardless,
but a one-line warning is printed so the user knows what to expect
before sinking compute into XTTS.

Pure module: no I/O, no Tk, no subprocess. Easy to unit test.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from videotranslator.ollama_length_control import chars_per_second_for


def estimate_segment_ratio(
    src_chars: int,
    slot_s: float,
    target_lang_code: str,
    expansion_factor: float = 1.0,
) -> float:
    """Estimated ``pre_stretch_ratio`` for a single segment.

    Returns ``0.0`` for degenerate inputs (zero/negative slot, zero/negative
    cps lookup, empty text). Callers can treat ``0.0`` as "no signal"
    rather than as an outlier.
    """
    if slot_s <= 0 or src_chars <= 0:
        return 0.0
    cps = chars_per_second_for(target_lang_code)
    if cps <= 0:
        return 0.0
    target_chars_at_normal_speed = slot_s * cps
    if target_chars_at_normal_speed <= 0:
        return 0.0
    return (src_chars * expansion_factor) / target_chars_at_normal_speed


def estimate_p90_ratio(
    segments: Iterable[Mapping],
    target_lang_code: str,
    expansion_factor: float = 1.0,
) -> float:
    """Return the P90 of expected ratios across ``segments``.

    Each segment must expose ``start``, ``end`` and one of ``text_src`` or
    ``text``. Segments with empty text or zero-length slot contribute a
    ``0.0`` ratio (kept in the distribution so a video of mostly-silence
    is not classified hard just because of a couple of dense segments).

    Returns ``0.0`` if the input is empty.
    """
    ratios: list[float] = []
    for s in segments:
        text = (s.get("text_src") or s.get("text") or "")
        slot_s = float(s.get("end", 0)) - float(s.get("start", 0))
        ratios.append(
            estimate_segment_ratio(len(text), slot_s, target_lang_code, expansion_factor)
        )
    if not ratios:
        return 0.0
    ratios.sort()
    n = len(ratios)
    # P90 index using the round-half-up convention used elsewhere in the
    # CSV analysis script: idx = max(0, ceil(0.9 * n) - 1)
    p90_idx = max(0, min(n - 1, int(round(0.90 * n)) - 1))
    return ratios[p90_idx]


# Default classification thresholds derived from observed production data:
# - Matt Cutts TED EN->IT: P90 ~1.50, dub sounded fluent enough -> "medium"
#   threshold sits just above this so TED-style clears as "easy" or borderline
# - Fitzgerald comedy clip: P90 2.43, dub sounded heavily accelerated -> "hard"
EASY_THRESHOLD = 1.30
HARD_THRESHOLD = 1.80


def classify_difficulty(
    p90: float,
    easy_threshold: float = EASY_THRESHOLD,
    hard_threshold: float = HARD_THRESHOLD,
) -> str:
    """Map ``p90`` to one of ``"easy" | "medium" | "hard"``."""
    if p90 <= easy_threshold:
        return "easy"
    if p90 <= hard_threshold:
        return "medium"
    return "hard"


def format_difficulty_log(
    p90: float,
    classification: str,
    target_lang_code: str,
) -> str:
    """One-line log message for the translation pipeline.

    Format is intentionally informational, not a warning, because the
    metric is *predictive* and the pipeline still runs to completion.
    """
    lang = (target_lang_code or "").upper().split("-")[0] or "TARGET"
    if classification == "easy":
        return (
            f"[difficulty] Expected P90 stretch ratio: {p90:.2f} - "
            f"{lang} dub will be fluent"
        )
    if classification == "medium":
        return (
            f"[difficulty] Expected P90 stretch ratio: {p90:.2f} - "
            f"{lang} dub will have some audibly accelerated segments"
        )
    return (
        f"[difficulty] Expected P90 stretch ratio: {p90:.2f} - "
        f"{lang} dub will be audibly accelerated on most segments "
        f"(source likely too dense for the target language; consider "
        f"shortening the source or accepting the limit)"
    )


def _parse_srt_segments(path: str) -> list[dict]:
    """Minimal SRT parser used only by the standalone CLI.

    Returns a list of ``{"start": float, "end": float, "text": str}``
    dicts. Robust enough for files produced by the dubbing pipeline
    itself; not a full SRT spec implementation.
    """
    import os
    import re

    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    timing_re = re.compile(
        r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)"
    )
    out: list[dict] = []
    for block in blocks:
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        if len(lines) < 3:
            continue
        m = timing_re.search(lines[1])
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = m.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        text = " ".join(lines[2:])
        out.append({"start": start, "end": end, "text": text})
    return out


def _cli() -> int:
    """Standalone CLI: estimate dubbing difficulty from a segments file.

    Accepts an SRT (typical pipeline output) or a JSON list with
    ``start``, ``end`` and ``text`` keys. Useful to pre-flight a video
    after a fast Whisper-only run, before sinking compute into TTS.

    Exit codes:
        0 — analysis printed
        2 — file missing, unsupported format, or no segments parsed

    Examples:
        python3 -m videotranslator.difficulty_detector /home/u/Video/x_it.srt
        python3 -m videotranslator.difficulty_detector --target-lang es \\
            --expansion 1.20 segments.json
    """
    import argparse
    import json
    import os
    import sys

    parser = argparse.ArgumentParser(
        prog="python3 -m videotranslator.difficulty_detector",
        description=(
            "Estimate the P90 of pre-stretch ratio for a list of segments "
            "(.srt produced by the pipeline, or a JSON list of objects with "
            "start, end and text). Reports the expected difficulty class "
            "and the warning message the runtime would log."
        ),
    )
    parser.add_argument("input_file", help=".srt or .json segments file")
    parser.add_argument(
        "--target-lang",
        default="it",
        help="Target language code (default: it). Used for cps lookup.",
    )
    parser.add_argument(
        "--expansion",
        type=float,
        default=1.0,
        help=(
            "Lang-pair expansion factor (target/source). "
            "EN->IT ~= 1.25, IT->EN ~= 0.80. Default: 1.0 (neutral)."
        ),
    )
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"error: file not found: {args.input_file}", file=sys.stderr)
        return 2

    lower = args.input_file.lower()
    if lower.endswith(".json"):
        try:
            with open(args.input_file, encoding="utf-8") as fh:
                segments = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            print(f"error: cannot parse JSON: {e}", file=sys.stderr)
            return 2
        if not isinstance(segments, list):
            print("error: JSON root must be a list of segments", file=sys.stderr)
            return 2
    elif lower.endswith(".srt"):
        segments = _parse_srt_segments(args.input_file)
    else:
        print(
            "error: only .srt and .json files supported; got "
            f"{args.input_file}",
            file=sys.stderr,
        )
        return 2

    if not segments:
        print(
            f"error: no segments parsed from {args.input_file}",
            file=sys.stderr,
        )
        return 2

    p90 = estimate_p90_ratio(segments, args.target_lang, args.expansion)
    classification = classify_difficulty(p90)
    msg = format_difficulty_log(p90, classification, args.target_lang)

    print(f"File:                {args.input_file}")
    print(f"Segments analyzed:   {len(segments)}")
    print(f"Target language:     {args.target_lang}")
    print(f"Expansion factor:    {args.expansion}")
    print(f"P90 estimate:        {p90:.3f}")
    print(f"Classification:      {classification.upper()}")
    print()
    print(msg)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
