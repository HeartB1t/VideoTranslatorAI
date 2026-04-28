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
