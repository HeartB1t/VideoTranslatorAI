"""Audio time-stretching engine selection and command builders.

This module isolates the policy that decides whether a given segment should
be stretched with ffmpeg's ``atempo`` filter or with the standalone
``rubberband`` CLI. Rubber Band yields markedly higher quality in the
1.15–1.50 ratio band (no audible "chipmunk" pitch artifacts that ``atempo``
sometimes introduces on cloned voices), but it is an optional system
dependency. The helpers here are pure (no I/O, no subprocess) so they can
be exercised by unit tests on systems where ``rubberband`` is not
installed; the real runtime in ``build_dubbed_track`` checks availability
once via ``shutil.which`` and falls back to ``atempo`` whenever the binary
is missing or fails at runtime.

Convention used throughout the module:

* ``ratio`` is ``input_duration / slot_duration``. Values greater than
  ``1.0`` mean the TTS audio is longer than the slot it must fit into and
  therefore needs to be compressed (sped up). ``rubberband`` itself uses
  ``-T <tempo-multiplier>`` with the same semantics, so the same number is
  passed straight through.
"""

from __future__ import annotations

# Engine identifiers — kept as bare strings (no Enum) to stay friendly to
# the legacy single-file caller, which already uses string comparisons.
_ENGINE_RUBBERBAND = "rubberband"
_ENGINE_ATEMPO = "atempo"


def select_stretch_engine(
    ratio: float,
    rubberband_available: bool,
    rb_min: float = 1.15,
    rb_max: float = 1.50,
) -> str:
    """Pick the stretch engine for a given compression ratio.

    Returns ``"rubberband"`` when ``rb_min <= ratio <= rb_max`` and the
    binary is available on the host; otherwise ``"atempo"``. Boundaries
    are inclusive so that a ratio sitting exactly on the edge (e.g. 1.15)
    is still routed to Rubber Band when it is installed — that is the
    band where quality matters most.

    Parameters
    ----------
    ratio:
        ``input_dur / slot_dur``. Treated as a magnitude; values ``<= 1.0``
        always return ``"atempo"`` because the caller does not invoke any
        stretching in that case (the audio already fits).
    rubberband_available:
        Result of a ``shutil.which("rubberband")`` lookup performed once
        per pipeline run.
    rb_min, rb_max:
        Inclusive bounds of the band in which Rubber Band is preferred.
        Outside this band ``atempo`` is the better choice: below ``rb_min``
        the difference is imperceptible and ``atempo`` is faster; above
        ``rb_max`` Rubber Band itself starts to introduce its own artifacts
        so we drop back to ``atempo``'s well-understood behaviour.
    """
    if not rubberband_available:
        return _ENGINE_ATEMPO
    if ratio < rb_min or ratio > rb_max:
        return _ENGINE_ATEMPO
    return _ENGINE_RUBBERBAND


def build_rubberband_command(
    input_path: str,
    output_path: str,
    ratio: float,
    sample_rate: int = 44100,
) -> list[str]:
    """Build the ``rubberband`` CLI invocation for a tempo compression.

    The CLI accepts ``-T <X>`` meaning "change tempo by multiple X"
    (equivalent to ``--time 1/X``). Since our ``ratio`` already encodes
    ``input_dur / slot_dur`` (i.e. the speed-up factor we want), we pass
    it through unchanged.

    ``--formant`` is enabled to keep the formant envelope stable across
    the stretch — Rubber Band documents this flag for pitch shifting, but
    enabling it on time-only changes is harmless and provides a safety
    net for cloned voices coming out of XTTS, which can otherwise drift
    in timbre at the band edges.

    Parameters
    ----------
    input_path, output_path:
        Filesystem paths passed verbatim to the CLI. The caller is
        responsible for quoting/escaping at the shell level — this
        helper returns an ``argv``-style list, ready for
        ``subprocess.run`` with ``shell=False``.
    ratio:
        Tempo multiplier (>1.0 compresses, <1.0 stretches). Must be
        strictly positive; ``ValueError`` otherwise to fail fast on
        upstream bugs that would otherwise hand Rubber Band a degenerate
        argument.
    sample_rate:
        Currently unused by the CLI invocation (Rubber Band keeps the
        input sample rate by default), but accepted for forward
        compatibility with a future ``--samplerate`` flag and to keep the
        caller side stable.
    """
    if ratio <= 0:
        raise ValueError(f"rubberband ratio must be > 0, got {ratio!r}")

    # The CLI keeps the input sample rate by default; the parameter is
    # accepted to keep the call sites symmetrical with the atempo path
    # (which forces -ar via ffmpeg). Reference it to silence linters
    # without inventing a flag the binary does not support.
    _ = sample_rate

    return [
        "rubberband",
        "--formant",
        "-T", f"{ratio:.6f}",
        input_path,
        output_path,
    ]


# Strategy identifiers for compute_overlap_strategy (TASK 2P).
# Kept as bare strings for the same reason as engine ids: the legacy
# single-file caller compares against literals.
_STRAT_FIT = "fit"                       # pcm fits the slot, no action
_STRAT_OVERLAP_CLEAN = "overlap_clean"   # mild overshoot, full pcm kept + crossfade tail
_STRAT_OVERLAP_TRUNCATE = "overlap_truncate"  # large overshoot, capped at slot+max_overlap with fade-out
_STRAT_TRUNCATE = "truncate"             # legacy hard-truncate (overlap disabled)


def compute_overlap_strategy(
    pcm_frames: int,
    slot_frames: int,
    max_overlap_frames: int,
    is_last_segment: bool = False,
    overlap_enabled: bool = True,
) -> tuple[str, int, int]:
    """Decide how to fit ``pcm_frames`` of TTS audio into a ``slot_frames`` slot.

    TASK 2P: hard-truncating segments that overshoot their slot leaves an
    audible "audio mozzato" artefact at end of phrase (15-25% of segments
    on dense voice-only content). Allowing a small overflow into the next
    segment's slot — capped at ``max_overlap_frames`` — preserves the
    tail of the phrase while keeping any leftover within a perceptually
    safe window. The actual mixing is performed by the caller's memmap
    accumulator, which sums int32 samples so the overflow naturally
    crossfades with whatever the next segment writes there.

    Parameters
    ----------
    pcm_frames:
        Length of the TTS pcm buffer, in samples (per-channel count).
    slot_frames:
        Length of the segment's allocated slot, in samples.
    max_overlap_frames:
        Maximum permitted overflow into the following segment's slot, in
        samples. Typical value: 0.40 * sample_rate (i.e. 400 ms).
    is_last_segment:
        When True the segment has no neighbour to overlap into, so the
        function downgrades any overlap strategy to a plain truncate. This
        keeps the very end of the dubbed track from running past
        ``total_duration`` (the memmap is bounded, but a trailing tail
        spilling into silent padding adds nothing useful).
    overlap_enabled:
        When False the function always returns the legacy ``"truncate"``
        strategy even for mild overshoots. Wired to the
        ``--no-overlap-fade`` CLI flag.

    Returns
    -------
    tuple ``(strategy, target_frames, fade_frames)``:
        * ``strategy`` — one of ``"fit"``, ``"overlap_clean"``,
          ``"overlap_truncate"``, ``"truncate"``.
        * ``target_frames`` — the number of pcm frames the caller should
          keep (``pcm_frames`` for ``fit``/``overlap_clean``, the capped
          length for the truncating strategies).
        * ``fade_frames`` — number of samples of trailing fade-out the
          caller should apply on the kept pcm to taper the tail. ``0``
          when no fade is needed (``fit``).

    The function is pure: no I/O, no globals, no float math beyond simple
    comparisons, so it is trivially testable without audio fixtures.
    """
    if pcm_frames <= 0 or slot_frames <= 0:
        # Defensive: nothing to mix or impossible slot. Caller will skip
        # the segment, but returning "fit" with zero-length keeps the
        # contract simple (no None branches).
        return (_STRAT_FIT, max(pcm_frames, 0), 0)

    overshoot = pcm_frames - slot_frames
    if overshoot <= 0:
        return (_STRAT_FIT, pcm_frames, 0)

    # Legacy path: overlap disabled by CLI, or this is the last segment
    # so there is no neighbour slot to spill into.
    if not overlap_enabled or is_last_segment:
        # Legacy fade-out matches the existing 200ms cap (TASK 2S).
        # The caller already knows the fade ramp length: we hand back a
        # safe upper bound (1/4 of the kept pcm, capped at 200ms-equivalent
        # via max_overlap_frames/2 — caller clamps further if needed).
        fade = min(max_overlap_frames // 2, slot_frames // 4)
        return (_STRAT_TRUNCATE, slot_frames, max(1, fade))

    if overshoot <= max_overlap_frames:
        # Overlap mode: keep the full pcm. The trailing fade lasts at most
        # OVERLAP_FADE_FRAMES = max_overlap_frames // 2 (i.e. 200ms when
        # the cap is 400ms), or the full overshoot when shorter.
        fade = min(max_overlap_frames // 2, overshoot)
        # Never fade longer than the pcm itself.
        fade = min(fade, pcm_frames)
        return (_STRAT_OVERLAP_CLEAN, pcm_frames, max(1, fade))

    # Beyond the overlap budget: cap at slot+max_overlap and fade. This
    # protects against TTS hallucinations that would otherwise shout over
    # several subsequent segments.
    target = slot_frames + max_overlap_frames
    fade = min(max_overlap_frames // 2, target // 4)
    return (_STRAT_OVERLAP_TRUNCATE, target, max(1, fade))
