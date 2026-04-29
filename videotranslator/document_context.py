"""Document-level context helper for Ollama-based dubbing translation.

Pure helpers (no I/O, no globals) so they can be unit-tested without a running
Ollama daemon.

Today every segment is translated with its immediate neighbours (prev/next)
as a local CONTEXT block (see :mod:`videotranslator.ollama_prompt`). On long
videos (>5 min) this still loses GLOBAL coherence: technical terminology
oscillates ("Ctrl+C" vs "Control V"), tone drifts segment by segment, and
discourse-level anaphora is resolved poorly (a "he" 3 minutes later refers
to a person introduced once at the start).

The fix implemented here, TASK 2K, is dirt-cheap and high-leverage:

1. Before the per-segment translation loop, concatenate the whole transcript
   and ask Ollama for ONE short semantic summary in the target language,
   listing the technical terms to preserve verbatim (brand names, CLI
   commands, API identifiers, …).
2. Inject that summary into EVERY per-segment prompt as a
   ``GLOBAL CONTEXT (do not translate, only for understanding)`` block,
   ABOVE the existing local prev/next CONTEXT block.

Cost: +1 Ollama call up front (~30–90s with thinking, ~5–15s without).
Benefit: terminology and tone anchored across the whole video instead of
drifting freely.

This module exposes only the prompt builder for the summary call and a tiny
gating heuristic — the actual call to Ollama lives in the legacy GUI module
where the HTTP client and timeouts are already wired.
"""

from __future__ import annotations


# Hard cap on how much source transcript we feed to the summarisation
# prompt. Ollama (qwen3:8b) handles ~32k tokens, but a 30-min video at
# ~150 wpm produces ~4500 words ~= 25k chars, which fits comfortably.
# We cap defensively at 60k chars to leave headroom for the instruction
# wrapper itself and for very long lecture-style content. Beyond this
# we DROP THE TAIL and keep the head (the opening of a video usually
# carries the most terminology / topic framing — "in this video we'll
# cover X, Y, Z" — so keeping the head is more useful than keeping the
# tail). Implementation matches: ``transcript[:max_chars]``.
SUMMARY_TRANSCRIPT_MAX_CHARS: int = 60_000

# Default budget for the summary itself, in words. 300 words = ~1500-2000
# chars depending on the language; small enough that injecting it in every
# per-segment prompt only adds ~10-15% to the prompt size, large enough
# to carry topic, tone, and a glossary of technical terms.
SUMMARY_DEFAULT_MAX_WORDS: int = 300

# Minimum number of segments before document-level context is worth its
# +1 Ollama call. On a 4-segment clip the local prev/next CONTEXT already
# sees the whole video, so the summary adds latency without insight.
SUMMARY_MIN_SEGMENTS: int = 5


def is_summary_useful(
    segments: list[dict] | None,
    min_segments: int = SUMMARY_MIN_SEGMENTS,
) -> bool:
    """Return True when the transcript is long enough for a global summary.

    Pure helper: the caller decides what to do when this returns False
    (typically: skip the summary call and translate with local context only).

    Empty / None inputs always return False so the caller does not have to
    pre-validate. ``min_segments`` is configurable for tests; the default
    of 5 segments was picked empirically — at 4 or fewer the local
    prev/next window already covers the full video.
    """
    if not segments:
        return False
    if min_segments <= 0:
        return True
    return len(segments) >= min_segments


def _concat_transcript(segments: list[dict]) -> str:
    """Join all segment texts into a single transcript string.

    Whitespace is normalised: each segment text is stripped, empty
    segments are skipped, and lines are joined with a single space so the
    resulting blob reads like prose. The summary model does not need
    timestamps.
    """
    parts: list[str] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def _truncate_transcript(
    transcript: str,
    max_chars: int = SUMMARY_TRANSCRIPT_MAX_CHARS,
) -> str:
    """Cap the transcript at ``max_chars`` from the head.

    See module docstring for why we keep the head, not the tail.
    """
    if max_chars <= 0:
        return ""
    if len(transcript) <= max_chars:
        return transcript
    return transcript[:max_chars]


def build_summary_prompt(
    segments: list[dict],
    target_lang_name: str,
    src_lang_name: str,
    *,
    is_qwen3: bool = False,
    thinking: bool = False,
    max_words: int = SUMMARY_DEFAULT_MAX_WORDS,
) -> str:
    """Build the Ollama prompt that produces the document-level summary.

    Strategy
    --------
    * Concatenate every segment's source text into a single transcript blob
      and truncate it from the head to ``SUMMARY_TRANSCRIPT_MAX_CHARS``.
    * Ask the model to produce a summary in ``target_lang_name``, capped at
      ``max_words`` words, that explicitly lists the technical terms /
      proper nouns / CLI tokens / brand names that must be preserved
      verbatim across the whole translation.
    * Mark the output as "context only — do not translate the transcript",
      so a model that "helpfully" tries to translate the whole thing
      instead of summarising it gets one extra chance to comply.

    The returned prompt is a plain string ready for ``/api/generate``.

    Qwen3 toggle
    ------------
    Mirrors :func:`videotranslator.ollama_prompt.build_translation_prompt`:
    Qwen3 + thinking → no suffix (let the model deliberate);
    Qwen3 + non-thinking → append ``/no_think`` to suppress the
    ``<think>`` block; non-Qwen3 → no suffix at all.

    Notes
    -----
    Returns an empty string when the transcript is empty (defensive: the
    caller should already have gated via :func:`is_summary_useful`, but
    this keeps the function safe to call unconditionally).
    """
    transcript = _concat_transcript(segments or [])
    transcript = _truncate_transcript(transcript)
    if not transcript:
        return ""

    # Words cap defensive floor: <50 words is not enough for terminology
    # listing; the caller probably mis-passed ``max_words=0``.
    effective_max_words = max(50, int(max_words)) if max_words else SUMMARY_DEFAULT_MAX_WORDS

    prompt = (
        f"You are a translation assistant. Read the following {src_lang_name} transcript "
        f"and produce a short SEMANTIC SUMMARY in {target_lang_name} that will be used "
        f"as a global glossary / context guide for the segment-by-segment dubbing "
        f"translation that follows.\n\n"
        f"REQUIREMENTS:\n"
        f"1. Maximum {effective_max_words} words.\n"
        f"2. Capture the topic, the speaker's tone (formal/casual/technical), and "
        f"the main entities / proper nouns.\n"
        f"3. Explicitly list the technical terms, brand names, product names, CLI "
        f"commands, API identifiers, file paths and acronyms that MUST be PRESERVED "
        f"VERBATIM in the translation (do NOT translate them — keep them in the "
        f"original language). Examples to look for: programming languages, software "
        f"names, keyboard shortcuts (Ctrl+C, Cmd+V), URLs, model names.\n"
        f"4. Use natural {target_lang_name}; this summary itself will not be spoken, "
        f"only read by another LLM as a context anchor.\n"
        f"5. Output ONLY the summary. No preamble, no quotes, no markdown headers, "
        f"no chain-of-thought.\n\n"
        f"{src_lang_name} transcript (for understanding only — DO NOT translate it "
        f"verbatim, only summarise):\n"
        f"{transcript}\n\n"
        f"{target_lang_name} summary (max {effective_max_words} words, glossary-style):\n"
    )

    # Same Qwen3 /no_think contract as build_translation_prompt: when the
    # user explicitly opted INTO thinking we omit the suffix so the model
    # can actually deliberate; otherwise we suppress <think> which would
    # otherwise leak into the summary text and confuse downstream prompts.
    if is_qwen3 and not thinking:
        prompt = prompt.rstrip() + "\n\n/no_think"

    return prompt
