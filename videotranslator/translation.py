"""Translation engine dispatcher for Ollama, MarianMT, DeepL and Google."""

from __future__ import annotations

import threading
import time

from videotranslator.quality_flags import (
    FLAG_TRANSLATION_FALLBACK,
    add_quality_flag,
    compute_segment_quality_flags,
)

# Google Translate (unofficial endpoint via deep-translator) throttles bursts
# with HTTP 429. Pace the requests and retry transient errors with backoff.
# When a few segments in a row still fail, Google is blocking this IP: wait
# a cooldown, send one probe request and abort the job if it fails too,
# rather than dubbing the rest of the video in the source language. Only one
# recovery per job: a second block aborts right away.
_GOOGLE_MIN_INTERVAL = 0.25     # seconds between requests (Google: 5 req/s)
_GOOGLE_MAX_ATTEMPTS = 3        # per segment, backoff 2 s then 4 s
_GOOGLE_BACKOFF_BASE = 2.0
_GOOGLE_MAX_CONSECUTIVE_FAILURES = 3
_GOOGLE_COOLDOWN = 30.0         # seconds before the probe request
_GOOGLE_REQUEST_TIMEOUT = 30.0  # seconds per request (deep-translator sets none)


class TranslationUnavailableError(RuntimeError):
    """The translation service failed for every non-empty segment."""


def _google_translate_with_timeout(translator, text: str):
    """Call translator.translate(text), raise TimeoutError after the timeout.

    deep-translator calls requests.get without a timeout, so a hung
    connection would block the job forever. Each request runs on its own
    daemon thread: on timeout that thread is abandoned (it ends when the
    connection finally answers or fails, or dies with the process), later
    requests never queue behind it and it never blocks the interpreter exit.
    A ThreadPoolExecutor worker would, because executor threads are joined
    at exit even after shutdown(wait=False).
    """
    outcome: dict = {}

    def request():
        try:
            outcome["text"] = translator.translate(text)
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(
        target=request, name="google-translate-request", daemon=True,
    )
    worker.start()
    worker.join(_GOOGLE_REQUEST_TIMEOUT)
    if worker.is_alive():
        raise TimeoutError(
            f"no answer from Google Translate within "
            f"{_GOOGLE_REQUEST_TIMEOUT:g} s"
        )
    if "error" in outcome:
        raise outcome["error"]
    return outcome["text"]


_NO_FLAGS = object()


def _snapshot_quality_flags(segments: list[dict]) -> list:
    """Copy each segment's quality flags, so an engine's additions can be undone."""
    snapshot = []
    for seg in segments:
        flags = seg.get("_quality_flags", _NO_FLAGS)
        snapshot.append(list(flags) if isinstance(flags, list) else flags)
    return snapshot


def _restore_quality_flags(segments: list[dict], snapshot: list) -> None:
    for seg, flags in zip(segments, snapshot):
        if flags is _NO_FLAGS:
            seg.pop("_quality_flags", None)
        else:
            seg["_quality_flags"] = flags


def _kept_source_after_failure(entry: dict) -> bool:
    """The engine failed on this entry and left its source text in place."""
    return (
        FLAG_TRANSLATION_FALLBACK in compute_segment_quality_flags(entry)
        and entry.get("text_tgt") == entry.get("text_src")
    )


def _marian_normalize_lang(code: str) -> str:
    """Normalize language codes to the short form Helsinki-NLP models expect."""
    if not code:
        return code
    c = code.lower()
    # Helsinki-NLP uses 'zh' not 'zh-cn'
    if c.startswith("zh"):
        return "zh"
    # Norwegian: 'no' -> 'nb' on HF (Bokmal)
    if c == "no":
        return "nb"
    return c.split("-")[0]


def _translate_with_marian(segments: list[dict], src: str, target: str) -> list[dict] | None:
    """Translate ``segments`` with MarianMT (offline).

    Returns the translated segments, or ``None`` when the source language is
    unknown (``"auto"``) or the model is unavailable, so the caller can fall
    through to (or fall back from) another engine.
    """
    if src == "auto":
        return None
    m_src = _marian_normalize_lang(src)
    m_tgt = _marian_normalize_lang(target)
    model_name = f"Helsinki-NLP/opus-mt-{m_src}-{m_tgt}"
    tokenizer = None
    model = None
    try:
        # lazy import to keep startup fast
        from transformers import MarianMTModel, MarianTokenizer
        import torch
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        print(f"     → MarianMT loaded ({model_name}, device={device})", flush=True)

        texts = [(seg.get("text") or "").strip() for seg in segments]
        results: list[str] = []
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Preserve empty strings to keep indices aligned
            non_empty_idx = [j for j, t in enumerate(batch) if t]
            batch_out = [""] * len(batch)
            if non_empty_idx:
                inputs = tokenizer(
                    [batch[j] for j in non_empty_idx],
                    return_tensors="pt", padding=True,
                    truncation=True, max_length=512,
                ).to(device)
                with torch.no_grad():
                    translated = model.generate(**inputs)
                decoded = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]
                for j, out in zip(non_empty_idx, decoded):
                    batch_out[j] = out
            results.extend(batch_out)
            print(f"     {min(i + batch_size, len(texts))}/{len(texts)}...", end="\r", flush=True)

        translated_segs = []
        for seg, tr in zip(segments, results):
            text = (seg.get("text") or "").strip()
            _entry: dict = {
                "start": seg["start"],
                "end":   seg["end"],
                "text_src": text,
                "text_tgt": tr or text,
            }
            if "speaker" in seg:
                _entry["speaker"] = seg["speaker"]
            # TASK 5C: forward whisper_suspicious flag through the MarianMT path
            # so the editor still highlights segments the sanity check tagged.
            _flags_in = compute_segment_quality_flags(seg)
            if _flags_in:
                _entry["_quality_flags"] = _flags_in
            translated_segs.append(_entry)
        print("     → Translation done (MarianMT)          ", flush=True)
        return translated_segs
    except Exception as e:
        print(f"     ! MarianMT model {model_name} not available "
              f"({e.__class__.__name__}).", flush=True)
        return None
    finally:
        # free VRAM
        try:
            del model
            del tokenizer
            import torch as _t
            if _t.cuda.is_available():
                _t.cuda.empty_cache()
        except Exception:
            pass


def _marian_fallback_or_raise(segments: list[dict], src: str, target: str,
                              message: str, *, try_marian: bool = True) -> list[dict]:
    """Last resort when an online engine is blocked: try offline MarianMT.

    Returns the MarianMT translation when it succeeds; otherwise raises
    :class:`TranslationUnavailableError` with ``message`` (the original reason).
    ``try_marian=False`` skips the attempt when MarianMT already failed or is
    ineligible (auto source), so an offline box does not eat the Hugging Face
    download timeout a second time (review S6a).
    """
    print(f"     ! {message}", flush=True)
    if try_marian:
        result = _translate_with_marian(segments, src, target)
        if result is not None:
            print("     → Fell back to MarianMT (offline) after the online engine "
                  "was blocked.", flush=True)
            return result
    raise TranslationUnavailableError(message)


def translate_segments(
    segments: list[dict], source: str, target: str,
    engine: str = "google", deepl_key: str = "",
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
    ollama_document_context: bool = True,
    difficulty_profile=None,
    ollama_use_cove: bool = True,
    ollama_translator=None,
) -> list[dict]:
    src = "auto" if source == "auto" else source
    print(f"[4/6] Translating {src.upper()}→{target.upper()} ({len(segments)} segments, engine={engine})...", flush=True)
    # MarianMT cannot run without an explicit source; once it has failed (or is
    # ineligible), the Google fallback below must not retry it, or an offline box
    # eats the Hugging Face download timeout a second time (review S6a).
    marian_failed = src == "auto"

    # ── Ollama LLM translation (v2.0) ──────────────────────────────────────
    # Structural lever against atempo artifacts: the LLM understands the
    # timing constraint and compresses the translation to match the source
    # duration, instead of letting MarianMT/Google produce literal output
    # that is +25% longer.
    if engine == "llm_ollama":
        # TASK 2U: the Profile can force CoVe off (EASY) but the explicit
        # caller flag (CLI --no-cove) takes priority. When the caller passes
        # False, we keep the override even on MEDIUM/HARD.
        _effective_use_cove = ollama_use_cove
        if difficulty_profile is not None and not difficulty_profile.use_cove:
            _effective_use_cove = False
        flags_before_ollama = _snapshot_quality_flags(segments)
        try:
            if ollama_translator is None:
                raise RuntimeError("ollama_translator callback is required")
            ollama_result = ollama_translator(
                segments, src, target,
                model=ollama_model, api_url=ollama_url,
                slot_aware=ollama_slot_aware, batch_size=1,
                thinking=ollama_thinking,
                use_document_context=ollama_document_context,
                difficulty_profile=difficulty_profile,
                use_cove=_effective_use_cove,
            )
        except Exception as e:
            print(f"     ! Ollama unavailable ({e}), falling back to Google Translate.", flush=True)
            engine = "google"
        else:
            # Ollama answered the health check but may still fail on every
            # segment (model stuck, timeouts): the result would dub the
            # source language, so switch engine as if it were unreachable.
            # Partial failures stay flagged in the Ollama result.
            non_empty = [
                entry for entry in ollama_result
                if (entry.get("text_src") or "").strip()
            ]
            if not non_empty or not all(
                _kept_source_after_failure(entry) for entry in non_empty
            ):
                return ollama_result
            print(
                f"     ! Ollama failed on all {len(non_empty)} segments, "
                f"falling back to Google Translate.",
                flush=True,
            )
            # Ollama flagged the input segment dicts it failed on and Google
            # copies the input flags: undo Ollama's additions (upstream ones
            # such as whisper_suspicious stay), or every segment Google
            # translates would show up as a fallback in the editor.
            _restore_quality_flags(segments, flags_before_ollama)
            engine = "google"

    # ── MarianMT local translation ──────────────────────────────────────────
    if engine == "marian":
        # Auto-detect is not supported: MarianMT needs an explicit source.
        if src == "auto":
            print("     ! MarianMT requires explicit source language (auto not supported), falling back to Google.", flush=True)
        else:
            result = _translate_with_marian(segments, src, target)
            if result is not None:
                return result
            marian_failed = True   # do not retry it in the Google fallback (S6a)
            print("     ! MarianMT unavailable, falling back to Google.", flush=True)
        # fall through to Google if MarianMT failed
        engine = "google"

    # ── DeepL: batch API with retry/backoff ─────────────────────────────────
    if engine == "deepl" and deepl_key.strip():
        key = deepl_key.strip()
        endpoint = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
        import requests
        texts = [(seg.get("text") or "").strip() for seg in segments]
        results: list[str] = [""] * len(texts)
        idx_nonempty = [i for i, t in enumerate(texts) if t]
        BATCH = 50
        MAX_RETRIES = 5
        headers = {"Authorization": f"DeepL-Auth-Key {key}"}
        deepl_target = target.upper()
        if deepl_target == "EN":
            deepl_target = "EN-US"
        deepl_source = None if src == "auto" else src.upper()
        failed_idx: set[int] = set()
        try:
            for i in range(0, len(idx_nonempty), BATCH):
                chunk_idx = idx_nonempty[i:i + BATCH]
                payload = [("target_lang", deepl_target)]
                if deepl_source:
                    payload.append(("source_lang", deepl_source))
                # `context` (DeepL v2) nudges the model toward concise spoken-register
                # output, reducing overrun vs. source duration for dubbing.
                payload.append((
                    "context",
                    "Keep the translation concise and natural for dubbing. "
                    "Prefer spoken register over formal register.",
                ))
                for j in chunk_idx:
                    payload.append(("text", texts[j]))
                batch_translated = False
                last_error = ""
                for attempt in range(MAX_RETRIES):
                    try:
                        r = requests.post(endpoint, headers=headers, data=payload, timeout=60)
                        if r.status_code == 429 or r.status_code >= 500:
                            last_error = f"HTTP {r.status_code}"
                            if attempt == MAX_RETRIES - 1:
                                break
                            wait = float(r.headers.get("Retry-After", 2 ** attempt))
                            print(f"     ! DeepL {r.status_code}, retry in {wait:.1f}s...", flush=True)
                            time.sleep(wait)
                            continue
                        if r.status_code == 403:
                            raise RuntimeError(f"DeepL 403 Forbidden - verifica la API key ({r.text[:200]})")
                        r.raise_for_status()
                        data = r.json()
                        for j, item in zip(chunk_idx, data.get("translations", [])):
                            results[j] = item.get("text", "") or texts[j]
                        batch_translated = True
                        break
                    except requests.RequestException as e:
                        last_error = str(e)
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(2 ** attempt)
                if not batch_translated:
                    print(f"     ! DeepL batch {i}-{i+len(chunk_idx)} failed: {last_error}", flush=True)
                    failed_idx.update(chunk_idx)
                print(f"     {min(i + BATCH, len(idx_nonempty))}/{len(idx_nonempty)}...", end="\r", flush=True)
            if idx_nonempty and len(failed_idx) == len(idx_nonempty):
                raise TranslationUnavailableError(
                    "DeepL could not translate any segment"
                )
            translated = []
            for k, (seg, tr) in enumerate(zip(segments, results)):
                text = (seg.get("text") or "").strip()
                entry = {
                    "start": seg["start"], "end": seg["end"],
                    "text_src": text, "text_tgt": tr or text,
                }
                if "speaker" in seg:
                    entry["speaker"] = seg["speaker"]
                # TASK 5C: propagate upstream quality flags (whisper_suspicious)
                # through the DeepL path. Segments of a failed batch keep the
                # source text and get the translation_fallback flag.
                _flags_in = compute_segment_quality_flags(seg)
                if _flags_in:
                    entry["_quality_flags"] = _flags_in
                if k in failed_idx:
                    add_quality_flag(entry, FLAG_TRANSLATION_FALLBACK)
                translated.append(entry)
            if failed_idx:
                print(
                    f"     ⚠ DeepL failed on {len(failed_idx)}/{len(idx_nonempty)} segments: "
                    f"they keep the source text and are flagged in the subtitle editor.",
                    flush=True,
                )
            print("     → Translation done (DeepL)          ", flush=True)
            return translated
        except Exception as e:
            print(f"     ! DeepL failed ({e}), falling back to Google Translate.", flush=True)
            engine = "google"

    # ── Google Translate fallback ──────────────────────────────────────────
    from deep_translator import GoogleTranslator
    from deep_translator.exceptions import RequestError, TooManyRequests
    import requests
    if engine == "deepl":
        print("     ! DeepL key missing, falling back to Google Translate.", flush=True)
    # A request timeout is handled like throttling: retried with backoff and
    # counted by the breaker.
    transient_errors = (
        TooManyRequests, RequestError, requests.RequestException, TimeoutError,
    )
    translator = GoogleTranslator(source=src, target=target)
    last_request = None
    consecutive_failures = 0
    recovered = False
    n_nonempty = 0
    n_failed = 0
    translated = []
    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        failed = False
        if not text:
            text_tgt = ""
        else:
            probing = consecutive_failures >= _GOOGLE_MAX_CONSECUTIVE_FAILURES
            if probing and recovered:
                return _marian_fallback_or_raise(
                    segments, src, target,
                    f"Google Translate blocked the requests again at segment "
                    f"{i + 1}/{len(segments)} (rate limited). Retry later or "
                    f"pick MarianMT, DeepL or Ollama as the translation engine.",
                    try_marian=not marian_failed)
            if probing:
                print(
                    f"     ! Google Translate failed on {consecutive_failures} "
                    f"segments in a row (rate limited?): waiting "
                    f"{_GOOGLE_COOLDOWN:.0f}s before a probe request...",
                    flush=True,
                )
                time.sleep(_GOOGLE_COOLDOWN)
            attempts = 1 if probing else _GOOGLE_MAX_ATTEMPTS
            text_tgt = None
            rate_limited = False
            for attempt in range(attempts):
                if last_request is not None:
                    wait = _GOOGLE_MIN_INTERVAL - (time.monotonic() - last_request)
                    if wait > 0:
                        time.sleep(wait)
                last_request = time.monotonic()
                try:
                    text_tgt = _google_translate_with_timeout(translator, text) or text
                    break
                except transient_errors as e:
                    if isinstance(e, TimeoutError):
                        # The abandoned request still holds the translator,
                        # whose URL params translate() mutates: use a new one.
                        translator = GoogleTranslator(source=src, target=target)
                    if attempt == attempts - 1:
                        print(f"     ! Error segment {i}: {e}", flush=True)
                        rate_limited = True
                    else:
                        time.sleep(_GOOGLE_BACKOFF_BASE * (2 ** attempt))
                except Exception as e:
                    # Not a throttling error (e.g. text too long): retrying
                    # won't help and it says nothing about a block.
                    print(f"     ! Error segment {i}: {e}", flush=True)
                    break
            if text_tgt is None:
                if probing:
                    # Any probe failure (429, or a captcha page that surfaces
                    # as TranslationNotFound) means Google is still blocking.
                    return _marian_fallback_or_raise(
                        segments, src, target,
                        f"Google Translate is still blocking the requests at "
                        f"segment {i + 1}/{len(segments)} (rate limited). Retry "
                        f"later or pick MarianMT, DeepL or Ollama as the "
                        f"translation engine.", try_marian=not marian_failed)
                text_tgt = text
                failed = True
                if rate_limited:
                    consecutive_failures += 1
            else:
                if probing:
                    recovered = True
                consecutive_failures = 0
        if text:
            n_nonempty += 1
        entry = {
            "start": seg["start"],
            "end": seg["end"],
            "text_src": text,
            "text_tgt": text_tgt,
        }
        if "speaker" in seg:
            entry["speaker"] = seg["speaker"]
        # TASK 5C: forward whisper_suspicious flag through the Google path.
        # Google translation has no length retry, so length_unfit is not
        # produced here; the sanity flag from upstream still surfaces in
        # the editor for human review.
        _flags_in = compute_segment_quality_flags(seg)
        if _flags_in:
            entry["_quality_flags"] = _flags_in
        if failed:
            n_failed += 1
            add_quality_flag(entry, FLAG_TRANSLATION_FALLBACK)
        translated.append(entry)
        if i % 10 == 0:
            print(f"     {i+1}/{len(segments)}...", end="\r", flush=True)
    if n_nonempty and n_failed == n_nonempty:
        return _marian_fallback_or_raise(
            segments, src, target,
            "Google Translate could not translate any segment (rate limited, "
            "blocked or unreachable). Retry later or pick MarianMT, DeepL or "
            "Ollama as the translation engine.", try_marian=not marian_failed)
    if n_failed:
        print(
            f"     ⚠ Google Translate failed on {n_failed}/{n_nonempty} segments: "
            f"they keep the source text and are flagged in the subtitle editor.",
            flush=True,
        )
    print("     → Translation done          ", flush=True)
    return translated
