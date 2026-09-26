"""Marian route resolution for live translation (design 4.9).

Pure and testable: the per-language pivot table, the route resolver and the
cache check. The concrete per-engine translators (Marian/Ollama/Google/DeepL)
need the real engines and land with the live session; only the routing data and
logic live here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from videotranslator.translation import _marian_normalize_lang

# Per-sentence hard timeouts (design 4.9).
TIMEOUTS_S: dict[str, float] = {
    "marian": 5.0,
    "ollama_delayed": 8.0,
    "ollama_live": 3.0,
    "google": 5.0,
    "deepl": 5.0,
}


@dataclass(frozen=True)
class MarianLeg:
    model: str
    # For target-group models only: the first candidate present in the
    # tokenizer's supported codes wins (chosen at prepare()).
    target_token_candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarianRoute:
    legs: tuple[MarianLeg, ...]  # 1 leg (direct) or 2 legs (pivot through English)
    pivot: bool


def _leg(model: str, *tokens: str) -> MarianLeg:
    return MarianLeg(f"Helsinki-NLP/{model}", tuple(tokens))


# Languages whose X<->en pair is the plain opus-mt-X-en / opus-mt-en-X.
_SIMPLE = ("ar", "cs", "da", "de", "es", "fi", "fr", "hi", "hu", "id", "it",
           "nl", "ru", "sv", "uk", "vi")

# (X -> en leg, en -> X leg) per Marian-normalized code (design 4.9, [FD] Hub
# query 2026-09-25). Norwegian is keyed "nb" (the normalizer maps "no" -> "nb").
EN_LEGS: Mapping[str, tuple[MarianLeg | None, MarianLeg | None]] = {
    **{c: (_leg(f"opus-mt-{c}-en"), _leg(f"opus-mt-en-{c}")) for c in _SIMPLE},
    "zh": (_leg("opus-mt-zh-en"), _leg("opus-mt-en-zh")),
    "el": (_leg("opus-mt-tc-big-el-en"), _leg("opus-mt-en-el")),
    "ja": (_leg("opus-mt-ja-en"), _leg("opus-tatoeba-en-ja")),
    "ko": (_leg("opus-mt-ko-en"), _leg("opus-mt-tc-big-en-ko")),
    "tr": (_leg("opus-mt-tr-en"), _leg("opus-mt-tc-big-en-tr")),
    "pt": (_leg("opus-mt-ROMANCE-en"), _leg("opus-mt-tc-big-en-pt")),
    "ro": (_leg("opus-mt-ROMANCE-en"), _leg("opus-mt-en-ro")),
    "pl": (_leg("opus-mt-pl-en"), _leg("opus-mt-en-zlw", ">>pol<<", ">>pl<<")),
    "nb": (_leg("opus-mt-gmq-en"), _leg("opus-mt-tc-big-en-gmq", ">>nob<<", ">>no<<")),
}


def _available(model: str, hub_has: Callable[[str], bool] | None,
               is_cached: Callable[[str], bool]) -> bool:
    if is_cached(model):
        return True
    return hub_has is not None and hub_has(model)


def marian_route(src: str, tgt: str, *, hub_has: Callable[[str], bool] | None,
                 is_cached: Callable[[str], bool]) -> MarianRoute | None:
    """Resolve a Marian route (design 4.9).

    Order: cached direct ``opus-mt-{s}-{t}``; cached ``tc-big``; the same two on
    the Hub when online (``hub_has`` is None offline, so only cached models
    count); else a pivot ``src -> en -> tgt`` from :data:`EN_LEGS` with each leg
    cached or on the Hub; else ``None`` (the caller shows ``live_err_marian_pair``).
    """
    s = _marian_normalize_lang(src)
    t = _marian_normalize_lang(tgt)
    if s == t:
        return None
    if s == "en" or t == "en":
        code = t if s == "en" else s
        legs = EN_LEGS.get(code)
        if not legs:
            return None
        leg = legs[1] if s == "en" else legs[0]
        if leg is not None and _available(leg.model, hub_has, is_cached):
            return MarianRoute((leg,), False)
        return None
    direct = f"Helsinki-NLP/opus-mt-{s}-{t}"
    tc_big = f"Helsinki-NLP/opus-mt-tc-big-{s}-{t}"
    if is_cached(direct):
        return MarianRoute((MarianLeg(direct),), False)
    if is_cached(tc_big):
        return MarianRoute((MarianLeg(tc_big),), False)
    if hub_has is not None:
        if hub_has(direct):
            return MarianRoute((MarianLeg(direct),), False)
        if hub_has(tc_big):
            return MarianRoute((MarianLeg(tc_big),), False)
    leg_in = EN_LEGS.get(s, (None, None))[0]
    leg_out = EN_LEGS.get(t, (None, None))[1]
    if (leg_in is not None and leg_out is not None
            and _available(leg_in.model, hub_has, is_cached)
            and _available(leg_out.model, hub_has, is_cached)):
        return MarianRoute((leg_in, leg_out), True)
    return None


def _default_is_cached(model: str) -> bool:
    """True when the model is already in the local Hugging Face cache."""
    try:
        from transformers import MarianMTModel  # heavy; imported lazily
        MarianMTModel.from_pretrained(model, local_files_only=True)
        return True
    except Exception:
        return False


def marian_is_cached(route: MarianRoute, *,
                     loader: Callable[[str], bool] | None = None) -> bool:
    """True when every leg of the route is already cached locally."""
    check = loader if loader is not None else _default_is_cached
    return all(check(leg.model) for leg in route.legs)
