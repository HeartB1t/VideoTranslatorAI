"""Wav2Lip runtime helpers."""

from __future__ import annotations

import os
import shutil
import sys
import threading
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


def select_torch_device_and_release_vram() -> str:
    """Return the preferred torch device and free CUDA cache when possible."""
    try:
        import torch  # type: ignore

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return device
    except Exception:
        return "cpu"


def build_wav2lip_env(repo_dir: Path, work_dir: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Build subprocess environment for Wav2Lip with scratch IO in work_dir."""
    env = dict(base_env or os.environ)
    env["PYTHONPATH"] = str(repo_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["TMPDIR"] = str(work_dir)
    env["TEMP"] = str(work_dir)
    env["TMP"] = str(work_dir)
    return env


def build_wav2lip_command(
    video_path: str,
    audio_path: str,
    out_path: str,
    *,
    inference_py: Path,
    checkpoint_path: Path,
    python_executable: str = sys.executable,
) -> list[str]:
    """Build the Wav2Lip inference command."""
    return [
        python_executable,
        str(inference_py),
        "--checkpoint_path",
        str(checkpoint_path),
        "--face",
        video_path,
        "--audio",
        audio_path,
        "--outfile",
        out_path,
        "--nosmooth",
    ]


def apply_lipsync(
    video_path: str,
    audio_path: str,
    tmp_dir: str,
    *,
    wav2lip_repo: Path,
    wav2lip_model: Path,
    wav2lip_work_dir: Path,
    ensure_assets: Callable[[], None],
    timeout: int = 3600,
    register_subprocess: Callable[[Any], None] | None = None,
    unregister_subprocess: Callable[[Any], None] | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
    timer_factory: Callable[..., Any] = threading.Timer,
    device_selector: Callable[[], str] = select_torch_device_and_release_vram,
    log: Callable[..., None] = print,
) -> str:
    """Sync lips of video_path with audio_path via Wav2Lip."""
    log("[+] Applying Lip Sync (Wav2Lip)...", flush=True)
    ensure_assets()

    device = device_selector()
    log(f"     Wav2Lip device: {device}", flush=True)

    inference_py = wav2lip_repo / "inference.py"
    if not inference_py.exists():
        raise RuntimeError(f"Wav2Lip inference script not found: {inference_py}")

    try:
        wav2lip_work_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as exc:
        raise RuntimeError(
            f"Wav2Lip work directory is not writable: {wav2lip_work_dir}"
        ) from exc

    out_path = os.path.join(tmp_dir, "video_lipsync.mp4")
    cmd = build_wav2lip_command(
        video_path,
        audio_path,
        out_path,
        inference_py=inference_py,
        checkpoint_path=wav2lip_model,
    )
    env = build_wav2lip_env(wav2lip_repo, wav2lip_work_dir)

    output_lines: list[str] = []
    proc = popen(
        cmd,
        cwd=str(wav2lip_work_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if register_subprocess is not None:
        register_subprocess(proc)
    watchdog = timer_factory(timeout, proc.kill)
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            log(f"     [wav2lip] {line}", flush=True)
        proc.wait()
    except Exception:
        proc.kill()
        proc.wait()
        raise
    finally:
        watchdog.cancel()
        if unregister_subprocess is not None:
            unregister_subprocess(proc)
        wav2lip_tmp = wav2lip_work_dir / "temp"
        if wav2lip_tmp.exists():
            shutil.rmtree(wav2lip_tmp, ignore_errors=True)

    if proc.returncode != 0 or not os.path.exists(out_path):
        tail = "\n".join(output_lines[-20:])
        raise RuntimeError(f"Wav2Lip failed (exit {proc.returncode}):\n{tail}")

    log(f"     → Lip sync done: {out_path}", flush=True)
    return out_path
