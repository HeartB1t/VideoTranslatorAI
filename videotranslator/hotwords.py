"""Hotwords loader for Whisper context-biased decoding.

faster-whisper's ``WhisperModel.transcribe(...)`` accepts a ``hotwords``
keyword that biases the decoder toward a list of expected terms (proper
nouns, brand names, technical jargon, regional slang). The bias is
applied as an extra prompt-side conditioning so the decoder produces
those tokens with higher probability when the audio matches phonetically.

Empirical reference: arXiv:2508.17796 ("Trie-based context biasing for
Whisper") reports a ~43-44% reduction in Biased-WER on rare-word
transcription with no measurable degradation on overall WER.

This module is **pure** (no faster-whisper import, no I/O outside the
JSON loader). It only handles:

  1. Parsing a comma-separated CLI string into a normalized list.
  2. Loading a JSON file (flat list OR per-language dict).
  3. Merging multiple sources while preserving insertion order.
  4. Converting the final list to the space-separated string that
     ``faster-whisper`` expects.

Sources, in priority order, are merged by the caller:

  * ``--hotwords "Strix, pipx, Docker"`` (CLI string).
  * ``--hotwords-file path/to/hotwords.json``.
  * Empty / ``None`` -> the decoder runs unbiased (default behavior).

JSON file accepts two shapes:

  * Flat list: ``["Strix", "pipx", "Docker"]``.
  * Per-language dict: ``{"en": [...], "it": [...], "de": [...]}`` —
    the caller passes ``src_lang`` (e.g. ``"it"``) and the matching
    list is returned. If the requested language is missing, the loader
    falls back to ``"en"``; if ``"en"`` is also missing it raises
    ``ValueError`` so the user notices the misconfigured file.

All entries are stripped of leading/trailing whitespace, empties are
dropped, duplicates are removed (case-sensitive: ``"OpenAI"`` and
``"openai"`` are kept separate because Whisper's tokenizer is
case-sensitive and the user might want both spellings biased).
"""

from __future__ import annotations

import json
from pathlib import Path


def parse_hotwords_string(s: str | None) -> list[str]:
    """Parse a comma-separated CLI string into a normalized list.

    Whitespace around each entry is stripped, empty entries are
    dropped, duplicates are removed preserving first-seen order. Case
    is preserved (Whisper's tokenizer is case-sensitive and Strix vs
    strix may bias different sub-tokens).

    Examples
    --------
    >>> parse_hotwords_string("")
    []
    >>> parse_hotwords_string("Strix, pipx, Docker")
    ['Strix', 'pipx', 'Docker']
    >>> parse_hotwords_string("  Strix  ,, Docker , Strix  ")
    ['Strix', 'Docker']
    """
    if not s:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for chunk in s.split(","):
        token = chunk.strip()
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def load_hotwords_file(
    path: str | Path,
    src_lang: str | None = None,
) -> list[str]:
    """Load hotwords from a JSON file.

    The file may contain either a flat ``list[str]`` or a
    ``dict[str, list[str]]`` keyed by language code (ISO 639-1, e.g.
    ``"en"``, ``"it"``, ``"de"``).

    For dict files:
      * ``src_lang`` selects the matching list.
      * ``src_lang`` of ``None`` or ``"auto"`` falls back to ``"en"``.
      * If ``src_lang`` is missing, the loader falls back to ``"en"``.
      * If ``"en"`` is also missing, raises ``ValueError`` so the
        caller can surface the misconfiguration.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        On malformed JSON, unsupported shape, or missing ``en``
        fallback in a dict file.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Hotwords file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in hotwords file {p}: {exc}") from exc

    if isinstance(raw, list):
        return _normalize_list(raw, source=str(p))

    if isinstance(raw, dict):
        # Per-language dict: try src_lang, then 'en' fallback.
        lang_key: str | None
        if src_lang and src_lang != "auto":
            lang_key = src_lang
        else:
            lang_key = "en"

        if lang_key in raw:
            return _normalize_list(raw[lang_key], source=f"{p}[{lang_key!r}]")

        # Fallback path when src_lang is set but missing in the dict.
        if "en" in raw:
            return _normalize_list(raw["en"], source=f"{p}['en']")

        raise ValueError(
            f"Hotwords file {p} is a per-language dict but neither "
            f"{lang_key!r} nor 'en' fallback are present. Add at least "
            f"an 'en' key."
        )

    raise ValueError(
        f"Hotwords file {p} must be a list or a per-language dict, "
        f"got {type(raw).__name__}."
    )


def _normalize_list(items: object, *, source: str) -> list[str]:
    """Validate and dedup a raw list-shaped value from JSON."""
    if not isinstance(items, list):
        raise ValueError(
            f"Expected list of strings at {source}, got "
            f"{type(items).__name__}."
        )
    out: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, str):
            raise ValueError(
                f"Hotword at {source}[{idx}] must be a string, got "
                f"{type(item).__name__}."
            )
        token = item.strip()
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def merge_hotwords(*sources: list[str] | None) -> list[str]:
    """Concatenate multiple hotwords lists into one, dedup'd.

    Preserves the order of first occurrence across all sources, so the
    caller can choose precedence by passing higher-priority lists first
    (e.g. CLI before file).

    ``None`` sources are skipped silently for caller convenience.
    """
    out: list[str] = []
    seen: set[str] = set()
    for src in sources:
        if not src:
            continue
        for token in src:
            if not isinstance(token, str):
                continue
            t = token.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out


def to_whisper_param(hotwords: list[str] | None) -> str | None:
    """Convert a normalized list to the format ``faster-whisper`` expects.

    ``faster-whisper`` accepts ``hotwords`` as a single
    space-separated string (the prompt-side conditioning is built
    from that string). Returns ``None`` if the list is empty so the
    caller can simply omit the kwarg and keep the default decoder
    behavior unchanged.
    """
    if not hotwords:
        return None
    cleaned = [h.strip() for h in hotwords if isinstance(h, str) and h.strip()]
    if not cleaned:
        return None
    return " ".join(cleaned)
