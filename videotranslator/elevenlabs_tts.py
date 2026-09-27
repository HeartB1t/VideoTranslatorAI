"""ElevenLabs text-to-speech for live dubbing (optional, online, paid).

- ``ElevenLabsClient``: the few REST calls the app needs (account quota, voice
  and model catalogue, synthesis), with the standard library only (urllib),
  so nothing new to install on Windows or Linux. The API key is sent only in
  the ``xi-api-key`` header and never appears in errors or logs.
- ``ElevenLabsClipSynth``: the live worker with the same interface as
  ``EdgeClipSynth`` (start / submit / stop / results), so the session and the
  scheduler do not change: one mp3 clip per sentence, written to a ``.part``
  file and renamed, measured, and reported with its deadline respected.
- ``FallbackClipSynth``: when ElevenLabs refuses the account (bad key, quota
  used up) it switches the rest of the session to another synth (Edge-TTS),
  if the user allowed it, and re-sends the sentence that failed.

Language support depends on the model: the catalogue lists each model's
languages, and ``language_code`` is sent only to the models that accept it
(Flash and Turbo v2.5); other models reject it.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .live_tts import Clip, LiveTtsUnavailable, measure_silence
from .tts_text_sanitizer import sanitize_for_tts

API_BASE = "https://api.elevenlabs.io"
KEYRING_USERNAME = "elevenlabs_api_key"
CONFIG_KEY = "elevenlabs_api_key"          # JSON fallback when no keyring exists
OUTPUT_FORMAT = "mp3_44100_64"
_BYTES_PER_SECOND = 64000 / 8               # 64 kbit/s CBR mp3
SPEED_MIN, SPEED_MAX = 0.7, 1.2
# Low-latency first: live dubbing needs the next sentence within seconds.
PREFERRED_LIVE_MODELS = ("eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_multilingual_v2")
_LANGUAGE_CODE_MODELS = ("eleven_flash_v2_5", "eleven_turbo_v2_5")


class ElevenLabsError(RuntimeError):
    """A failed call. ``kind``: auth, quota, paid_voice (a voice the plan may not
    use through the API), rate_limited, invalid, timeout, unavailable."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind


def classify_http(status: int, body: bytes) -> str:
    detail: Any = None
    try:
        detail = json.loads(body.decode("utf-8", "replace")).get("detail")
    except Exception:
        pass
    code = detail.get("status") if isinstance(detail, dict) else None
    reason = detail.get("code") if isinstance(detail, dict) else None
    if reason == "paid_plan_required":
        return "paid_voice"
    if code in ("quota_exceeded", "insufficient_credits") or status == 402:
        return "quota"
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limited"
    if status in (400, 404, 422):
        return "invalid"
    return "unavailable"


@dataclass(frozen=True)
class Voice:
    voice_id: str
    name: str
    accent: str = ""
    gender: str = ""
    languages: tuple[str, ...] = ()        # verified languages, when listed
    preview_url: str = ""                  # free sample of the voice (usually English)
    previews: tuple[tuple[str, str], ...] = ()   # (language, sample URL) per language
    paid_only: bool = False                # a library voice: free plans cannot use it via API

    def sample_url(self, lang: str) -> str:
        """The free sample in ``lang`` when the voice has one, else the default."""
        wanted = _lang(lang)
        for code, url in self.previews:
            if code == wanted and url:
                return url
        return self.preview_url

    def label(self) -> str:
        extra = [part for part in (self.accent, self.gender) if part]
        return f"{self.name} ({', '.join(extra)})" if extra else self.name


@dataclass(frozen=True)
class Model:
    model_id: str
    name: str
    languages: tuple[str, ...]
    can_tts: bool

    def supports(self, lang: str) -> bool:
        return _lang(lang) in self.languages


@dataclass(frozen=True)
class Account:
    used: int
    limit: int
    tier: str


def _lang(code: str) -> str:
    return (code or "").split("-")[0].split("_")[0].lower()


def parse_voices(data: dict) -> list[Voice]:
    voices = []
    for item in data.get("voices") or []:
        labels = item.get("labels") or {}
        verified = [v for v in item.get("verified_languages") or [] if isinstance(v, dict)]
        langs = tuple(sorted({_lang(v.get("language", "")) for v in verified
                              if v.get("language")}))
        previews: dict[str, str] = {}
        for v in verified:
            code, url = _lang(v.get("language", "")), v.get("preview_url") or ""
            if code and url and code not in previews:
                previews[code] = str(url)
        # Free plans may use the default (premade) voices and their own ones;
        # voices added from the library need a paid plan through the API.
        paid_only = item.get("category") not in (None, "premade") and not item.get("is_owner")
        if item.get("voice_id"):
            voices.append(Voice(item["voice_id"], item.get("name") or item["voice_id"],
                                labels.get("accent", "") or "", labels.get("gender", "") or "",
                                langs, str(item.get("preview_url") or ""),
                                tuple(sorted(previews.items())), paid_only))
    return sorted(voices, key=lambda v: v.name.lower())


def parse_models(data: list) -> list[Model]:
    models = []
    for item in data or []:
        if not item.get("model_id"):
            continue
        langs = tuple(sorted({_lang(lang.get("language_id", ""))
                              for lang in item.get("languages") or []}))
        models.append(Model(item["model_id"], item.get("name") or item["model_id"], langs,
                            bool(item.get("can_do_text_to_speech", True))))
    return models


def pick_live_model(models: list[Model], lang: str) -> Model | None:
    """The fastest TTS model that speaks ``lang`` (None if none does)."""
    usable = [m for m in models if m.can_tts and m.supports(lang)]
    for model_id in PREFERRED_LIVE_MODELS:
        for model in usable:
            if model.model_id == model_id:
                return model
    return usable[0] if usable else None


def rate_to_speed(rate_pct: int) -> float:
    """The session's Edge-style rate (+N %) as an ElevenLabs speed factor."""
    return round(min(SPEED_MAX, max(SPEED_MIN, 1.0 + rate_pct / 100.0)), 2)


class ElevenLabsClient:
    def __init__(self, api_key: str, *, opener: Callable[..., Any] = urllib.request.urlopen,
                 base: str = API_BASE, timeout: float = 10.0) -> None:
        self._key = (api_key or "").strip()
        self._open = opener
        self._base = base.rstrip("/")
        self._timeout = timeout

    def _request(self, method: str, path: str, *, body: dict | None = None,
                 query: dict | None = None, accept: str = "application/json",
                 timeout: float | None = None) -> bytes:
        if not self._key:
            raise ElevenLabsError("auth", "no API key")
        url = self._base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "xi-api-key": self._key, "Accept": accept,
            **({"Content-Type": "application/json"} if data is not None else {})})
        try:
            with self._open(req, timeout=timeout or self._timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            try:
                payload = exc.read()
            except Exception:
                payload = b""
            kind = classify_http(exc.code, payload)
            raise ElevenLabsError(kind, f"HTTP {exc.code}") from None
        except TimeoutError:
            raise ElevenLabsError("timeout", "timed out") from None
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            kind = "timeout" if "timed out" in str(reason) else "unavailable"
            raise ElevenLabsError(kind, type(exc).__name__) from None

    def _json(self, path: str) -> Any:
        try:
            return json.loads(self._request("GET", path).decode("utf-8"))
        except ValueError:
            raise ElevenLabsError("unavailable", "invalid JSON") from None

    def account(self) -> Account:
        data = self._json("/v1/user/subscription")
        return Account(int(data.get("character_count") or 0),
                       int(data.get("character_limit") or 0), str(data.get("tier") or ""))

    def voices(self) -> list[Voice]:
        return parse_voices(self._json("/v1/voices"))

    def models(self) -> list[Model]:
        return parse_models(self._json("/v1/models"))

    def synthesize(self, text: str, voice_id: str, model_id: str, *,
                   language: str | None = None, speed: float = 1.0,
                   timeout: float | None = None) -> bytes:
        body: dict[str, Any] = {"text": text, "model_id": model_id,
                                "voice_settings": {"speed": speed}}
        if language and model_id in _LANGUAGE_CODE_MODELS:
            body["language_code"] = _lang(language)
        audio = self._request("POST", f"/v1/text-to-speech/{urllib.parse.quote(voice_id)}",
                              body=body, query={"output_format": OUTPUT_FORMAT},
                              accept="audio/mpeg", timeout=timeout)
        if not audio:
            raise ElevenLabsError("unavailable", "empty audio")
        return audio


class ElevenLabsClipSynth:
    """Live TTS worker on ElevenLabs, interchangeable with ``EdgeClipSynth``.

    ``results`` receives ``(seg_id, gen, Clip | None, reason | None)``. A
    failure reason is ``elevenlabs_<kind>``; ``fatal`` is set to ``auth`` or
    ``quota`` when the account cannot be used for the rest of the session.
    """

    name = "ElevenLabs"

    def __init__(self, api_key: str, voice_id: str, model_id: str, out_dir, *, breaker,
                 language: str | None = None, client: ElevenLabsClient | None = None,
                 av_module=None, max_concurrent: int = 2, max_in_flight: int = 8,
                 clock: Callable[[], float] | None = None,
                 thread_factory=threading.Thread, sanitize=None) -> None:
        self._client = client or ElevenLabsClient(api_key)
        self._has_key = bool((api_key or "").strip()) or client is not None
        self._voice_id = voice_id
        self._model_id = model_id
        self._language = language
        self._out_dir = Path(out_dir)
        self._breaker = breaker
        self._av = av_module
        self._max_concurrent = max(1, max_concurrent)
        self._max_in_flight = max_in_flight
        self._clock = clock or time.monotonic
        self._thread_factory = thread_factory
        self._sanitize = sanitize or sanitize_for_tts
        self.results: queue.Queue = queue.Queue()
        self._requests: queue.Queue = queue.Queue()
        self._threads: list[Any] = []
        self._lock = threading.Lock()
        self._in_flight = 0
        self._stopping = threading.Event()
        self._started = False
        self.fatal: str | None = None

    def start(self) -> None:
        if not self._has_key or not self._voice_id or not self._model_id:
            raise LiveTtsUnavailable("ElevenLabs is not configured (key, voice, model)")
        try:
            self._out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LiveTtsUnavailable(f"cannot create tts dir: {exc}") from exc
        for index in range(self._max_concurrent):
            thread = self._thread_factory(target=self._run, name=f"live-tts-el{index}",
                                          daemon=True)
            thread.start()
            self._threads.append(thread)
        self._started = True

    def submit(self, seg_id: int, gen: int, text: str, rate_pct: int,
               deadline_mono: float) -> bool:
        with self._lock:
            if (not self._started or self._stopping.is_set() or self.fatal
                    or not self._breaker.allow() or self._in_flight >= self._max_in_flight
                    or deadline_mono - self._clock() <= 0):
                return False
            self._in_flight += 1
        self._requests.put((seg_id, gen, text, rate_pct, deadline_mono))
        return True

    def stop(self, timeout_s: float) -> bool:
        self._stopping.set()
        for _ in self._threads:
            self._requests.put(None)
        end = time.monotonic() + max(0.0, timeout_s)
        for thread in self._threads:
            thread.join(max(0.0, end - time.monotonic()))
        alive = any(t.is_alive() for t in self._threads)
        if not alive:
            for part in self._out_dir.glob("clip_*.mp3.part"):
                try:
                    part.unlink()
                except OSError:
                    pass
        return not alive

    def _run(self) -> None:
        while not self._stopping.is_set():
            req = self._requests.get()
            if req is None:
                return
            try:
                self._one(*req)
            finally:
                with self._lock:
                    self._in_flight = max(0, self._in_flight - 1)

    def _one(self, seg_id: int, gen: int, text: str, rate_pct: int,
             deadline: float) -> None:
        clean = self._sanitize(text) if self._sanitize else (text or "").strip()
        if not clean:
            self.results.put((seg_id, gen, None, "empty"))
            return
        remaining = deadline - self._clock()
        if remaining < 0.3:
            self.results.put((seg_id, gen, None, "late"))
            return
        try:
            audio = self._client.synthesize(clean, self._voice_id, self._model_id,
                                            language=self._language,
                                            speed=rate_to_speed(rate_pct),
                                            timeout=max(0.5, min(remaining, 15.0)))
        except ElevenLabsError as exc:
            if exc.kind in ("auth", "quota", "paid_voice"):
                self.fatal = exc.kind
            self._breaker.record_failure(
                kind="quota" if exc.kind in ("auth", "quota", "paid_voice") else "tts")
            self.results.put((seg_id, gen, None, f"elevenlabs_{exc.kind}"))
            return
        except Exception as exc:                   # noqa: BLE001 - never kill the worker
            self._breaker.record_failure(kind="tts")
            self.results.put((seg_id, gen, None, f"elevenlabs_error: {type(exc).__name__}"))
            return
        if self._stopping.is_set():
            return
        clip = self._write_clip(seg_id, gen, audio, rate_pct)
        if clip is None:
            self.results.put((seg_id, gen, None, "elevenlabs_write"))
            return
        self._breaker.record_success()
        self.results.put((seg_id, gen, clip, None))

    def _write_clip(self, seg_id: int, gen: int, audio: bytes, rate_pct: int) -> Clip | None:
        part = self._out_dir / f"clip_{gen}_{seg_id}.mp3.part"
        final = self._out_dir / f"clip_{gen}_{seg_id}.mp3"
        try:
            part.write_bytes(audio)
            os.replace(part, final)
        except OSError:
            try:
                part.unlink()
            except OSError:
                pass
            return None
        duration = len(audio) / _BYTES_PER_SECOND
        bounds = (measure_silence(str(final), av_module=self._av)
                  if self._av is not None else None)
        start, end = bounds if bounds else (0.0, duration)
        return Clip(seg_id, gen, str(final), duration, f"+{rate_pct}%", start, end)


class _MergedResults:
    """``results`` of FallbackClipSynth: the session only calls get_nowait()."""

    def __init__(self, owner: "FallbackClipSynth") -> None:
        self._owner = owner

    def get_nowait(self):
        return self._owner._next_result()


class FallbackClipSynth:
    """ElevenLabs first; after a fatal account error, another synth for the rest.

    The request that hit the fatal error is re-sent to the fallback, so the
    sentence is still voiced when time allows. ``on_switch(reason)`` is called
    once, on the session thread, when the switch happens.
    """

    def __init__(self, primary: ElevenLabsClipSynth, make_fallback: Callable[[], Any], *,
                 on_switch: Callable[[str], None] = lambda _r: None) -> None:
        self._primary = primary
        self._make_fallback = make_fallback
        self._on_switch = on_switch
        self._fallback: Any = None
        self._pending: dict[tuple[int, int], tuple] = {}
        self.results = _MergedResults(self)

    @property
    def name(self) -> str:
        return getattr(self._fallback, "name", "edge-tts") if self._fallback else \
            self._primary.name

    def start(self) -> None:
        self._primary.start()

    def submit(self, seg_id: int, gen: int, text: str, rate_pct: int,
               deadline_mono: float) -> bool:
        if self._fallback is not None:
            return self._fallback.submit(seg_id, gen, text, rate_pct, deadline_mono)
        ok = self._primary.submit(seg_id, gen, text, rate_pct, deadline_mono)
        if ok:
            self._pending[(seg_id, gen)] = (text, rate_pct, deadline_mono)
        elif self._primary.fatal and self._switch(self._primary.fatal):
            return self._fallback.submit(seg_id, gen, text, rate_pct, deadline_mono)
        return ok

    def _switch(self, reason: str) -> bool:
        if self._fallback is not None:
            return True
        try:
            fallback = self._make_fallback()
            if fallback is None:
                return False
            fallback.start()
        except Exception:                          # noqa: BLE001 - keep ElevenLabs errors
            return False
        self._fallback = fallback
        self._on_switch(reason)
        return True

    def _next_result(self):
        try:
            result = self._primary.results.get_nowait()
        except queue.Empty:
            if self._fallback is None:
                raise
            return self._fallback.results.get_nowait()
        seg_id, gen, clip, reason = result
        request = self._pending.pop((seg_id, gen), None)
        if (clip is None and self._primary.fatal and request is not None
                and self._switch(self._primary.fatal)):
            text, rate_pct, deadline = request
            if self._fallback.submit(seg_id, gen, text, rate_pct, deadline):
                # Re-sent: its result will come from the fallback later.
                return self._next_result()
        return result

    def stop(self, timeout_s: float) -> bool:
        ok = self._primary.stop(timeout_s)
        if self._fallback is not None:
            ok = self._fallback.stop(timeout_s) and ok
        return ok
