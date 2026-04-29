"""Pick a compatible Ollama model when the requested tag is not installed.

When the user has selected the Ollama engine and the configured model is
absent (e.g. a leftover ``mistral-nemo:12b-instruct`` from an earlier
experiment), the previous behaviour was to skip Ollama entirely and fall
back to Google Translate. That silently bypasses the whole Phase-2 LLM
work (length re-prompt, context-aware translation, thinking mode) and
the user has no idea why output quality regressed.

The smart selector instead inspects the daemon's ``/api/tags`` response,
finds the closest available model (preferring the same family, then a
preferred-families ranking, then alphabetical fallback) and returns it
so the pipeline can proceed on Ollama with a clear log.

Pure module: no I/O, no requests, no logging. Easy to unit test.
"""

from __future__ import annotations

import re
from typing import Sequence


# Default ranking of model families to consider when the requested family
# is not available. ``qwen3`` first because it carries our calibration
# (thinking mode, slot-aware prompt, length re-prompt) — those features
# generalise reasonably to the other qwen* families and most modern
# instruction-tuned LLMs but we want a deterministic, conservative order.
DEFAULT_PREFERRED_FAMILIES: tuple[str, ...] = (
    "qwen3",
    "qwen2.5",
    "qwen2",
    "llama3.1",
    "llama3.2",
    "llama3",
    "mistral-nemo",
    "mistral",
    "mixtral",
    "gemma2",
    "phi3",
)


def _size_in_b(name: str) -> int:
    """Extract the parameter count in billions from an Ollama tag.

    ``"qwen3:14b"`` -> 14, ``"qwen2.5:7b-instruct-q4_K_M"`` -> 7,
    ``"mistral"`` -> 0 (no size indicator). The regex matches the first
    ``:Nb`` after the colon, case-insensitive, so quantization tails do
    not interfere.
    """
    m = re.search(r":(\d+)b\b", name.lower())
    return int(m.group(1)) if m else 0


def _prefer_larger(name: str) -> tuple[int, str]:
    """Sort key: ``(-size, name)`` so larger models come first.

    Falls back to alphabetical when sizes are equal or unparseable, which
    keeps the ordering deterministic across runs and platforms.
    """
    return (-_size_in_b(name), name)


def _base_family(name: str) -> str:
    """Return the family identifier (everything before the first ``:``)."""
    return name.split(":", 1)[0] if ":" in name else name


def select_compatible_model(
    requested: str,
    available: Sequence[str],
    preferred_families: tuple[str, ...] = DEFAULT_PREFERRED_FAMILIES,
) -> str | None:
    """Pick the best Ollama model for ``requested`` from ``available``.

    Returns ``None`` only if ``available`` is empty (the daemon has no
    models at all). In every other case it returns a usable tag, with
    the following decreasing-quality strategy:

    1. **Exact match**: ``requested`` is already in ``available``.
    2. **Prefix match**: an available model starts with ``requested + "-"``
       (different quantization of the same tag).
    3. **Same base family**: an available model shares the part before
       the colon (``"qwen2.5:7b-instruct"`` matches ``"qwen2.5:14b"``).
       Within the family the largest parameter count wins.
    4. **Preferred families**: walk ``preferred_families`` in order and
       return the largest available model in the first family that has
       at least one entry.
    5. **Deterministic fallback**: if none of the preferred families
       match, return the largest model in ``available`` overall, breaking
       ties alphabetically.

    The function never raises on bad inputs — empty/None requested string
    is treated as "no preference" and goes straight to step 4.
    """
    if not available:
        return None

    available_list = list(available)
    requested = (requested or "").strip()

    if requested:
        # Step 1: exact match
        if requested in available_list:
            return requested

        # Step 2: prefix match (different quantization tail)
        prefix_matches = [m for m in available_list if m.startswith(requested + "-")]
        if prefix_matches:
            return sorted(prefix_matches, key=_prefer_larger)[0]

        # Step 3: same base family
        req_base = _base_family(requested)
        family_matches = [m for m in available_list if _base_family(m) == req_base]
        if family_matches:
            return sorted(family_matches, key=_prefer_larger)[0]

    # Step 4: preferred families ranking
    for family in preferred_families:
        candidates = [m for m in available_list if _base_family(m) == family]
        if candidates:
            return sorted(candidates, key=_prefer_larger)[0]

    # Step 5: deterministic fallback to largest overall
    return sorted(available_list, key=_prefer_larger)[0]
