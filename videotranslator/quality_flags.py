"""Per-segment quality flags surfaced in the subtitle editor (TASK 5C).

Pipeline stages set string tags on each segment dict (under the
``_quality_flags`` key) when they detect candidates for human review:

- :data:`FLAG_LENGTH_UNFIT` — the LLM length retry loop exhausted its
  iterations without bringing the translation under
  ``target_chars * threshold``. Likely the translation is still too long
  for the audio slot and ``atempo`` will accelerate the dub past the
  comfortable listening band.
- :data:`FLAG_WHISPER_SUSPICIOUS` — Whisper sanity check (TASK 2M)
  flagged short non-words (``ay``, ``em``) or immediate repetitions
  (``the the``) in the source transcript. The translation propagates
  the noise downstream — manual edit recommended.
- :data:`FLAG_TRANSLATION_FALLBACK` — the primary translation engine
  (Ollama / DeepL / MarianMT) failed for the segment and the pipeline
  fell through to the secondary engine, or — worst case — kept the
  source text as-is. The translation is likely lower quality.

The module is **pure**: no I/O, no side effects, no Tk imports. The
GUI module reads the flags via :func:`compute_segment_quality_flags`
to colourise rows in the subtitle editor; the pipeline stages write
them via :func:`add_quality_flag`.

Design choice — list, not set: the flag count is small (<= 3 today)
and ordering matters for the editor priority resolver
(:func:`primary_flag`). A list with ``in`` membership checks keeps the
JSON-serialisability of the segment dicts intact for the metrics CSV
and the ``--subs-only`` save path.
"""

from __future__ import annotations

from typing import Iterable

# ── Public flag constants ────────────────────────────────────────────────
# Use strings (not Enum) so segments stay JSON-serialisable for the
# metrics CSV dump and so legacy callers that don't import this module
# can still inspect the flags ad-hoc.

FLAG_LENGTH_UNFIT: str = "length_unfit"
FLAG_WHISPER_SUSPICIOUS: str = "whisper_suspicious"
FLAG_TRANSLATION_FALLBACK: str = "translation_fallback"

# Priority order: the editor uses the *first* matching flag to colourise
# the row. Worst → least severe. ``translation_fallback`` is the most
# severe (the primary engine flat-out failed); ``length_unfit`` is mid
# (the translation exists but won't fit comfortably); ``whisper_suspicious``
# is the mildest (the translation may be fine even if the source had
# noise tokens, depending on the LLM's ability to bridge them).
_FLAG_PRIORITY: tuple[str, ...] = (
    FLAG_TRANSLATION_FALLBACK,
    FLAG_LENGTH_UNFIT,
    FLAG_WHISPER_SUSPICIOUS,
)

# Treeview tag colours for the dark Catppuccin Mocha theme (BG=#1e1e2e,
# FG=#cdd6f4). Foreground deliberately dark (#1e1e2e) so the row stands
# out against the surrounding rows AND remains legible — light-on-light
# would be unreadable on the high-saturation background colours below.
QUALITY_FLAG_COLOURS: dict[str, dict[str, str]] = {
    FLAG_TRANSLATION_FALLBACK: {
        "background": "#f38ba8",  # red — Catppuccin Mocha red, matches RED const
        "foreground": "#1e1e2e",
    },
    FLAG_LENGTH_UNFIT: {
        "background": "#fab387",  # peach
        "foreground": "#1e1e2e",
    },
    FLAG_WHISPER_SUSPICIOUS: {
        "background": "#f9e2af",  # yellow
        "foreground": "#1e1e2e",
    },
}


def add_quality_flag(seg: dict, flag: str) -> None:
    """Append ``flag`` to ``seg["_quality_flags"]`` if not already present.

    Initialises the list lazily — segments without flags don't carry
    the empty list, keeping the dict shape compatible with legacy
    callers that don't expect the key. No-op when ``flag`` is empty/None
    or already in the list.
    """
    if not flag:
        return
    if not isinstance(seg, dict):
        return
    flags = seg.get("_quality_flags")
    if not isinstance(flags, list):
        flags = []
        seg["_quality_flags"] = flags
    if flag not in flags:
        flags.append(flag)


def compute_segment_quality_flags(seg: dict) -> list[str]:
    """Return the flag list stored on ``seg`` (or ``[]`` if none).

    Defensive against malformed segments (non-dict, missing key,
    non-list value). The returned list is a *copy* so callers can
    safely reorder it for display without affecting the pipeline state.
    """
    if not isinstance(seg, dict):
        return []
    flags = seg.get("_quality_flags")
    if not isinstance(flags, list):
        return []
    return [f for f in flags if isinstance(f, str) and f]


def primary_flag(flags: Iterable[str]) -> str | None:
    """Pick the highest-priority flag for colouring a single row.

    The Treeview row can only carry one tag's colour at a time, so
    when a segment has multiple flags we pick the most severe one
    (per :data:`_FLAG_PRIORITY`). Returns ``None`` when ``flags`` is
    empty or contains only unknown strings.
    """
    if not flags:
        return None
    flag_set = {f for f in flags if isinstance(f, str)}
    if not flag_set:
        return None
    for known in _FLAG_PRIORITY:
        if known in flag_set:
            return known
    return None


def has_any_flag(seg: dict) -> bool:
    """Convenience: does the segment carry at least one quality flag?"""
    return bool(compute_segment_quality_flags(seg))


__all__ = [
    "FLAG_LENGTH_UNFIT",
    "FLAG_WHISPER_SUSPICIOUS",
    "FLAG_TRANSLATION_FALLBACK",
    "QUALITY_FLAG_COLOURS",
    "add_quality_flag",
    "compute_segment_quality_flags",
    "primary_flag",
    "has_any_flag",
]
