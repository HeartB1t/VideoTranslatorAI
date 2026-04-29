"""Chain-of-Verification (CoVe) for translation quality.

Implements the structured verification pattern from the ACL 2024 paper
'Chain-of-Verification Reduces Hallucination in Large Language Models'
adapted to MT validation.

After the LLM produces a candidate translation, a second prompt asks
the SAME model to verify specific quality criteria as isolated
yes/no questions (NOT open-ended self-reflection, which sometimes
produces false-positive "yes I dropped a negation" hallucinations
per arxiv 2406.10400).

Triggered only when the source text contains risk patterns (negations,
quantifiers) so we don't pay the latency tax on every segment.

The function shapes mirror :mod:`videotranslator.ollama_prompt` so the
caller in ``_translate_with_ollama`` can keep configuration logic local
and the builder stays a deterministic pure function suitable for
table-driven tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# Patterns that, when present in source, justify CoVe verification.
#
# Negation list covers the common English forms qwen3 statistically
# drops on EN→IT dubbing translation: "haven't" → "hai" (positive),
# "won't" → "vuoi" (modal flip). Italian negation auxiliaries ("non",
# "mai") are handled by the same regex so a reverse direction also
# triggers verification — most of the production usage is EN→IT today
# but the module must not silently degrade for IT→EN.
#
# We deliberately keep the list short and high-precision: every false
# positive here costs an extra Ollama call. Risk patterns we do NOT
# include (yet): conditionals, double negatives, sarcasm — they are
# either too noisy or already captured by the negation list itself.
# Note on n't: ``\b`` is a word boundary, but ``'`` is NOT a word
# character so ``\bn't\b`` would require a transition into a word
# character right before the ``n``. In contracted forms like
# ``haven't`` the ``n`` is preceded by ``e`` (word char), so the
# leading ``\b`` does NOT match. We therefore handle ``n't`` with an
# explicit ``(?<=[a-zA-Z])n't\b`` lookbehind so contractions trigger
# regardless of host verb (haven't, can't, won't, isn't, ...).
_NEGATION_PATTERN = re.compile(
    r"(?:\b("
    r"not|no|never|nobody|nothing|nowhere|none|neither|nor"
    r"|non|mai|nessuno|niente|nulla|né"
    r")\b)"
    r"|(?:(?<=[a-zA-Z])n't\b)",
    re.IGNORECASE,
)

# Quantifier list: words that change logical truth when dropped or
# softened. "all/some/none/every" are textbook MT failure modes —
# qwen3 sometimes paraphrases "all of them" as "loro" (just "them"),
# losing the universal quantifier. The list is intentionally narrow
# (no "few", "many", "most" by default — they are more often safely
# paraphrased than the strict quantifiers below).
_QUANTIFIER_PATTERN = re.compile(
    r"\b("
    r"all|every|everyone|everybody|everything|everywhere"
    r"|some|someone|somebody|something|somewhere"
    r"|none|nobody|nothing|nowhere"
    r"|each|both"
    r"|tutti|tutto|ogni|ognuno|qualcuno|qualcosa|nessuno|niente|entrambi|ciascuno"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class CoVeMetrics:
    """Mutable counters for Chain-of-Verification observability."""

    attempted: int = 0
    corrected: int = 0
    skipped: int = 0
    rejected: int = 0
    failed: int = 0

    @property
    def unchanged(self) -> int:
        return max(0, self.attempted - self.corrected - self.rejected - self.failed)

    def record_skipped(self) -> None:
        self.skipped += 1

    def record_attempt(self) -> None:
        self.attempted += 1

    def record_correction(self) -> None:
        self.corrected += 1

    def record_rejected(self) -> None:
        self.rejected += 1

    def record_failure(self) -> None:
        self.failed += 1

    def summary(self) -> str:
        return (
            f"{self.attempted} verified, {self.corrected} corrected, "
            f"{self.unchanged} unchanged, {self.rejected} rejected, "
            f"{self.failed} failed, {self.skipped} skipped"
        )


def needs_verification(source_text: str) -> tuple[bool, list[str]]:
    """Return ``(needs_cove, reasons)``.

    Parameters
    ----------
    source_text:
        The original source segment text (untranslated).

    Returns
    -------
    tuple[bool, list[str]]
        ``needs_cove`` is True when the source contains negations or
        quantifiers that the model is statistically likely to drop or
        invert. ``reasons`` is a small list of detected risk types
        (``'negation'``, ``'quantifier'``) used by
        :func:`build_verification_prompt` to tailor the questions.

    The check is whitespace/case insensitive and tolerant to
    punctuation. Empty / whitespace-only input returns
    ``(False, [])`` so callers can short-circuit.
    """
    if not source_text:
        return False, []
    s = source_text.strip()
    if not s:
        return False, []

    reasons: list[str] = []
    if _NEGATION_PATTERN.search(s):
        reasons.append("negation")
    if _QUANTIFIER_PATTERN.search(s):
        reasons.append("quantifier")
    return (bool(reasons), reasons)


def build_verification_prompt(
    source_text: str,
    candidate_translation: str,
    src_lang_name: str,
    tgt_lang_name: str,
    reasons: list[str],
    *,
    is_qwen3: bool = False,
    thinking: bool = False,
) -> str:
    """Build the CoVe second-pass verification prompt.

    The prompt asks the model isolated yes/no questions tailored to
    ``reasons`` (negation / quantifier), then asks for a single output
    line containing either the corrected translation or the original
    if every check passed.

    Parameters
    ----------
    source_text:
        The original source segment.
    candidate_translation:
        The first-pass translation produced by ``_translate_with_ollama``.
    src_lang_name, tgt_lang_name:
        Human-readable language names (e.g. ``"English"``, ``"Italian"``).
    reasons:
        Risk types detected by :func:`needs_verification`. When the list
        is empty this function still returns a valid prompt with a
        generic 'preserve meaning' check, but callers are expected to
        skip the CoVe step entirely in that case.
    is_qwen3, thinking:
        Same semantics as :func:`videotranslator.ollama_prompt.build_translation_prompt`.
        When ``is_qwen3`` is True and ``thinking`` is False, the prompt
        is suffixed with ``/no_think`` so qwen3 does not emit a
        chain-of-thought block that downstream parsing would have to
        strip.

    Returns
    -------
    str
        A prompt ready to POST to ``/api/generate``. Output format is
        single-line: line 1 = corrected (or unchanged) translation,
        no preamble. The simple format helps the existing
        ``_ollama_strip_preamble`` parse cleanly without CoVe-specific
        post-processing.
    """
    src = (source_text or "").strip()
    cand = (candidate_translation or "").strip()

    questions: list[str] = []
    if "negation" in reasons:
        questions.append(
            f"1. Does the {tgt_lang_name} translation preserve every negation "
            f"from the {src_lang_name} source (not / no / n't / never / nobody "
            f"/ nothing / none / non / mai)? Answer YES or NO."
        )
    if "quantifier" in reasons:
        # Numbering depends on whether the negation question was added
        # so the prompt reads naturally regardless of which checks fire.
        idx = len(questions) + 1
        questions.append(
            f"{idx}. Does the {tgt_lang_name} translation preserve "
            f"quantifiers (all / every / some / none / each / both) "
            f"with the same logical sense? Answer YES or NO."
        )
    if not questions:
        # Defensive: callers should skip CoVe when reasons is empty,
        # but if they don't, fall back to a generic meaning check so
        # we never emit a malformed prompt.
        questions.append(
            f"1. Does the {tgt_lang_name} translation preserve the "
            f"meaning of the {src_lang_name} source faithfully? "
            f"Answer YES or NO."
        )

    questions_block = "\n".join(questions)

    prompt = (
        f"You are a translation verifier. A first-pass {tgt_lang_name} "
        f"translation of a {src_lang_name} dubbing line was produced. "
        f"Your job is to verify specific quality criteria as isolated "
        f"yes/no questions, then output a single line containing either "
        f"the corrected translation or the original if every check "
        f"passed.\n\n"
        f"{src_lang_name} source:\n{src}\n\n"
        f"{tgt_lang_name} candidate translation:\n{cand}\n\n"
        f"VERIFICATION QUESTIONS (think internally, do NOT print the answers):\n"
        f"{questions_block}\n\n"
        f"OUTPUT INSTRUCTIONS:\n"
        f"- If ANY answer above was NO, output a corrected {tgt_lang_name} "
        f"translation that fixes the failed check while keeping the rest "
        f"unchanged.\n"
        f"- If ALL answers were YES, output the original candidate "
        f"translation UNCHANGED.\n"
        f"- Output ONLY the final {tgt_lang_name} sentence on a single "
        f"line. No preamble, no quotes, no explanations, no answers to "
        f"the questions.\n\n"
        f"Final {tgt_lang_name} translation:\n"
    )

    # Same /no_think contract as build_translation_prompt: when qwen3
    # is configured for non-thinking, append the suffix so the model
    # skips chain-of-thought emission. Thinking-mode users keep the
    # deliberation explicitly.
    if is_qwen3 and not thinking:
        prompt = prompt.rstrip() + "\n\n/no_think"

    return prompt


def parse_verification_response(
    response: str,
    original_translation: str = "",
) -> tuple[str, bool]:
    """Parse the CoVe model response into ``(corrected, was_changed)``.

    Parameters
    ----------
    response:
        Raw model response, already passed through
        ``_ollama_strip_preamble`` upstream (so we expect a clean
        single line, but stay tolerant to multi-line residue).
    original_translation:
        The first-pass translation. Used to detect "no change" outputs
        such as the model literally repeating the candidate (the most
        common YES-YES path) or emitting a meta-string like "Same as
        before" / "Unchanged".

    Returns
    -------
    tuple[str, bool]
        ``corrected_translation`` is the cleaned single-line output
        (empty when the response was unparseable). ``was_changed`` is
        a heuristic: True when the corrected text differs significantly
        from the original AND looks like a real translation (not a
        meta-string). Caller decides whether to apply the correction
        or skip it for logging-only.
    """
    if not response:
        return ("", False)

    # Take the first non-empty line. CoVe prompt asks for single-line
    # output but qwen3 occasionally emits a leading blank line or
    # quotes the result on a second line.
    lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
    if not lines:
        return ("", False)
    corrected = lines[0]

    # Strip surrounding quotes/brackets that some models add despite
    # the explicit instruction. We mirror a minimal subset of
    # _ollama_strip_preamble (full strip is upstream) — only the
    # quote characters that are common across qwen3 / llama / mistral.
    for opener, closer in (
        ('"', '"'), ("'", "'"),
        ("«", "»"), ("“", "”"),
        ("‘", "’"), ("[", "]"),
    ):
        if corrected.startswith(opener) and corrected.endswith(closer):
            corrected = corrected[len(opener):-len(closer)].strip()
            break

    if not corrected:
        return ("", False)

    # Detect meta-string outputs: "same as before", "unchanged",
    # "no changes needed", "yes" (some models emit just the answer
    # despite the instruction). These mean "no correction" — return
    # the original as-is so the caller can keep the candidate.
    _META_RE = re.compile(
        r"^("
        r"same(\s+as\s+(before|original|candidate))?"
        r"|unchanged"
        r"|no\s+changes?(\s+needed)?"
        r"|all\s+good"
        r"|yes"
        r"|no"
        r")\.?\s*$",
        re.IGNORECASE,
    )
    if _META_RE.match(corrected):
        return (original_translation, False)

    # Compare with original (if provided) using a normalised form so
    # whitespace / punctuation drift doesn't trigger false "changed"
    # signals. Two translations are considered equal when they match
    # after lower-casing and collapsing internal whitespace.
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    if original_translation and _norm(corrected) == _norm(original_translation):
        return (original_translation, False)

    return (corrected, True)
