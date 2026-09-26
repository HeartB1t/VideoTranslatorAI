"""Download, verify and benchmark the Whisper speech models.

Feature "hardware-aware model selection", steps 4 and 5. Only Whisper is
downloaded here: it is the stage whose model depends most on the hardware.
MarianMT and XTTS are fetched by their libraries on first use, Ollama models
by ``ollama pull``; the catalogue labels them accordingly.

- Download: a separate Python process runs ``faster_whisper.download_model``,
  so a Cancel terminates it at once; the Hugging Face cache keeps the partial
  ``.incomplete`` file and the next attempt resumes it. A file is promoted in
  the cache only when complete, so an interrupted download never replaces a
  working model, and the app keeps using the current model until the new one
  is verified and the user applies it.
- Verification: every downloaded file is hashed and compared with the Hub
  metadata (SHA-256 for large LFS files, the git blob id for small ones).
- Benchmark: opt-in, on the first seconds of a local media file; it measures
  load time, time to the first transcribed segment and the real-time factor.
  Nothing is uploaded: the audio stays on the PC.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .hardware_profile import default_model_dir
from .model_catalog import WHISPER
from .subprocess_utils import no_window_kwargs

_WEIGHTS = "model.bin"


def _lookup(repo: str, filename: str) -> str | None:
    try:
        from huggingface_hub import try_to_load_from_cache
    except Exception:
        return None
    try:
        found = try_to_load_from_cache(repo, filename)
    except Exception:
        return None
    return found if isinstance(found, str) else None


def whisper_snapshot_dir(key: str, *,
                         lookup: Callable[[str, str], str | None] = _lookup) -> Path | None:
    """Folder of the cached model files, or None when the model is not on disk."""
    opt = WHISPER.get(key)
    if opt is None or not opt.repo:
        return None
    path = lookup(opt.repo, _WEIGHTS)
    return Path(path).parent if path else None


def cached_whisper_models(*, lookup: Callable[[str, str], str | None] = _lookup) -> set[str]:
    return {key for key in WHISPER if whisper_snapshot_dir(key, lookup=lookup) is not None}


def repo_cache_dir(repo: str, *, root: Path | None = None) -> Path:
    base = (root or default_model_dir()) / "hub"
    return base / ("models--" + repo.replace("/", "--"))


def downloaded_mb(repo: str, *, root: Path | None = None) -> float:
    """MB already in the cache for ``repo`` (partial files included): progress."""
    blobs = repo_cache_dir(repo, root=root) / "blobs"
    total = 0
    try:
        for item in blobs.iterdir():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    except OSError:
        return 0.0
    return total / (1024 * 1024)


# --- verification ------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # noqa: S324


def _model_info(repo: str, revision: str) -> Any:
    from huggingface_hub import HfApi
    return HfApi().model_info(repo, revision=revision, files_metadata=True)


def verify_snapshot(repo: str, snapshot: Path, *,
                    model_info: Callable[[str, str], Any] = _model_info) -> list[str]:
    """Names of the files in ``snapshot`` whose hash differs from the Hub.

    An empty list means every downloaded file matches. The snapshot folder name
    is the commit the files came from, so they are checked against it.
    """
    info = model_info(repo, snapshot.name)
    bad: list[str] = []
    for sibling in getattr(info, "siblings", None) or []:
        path = snapshot / sibling.rfilename
        if not path.is_file():
            continue                   # not part of the download (README, ...)
        lfs = getattr(sibling, "lfs", None)
        if lfs is not None and getattr(lfs, "sha256", None):
            ok = _file_sha256(path) == lfs.sha256
        elif getattr(sibling, "blob_id", None):
            ok = _git_blob_sha1(path) == sibling.blob_id
        else:
            continue
        if not ok:
            bad.append(sibling.rfilename)
    if not (snapshot / _WEIGHTS).is_file():
        bad.append(_WEIGHTS)
    return bad


# --- download ----------------------------------------------------------------

_DOWNLOAD_SCRIPT = (
    "import sys\n"
    "from faster_whisper import download_model\n"
    "download_model(sys.argv[1])\n"
)


class WhisperDownload:
    """Download one Whisper model in a child process, then verify it.

    ``state`` goes running -> verifying -> done | failed | cancelled; poll it
    (and ``progress_mb``) from the Tk thread. ``error`` holds the reason of a
    failure. Never blocks the caller.
    """

    def __init__(self, key: str, *, popen: Callable[..., Any] = subprocess.Popen,
                 verify: Callable[[str, Path], list[str]] = verify_snapshot,
                 snapshot_dir: Callable[[str], Path | None] = whisper_snapshot_dir,
                 python: str | None = None) -> None:
        opt = WHISPER[key]
        self.key = key
        self.repo = opt.repo or ""
        self.expected_mb = opt.download_mb
        self._popen = popen
        self._verify = verify
        self._snapshot_dir = snapshot_dir
        self._python = python or sys.executable
        self._lock = threading.Lock()
        self._proc: Any = None
        self._cancelled = False
        self.state = "idle"
        self.error = ""
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self.state != "idle":
                return
            self.state = "running"
        self._thread = threading.Thread(target=self._run, name="model-download",
                                        daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            proc = self._proc
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass

    def progress_mb(self) -> float:
        return downloaded_mb(self.repo) if self.repo else 0.0

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def _finish(self, state: str, error: str = "") -> None:
        with self._lock:
            self.state = "cancelled" if self._cancelled else state
            self.error = "" if self._cancelled else error

    def _run(self) -> None:
        try:
            with self._lock:
                if self._cancelled:
                    self.state = "cancelled"
                    return
                self._proc = self._popen(
                    [self._python, "-c", _DOWNLOAD_SCRIPT, self.key],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE, **no_window_kwargs(sys.platform))
            _out, err = self._proc.communicate()
            if self._cancelled:
                self._finish("cancelled")
                return
            if self._proc.returncode != 0:
                detail = (err or b"").decode("utf-8", "replace").strip().splitlines()
                self._finish("failed", detail[-1] if detail else "download failed")
                return
            with self._lock:
                self.state = "verifying"
            snapshot = self._snapshot_dir(self.key)
            if snapshot is None:
                self._finish("failed", "model not found in the cache after download")
                return
            bad = self._verify(self.repo, snapshot)
            if bad:
                self._finish("failed", "checksum mismatch: " + ", ".join(bad))
                return
            self._finish("done")
        except Exception as exc:                # noqa: BLE001 (reported, not raised)
            self._finish("failed", str(exc) or type(exc).__name__)


# --- benchmark ---------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkResult:
    model: str
    device: str
    audio_s: float
    load_s: float
    first_segment_s: float | None   # from the start of transcription
    total_s: float

    @property
    def realtime_factor(self) -> float:
        """Transcription time / audio time: below 1.0 is faster than real time."""
        return self.total_s / self.audio_s if self.audio_s > 0 else float("inf")


def read_audio_16k(path: str, seconds: float, *,
                   run: Callable[..., Any] = subprocess.run) -> Any:
    """First ``seconds`` of ``path`` as 16 kHz mono float32 (ffmpeg)."""
    import numpy as np
    proc = run(["ffmpeg", "-nostdin", "-v", "error", "-t", f"{seconds:.1f}", "-i", path,
                "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
               capture_output=True, timeout=120, **no_window_kwargs(sys.platform))
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b"").decode("utf-8", "replace").strip()
                           or "ffmpeg failed")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def benchmark_whisper(key: str, media_path: str, *, seconds: float = 30.0,
                      use_gpu: bool = True, cancel: threading.Event | None = None,
                      model_cls: Any = None, read_audio: Callable[..., Any] = read_audio_16k,
                      clock: Callable[[], float] = time.perf_counter
                      ) -> BenchmarkResult | None:
    """Time one Whisper model on local audio. None when cancelled.

    Loads the model, transcribes up to ``seconds`` of the media and frees the
    model (and the GPU memory) before returning.
    """
    audio = read_audio(media_path, seconds)
    audio_s = len(audio) / 16000.0
    if audio_s <= 0:
        raise ValueError("no audio in the media")
    if model_cls is None:
        from faster_whisper import WhisperModel as model_cls
    device, compute = ("cuda", "float16") if use_gpu else ("cpu", "int8")
    t0 = clock()
    model = model_cls(key, device=device, compute_type=compute)
    try:
        load_s = clock() - t0
        t1 = clock()
        first: float | None = None
        segments, _info = model.transcribe(audio, beam_size=5, vad_filter=False)
        for _seg in segments:
            if first is None:
                first = clock() - t1
            if cancel is not None and cancel.is_set():
                return None
        return BenchmarkResult(key, device, audio_s, load_s, first, clock() - t1)
    finally:
        del model
        if use_gpu:
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
