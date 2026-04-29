"""Subtitle and Whisper segment manipulation helpers."""

import re

from videotranslator.ollama_length_control import chars_per_second_for

END_PUNCT_CHARS = r".?!;。？！；؟"

# --- TASK 2L: continuation-token lists -------------------------------------
# Function words that, when they appear at the END of a Whisper segment,
# almost certainly mean the sentence has been cut mid-clause: prepositions,
# articles, conjunctions and a few subordinators. We keep each list short
# (high-precision tokens only) so we don't accidentally merge legitimate
# sentences that simply happen to end on a common word.
_CONTINUATION_TOKENS_EN: tuple[str, ...] = (
    "to", "for", "of", "at", "in", "on", "by", "with", "from",
    "about", "and", "or", "but", "because", "so", "that",
    "which", "who", "when", "while", "since", "if", "though",
    "as", "than", "into", "onto", "upon", "across",
    "the", "a", "an",
)
_CONTINUATION_TOKENS_IT: tuple[str, ...] = (
    "di", "del", "della", "dello", "dei", "delle", "degli",
    "al", "alla", "allo", "agli", "alle",
    "per", "con", "da", "in", "su", "tra", "fra",
    "e", "o", "ma", "che", "chi", "quando", "mentre", "se",
    "il", "la", "lo", "i", "gli", "le", "un", "una", "uno",
    "ha", "ho", "hai", "abbiamo", "avete", "hanno",
)
_CONTINUATION_TOKENS_ES: tuple[str, ...] = (
    "de", "del", "al", "a", "en", "con", "por", "para", "sobre", "entre",
    "y", "o", "pero", "que", "cuando", "mientras", "si",
    "el", "la", "los", "las", "un", "una", "unos", "unas",
)
_CONTINUATION_TOKENS_FR: tuple[str, ...] = (
    "de", "du", "des", "au", "aux", "à", "en", "avec", "pour", "par",
    "sur", "sous", "entre", "vers", "chez",
    "et", "ou", "mais", "que", "qui", "quand", "pendant", "si",
    "le", "la", "les", "un", "une", "des",
)
_CONTINUATION_TOKENS_DE: tuple[str, ...] = (
    "von", "vom", "zur", "zum", "am", "im", "in", "mit", "bei", "auf",
    "für", "über", "unter", "gegen",
    "und", "oder", "aber", "dass", "wenn", "weil", "während",
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
)

_CONTINUATION_TOKENS_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": _CONTINUATION_TOKENS_EN,
    "it": _CONTINUATION_TOKENS_IT,
    "es": _CONTINUATION_TOKENS_ES,
    "fr": _CONTINUATION_TOKENS_FR,
    "de": _CONTINUATION_TOKENS_DE,
}

# Trailing punctuation we strip before testing the last token. We keep a
# trailing period because the typical Whisper false-stop is "to." / "going
# to.", so we MUST be able to look past the dot.
_TRAILING_PUNCT_RE = re.compile(r"[\s\.,;:?!\"\'\)\]\}…]+$")


def split_on_punctuation(
    segments: list[dict],
    min_duration: float = 1.0,
) -> list[dict]:
    """Split segments on strong sentence punctuation while preserving timing."""
    pattern = re.compile(rf"([{re.escape(END_PUNCT_CHARS)}]+)(\s*)(?=\S)")

    out: list[dict] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        start = float(seg["start"])
        end = float(seg["end"])
        duration = max(end - start, 1e-6)
        if not text or duration < 2 * min_duration:
            out.append(seg)
            continue

        cuts: list[int] = []
        for match in pattern.finditer(text):
            next_idx = match.end()
            if next_idx >= len(text):
                continue
            next_ch = text[next_idx]
            ws_between = match.group(2)
            is_latin = next_ch.isascii() and next_ch.isalpha()
            if is_latin:
                if ws_between and next_ch.isupper():
                    cuts.append(next_idx)
            elif not next_ch.isascii():
                cuts.append(next_idx)

        if not cuts:
            out.append(seg)
            continue

        pieces: list[tuple[str, int]] = []
        prev = 0
        for cut in cuts:
            piece = text[prev:cut].strip()
            if piece:
                pieces.append((piece, cut))
            prev = cut
        tail = text[prev:].strip()
        if tail:
            pieces.append((tail, len(text)))

        if len(pieces) <= 1:
            out.append(seg)
            continue

        total_chars = len(text)
        sub_segments: list[dict] = []
        prev_char = 0
        for piece_text, char_end in pieces:
            sub_start = start + duration * (prev_char / total_chars)
            sub_end = start + duration * (char_end / total_chars)
            if sub_end - sub_start < min_duration:
                if sub_segments:
                    sub_segments[-1]["end"] = sub_end
                    sub_segments[-1]["text"] = (
                        sub_segments[-1]["text"] + " " + piece_text
                    ).strip()
                    prev_char = char_end
                    continue
                sub_segments = []
                break
            new_seg = {"start": sub_start, "end": sub_end, "text": piece_text}
            if "speaker" in seg:
                new_seg["speaker"] = seg["speaker"]
            sub_segments.append(new_seg)
            prev_char = char_end

        if sub_segments and len(sub_segments) > 1:
            out.extend(sub_segments)
        else:
            out.append(seg)

    return out


def merge_short_segments(
    segments: list[dict],
    min_duration: float = 3.0,
    max_gap: float = 2.0,
    max_merged_duration: float = 20.0,
    aggressive: bool = False,
    verbose: bool = False,
) -> list[dict]:
    """Merge short adjacent segments and terminal orphan fragments."""
    if aggressive:
        min_duration = max(min_duration, 4.0)
        max_gap = max(max_gap, 1.5)
        max_merged_duration = max(max_merged_duration, 30.0)
    if not segments:
        return segments

    merged: list[dict] = []
    for seg in segments:
        if not merged:
            merged.append(dict(seg))
            continue
        prev = merged[-1]
        prev_dur = prev["end"] - prev["start"]
        gap = seg["start"] - prev["end"]
        same_speaker = prev.get("speaker") == seg.get("speaker")
        new_dur = seg["end"] - prev["start"]
        if (
            prev_dur < min_duration
            and gap <= max_gap
            and gap >= -0.5
            and same_speaker
            and new_dur <= max_merged_duration
        ):
            prev["end"] = max(prev["end"], seg["end"])
            prev["text"] = (prev.get("text", "") + " " + seg.get("text", "")).strip()
            if "words" in prev or "words" in seg:
                prev["words"] = prev.get("words", []) + seg.get("words", [])
        else:
            merged.append(dict(seg))

    final: list[dict] = []
    for idx, seg in enumerate(merged):
        if idx == 0 or not final:
            final.append(seg)
            continue
        prev = final[-1]
        text = (seg.get("text", "") or "").strip()
        n_words = len(text.split()) if text else 0
        ends_with_terminal = bool(text) and text[-1] in ".?!"
        same_speaker = prev.get("speaker") == seg.get("speaker")
        gap = seg["start"] - prev["end"]
        new_dur = seg["end"] - prev["start"]
        is_orphan = (
            n_words > 0
            and n_words <= 5
            and ends_with_terminal
            and same_speaker
            and gap <= 3.0
            and gap >= -0.5
            and new_dur <= 25.0
        )
        if is_orphan:
            if verbose:
                print(
                    f"[merge] orphan merged into previous: '{text}' "
                    f"(gap={gap:.2f}s, words={n_words})",
                    flush=True,
                )
            prev["end"] = max(prev["end"], seg["end"])
            prev["text"] = (prev.get("text", "") + " " + seg.get("text", "")).strip()
            if "words" in prev or "words" in seg:
                prev["words"] = prev.get("words", []) + seg.get("words", [])
        else:
            final.append(seg)
    return final


def _estimate_ratio(
    seg: dict,
    target_lang_code: str,
    expansion_factor: float,
) -> float:
    """Estimate the pre-stretch ratio for a single segment.

    The formula mirrors the budget used in :mod:`ollama_length_control`:
    ``(src_chars × expansion_factor) / (slot_s × cps_target)``. Returns
    0.0 for degenerate inputs (no text or non-positive slot) so callers
    can simply skip them.
    """
    text = (seg.get("text") or "").strip()
    if not text:
        return 0.0
    slot = float(seg.get("end", 0.0)) - float(seg.get("start", 0.0))
    if slot <= 0:
        return 0.0
    cps = chars_per_second_for(target_lang_code)
    if cps <= 0:
        return 0.0
    expected_chars = len(text) * max(expansion_factor, 0.0)
    return expected_chars / (slot * cps)


def expand_tight_slots(
    segments: list[dict],
    target_lang_code: str,
    expansion_factor: float = 1.0,
    tight_ratio_threshold: float = 1.50,
    max_gap_steal_s: float = 1.5,
    min_gap_keep_s: float = 0.15,
    max_neighbor_steal_s: float = 0.5,
    neighbor_easy_ratio: float = 0.80,
    bidirectional: bool = True,
) -> list[dict]:
    """Extend "tight" segments by borrowing time from silent gaps and easy neighbors.

    Pure function: returns a NEW list of dicts; the input ``segments`` and
    its dict elements are never mutated. Only ``start`` and ``end`` are
    adjusted on the copies — text and metadata are preserved verbatim, so
    no translation is invalidated.

    Strategy (per segment ``i`` whose expected ratio exceeds
    ``tight_ratio_threshold``); steps are tried in order and each subsequent
    step runs only if the segment is still tight after the previous one:

    Step 1 — forward gap stealing (silent gap ``[i].end → [i+1].start``)
        If the gap exceeds ``2 × min_gap_keep_s``, steal up to
        ``min(gap - min_gap_keep_s, max_gap_steal_s)`` seconds by
        extending ``segments[i].end``.

    Step 1b — backward gap stealing (silent gap ``[i-1].end → [i].start``)
        Symmetric to Step 1: if the gap exceeds ``2 × min_gap_keep_s``,
        anticipate ``segments[i].start`` by stealing the silence (the
        previous end is preserved so the conserved gap shrinks but
        never disappears). Skipped for the first segment and when
        ``bidirectional=False``.

    Step 2 — forward neighbor borrowing
        If still tight AND ``segments[i+1]`` is "easy" (expected ratio
        below ``neighbor_easy_ratio``), steal up to
        ``max_neighbor_steal_s`` from the start of the next slot. Both
        ``segments[i].end`` and ``segments[i+1].start`` shift by the
        same delta so the boundary moves but no overlap is created.

    Step 2b — backward neighbor borrowing
        Symmetric to Step 2: if still tight AND ``segments[i-1]`` is
        "easy" (using its CURRENT slot, i.e. post any prior cessions),
        steal up to ``max_neighbor_steal_s`` from the tail of the
        previous slot. Both ``segments[i-1].end`` and ``segments[i].start``
        shift by the same delta. Skipped for the first segment and when
        ``bidirectional=False``.

    Order of tentatives: 1 → 1b → 2 → 2b — silent gaps are tried before
    invasive neighbor stealing because they don't compete with another
    segment's slot.

    Edge cases:
      * empty input → returns ``[]``
      * single segment → returned unchanged (no neighbor, no gap)
      * first segment ``i = 0`` → no Step 1b nor 2b
      * last segment ``i = N-1`` → no Step 1 nor 2
      * already-loose segments (ratio ≤ tight) → untouched
      * tiny gaps (below ``2 × min_gap_keep_s``) → skipped to keep a
        natural breath pause
      * non-positive slot or empty text → skipped (defensive)
      * cumulative shift: the loop runs left-to-right and uses the
        CURRENT ``[i-1]`` slot (post-previous-modifications) so a
        segment that already ceded time to ``[i-2]`` is correctly
        evaluated as smaller before considering further cessions.

    Set ``bidirectional=False`` to restore the pre-2O behaviour (Step 1 +
    Step 2 only, forward-direction borrowing). The CLI flag
    ``--no-slot-expansion`` disables the whole function (no call site
    invokes it at all).
    """
    if not segments:
        return []
    out: list[dict] = [dict(seg) for seg in segments]
    n = len(out)
    if n < 2:
        return out

    cps = chars_per_second_for(target_lang_code)

    def _ratio_now(seg: dict) -> float:
        """Recompute the expected pre-stretch ratio using the current
        ``start``/``end`` of ``seg``. Returns 0.0 for degenerate inputs."""
        text_now = (seg.get("text") or "").strip()
        if not text_now:
            return 0.0
        slot_now = float(seg.get("end", 0.0)) - float(seg.get("start", 0.0))
        if slot_now <= 0 or cps <= 0:
            return 0.0
        return (len(text_now) * max(expansion_factor, 0.0)) / (slot_now * cps)

    for i in range(n):
        cur = out[i]
        cur_start = float(cur.get("start", 0.0))
        cur_end = float(cur.get("end", 0.0))

        if cur_end - cur_start <= 0:
            continue

        cur_ratio = _ratio_now(cur)
        if cur_ratio <= tight_ratio_threshold:
            continue

        # ---- Step 1: forward gap stealing -------------------------------
        if i + 1 < n:
            nxt = out[i + 1]
            nxt_start = float(nxt.get("start", 0.0))
            gap_fwd = nxt_start - cur_end
            if gap_fwd > 2 * min_gap_keep_s:
                steal = min(gap_fwd - min_gap_keep_s, max_gap_steal_s)
                if steal > 0:
                    cur_end += steal
                    cur["end"] = cur_end
                    if _ratio_now(cur) <= tight_ratio_threshold:
                        continue

        # ---- Step 1b: backward gap stealing -----------------------------
        if bidirectional and i - 1 >= 0:
            prv = out[i - 1]
            prv_end = float(prv.get("end", 0.0))
            gap_bwd = cur_start - prv_end
            if gap_bwd > 2 * min_gap_keep_s:
                steal = min(gap_bwd - min_gap_keep_s, max_gap_steal_s)
                if steal > 0:
                    cur_start -= steal
                    cur["start"] = cur_start
                    if _ratio_now(cur) <= tight_ratio_threshold:
                        continue

        # ---- Step 2: forward neighbor borrowing -------------------------
        if i + 1 < n:
            nxt = out[i + 1]
            nxt_start = float(nxt.get("start", 0.0))
            nxt_end = float(nxt.get("end", 0.0))
            nxt_slot = nxt_end - nxt_start
            if nxt_slot > 0 and cps > 0:
                nxt_ratio = _ratio_now(nxt)
                if 0.0 < nxt_ratio < neighbor_easy_ratio:
                    nxt_text = (nxt.get("text") or "").strip()
                    if nxt_text:
                        expected_chars_nxt = (
                            len(nxt_text) * max(expansion_factor, 0.0)
                        )
                        denom = tight_ratio_threshold * cps
                        if denom > 0:
                            slot_at_tight = expected_chars_nxt / denom
                            spare = max(0.0, nxt_slot - slot_at_tight)
                            steal_n = min(max_neighbor_steal_s, spare)
                            steal_n = min(steal_n, max(0.0, nxt_slot - 0.1))
                            if steal_n > 0:
                                cur_end += steal_n
                                nxt_start += steal_n
                                cur["end"] = cur_end
                                nxt["start"] = nxt_start
                                if _ratio_now(cur) <= tight_ratio_threshold:
                                    continue

        # ---- Step 2b: backward neighbor borrowing -----------------------
        if bidirectional and i - 1 >= 0:
            prv = out[i - 1]
            prv_start = float(prv.get("start", 0.0))
            prv_end = float(prv.get("end", 0.0))
            prv_slot = prv_end - prv_start
            if prv_slot > 0 and cps > 0:
                prv_ratio = _ratio_now(prv)
                if 0.0 < prv_ratio < neighbor_easy_ratio:
                    prv_text = (prv.get("text") or "").strip()
                    if prv_text:
                        expected_chars_prv = (
                            len(prv_text) * max(expansion_factor, 0.0)
                        )
                        denom = tight_ratio_threshold * cps
                        if denom > 0:
                            slot_at_tight = expected_chars_prv / denom
                            spare = max(0.0, prv_slot - slot_at_tight)
                            steal_n = min(max_neighbor_steal_s, spare)
                            steal_n = min(steal_n, max(0.0, prv_slot - 0.1))
                            if steal_n > 0:
                                cur_start -= steal_n
                                prv_end -= steal_n
                                cur["start"] = cur_start
                                prv["end"] = prv_end

    return out


def _last_word(text: str) -> str:
    """Return the last whitespace-separated word of ``text`` with trailing
    punctuation stripped. Empty string if no alphabetic content remains."""
    stripped = _TRAILING_PUNCT_RE.sub("", text or "").rstrip()
    if not stripped:
        return ""
    parts = stripped.split()
    if not parts:
        return ""
    last = parts[-1]
    # Strip leading punctuation too (e.g. opening quote on a single token).
    return last.lstrip("\"'([{").rstrip("\"'.,;:?!)]}…")


def _starts_with_proper_capital(text: str) -> bool:
    """Return True when ``text`` starts with an uppercase letter that is
    *not* the English standalone "I" / "I'm" / "I'll" — those are legitimate
    lowercase-equivalents at sentence start that should not block joining.
    """
    s = (text or "").lstrip()
    if not s:
        return False
    first = s[0]
    if not first.isalpha() or not first.isupper():
        return False
    if s == "I" or s.startswith("I ") or s.startswith("I'"):
        return False
    return True


def _should_join(
    seg_i: dict,
    seg_next: dict,
    max_gap: float,
    tokens: tuple[str, ...],
) -> bool:
    """Decide whether ``seg_i`` and ``seg_next`` are halves of the same
    sentence wrongly cut by Whisper. See :func:`repair_split_sentences`
    for the full set of conditions."""
    text_i = (seg_i.get("text") or "").strip()
    text_next = (seg_next.get("text") or "").strip()
    if not text_i or not text_next:
        return False

    # Different speakers → always keep them split.
    if seg_i.get("speaker") != seg_next.get("speaker"):
        return False

    # Gap budget: only join when the segments are nearly contiguous.
    try:
        gap = float(seg_next["start"]) - float(seg_i["end"])
    except (KeyError, TypeError, ValueError):
        return False
    if gap > max_gap:
        return False

    # Continuation token at the end of seg_i?
    last = _last_word(text_i).lower()
    if not last or last not in tokens:
        return False

    # Capitalised continuation (other than "I" / "I'm") usually means a
    # NEW sentence began — don't merge in that case. Lowercase continuation
    # is the strongest possible signal of a mid-clause cut.
    if _starts_with_proper_capital(text_next):
        return False

    return True


def repair_split_sentences(
    segments: list[dict],
    max_join_gap_s: float = 0.5,
    src_lang_hint: str = "en",
) -> list[dict]:
    """Detect Whisper segmentation that broke sentences mid-clause and
    join the offending pairs back into single segments.

    Pure function: returns a NEW list, never mutates input. Each output
    dict is also a fresh copy. ``text`` (and ``text_tgt`` if present) are
    concatenated when joining; ``start`` of the left segment and ``end``
    of the right segment are kept; ``speaker`` is preserved when equal
    on both sides (segments with different speakers are never merged).

    Heuristic: a segment ending with a continuation token (preposition,
    article, conjunction, subordinator) AND a follow-up segment starting
    in lowercase (or with the English standalone "I"/"I'm") AND a small
    inter-segment gap is almost always a Whisper false-stop.

    ``src_lang_hint`` selects the token list. Unknown / multi-region
    codes (e.g. ``"en-US"``, ``"auto"``) fall back to English, which is
    the safest default since false-stops on the English ASR are by far
    the most common pattern reported.

    The merge is **cascading**: if a join produces a new segment whose
    new tail still ends in a continuation token AND the segment after
    matches all conditions too, the chain is collapsed in one go.

    Returns a same-or-shorter list.
    """
    if not segments:
        return []

    # Defensive copy so we never mutate caller dicts.
    work: list[dict] = [dict(s) for s in segments]
    if len(work) < 2:
        return work

    # Resolve token list once. Strip region tag so "en-US" behaves like "en".
    base_lang = (src_lang_hint or "en").split("-")[0].lower()
    tokens = _CONTINUATION_TOKENS_BY_LANG.get(
        base_lang, _CONTINUATION_TOKENS_EN
    )

    out: list[dict] = []
    i = 0
    n = len(work)
    while i < n:
        cur = dict(work[i])  # working copy we may extend in-place
        j = i + 1
        while j < n and _should_join(cur, work[j], max_join_gap_s, tokens):
            nxt = work[j]
            # Concatenate text with a single space.
            cur_text = (cur.get("text") or "").strip()
            nxt_text = (nxt.get("text") or "").strip()
            if cur_text and nxt_text:
                cur["text"] = cur_text + " " + nxt_text
            elif nxt_text:
                cur["text"] = nxt_text
            # Preserve text_tgt symmetrically if a caller already attached one.
            if "text_tgt" in cur or "text_tgt" in nxt:
                cur_tgt = (cur.get("text_tgt") or "").strip()
                nxt_tgt = (nxt.get("text_tgt") or "").strip()
                merged_tgt = (cur_tgt + " " + nxt_tgt).strip()
                if merged_tgt:
                    cur["text_tgt"] = merged_tgt
            # Extend the time slot to cover both segments.
            try:
                cur["end"] = max(float(cur["end"]), float(nxt["end"]))
            except (KeyError, TypeError, ValueError):
                cur["end"] = nxt.get("end", cur.get("end"))
            # Keep words list contiguous if either side carried one.
            if "words" in cur or "words" in nxt:
                cur["words"] = list(cur.get("words", [])) + list(
                    nxt.get("words", [])
                )
            j += 1
        out.append(cur)
        i = j
    return out

