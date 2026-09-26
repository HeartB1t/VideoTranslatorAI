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


# --- Concrete per-sentence translators (design 4.9). ------------------------

import concurrent.futures
from dataclasses import dataclass as _dataclass


@_dataclass(frozen=True)
class Outcome:
    text: str
    ok: bool
    latency_s: float
    error: str | None = None   # rate_limited | quota | timeout | unavailable | error


class LiveTranslateError(Exception):
    def __init__(self, key: str, params: dict | None = None) -> None:
        super().__init__(key)
        self.key = key
        self.params = params or {}


def _cuda_device(torch_module) -> str:
    try:
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


class MarianLiveTranslator:
    """Offline MarianMT translator, one tokenizer+model per route leg (design 4.9).

    Loads the leg(s) once on prepare (CUDA if available), runs greedy decoding
    with max_length 512, and for a pivot route runs leg 1 then leg 2 inside the
    same per-sentence timeout. Group target models get their ``>>xxx<<`` token.
    """

    name = "marian"
    online = False

    def __init__(self, *, hub_has=None, is_cached=None, tokenizer_loader=None,
                 model_loader=None, torch_module=None,
                 clock: Callable[[], float] | None = None) -> None:
        self._hub_has = hub_has
        self._is_cached = is_cached if is_cached is not None else (lambda m: True)
        self._tokenizer_loader = tokenizer_loader
        self._model_loader = model_loader
        self._torch = torch_module
        import time as _t
        self._clock = clock or _t.monotonic
        self._legs: list[tuple[Any, Any, str | None]] = []  # (tokenizer, model, token)
        self._pivot = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _load(self):
        if self._tokenizer_loader and self._model_loader:
            return self._tokenizer_loader, self._model_loader, "cpu"
        from transformers import MarianMTModel, MarianTokenizer
        if self._torch is None:
            import torch as torch_module
        else:
            torch_module = self._torch
        device = _cuda_device(torch_module)

        def tok_loader(model):
            return MarianTokenizer.from_pretrained(model)

        def mdl_loader(model):
            return MarianMTModel.from_pretrained(model).to(device)

        return tok_loader, mdl_loader, device

    def prepare(self, src: str, tgt: str) -> None:
        route = marian_route(src, tgt, hub_has=self._hub_has, is_cached=self._is_cached)
        if route is None:
            raise LiveTranslateError("marian_pair", {"src": src, "tgt": tgt})
        self._pivot = route.pivot
        tok_loader, mdl_loader, device = self._load()
        self._device = device
        self._legs = []
        for leg in route.legs:
            tokenizer = tok_loader(leg.model)
            model = mdl_loader(leg.model)
            token = self._pick_token(tokenizer, leg.target_token_candidates)
            self._legs.append((tokenizer, model, token))

    @staticmethod
    def _pick_token(tokenizer, candidates: tuple[str, ...]) -> str | None:
        if not candidates:
            return None
        supported = set(getattr(tokenizer, "supported_language_codes", []) or [])
        for candidate in candidates:
            if candidate in supported:
                return candidate
        return candidates[0]

    def _run_leg(self, tokenizer, model, token: str | None, text: str) -> str:
        source = f"{token} {text}" if token else text
        batch = tokenizer([source], return_tensors="pt", truncation=True, max_length=512)
        batch = {k: v.to(getattr(self, "_device", "cpu")) for k, v in batch.items()}
        generated = model.generate(**batch, num_beams=1, max_length=512)
        return tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def _translate_sync(self, text: str) -> str:
        current = text
        for tokenizer, model, token in self._legs:
            current = self._run_leg(tokenizer, model, token, current)
        return current

    def translate(self, text: str, *, context=(), timeout_s: float = 5.0) -> Outcome:
        start = self._clock()
        try:
            future = self._executor.submit(self._translate_sync, text)
            result = future.result(timeout=timeout_s)
            return Outcome(result, True, self._clock() - start)
        except concurrent.futures.TimeoutError:
            return Outcome(text, False, self._clock() - start, error="timeout")
        except Exception:
            return Outcome(text, False, self._clock() - start, error="error")

    def close(self) -> None:
        self._legs = []
        self._executor.shutdown(wait=False)
        if self._torch is not None:
            try:
                self._torch.cuda.empty_cache()
            except Exception:
                pass


def make_translator(engine: str, **deps) -> Any:
    """Build the per-sentence translator for ``engine`` (design 4.9).

    MarianMT is fully offline. The online engines are thin wrappers to be filled
    in with their real clients; unknown engines raise.
    """
    if engine == "marian":
        return MarianLiveTranslator(**{k: deps[k] for k in (
            "hub_has", "is_cached", "tokenizer_loader", "model_loader",
            "torch_module", "clock") if k in deps})
    raise LiveTranslateError("ollama" if engine == "ollama" else "internal",
                             {"engine": engine})
