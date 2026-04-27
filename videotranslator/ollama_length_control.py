"""Length control helpers for Ollama-based dubbing translation.

Pure helpers (no I/O) so they can be unit-tested without a running daemon.

The dubbing pipeline asks the LLM for a translation and then has to fit that
translation into a fixed audio slot. Languages expand at different rates
(EN→IT averages ~1.25x, EN→DE ~1.30x, etc.); when a single segment ends up
substantially over the expected expansion the downstream ffmpeg ``atempo``
filter accelerates the spoken audio so much that listeners hear chipmunk
artefacts. The cleanest fix is to ask the LLM to rewrite that specific
segment shorter, with the character budget made explicit in the prompt.

This module provides three building blocks used by ``_translate_with_ollama``:

* :func:`compute_target_chars` — given the source length and the language
  expansion factor, how many characters does the target translation need to
  stay under to fit a typical slot (with some slack)?
* :func:`should_reprompt_for_length` — is the first translation long enough
  over the target that a re-prompt is worth the extra Ollama round-trip?
* :func:`build_rewrite_shorter_prompt` — construct the explicit "rewrite
  shorter" prompt, including the previous translation and the numeric budget.

Defaults are conservative: re-prompt only when 10% over the slack-adjusted
target. That keeps the extra LLM calls focused on the few segments that
matter.
"""

from __future__ import annotations


def compute_target_chars(
    src_chars: int,
    expansion_factor: float,
    slack: float = 1.20,
) -> int:
    """Estimated character budget for the translation.

    ``expansion_factor`` reflects the average length ratio between target
    and source language (e.g. 1.25 for EN→IT). ``slack`` is the additional
    margin we tolerate on top of the average before considering the
    translation too long for the audio slot. The returned value is always
    at least ``50`` so that very short segments do not trigger a retry just
    because the floor is mathematically tiny.
    """
    if src_chars <= 0 or expansion_factor <= 0 or slack <= 0:
        return 50
    return max(50, int(src_chars * expansion_factor * slack))


def should_reprompt_for_length(
    translation_chars: int,
    target_chars: int,
    threshold: float = 1.10,
) -> bool:
    """Whether the first translation overshot the budget enough to retry.

    ``threshold`` is the multiplicative tolerance over ``target_chars``
    before a retry is triggered. Default 1.10 means we accept up to 10%
    over the target; beyond that we ask the model to shorten.
    """
    if target_chars <= 0 or threshold <= 0:
        return False
    return translation_chars > target_chars * threshold


def build_rewrite_shorter_prompt(
    first_translation: str,
    slot_s: float,
    target_chars: int,
    target_lang_name: str,
    is_qwen3: bool = False,
    thinking: bool = False,
) -> str:
    """Prompt asking the model to shorten its previous translation.

    The numeric budget (``target_chars``) and the slot duration are stated
    explicitly so the model has unambiguous targets. The output instruction
    mirrors the original translation prompt so ``_ollama_strip_preamble``
    can keep doing its job.

    On Qwen3 with non-thinking we still append the ``/no_think`` suffix as
    documented by the Qwen team; thinking mode omits it so the model can
    actually deliberate.
    """
    prompt = (
        f"The previous {target_lang_name} translation is too long for the audio slot.\n\n"
        f"Previous translation ({len(first_translation)} chars):\n"
        f"{first_translation}\n\n"
        f"REQUIREMENTS:\n"
        f"1. Rewrite shorter: maximum {target_chars} characters.\n"
        f"2. Target spoken duration: ~{slot_s:.1f} seconds.\n"
        f"3. Preserve the core meaning. Drop redundant adverbs, filler words, verbose constructions.\n"
        f"4. Use SPOKEN register, not formal/written language.\n"
        f"5. Output ONLY the shorter {target_lang_name} translation. No explanations, no quotes, no preambles.\n\n"
        f"Shorter {target_lang_name} translation:\n"
    )
    if is_qwen3 and not thinking:
        prompt = prompt.rstrip() + "\n\n/no_think"
    return prompt
