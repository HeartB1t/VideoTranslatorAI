"""Audio mixing helpers used by the dubbing track assembler."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any


def overlay_pcm(mix: Any, pcm: Any, start_frame: int, total_frames: int) -> None:
    """Overlay an int16 PCM buffer into an int32 mix buffer in-place."""
    end_frame = min(start_frame + pcm.shape[0], total_frames)
    length = end_frame - start_frame
    if length <= 0:
        return
    mix[start_frame:end_frame] += pcm[:length].astype("int32")


def apply_tail_fade(pcm: Any, fade_len: int) -> Any:
    """Apply a linear fade-out to the tail of a PCM buffer."""
    import numpy as np  # type: ignore

    fade_len = max(1, min(fade_len, pcm.shape[0] // 4 or 1))
    ramp = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    tail = pcm[-fade_len:].astype(np.float32) * ramp[:, None]
    pcm[-fade_len:] = tail.astype(np.int16)
    return pcm


def read_segment_to_pcm(
    path: str,
    *,
    tmp_dir: str,
    sample_rate: int = 44100,
    channels: int = 2,
    sf_module: Any | None = None,
    run_ffmpeg: Callable[[list[str]], None] | Callable[..., None] | None = None,
    log: Callable[..., None] = print,
) -> Any | None:
    """Read a segment as int16 PCM, converting to target sample rate/channels when needed."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    if sf_module is None:
        import soundfile as sf_module  # type: ignore
    try:
        data, sr = sf_module.read(path, dtype="int16", always_2d=True)
    except Exception as exc:
        log(f"     ! Cannot read {path}: {exc}", flush=True)
        return None
    if data.size == 0:
        return None
    if sr == sample_rate and data.shape[1] == channels:
        return data
    if run_ffmpeg is None:
        raise RuntimeError("run_ffmpeg callback is required for PCM conversion")

    conv = os.path.join(tmp_dir, Path(path).stem + "_pcm.wav")
    try:
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                path,
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                "-sample_fmt",
                "s16",
                conv,
            ],
            step=f"pcm conv {Path(path).name}",
        )
        return sf_module.read(conv, dtype="int16", always_2d=True)[0]
    except Exception as exc:
        log(f"     ! PCM conv failed {path}: {exc}", flush=True)
        return None
