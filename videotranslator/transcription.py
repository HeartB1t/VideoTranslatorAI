"""faster-Whisper transcription helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .hotwords import to_whisper_param

LogCallback = Callable[[str], None]


def whisper_device_and_compute(torch_module: Any) -> tuple[str, str]:
    """Return the preferred faster-Whisper device and compute type."""
    device = "cuda" if torch_module.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    return device, compute


def build_transcribe_kwargs(
    lang_source: str,
    hotwords: list[str] | None = None,
) -> dict[str, Any]:
    """Return the standard faster-Whisper decoding parameters."""
    kwargs: dict[str, Any] = {
        "language": None if lang_source == "auto" else lang_source,
        "beam_size": 5,
        "vad_filter": True,
        "vad_parameters": {"threshold": 0.3, "min_silence_duration_ms": 300},
        "condition_on_previous_text": False,
        "repetition_penalty": 1.3,
        "no_repeat_ngram_size": 3,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "temperature": 0,
    }
    hotwords_param = to_whisper_param(hotwords)
    if hotwords_param:
        kwargs["hotwords"] = hotwords_param
    return kwargs


def normalize_whisper_segments(raw_segments: Iterable[Any]) -> list[dict[str, Any]]:
    """Convert faster-Whisper segments to plain dicts and drop adjacent dupes."""
    out: list[dict[str, Any]] = []
    prev_text: str | None = None
    for segment in raw_segments:
        text = (getattr(segment, "text", "") or "").strip()
        if text and text != prev_text:
            out.append(
                {
                    "start": getattr(segment, "start"),
                    "end": getattr(segment, "end"),
                    "text": text,
                }
            )
            prev_text = text
    return out


def is_cuda_runtime_error(exc: BaseException) -> bool:
    """Return True when a faster-Whisper RuntimeError should retry on CPU."""
    msg = str(exc)
    return "libcublas" in msg or "CUDA" in msg or "cuda" in msg.lower()


def transcribe_audio(
    audio_path: str,
    model_name: str,
    lang_source: str,
    hotwords: list[str] | None = None,
    *,
    whisper_model_cls: Callable[..., Any] | None = None,
    torch_module: Any | None = None,
    log_cb: LogCallback | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Transcribe an audio file with faster-Whisper and return segments/language."""
    if torch_module is None:
        import torch as torch_module
    if whisper_model_cls is None:
        from faster_whisper import WhisperModel

        whisper_model_cls = WhisperModel

    device, compute = whisper_device_and_compute(torch_module)
    if log_cb is not None:
        log_cb(f"[3/6] Transcribing with faster-Whisper (model={model_name}, device={device})...")

    model = None
    try:
        try:
            model = whisper_model_cls(model_name, device=device, compute_type=compute)
        except Exception as exc:
            if device != "cuda":
                raise
            if log_cb is not None:
                log_cb(f"     ! CUDA unavailable ({exc}), falling back to CPU...")
            device, compute = "cpu", "int8"
            model = whisper_model_cls(model_name, device=device, compute_type=compute)

        kwargs = build_transcribe_kwargs(lang_source, hotwords)
        if "hotwords" in kwargs and log_cb is not None:
            log_cb(f"     [whisper] biased decoding with {len(hotwords or [])} hotwords")

        def run_with(current_device: str, current_compute: str):
            nonlocal model
            if current_device != device:
                del model
                model = whisper_model_cls(
                    model_name,
                    device=current_device,
                    compute_type=current_compute,
                )
            raw_segments, info = model.transcribe(audio_path, **kwargs)
            return normalize_whisper_segments(raw_segments), info

        try:
            result, info = run_with(device, compute)
        except RuntimeError as exc:
            if device == "cuda" and is_cuda_runtime_error(exc):
                if log_cb is not None:
                    log_cb(f"     ! CUDA error during inference ({exc}), retrying on CPU...")
                result, info = run_with("cpu", "int8")
                device = "cpu"
            else:
                raise
    finally:
        if model is not None:
            del model
        try:
            if device == "cuda":
                torch_module.cuda.empty_cache()
        except Exception:
            pass

    detected = getattr(info, "language", None) or lang_source
    if log_cb is not None:
        log_cb(f"     -> {len(result)} segments | detected language: {detected}")
    return result, detected
