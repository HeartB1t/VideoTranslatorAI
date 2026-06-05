"""Difficulty-aware profile orchestrator.

Maps the (easy|medium|hard) classification produced by
``videotranslator.difficulty_detector`` into concrete pipeline parameter
overrides. The runtime then uses the resolved :class:`Profile` instead
of hardcoded knobs spread across ``translate_with_ollama`` (length
re-prompt budget), ``build_dubbed_track`` (post-stretch cap, Rubber Band
band) and XTTS generation (native speed cap).

The profiles are quality-first: as density rises, the pipeline spends
more effort rewriting translations shorter and keeps post-stretch
compression inside a bounded, audible-quality range. The older policy
allowed very high ``atempo`` factors to avoid truncation; that completed
more renders, but produced sudden speed jumps on dense videos.

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
        denser the source, the more chances the LLM gets before audio
        stretch is allowed to solve the problem.
    target_chars_slack:
        Tolerance multiplier used when computing the spoken character
        budget for a slot. Lower values force shorter dubbing lines
        before TTS, reducing later speed spikes.
    target_chars_floor:
        Minimum character budget for very short segments. Lower floors
        make 1-2 second slots eligible for rewrite instead of silently
        accepting lines that can only fit by speeding up audio.
    atempo_cap:
        Upper clamp passed to :func:`_build_atempo_chain` (and used as
        the runtime hard cap on raw stretch ratio). Kept deliberately
        low: anything far above ~1.5x sounds like a sudden speed-up.
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
    target_chars_slack: float
    target_chars_floor: int
    atempo_cap: float
    rubberband_min: float
    rubberband_max: float
    xtts_speed_cap: float
    use_cove: bool = True


# Calibration baseline:
#   - EASY keeps a little room and avoids needless extra LLM calls.
#   - MEDIUM is the default quality profile for dense but recoverable
#     videos: retry more, tighten the budget, cap speed jumps at 1.5x.
#   - HARD is strict on text length, not permissive on speed. It gives
#     one more rewrite attempt and allows only a modest extra post-stretch
#     ceiling for otherwise impossible segments.
EASY = Profile(
    length_retry_threshold=1.10,
    length_retry_max_iter=1,
    target_chars_slack=1.10,
    target_chars_floor=50,
    atempo_cap=1.35,
    rubberband_min=1.15,
    rubberband_max=1.35,
    xtts_speed_cap=1.25,
    # EASY videos are low-density and the in-prompt PRESERVE NEGATIONS
    # rule is enough; skip the CoVe per-segment cost.
    use_cove=False,
)
MEDIUM = Profile(
    length_retry_threshold=1.00,
    length_retry_max_iter=2,
    target_chars_slack=1.05,
    target_chars_floor=35,
    atempo_cap=1.50,
    rubberband_min=1.15,
    rubberband_max=1.50,
    xtts_speed_cap=1.30,
    use_cove=True,
)
HARD = Profile(
    length_retry_threshold=0.98,
    length_retry_max_iter=3,
    target_chars_slack=1.00,
    target_chars_floor=25,
    atempo_cap=1.65,
    rubberband_min=1.15,
    rubberband_max=1.65,
    xtts_speed_cap=1.35,
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
    — at worst the runtime keeps the default quality profile.
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
        f"target slack {profile.target_chars_slack}, "
        f"target floor {profile.target_chars_floor}, "
        f"atempo cap {profile.atempo_cap}, "
        f"rubberband {profile.rubberband_min}-{profile.rubberband_max}, "
        f"xtts cap {profile.xtts_speed_cap}"
    )
