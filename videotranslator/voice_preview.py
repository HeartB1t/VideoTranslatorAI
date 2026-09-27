"""Listen to a voice before choosing it (the speaker icon next to a voice).

- ``PREVIEW_SENTENCES``: one short sentence per target language, spoken by an
  Edge-TTS voice to let the user hear it in the language of the dub.
- ``fetch_sample`` downloads the free sample an ElevenLabs voice ships with
  (``preview_url``): no characters of the plan are used.
- ``synthesize_edge`` speaks a sentence with an Edge-TTS voice (free, online).
- ``VoicePreview`` runs one preview at a time on its own worker thread: it
  loads the audio, plays it, and reports ``loading`` / ``playing`` / ``idle``
  / ``error`` through a callback. A new request replaces the running one; the
  same key while loading or playing stops it (toggle).
- Playback uses a video-less libmpv instance, like the live voice, and falls
  back to ``ffplay`` (shipped with ffmpeg) when libmpv is missing. libmpv is
  created on the worker, never on the Tk thread.
"""

from __future__ import annotations

import asyncio
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .subprocess_utils import no_window_kwargs

MAX_SAMPLE_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_S = 15.0
EDGE_TIMEOUT_S = 20.0
_START_TIMEOUT_S = 5.0
_POLL_S = 0.05

# Keys are the target language codes of LANGUAGES in video_translator_gui.py.
PREVIEW_SENTENCES: dict[str, str] = {
    "ar": "مرحبًا، هذا هو الصوت الذي سأستخدمه لدبلجة الفيديو.",
    "zh-CN": "你好，这是我将用来为视频配音的声音。",
    "cs": "Dobrý den, tímto hlasem nadabuji vaše video.",
    "da": "Hej, det er denne stemme, jeg vil bruge til at eftersynkronisere videoen.",
    "de": "Hallo, mit dieser Stimme werde ich das Video synchronisieren.",
    "el": "Γεια σας, αυτή είναι η φωνή που θα χρησιμοποιήσω για τη μεταγλώττιση του βίντεο.",
    "en": "Hello, this is the voice I will use to dub the video.",
    "es": "Hola, esta es la voz que usaré para doblar el vídeo.",
    "fi": "Hei, tällä äänellä dubbaan videon.",
    "fr": "Bonjour, voici la voix que j'utiliserai pour doubler la vidéo.",
    "hi": "नमस्ते, इसी आवाज़ में मैं वीडियो की डबिंग करूँगा।",
    "hu": "Szia, ezzel a hanggal fogom szinkronizálni a videót.",
    "id": "Halo, ini suara yang akan saya gunakan untuk menyulih suara video.",
    "it": "Ciao, questa è la voce che userò per doppiare il video.",
    "ja": "こんにちは、この声で動画を吹き替えます。",
    "ko": "안녕하세요, 이 목소리로 동영상을 더빙하겠습니다.",
    "nl": "Hallo, dit is de stem waarmee ik de video ga nasynchroniseren.",
    "no": "Hei, dette er stemmen jeg skal bruke til å dubbe videoen.",
    "pl": "Cześć, tym głosem zrobię dubbing filmu.",
    "pt": "Olá, esta é a voz que vou usar para dobrar o vídeo.",
    "ro": "Bună, aceasta este vocea pe care o voi folosi pentru dublarea videoclipului.",
    "ru": "Здравствуйте, этим голосом я озвучу видео.",
    "sv": "Hej, det här är rösten jag kommer att använda för att dubba videon.",
    "tr": "Merhaba, videoyu bu sesle seslendireceğim.",
    "uk": "Вітаю, цим голосом я озвучу відео.",
    "vi": "Xin chào, đây là giọng tôi sẽ dùng để lồng tiếng cho video.",
}


def preview_sentence(lang: str) -> str:
    """The sample sentence for a target language (English if unknown)."""
    if lang in PREVIEW_SENTENCES:
        return PREVIEW_SENTENCES[lang]
    base = (lang or "").split("-")[0].split("_")[0].lower()
    for code, sentence in PREVIEW_SENTENCES.items():
        if code.split("-")[0].lower() == base:
            return sentence
    return PREVIEW_SENTENCES["en"]


class PreviewError(RuntimeError):
    """A preview that could not be played. ``kind``: network, no_sample,
    no_player, failed."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind


# -- audio loaders (worker thread) ---------------------------------------------

def fetch_sample(url: str, *, opener: Callable[..., Any] = urllib.request.urlopen,
                 timeout: float = FETCH_TIMEOUT_S,
                 max_bytes: int = MAX_SAMPLE_BYTES) -> bytes:
    """Download a voice sample. Only https URLs, at most ``max_bytes``."""
    if not url or urllib.parse.urlsplit(url).scheme != "https":
        raise PreviewError("no_sample", "no https sample URL")
    req = urllib.request.Request(url, headers={"Accept": "audio/*"})
    try:
        with opener(req, timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)
    except (urllib.error.URLError, OSError) as exc:
        raise PreviewError("network", type(exc).__name__) from None
    if not data:
        raise PreviewError("network", "empty sample")
    if len(data) > max_bytes:
        raise PreviewError("failed", "sample too large")
    return data


def synthesize_edge(text: str, voice: str, rate_pct: int = 0, *,
                    communicate: Callable[..., Any] | None = None,
                    timeout: float = EDGE_TIMEOUT_S) -> bytes:
    """Speak ``text`` with an Edge-TTS voice and return the mp3 bytes."""
    if communicate is None:
        try:
            import edge_tts
        except ImportError:
            raise PreviewError("failed", "edge-tts is not installed") from None
        communicate = edge_tts.Communicate

    async def run() -> bytes:
        comm = communicate(text, voice, rate=f"{int(rate_pct):+d}%")
        buf = bytearray()
        async for chunk in comm.stream():
            if chunk.get("type") == "audio":
                buf += chunk["data"]
        return bytes(buf)

    try:
        data = asyncio.run(asyncio.wait_for(run(), timeout))
    except PreviewError:
        raise
    except Exception as exc:                   # noqa: BLE001 - network, service, timeout
        raise PreviewError("network", type(exc).__name__) from None
    if not data:
        raise PreviewError("network", "no audio")
    return data


# -- players (worker thread) ---------------------------------------------------

class MpvPreviewPlayer:
    """A video-less libmpv instance, the same options as the live voice."""

    def __init__(self, mpv_module, *, sys_platform: str) -> None:
        from .player_engine import build_mpv_options
        options = build_mpv_options("voice", sys_platform=sys_platform, wid=None,
                                    vo_profile="none")
        self._player = mpv_module.MPV(**options)

    def play(self, path: str) -> None:
        self._player.command("loadfile", str(path), "replace")
        self._player.command("set", "pause", "no")

    def is_idle(self) -> bool:
        return bool(self._player.idle_active)

    def stop(self) -> None:
        self._player.command("stop")

    def close(self) -> None:
        self._player.terminate()


class FfplayPreviewPlayer:
    """``ffplay`` in a hidden child process (fallback when libmpv is missing)."""

    def __init__(self, exe: str, *, sys_platform: str,
                 popen: Callable[..., Any] = subprocess.Popen) -> None:
        self._exe = exe
        self._platform = sys_platform
        self._popen = popen
        self._proc = None

    def play(self, path: str) -> None:
        self.stop()
        self._proc = self._popen(
            [self._exe, "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, **no_window_kwargs(self._platform))

    def is_idle(self) -> bool:
        return self._proc is None or self._proc.poll() is not None

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(2.0)
        except Exception:                      # noqa: BLE001
            try:
                proc.kill()
            except Exception:                  # noqa: BLE001
                pass

    def close(self) -> None:
        self.stop()


def make_player(*, sys_platform: str = sys.platform,
                load_mpv: Callable[[], Any] | None = None,
                which: Callable[[str], str | None] = shutil.which):
    """libmpv first, then ffplay; raises PreviewError('no_player')."""
    platform_key = "win32" if sys_platform == "win32" else "linux"
    try:
        if load_mpv is None:
            from .libmpv_runtime import load_mpv as load_mpv
        return MpvPreviewPlayer(load_mpv(), sys_platform=platform_key)
    except Exception:                          # noqa: BLE001 - try the fallback
        pass
    exe = which("ffplay")
    if exe:
        return FfplayPreviewPlayer(exe, sys_platform=platform_key)
    raise PreviewError("no_player", "neither libmpv nor ffplay is available")


# -- controller ----------------------------------------------------------------

class VoicePreview:
    """One preview at a time on a worker thread.

    ``on_state(key, state, error_kind)`` is called from the worker with state
    ``loading``, ``playing``, ``idle`` or ``error`` (``error_kind`` set only
    for errors); the GUI hands it to the Tk thread.
    """

    def __init__(self, on_state: Callable[[str, str, str | None], None], *,
                 player_factory: Callable[[], Any] = make_player,
                 temp_dir: str | os.PathLike | None = None,
                 thread_factory: Callable[..., threading.Thread] = threading.Thread,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._on_state = on_state
        self._player_factory = player_factory
        self._temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self._thread_factory = thread_factory
        self._clock = clock
        self._requests: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._active: tuple[str, str] | None = None   # (key, state) loading/playing
        self._thread: threading.Thread | None = None
        self._player = None
        self._closed = False
        self._seq = 0

    # -- Tk-side API -------------------------------------------------------------

    def active_key(self) -> str | None:
        with self._lock:
            return self._active[0] if self._active else None

    def toggle(self, key: str, loader: Callable[[], bytes], *, suffix: str = ".mp3") -> None:
        """Play ``key``; if it is already loading or playing, stop it."""
        with self._lock:
            if self._closed:
                return
            if self._active is not None and self._active[0] == key:
                self._requests.put(("stop",))
                return
        self.play(key, loader, suffix=suffix)

    def play(self, key: str, loader: Callable[[], bytes], *, suffix: str = ".mp3") -> None:
        with self._lock:
            if self._closed:
                return
            self._requests.put(("play", key, loader, suffix))
            if self._thread is None:
                self._thread = self._thread_factory(target=self._run, name="voice-preview",
                                                    daemon=True)
                self._thread.start()

    def stop(self) -> None:
        self._requests.put(("stop",))

    def close(self, timeout_s: float = 3.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            thread = self._thread
        self._requests.put(("close",))
        if thread is not None:
            thread.join(timeout_s)

    # -- worker ------------------------------------------------------------------

    def _emit(self, key: str, state: str, kind: str | None = None) -> None:
        with self._lock:
            self._active = (key, state) if state in ("loading", "playing") else None
        try:
            self._on_state(key, state, kind)
        except Exception:                      # noqa: BLE001 - never kill the worker
            pass

    def _latest(self, first):
        """Collapse queued requests: the last one wins, close always wins."""
        request = first
        while True:
            try:
                nxt = self._requests.get_nowait()
            except queue.Empty:
                return request
            if request[0] == "close":
                continue
            request = nxt

    def _run(self) -> None:
        pending = None
        try:
            while True:
                request = self._latest(pending or self._requests.get())
                pending = None
                if request[0] == "close":
                    return
                if request[0] == "stop":
                    continue
                pending = self._one(*request[1:])
        finally:
            self._shutdown_player()

    def _one(self, key: str, loader: Callable[[], bytes], suffix: str):
        """Load and play one preview; return a request that interrupted it."""
        self._emit(key, "loading")
        try:
            data = loader()
        except PreviewError as exc:
            data, error = None, exc.kind
        except Exception:                      # noqa: BLE001
            data, error = None, "failed"
        interrupt = self._poll_request()
        if interrupt is not None:
            self._emit(key, "idle")
            return interrupt
        if data is None:
            self._emit(key, "error", error)
            return None
        path = self._write(data, suffix)
        if path is None:
            self._emit(key, "error", "failed")
            return None
        try:
            return self._play_file(key, path)
        finally:
            self._remove(path)

    def _play_file(self, key: str, path: Path):
        try:
            if self._player is None:
                self._player = self._player_factory()
            self._player.play(str(path))
        except PreviewError as exc:
            self._emit(key, "error", exc.kind)
            return None
        except Exception:                      # noqa: BLE001
            self._emit(key, "error", "failed")
            return None
        started = False
        deadline = self._clock() + _START_TIMEOUT_S
        while True:
            interrupt = self._poll_request(_POLL_S)
            if interrupt is not None:
                self._stop_player()
                self._emit(key, "idle")
                return None if interrupt[0] == "stop" else interrupt
            try:
                idle = self._player.is_idle()
            except Exception:                  # noqa: BLE001
                self._emit(key, "error", "failed")
                return None
            if not started:
                if not idle:
                    started = True
                    self._emit(key, "playing")
                elif self._clock() > deadline:
                    self._stop_player()
                    self._emit(key, "error", "failed")
                    return None
            elif idle:
                self._emit(key, "idle")
                return None

    def _poll_request(self, timeout: float = 0.0):
        try:
            if timeout > 0:
                return self._requests.get(timeout=timeout)
            return self._requests.get_nowait()
        except queue.Empty:
            return None

    def _write(self, data: bytes, suffix: str) -> Path | None:
        self._seq += 1
        path = self._temp_dir / f"vtai_voice_preview_{os.getpid()}_{self._seq}{suffix}"
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError:
            return None
        return path

    def _remove(self, path: Path) -> None:
        # On Windows the player may hold the file for a moment after stop.
        for _ in range(10):
            try:
                path.unlink()
                return
            except FileNotFoundError:
                return
            except OSError:
                time.sleep(0.05)

    def _stop_player(self) -> None:
        try:
            if self._player is not None:
                self._player.stop()
        except Exception:                      # noqa: BLE001
            pass

    def _shutdown_player(self) -> None:
        player, self._player = self._player, None
        if player is None:
            return
        try:
            player.stop()
        except Exception:                      # noqa: BLE001
            pass
        try:
            player.close()
        except Exception:                      # noqa: BLE001
            pass
