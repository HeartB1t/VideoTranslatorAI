"""TTS text sanitizer.

Coqui XTTS v2 (and other neural TTS) occasionally verbalize punctuation
characters as words instead of treating them as prosodic cues:

- ``:`` -> "due punti" / "two dots" (Italian / English)
- ``;`` -> "punto e virgola" / "semicolon"
- ``...`` / ``…`` -> "puntini" / "dot dot dot"
- em-dash ``-``, en-dash ``-``, hyphen-double ``--`` -> spelled out

The bug is text-tokenization specific: TTS models normalize the input by
splitting on whitespace and any non-letter token surrounded by whitespace
becomes an utterance candidate. With voice cloning the model can imitate
"reading aloud" style and pronounce the symbol literally.

This module replaces problematic characters with their closest prosodic
neighbour (comma for soft pause, period for hard pause) BEFORE the text
reaches XTTS. It is intentionally small and language-agnostic: every
substitution is a defensible prosodic equivalent in any language.

The legacy ``_strip_xtts_terminal_punct()`` already handles trailing
``.!?;:`` because the same model also pronounces them at end of clip;
this module complements it by addressing INTERNAL occurrences.
"""

from __future__ import annotations

import re

# Order matters: multi-char patterns first so they do not get rewritten by
# later single-char rules (e.g. "..." must collapse before "." passes through).
_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    # Multi-dot ellipsis (ASCII and Unicode) -> single period.
    ("…", "."),  # …
    ("...", "."),
    ("..", "."),
    # Em-dash, en-dash, double hyphen -> comma (soft pause, no spelling).
    ("—", ","),  # —
    ("–", ","),  # –
    ("--", ","),
    # Semicolon -> period. Colon is handled via regex below to preserve
    # digit-flanked occurrences (clock times, scores, ratios).
    (";", "."),
)

# Colon between non-digits OR adjacent to a non-digit becomes a comma.
# Digit-flanked colons stay intact: clock times "10:30", durations "1:23:45",
# scores "3:1" must keep their original spelling so XTTS pronounces them as
# numbers, not as "ten comma thirty".
_COLON_SAFE_TO_COMMA = re.compile(r"(?<!\d):|:(?!\d)")

# Collapse repeated commas / periods left by the substitutions
# (e.g. ", , " or ". . " when source contained "—," or ".:").
_COLLAPSE_DOUBLE_COMMA = re.compile(r",(\s*,)+")
_COLLAPSE_DOUBLE_PERIOD = re.compile(r"\.(\s*\.)+")
# Collapse ", ." or ". ," sequences to a single period (period wins).
_COMMA_BEFORE_PERIOD = re.compile(r",\s*\.")
_PERIOD_BEFORE_COMMA = re.compile(r"\.\s*,")
# Collapse runs of whitespace introduced by replacements into single spaces.
_MULTI_WS = re.compile(r"[ \t]{2,}")


def sanitize_for_tts(text: str) -> str:
    """Return ``text`` with TTS-unsafe punctuation rewritten.

    Idempotent: ``sanitize_for_tts(sanitize_for_tts(x)) == sanitize_for_tts(x)``.

    Empty / None input returns "" so callers can chain safely.
    """
    if not text:
        return ""
    out = text
    for src, dst in _REPLACEMENTS:
        out = out.replace(src, dst)
    out = _COLON_SAFE_TO_COMMA.sub(",", out)
    out = _COMMA_BEFORE_PERIOD.sub(".", out)
    out = _PERIOD_BEFORE_COMMA.sub(".", out)
    out = _COLLAPSE_DOUBLE_PERIOD.sub(".", out)
    out = _COLLAPSE_DOUBLE_COMMA.sub(",", out)
    out = _MULTI_WS.sub(" ", out)
    return out.strip()
