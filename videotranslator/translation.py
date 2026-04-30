"""Translation engine dispatcher for Ollama, MarianMT, DeepL and Google."""

from __future__ import annotations

from videotranslator.quality_flags import compute_segment_quality_flags


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

    # ── Ollama LLM translation (v2.0) ──────────────────────────────────────
    # Leva strutturale contro gli atempo artifacts: l'LLM capisce il vincolo
    # temporale e comprime la traduzione alla sorgente, invece di lasciare che
    # MarianMT/Google producano output letterali +25% più lunghi.
    if engine == "llm_ollama":
        # TASK 2U: il Profile può forzare CoVe off (EASY) ma il flag
        # esplicito del caller (CLI --no-cove) ha priorità. Quando il
        # caller passa False, manteniamo l'override anche su MEDIUM/HARD.
        _effective_use_cove = ollama_use_cove
        if difficulty_profile is not None and not difficulty_profile.use_cove:
            _effective_use_cove = False
        try:
            if ollama_translator is None:
                raise RuntimeError("ollama_translator callback is required")
            return ollama_translator(
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

    # ── MarianMT local translation ──────────────────────────────────────────
    if engine == "marian":
        # Auto-detect is not supported: we need an explicit source language.
        if src == "auto":
            print("     ! MarianMT requires explicit source language (auto not supported), falling back to Google.", flush=True)
        else:
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
                    # TASK 5C: forward whisper_suspicious flag through the
                    # MarianMT path so the editor still highlights segments
                    # the upstream sanity check tagged. Other flags
                    # (length_unfit, translation_fallback) are Ollama-only.
                    _flags_in = compute_segment_quality_flags(seg)
                    if _flags_in:
                        _entry["_quality_flags"] = _flags_in
                    translated_segs.append(_entry)
                print("     → Translation done (MarianMT)          ", flush=True)
                return translated_segs
            except Exception as e:
                print(f"     ! MarianMT model {model_name} not available ({e.__class__.__name__}), falling back to Google.", flush=True)
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
        # fall through to Google if MarianMT failed
        engine = "google"

    # ── DeepL: batch API con retry/backoff ──────────────────────────────────
    if engine == "deepl" and deepl_key.strip():
        key = deepl_key.strip()
        endpoint = "https://api-free.deepl.com/v2/translate" if key.endswith(":fx") else "https://api.deepl.com/v2/translate"
        import requests, time as _time
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
                for attempt in range(MAX_RETRIES):
                    try:
                        r = requests.post(endpoint, headers=headers, data=payload, timeout=60)
                        if r.status_code == 429 or r.status_code >= 500:
                            wait = float(r.headers.get("Retry-After", 2 ** attempt))
                            print(f"     ! DeepL {r.status_code}, retry in {wait:.1f}s...", flush=True)
                            _time.sleep(wait)
                            continue
                        if r.status_code == 403:
                            raise RuntimeError(f"DeepL 403 Forbidden — verifica la API key ({r.text[:200]})")
                        r.raise_for_status()
                        data = r.json()
                        for j, item in zip(chunk_idx, data.get("translations", [])):
                            results[j] = item.get("text", "") or texts[j]
                        break
                    except requests.RequestException as e:
                        if attempt == MAX_RETRIES - 1:
                            print(f"     ! DeepL batch {i}-{i+len(chunk_idx)} failed: {e}", flush=True)
                            for j in chunk_idx:
                                results[j] = texts[j]
                        else:
                            _time.sleep(2 ** attempt)
                print(f"     {min(i + BATCH, len(idx_nonempty))}/{len(idx_nonempty)}...", end="\r", flush=True)
            translated = []
            for seg, tr in zip(segments, results):
                text = (seg.get("text") or "").strip()
                entry = {
                    "start": seg["start"], "end": seg["end"],
                    "text_src": text, "text_tgt": tr or text,
                }
                if "speaker" in seg:
                    entry["speaker"] = seg["speaker"]
                # TASK 5C: propagate upstream quality flags (whisper_suspicious)
                # through the DeepL path. DeepL itself doesn't add new flags
                # in this version — failed batches just keep the source text.
                _flags_in = compute_segment_quality_flags(seg)
                if _flags_in:
                    entry["_quality_flags"] = _flags_in
                translated.append(entry)
            print("     → Translation done (DeepL)          ", flush=True)
            return translated
        except Exception as e:
            print(f"     ! DeepL failed ({e}), falling back to Google Translate.", flush=True)
            engine = "google"

    # ── Google Translate fallback ──────────────────────────────────────────
    from deep_translator import GoogleTranslator
    if engine == "deepl":
        print("     ! DeepL key missing, falling back to Google Translate.", flush=True)
    translator = GoogleTranslator(source=src, target=target)
    translated = []
    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        if not text:
            text_tgt = ""
        else:
            try:
                text_tgt = translator.translate(text) or text
            except Exception as e:
                print(f"     ! Error segment {i}: {e}", flush=True)
                text_tgt = text
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
        translated.append(entry)
        if i % 10 == 0:
            print(f"     {i+1}/{len(segments)}...", end="\r", flush=True)
    print("     → Translation done          ", flush=True)
    return translated


