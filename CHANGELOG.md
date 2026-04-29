# Changelog

All notable changes to this project are listed here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [1.7] — 2026-04-29

### Added

- **Modular `videotranslator/` package** — the 9000-line single file is now
  backed by 12 isolated modules (translation, audio stretch, sanitizers,
  metrics, segments, …) covered by 229 unit tests so individual stages can
  evolve and be tested independently. The legacy entry point
  `video_translator_gui.py` continues to expose the same CLI and GUI.
- **Length re-prompt loop on Ollama** — when an LLM translation overshoots
  the audio slot it is queried again with an explicit "rewrite shorter,
  max N chars" prompt. Empirical effect on the calibration video set:
  −35% character count on outliers, ≈ 15–20% fewer "audibly accelerated"
  segments end-to-end.
- **Context-aware sliding window** — every Ollama translation prompt now
  includes the previous and next segment as do-not-translate context, so
  qwen3 stops mistranslating dangling fragments at segment boundaries
  (`stick.` left in English, vocatives confused with subjects, etc.).
- **Rubber Band CLI tier dispatcher** — segments in the `1.15 ≤ ratio ≤ 1.50`
  band are now stretched with `rubberband` (pitch-preserving) instead of
  ffmpeg `atempo` (pitch-altering chipmunk). Install with
  `apt install rubberband-cli` (Linux) or `brew install rubberband`
  (macOS); the pipeline auto-falls back to `atempo` when the binary is
  not on `PATH`.
- **Smart Ollama model fallback** — if the configured Ollama tag is not
  installed but the daemon has another usable model (e.g. `qwen3:14b`),
  the pipeline now uses it instead of silently dropping to Google
  Translate. The substitution is logged with the original and the
  resolved tag.
- **TTS punctuation sanitizer** — XTTS no longer verbalises `:`, `;`,
  em-dash, en-dash, double hyphen, Unicode ellipsis and ASCII `...`.
  Digit-flanked colons (`10:30`, `1:23:45`, `3:1`) are preserved so they
  read as numbers, not as comma-separated parts.
- **Wav2Lip face pre-check** — when lip-sync is enabled the pipeline now
  samples 15 frames with OpenCV Haar Cascade before invoking Wav2Lip,
  and skips the 30–60s inference cleanly on voice-only / no-face content
  (podcasts, screen recordings, voice-over animations).
- **Smart slot expansion (silence borrowing)** — segments predicted to
  overshoot their audio slot can borrow time from an adjacent silence
  gap or from a neighbour that has slack. Opt-out via
  `--no-slot-expansion`.
- **Per-segment metrics CSV** — `build_dubbed_track` writes a
  `*_metrics.csv` next to every dub with 15 columns (slot duration,
  source/target chars, length-retry flags, TTS duration, pre-stretch
  ratio, stretch engine, text excerpts) for offline P90/P95 analysis
  across runs.
- **Pre-flight difficulty estimator** — before translation the pipeline
  prints a `[difficulty]` line predicting the expected P90 stretch ratio
  and a category (`fluent` / `some accelerated` / `most accelerated`),
  so the user knows upfront what to expect.
- **Standalone module CLIs** — four user-facing modules expose
  `python3 -m videotranslator.<name>` invocations for ad-hoc usage:
  `face_detector`, `metrics_csv`, `tts_text_sanitizer`,
  `difficulty_detector`.

### Changed

- The qwen3 thinking-mode toggle hint now reads `~10x slower` (was `~5x`)
  to match observed end-to-end timings on dense video content.
- The thinking-mode `num_predict` budget for Qwen3 is bumped automatically
  on the empty-response retry, so chain-of-thought tokens do not exhaust
  the budget before the answer is emitted.

### Fixed

- `_ollama_strip_preamble` correctly handles closed `<think>` blocks,
  orphan `<think>` (truncated output), variant tags `<thinking>` /
  `<reasoning>`, and translation-after-double-newline cases. Covered by
  12 dedicated unit tests.
- The pre-flight difficulty estimator now divides by an anticipated
  XTTS adaptive-speed factor so the predicted P90 aligns with the
  observed `pre_stretch_ratio` (gap reduced from +0.58 to +0.23 on the
  calibration runs).

### Calibration honesty

The pipeline accepts 26 target languages but the difficulty estimator's
`tts_speed_factor` table is empirically calibrated only for Italian
(three production runs). For other targets the table currently uses
plausible defaults (1.10 for most languages, 1.05 for logographic
scripts). Difficulty warnings on non-IT targets may be slightly
conservative until per-language calibration data accumulates.

### Backwards compatibility

The legacy `video_translator_gui.py` entry point keeps the same CLI flags
and GUI layout; existing user configs in `~/.videotranslatorai_config.json`
continue to work. Phase-2 features can be disabled individually:
- `--no-slot-expansion` disables the smart slot expansion (TASK 2E).
- `--ollama-no-slot-aware` reverts the Ollama prompt to the simpler form.
- `--no-difficulty-detector` (planned in v1.8) will silence the pre-flight
  warning if needed.

The optional `rubberband-cli` system dependency is detected at startup;
when missing the pipeline transparently falls back to ffmpeg `atempo` —
no configuration change required.
