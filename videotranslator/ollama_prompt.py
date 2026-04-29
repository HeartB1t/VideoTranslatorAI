"""Prompt builder for Ollama-based dubbing translation.

Pure helpers (no I/O, no globals) so they can be unit-tested without a running
Ollama daemon.

The dubbing pipeline asks the LLM to translate one segment at a time. Whisper
splits utterances on punctuation/pause, so a single sentence frequently spans
two adjacent segments. Without context, the LLM sees only the fragment and
loses information needed for correct semantics: a stray word like ``stick``
at the start of a segment can be mistranslated as a noun (``bastoncino``)
when the preceding segment ended with ``...less likely to``.

This module provides :func:`build_translation_prompt`, which optionally
injects the previous and next segment text as a CONTEXT block. The CONTEXT
is explicitly marked as "for understanding only — do not translate" so the
model uses it for disambiguation but emits a translation only for the target
segment.

The function is intentionally parameter-heavy (every dynamic input is
explicit) so the caller — :func:`_translate_with_ollama` — can keep its
configuration logic and the builder stays a deterministic pure function
suitable for table-driven tests.
"""

from __future__ import annotations


# Hard cap on context snippet length. The CONTEXT block is for
# disambiguation only; passing the entire neighbouring segment when it is
# very long would inflate the prompt (slowing Ollama, eating context window
# budget) without a corresponding accuracy gain. 200 chars covers ~30-40
# words which is enough for sentence-completion context (the typical
# "...less likely to" → "stick. When I gave up..." case).
CONTEXT_SNIPPET_MAX_CHARS: int = 200


def _truncate_context(text: str | None) -> str:
    """Return ``text`` stripped and truncated to :data:`CONTEXT_SNIPPET_MAX_CHARS`.

    Returns an empty string when ``text`` is ``None`` or whitespace-only,
    so callers can safely use ``if snippet:`` to gate the CONTEXT block.
    """
    if not text:
        return ""
    s = text.strip()
    if not s:
        return ""
    if len(s) > CONTEXT_SNIPPET_MAX_CHARS:
        return s[:CONTEXT_SNIPPET_MAX_CHARS]
    return s


def build_translation_prompt(
    text: str,
    slot_s: float,
    src_name: str,
    tgt_name: str,
    *,
    slot_aware: bool = True,
    is_qwen3: bool = False,
    thinking: bool = False,
    prev_text: str | None = None,
    next_text: str | None = None,
    global_context: str | None = None,
) -> str:
    """Build the full Ollama translation prompt for a single segment.

    Parameters
    ----------
    text:
        The source segment to translate.
    slot_s:
        Audio slot duration in seconds. Used for the slot-aware reading-time
        clause when ``slot_aware`` is True and ``slot_s > 0``.
    src_name, tgt_name:
        Human-readable language names (e.g. ``"Italian"``, ``"English"``).
        These are interpolated verbatim into the prompt.
    slot_aware:
        When True the prompt includes a "target reading time" clause and a
        "~Xs" hint at the end. Disable for batch modes that do not need
        per-segment timing pressure.
    is_qwen3:
        When True the model is treated as Qwen3 family. Combined with
        ``thinking=False`` this appends the ``/no_think`` suffix to disable
        chain-of-thought emission.
    thinking:
        Qwen3 thinking mode toggle. Only meaningful when ``is_qwen3`` is True.
    prev_text, next_text:
        Optional adjacent segment text used as CONTEXT (for disambiguation
        only). When provided, both are truncated to
        :data:`CONTEXT_SNIPPET_MAX_CHARS` and inserted as a CONTEXT block
        before the requirements list. The LLM is explicitly instructed not
        to translate this material.
    global_context:
        Optional document-level summary of the whole transcript (TASK 2K).
        When provided, it is injected as a ``GLOBAL CONTEXT`` block ABOVE
        the local prev/next CONTEXT block so the model anchors terminology,
        tone and global anaphora across the whole video. The LLM is
        instructed not to translate this material.

    Returns
    -------
    str
        The fully-rendered prompt ready to POST to ``/api/generate``.
    """

    prev_snippet = _truncate_context(prev_text)
    next_snippet = _truncate_context(next_text)
    has_local_context = bool(prev_snippet) or bool(next_snippet)
    # Document-level context is just a stripped-non-empty check; no length
    # cap here because the whole point of the summary is to be present in
    # full on every prompt. The summary builder upstream caps the source
    # transcript before generation, so the summary is already bounded.
    global_snippet = (global_context or "").strip()
    has_global_context = bool(global_snippet)
    has_context = has_local_context or has_global_context

    # CONTEXT blocks — emitted only when there is something to say.
    # GLOBAL CONTEXT goes FIRST so the model reads the document-level
    # anchor before any local prev/next snippet. Both blocks share the
    # same "do not translate" framing.
    context_parts: list[str] = []
    if has_global_context:
        context_parts.append(
            "GLOBAL CONTEXT (entire video summary, for understanding only — DO NOT translate, "
            "only the target segment below):\n"
            f"{global_snippet}"
        )
    if has_local_context:
        local_lines = [
            "CONTEXT (for understanding only — DO NOT translate, only the target segment below):",
        ]
        if prev_snippet:
            local_lines.append(f"[Previous] {prev_snippet}")
        if next_snippet:
            local_lines.append(f"[Next] {next_snippet}")
        context_parts.append("\n".join(local_lines))
    if context_parts:
        context_block = "\n\n".join(context_parts) + "\n\n"
    else:
        context_block = ""

    slot_clause = ""
    if slot_aware and slot_s > 0:
        slot_clause = (
            f"2. Target reading time: approximately {slot_s:.1f} seconds when spoken aloud at normal pace.\n"
        )

    # When CONTEXT is present we tighten the wording on the source-text
    # marker so a model that "helpfully" tries to translate the surrounding
    # context is reminded one more time which fragment is the actual target.
    # Wording is split: with local prev/next we reference those tokens
    # explicitly (most common case, regression test relies on it); with
    # only the document-level summary we use a more generic phrasing.
    if has_local_context:
        target_marker = (
            f"{src_name} text TO TRANSLATE (only this, ignoring the [Previous]/[Next] context):\n"
        )
    elif has_global_context:
        target_marker = (
            f"{src_name} text TO TRANSLATE (only this, ignoring the GLOBAL CONTEXT above):\n"
        )
    else:
        target_marker = f"{src_name} text:\n"

    slot_hint = ""
    if slot_aware and slot_s > 0:
        slot_hint = f", ~{slot_s:.1f}s"

    prompt = (
        f"You are a professional dubbing translator. Translate the following {src_name} text to {tgt_name} for voice dubbing.\n\n"
        f"{context_block}"
        f"CRITICAL REQUIREMENTS:\n"
        f"1. Keep it CONCISE — {tgt_name} tends to be longer than {src_name}; your job is to compress while preserving meaning.\n"
        f"{slot_clause}"
        f"3. Use SPOKEN register, NOT formal/written language. Natural dubbing dialogue.\n"
        f"4. Drop filler words, redundant adverbs, verbose constructions where possible.\n"
        f"5. PRESERVE NEGATIONS exactly. If the source contains 'not', 'no', \"don't\", \"doesn't\", \"haven't\", \"can't\", \"won't\", \"isn't\", \"wasn't\", 'never', 'nobody', 'nothing', 'none', the {tgt_name} translation MUST contain the equivalent negation. NEVER drop or invert a negation. PRESERVE quantifiers (all/some/none/every/each) in the same logical sense.\n"
        f"6. Output ONLY the translated text. No explanations, no quotes, no preambles.\n\n"
        f"{target_marker}{text}\n\n"
        f"{tgt_name} translation (spoken, concise{slot_hint}):\n"
    )

    # Doppia safety: se l'API Ollama non interpreta `think:false` (versioni
    # pre-2025), il suffisso `/no_think` nel prompt è il toggle ufficiale
    # documentato da Qwen e vince comunque. Quando l'utente sceglie
    # esplicitamente la modalità thinking lo OMETTIAMO (altrimenti il toggle
    # `/no_think` annulla il think richiesto via API).
    if is_qwen3 and not thinking:
        prompt = prompt.rstrip() + "\n\n/no_think"

    return prompt
