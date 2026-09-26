# Action Plan

## README localization handoff to Claude Code (2026-09-26)

### Why this changed

The operator asked for complete translations of the main README, with every
section in its corresponding position, not shortened overviews. They also
requested a dedicated directory because 25 translated files cluttered the
GitHub repository root. This is a documentation change, not a player or
translation-runtime change.

### Delivered structure

- `README.md` remains the complete English source at the repository root.
- `docs/i18n/README.md` is the language index; `docs/i18n/README.<lang>.md`
  contains each of the 25 complete translations (26 languages including English).
- The previous root-level translated READMEs and `README_LANGUAGES.md` have
  been replaced by this structure. Their historical versions remain in Git.
- Each page keeps the original section order, tables, lists, installation and
  uninstall instructions, executable examples, CLI options and license notes.
  Language navigation and relative technical-document links are rebased for
  the new directory. Native language names remain visible in the selector.
- `tests/test_readme_translations.py` checks all 25 files, ordered structure,
  table dimensions, commands, per-section inline code, link destinations and
  long accidentally untranslated English passages. CI also runs on changes to
  `README.md` and `docs/i18n/**`.

### Maintenance instructions

Update the corresponding sections in **all 25 translations** whenever the
English README changes. Keep command syntax, paths, model identifiers and
URLs unchanged except for relative-link rebasing. Do not recreate short
language summaries or move these files back into the repository root.
Run `python -m unittest discover -s tests -p test_readme_translations.py -v`
before committing documentation changes.

Translations used machine-translation assistance followed by editorial and
technical corrections. Structural tests do not certify native-level fluency
or semantic equivalence; further native-language proofreading is welcome.
This delivery does not complete the pending live-audio acceptance, overlap/fade,
hardware-aware model selection or ElevenLabs work described below.

### Verification

All six README checks passed across 25 translations. A separate Markdown-render
audit matched the English page: 30 headings, 9 tables, 8 fenced examples,
42 rendered links and 103 inline-code spans per page. Compilation and
`git diff --check` passed. The complete unittest suite ran 1,381 tests:
Xvfb OK (15 skipped), no display OK (118 skipped). An initial run on the physical
desktop failed in Tk theme/teardown tests; isolated reruns passed without runtime
changes. Remote CI status is recorded in the GitHub check for this delivery.

## Live P5 handoff to Claude Code (2026-09-26)

### Latest published checkpoint

- `696e6a1`: startup hold, pre-lock speech retention, pacer clip recovery, and
  linked README pages covering 26 languages. Those pages were initially quick
  starts; the subsequent README localization delivery above replaces them with
  complete translations in `docs/i18n/`.
- Verification: 1,360 pytest tests passed, 15 skipped, 864 subtests passed;
  the existing backup directory was excluded from collection. Translation links
  and `git diff --check` passed. [GitHub CI](https://github.com/HeartB1t/VideoTranslatorAI/actions/runs/36268476286)
  completed successfully for this commit.
- Operator feedback: after reconsidering the selected live/delayed mode, the
  operator reported that playback worked perfectly and authorized commit/push.
  Record this as a successful manual playback test, not full acceptance of
  delayed-mode buffering, pause/seek, Windows, or every language/engine pair.
- Hardware-aware model selection and ElevenLabs integration are documented
  below as planned features; neither has been implemented in this delivery.

The earlier delivery notes and verification counts below are historical.

Operator test follow-up: live Italian-to-English translation reported working,
but overlapping original speech was distracting. Added a running-row checkbox
"Mute original audio" (all 26 languages), also visible before starting beside
the dub/subtitles controls. The preselected value is applied at session launch.
It silences the entire original
soundtrack, including music, independently of translated speech, ducking and
the master mute. It resets when the live session ends. This is a manual audio
choice; the overlap/fade work below remains open.

Base commit before this delivery: `65e91fd`. The following fixes and original-audio
mute control form the delivery requested by the operator. This is an implementation
checkpoint, not completed P5 acceptance. Local history and detailed evidence are in
`_dev/CHANGELOG.md`, entry `live-p5-codex-handoff` (that file is gitignored).

### Implemented and checked locally

- Finding 9, software path: GUI pause intents are queued to the live scheduler;
  only the scheduler writes pause during a live session. The user's pause flag
  is distinct from the pacer's buffering flag. mpv pause observations never feed
  back into user intent. Initial pause and the current playhead are passed at launch.
- Live seek uses the same absolute target for the player and session; dragging
  invalidates the clock and commits one exact seek on release. Player Stop stops
  the live session too.
- A seek into a cached caption leaves the producer generation unchanged. Outside
  coverage, the existing decoder worker reopens at `max(0, target - 0.5)` with a
  new generation. Workers remain available after EOF; Whisper is not reloaded.
  Each producer owns its mutable segmenter/assembler. Old ASR/MT results are
  rejected, including results that finish during a seek. EOF is generation-tagged
  and reaches the pacer after MT finishes, rather than when decoding alone finishes.
- Scheduler: cached clips replay; in-flight TTS remains in-flight across a seek
  instead of rewriting the same clip path. A playback-restart without a time jump
  no longer abandons a preloaded clip. A user pause prevents voice playback;
  `696e6a1` adds an exception for recovery during a pacer-owned pause.
- Finding 10, duration feedback only: accepted successful clips update
  `EdgeDurationModel.observe()` with audible duration and rate. Rate estimation
  and synthesis use the shared `sanitize_for_tts` text.
- Async TTS shutdown cancels and awaits pending tasks, shuts down async generators
  and the executor, then closes the loop. The worker removes partial files after
  closing their handles, including when `stop()` times out on the caller.
- Regression tests also cover prior fixes: mixer mute, volume restoration, and
  keeping/stopping the TTS worker across dub toggles.

Verification including the mute control: 1,367 tests discovered; Xvfb run OK (15
skipped), no-DISPLAY run OK (116 skipped), py_compile and `git diff --check` OK.
The idle-row control was also checked visually in a complete app under Xvfb.
These are local checks, not listening tests or Windows acceptance; remote CI is
recorded separately after publication.

### Completed startup and clip-recovery fixes

These fixes are implemented and covered by automated regression tests. They are
not pending implementation; real audio and platform acceptance remain separate
open tasks in the acceptance section below.

- [x] Live startup gate and initial speech preservation.
   URL playback now loads paused, and file playback is paused at its current media
   position before the session starts. The gate releases after an initial translated
   output (and synthesized clip when dubbing is enabled), two seconds of confirmed
   VAD silence, or source EOF. Auto-detected language retains pre-lock utterances
   and sends them through translation in order after `LanguageLock` decides.
   Preparation state is shown through the existing loading/detecting/buffering
   statuses; Stop cancels the session and model/pipeline errors use the existing
   error path. Synthesis failures are logged and surface the existing TTS warning.
   Silence can release playback before the first speech; the pacer and
   late-clip recovery then keep the playhead coordinated. Real audio acceptance is
   still pending.
- [x] Late clip handling coordinated with the pacer. The
   session now distinguishes a pacer-owned pause from a user pause. In delayed
   mode, a ready clip that is late only because the pacer held the media clock can
   be played as a recovery clip, while the picture remains held; clips older than
   the configured media-time freshness bound still drop. Recovery remains ordered
   and does not change the separate live-mode lag policy. Real audio acceptance is
   still pending.

### Remaining implementation work, in order

Only unfinished implementation work is listed here. Do not reimplement the
completed fixes above merely because their audio acceptance is still pending.

1. Finding 10 overlap policy, spec 4.11: wait up to 0.6 s, speed the current clip
   when needed, fade for 0.18 s if the remaining wait would exceed 1 s. Wire
   `ClipSpeed` and `FadeRamp` into actual execution; `StopClip.fade_s` is still
   ignored. Test two adjacent clips, EOF during fade, pause during overlap,
   mute during fade, and stop/seek cancelling the fade.
2. Voice backend creation on a worker, with completion on Tk. Capture the player
   backend/bridge identity before starting; reject and terminate stale results
   after Stop, close, media change or VO fallback. Cover enabling dub after a
   session started with dub disabled (the voice backend may not exist yet).
3. VO fallback: stop/join the session and terminate the old voice backend before
   closing/replacing its bridge. Never reuse a voice backend bound to the old
   bridge. Test all fallback branches and closing during replacement.
4. Bound active scheduler segments to the design's 2,000 entries and avoid
   repeatedly scanning an unbounded history at 50 Hz. Preserve file clip cache
   replay, in-flight results and caption coverage. Add a long-video test.
5. Audit dub-toggle state and dropped metrics, plus remaining dormant paths:
   `duck_af`, `LeadCalibrator`, voice-time-pos observer. Wire required behavior or
   explicitly retire unused paths. Do not mark all P2 12-21 closed from this list;
   reconcile each item against the original Fable review.
6. Persistent `falling_behind` delay adjustment remains open. Verify actual engine
   and delay changes during a running session (control/status updates alone are
   not evidence of a producer configuration change).

For each item: add behavioral regression tests, implement, reread the changed
functions, run targeted tests and then the project checks. Update this section
and `_dev/CHANGELOG.md` with the actual result. Audio acceptance does not block
writing deterministic software tests; it still blocks calling P5 validated.

### Acceptance and later phases still open

- Listening test on real video: two mpv instances, audible duck, pause/resume,
  forward/backward seek and five clips after each seek, dub toggles and shutdown.
- S3 measurements of duck latency and voice lead; current values are provisional.
- Windows: second mpv, Edge-TTS, clip paths, rename/cleanup and rapid seek/stop.
- S1 maximize on the operator's real window manager.
- P6 growing live broadcasts and S2 ingest acceptance; resolved VOD URLs are not
  the P6 live-stream implementation. P7 parity and ComponentInstaller remain.

### Operator live-test bug checklist (2026-09-26)

Checked boxes record implemented changes and automated regression checks.
The operator reported successful playback; the full acceptance matrix above
remains open. TLS/reconnect diagnosis is deferred separately below.

- [x] Prevent playback from advancing before live models and the initial dubbed
  audio are ready; retain and process early speech while automatic language
  detection locks. See the startup gate under
  [completed fixes](#completed-startup-and-clip-recovery-fixes).
  Unit tests pass; listen-test pending.
- [x] Recover late dubbed clips when the player is waiting on the pacer, without
  speaking them out of order or letting voice delay grow without bound. See late
  clip handling under [completed fixes](#completed-startup-and-clip-recovery-fixes).
  Unit tests pass; listen-test pending.

Deferred diagnosis, outside the current fix scope: mpv reported TLS connection
resets/reconnects, and the log contains repeated URL resolution messages. The
first may be an upstream/network interruption; the second may be repeated user
starts. Revisit after the startup and dubbed-clip synchronization fixes.

## Future feature - Hardware-aware AI model selection

User proposal (2026-09-26): let users discover, download and choose newer AI
models, with recommendations and settings tailored to their PC hardware. This is
a planned feature, not an implementation commitment to any specific model or
provider. Research supported models, licences, platform support and current
releases when implementation begins; do not hard-code claims that models are
"latest" in this roadmap.

### Goals

- Detect available CPU, system RAM, GPU/backend, usable VRAM and disk space, then
  recommend compatible options for speed, balanced use or quality.
- Cover the actual pipeline stages separately: speech recognition, translation
  for the selected language pair, and speech synthesis. Some current choices
  (for example Google translation and Edge-TTS) are online services, not
  downloadable local models; label their network and account requirements rather
  than presenting them as hardware-selected downloads.
- Let users compare measured first-result latency, sustained real-time factor,
  memory use, language coverage, download size and whether an internet connection
  is needed. Hardware detection alone is not a performance benchmark.
- Keep a known-good configuration and allow users to switch back after testing a
  new option. Installing or changing a model requires explicit user choice.

### Proposed implementation order

1. Fix live startup and synchronization first: hold playback while required
   components prepare and the initial audio buffer is ready; preserve early
   recognized speech while automatic source-language detection locks; make the
   pacer and late-clip policy share the reason playback is paused. A faster model
   must not be used to hide these timing/state bugs.
2. Inventory the model interfaces already used by ASR, translation and TTS.
   Identify interchangeable backends and define per-stage compatibility,
   fallback and cache/version metadata without changing the defaults.
3. Add read-only hardware discovery with graceful CPU-only and unsupported-GPU
   paths. Show detected hardware and recommendations before downloading anything.
4. Add a curated model catalogue with pinned versions, checksums, licence and
   language metadata, disk/VRAM requirements, platform support and download
   source. Use resumable downloads, temporary files plus atomic promotion, and
   retain the previous working model until the new one passes validation.
5. Add an opt-in short benchmark and report first-clip latency and sustained
   throughput for the chosen pipeline. Benchmarking should be cancellable and
   should not upload audio or hardware identifiers.
6. Integrate choices into profiles such as Speed, Balanced and Quality, while
   preserving manual per-stage selection and existing settings. Test Windows
   and Linux, offline operation for local models, insufficient disk/VRAM, failed
   downloads, checksum mismatch, rollback and model initialization failure.

### Acceptance criteria

- Recommendations explain their evidence and distinguish local models from
  online services; users can ignore them and keep current settings.
- The app never silently downloads, replaces or upgrades a model. Downloads are
  verified, cancellable, resumable and recoverable without destroying the last
  working configuration.
- A selected model is loaded and warmed before live playback begins; startup
  status reports preparation and the first speech buffer. Model choice is not
  considered a fix for late-clip drops unless timing tests confirm that behavior.
- Benchmarks measure real startup and sustained pipeline timing on the machine,
  without transmitting user data.

## Future feature - ElevenLabs voices for live dubbing

Integrate ElevenLabs as an optional live TTS provider so users can choose more
natural multilingual voices. Treat language support as model- and voice-specific:
the current product language list must be intersected with the provider's current
model capabilities, and voice/accent fit must be visible. ElevenLabs currently
documents multilingual models with different language coverage and latency, and
the TTS API accepts a voice ID, model ID and optional language code. Re-check the
official catalog when implementation begins rather than hard-coding today's
coverage. Sources: [models](https://elevenlabs.io/docs/overview/models), [TTS API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert), [language and accent guidance](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-do-i-select-the-language-and-accent).

### Integration requirements

- Add an optional `ElevenLabs` engine/provider alongside local and existing TTS
  choices; retain existing providers as free/offline fallbacks.
- Let users configure and validate their API key without committing or logging
  it. Make network use, account/quota requirements, privacy implications and
  per-character cost clear before sending translated text.
- Load/select voices from the provider catalog, showing supported languages and
  voice/accent metadata; do not imply every voice is equally native in every
  language. Cache catalog data with an explicit refresh action.
- Select a compatible multilingual model based on latency/quality preference;
  expose model choice only when the account supports it. Return synthesized audio
  through the current clip/scheduler interface, preserving deadlines, cancellation,
  retry limits, audio format conversion and file cleanup.
- Keep all provider I/O off the Tk thread. Handle rate limits, quota exhaustion,
  authentication errors, network loss and model unavailability with localized
  status and a user-selectable fallback provider.
- Test API behavior with mocked responses, no-secret logging, supported/unsupported
  language and voice combinations, timeout/cancel, format conversion, scheduler
  deadlines and offline fallback. Never require a live paid API in CI.

The baseline/action items below are historical; environment blocker statements
must be rechecked before treating them as current machine state.

## Baseline

- Backup created before edits: `.project_backups/VideoTranslatorAI_backup_20260616_235500.tar.gz`.
- Unit suite baseline was passing before changes.
- Current package entry points: `videotranslatorai`, `videotranslator-ai`,
  `video-translator-ai`, and `python -m videotranslator`.

## P0 - Safety And Verification

1. Keep every structural change covered by targeted unit tests first.
2. Keep the default CI lightweight: compile, metadata dry-run, unit suite.
3. Put real AI/GPU checks behind `VTAI_RUN_HEAVY_SMOKE=1`.

## P1 - Monolith Bottleneck

1. Extract CLI parser and job builder into `videotranslator.cli`.
2. Make GUI, CLI and batch flows construct `TranslationJobConfig`.
3. Remove duplicated option/default resolution from GUI worker paths.
4. Add contract tests that every `TranslationJobConfig` field reaches
   `translate_video`.
5. Inject final output operations into `PipelineRuntime` so the runner has no
   hidden subprocess/file dependencies.

## P1 - Packaging

1. Keep `pyproject.toml` as the package source of truth.
2. Preserve legacy `python video_translator_gui.py` while supporting installed
   commands.
3. Move GUI assets into package data through `importlib.resources` in a later
   pass; the current GUI still falls back cleanly if icons are absent.

## P1 - Real Pipeline Smoke

1. Maintain `tests/test_heavy_smoke.py` as opt-in empirical coverage.
2. Run Wav2Lip import smoke after dependency changes.
3. Run Whisper synthetic speech smoke when model/cache state allows it.
4. Run CUDA and Ollama smoke only when the driver and daemon are actually ready.

## Current Environment Blockers

- Wav2Lip Python face stack was installed and now imports successfully.
- Torch is installed with CUDA 12.4 wheels, but `torch.cuda.is_available()` is
  currently false and `nvidia-smi` intermittently fails to communicate with the
  driver.
- Ollama binary is present, but `ollama list` reports that the daemon is not
  responding.
