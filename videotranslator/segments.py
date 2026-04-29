"""Subtitle and Whisper segment manipulation helpers."""

import re

from videotranslator.ollama_length_control import chars_per_second_for

END_PUNCT_CHARS = r".?!;。？！；؟"


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
) -> list[dict]:
    """Extend "tight" segments by borrowing time from silent gaps and easy neighbors.

    Pure function: returns a NEW list of dicts; the input ``segments`` and
    its dict elements are never mutated. Only ``start`` and ``end`` are
    adjusted on the copies — text and metadata are preserved verbatim, so
    no translation is invalidated.

    Strategy (per segment ``i`` whose expected ratio exceeds
    ``tight_ratio_threshold``):

    Step 1 — gap stealing
        ``gap = segments[i+1].start - segments[i].end``. If the gap exceeds
        ``2 × min_gap_keep_s``, steal up to
        ``min(gap - min_gap_keep_s, max_gap_steal_s)`` seconds of silence
        by extending ``segments[i].end`` (the next start is left alone, so
        the conserved gap shrinks but never disappears).

    Step 2 — neighbor borrowing
        If the segment is still tight after Step 1 AND ``segments[i+1]`` is
        "easy" (its expected ratio is below ``neighbor_easy_ratio``), steal
        up to ``max_neighbor_steal_s`` seconds from the start of the next
        slot. Both ``segments[i].end`` and ``segments[i+1].start`` shift
        by the same delta so the boundary moves but no overlap is created.

    Edge cases:
      * empty input → returns ``[]``
      * single segment → returned unchanged (no neighbor, no gap)
      * tail segment (last) → only Step 1 (no neighbor for borrowing) and
        only when followed by a gap, which doesn't apply for the last one;
        the last segment is therefore left as-is
      * already-loose segments (ratio ≤ tight) → untouched
      * tiny gaps (below ``2 × min_gap_keep_s``) → skipped to keep a
        natural breath pause
      * non-positive slot or empty text → skipped (defensive)

    The function intentionally does NOT cascade: each segment is evaluated
    once against its right neighbor, so timestamps cannot drift across many
    successive borrowings within a single call.
    """
    if not segments:
        return []
    out: list[dict] = [dict(seg) for seg in segments]
    n = len(out)
    if n < 2:
        return out

    for i in range(n - 1):
        cur = out[i]
        nxt = out[i + 1]
        cur_start = float(cur.get("start", 0.0))
        cur_end = float(cur.get("end", 0.0))
        nxt_start = float(nxt.get("start", 0.0))
        nxt_end = float(nxt.get("end", 0.0))

        slot = cur_end - cur_start
        if slot <= 0:
            continue

        cur_ratio = _estimate_ratio(cur, target_lang_code, expansion_factor)
        if cur_ratio <= tight_ratio_threshold:
            continue

        delta_total = 0.0

        # Step 1: steal from silent gap to the next segment.
        gap = nxt_start - cur_end
        if gap > 2 * min_gap_keep_s:
            steal = min(gap - min_gap_keep_s, max_gap_steal_s)
            if steal > 0:
                cur_end += steal
                delta_total += steal

        # Recompute current ratio with the new end before deciding on
        # neighbor borrowing. If we already brought the slot below tight,
        # leave the neighbor alone.
        new_slot = cur_end - cur_start
        text = (cur.get("text") or "").strip()
        if not text or new_slot <= 0:
            cur["end"] = cur_end
            continue
        cps = chars_per_second_for(target_lang_code)
        if cps <= 0:
            cur["end"] = cur_end
            continue
        cur_ratio_after_gap = (
            len(text) * max(expansion_factor, 0.0)
        ) / (new_slot * cps)

        # Step 2: borrow from an "easy" neighbor's slot.
        if cur_ratio_after_gap > tight_ratio_threshold:
            nxt_slot = nxt_end - nxt_start
            if nxt_slot > 0:
                nxt_ratio = _estimate_ratio(nxt, target_lang_code, expansion_factor)
                if 0.0 < nxt_ratio < neighbor_easy_ratio:
                    # Don't strip the neighbor below its own tight threshold.
                    # The maximum we could take while keeping nxt under tight
                    # is the slot reduction that pushes its ratio toward tight.
                    nxt_text = (nxt.get("text") or "").strip()
                    if nxt_text:
                        # Slot at which nxt would hit tight_ratio_threshold:
                        #   slot_at_tight = expected_chars / (tight × cps)
                        # Anything above slot_at_tight is "spare" time.
                        expected_chars_nxt = len(nxt_text) * max(expansion_factor, 0.0)
                        denom = tight_ratio_threshold * cps
                        if denom > 0:
                            slot_at_tight = expected_chars_nxt / denom
                            spare = max(0.0, nxt_slot - slot_at_tight)
                            steal_n = min(max_neighbor_steal_s, spare)
                            # Never borrow more than the neighbor slot itself.
                            steal_n = min(steal_n, max(0.0, nxt_slot - 0.1))
                            if steal_n > 0:
                                cur_end += steal_n
                                nxt_start += steal_n
                                delta_total += steal_n
                                nxt["start"] = nxt_start

        if delta_total > 0:
            cur["end"] = cur_end

    return out

