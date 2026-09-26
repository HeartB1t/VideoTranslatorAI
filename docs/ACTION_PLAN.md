# Action Plan

## Live P5 handoff to Claude Code (2026-09-26)

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
  no longer abandons a preloaded clip. A paused video cannot start a voice clip.
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

### Remaining implementation work, in order

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
