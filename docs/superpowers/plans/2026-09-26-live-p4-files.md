# Live P4: Real-time translation of local files, subtitles

**Status:** pure foundation IMPLEMENTED and verified (2026-09-26 autonomous
session); integration, GUI, i18n and real-hardware acceptance remain. Needs P2
(done). Does NOT need P3 or the S2 stream spike.

## Progress (2026-09-26)

Done, each its own commit, TDD, suite green (1154 tests), CI green:

- `live_health.py` (`dddc64a`): CircuitBreaker, RollingStats, VTAI_LIVE_FAULTS parser.
- `live_segment.py` (`5092f3a`): UtteranceSegmenter, SentenceAssembler.
- `live_sync.py` (`a8cc621`): FilePacer, derive_live_timing, recommended_delay_s,
  live_distance_s (file side; stream EdgeEstimator/DelayController still P6).
- `live_translate.py` (`9b4b0c9`): EN_LEGS, marian_route, marian_is_cached, TIMEOUTS_S.
- `live_asr.py` (`34b2321`): decoder_time, HallucinationFilter, LanguageLock (pure
  parts; PyAV/onnxruntime/Whisper classes still to add for real hardware).
- `live_scheduler.py` (`e4c8165`, `f993473`): caption wrap/paginate/ASS render, and
  DubScheduler caption path (media-time caption emission, ready_until, on_seek).

Remaining for P4 (see the split below): the live_* i18n vocabulary in 26 languages
plus live_health's STATUS/WARN/ERROR code maps (blocked on the i18n literal-key
scanner); live_asr ML classes; live_session wiring; live_bar_tk + player button;
ComponentInstaller live deps; the DubScheduler dub path is P5. All acceptance
items in section 9 need real GPU/CPU/media and Windows.

**Goal:** while a local file plays in the integrated player, translate it in near
real time and show translated captions, in two modes: Delayed (pre-roll, high
accuracy) and Live (never pauses, bounded lag). No dubbing yet (that is P5); P4
renders captions only.

**Binding spec:** `docs/superpowers/specs/2026-09-25-video-player-live-design.md`,
sections 4.1-4.4, 4.6-4.9, 4.11-4.12, 4.14-4.15, and the P4 block in section 9.
All acceptance items and their measuring methods live there; this plan does not
copy them, it enumerates the work and its order.

## Latency note (operator decision needed before P5/P6, NOT before P4)

The operator asked for "0.5 ms latency in real-time playback". That figure is not
physically reachable end to end for video (a frame lasts 16-33 ms) and it is not in
the approved design, whose real-time model is "like YouTube" with a delay slider.
Sub-millisecond only applies to single operations (frame copy via `memmove`,
~0.003 ms, already in the design) and to command responsiveness. P4 (captions) is
latency-tolerant: its targets are p90 caption offset <= 0.3 s (Delayed) and median
<= 2.5 s (Live). P5 (live voice) and P6 (live streams) are where "latency" must be
defined concretely with the operator before implementation.

## Modules (new, under `videotranslator/`)

Classified by how they can be verified here on this Linux dev machine.

Pure / TDD-able now (no ML stack, no GPU, no real media; fake clocks and injected
adapters, like the existing `live`-adjacent tests):

1. `live_health.py` - `CircuitBreaker`, `RollingStats`, status/warning/error code
   maps, `VTAI_LIVE_FAULTS` fault-injection parser. Spec 4.14, 4.9 fault codes.
2. `live_segment.py` - VAD utterance segmenter (state machine over frame
   probabilities) and sentence assembler. Spec 4.7. Pure given frame probabilities.
3. `live_sync.py` (FilePacer part only) - `FilePacer`, `derive_live_timing`,
   `recommended_delay_s`, `live_distance_s`, `EdgeEstimator`, `DelayController`.
   Spec 4.3, 4.4, 5.5. Pure with a fake clock. (Stream parts are P6.)
4. `live_scheduler.py` (captions only) - `DubScheduler` caption actions, caption
   wrap/paginate, ASS escaping mirroring `osd_libass.c:200-252` (CT12). Spec 4.11,
   4.12. Pure with a fake clock.
5. `live_translate.py` - per-sentence translators (Marian, Ollama, Google, DeepL)
   with hard timeouts; Marian route resolver (direct, tc-big, group, pivot);
   `marian_is_cached`; never a silent fallback engine. Spec 4.9, CT9. The route
   resolver and timeout wrapping are unit-testable with fake engines; real model
   calls are the hardware part.

Needs the ML stack / real media / GPU (verify partly here, fully as manual
acceptance):

6. `live_asr.py` - `AudioDecoder` (PyAV, lazy), `StreamingVad` (onnxruntime, lazy),
   `PersistentWhisper`, `LanguageLock`, `filter_hallucinations`. Spec 4.7, 4.8, C37.
   The decoder time-domain math (4.3) and the hallucination filter are unit-testable;
   real decode/VAD/ASR need media and models.
7. `live_session.py` (file source) - wires decoder -> segmenter -> ASR -> MT ->
   scheduler, the generation counter and seek handling (4.4), stop and stale-session
   cleanup with `session.lock` (4.15, F7), thread lifecycle.

GUI / integration (verify with Xvfb build + screenshot, like P0-P3):

8. `live_bar_tk.py` - idle and running rows; the player "translate live" button and
   its disabled tooltips; exclusivity messages (`live_err_busy`, `live_err_busy_job`,
   `live_err_editor_open`, `live_err_busy_install`); the online-engine warning
   (`live_warn_online_engine`); the Marian consent and pivot banner; the CPU
   fallback banner. Spec 4.2, 6.2, G1.
9. `ComponentInstaller` for live dependencies (PyAV, onnxruntime, silero) with the
   Windows path; live i18n keys in all 26 languages.

## Suggested order (one change per commit, TDD, green before push)

Foundation first (pure, fully verifiable here), then the ML/session wiring, then
the GUI, then acceptance:

P4.1 `live_health` (+tests) -> P4.2 `live_segment` (+tests) ->
P4.3 `live_sync` FilePacer (+tests) -> P4.4 `live_scheduler` captions (+tests) ->
P4.5 `live_translate` routes + timeouts (+tests, fake engines) ->
P4.6 `live_asr` decoder time-domain + hallucination filter (+tests) ->
P4.7 `live_session` file wiring, generation/seek, stop/lock (+tests with fakes) ->
P4.8 `live_bar_tk` + player button + exclusivity + banners (+Xvfb build, screenshot) ->
P4.9 `ComponentInstaller` live deps + 26-language i18n (+coverage test) ->
P4.10 acceptance (real GPU/CPU runs, fault injection, Ollama, auto-lang, Marian
routes, Stop VRAM/threads, Windows manual).

## What can proceed autonomously vs. what needs the operator

Autonomous (green, verifiable here): P4.1-P4.5, the unit-testable parts of P4.6-P4.7,
the Xvfb build of P4.8, and P4.9's i18n coverage. Each is a small commit with tests,
py_compile, unittest (no-DISPLAY and Xvfb), dash check, then push when green.

Needs the operator / real hardware (cannot be marked done here): the ASR/GPU/CPU
runs, fault-injection acceptance, Ollama unload, auto source-language lock on real
IT/JA samples, the Marian route runs, Stop VRAM/thread checks, and the whole Windows
item. Also: confirm the P4 caption modes and the "latency" meaning for P5/P6.

## Handoff instructions

1. Base at the time of writing: `bdee989` (P3 + output folder done, CI green).
2. Read the spec sections listed under "Binding spec" and the P4 block in section 9
   before touching code; they hold the exact APIs and acceptance methods.
3. Build strictly in the P4.1.. order; keep each module pure where the spec allows and
   inject adapters, so it is testable without the ML stack.
4. Do not start P5 (dub) or P6 (streams) from here; `live_sync` stream parts and
   `live_scheduler` dub actions are out of P4 scope.
5. Keep the two preexisting untracked paths untouched:
   `_backup_ui_redesign_20260617/` and `_demo_styles.py`.
