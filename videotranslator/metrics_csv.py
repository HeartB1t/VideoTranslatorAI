"""Per-segment metrics CSV dump.

Records the data needed to compute P90/P95 of stretch ratios across
multiple test runs: this is the single most useful number for evaluating
dubbing quality, because the user perceives the worst few segments, not
the average.

Each row corresponds to one segment in the pipeline. Fields are stable
across runs so external scripts (notebook, awk, sqlite) can join them.

Schema:

  segment_index            0-based index in the segment list
  start_s, end_s, slot_s   timestamps and slot duration in seconds
  src_chars, tgt_chars     character lengths of source / translation
  target_chars             length budget computed from slot_s and target lang cps
  length_retry_attempted   True if the re-prompt loop fired for this segment
  length_retry_succeeded   True if the retry produced a strictly shorter text
  tts_duration_ms          observed TTS output duration before stretch
  pre_stretch_ratio        tts_duration_ms / slot_ms (key audibility metric)
  stretch_engine           'none', 'atempo', 'rubberband', 'atempo_fallback'
  stretch_truncated        True if audio was hard-cut after stretch (>4x cap)
  text_src, text_tgt       full source / translation text for outlier audit
"""

from __future__ import annotations

import csv
from typing import Iterable, Mapping

CSV_FIELDS: tuple[str, ...] = (
    "segment_index",
    "start_s",
    "end_s",
    "slot_s",
    "src_chars",
    "tgt_chars",
    "target_chars",
    "length_retry_attempted",
    "length_retry_succeeded",
    "tts_duration_ms",
    "pre_stretch_ratio",
    "stretch_engine",
    "stretch_truncated",
    "text_src",
    "text_tgt",
)


def normalize_row(raw: Mapping[str, object]) -> dict[str, object]:
    """Return a row dict with all CSV_FIELDS populated.

    Missing fields default to "" so the CSV stays rectangular when a
    pipeline phase has no data for some segments (e.g. silent segments
    skip TTS so tts_duration_ms is empty).
    """
    return {field: raw.get(field, "") for field in CSV_FIELDS}


def dump_segment_metrics(rows: Iterable[Mapping[str, object]], path: str) -> int:
    """Write one CSV row per segment in `rows` to `path`.

    Returns the number of rows written. Caller is responsible for
    catching IOError / PermissionError if the destination is not
    writable: the metrics file is informational and must never abort
    the dubbing pipeline on failure.
    """
    written = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=list(CSV_FIELDS), extrasaction="ignore"
        )
        writer.writeheader()
        for raw in rows:
            writer.writerow(normalize_row(raw))
            written += 1
    return written


def _cli() -> int:
    """Standalone analyzer: read a metrics CSV and print P50/P75/P90/P95,
    distribution buckets, engine breakdown and top-N outliers with text.

    Exit codes:
        0 — analysis printed
        2 — file missing or empty / malformed

    Example:
        python3 -m videotranslator.metrics_csv ~/Video/yt_xxx_it_metrics.csv
        python3 -m videotranslator.metrics_csv --top 5 m.csv
    """
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(
        prog="python3 -m videotranslator.metrics_csv",
        description=(
            "Analyze a per-segment metrics CSV produced by build_dubbed_track. "
            "Reports P50/P75/P90/P95 of pre_stretch_ratio, distribution by "
            "audibility band, breakdown by stretch engine, and the top-N "
            "outliers with their text for semantic audit."
        ),
    )
    parser.add_argument("csv_file", help="Path to a *_metrics.csv file.")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of worst outliers to display (default: 10).",
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"error: csv not found: {args.csv_file}", file=sys.stderr)
        return 2

    with open(args.csv_file, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print(f"error: csv is empty: {args.csv_file}", file=sys.stderr)
        return 2

    def _ratio(r):
        try:
            return float(r.get("pre_stretch_ratio", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    ratios = sorted(_ratio(r) for r in rows)
    n = len(ratios)

    def percentile(p: int) -> float:
        idx = max(0, min(n - 1, int(round(p * n / 100)) - 1))
        return ratios[idx]

    print(f"File:             {args.csv_file}")
    print(f"Segments:         {n}")
    print(f"Mean ratio:       {sum(ratios) / n:.3f}")
    print(f"Median (P50):     {percentile(50):.3f}")
    print(f"P75:              {percentile(75):.3f}")
    print(f"P90:              {percentile(90):.3f}")
    print(f"P95:              {percentile(95):.3f}")
    print(f"Min / Max:        {min(ratios):.3f} / {max(ratios):.3f}")

    print()
    print("Distribution by audibility band:")
    zones = (
        (0.0, 1.00, "fit       "),
        (1.00, 1.10, "imperc    "),
        (1.10, 1.30, "mild      "),
        (1.30, 1.50, "noticeable"),
        (1.50, 2.00, "strong    "),
        (2.00, 99.0, "severe    "),
    )
    for lo, hi, label in zones:
        count = sum(1 for r in ratios if lo < r <= hi or (lo == 0.0 and r <= 0.0))
        # Special case: include 0.0 in "fit" bucket so silent segments
        # are not orphaned.
        if lo == 0.0:
            count = sum(1 for r in ratios if r <= hi)
        pct = 100.0 * count / n
        bar = "#" * int(40 * count / n)
        print(f"  {label}: {count:>4d}  ({pct:5.1f}%) {bar}")

    print()
    print("Stretch engine breakdown:")
    engines: dict[str, int] = {}
    for r in rows:
        engines[r.get("stretch_engine", "?") or "?"] = (
            engines.get(r.get("stretch_engine", "?") or "?", 0) + 1
        )
    for engine, count in sorted(engines.items(), key=lambda kv: -kv[1]):
        print(f"  {engine:<20s} {count}")

    print()
    print(f"Top {min(args.top, n)} worst outliers (highest ratio):")
    worst = sorted(rows, key=lambda r: -_ratio(r))[: args.top]
    for r in worst:
        idx = r.get("segment_index", "?") or "?"
        ratio = _ratio(r)
        engine = (r.get("stretch_engine") or "?")[:18]
        slot = r.get("slot_s", "?")
        text_tgt = (r.get("text_tgt") or "")[:90]
        print(
            f"  #{idx:>3} ratio={ratio:5.2f} engine={engine:<18s} "
            f"slot={slot}s"
        )
        if text_tgt:
            print(f"        TGT: {text_tgt}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
