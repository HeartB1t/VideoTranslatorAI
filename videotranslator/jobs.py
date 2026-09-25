"""Structured job configuration for the translation pipeline.

The GUI and CLI still live in ``video_translator_gui.py`` while the
monolith is being reduced. This module gives both entry points a shared,
testable contract for the many options passed into ``translate_video``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranslationJobConfig:
    """Immutable options for a single video translation job."""

    video_in: str
    output: str | None = None
    output_dir: str | None = None
    model: str = "small"
    lang_source: str = "auto"
    lang_target: str = "it"
    voice: str | None = None
    tts_rate: str = "+0%"
    no_subs: bool = False
    subs_only: bool = False
    no_demucs: bool = False
    translation_engine: str = "google"
    deepl_key: str = ""
    segments_override: list[dict[str, Any]] | None = None
    tts_engine: str = "edge"
    use_diarization: bool = False
    hf_token: str = ""
    use_lipsync: bool = False
    xtts_speed: float | None = None
    ollama_model: str = "qwen3:8b"
    ollama_url: str = "http://localhost:11434"
    ollama_slot_aware: bool = True
    ollama_thinking: bool = False
    ollama_document_context: bool = True
    slot_expansion: bool = True
    sentence_repair: bool = True
    overlap_fade_enabled: bool = True
    whisper_sanity: bool = True
    difficulty_profile_enabled: bool = True
    difficulty_override: str | None = None
    hotwords: list[str] | None = field(default=None)
    ollama_use_cove: bool = True
    keep_original_audio: bool = True

    def to_translate_video_kwargs(self) -> dict[str, Any]:
        """Return kwargs compatible with legacy ``translate_video``."""
        return asdict(self)


@dataclass(frozen=True)
class TranslationJobResult:
    """Normalized wrapper around the legacy pipeline result dict."""

    outputs: dict[str, Any]

    @property
    def output_path(self) -> str | None:
        value = (
            self.outputs.get("output")
            or self.outputs.get("video")
            or self.outputs.get("video_out")
        )
        return str(value) if value else None

    @property
    def subtitle_path(self) -> str | None:
        value = self.outputs.get("srt") or self.outputs.get("subtitle")
        return str(value) if value else None


@dataclass(frozen=True)
class JobOutput:
    """Stable, UI-safe description of a completed pipeline artifact."""

    video_path: str | None = None
    subtitle_path: str | None = None
    source_path: str | None = None
    title: str | None = None

    @classmethod
    def from_result(cls, result: dict[str, Any] | TranslationJobResult,
                    *, source_path: str | None = None) -> "JobOutput":
        outputs = result.outputs if isinstance(result, TranslationJobResult) else result
        normalized = TranslationJobResult(outputs=outputs or {})
        video = normalized.output_path
        return cls(video, normalized.subtitle_path, source_path,
                   Path(video).name if video else None)


@dataclass(frozen=True)
class PipelineProgressEvent:
    """Small progress event for future GUI/headless pipeline callbacks."""

    stage: str
    message: str
    current: int | None = None
    total: int | None = None
