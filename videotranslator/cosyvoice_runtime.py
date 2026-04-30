"""CosyVoice install/cache/model helpers."""

from __future__ import annotations

import contextlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any


COSYVOICE_PIP_PKG = "cosyvoice"


def cosyvoice_cache_dir(
    *,
    sys_platform: str | None = None,
    env: dict[str, str] | None = None,
    home: Path | None = None,
    temp_dir: str | None = None,
) -> Path:
    """Return the cache directory used for CosyVoice model weights."""
    platform = sys_platform or sys.platform
    env_map = env or os.environ
    home_path = home or Path.home()
    if platform.startswith("win"):
        base = Path(env_map.get("LOCALAPPDATA", str(home_path))) / "VideoTranslatorAI"
    else:
        base = Path(env_map.get("XDG_CACHE_HOME", str(home_path / ".cache"))) / "videotranslatorai"
    cache = base / "cosyvoice"
    try:
        cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache = Path(temp_dir or tempfile.gettempdir()) / "videotranslatorai_cosyvoice"
        cache.mkdir(parents=True, exist_ok=True)
    return cache


def cosyvoice_is_installed(find_spec: Callable[[str], Any] = importlib.util.find_spec) -> bool:
    """Return True when the Python package `cosyvoice` is importable."""
    try:
        return find_spec("cosyvoice") is not None
    except (ValueError, ModuleNotFoundError, ImportError):
        return False


def cosyvoice_model_present(cache_dir: Path | None = None) -> bool:
    """Return True if the CosyVoice-300M-Instruct marker file exists."""
    cache = cache_dir or cosyvoice_cache_dir()
    return (cache / "CosyVoice-300M-Instruct" / "llm.pt").exists()


def cosyvoice_install(
    *,
    log_cb: Callable[[str], None] | None = None,
    timeout_s: int = 1800,
    version_info: tuple[int, int] | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
    timer_factory: Callable[..., Any] = threading.Timer,
    register_subprocess: Callable[[Any], None] | None = None,
    unregister_subprocess: Callable[[Any], None] | None = None,
    python_executable: str = sys.executable,
) -> tuple[bool, str]:
    """Install the CosyVoice community wrapper in the current runtime."""
    log = log_cb or (lambda _s: None)
    py_major, py_minor = version_info or (sys.version_info.major, sys.version_info.minor)
    if (py_major, py_minor) >= (3, 12):
        msg = (
            f"Python {py_major}.{py_minor} non supportato dal community "
            f"wrapper PyPI 'cosyvoice 0.0.8' (setup.py KeyError __version__). "
            f"CosyVoice ufficiale richiede Python 3.10 in conda env dedicato. "
            f"Setup manuale: vedi docs/COSYVOICE_INSTALL.md (clone GitHub + "
            f"conda env). Per ora la pipeline ricade su XTTS v2."
        )
        log(f"[!] {msg}\n")
        return False, msg

    cmd = [
        python_executable,
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "--no-color",
        COSYVOICE_PIP_PKG,
    ]
    log(f"[*] pip install {COSYVOICE_PIP_PKG} (può richiedere alcuni minuti)...\n")
    try:
        proc = popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return False, f"Failed to spawn pip install: {exc}"

    if register_subprocess is not None:
        register_subprocess(proc)
    timed_out = {"fired": False}

    def on_timeout() -> None:
        timed_out["fired"] = True
        with contextlib.suppress(Exception):
            proc.kill()
            if proc.stdout is not None:
                proc.stdout.close()

    watchdog = timer_factory(timeout_s, on_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"    {line}\n")
        with contextlib.suppress(Exception):
            proc.wait(timeout=30)
    except Exception as exc:
        log(f"    ! pip install error: {exc}\n")
    finally:
        watchdog.cancel()
        if unregister_subprocess is not None:
            unregister_subprocess(proc)

    if timed_out["fired"]:
        return False, f"pip install timed out after {timeout_s}s"
    if proc.returncode != 0:
        return False, f"pip install {COSYVOICE_PIP_PKG} failed (rc={proc.returncode})"
    return True, ""


def cosyvoice_download_model(
    cache_dir: Path | None = None,
    *,
    log_cb: Callable[[str], None] | None = None,
    modelscope_snapshot_download: Callable[..., Any] | None = None,
    hf_snapshot_download: Callable[..., Any] | None = None,
) -> tuple[bool, str]:
    """Download CosyVoice-300M-Instruct through ModelScope, then HuggingFace."""
    log = log_cb or (lambda _s: None)
    cache = cache_dir or cosyvoice_cache_dir()
    target_dir = cache / "CosyVoice-300M-Instruct"
    if (target_dir / "llm.pt").exists():
        log(f"[+] CosyVoice model già presente in {target_dir}\n")
        return True, ""

    log(f"[*] Download CosyVoice-300M-Instruct (~1.7 GB) → {target_dir}...\n")
    try:
        if modelscope_snapshot_download is None:
            from modelscope import snapshot_download as modelscope_snapshot_download  # type: ignore
        modelscope_snapshot_download("iic/CosyVoice-300M-Instruct", local_dir=str(target_dir))
        log("[+] Download da ModelScope OK\n")
        return True, ""
    except Exception as exc:
        log(f"    ! ModelScope download fallito ({exc}), provo HuggingFace...\n")

    try:
        if hf_snapshot_download is None:
            from huggingface_hub import snapshot_download as hf_snapshot_download  # type: ignore
        hf_snapshot_download(
            repo_id="model-scope/CosyVoice-300M-Instruct",
            local_dir=str(target_dir),
        )
        log("[+] Download da HuggingFace OK\n")
        return True, ""
    except Exception as exc:
        return False, f"Sia ModelScope che HuggingFace hanno fallito: {exc}"
