"""Difficulty-aware profile orchestrator.

Maps the (easy|medium|hard) classification produced by
``videotranslator.difficulty_detector`` into concrete pipeline parameter
overrides. The runtime then uses the resolved :class:`Profile` instead
of the hardcoded constants previously spread across
``translate_with_ollama`` (length re-prompt threshold) and
``build_dubbed_track`` (atempo cap, Rubber Band band, XTTS speed cap).

The MEDIUM profile reproduces the legacy v1.7 / pre-2G v2 behaviour
exactly — passing ``--no-difficulty-profile`` (or feeding a
classification not in :data:`PROFILES`) leaves the pipeline indistinct
from the old hard-coded path. EASY relaxes the knobs (less retry, more
margin) while HARD makes them stricter (more retry, larger atempo cap,
extended Rubber Band band, higher XTTS native speed cap) so that videos
classified as audibly accelerated still degrade gracefully.

Pure module: no I/O, no Tk, no subprocess. Easy to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    """Resolved tuning parameters for one difficulty class.

    Attributes
    ----------
    length_retry_threshold:
        Multiplier over the per-segment character budget that triggers
        the Ollama "rewrite shorter" re-prompt. Lower values produce
        more retries (more aggressive shortening).
    length_retry_max_iter:
        Maximum number of "rewrite shorter" attempts per segment. The
        legacy code path runs at most one retry; HARD profile bumps it
        to two so videos that overshoot even after the first rewrite
        get one more chance before falling back to safety truncation.
    atempo_cap:
        Upper clamp passed to :func:`_build_atempo_chain` (and used as
        the runtime hard cap on raw stretch ratio). Higher caps allow
        more aggressive compression on HARD videos at the price of more
        audible artefacts.
    rubberband_min, rubberband_max:
        Inclusive band where :func:`select_stretch_engine` prefers
        Rubber Band CLI over ``ffmpeg atempo``. Outside this band atempo
        wins because Rubber Band itself degrades.
    xtts_speed_cap:
        Hard ceiling on the per-segment adaptive XTTS native speed
        passed to :func:`_compute_segment_speed`. A higher cap shifts
        the compression workload from ``atempo`` (post-stretch) to XTTS
        (synthesis-time), which sounds cleaner but risks XTTS prosody
        loss above ~1.40.
    use_cove:
        Whether to enable Chain-of-Verification (TASK 2U) for the
        Ollama LLM translation path. When True, segments containing
        risk patterns (negations, quantifiers) get a second-pass
        verification call so the model can self-correct dropped
        negations and softened quantifiers. Disabled on EASY because
        the legacy "PRESERVE NEGATIONS" requirement in the main prompt
        is sufficient for low-density videos and CoVe's per-segment
        latency tax is not justified.
    """

    length_retry_threshold: float
    length_retry_max_iter: int
    atempo_cap: float
    rubberband_min: float
    rubberband_max: float
    xtts_speed_cap: float
    use_cove: bool = True


# Calibration baseline:
#   - MEDIUM reproduces the legacy v1.7 / pre-2G v2 hard-coded constants
#     (1.10 retry threshold in _translate_with_ollama, atempo cap 4.0 in
#     _build_atempo_chain default, rubberband band 1.15-1.50 in
#     select_stretch_engine default, XTTS ceiling 1.35 effective via
#     _compute_segment_speed hard_cap and _suggest_xtts_speed cap).
#   - EASY relaxes everything: a video already comfortable in its slots
#     does not need aggressive retry or extended bands; this saves
#     Ollama calls and keeps stretch artefacts minimal.
#   - HARD widens the knobs: lower retry threshold (1.05) catches more
#     overshoots, max_iter=2 gives a second chance, atempo cap goes to
#     5.0 (still within ffmpeg's safe practical range with chained
#     instances), rubberband band extended to 1.80 to avoid falling
#     back to atempo for ratios that Rubber Band still handles
#     acceptably, and XTTS cap 1.45 lets synthesis absorb more of the
#     compression burden.
EASY = Profile(
    length_retry_threshold=1.20,
    length_retry_max_iter=1,
    atempo_cap=3.0,
    rubberband_min=1.15,
    rubberband_max=1.50,
    xtts_speed_cap=1.30,
    # EASY videos are low-density and the in-prompt PRESERVE NEGATIONS
    # rule is enough; skip the CoVe per-segment cost.
    use_cove=False,
)
MEDIUM = Profile(
    length_retry_threshold=1.10,
    length_retry_max_iter=1,
    atempo_cap=4.0,
    rubberband_min=1.15,
    rubberband_max=1.50,
    xtts_speed_cap=1.35,
    use_cove=True,
)
HARD = Profile(
    length_retry_threshold=1.05,
    length_retry_max_iter=2,
    atempo_cap=5.0,
    rubberband_min=1.15,
    rubberband_max=1.80,
    xtts_speed_cap=1.45,
    use_cove=True,
)

PROFILES: dict[str, Profile] = {
    "easy":   EASY,
    "medium": MEDIUM,
    "hard":   HARD,
}


def resolve_profile(classification: str) -> Profile:
    """Return the :class:`Profile` for ``classification``.

    Falls back to :data:`MEDIUM` for unknown / empty / ``None`` inputs
    so a typo or future classification value never crashes the pipeline
    — at worst the runtime keeps the legacy behaviour.
    """
    if not classification:
        return MEDIUM
    return PROFILES.get(classification.lower(), MEDIUM)


def format_profile_log(
    classification: str,
    profile: Profile,
    p90: float,
) -> str:
    """One-line banner describing the applied profile.

    Printed by ``translate_video`` immediately after the existing
    ``[difficulty]`` log so the user can see *why* the pipeline picked
    a given retry threshold / atempo cap / Rubber Band band.
    """
    return (
        f"[difficulty] {classification.upper()} profile applied "
        f"(P90 ~{p90:.2f}): "
        f"retry threshold {profile.length_retry_threshold}, "
        f"atempo cap {profile.atempo_cap}, "
        f"rubberband {profile.rubberband_min}-{profile.rubberband_max}, "
        f"xtts cap {profile.xtts_speed_cap}"
    )
