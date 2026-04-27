"""Subtitle and Whisper segment manipulation helpers."""

import re

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

