"""Media helpers shared by the GUI, CLI and future pipeline modules."""

from __future__ import annotations

import subprocess
import os
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any


SubprocessRun = Callable[..., Any]
LogCallback = Callable[[str], None]


def run_ffmpeg(
    cmd: list[str],
    step: str = "ffmpeg",
    *,
    run: SubprocessRun = subprocess.run,
):
    """Run ffmpeg and raise a concise RuntimeError on failure."""
    proc = run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()[-10:]
        raise RuntimeError(f"{step} failed (exit {proc.returncode}):\n" + "\n".join(err))
    return proc


def build_extract_audio_cmd(video_path: str, audio_path: str) -> list[str]:
    """Return the ffmpeg command used for the first pipeline audio extraction."""
    return [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "2",
        audio_path,
    ]


def build_resample_vocals_cmd(vocals_raw_path: str, vocals_16k_path: str) -> list[str]:
    """Return the ffmpeg command that prepares Demucs vocals for Whisper."""
    return [
        "ffmpeg",
        "-y",
        "-i",
        vocals_raw_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        vocals_16k_path,
    ]


def demucs_apply_kwargs(apply_model: Callable[..., Any], device: str) -> dict[str, Any]:
    """Return safe Demucs apply_model kwargs for this installed version."""
    kwargs: dict[str, Any] = {"device": device}
    try:
        sig = inspect.signature(apply_model)
        if "segment" in sig.parameters:
            kwargs["segment"] = 7.0
        if "overlap" in sig.parameters:
            kwargs["overlap"] = 0.25
    except (TypeError, ValueError):
        pass
    return kwargs


def extract_audio(
    video_path: str,
    audio_path: str,
    *,
    log_cb: LogCallback | None = None,
    runner: Callable[[list[str], str], Any] = run_ffmpeg,
) -> None:
    """Extract stereo 44.1 kHz PCM audio from a video file."""
    if log_cb is not None:
        log_cb(f"[1/6] Extracting audio from: {Path(video_path).name}")
    runner(build_extract_audio_cmd(video_path, audio_path), "extract_audio")
    if log_cb is not None:
        log_cb(f"     -> {audio_path}")


def separate_audio(
    audio_path: str,
    tmp_dir: str,
    *,
    log_cb: LogCallback | None = None,
    ffmpeg_runner: Callable[[list[str], str], Any] = run_ffmpeg,
) -> tuple[str, str]:
    """Separate voice/music with Demucs and return ``(vocals_16k, background)``."""
    if log_cb is not None:
        log_cb("[2/6] Separating voice/music with Demucs...")

    import torch
    import torchaudio
    from demucs import pretrained
    from demucs.apply import apply_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = pretrained.get_model("htdemucs")
    model.to(device)

    waveform, sr = torchaudio.load(audio_path)
    if waveform.shape[0] == 1:
        waveform = waveform.repeat(2, 1)
    waveform = waveform.to(device)

    sources = None
    try:
        with torch.no_grad():
            sources = apply_model(
                model,
                waveform.unsqueeze(0),
                **demucs_apply_kwargs(apply_model, device),
            )[0]
        vocals = sources[3].mean(0, keepdim=True).cpu()
        background = sources[:3].sum(0).mean(0, keepdim=True).cpu()
    finally:
        del model, waveform
        if sources is not None:
            del sources
        if device == "cuda":
            torch.cuda.empty_cache()

    vocals_raw = os.path.join(tmp_dir, "vocals_raw.wav")
    vocals_16k = os.path.join(tmp_dir, "vocals_16k.wav")
    bg_path = os.path.join(tmp_dir, "background.wav")

    torchaudio.save(vocals_raw, vocals, sr)
    torchaudio.save(bg_path, background, sr)

    ffmpeg_runner(
        build_resample_vocals_cmd(vocals_raw, vocals_16k),
        "resample vocals",
    )

    if log_cb is not None:
        log_cb(f"     -> Vocals (16kHz): {vocals_16k}")
        log_cb(f"     -> Background: {bg_path}")
    return vocals_16k, bg_path
