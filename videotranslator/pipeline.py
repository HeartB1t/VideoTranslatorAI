"""Thin testable pipeline entry point.

This is intentionally small: the heavy implementation still lives in the
legacy GUI module. New callers can depend on this stable contract while
the monolith is reduced one stage at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .jobs import PipelineProgressEvent, TranslationJobConfig, TranslationJobResult

PipelineRunner = Callable[..., dict[str, Any]]
ProgressCallback = Callable[[PipelineProgressEvent], None]


def run_translation_job(
    config: TranslationJobConfig,
    *,
    runner: PipelineRunner,
    progress_cb: ProgressCallback | None = None,
) -> TranslationJobResult:
    """Run one translation job through an injected legacy-compatible runner."""
    if progress_cb is not None:
        progress_cb(PipelineProgressEvent("start", config.video_in, current=0, total=1))
    raw = runner(**config.to_translate_video_kwargs())
    result = TranslationJobResult(outputs=raw or {})
    if progress_cb is not None:
        progress_cb(PipelineProgressEvent("done", config.video_in, current=1, total=1))
    return result
