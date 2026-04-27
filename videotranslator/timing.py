"""Timing heuristics for dubbed speech generation."""

LANG_EXPANSION: dict[str, float] = {
    "en": 1.00,
    "zh-CN": 0.70, "zh": 0.70, "ja": 0.85, "ko": 0.90,
    "it": 1.25, "es": 1.25, "pt": 1.22, "fr": 1.27, "de": 1.20,
    "nl": 1.18, "sv": 1.15, "da": 1.12, "no": 1.12, "fi": 1.10,
    "ru": 1.15, "uk": 1.15, "pl": 1.15, "cs": 1.10, "hu": 1.20,
    "ar": 1.08, "hi": 1.10, "tr": 1.10, "el": 1.20, "ro": 1.20,
    "vi": 1.15, "id": 1.10,
}

XTTS_CHARS_PER_SEC = {
    "en": 16.0, "it": 15.0, "es": 15.5, "fr": 15.0, "de": 14.5,
    "pt": 15.0, "nl": 15.0, "ja": 10.0, "zh-CN": 8.0, "zh": 8.0,
    "ko": 10.5, "ru": 13.5, "ar": 13.0, "hi": 13.0, "tr": 14.0,
    "pl": 13.5, "uk": 13.5, "cs": 14.0, "el": 13.0, "hu": 13.0,
    "fi": 13.5, "sv": 14.5, "da": 14.5, "no": 14.5, "ro": 14.5,
    "vi": 13.0, "id": 14.0,
}


def _norm_lang(code: str) -> str:
    code = (code or "").strip()
    if not code or code.lower() == "auto":
        return "en"
    if code.lower().startswith("zh"):
        return code if code in LANG_EXPANSION else "zh"
    return code


def suggest_xtts_speed(
    lang_source: str,
    lang_target: str,
    user_override: float | None = None,
) -> tuple[float, float, bool]:
    """Return ``(speed, expansion_ratio, auto)`` for XTTS-style engines."""
    src_exp = LANG_EXPANSION.get(_norm_lang(lang_source), 1.0)
    tgt_exp = LANG_EXPANSION.get(_norm_lang(lang_target), 1.0)
    ratio = (tgt_exp / src_exp) if src_exp > 0 else 1.0

    if user_override is not None:
        return float(user_override), ratio, False

    if ratio >= 1.20:
        speed = 1.35
    elif ratio >= 1.10:
        speed = 1.30
    elif ratio <= 0.75:
        speed = 1.15
    else:
        speed = 1.25
    return max(1.10, min(speed, 1.40)), ratio, True


def estimate_tts_duration_s(text: str, lang: str) -> float:
    """Estimate spoken duration at XTTS speed=1.0."""
    key = (lang or "").strip()
    rate = XTTS_CHARS_PER_SEC.get(key)
    if rate is None:
        rate = XTTS_CHARS_PER_SEC.get(key.lower())
    if rate is None:
        rate = XTTS_CHARS_PER_SEC.get(key.split("-")[0].lower(), 14.0)
    return max(0.5, len((text or "").strip()) / rate)


def compute_segment_speed(
    text: str,
    slot_s: float,
    lang_target: str,
    ceiling: float = 1.40,
) -> float:
    """Compute adaptive per-segment TTS speed."""
    hard_cap = min(1.40, max(1.05, ceiling))
    if not text or slot_s <= 0:
        return max(1.05, min(hard_cap, 1.25))
    required = estimate_tts_duration_s(text, lang_target) / slot_s
    return max(1.05, min(required, hard_cap))

