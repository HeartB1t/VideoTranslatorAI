"""Sanity checks for Whisper transcription output (TASK 2M).

Whisper-large-v3 occasionally produces non-words on noisy clips:

- isolated 1-3 char tokens that aren't real English words (``ay``,
  ``em``, ``ux``)
- truncated contractions (``Im`` instead of ``I'm``)
- repeated words (``the the``, ``and and``)

These propagate into Ollama translation and produce incomprehensible
target text. This module flags suspicious tokens for warning logs;
the actual fix (manual edit via subtitle editor, or re-translate via
Ollama with full-context fix prompt) lives in the caller.

Pure module: no I/O, no network, no subprocess. The whitelist is a
compact in-memory ``frozenset`` of common English tokens (~250 entries),
chosen to cover the false-positive surface for the 1-3 char filter
without claiming dictionary completeness.
"""

from __future__ import annotations

import re

# Compact whitelist of common English short tokens (1-3 chars). The
# filter only inspects 1-3 char tokens, so longer words (like
# ``okay`` or ``hello``) are never flagged regardless of being here.
# Keep the list focused on words that *do* fit in 1-3 chars to avoid
# false positives from the heuristic.
_COMMON_ENGLISH_TOKENS: frozenset[str] = frozenset({
    # articles, conjunctions, prepositions
    "a", "an", "the",
    "and", "or", "but", "if", "so", "as", "nor", "yet",
    "of", "to", "in", "on", "at", "by", "for", "off", "out", "up",
    "via", "per", "vs",
    # pronouns + possessives
    "i", "me", "my", "we", "us", "our",
    "he", "him", "his", "she", "her", "hers",
    "it", "its", "you",
    # auxiliaries / common short verbs
    "am", "is", "are", "was", "be", "been",
    "do", "did", "has", "had", "have",
    "can", "may", "let", "get", "got", "go", "see", "say",
    "use", "run", "put", "try", "ask", "buy", "cut", "eat", "fly",
    "win", "sit", "set", "lie", "lay", "pay", "saw", "won", "ran",
    "led", "led", "fed", "fit", "hit", "met",
    # common short nouns / adjectives / adverbs
    "no", "not", "yes", "ok", "all", "any", "few", "lot",
    "big", "low", "new", "old", "bad", "far", "hot", "icy",
    "now", "too", "way", "day", "yet", "own", "one", "two",
    "ten", "six", "men", "man", "boy", "guy", "kid",
    "car", "bus", "key", "job", "law", "art", "war", "tax",
    "end", "top", "fun", "use", "act", "age",
    # verbs / contractions stems short
    "let", "ran", "won", "lay", "led",
    # common interjections / short fillers
    "oh", "uh", "ah", "hi", "ha", "ho", "ow",
    # demonstratives / question words 1-3
    "who", "why", "how",
    # common short tech / domain (English) words
    "app", "web", "url", "css", "ssh", "sql", "tcp", "ip",
    "git", "ssh", "tor",
    # "ok" variants are 1-3 only ("okay" is 4)
    "ok",
})


# Match alphabetic tokens of length 1-3. ``\b`` keeps numbers /
# punctuation out and avoids matching the inside of longer words.
# The regex deliberately ignores hyphenated parts and apostrophe
# parts (e.g. ``don't`` won't trigger), because those are normal
# Whisper output for English.
_SUSPICIOUS_TOKEN_RE = re.compile(r"\b([A-Za-z]{1,3})\b")


# Repeated-word detector: ``(\w+)\s+\1`` with case-insensitive match.
# Apostrophes count as word chars so ``it's it's`` is caught too.
_REPEAT_TOKEN_RE = re.compile(r"\b([A-Za-z']+)\s+\1\b", re.IGNORECASE)


def find_suspicious_tokens(text: str) -> list[str]:
    """Return tokens that look like Whisper transcription noise.

    Cases caught:

    - isolated short tokens (``ay``, ``em``, ``ux``) not in the
      common-words whitelist
    - DOES NOT catch real short words (``I``, ``a``, ``of``, ``to``,
      ``the``)
    - DOES NOT catch numbers or alphanumerics (``42``, ``3rd``)
    - DOES NOT catch words longer than 3 chars (``okay``, ``hello``)

    Returns a list of de-duplicated lowercase strings preserving
    order of first appearance.
    """
    if not text:
        return []
    suspicious: list[str] = []
    seen: set[str] = set()
    for tok in _SUSPICIOUS_TOKEN_RE.findall(text):
        low = tok.lower()
        if low in _COMMON_ENGLISH_TOKENS:
            continue
        if low.isdigit():
            continue
        if low in seen:
            continue
        seen.add(low)
        suspicious.append(low)
    return suspicious


def detect_repeated_words(text: str) -> list[str]:
    """Detect immediate repeated words like ``the the`` / ``and and``.

    Returns the repeated tokens (lowercased, deduplicated, in order
    of first appearance). Common legitimate cases (``had had``,
    ``that that``) are still flagged: they are rare enough that a
    manual review of the segment is worth the false positive.
    """
    if not text:
        return []
    matches = _REPEAT_TOKEN_RE.findall(text)
    out: list[str] = []
    seen: set[str] = set()
    for tok in matches:
        low = tok.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(low)
    return out


def sanity_score_segments(segments: list[dict]) -> dict[int, dict]:
    """Run sanity checks on every segment with text content.

    Each segment is read as ``segment.get("text_src") or
    segment.get("text")``. Segments without either key (or with
    empty/whitespace-only text) are skipped silently.

    Returns a dict mapping ``segment_index -> {"suspicious": [...],
    "repeats": [...]}`` for each segment that has at least one flag.
    Returns an empty dict when nothing is flagged or when
    ``segments`` is empty/None.
    """
    out: dict[int, dict] = {}
    if not segments:
        return out
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        text = (seg.get("text_src") or seg.get("text") or "")
        if isinstance(text, str):
            text = text.strip()
        else:
            continue
        if not text:
            continue
        susp = find_suspicious_tokens(text)
        reps = detect_repeated_words(text)
        if susp or reps:
            out[i] = {"suspicious": susp, "repeats": reps}
    return out


__all__ = [
    "find_suspicious_tokens",
    "detect_repeated_words",
    "sanity_score_segments",
]
