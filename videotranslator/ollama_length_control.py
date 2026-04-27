"""Length control helpers for Ollama-based dubbing translation.

Pure helpers (no I/O) so they can be unit-tested without a running daemon.

The dubbing pipeline asks the LLM for a translation and then has to fit that
translation into a fixed audio slot. When a translation overshoots the slot
duration, the downstream ffmpeg ``atempo`` filter accelerates the spoken
audio so much that listeners hear chipmunk artefacts. The cleanest fix is
to ask the LLM to rewrite that specific segment shorter, with the budget
made explicit in the prompt.

This module provides three building blocks used by ``_translate_with_ollama``:

* :func:`compute_target_chars` — given the audio slot duration and the
  target language, how many characters does the translation need to stay
  under to fit?
* :func:`should_reprompt_for_length` — is the first translation long enough
  over the target that a re-prompt is worth the extra Ollama round-trip?
* :func:`build_rewrite_shorter_prompt` — construct the explicit "rewrite
  shorter" prompt, including the previous translation and the numeric budget.

The target is computed from the slot duration, NOT from the source character
count. The proportional formula (src_chars × expansion) was tried first but
failed on segments where the source is dense in a short slot (e.g. 113 EN
chars in 4s): the proportional target became permissive while the spoken
budget was actually tight, and the re-prompt did not fire.
"""

from __future__ import annotations


# Average characters-per-second of natural spoken speech, by ISO language
# code. These are empirical averages calibrated against XTTS v2 output:
# logographic scripts (zh/ja/ko) pack much more meaning per character so
# their char/sec is far lower; Romance languages with many open syllables
# sit around 14–16; Germanic and Slavic compound-heavy languages sit lower
# around 12–14. The default 14.0 is a safe middle ground for unmapped
# languages.
_CHARS_PER_SECOND_BY_LANG: dict[str, float] = {
    "en": 14.0,
    "it": 15.0, "es": 16.0, "pt": 14.5, "fr": 14.0, "ro": 14.5,
    "de": 13.5, "nl": 13.5, "sv": 13.5, "da": 14.0, "no": 14.0,
    "pl": 13.0, "cs": 13.0, "el": 13.0, "tr": 13.5, "hu": 12.5,
    "ru": 12.5, "uk": 12.5, "fi": 12.0,
    "ar": 13.0, "hi": 13.0, "id": 14.5,
    # Logographic / syllabary scripts: each character carries far more
    # phonetic content, so chars/sec is much lower.
    "zh": 6.0, "ja": 7.0, "ko": 8.0,
}

DEFAULT_CHARS_PER_SECOND: float = 14.0


def chars_per_second_for(target_lang_code: str) -> float:
    """Lookup the speech-rate constant for a language code.

    Accepts both pure ISO codes ("it") and locale-style ("it-IT"); the
    region suffix is dropped before lookup. Unknown codes fall back to
    :data:`DEFAULT_CHARS_PER_SECOND`.
    """
    if not target_lang_code:
        return DEFAULT_CHARS_PER_SECOND
    code = target_lang_code.lower().split("-")[0]
    return _CHARS_PER_SECOND_BY_LANG.get(code, DEFAULT_CHARS_PER_SECOND)


def compute_target_chars(
    slot_s: float,
    target_lang_code: str,
    slack: float = 1.10,
) -> int:
    """Character budget that fits the spoken audio in ``slot_s`` seconds.

    The budget is ``slot_s × chars_per_second(target_lang) × slack``,
    floored at 50 to avoid retrying on micro-segments where any small
    rounding would otherwise trigger.

    ``slack`` is a tolerance multiplier (default 1.10 = +10% over the
    natural-rate budget); paired with :func:`should_reprompt_for_length`'s
    own threshold it controls how aggressively re-prompts fire. Returns
    50 if any input is non-positive (defensive default).
    """
    if slot_s <= 0 or slack <= 0:
        return 50
    cps = chars_per_second_for(target_lang_code)
    return max(50, int(slot_s * cps * slack))


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
