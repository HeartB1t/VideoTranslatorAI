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
