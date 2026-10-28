"""Slot-aware Ollama translation orchestrator for dubbing.

Ties together the prompt builders, length control, Chain-of-Verification and
document context modules around one local Ollama daemon.
"""

from __future__ import annotations

import os

from . import platforms as _platforms
from .difficulty_detector import (
    classify_difficulty as _classify_difficulty,
    estimate_p90_ratio as _estimate_p90_ratio,
    format_difficulty_log as _format_difficulty_log,
    tts_speed_factor_for as _tts_speed_factor_for,
)
from .difficulty_profile import (
    MEDIUM as _DIFFICULTY_PROFILE_MEDIUM,
    Profile as _DifficultyProfile,
)
from .document_context import (
    build_summary_prompt as _build_summary_prompt,
    is_summary_useful as _is_summary_useful,
)
from .ollama_cove import (
    CoVeMetrics as _CoVeMetrics,
    build_verification_prompt as _cove_build_verification_prompt,
    needs_verification as _cove_needs_verification,
    parse_verification_response as _cove_parse_verification_response,
)
from .ollama_length_control import (
    build_rewrite_shorter_prompt as _build_rewrite_shorter_prompt,
    compute_target_chars as _compute_target_chars,
    should_reprompt_for_length as _should_reprompt_for_length,
)
from .ollama_prompt import build_translation_prompt as _build_translation_prompt
from .ollama_runtime import (
    _ollama_health_check,
    _ollama_lang_name,
    _ollama_num_predict_for_segment,
    _ollama_strip_preamble,
)
from .quality_flags import (
    FLAG_LENGTH_UNFIT as _FLAG_LENGTH_UNFIT,
    FLAG_TRANSLATION_FALLBACK as _FLAG_TRANSLATION_FALLBACK,
    add_quality_flag as _add_quality_flag,
    compute_segment_quality_flags as _compute_segment_quality_flags,
)
from .timing import LANG_EXPANSION


def translate_with_ollama(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
    model: str = "qwen3:8b",
    api_url: str = "http://localhost:11434",
    slot_aware: bool = True,
    batch_size: int = 1,
    fallback_fn=None,
    thinking: bool = False,
    use_document_context: bool = True,
    difficulty_profile: _DifficultyProfile | None = None,
    use_cove: bool = True,
) -> list[dict]:
    """Translate segments via a local Ollama daemon using a slot-aware prompt
    that enforces conciseness for dubbing.

    Args:
        segments: list of dicts with keys `start`, `end`, `text`, opt `speaker`.
        source_lang: ISO code of the source language (e.g. "en"). "auto" accepted.
        target_lang: ISO code of the target language (e.g. "it").
        model: Ollama model name (default "qwen3:8b"). For Qwen3, thinking mode
               is disabled automatically (think=False + /no_think suffix) to
               prevent <think>...</think> blocks that XTTS would speak as outliers.
        api_url: base URL of the Ollama daemon (default "http://localhost:11434").
        slot_aware: if True, includes reading time in the prompt (recommended).
        batch_size: number of segments to pack into a single prompt. 1 = safe
                    (trivial parsing), >1 = faster but brittle parsing. In v2.0
                    we keep the default at 1 and leave the parameter as a future
                    hook (the code supports >1 with automatic per-segment fallback
                    if output parsing fails).
        fallback_fn: optional callable `(seg) -> str` invoked for a single
                     segment when Ollama raises. If None, the source text is
                     used as-is (degrades to "no translation").
        difficulty_profile: TASK 2G v2 profile (easy/medium/hard) that configures
                     the budget, threshold, and iteration count for the length
                     re-prompt. If None, the MEDIUM quality profile is used.
        use_cove: if True (default), enables the second-pass Chain-of-Verification
                     (TASK 2U) on segments containing risky patterns (negations,
                     quantifiers). The model verifies with isolated yes/no
                     questions whether the first translation preserves negations
                     and quantifiers, and can correct it. Covered by the Profile
                     (EASY=False, MEDIUM/HARD=True) but the caller can override
                     the flag (CLI ``--no-cove`` to disable globally).

    Returns the list of segments with `text_src` and `text_tgt` populated,
    using the same schema produced by `translate_segments` for other engines.
    """
    import re as _re
    import requests
    base = _platforms.loopback_ipv4(api_url)
    src_name = _ollama_lang_name(source_lang)
    tgt_name = _ollama_lang_name(target_lang)

    # TASK 2G v2: profile orchestrator. None = default MEDIUM quality policy.
    # The caller is expected
    # to pass a resolved Profile when --no-difficulty-profile is OFF;
    # we fall back to MEDIUM here so the public function stays usable
    # standalone (CLI, notebooks) without forcing every caller to know
    # about the orchestrator.
    _profile = difficulty_profile or _DIFFICULTY_PROFILE_MEDIUM

    # Health check upfront - if Ollama is down we raise immediately instead of
    # failing 300 times in the loop.
    # TASK 2J: if the requested model is missing
    # but the daemon has another usable model, the selector returns it via
    # `resolved_model` and we proceed with it instead of falling through to
    # Google. Surface the warning so the user sees what happened.
    ok, msg, resolved_model = _ollama_health_check(base, model)
    if not ok:
        raise RuntimeError(msg)
    if msg and resolved_model and resolved_model != model:
        print(f"     ! {msg}", flush=True)
        model = resolved_model

    print(f"     → Ollama ready ({model} @ {base}, slot_aware={slot_aware}, batch={batch_size})", flush=True)

    # Detect Qwen3 family - needs thinking mode disabled to avoid <think>
    # blocks in output that XTTS would pronounce as audible chain-of-thought.
    # Sampling parameters tuned per Qwen team's official recommendations:
    #   - Qwen3 non-thinking: T=0.7, TopP=0.8, TopK=20 (avoids endless loops)
    #   - Qwen2.x and others: stricter T=0.3, TopP=0.9 for translation
    # Double protection: payload `think:false` (Ollama API ≥2025) +
    # /no_think suffix in the prompt (also works on older versions).
    is_qwen3 = model.lower().startswith("qwen3")
    # `thinking` is only meaningful for Qwen3 (other models ignore the flag).
    # For non-Qwen3 models the log label stays "standard"; for Qwen3 it reflects
    # the user's choice - thinking=True enables step-by-step deliberation
    # (~10x slower, reduces idiom/grammar errors), False keeps fast behaviour
    # with the /no_think prompt.
    if is_qwen3:
        _mode_label = f"Qwen3 {'thinking' if thinking else 'non-thinking'} (think={thinking})"
    else:
        _mode_label = "standard"
    print(f"     → Mode: {_mode_label}", flush=True)

    # Debug opt-in: when set, logs source + final output for every segment.
    # Useful for investigating preamble/commentary residues without re-running the pipeline.
    _ollama_debug = os.environ.get("VIDEOTRANSLATORAI_OLLAMA_DEBUG") == "1"

    # Length safeguard: compute the expected expansion factor (target/source)
    # from the LANG_EXPANSION table once, before the segment loop. Used to
    # estimate the maximum plausible length for each segment. Cap 1.8× =
    # permissive margin for verbose LLMs but catches commentary outliers.
    _src_key = (source_lang or "").split("-")[0] if source_lang != "auto" else ""
    _tgt_key = target_lang.split("-")[0] if target_lang else ""
    _exp_tgt = LANG_EXPANSION.get(target_lang, LANG_EXPANSION.get(_tgt_key, 1.0))
    _exp_src = LANG_EXPANSION.get(source_lang, LANG_EXPANSION.get(_src_key, 1.0)) or 1.0
    _expansion_factor = _exp_tgt / _exp_src if _exp_src > 0 else 1.0

    # TASK 2G: pre-flight difficulty estimate. Pure-text heuristic that
    # predicts the P90 of pre_stretch_ratio BEFORE TTS+stretch. Lets the
    # user know upfront whether the dub will be fluent (easy), partially
    # accelerated (medium) or audibly accelerated on most segments (hard).
    # Informational only - pipeline runs to completion regardless.
    #
    # tts_speed_factor lookup is per-target-language (it=1.15, en/es/fr/de
    # ~=1.10, zh/ja/ko ~=1.05). Empirical means observed on production
    # CSVs; the XTTS cap is 1.35 but most segments land lower. Using the
    # cap as divisor would over-correct. See difficulty_detector module
    # for the full table and calibration notes.
    _est_p90 = _estimate_p90_ratio(
        segments, target_lang, _expansion_factor,
        tts_speed_factor=_tts_speed_factor_for(target_lang),
    )
    if _est_p90 > 0:
        _diff_class = _classify_difficulty(_est_p90)
        print(
            f"     {_format_difficulty_log(_est_p90, _diff_class, target_lang)}",
            flush=True,
        )

    translated: list[dict] = []
    total = len(segments)
    total_src_chars = 0
    total_tgt_chars = 0
    failed = 0
    truncated_count = 0
    # TASK 2C-1: iterative re-prompt for length control. `rewrite_attempts`
    # counts the segments whose first translation was over budget and for which
    # we requested a "rewrite shorter" retry. `rewrite_success` counts how many
    # of those retries actually produced a shorter version.
    rewrite_attempts = 0
    rewrite_success = 0
    # TASK 2U: Chain-of-Verification counters. Kept in a small shared object
    # so logs/tests can distinguish useful corrections from rejected empty
    # responses, HTTP failures and skipped non-risky segments.
    cove_metrics = _CoVeMetrics()

    def _build_prompt(
        text: str,
        slot_s: float,
        prev_text: str | None = None,
        next_text: str | None = None,
    ) -> str:
        # Thin wrapper around the pure module-level builder. Closure captures
        # src_name, tgt_name, slot_aware, is_qwen3, thinking from the
        # surrounding _translate_with_ollama scope so the call sites stay
        # short. The actual prompt construction (including the optional
        # CONTEXT block injecting prev_text/next_text for disambiguation
        # and the document-level GLOBAL CONTEXT from TASK 2K) lives in
        # videotranslator.ollama_prompt and is unit-tested there.
        return _build_translation_prompt(
            text,
            slot_s,
            src_name,
            tgt_name,
            slot_aware=slot_aware,
            is_qwen3=is_qwen3,
            thinking=thinking,
            prev_text=prev_text,
            next_text=next_text,
            global_context=_global_context,
        )

    def _call_ollama(prompt: str, num_predict: int) -> str:
        if is_qwen3:
            options = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "num_predict": num_predict,
            }
        else:
            options = {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": num_predict,
            }
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        # Toggle thinking mode on Qwen3 via the native API flag (Ollama
        # supports `think` from 2025+). If the API ignores the flag on older
        # versions, the `/no_think` suffix in the prompt (when thinking=False)
        # acts as a safety fallback. With thinking=True the model deliberates
        # step-by-step: ~10x slower but reduces idiom/grammar errors.
        if is_qwen3:
            payload["think"] = bool(thinking)
        # Generous timeout: qwen3:8b / qwen2.5:7b on an RTX 3090 produces
        # ~40-80 tok/s, but on CPU-only it can drop to 2-5 tok/s. With thinking
        # enabled the model produces 3-5x more tokens (internal chain-of-thought
        # + answer), so we raise the timeout to 360 s to avoid cut-off.
        _timeout = 360 if (is_qwen3 and thinking) else 120
        r = requests.post(f"{base}/api/generate", json=payload, timeout=_timeout)
        r.raise_for_status()
        data = r.json()
        return _ollama_strip_preamble(data.get("response", ""))

    # TASK 2K: document-level context. One Ollama call up front to get a
    # semantic summary of the whole transcript; injected into every per-
    # segment prompt as 'GLOBAL CONTEXT (do not translate)' to anchor
    # terminology, tone and global referents (a "he" 3 minutes later
    # referring to a person introduced at the start). Skipped for short
    # videos where the local prev/next window already covers everything,
    # and skipped entirely when the caller passes use_document_context=False
    # (CLI --no-document-context, ergonomic opt-out for fast runs).
    _global_context: str | None = None
    if use_document_context and _is_summary_useful(segments):
        try:
            _summary_prompt = _build_summary_prompt(
                segments, tgt_name, src_name,
                is_qwen3=is_qwen3, thinking=thinking,
            )
            if _summary_prompt:
                # Token budget for the summary: bias the input length
                # toward "long" so the output budget is generous. The
                # summary is a one-off call; spending an extra ~500
                # tokens of headroom is cheaper than truncating the
                # glossary.
                _summary_predict = _ollama_num_predict_for_segment(
                    "x" * 1500, is_qwen3, thinking,
                )
                _summary_raw = _call_ollama(_summary_prompt, _summary_predict)
                _summary_clean = (_summary_raw or "").strip()
                if _summary_clean:
                    _global_context = _summary_clean
                    print(
                        f"     → Document context: {len(_global_context)} chars summary "
                        f"generated for translation guide",
                        flush=True,
                    )
        except Exception as _ctx_err:
            print(
                f"     ! Document context generation failed: {_ctx_err}; "
                f"proceeding without global context",
                flush=True,
            )
            _global_context = None

    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        slot_s = max(0.0, float(seg.get("end", 0)) - float(seg.get("start", 0)))

        # TASK 2D: sliding context window. Pass the previous and next
        # segment text as CONTEXT (for understanding only) so qwen3 can
        # resolve sentence-spanning fragments like "...less likely to" /
        # "stick. When I gave up sugar..." that Whisper splits on
        # punctuation/pause. Each snippet is capped at
        # _CONTEXT_SNIPPET_MAX_CHARS by the builder to keep the prompt
        # compact and Ollama latency low.
        _prev_text: str | None = None
        if i > 0:
            _prev_raw = (segments[i - 1].get("text") or "").strip()
            if _prev_raw:
                _prev_text = _prev_raw
        _next_text: str | None = None
        if i + 1 < len(segments):
            _next_raw = (segments[i + 1].get("text") or "").strip()
            if _next_raw:
                _next_text = _next_raw

        # Per-segment metrics counters (used later when building entry dict
        # so the metrics CSV can correlate ratio outliers with retry decisions).
        _seg_target_chars = 0
        _seg_retry_attempted = False
        _seg_retry_succeeded = False

        if not text:
            tr = ""
        else:
            try:
                prompt = _build_prompt(
                    text,
                    slot_s,
                    prev_text=_prev_text,
                    next_text=_next_text,
                )
                num_predict = _ollama_num_predict_for_segment(text, is_qwen3, thinking)
                tr = _call_ollama(prompt, num_predict)
                if not tr:
                    if is_qwen3 and thinking:
                        retry_predict = _ollama_num_predict_for_segment(
                            text, is_qwen3, thinking, retry=1
                        )
                        print(
                            f"     ! Ollama thinking returned empty response for segment #{i} "
                            f"(num_predict={num_predict}); retrying with num_predict={retry_predict}",
                            flush=True,
                        )
                        tr = _call_ollama(prompt, retry_predict)
                        if not tr:
                            print(
                                f"     ! Ollama thinking retry exhausted for segment #{i} "
                                f"(initial num_predict={num_predict}, retry num_predict={retry_predict}); "
                                f"falling back",
                                flush=True,
                            )
                    if not tr:
                        # Empty response - treat as failure and fall back.
                        raise RuntimeError("empty response")
                # ── Length re-prompt (TASK 2C-1, 2G v2) ─────────────────
                # If the first translation is significantly over the budget
                # allowed for the audio slot, ask the model to rewrite it
                # shorter. This reduces the "strong/severe" zone of the atempo
                # diagnostic (>1.50x) without penalising segments already within
                # budget. Cost: +N Ollama calls only for outliers
                # (N = profile.length_retry_max_iter, 2 for MEDIUM, 3 for HARD).
                #
                # TASK 2G v2: budget, threshold, and iteration count come from
                # the Profile. Denser profiles demand shorter sentences before
                # letting atempo/rubberband compress the audio.
                target_chars = _compute_target_chars(
                    slot_s,
                    target_lang,
                    slack=_profile.target_chars_slack,
                    min_chars=_profile.target_chars_floor,
                )
                _seg_target_chars = target_chars
                _retry_threshold = _profile.length_retry_threshold
                _retry_max_iter = _profile.length_retry_max_iter
                _retry_iter = 0
                while (
                    _retry_iter < _retry_max_iter
                    and _should_reprompt_for_length(
                        len(tr), target_chars, threshold=_retry_threshold
                    )
                ):
                    _retry_iter += 1
                    rewrite_attempts += 1
                    _seg_retry_attempted = True
                    rewrite_prompt = _build_rewrite_shorter_prompt(
                        first_translation=tr,
                        slot_s=slot_s,
                        target_chars=target_chars,
                        target_lang_name=tgt_name,
                        is_qwen3=is_qwen3,
                        thinking=thinking,
                    )
                    rewrite_predict = _ollama_num_predict_for_segment(
                        text, is_qwen3, thinking
                    )
                    try:
                        tr_short = _call_ollama(rewrite_prompt, rewrite_predict)
                    except Exception as _re_err:
                        tr_short = ""
                        print(
                            f"     ! Length retry seg #{i} (iter {_retry_iter}) "
                            f"HTTP failed: {_re_err}; keeping previous translation",
                            flush=True,
                        )
                        # On HTTP error stop iterating: a flaky daemon would
                        # otherwise burn the full retry budget for nothing.
                        break
                    if tr_short and len(tr_short) < len(tr):
                        if not _seg_retry_succeeded:
                            # Count "first success" once even if further iter
                            # produce additional shrinkage; rewrite_success is
                            # the number of segments improved, not the total
                            # number of successful calls.
                            rewrite_success += 1
                            _seg_retry_succeeded = True
                        _iter_tag = (
                            f" iter {_retry_iter}/{_retry_max_iter}"
                            if _retry_max_iter > 1 else ""
                        )
                        print(
                            f"     ↺ Length retry seg #{i}{_iter_tag}: "
                            f"{len(tr)} → {len(tr_short)} chars "
                            f"(target {target_chars}, slot {slot_s:.1f}s)",
                            flush=True,
                        )
                        tr = tr_short
                    elif tr_short:
                        # Model responded but did not shorten. Log only when
                        # _ollama_debug to avoid cluttering the output, and
                        # stop the loop: a second iteration with the same
                        # translation would hit the same local minimum of the
                        # model, wasting budget.
                        if _ollama_debug:
                            print(
                                f"     [ollama-debug] length retry seg #{i} "
                                f"iter {_retry_iter} did not shorten "
                                f"({len(tr_short)} >= {len(tr)})",
                                flush=True,
                            )
                        break
                # TASK 5C: post-retry quality flag. If the (possibly
                # multi-iter) length retry loop exhausted its budget and
                # the translation is *still* above the comfort threshold,
                # mark the segment so the editor highlights it for review.
                # The pipeline still ships the over-budget translation -
                # this is purely a hint for the human reviewer.
                if (
                    _seg_target_chars > 0
                    and _should_reprompt_for_length(
                        len(tr), _seg_target_chars, threshold=_retry_threshold
                    )
                ):
                    _add_quality_flag(seg, _FLAG_LENGTH_UNFIT)
                # ── Length safeguard ────────────────────────────────────
                # If the residual output after strip_preamble is >> the source
                # relative to the expected expansion, the model almost certainly
                # included unstripped commentary. Truncate to the first complete
                # sentence (or to a char cap with word-boundary) to prevent
                # XTTS from synthesising 20+ seconds of disclaimer.
                # v2.2: tighter cap 1.5x (was 1.8x) to catch Ollama outliers
                # from unstripped commentary/disclaimers more aggressively.
                max_reasonable_chars = max(
                    50, int(len(text) * _expansion_factor * 1.5)
                )
                if len(tr) > max_reasonable_chars:
                    # v2.2: always log the truncated SRC and OUT so the user can
                    # diagnose which segments triggered the safety without having
                    # to set VIDEOTRANSLATORAI_OLLAMA_DEBUG.
                    src_preview = text[:120] + ("..." if len(text) > 120 else "")
                    cleaned_preview = tr[:200] + ("..." if len(tr) > 200 else "")
                    print(
                        f"     ! Ollama output sospetto (segment {i}): "
                        f"{len(tr)} chars vs max atteso {max_reasonable_chars}. "
                        f"Attivo safety truncation.",
                        flush=True,
                    )
                    print(f"       SRC: {src_preview!r}", flush=True)
                    print(f"       OUT: {cleaned_preview!r}", flush=True)
                    # Strategy: first complete sentence (.?!。？！ followed by
                    # space/end). Fallback: cap with word-boundary.
                    m = _re.search(r"^(.+?[.?!。？！])(?:\s|$)", tr)
                    if m and len(m.group(1)) <= max_reasonable_chars * 1.1:
                        tr = m.group(1)
                    else:
                        tr = tr[:max_reasonable_chars].rsplit(" ", 1)[0] + "..."
                    truncated_count += 1
                # ── Chain-of-Verification (TASK 2U) ────────────────────
                # Second-pass opt-in that targets semantic errors by qwen3
                # on risky segments (negations, quantifiers).
                # Reference: ACL 2024 paper 'Chain-of-Verification
                # Reduces Hallucination in Large Language Models'.
                # Triggered ONLY if: (a) flag use_cove True (controlled
                # by Profile + CLI --no-cove), (b) source contains a
                # risky pattern, (c) candidate translation is non-empty.
                # Failure is best-effort: the first translation remains
                # valid if the HTTP check fails or the output is unusable.
                if use_cove and tr:
                    _cove_needs, _cove_reasons = _cove_needs_verification(text)
                    if _cove_needs:
                        cove_metrics.record_attempt()
                        try:
                            _cove_prompt = _cove_build_verification_prompt(
                                source_text=text,
                                candidate_translation=tr,
                                src_lang_name=src_name,
                                tgt_lang_name=tgt_name,
                                reasons=_cove_reasons,
                                is_qwen3=is_qwen3,
                                thinking=thinking,
                            )
                            _cove_predict = _ollama_num_predict_for_segment(
                                text, is_qwen3, thinking
                            )
                            _cove_raw = _call_ollama(_cove_prompt, _cove_predict)
                            _cove_corrected, _cove_changed = (
                                _cove_parse_verification_response(
                                    _cove_raw, original_translation=tr
                                )
                            )
                            if _cove_changed and _cove_corrected:
                                cove_metrics.record_correction()
                                if _ollama_debug:
                                    print(
                                        f"     ↻ CoVe seg #{i} "
                                        f"(reasons={','.join(_cove_reasons)}): "
                                        f"{tr!r} → {_cove_corrected!r}",
                                        flush=True,
                                    )
                                tr = _cove_corrected
                            elif _cove_changed and not _cove_corrected:
                                cove_metrics.record_rejected()
                        except Exception as _cove_err:
                            cove_metrics.record_failure()
                            # CoVe is opt-in best-effort: an HTTP error or
                            # a parse failure must not block the segment.
                            # The first translation remains valid.
                            if _ollama_debug:
                                print(
                                    f"     ! CoVe seg #{i} failed: {_cove_err}",
                                    flush=True,
                                )
                    else:
                        cove_metrics.record_skipped()
                if _ollama_debug:
                    print(
                        f"     [ollama-debug] seg#{i} src={text!r} → tgt={tr!r}",
                        flush=True,
                    )
            except Exception as e:
                failed += 1
                fb_text = None
                if fallback_fn is not None:
                    try:
                        fb_text = fallback_fn(seg)
                    except Exception as fe:
                        print(f"     ! Ollama+fallback both failed for segment #{i}: {fe}", flush=True)
                if fb_text:
                    tr = fb_text
                    print(
                        f"     ! Ollama translation failed for segment #{i}, fallback used: {e}",
                        flush=True,
                    )
                else:
                    tr = text
                    print(
                        f"     ! Ollama translation failed for segment #{i}, keeping source: {e}",
                        flush=True,
                    )
                # TASK 5C: primary engine failed for this segment - flag so
                # the editor surfaces it. Both branches (fallback used OR
                # source kept) are lower-quality than a successful Ollama
                # translation, so they share the same flag.
                _add_quality_flag(seg, _FLAG_TRANSLATION_FALLBACK)

        total_src_chars += len(text)
        total_tgt_chars += len(tr)
        entry = {
            "start": seg["start"],
            "end":   seg["end"],
            "text_src": text,
            "text_tgt": tr or text,
            # STEP 1: per-segment metrics for CSV dump in build_dubbed_track.
            # Underscore prefix marks them as internal pipeline metadata so
            # downstream consumers (subtitle writers, editors) ignore them.
            "_target_chars": _seg_target_chars,
            "_length_retry_attempted": _seg_retry_attempted,
            "_length_retry_succeeded": _seg_retry_succeeded,
        }
        if "speaker" in seg:
            entry["speaker"] = seg["speaker"]
        # TASK 5C: propagate quality flags from the source segment (where the
        # Whisper sanity stage tagged whisper_suspicious) and from the in-loop
        # additions (length_unfit, translation_fallback) to the translated
        # entry so the subtitle editor can colourise the row.
        _flags_for_entry = _compute_segment_quality_flags(seg)
        if _flags_for_entry:
            entry["_quality_flags"] = _flags_for_entry
        translated.append(entry)
        if (i + 1) % 4 == 0 or i + 1 == total:
            print(f"     {i+1}/{total}...", end="\r", flush=True)

    # Shrinkage statistic: how much more concise the Ollama output is relative
    # to the source (character-count approximation). Useful for diagnosing
    # whether the "CONCISE" prompt is working (expected ratio ~0.9-1.1 vs the
    # naïve 1.25 for EN→IT with deep-translator).
    if total_src_chars > 0:
        ratio = total_tgt_chars / total_src_chars
        # Naïve expansion expected from the LANG_EXPANSION table (literal baseline)
        exp_tgt = LANG_EXPANSION.get(target_lang, LANG_EXPANSION.get(target_lang.split("-")[0], 1.0))
        exp_src = LANG_EXPANSION.get(source_lang, LANG_EXPANSION.get((source_lang or "").split("-")[0], 1.0))
        baseline = (exp_tgt / exp_src) if exp_src > 0 else 1.0
        shrinkage_pct = (ratio / baseline - 1.0) * 100.0 if baseline > 0 else 0.0
        fail_note = f", {failed} fallback" if failed else ""
        print(
            f"     → Ollama translation: {total}/{total} segments, "
            f"char ratio={ratio:.2f} vs literal baseline {baseline:.2f} "
            f"(shrinkage {shrinkage_pct:+.1f}%){fail_note}",
            flush=True,
        )
        if rewrite_attempts > 0:
            print(
                f"     → Length re-prompt: {rewrite_attempts} segments over budget, "
                f"{rewrite_success} shortened ({rewrite_attempts - rewrite_success} kept original)",
                flush=True,
            )
        if truncated_count > 0:
            print(
                f"     → Safety-truncated for length: {truncated_count} segments "
                f"(see log above for context)",
                flush=True,
            )
        if cove_metrics.attempted > 0:
            # TASK 2U: CoVe summary. The "verified" count is the number
            # of segments where the source had a risk pattern (negation
            # / quantifier) and we ran the second-pass; "corrected" is
            # the subset where the model produced a substantially
            # different translation that we accepted. A 0/N corrected
            # rate is normal on clean translations - it just means the
            # first pass already preserved every negation.
            print(
                f"     → CoVe verification: {cove_metrics.summary()}",
                flush=True,
            )
    else:
        print(f"     → Ollama translation: {total}/{total} segments (no text)", flush=True)

    return translated
