# Integrated Player P2: File Player Implementation Plan (lean)

**Goal:** play local files in the left pane: preview of the selected Input item, transport,
seek bar, volume, snapshot, open folder, playlist popup, fullscreen, keyboard and mouse,
theme and language hooks, the VO profile chain, release before jobs and a clean close.

**Spec (binding):** `docs/superpowers/specs/2026-09-25-video-player-live-design.md`, phase P2
in section 9. Interfaces: 2.2 (`player_engine.py` pure parts and adapter, `player_core.py`,
`player_settings.py`, `platforms.py` additions), 2.3 (Tk glue), 2.4 (threads), 2.5 (config
keys), 2.6 (P2 strings), 3.1 (layout, lifecycle, options, VO chain), 3.2 (F1 preview), 3.6
(file lifecycle), 3.7 (snapshot, folder, playlist, keys, mouse), 6.4 (close), 7.2/7.5 (tests).
S1 is GO (in-process VO re-creation enabled on Linux).

**Style (lean plan):** each task lists scope, the spec sections that define it, and the tests
that must fail first. The code is written from the spec during execution, not copied here.

## Global Constraints

- Executed by the controller without subagents, one task at a time: TDD, self-review of the
  diff (touched functions read in full), verification, commit, push, CI check. Codex second
  opinion on threads, the mpv adapter and the close sequence.
- Conventional commits, no `Co-Authored-By` trailer, no em/en dash anywhere.
- Every user-visible string in `videotranslator/ui_strings_player.py`, 26 languages, coverage
  tests green; brand names untranslated.
- Windows + Linux parity; Windows-only behaviour gets a pure test and an operator item.
- Tests: `python3 -m unittest discover -s tests`; hermetic for CI (no libmpv, no display, no
  network): pure modules and `InMemoryBackend`; Tk tests skip without a display; real-mpv
  tests are opt-in (`VTAI_PLAYER_REAL=1`) with the unpacked libmpv 0.41 under
  `_dev/research/player-2026-09-25/probe/`, on a private Xvfb only.
- The GUI file grows by wiring only; logic lives in the new modules.
- No Tk call from any mpv thread: callbacks write the `EventBridge` only; Tk drains it.

## Task 1: `player_settings.py`

Scope: `PlayerSettings`, `LiveSettings`, `normalize_player_settings`,
`normalize_live_settings`, `settings_to_config` (spec 2.2, 2.5). Pure.
Tests: defaults for an empty config; every malformed value falls back; round trip through
`settings_to_config`; `vo_profile` accepted only from `VO_PROFILES[sys_platform]`.

## Task 2: `player_core.py` pure helpers

Scope: `format_clock`, `x_to_seconds`, `seconds_to_x`, `pick_audio_track_ids`,
`snapshot_path`, `controls_visible` (reflow at 360/460/700 px), `PLAYER_KEYS`,
`handles_player_key`, `mouse_action` (2- and 3-char states, only `state[0]`),
`playlist_groups`, `STATUS_KEYS` (spec 2.2, 3.7).
Tests: table tests for each; `handles_player_key` False for every interactive class of the
spec list; `STATUS_KEYS` values exist in all 26 languages (after Task 5).

## Task 3: `player_engine.py` pure parts

Scope: `EventBridge`, `PlaybackClock`, `CommandQueue`, `MixState`/`VolumeMixer`,
`VO_PROFILES`, `build_mpv_options`, `next_vo_profile`, `detect_vo_failure`,
`duck_channel_for`, `af_duck_command` (spec 2.2, 3.1 option table). `InMemoryBackend`
implementing `PlayerBackend` for tests.
Tests: bridge coalescing and bounded deque (log entries dropped first), unknown event ids
dropped; clock ignores values while seeking or while a restart is expected; queue key
replacement and max size; option table per kind and platform; VO chain skips unaccepted
profiles; failure strings detected only after the grace period.

## Task 4: `PlayerController` state machine

Scope: `MediaItem`, `PlayerState`, `PlayerController` (load, playlist, play/pause, stop,
next/previous, seek with keyframes while dragging, relative seek, volume, mute, audio
selection, subtitles visibility, snapshot, `remove_items`, `release_for_job`, `release`,
`is_released`, `apply_events`, `attach_backend` replaying a pending load) (spec 2.2, 3.2,
3.6). Driven by `InMemoryBackend`.
Tests: every intent produces the expected backend calls and state; removal of the loaded
item stops and lifts the placeholder; release rules; settings saved through `save`.

## Task 5: P2 strings

Scope: the P2 keys of spec 2.6 (controls, tooltips, messages, playlist, snapshot, errors) in
all 26 languages in `ui_strings_player.py`; `STATUS_KEYS` coverage.
Tests: the existing coverage tests plus `STATUS_KEYS` values in every language.

## Task 6: `MpvBackend`, `X11ErrorGuard`, `platforms.reveal_in_file_manager`

Scope: the real adapter (mpv-cmd thread with `CommandQueue`, properties written before
`command("loadfile", uri, "replace")`, observers and key bindings into the bridge,
`screenshot`, `terminate(timeout_s)` off Tk), `create_video_backend`, `X11ErrorGuard`
(capture before the first VO init, restore after terminate and after a detected VO
failure), `reveal_in_file_manager` (Linux xdg-open of the folder, Windows
`explorer /select,"path"`) (spec 2.2, 3.1, 3.7, 6.4).
Tests: hermetic tests with fake `mpv` module objects; opt-in real test on Xvfb with the
unpacked libmpv (load, play, pause, seek, screenshot, terminate under 2 s, VO chain with EGL
removed and trigger T1 survived).

## Task 7: `PlayerPanel` controls

Scope: extend `player_panel_tk.py`: seek bar (canvas), time labels, now playing, transport
(previous, back, stop, play/pause, forward, next), snapshot, open folder, playlist popup,
volume slider, fullscreen button, icon shapes, reflow, focus rings, theme and language hooks
(spec 2.3, 3.7).
Tests (Tk, skip without display, `InMemoryBackend`): every button and key does its action;
reflow hides exactly the planned controls; theme switch recolours, language switch relabels
controls and tooltips; Tab reaches every control with a visible focus ring.

## Task 8: GUI wiring

Scope: panel build with the controller; player-init worker (load_mpv off Tk, backend
created on the Tk-owned wid); F1 preview on `<<ListboxSelect>>`; Input removal and clear;
release before jobs; keyboard routing through `handles_player_key`; mouse via mpv key
bindings; fullscreen layout (grid_remove of header, card column, log, progress); the close
sequence (spec 3.1, 3.2, 3.6, 6.4); badge and placeholder from P1 kept.
Tests: Tk tests with `InMemoryBackend` (preview, removal, focus rules: space in the URL box,
Start button, volume slider); close stops the backend first.

## Task 9: evidence

Real-mpv checks on a private Xvfb with the unpacked libmpv 0.41: preview latency (median of
10 selections under 1 s), 20 closes during playback under 2 s each, VO chain fallback,
screenshots of the player at 1100x780 and in fullscreen. Recorded in `## Evidence` below and
in `_dev/CHANGELOG.md`. Operator items: x11egl on the real NVIDIA display, Windows 11 at
100 % and 150 % DPI, Wayland (S5).

## Evidence

Recorded on 2026-09-25 with libmpv 0.41.0 and python-mpv 1.0.8 on a private
1400x900 Xvfb display with xfwm4. The harness and raw JSON are under
`_dev/player_p2_app_evidence.py` and
`_dev/screenshots/player-p2-2026-09-25/`.

- Preview latency: 10 alternating real loads, median 0.4532 s and maximum 0.6013 s.
  Pass: median is below 1 s.
- Close: 20 independent processes, each with one playing App and one Tk interpreter;
  20/20 clean closes below 2 s, maximum 0.1595 s. The backend terminated before the
  host was destroyed.
- VO fallback: forced `x11egl` failure with an invalid EGL vendor file; the App detected
  it, restored the captured X11 handler, recreated once with `x11sw`, received fresh
  `video-params`, and closed in 0.1601 s. Pass.
- Native adapter smoke: 2/2 passed (embedded load, seek, snapshot, bounded terminate;
  forced EGL failure, `x11sw` fallback and deliberate X error survived).
- `app-1100x780.png`: pass. The selected file is loaded, the placeholder is unmapped,
  duration and all controls are visible, and the card column does not resize the video.
- `app-fullscreen.png`: pass. xfwm4 reports 1400x900+0+0; header, card column, log,
  progress, padding and border are absent, while the controls remain reachable.
- Automated gate after the visual fix: 1040 tests passed with 6 skips both headless and
  under Xvfb; py_compile, forbidden-dash scan and `git diff --check` passed.

Operator items that need hardware outside this environment remain: `x11egl` on the real
NVIDIA display, Windows 11 at 100 and 150 percent DPI, and a Wayland desktop. These are
platform checks, not known failures; Linux X11 and the software fallback are green.
