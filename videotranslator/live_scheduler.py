"""Caption rendering helpers for live mode (design 4.11, 4.12).

Pure helpers used by the live scheduler: greedy caption wrapping, time-boxed
pagination of long captions, and ASS escaping/rendering that mirrors mpv's own
OSD escaping. The stateful ``DubScheduler`` (segment state machine, clip and
duck actions) lands with the live session.
"""

from __future__ import annotations

from collections.abc import Sequence

# U+2060 WORD JOINER, inserted after every backslash so a literal "\n"/"\N" in
# speech stays literal (design 4.12, [CT] finding 12).
_WORD_JOINER = "\u2060"


def _greedy_lines(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_caption(text: str, max_chars: int = 42, max_lines: int = 2) -> list[str]:
    """Greedy word-wrap into lines of at most ``max_chars``, at most ``max_lines``.

    Returns one page of lines; use :func:`paginate_caption` for text that needs
    more than ``max_lines`` lines.
    """
    return _greedy_lines(text, max_chars)[:max_lines]


def paginate_caption(text: str, start: float, end: float
                     ) -> list[tuple[float, float, list[str]]]:
    """Split a long caption into time-boxed pages of at most two lines.

    Each page's duration is proportional to its character count; the last page
    ends exactly at ``end``.
    """
    max_chars, max_lines = 42, 2
    lines = _greedy_lines(text, max_chars)
    if not lines:
        return []
    pages = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
    weights = [max(1, len(" ".join(page))) for page in pages]
    total = sum(weights)
    span = end - start
    out: list[tuple[float, float, list[str]]] = []
    cursor = start
    for i, (page, weight) in enumerate(zip(pages, weights)):
        page_end = end if i == len(pages) - 1 else cursor + span * weight / total
        out.append((cursor, page_end, page))
        cursor = page_end
    return out


def ass_escape(text: str) -> str:
    """Mirror mpv's OSD escaping (osd_libass.c:200-252, [CT] finding 12).

    Every backslash is followed by U+2060 so typed "\\n"/"\\N" stays literal, and
    every "{" becomes "\\{". Nothing is doubled. Real line breaks are inserted as
    "\\N" by :func:`caption_ass` after escaping.
    """
    return text.replace("\\", "\\" + _WORD_JOINER).replace("{", "\\{")


def caption_ass(lines: Sequence[str], *, font_px: int, italic: bool) -> str:
    """Render caption lines as an ASS events string (design 4.12 style)."""
    style = "{\\an2\\fs%d\\bord2\\shad0}" % font_px
    if italic:
        style += "{\\i1}"
    return style + "\\N".join(ass_escape(line) for line in lines)
