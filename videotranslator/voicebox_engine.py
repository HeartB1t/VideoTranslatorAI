"""Voicebox (jamiepine/voicebox, MIT) as a voice-cloning TTS engine.

Voicebox runs as a separate local program (its own Python environment or
Docker; its numpy/torch pins conflict with ours, so it is never imported
here). This module only talks to its REST API on 127.0.0.1, with urllib:

- ``GET /health``: reachability and GPU state;
- ``POST /profiles`` + ``POST /profiles/{id}/samples`` (multipart ``file`` +
  ``reference_text``): a temporary cloned-voice profile from a clean sample
  of the video's voice (one per speaker with diarization);
- ``POST /generate/stream``: one WAV per sentence;
- ``DELETE /profiles/{id}``: the temporary profiles are removed at the end.

Paths and payloads follow Voicebox's backend source (no route prefix,
v0.5.x); the API is pre-1.0, so every call is checked and any failure makes
the whole video fall back to Edge-TTS (one voice per video, never a mix).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

from .platforms import loopback_ipv4
from .tts_reference import build_vad_reference_tiered, extract_speaker_reference
from .tts_text_sanitizer import sanitize_for_tts

DEFAULT_URL = "http://127.0.0.1:17493"
# Languages Voicebox accepts for profiles and generation (its request schema).
LANGUAGES = frozenset(("zh", "en", "ja", "ko", "de", "fr", "ru", "pt", "es", "it", "he",
                       "ar", "da", "el", "fi", "hi", "ms", "nl", "no", "pl", "sv", "sw",
                       "tr"))
# Engines usable for cloning; Chatterbox Multilingual (MIT) covers the most
# European languages, Qwen3-TTS is Voicebox's default.
ENGINES = ("chatterbox", "qwen", "chatterbox_turbo", "tada", "luxtts", "kokoro")
DEFAULT_ENGINE = "chatterbox"


class VoiceboxError(RuntimeError):
    """``kind``: unreachable, timeout, invalid (4xx), server (5xx)."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind


def _lang(code: str) -> str:
    return (code or "").split("-")[0].lower()


def supports_language(lang: str) -> bool:
    return _lang(lang) in LANGUAGES


def is_local_url(url: str) -> bool:
    """Voicebox has no authentication: only a loopback address is accepted."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1")


def _multipart(fields: dict[str, str], file_field: str, file_path: str,
               boundary: str) -> bytes:
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\""
                     f"\r\n\r\n{value}\r\n".encode("utf-8"))
    data = Path(file_path).read_bytes()
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
                 f"filename=\"{Path(file_path).name}\"\r\nContent-Type: audio/wav\r\n\r\n"
                 .encode("utf-8") + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts)


class VoiceboxClient:
    def __init__(self, base_url: str = DEFAULT_URL, *,
                 opener: Callable[..., Any] = urllib.request.urlopen,
                 timeout: float = 10.0) -> None:
        self.base_url = loopback_ipv4(base_url or DEFAULT_URL)
        if not is_local_url(self.base_url):
            raise VoiceboxError("invalid", "Voicebox must run on this PC (127.0.0.1)")
        self._open = opener
        self._timeout = timeout

    def _request(self, method: str, path: str, *, body: bytes | None = None,
                 content_type: str | None = None, timeout: float | None = None) -> bytes:
        headers = {"Accept": "*/*"}
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(self.base_url + path, data=body, method=method,
                                     headers=headers)
        try:
            with self._open(req, timeout=timeout or self._timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = str(json.loads(exc.read().decode("utf-8", "replace"))
                             .get("detail", ""))[:200]
            except Exception:
                pass
            kind = "server" if exc.code >= 500 else "invalid"
            raise VoiceboxError(kind, f"HTTP {exc.code} {detail}".strip()) from None
        except TimeoutError:
            raise VoiceboxError("timeout", "timed out") from None
        except (urllib.error.URLError, OSError) as exc:
            reason = str(getattr(exc, "reason", exc))
            kind = "timeout" if "timed out" in reason else "unreachable"
            raise VoiceboxError(kind, reason) from None

    def _json(self, method: str, path: str, payload: Any = None, **kw) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        raw = self._request(method, path, body=body,
                            content_type="application/json" if body else None, **kw)
        try:
            return json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            raise VoiceboxError("server", "invalid JSON") from None

    def health(self) -> dict:
        return self._json("GET", "/health", timeout=5.0) or {}

    def profiles(self) -> list[dict]:
        return list(self._json("GET", "/profiles") or [])

    def create_profile(self, name: str, language: str, *, engine: str) -> str:
        data = self._json("POST", "/profiles", {
            "name": name[:100], "language": _lang(language), "voice_type": "cloned",
            "default_engine": engine,
            "description": "Temporary voice created by VideoTranslatorAI"})
        if not isinstance(data, dict) or not data.get("id"):
            raise VoiceboxError("server", "no profile id")
        return str(data["id"])

    def add_sample(self, profile_id: str, wav_path: str, reference_text: str) -> None:
        boundary = "vtai" + uuid.uuid4().hex
        body = _multipart({"reference_text": reference_text}, "file", wav_path, boundary)
        self._request("POST", f"/profiles/{urllib.parse.quote(profile_id)}/samples",
                      body=body, content_type=f"multipart/form-data; boundary={boundary}",
                      timeout=120.0)

    def delete_profile(self, profile_id: str) -> None:
        self._request("DELETE", f"/profiles/{urllib.parse.quote(profile_id)}")

    def generate(self, profile_id: str, text: str, language: str, *, engine: str,
                 timeout: float = 300.0) -> bytes:
        audio = self._request("POST", "/generate/stream", body=json.dumps({
            "profile_id": profile_id, "text": text, "language": _lang(language),
            "engine": engine, "normalize": True}).encode("utf-8"),
            content_type="application/json", timeout=timeout)
        if not audio.startswith(b"RIFF"):
            raise VoiceboxError("server", "the answer is not a WAV file")
        return audio


def describe_health(health: dict) -> str:
    """Short device summary for the UI: the GPU type, or CPU."""
    if health.get("gpu_available"):
        return str(health.get("gpu_type") or "GPU")
    return "CPU"


def _transcribe_reference(path: str, language: str) -> str:
    """Text spoken in the reference clip (Voicebox needs it for cloning)."""
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    try:
        segments, _info = model.transcribe(path, language=None, beam_size=1)
        return " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        del model


def generate_tts_voicebox(
    segments: list[dict],
    reference_audio: str,
    lang_target: str,
    tmp_dir: str,
    diar_segments: list[dict] | None = None,
    *,
    base_url: str = DEFAULT_URL,
    engine: str = DEFAULT_ENGINE,
    client: VoiceboxClient | None = None,
    build_reference: Callable[..., str | None] = build_vad_reference_tiered,
    speaker_reference: Callable[..., str | None] = extract_speaker_reference,
    transcribe: Callable[[str, str], str] = _transcribe_reference,
    log: Callable[..., None] = print,
) -> list[str] | None:
    """Voice-cloned TTS through Voicebox. None means: use Edge-TTS instead.

    Returns one WAV path per segment (empty sentences have no file, as with
    XTTS). Any failure returns None so the whole video uses one voice engine.
    """
    if not supports_language(lang_target):
        log(f"[!] Voicebox does not support '{lang_target}', falling back to Edge-TTS.",
            flush=True)
        return None
    engine = engine if engine in ENGINES else DEFAULT_ENGINE
    try:
        client = client or VoiceboxClient(base_url)
        health = client.health()
    except VoiceboxError as exc:
        log(f"[!] Voicebox not available at {base_url} ({exc}); falling back to Edge-TTS.",
            flush=True)
        return None
    log(f"[5/6] Generating TTS with Voicebox ({engine}, voice cloning, "
        f"device={describe_health(health)})...", flush=True)

    created: list[str] = []
    try:
        references: dict[str | None, str] = {}
        ref_clip = os.path.join(tmp_dir, "voicebox_ref.wav")
        if not build_reference(reference_audio, ref_clip):
            log("     ! Voicebox: no clean voice sample found in the video.", flush=True)
            return None
        references[None] = ref_clip
        for spk in sorted({d["speaker"] for d in diar_segments or [] if d.get("speaker")}):
            ref = speaker_reference(reference_audio, diar_segments, spk, tmp_dir)
            if ref:
                refined = os.path.join(tmp_dir, f"{Path(ref).stem}_voicebox.wav")
                references[spk] = refined if build_reference(ref, refined) else ref

        stamp = time.strftime("%Y%m%d-%H%M%S")
        profiles: dict[str | None, str] = {}
        for spk, ref in references.items():
            text = transcribe(ref, lang_target)
            if not text:
                log(f"     ! Voicebox: no speech recognised in the sample of {spk or 'the video'}.",
                    flush=True)
                if spk is None:
                    return None
                continue
            profile_id = client.create_profile(
                f"VideoTranslatorAI {stamp} {spk or 'voice'}", lang_target, engine=engine)
            created.append(profile_id)
            client.add_sample(profile_id, ref, text)
            profiles[spk] = profile_id

        files: list[str] = []
        total = len(segments)
        for index, seg in enumerate(segments):
            out = os.path.join(tmp_dir, f"seg_{index:04d}.wav")
            files.append(out)
            text = sanitize_for_tts((seg.get("text_tgt") or seg.get("text") or "").strip())
            if not text:
                continue
            profile_id = profiles.get(seg.get("speaker"), profiles[None])
            Path(out).write_bytes(client.generate(profile_id, text, lang_target,
                                                  engine=engine))
            if (index + 1) % 10 == 0 or index + 1 == total:
                log(f"     {index + 1}/{total} sentences", flush=True)
        log("     → Voicebox TTS done", flush=True)
        return files
    except VoiceboxError as exc:
        log(f"[!] Voicebox failed ({exc}); falling back to Edge-TTS.", flush=True)
        return None
    except OSError as exc:
        log(f"[!] Voicebox output could not be written ({exc}); falling back to Edge-TTS.",
            flush=True)
        return None
    finally:
        for profile_id in created:
            try:
                client.delete_profile(profile_id)
            except VoiceboxError:
                pass
