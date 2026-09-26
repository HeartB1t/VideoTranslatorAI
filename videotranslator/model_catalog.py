"""Curated model catalogue and hardware-based recommendations.

Feature "hardware-aware model selection", step 2: for each pipeline stage
(speech recognition for files and for live, translation, speech synthesis) list
the options the app already supports, with their resource needs, and recommend
one per preference ("speed", "balanced", "quality") from a ``HardwareInfo``.

Resource figures are conservative estimates (faster-whisper README benchmarks
and measurements on the dev machine), used only to rank options; they are not
a benchmark. Online services (Google, DeepL, Edge-TTS) are labelled as such
rather than presented as hardware-selected downloads. Pure module: no I/O.

Every recommendation carries its evidence as ``(reason_key, params)`` pairs,
rendered through the UI strings, so the user sees why an option was chosen and
can ignore it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from .hardware_profile import HardwareInfo

PREFERENCES = ("speed", "balanced", "quality")


@dataclass(frozen=True)
class ModelOption:
    stage: str                 # "asr", "asr_live", "mt", "tts"
    key: str                   # value written to the settings (model or engine)
    label: str                 # display name (a product/model name, not translated)
    local: bool                # runs on this PC (downloaded model) or online service
    download_mb: int = 0       # 0 = nothing to download (online, or on first use)
    vram_gb: float = 0.0       # GPU memory needed on CUDA
    ram_gb: float = 0.0        # system memory needed on CPU
    quality: int = 0           # 1 (lowest) .. 6 (highest), same stage only
    needs_account: bool = False
    repo: str | None = None    # Hugging Face repo (Whisper models)
    licence: str = ""


# Whisper (faster-whisper / CTranslate2). VRAM is fp16 with beam 5, RAM is int8.
WHISPER = {
    "tiny": ModelOption("asr", "tiny", "Whisper tiny", True, 75, 0.6, 0.6, 1,
                        repo="Systran/faster-whisper-tiny", licence="MIT"),
    "base": ModelOption("asr", "base", "Whisper base", True, 145, 0.8, 0.8, 2,
                        repo="Systran/faster-whisper-base", licence="MIT"),
    "small": ModelOption("asr", "small", "Whisper small", True, 484, 1.2, 1.2, 3,
                         repo="Systran/faster-whisper-small", licence="MIT"),
    "medium": ModelOption("asr", "medium", "Whisper medium", True, 1530, 2.6, 2.4, 4,
                          repo="Systran/faster-whisper-medium", licence="MIT"),
    "large-v3-turbo": ModelOption("asr", "large-v3-turbo", "Whisper large-v3-turbo",
                                  True, 1620, 3.0, 3.5, 5,
                                  repo="mobiuslabsgmbh/faster-whisper-large-v3-turbo",
                                  licence="MIT"),
    "large-v2": ModelOption("asr", "large-v2", "Whisper large-v2", True, 3090, 4.8, 4.5, 5,
                            repo="Systran/faster-whisper-large-v2", licence="MIT"),
    "large-v3": ModelOption("asr", "large-v3", "Whisper large-v3", True, 3090, 4.8, 4.5, 6,
                            repo="Systran/faster-whisper-large-v3", licence="MIT"),
}

MT = {
    "google": ModelOption("mt", "google", "Google Translate", False, quality=3),
    "deepl": ModelOption("mt", "deepl", "DeepL", False, quality=5, needs_account=True),
    "marian": ModelOption("mt", "marian", "MarianMT", True, 300, 0.0, 1.5, 3,
                          licence="CC-BY 4.0"),
    "qwen3:8b": ModelOption("mt", "qwen3:8b", "Ollama qwen3:8b", True, 5200, 7.0, 10.0, 4,
                            licence="Apache-2.0"),
    "qwen3:14b": ModelOption("mt", "qwen3:14b", "Ollama qwen3:14b", True, 9300, 11.0, 16.0,
                             5, licence="Apache-2.0"),
    # For GPUs larger than a 24 GB card once live Whisper has its share.
    "qwen3:32b": ModelOption("mt", "qwen3:32b", "Ollama qwen3:32b", True, 20000, 22.0, 32.0,
                             6, licence="Apache-2.0"),
}

TTS = {
    "edge": ModelOption("tts", "edge", "Edge-TTS", False, quality=3),
    "xtts": ModelOption("tts", "xtts", "Coqui XTTS v2", True, 1870, 4.0, 6.0, 5,
                        licence="CPML (non-commercial)"),
    # Separate local program (its own models and memory): never recommended
    # automatically, since it must be installed and started apart.
    "voicebox": ModelOption("tts", "voicebox", "Voicebox (local server)", True, quality=5,
                            licence="MIT"),
}

STAGE_OPTIONS = {"asr": WHISPER, "asr_live": WHISPER, "mt": MT, "tts": TTS}

# Headroom left free on the GPU/RAM (desktop, other apps, the video player).
_VRAM_HEADROOM_GB = 1.0
_RAM_HEADROOM_GB = 2.0
_DISK_HEADROOM_GB = 1.0


@dataclass(frozen=True)
class Recommendation:
    stage: str
    option: ModelOption
    reasons: tuple[tuple[str, dict[str, Any]], ...] = field(default_factory=tuple)


def _fmt(value: float | None) -> str:
    return "?" if value is None else f"{value:.1f}"


def _fits(opt: ModelOption, hw: HardwareInfo, *, gpu: bool) -> bool:
    if gpu:
        return (hw.vram_gb or 0.0) - _VRAM_HEADROOM_GB >= opt.vram_gb
    ram = hw.ram_gb if hw.ram_gb is not None else 8.0    # unknown RAM: assume 8 GB
    return ram - _RAM_HEADROOM_GB >= opt.ram_gb


def _disk_ok(opt: ModelOption, hw: HardwareInfo, cached: set[str]) -> bool:
    if opt.key in cached or not opt.download_mb or hw.disk_free_gb is None:
        return True
    return hw.disk_free_gb - _DISK_HEADROOM_GB >= opt.download_mb / 1024


def _device_reason(hw: HardwareInfo) -> tuple[str, dict[str, Any]]:
    if hw.vram_gb is not None:
        return ("rec_reason_gpu", {"gpu": hw.best_gpu.name, "vram": _fmt(hw.vram_gb)})
    if hw.best_gpu is not None:
        return ("rec_reason_gpu_unusable", {"gpu": hw.best_gpu.name})
    return ("rec_reason_cpu", {"cores": hw.cpu_cores or "?", "ram": _fmt(hw.ram_gb)})


# Preferred Whisper order per preference; the first that fits wins.
_ASR_ORDER = {
    ("gpu", "quality"): ("large-v3", "large-v3-turbo", "medium", "small", "base", "tiny"),
    ("gpu", "balanced"): ("large-v3-turbo", "medium", "small", "base", "tiny"),
    ("gpu", "speed"): ("large-v3-turbo", "small", "base", "tiny"),
    ("cpu", "quality"): ("medium", "small", "base", "tiny"),
    ("cpu", "balanced"): ("small", "base", "tiny"),
    ("cpu", "speed"): ("base", "tiny"),
}
# Live needs faster-than-real-time transcription: lighter choices.
_ASR_LIVE_ORDER = {
    ("gpu", "quality"): ("large-v3-turbo", "medium", "small", "base", "tiny"),
    ("gpu", "balanced"): ("large-v3-turbo", "small", "base", "tiny"),
    ("gpu", "speed"): ("small", "base", "tiny"),
    ("cpu", "quality"): ("small", "base", "tiny"),
    ("cpu", "balanced"): ("base", "tiny"),
    ("cpu", "speed"): ("tiny",),
}
# A CPU with few cores cannot keep small/medium real time.
_CPU_MIN_CORES = {"medium": 8, "small": 4}


def _pick_whisper(hw: HardwareInfo, preference: str, order: dict, stage: str,
                  cached: set[str]) -> Recommendation:
    gpu = hw.vram_gb is not None
    reasons: list[tuple[str, dict[str, Any]]] = [_device_reason(hw)]
    for key in order[("gpu" if gpu else "cpu", preference)]:
        opt = WHISPER[key]
        if not _fits(opt, hw, gpu=gpu):
            continue
        if not gpu and (hw.cpu_cores or 0) < _CPU_MIN_CORES.get(key, 0):
            continue
        if not _disk_ok(opt, hw, cached):
            reasons.append(("rec_reason_disk", {"model": opt.label,
                                                "free": _fmt(hw.disk_free_gb)}))
            continue
        need = opt.vram_gb if gpu else opt.ram_gb
        reasons.append(("rec_reason_fits", {"model": opt.label, "need": _fmt(need)}))
        return Recommendation(stage, replace(opt, stage=stage), tuple(reasons))
    tiny = WHISPER["tiny"]
    reasons.append(("rec_reason_fallback", {"model": tiny.label}))
    return Recommendation(stage, replace(tiny, stage=stage), tuple(reasons))


def _pick_mt(hw: HardwareInfo, preference: str, cached: set[str],
             live_asr: ModelOption) -> Recommendation:
    if preference == "speed":
        return Recommendation("mt", MT["google"], (("rec_reason_online_fast", {}),))
    if preference == "quality" and hw.vram_gb is not None:
        # In a live session Whisper and the LLM share the GPU: the LLM gets
        # what is left after the live speech model.
        budget = hw.vram_gb - _VRAM_HEADROOM_GB - live_asr.vram_gb
        for key in ("qwen3:32b", "qwen3:14b", "qwen3:8b"):
            opt = MT[key]
            if budget >= opt.vram_gb and _disk_ok(opt, hw, cached):
                return Recommendation("mt", opt, (
                    _device_reason(hw),
                    ("rec_reason_fits", {"model": opt.label, "need": _fmt(opt.vram_gb)}),
                    ("rec_reason_ollama", {})))
    return Recommendation("mt", MT["marian"], (("rec_reason_offline", {}),))


def _pick_tts(hw: HardwareInfo, preference: str, cached: set[str]) -> Recommendation:
    xtts = TTS["xtts"]
    if (preference == "quality" and hw.vram_gb is not None
            and _fits(xtts, hw, gpu=True) and _disk_ok(xtts, hw, cached)):
        return Recommendation("tts", xtts, (
            _device_reason(hw),
            ("rec_reason_fits", {"model": xtts.label, "need": _fmt(xtts.vram_gb)}),
            ("rec_reason_licence", {"licence": xtts.licence})))
    reasons: list[tuple[str, dict[str, Any]]] = [("rec_reason_online_free", {})]
    if preference == "quality":
        reasons.append(("rec_reason_needs_gpu", {"model": xtts.label}))
    return Recommendation("tts", TTS["edge"], tuple(reasons))


def recommend(hw: HardwareInfo, preference: str = "balanced", *,
              cached: set[str] | frozenset[str] = frozenset()) -> dict[str, Recommendation]:
    """One recommendation per stage: ``asr``, ``asr_live``, ``mt``, ``tts``.

    ``cached`` holds the keys of models already on disk (no download, no disk
    check). Unknown preferences fall back to "balanced".
    """
    if preference not in PREFERENCES:
        preference = "balanced"
    cached = set(cached)
    live = _pick_whisper(hw, preference, _ASR_LIVE_ORDER, "asr_live", cached)
    return {
        "asr": _pick_whisper(hw, preference, _ASR_ORDER, "asr", cached),
        "asr_live": live,
        "mt": _pick_mt(hw, preference, cached, live.option),
        "tts": _pick_tts(hw, preference, cached),
    }


def assess(opt: ModelOption, hw: HardwareInfo, *,
           cached: set[str] | frozenset[str] = frozenset()) -> str:
    """How an option fits this PC, for the manual choice list.

    ``online`` (a service, nothing runs here), ``ok`` (fits with headroom),
    ``tight`` (fits only without headroom: may be slow or fail with other apps
    open), ``too_big`` (does not fit the memory), ``no_disk`` (not enough free
    disk to download it). Every option stays selectable: this is advice.
    """
    if not opt.local:
        return "online"
    if not _disk_ok(opt, hw, set(cached)):
        return "no_disk"
    gpu = hw.vram_gb is not None and opt.vram_gb > 0
    if gpu:
        have, need, headroom = hw.vram_gb, opt.vram_gb, _VRAM_HEADROOM_GB
    else:
        have = hw.ram_gb if hw.ram_gb is not None else 8.0
        need, headroom = opt.ram_gb, _RAM_HEADROOM_GB
    if have - headroom >= need:
        return "ok"
    return "tight" if have >= need else "too_big"
