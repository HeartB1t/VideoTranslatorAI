# Player video integrato e traduzione in tempo reale - Design (BOZZA)

**Data:** 2026-09-25
**Stato:** BOZZA, non ancora approvata dall'operatore. Nessuna implementazione prima
dell'approvazione. Decisioni aperte nella sezione 10 (Q1-Q14), ciascuna con una risposta
consigliata.
**Motore:** libmpv via python-mpv (approccio A, approvato dall'operatore il 2026-09-25).
**Fonti:** le note di ricerca citate come [01]..[06], [CT], [CC], [parity], [sync], [mvp]
e gli script di prova `probe/` sono locali e fuori da git
(`_dev/research/player-2026-09-25/`, sulla macchina di sviluppo).
**Processo:** 6 ricerche parallele, 3 design indipendenti, 2 giudici, sintesi, critica
tecnica avversaria (con prove eseguite) e critica di completezza, versione finale.

Il documento che segue e' in inglese (lingua di lavoro dei sub-agenti).

---

# Integrated player and real-time translation: final design

Date: 2026-09-25. Status: final, for operator review (decisions in section 10). Engine:
libmpv via python-mpv (approach A, approved by the operator).

Basis: `design-draft.md` (the parity design with the best ideas of the sync and MVP designs
grafted in), corrected by the two adversarial critiques of the draft:
- [CT] `critique-technical.md`: every section 11 claim attacked with runs (RUN) against Kali
  `libmpv2 0.41.0` unpacked into `probe/lib` and the python-mpv 1.0.8 wheel unpacked into
  `probe/wheel`, headless or on a private Xvfb display, plus source reading (SRC). Probe
  scripts: `_dev/research/player-2026-09-25/probe/p1..p14*.py`.
- [CC] `critique-completeness.md`: the draft checked against the operator requirements,
  the project rules and the code at `c155227`; findings G1-G31, T1-T4.
Every refuted claim is corrected in place, and every gap is either filled or moved to
section 10 as an operator decision with a recommended answer. Section 0.3 maps each
critique finding to its fix. Section 11 lists every claim with its final status.

Evidence legend (used everywhere below):
- RUN: executed on this machine (by [04], [05] or [CT], or for this final design, [FD]);
- SRC: read in a primary source (file:line or URL given), not run;
- UNVERIFIED: neither; each one appears in section 11 with a fallback.

Ground truth: research notes 01-06 in this folder, cited [01]..[06]. The three competing
designs are cited [parity], [sync] and [mvp]. Code references are `file:line` at HEAD
`c155227` (re-checked today with `git rev-parse --short HEAD`). The working tree is clean
apart from untracked backups. `videotranslator/translation.py` and
`tests/test_translation.py` were not read, because another agent is editing them. Web facts
cite a URL or the note that verified them.

New local checks made for this final design [FD] (read-only, 2026-09-25):
- Marian coverage on the Hugging Face Hub, queried today through
  `https://huggingface.co/api/models/Helsinki-NLP/<name>` (HTTP 200 = exists) for every
  target language of `LANGUAGES` (video_translator_gui.py:41, 26 codes) against the hubs
  `en` and `it`, for `opus-mt-*`, `opus-mt-tc-big-*` and the group models. Results in 4.9.
- faster-whisper 1.2.1 metadata (`importlib.metadata.requires`) lists
  `onnxruntime<2,>=1.14` and `av>=11`; installed here: onnxruntime 1.24.4, PyAV 17.0.0,
  edge-tts 7.2.8.
- `_GlobalRedirect.write` falls back to `self._original.write` when the thread has no
  redirect (video_translator_gui.py:5248-5252), and `fileno()` returns
  `self._original.fileno()` (:5261-5262); the redirect is installed over the ORIGINAL
  `sys.stdout`/`sys.stderr` (:5711-5712), which are None under pythonw.
- `_install_deps` sets `self._running = True` (:5945), runs
  `pip install --break-system-packages` without `--user` (:5951-5952), and ends in
  `_install_done` (:6021), which chains `_check_optional_deps` after 300 ms (:6030).
- `_keyboard_operable(widget, action)` is a static method of `App` (:6175-6188).
- The Settings window is built at :7250-7330 (Appearance section, Language section, then
  the Reset/Close buttons at :7322-7330).
- The installer copies `assets\icon.ico`, `assets\icon.png` and `assets\icon_256.png`
  (setup_windows.bat:786-788).
- python-mpv 1.0.8 (`probe/wheel/mpv.py`): `terminate()` sets `self.handle = None` before
  destroying (:1163), so `__del__` (:1153-1155) is a no-op after an explicit terminate; the
  stream read callback copies byte by byte (:1869-1870); the ctypes stream types are
  `StreamReadFn`..`StreamOpenFn` (:505-520); `PLAYBACK_RESTART = 21` is an event id (:305).
- `ffprobe` is already a runtime tool of the pipeline (`videotranslator/output_media.py:47-63`).

Earlier local checks made for the draft (read-only, still valid):
- Wav2Lip muxes its `--audio` input into the output:
  `~/.local/share/wav2lip/Wav2Lip/inference.py:276`,
  `ffmpeg -y -i {args.audio} -i temp/result.avi -strict -2 -q:v 1 {outfile}`. The pipeline
  passes the vocals-only track (`videotranslator/pipeline_runner.py:506-510`), then
  `shutil.move(synced, output)` (:511). Lip-synced outputs therefore carry the dubbed
  voice WITHOUT background music today. VERIFIED by reading the source in the local
  checkout.
- faster-whisper 1.2.1 metadata requires `av>=11`; the installed PyAV is 17.0.0.
- Nothing in the GUI or the package calls `locale.setlocale/format/atof/localeconv`
  (grep). The process-wide `LC_NUMERIC=C` that python-mpv sets on Linux is therefore
  harmless.
- libmpv and python-mpv are still NOT installed system-wide on this machine
  (`find_library("mpv")` is None). Every mpv runtime behaviour comes from [04] and [CT]
  (runs with an unpacked Kali libmpv2 0.41.0; [CT] also unpacked 0.34.1 and 0.35.1 sources
  and python-mpv 1.0.4-1.0.8 wheels) or from source reading.
- Worker tests pin the arguments `_on_done` receives. `tests/test_ui_worker_outcomes.py:177,183`
  assert them exactly with `assert_called_once_with(False, UNAVAILABLE)` /
  `(False, None)`. `_fake_app()` (:36-52) has no `_on_job_outputs`.
- Backlog status: Tasks 1-5 are committed (`c4d76d9`, `4b3fb66`). The Task 5 review,
  Task 6 (theme detection off the Tk thread) and Task 7 (translated card titles) are
  pending in the cloud session (`.superpowers/sdd/2026-09-25-backlog-hardening/progress.md`).
- The operator ruled that GUI checks run under Xvfb while the operator uses the PC
  (same ledger).

---

## 0 Reading guide

### 0.1 Decisions at a glance

1. Two libmpv instances per app lifetime, both created lazily:
   - `video`: embedded through `wid`;
   - `voice`: audio only, for the live dub.
   mpv never touches the network (`ytdl=no`). Live sources reach it only through our own
   ingest.
2. The Tk thread never makes a synchronous libmpv call:
   - Tk-originated commands go through a per-instance `mpv-cmd` thread with coalescing
     keys;
   - mpv callbacks only write into an `EventBridge`;
   - Tk drains the bridge every 50 ms.
3. Code layout:
   - pure controllers;
   - one adapter module that touches `mpv`;
   - `*_tk.py` panels.
   The GUI file receives wiring only: at most +360 net lines across all phases, strings
   excluded (the draft's +300 plus about 60 for the critique fixes: the Settings section,
   the redirect factory, the live guards and flags).
4. Time domains:
   - files use the rebased player timeline (`rebase-start-time=yes`);
   - URL sessions use raw MPEG-TS PTS (`rebase-start-time=no`).
   Within each session, mpv, PyAV and the scheduler share one number with no offset
   (confirmed within 25 ms by [CT] C17/C18 RUN).
   - `time-pos` is trusted only when valid: never while `seeking`, never between one of our
     load/seek commands and the next `playback-restart` event, and (raw sessions) never
     below the first PTS. mpv reports a clamped value in those windows ([CT] finding 6).
   - A `PlaybackClock` epoch increments on each `playback-restart`; only an epoch change
     can trigger the scheduler's seek handling, so PTS gaps inside a stream never do.
5. Live streams use one ffmpeg ingest, which writes a chunked on-disk `LiveStore`. Two
   readers consume the store:
   - mpv, through the `vtlive://` stream protocol (primary transport), registered with
     raw ctypes callbacks that copy with `ctypes.memmove` (python-mpv's helper copies byte
     by byte in Python, [CT] finding 4);
   - PyAV, for the ASR.
   Spike S2 compares `vtlive://` with `lavf://file:` + `follow=1` (RUN-confirmed on Linux,
   [CT] C14), and keeps a local HLS EVENT playlist as the last fallback.
   `LiveStore.player_uri()` hides the choice.
6. Sync control:
   - `EdgeEstimator` turns the HLS burst sawtooth into a straight edge line;
   - `DelayController` runs at 1 Hz with a 3 s band and hysteresis;
   - the controller acts only through pause, speed nudges of +-3 % and FORWARD seeks
     inside mpv's demuxer cache;
   - the live-video distance is L = clamp(1.5 x max burst gap, 2, 8) s (YouTube live
     segments are 5 s, [CT] C21 RUN, so L is about 7.5 s there);
   - for local files the same "Delayed" slider sets how many seconds of translated
     material the pacer keeps ahead of the playhead (`live_file_ahead_s`).
7. Translation:
   - MarianMT is the default, Ollama is selectable, Google and DeepL are selectable with a
     warning;
   - MarianMT uses a route per language pair: a direct model, else a `tc-big` or group
     model, else a pivot through English with two models (Q12). Direct pairs are missing
     for many combinations ([CT] C39 REFUTED, [FD] table in 4.9);
   - each engine has a circuit breaker;
   - a failed sentence keeps the source text in italics and is not dubbed;
   - the engine never changes by itself: the rate-limit banner offers a one-click "Switch
     to MarianMT".
8. Dub:
   - Edge-TTS per sentence; the leading and trailing silence of each clip is measured and
     skipped (0.16-0.21 s and 0.26-0.84 s, [CT] finding 11);
   - the `voice` instance plays each clip at its slot;
   - the original is ducked through a labelled lavfi `volume` filter with
     `af-command vtduck volume <g> volume` on mpv >= 0.37 only (the `<target>` argument
     exists from 0.37; without it the command returns an error, [CT] C29 REFUTED);
   - on mpv < 0.37, or if the filter probe fails, a single-writer volume mixer takes over;
   - the duck starts early by a measured duck latency (0.19-0.39 s, [CT] C30).
9. Detection and loading:
   - detection is a ctypes probe;
   - before the first in-process load of a given libmpv file, a subprocess load check
     runs, so a crashing DLL cannot kill the app; the same subprocess reports the mpv
     version, the resolved library path and which VO profiles' options this build accepts
     (an invalid option makes `MPV()` raise and leak a core, [CT] finding 2);
   - `import mpv` exists only in `libmpv_runtime.load_mpv()`, and runs off the Tk thread;
   - on Linux X11, Tk's X error handler is captured before the first VO init and restored
     after every VO uninit, because mpv displaces it and every VO uninit leaves Xlib's
     process-exiting default ([CT] finding 5).
10. Windows DLL:
    - installed by `python -m videotranslator.libmpv_runtime install`, called by the
      installer and by the GUI per-user fallback;
    - renamed `mpv-2.dll` and never put on the machine or user PATH;
    - the build sources are data (an `AssetSource` tuple), so the operator's licence
      choice (Q1) changes data, not code.
11. Threads and output: every thread our code creates installs the GUI's thread-local log
    redirect, and `_GlobalRedirect` tolerates a None original stream, so library output
    (tqdm, warnings) can never raise under pythonw on Windows ([CC] G2).

### 0.2 Judge findings and where they are fixed

| # | Finding (judge) | Fix | Section |
|---|---|---|---|
| F1 | [parity]/[mvp] DelayController decides on a raw ingest edge that advances in HLS segment bursts: speed nudges flap and delayed mode pauses every segment (both judges) | `EdgeEstimator` (peak-hold linear edge + stall detection), controller at 1 Hz, 0.5 s dead band, 3 s band, 2 s hysteresis, pause only below -3 s; mpv cache-pause handles true starvation | 5.2, 5.3 |
| F2 | Live video at a fixed 1.5 s behind the edge hits paused-for-cache on 2-6 s segments | L = clamp(1.5 x max_burst_gap_s, 2, 8), measured over 60 s | 5.4 |
| F3 | [parity] VolumeMixer: two writers of the mpv `volume` property (slider and ducking) | ducking on a separate channel (`af-command vtduck volume <g> volume` on a labelled filter, mpv >= 0.37); otherwise the fallback mixer has exactly one applier per mode plus a 250 ms re-assert | 4.13 |
| F4 | [parity] Windows VO failure is error-only (VMs without 3D) | VO profile chain `auto -> d3d11-warp` on Windows, `x11egl -> x11vk -> x11sw` on Linux (profiles pre-validated by the probe subprocess), persisted as `player_vo_profile` | 3.1, 6.1 |
| F5 | [parity] separate strings module changes the i18n convention | kept, flagged as operator decision Q5 | 2.6, 10 |
| F6 | [parity] live transport never run | spike S2 with three candidates, measurable go/no-go criteria, before any stream code | 4.6, 9 |
| F7 | [parity] stale-session cleanup (dirs older than 1 h) can delete a second instance's running session | `session.lock` with pid and process start token; per-OS `pid_alive` (never `os.kill` on Windows); delete only when the owner is dead | 4.15 |
| F8 | [parity] implicit live source ("selected file, else first URL") | two explicit entry points: player button for the loaded file, "Watch live" next to Download for a URL | 4.2 |
| F9 | [mvp] unbounded single TS file, disk full mid-session | chunked store, retention by reader low-water, size cap, free-space check at start and every 30 s | 4.6 |
| F10 | [mvp] no ingest restart or re-resolve | `IngestPolicy`: stall detection, backoff, re-resolve rules, `-output_ts_offset` restart | 4.5 |
| F11 | [mvp] VP9/Opus can reach `-c copy` into MPEG-TS | `is_ts_compatible` checks the chosen format before ffmpeg starts | 4.5 |
| F12 | [mvp] all Tk glue in the 8,400-line GUI file | `player_panel_tk.py`, `live_bar_tk.py` | 2.3 |
| F13 | [sync] `size` reported while live | no size callback for the stream's whole life (python-mpv and our raw registration read it only at open, [CT] finding 7) | 4.6 |
| F14 | [sync] ctypes DLL load on the Tk thread at startup | startup check loads nothing; the first load is preceded by a subprocess check and runs on a worker | 3.1 |
| F15 | [sync] live on a loaded file reloads it with raw PTS | files keep `rebase-start-time=yes`, no reload | 4.3 |
| F16 | [sync] URL job with lip sync has no A/B | the dual-audio mux happens inside the pipeline; the lip-sync branch re-muxes while the URL temp source still exists | 3.4 |
| F17 | [sync] VOD longer than the cap fails | VOD ingest backpressure (ingest pauses reading, ffmpeg blocks on the pipe) | 4.5 |
| F18 | [sync] transport icons on Windows fonts | canvas-drawn icons, no Unicode glyphs | 2.3 |
| F19 | [sync] 17 modules, many knobs | 18 small modules (bridge folded into the adapter), 18 config keys (one internal), no latency or model knobs | 2.1, 2.5 |

Grafted ideas (the source is in brackets):
- From [sync]:
  - `PlaybackClock` and explicit `audio_buffer=0.2`;
  - `mpv-cmd` thread;
  - raw-PTS domain for URL sessions;
  - VO profile chain;
  - `VTAI_LIVE_FAULTS`;
  - `av` declared explicitly (reverted in the final design: `av` and `onnxruntime` both arrive with faster-whisper, R8);
  - `marian_is_cached` consent;
  - hallucination filter;
  - bounded idle-active release before jobs;
  - pid-based stale cleanup;
  - queue table;
  - breaker with half-open probe and doubling cooldown;
  - "Switch to MarianMT" action;
  - ASR backpressure;
  - caption wrap and pagination;
  - gradual auto-raise of the delay.
- From [mvp]:
  - delayed start by loading the player only once D seconds are stored;
  - `lavf://file:` + `follow=1` as a transport candidate;
  - generation counter;
  - clips kept for the whole file session;
  - Windows builds as data;
  - the Wav2Lip vocals-only finding (now verified);
  - explicit live buttons;
  - free-space check;
  - spikes before any GUI code.

### 0.3 Critique findings and where they are fixed

[CT] ranked findings and refutations (R-numbers are [CT] section 2):

| # | Finding | Fix in this design | Section |
|---|---|---|---|
| CT1 | C29 REFUTED: `af-command vtduck volume <g>` returns MPV_ERROR_COMMAND on 0.41 although the gain applies; 0.34-0.36 have no `<target>` argument | AfDuck only on mpv >= 0.37 with the target argument (`af-command vtduck volume <g> volume`); VolumeDuck on older builds or when the probe fails | 4.13 |
| CT2, R1 | `gpu_context=x11` is invalid on Debian/Kali 0.41; `MPV()` raises and leaks the half-created core | Linux chain `x11egl -> x11vk -> x11sw`; the probe subprocess reports which profiles' options the build accepts, so the in-process `MPV()` never gets an invalid option | 3.1 |
| CT3, R2 | the draft's YouTube live selectors select nothing (video-only avc1 HLS plus audio-only 233/234 with `acodec=None`) | selector `bv*[height<=H][vcodec^=avc1]+ba/b[height<=H]`; unknown codecs probed with ffprobe before the ingest | 4.5 |
| CT4 | python-mpv's stream read callback copies byte by byte (8-13 MB/s, GIL held) | raw ctypes registration of `vtlive` with `ctypes.memmove`; strong references to every CFUNCTYPE until `close` | 4.6 |
| CT5 | C6 REFUTED: mpv displaces Tk's X error handler at VO init and every VO uninit leaves Xlib's exiting default | `X11ErrorGuard` captures Tk's handler before the first VO init and restores it after each VO uninit; in-process VO re-creation only if S1 proves the restore | 2.2, 3.1 |
| CT6, R3 | `time-pos` is clamped while a seek or load is pending | validity rules and a `playback-restart` epoch in `PlaybackClock`; the scheduler reacts to epochs, not to raw jumps | 2.2, 4.11 |
| CT7, R4 | `vtlive` semantics: seek return value ignored, `b""` is a permanent EOF, size read only at open, close arrives about 106 ms after `idle-active`, positions relative to the first `seek(0)` | `MpvStreamAdapter` contract rewritten (blocking reads, exact seeks or an error, relative positions, a `closed` Event); stop waits on that Event | 4.6, 4.15 |
| CT8, R7 | C24 REFUTED: `-reconnect*` never reach HLS segment requests; `-seg_max_retry` exists only in FFmpeg >= 6.0 | `-rw_timeout` kept (it reaches segments); `-seg_max_retry 3` added only when the local ffmpeg is >= 6.0; `IngestPolicy` stall detection stays the real guard | 4.5 |
| CT9 | C39 REFUTED: `opus-mt-{src}-{tgt}` is missing for many pairs | Marian route resolver (direct, `tc-big`, group model with target token, pivot through English); coverage table from [FD]; Q12 | 4.9, 10 |
| CT10 | python-mpv 1.0.5 `MPV.loadfile()` fails on libmpv 0.41 | pin `mpv>=1.0.6,<2`; per-file options are set as properties, never passed to `loadfile` | 2.2, 8.1 |
| CT11, R8 | Edge clips carry 0.16-0.21 s leading and 0.26-0.84 s trailing silence; `estimate_tts_duration_s` is -30 % (en) and -59 % (ja) off; duck latency not calibrated | silence measured per clip and skipped; per-language duration model learned in session; duck lead from S3 measurements | 4.10, 4.11 |
| CT12 | `ass_escape` spec contradicts mpv's own escaping | mirror `osd_libass.c:200-252` (`\` + U+2060, `\{`, no doubling) | 2.2, 4.12 |
| CT13 | PyAV `container.start_time` is in microseconds | divide by `av.time_base` | 4.3 |
| CT14, R9 | each click gives two callbacks, a double click gives two clicks and then `MBTN_LEFT_DBL`, a wheel notch fires twice | pure `mouse_action(name, state)`: act on one state only; VLC-like double click | 3.7 |
| R5 | plain `sudo` prompts on an invisible terminal | privilege chain `pkexec`, then `sudo -n`, then the manual command | 2.2, 8.2 |
| C3 | Windows d3d11 flip model vs an overlapping sibling HWND unknown | S4 item; fallback `d3d11_flip=no` | 9, 11 |
| C5 | `MPV.__del__` runs `terminate()` on whichever thread drops the last reference | the adapter owns the only reference and always terminates on a helper thread; after that `__del__` is a no-op (`mpv.py:1163`) | 2.4, 6.4 |
| C8 | wrong zip member path for the Vulkan loader | `VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll` | 8.3 |
| C9 | the `AddedDllDirectory` handle must stay alive | kept for the process lifetime | 8.3 |
| C10 | Windows builds are mpv master snapshots | BUILD.txt records the mpv commit; S4 re-runs S1/S3 on the pinned snapshot | 8.3, 9 |
| C34 | edge-tts timeouts must be `int` | ints only; support detected with `inspect.signature`, no `TypeError` fallback | 4.10 |
| C37 | the VAD wrapper also needs a remainder buffer | specified (h, c, 64-sample context, remainder) with the exact faster-whisper helpers | 4.7 |

[CC] findings:

| # | Finding | Fix in this design | Section |
|---|---|---|---|
| G1 | the editor sets `_running = False` while open, so live could start | `_editor_open` flag in every live guard; live buttons disabled while the editor exists | 4.2, 6.2 |
| G2 | library output from new threads raises under pythonw | `_GlobalRedirect` drops output when the original stream is None; every new thread installs the redirect | 1.3 R9, 2.4 |
| G3 | the player pip install cannot go through `_install_deps` as described | `ComponentInstaller` with an `on_done` callback, `importlib.invalidate_caches()`, user-site re-add, restart message when still not importable; its own `_installing` flag | 2.2, 6.1, 8.2 |
| G4 | the `live_err_deps` recovery would use the Italian-only popup | the same translated `ComponentInstaller` flow | 6.2 |
| G5 | the global `<Key>` binding double-fires with Button/Radiobutton/Scale class bindings | player keys act only when focus is inside the player pane or on a non-interactive widget | 3.7 |
| G6 | canvas controls not keyboard operable; hidden actions have no keys | focusable canvas controls with focus ring and activation keys; shortcuts for every action | 2.3, 3.7 |
| G7 | files had no adjustable delay | the slider applies to files as the translated lead kept ahead (`live_file_ahead_s`) | 2.5, 5.5 |
| G8 | Marian coverage of the 26 targets unassessed | [FD] table and routes | 4.9 |
| G9 | streams with unknown codecs refused | ffprobe of the chosen URLs when yt-dlp reports None | 4.5 |
| G10 | Linux fingerprint not computable from a soname | path resolved from `ldconfig -p` (quick) and from `/proc/self/maps` in the probe | 2.2, 3.1 |
| G11 | 0.34 accepted but never tested | 0.34 (Ubuntu 22.04) added to S1 headless and S3; tested floor constant; Q13 | 9, 10 |
| G12 | `os.kill(pid, 0)` is not a liveness probe on Windows | `platforms.pid_alive` per OS plus a start token | 4.15 |
| G13 | i18n key gaps | 18 keys added, every state mapped, a literal-key test | 2.6 |
| G14, G15 | R8 inconsistent (`av` declared, `onnxruntime` not); `av>=11` against the .bat pin rule | neither declared; both come with faster-whisper; guarded by `find_spec` | 1.3 R8, 8.1 |
| G16 | console windows from pythonw children | `subprocess_utils.no_window_kwargs()` on every new child (7zr, probe, ffprobe, ingest) | 1.3 R1 |
| G17 | the mpv child window may keep keyboard focus | `video_host.focus_set()` after each mouse event; S1/S4 item | 3.7, 11 |
| G18 | `explorer /select,<path>` quoting | native command-line string built by us; fallback `os.startfile(dir)` | 3.7 |
| G19 | a running job's output can be loaded from Results | Results group disabled while `_running` | 3.7 |
| G20 | removing or clearing the loaded input item unspecified | stop and show the placeholder | 3.2 |
| G21 | snapshot and open folder in stream sessions | snapshot enabled, open folder disabled | 5.9 |
| G22 | settings placement | a "Player" section after Language | 2.3 |
| G23 | project rule: Windows status per new library | table | 8.6 |
| G24 | ffmpeg installer refactor and full LOCALAPPDATA cleanup are out of scope | dropped from this project; Q11 | 8.2, 8.3, 10 |
| G25 | DeepL key in a dataclass repr | `field(repr=False)`; configs never logged | 2.2 |
| G26 | mode and delay only selectable after start | LiveBar idle row visible whenever the player is ready | 2.3 |
| G27, T4 | `merge_into` raising at import | never raises; collisions caught by a test | 2.6 |
| G28 | placeholder logo undefined | `assets/icon_256.png` (copied by the installer), canvas fallback | 2.3 |
| G29 | editor placement off screen | clamped to the screen | 3.5 |
| G30 | the 12 h guard reused `live_status_ended` | `live_status_time_limit` | 4.3 |
| G31 | "Watch live" label wrap | own grid cell with `wraplength` | 2.3 |
| T1 | Tk tests always skip in CI | local Xvfb gate in every phase; optional CI job Q14 | 7.4, 10 |
| T2 | slow or flaky real-thread tests | injected `LiveTimeouts` of about 0.1 s in tests | 7.1 |
| T3 | import-hygiene test depends on test order | runs in a subprocess | 7.1 |
| [CC] 7 | phase acceptance incomplete, no Windows live before P7 | every phase has measurable items with a method; Windows items in P2-P6; P7 must-pass floor | 9 |

---

## 1 Overview and scope

### 1.1 What v1 includes

- F1 Preview: selecting a file in the Input list loads it, paused, in the left pane.
- F2 Auto-load: when a job ends, its dubbed output loads paused BEFORE the modal
  completion dialog. A batch fills the playlist with every output.
- F3 A/B audio: one toggle switches Original and Dubbed at the same position.
  - File mode: an audio track switch. Every new output carries the original audio as a
    second track (Q3); older outputs fall back to adding the source as external audio.
  - Live mode: dub on or off.
- F4 Subtitles:
  - the generated SRT is shown, with a toggle;
  - in the pre-dubbing editor, the player shows the source video with the edited segments
    as live-updated subtitles;
  - clicking a row seeks the player.
- F5 Real-time translation "like YouTube", for:
  - (a) the local file loaded in the player;
  - (b) a URL: YouTube Live, Twitch live, or a VOD URL through the same path.
  The output is translated subtitles AND an Edge-TTS dub per sentence over the ducked
  original.
- Sync modes, chosen before or during a session:
  - "Delayed video": an adjustable delay, subtitles and voice in sync with the speaker.
    For streams the slider sets the playback delay behind the ingest edge; for local
    files it sets how much translated material is kept ready ahead of the playhead;
  - "Live video": the picture near the live edge (streams) or never paused (files);
    subtitles and voice lag.
- Controls per the operator mockup:
  - dark video surface with a centred placeholder when idle;
  - seek bar with the current time on the left and the duration on the right;
  - "Now playing: <file>";
  - Playlist;
  - previous, back 10 s, stop, play/pause, forward 10 s, next;
  - snapshot;
  - open folder;
  - volume icon and slider;
  - fullscreen.
- Installation and detection:
  - Windows installer step;
  - Linux install from the GUI (package manager);
  - a preflight probe;
  - an in-panel placeholder that states why the player is unavailable and offers Install.

### 1.2 Explicitly out of v1

- Plain URL playback without translation. A live session with the dub off is the v1
  equivalent.
- DVR in stream sessions: no backward seeks. The live seek bar is an indicator and clicks
  are ignored. Pause and resume are allowed (5.3).
- XTTS or cloned voice in live mode, and any offline live TTS. Edge-TTS needs the network.
- Demucs in live mode: the original voice stays audible under the duck.
- Streaming ASR policies (LocalAgreement, SimulStreaming, [05] 3.1-3.2): v1 uses VAD
  utterance chunking.
- Bilingual subtitles, subtitle style settings, and a post-job read-only segment list.
  Click-to-seek exists in the pre-dubbing editor only.
- Runtime `wid` change, a separate fullscreen Toplevel, macOS, native Wayland embedding
  (XWayland only).
- Diarization, lip sync and per-speaker voices in live mode. Recording or exporting a live
  session.
- A live session running concurrently with a dubbing job (Q4).
- mpv's own OSC, config files, scripts and default key bindings.

### 1.3 Guiding rules

- R1 Parity. Use only primitives that behave the same on Windows and Linux:
  - regular files;
  - anonymous pipes (ffmpeg stdout);
  - in-process callbacks;
  - `subprocess` with list arguments, plus `CREATE_NO_WINDOW` on Windows for EVERY new
    child (7zr.exe, the probe subprocess, ffprobe, the ingest ffmpeg, pip), through a new
    `subprocess_utils.no_window_kwargs(sys_platform)` ([CC] G16).
  No FIFOs, named pipes, `fd://`, POSIX signals or shell strings. The one exception is
  `explorer /select,"<path>"`, a native Windows command line built by us, not a shell
  (3.7).
- R2 Degrade, never block. A missing player or live component disables only that feature
  and shows a reason key plus an action. The dubbing pipeline is untouched.
- R3 Pure core, thin shell:
  - decisions live in Tk-free, mpv-free modules with injected clocks, runners and
    factories;
  - side effects live in small adapters;
  - the GUI file wires.
- R4 Threads:
  - each object has one owner (2.4);
  - mpv callbacks only write to the bridge;
  - the Tk thread never calls libmpv synchronously;
  - non-mpv workers reach Tk with `after(0, ...)`, the existing pattern;
  - `live-sched` is the only timing authority of a session.
- R5 Bounded everything. Every queue and buffer has a bound and a stated overflow policy
  (4.14). Disk use is capped.
- R6 One time domain per session (4.3).
- R7 i18n:
  - pure modules return keys plus format parameters, never user text;
  - every key exists in 26 languages;
  - log lines stay English, as today ([01] 8).
- R8 No new hard dependency:
  - python-mpv is optional (`requirements-player.txt`);
  - live mode uses dependencies already installed: faster-whisper 1.2.1 requires both
    `av>=11` and `onnxruntime<2,>=1.14` ([FD] metadata), plus edge-tts, deep-translator,
    requests and yt-dlp (core), transformers and sentencepiece (optional profile), ffmpeg
    and ffprobe;
  - live code imports `av` and `onnxruntime` directly, so both are checked with
    `find_spec` before a session starts (`live_err_deps`), but neither is declared: the
    draft declared `av` only, which was inconsistent ([CC] G14) and clashed with the batch
    file's pin rule ([CC] G15). A static test asserts that no new requirement line appears
    besides `requirements-player.txt`.
- R9 Output safety under pythonw ([CC] G2): `_GlobalRedirect` (video_translator_gui.py:5238)
  drops text when its original stream is None (pythonw) instead of raising, and every
  thread created by new code installs the thread-local GUI redirect (the pattern of
  :7852/:7906). Library writes (tqdm from huggingface_hub, `warnings`, logging fallbacks)
  therefore reach the log or vanish, never raise.

---

## 2 Components and modules

### 2.1 Module map

All new modules live under `videotranslator/` and are stdlib-only at import time. Every
heavy import is lazy, inside a factory. numpy (in `requirements-dev.txt`) is the only
third-party module-level import allowed. Only modules named `*_tk.py` import tkinter
(precedent: `videotranslator/ui_theme_tk.py`).

| Module | One purpose | Pure? | Uses | Phase |
|---|---|---|---|---|
| `libmpv_runtime.py` (new) | find, probe (load, mpv version, resolved path, accepted VO profiles), install and import libmpv; `python -m` CLI | core pure, side effects injected | `js_runtime.app_data_dir`, `subprocess_utils` | P1 |
| `system_packages.py` (new) | Linux package-manager plans for libmpv; `ComponentInstaller` (pip and system plans on a worker, `on_done` callback, import-path refresh) used by the player and live installs | plans pure, runner and thread factory injected | `subprocess_utils` | P1 |
| `player_engine.py` (new) | the ONLY code that touches `mpv.MPV`: `EventBridge`, `PlaybackClock`, `CommandQueue`, `VolumeMixer` (pure), option builder, VO chain and duck-channel choice (pure), `X11ErrorGuard`, raw `vtlive` stream registration, `MpvBackend`, `MpvVoiceBackend`, `InMemoryBackend`, `InMemoryVoice` | adapter; listed parts pure | `libmpv_runtime` | P2 (voice P5, stream P6) |
| `player_core.py` (new) | player state machine and user intents; seek maths, time format, track picking, snapshot path, release rules, key map and filter, mouse mapping, playlist groups, reflow | pure | backend protocol only | P2 |
| `player_settings.py` (new) | normalise `player_*`, `live_*` and `keep_original_audio` config keys | pure | none | P2 |
| `player_panel_tk.py` (new) | Tk `PlayerPanel`: video host, placeholder, seek bar, controls, playlist popup, fullscreen layout hook; pure `icon_shapes()` | Tk glue | `player_core`, `ui_theme` | P2 |
| `ui_strings_player.py` (new, Q5) | player and live strings, 26 languages, `merge_into()` | data | none | P1-P6 |
| `live_health.py` (new) | `CircuitBreaker`, `RollingStats`, status/warning/error code maps, `VTAI_LIVE_FAULTS` parser | pure | none | P4 |
| `live_segment.py` (new) | VAD utterance segmenter (state machine over frame probabilities), sentence assembler | pure | `segments` | P4 |
| `live_asr.py` (new) | `AudioDecoder` (PyAV, lazy), `StreamingVad` (onnxruntime, lazy), `PersistentWhisper`, `LanguageLock`, `filter_hallucinations` | adapters, factories injected | `transcription`, `hotwords`, `whisper_sanity` | P4 |
| `live_translate.py` (new) | per-sentence translators (Marian, Ollama, Google, DeepL) with hard timeouts; Marian route resolver (direct, `tc-big`, group, pivot); `marian_is_cached`; never a fallback engine | engines injected | `ollama_prompt`, `ollama_runtime`, `quality_flags`, `live_health` | P4 |
| `live_tts.py` (new) | `EdgeClipSynth` (asyncio thread, deadlines, atomic files), clip silence measurement, per-language `EdgeDurationModel`, rate choice, CBR duration | async, factory injected | `timing`, `tts_text_sanitizer`, `live_health` | P5 |
| `live_sync.py` (new) | `EdgeEstimator`, `DelayController`, `FilePacer`, `derive_live_timing`, `recommended_delay_s`, `live_distance_s` | pure, fake clock | none | P4 (files), P6 (streams) |
| `live_scheduler.py` (new) | `DubScheduler` (caption, clip and duck actions), caption wrap/paginate, ASS escaping | pure, fake clock | none | P4 (captions), P5 (dub) |
| `live_store.py` (new) | chunked growing byte store, `TailReader` (PyAV), `MpvStreamAdapter` (`vtlive://`), `SeekIndex`, `player_uri()` | files plus Condition | none | P6 |
| `live_source.py` (new) | URL resolve (yt-dlp `download=False`), TS-safe format choice, codec probe (ffprobe) when yt-dlp reports none, ffmpeg version gate, ingest command, `IngestPolicy` (pure), `IngestWorker` | cmd and policy pure, Popen and runner injected | `input_source`, `js_runtime`, `subprocess_utils` | P6 |
| `live_session.py` (new) | orchestration: threads, queues, start/stop, status snapshot, stale cleanup | threads; every component injected via `LiveFactories` | all `live_*`, backend protocols | P4-P6 |
| `live_bar_tk.py` (new) | Tk `LiveBar` under the player: stop, mode toggle, delay slider, engine, status, banner, privacy icon | Tk glue | `live_session`, `player_settings` | P4 |
| `output_media.py` (edit) | `mux_video(..., original_audio_input=None)`, pure `segments_to_srt()` | builder pure | none | P3 |
| `jobs.py` (edit) | `JobOutput`, `job_output_from_result()`, `TranslationJobConfig.keep_original_audio` | pure | none | P3 |
| `pipeline_runner.py` (edit) | pass the original audio to the mux; the lip-sync branch re-muxes instead of `shutil.move` | - | `output_media` | P3 |
| `preflight.py`, `cli.py` (edit) | native libmpv check, `--preflight-player`, `--no-original-audio` | injectable | `libmpv_runtime` | P1, P3 |
| `platforms.py` (edit) | `reveal_in_file_manager(path, *, sys_platform, popen)`; `pid_alive(pid, *, sys_platform)`, `process_start_token(pid, *, sys_platform)` | runner / ctypes injected | none | P2, P6 |
| `subprocess_utils.py` (edit) | `no_window_kwargs(sys_platform)` (`creationflags=CREATE_NO_WINDOW` on win32, `{}` elsewhere) | pure | none | P1 |

Count: 18 new modules. Most are 100-300 lines. No new module imports
`video_translator_gui`: voices, language lists and strings come in as parameters.

Reused unchanged:
- `transcription.py`: `whisper_device_and_compute` (:13), `build_transcribe_kwargs`
  (:20), `normalize_whisper_segments` (:43), `is_cuda_runtime_error` (:61).
- `hotwords.to_whisper_param`.
- `segments.py`: `END_PUNCT_CHARS` (:7), `split_on_punctuation` (:62).
- `whisper_sanity.sanity_score_segments` (:135).
- `quality_flags.add_quality_flag` (:77) and `FLAG_TRANSLATION_FALLBACK`.
- `timing.estimate_tts_duration_s` (:56).
- `tts_text_sanitizer.sanitize_for_tts` (:65).
- `ollama_prompt.build_translation_prompt` (:53).
- `ollama_runtime.py`: `_ollama_health_check` (:88), `_ollama_strip_preamble` (:155),
  `set_subprocess_hooks` (:20).
- `input_source.py`: `build_ytdlp_options` (:40), `emit_download_warnings` (:27),
  `is_probable_url` (:123).
- `js_runtime.py`: `ensure_js_runtime` (:205), `resolve_js_runtimes` (:140),
  `app_data_dir` (:86).
- `subprocess_utils.ActiveSubprocessRegistry` (:64).
- `platforms.py`: `runtime_app_paths` (:141), `default_videos_dir` (:256).
- `jobs.TranslationJobResult.output_path` (:62).

Not modified: `videotranslator/translation.py`. Another agent is editing it, and its batch
dispatcher falls back silently to Google, which is wrong for live ([02] 4). Live
translation is a separate module on purpose. The Marian language-code helper
(`_marian_normalize_lang`, HEAD translation.py:30-41 per [02]) is imported read-only in
P4, after the concurrent work lands. It is never duplicated. If it is still private then,
a one-line public alias is added in that file as part of P4.

### 2.2 Public interfaces

`libmpv_runtime.py`
```python
MIN_API = (1, 108)                        # python-mpv import gate (mpv.py:565, [CT] 3)
TESTED_FLOOR = (0, 34)                    # lowest mpv release covered by S1/S3 (Q13);
                                          # below it: reason libmpv-too-old
AF_TARGET_MIN = (0, 37)                   # `af-command ... <target>` exists from 0.37 ([CT] C29)
RUNTIME_DIR_NAME = "mpv-runtime"          # hyphen: never importable ([03] 3.2 namespace trap)
WINDOWS_DLL_TARGET = "mpv-2.dll"          # python-mpv tries this name first ([06] 4)
REASON_KEYS: dict[str, str]               # reason -> UI_STRINGS key, "ok" included (tested)

@dataclass(frozen=True)
class LibmpvStatus:
    ok: bool
    reason: str      # ok | python-mpv-missing | libmpv-missing | libmpv-too-old
                     # | libmpv-load-failed | vulkan-loader-missing | probe-crashed
                     # | restart-required
    api_version: tuple[int, int] | None
    mpv_version: tuple[int, int] | None  # parsed from `mpv-version` ("mpv 0.41.0",
                                         # "mpv v0.41.0-1050-ge76a35ec9"); probe only
    path: str | None                     # REAL path of the library file (see fingerprint)
    vo_profiles_ok: tuple[str, ...]      # profiles whose options this build accepts
    detail: str                          # English, log and preflight only
    build: Mapping[str, str]             # BUILD.txt fields (Windows), {} elsewhere
    fingerprint: str | None              # "<realpath>|<size>|<mtime_ns>"
    # Linux: find_library returns a soname only ([CC] G10), so quick_presence resolves the
    # path by parsing `ldconfig -p` ("libmpv.so.2 (libc6,x86-64) => /path"), and the probe
    # subprocess reports the path actually mapped (/proc/self/maps line containing
    # "libmpv.so"). os.stat follows the symlink, so an `apt upgrade` changes size/mtime.
    # Windows: the candidate file itself.

class PlayerUnavailable(Exception):
    status: LibmpvStatus

def windows_candidate_dirs(env: Mapping[str, str], app_dir: Path) -> list[Path]
    # VTAI_LIBMPV_DIR, app_dir/mpv-runtime, %ProgramFiles%\VideoTranslatorAI\mpv-runtime,
    # %LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime (shape of platforms.py:289-312)
def parse_api_version(raw: int) -> tuple[int, int]            # raw >> 16, raw & 0xFFFF
def classify_import_error(exc: BaseException, *, sys_platform: str,
                          vulkan_present: bool) -> str
def parse_ldconfig(output: str, soname_prefix: str = "libmpv.so") -> str | None
def parse_mpv_version(text: str) -> tuple[int, int] | None
def quick_presence(*, sys_platform, env, app_dir, find_library, run_ldconfig, isfile,
                   find_spec) -> LibmpvStatus
    # NO library load: file existence (Windows) or ldconfig lookup (Linux); startup badge
def probe_libmpv(*, sys_platform, env, app_dir, find_library, cdll, isfile,
                 read_maps) -> LibmpvStatus
    # runs ONLY inside the `check` subprocess: ctypes load + mpv_client_api_version();
    # then mpv_create + mpv_set_option_string for each VO profile's options on a fresh
    # uninitialised handle (an invalid choice fails at set time: [CT] RUN, ValueError -7
    # through python-mpv), destroyed each time; then one handle with vo=null, ao=null,
    # idle=yes, initialised, to read `mpv-version`; mpv_terminate_destroy
def probe_in_subprocess(*, run, python: str = sys.executable, timeout: float = 20.0,
                        runtime_dir: Path | None = None) -> LibmpvStatus
    # `python -m videotranslator.libmpv_runtime check --json`; crash/timeout -> probe-crashed;
    # no_window_kwargs on Windows ([CC] G16)
def prepare_import(env: MutableMapping[str, str], *, sys_platform: str, runtime_dir: Path | None,
                   add_dll_directory, system32_has_vulkan: bool) -> Callable[[], None]
    # Windows: PREPEND runtime_dir to env["PATH"] (restore() puts the old value back);
    # add runtime_dir/vulkan-fallback via add_dll_directory only when System32 lacks
    # vulkan-1.dll, and keep the returned handle referenced for the process lifetime
    # (closing it would drop the directory while libmpv may still resolve imports,
    # [CT] C9). Linux: no-op.
def load_mpv(*, importer=importlib.import_module, **kw) -> ModuleType
    # the ONLY `import mpv` in the code base; raises PlayerUnavailable; module cached

@dataclass(frozen=True)
class AssetSource:
    kind: str                            # "github-latest" | "pinned"
    name: str                            # e.g. "zhongfly-lgpl", "shinchiro-gpl-20260920"
    licence: str                         # "LGPL" | "GPL"
    urls: tuple[str, ...] = ()           # pinned: mirrors in order
    sha256: str | None = None            # pinned archive
    member: str = "libmpv-2.dll"
    member_sha256: str | None = None     # pinned DLL
    repo: str | None = None              # github-latest: "zhongfly/mpv-winbuild"
    asset_pattern: str | None = None     # regex on asset names
    max_releases: int = 3                # github-latest: newest N tried in order
    max_bytes: int = 64 << 20
WINDOWS_LIBMPV_SOURCES: tuple[AssetSource, ...]   # order and content = operator decision Q1
SEVENZR: AssetSource                              # 7zr.exe 26.03, pinned ([06] 2)
VULKAN_RUNTIME: AssetSource                       # LunarG 1.4.357.0 zip, pinned ([06] 4.1);
    # member "VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll" ([CT] C8 correction)
def install_windows(dest: Path, *, sources, sevenzr, vulkan, downloader, runner,
                    probe, system32: Path, log) -> LibmpvStatus
def main(argv: list[str] | None = None) -> int
    # "install --dest DIR" | "check [--dir DIR] [--json]"; exit 0 ok, 2 unavailable,
    # 3 unexpected error; never 1 (the batch tells "optional missing" from a crash)
```

Why PREPEND and not narrow PATH ([parity] narrowed it). Changing `os.environ["PATH"]` is
process-wide. If a dubbing job spawns `ffmpeg` while the player initialises (a user
selecting a file during a job), a narrowed PATH would hide ffmpeg for that instant; ffmpeg
reaches the PATH on Windows through the installer (`setup_windows.bat:1147-1152`).
Prepending is enough to win the name-order trap. Our file is named `mpv-2.dll`, which
python-mpv tries first ([06] 4), and CPython's Windows `find_library` returns the first
PATH entry that contains that name ([03] 2.1). The previous value is restored right after
the import.

`system_packages.py`
```python
def detect_manager(which) -> str | None                  # apt-get | dnf | pacman | zypper
def libmpv_packages(manager: str, *, apt_has: Callable[[str], bool]) -> tuple[str, ...]
    # apt: libmpv2 if `apt-cache show libmpv2` succeeds else libmpv1; dnf: mpv-libs;
    # pacman: mpv; zypper: libmpv2 (Tumbleweed 0.41, Leap 15.6 0.36 backports, [CT] C48)
def privilege_prefixes(which) -> list[list[str]]         # [["pkexec"], ["sudo", "-n"]]
    # plain `sudo` is NOT tried: it reads the password from the terminal device, not
    # stdin (`man sudo`, -S), so from the GUI it would block or fail ([CT] R5); when both
    # prefixes fail the placeholder shows the manual command
def build_install_plan(manager: str, packages: Sequence[str],
                       prefix: list[str]) -> list[list[str]]
    # apt-get update + install -y; dnf install -y; pacman -S --needed --noconfirm (never -Sy)
def manual_command(manager: str, packages: Sequence[str]) -> str     # the {cmd} of the message
def run_plan(plan, *, runner, log) -> bool                # stdin=DEVNULL, output streamed
def pip_install_command(python: str, packages: Sequence[str]) -> list[str]
    # [python, "-m", "pip", "install", "--break-system-packages", "--no-color", *packages]:
    # the same flags as _install_deps (video_translator_gui.py:5951-5952), so the result
    # lands where today's installs land
def refresh_import_paths(*, importlib_module, site_module, sys_path: list[str],
                         isdir) -> None
    # importlib.invalidate_caches(); if site.ENABLE_USER_SITE and the user site dir now
    # exists but is not on sys.path (it did not exist at interpreter start,
    # /usr/lib/python3.13/site.py:380, [CC] G3), site.addsitedir(user_site)

@dataclass(frozen=True)
class InstallResult:
    ok: bool; restart_required: bool; failed_step: str | None
class ComponentInstaller:                  # replaces the draft's reuse of _install_deps
    def __init__(self, *, runner, thread_factory, find_spec, refresh, log,
                 post: Callable[[Callable[[], None]], None])   # post = after(0, ...)
    def install(self, *, pip_packages: Sequence[str], system_plan: list[list[str]] | None,
                windows_install: Callable[[], "LibmpvStatus"] | None,
                expect_modules: Sequence[str],
                on_done: Callable[[InstallResult], None]) -> None
        # worker: pip (if any), then the system plan or the Windows DLL install, then
        # refresh_import_paths, then find_spec for each expected module; a module still
        # missing gives restart_required=True (message player_restart_required);
        # on_done is posted to Tk. Never touches App._running (it has its own
        # App._installing flag), never chains _check_optional_deps.
```

`player_engine.py` (pure parts first)
```python
class EventBridge:                         # the ONLY path from mpv threads to consumers
    LATEST = ("time-pos", "duration", "pause", "paused-for-cache", "seeking", "core-idle",
              "idle-active", "eof-reached", "speed", "demuxer-cache-time",
              "demuxer-cache-duration", "video-params", "track-list")
    def set_latest(self, name: str, value: object, mono: float) -> None  # any thread, O(1)
    def post(self, kind: str, payload: object = None) -> None
        # deque(maxlen=512); when full, the oldest "log" entries go first; kinds include
        # file-loaded, end-file, playback-restart (event id 21, mpv.py:305), click,
        # dblclick, wheel, log, stream-error, stream-closed
    def latest(self, name: str) -> tuple[object, float] | None           # value, stamp
    def drain(self) -> "BridgeSnapshot"      # Tk: changed props + events since last drain
    def close(self) -> None                  # later writes dropped; reads keep last values

class PlaybackClock:                       # extrapolates time-pos between observations;
                                           # thread-safe (one Lock): observed on Tk, read by
                                           # live-sched; expect_restart is called by whoever
                                           # enqueues a load/seek (controller or live-sched)
    def expect_restart(self) -> None           # called when WE issue load/seek/reload
    def on_playback_restart(self, mono: float) -> None   # epoch += 1; validity back
    def observe(self, pos: float | None, mono: float, *, speed: float, running: bool,
                seeking: bool) -> None
        # a value is IGNORED while seeking, while a restart is expected, and (raw
        # sessions) below first_pts; mpv clamps time-pos to [0, duration] in those
        # windows (playloop.c:553-561, [CT] finding 6: 7.14 reported for 140 ms during a
        # seek to 1007.52)
    def now(self, mono: float) -> float | None   # pos + (mono - stamp) * speed if running
    valid: bool; epoch: int; first_pts: float | None
    # running = not pause and not paused-for-cache and not seeking and not core-idle

class CommandQueue:                        # pure; used by the mpv-cmd thread
    def put(self, fn: Callable[[], None], *, key: str | None = None) -> bool
        # same key replaces the queued one (seek, volume, pause, loadfile); max 64;
        # returns False when full (caller shows player_busy)
    def get(self, timeout: float) -> Callable[[], None] | None
    def close(self) -> None

@dataclass(frozen=True)
class MixState:
    version: int; owner: str; video_volume: float; voice_volume: float; muted: bool
class VolumeMixer:                         # state only, under a Lock; never calls mpv
    def set_user_volume(self, value: float) -> None      # Tk (slider)
    def set_muted(self, muted: bool) -> None             # Tk
    def set_duck_gain(self, gain: float) -> None         # live-sched (fallback duck only)
    def set_owner(self, owner: str) -> None              # "cmd" | "sched" (session start/stop)
    def snapshot(self) -> MixState

VO_PROFILES = {"linux": ("x11egl", "x11vk", "x11sw"), "win32": ("auto", "d3d11-warp")}
    # x11glx removed: gl-x11 is disabled by default in mpv meson since at least 0.35.1
    # and `gpu_context=x11` is rejected by the Kali 0.41 build ([CT] finding 2, R1);
    # x11vk is compiled in that build (`--gpu-context=help`, [CT] RUN)
def build_mpv_options(kind: str, *, sys_platform: str, wid: int | None,
                      vo_profile: str) -> dict[str, str]          # table in 3.1
def next_vo_profile(sys_platform: str, current: str,
                    accepted: Sequence[str]) -> str | None        # skips profiles the probe
                                                                  # did not accept
def detect_vo_failure(log_lines: Sequence[str], *, video_params_seen: bool,
                      has_video_track: bool, seconds_since_loaded: float) -> bool
    # strings confirmed in 0.41 and in the Windows DLL ([CT] C49): "Failed initializing
    # any suitable GPU context", "Error opening/initializing the selected video_out";
    # after them playback continues audio-only (video-params None)
def stream_session_options(delay_max_s: float) -> dict[str, str]   # 3.1 last row
def duck_channel_for(mpv_version: tuple[int, int] | None) -> str   # "af" if >= (0, 37)
                                                                   # else "volume"
def af_duck_command(gain: float) -> list[str]
    # ["af-command", "vtduck", "volume", f"{gain:.3f}", "volume"]; the last element is the
    # <target> filter name ([CT] C29: target "volume" succeeds on 0.41; without it FFmpeg
    # overwrites the return code with ENOSYS, avfiltergraph.c 1312-1334 at n7.1)

class X11ErrorGuard:                        # Linux, Tk windowing system "x11" only
    def __init__(self, *, load_libx11: Callable[[], object])  # ctypes CDLL of libX11
    def capture(self) -> None
        # Tk thread, BEFORE the first VO init: prev = XSetErrorHandler(NULL) returns
        # Tk's handler (installed once, tkError.c:24,102-104), then XSetErrorHandler(prev)
        # puts it back; the pointer is stored ([CT] RUN read the pointer)
    def restore(self) -> None
        # XSetErrorHandler(tk_handler); called right after the video instance's
        # terminate() returns (on that helper thread) and right after detect_vo_failure
        # fires (on Tk). Never while a VO is alive: mpv's handler is then installed,
        # logs X errors and returns 0 (non-fatal), and Tk's per-request handlers do not run
    @property
    def captured(self) -> bool
# Why: mpv installs its handler at VO init (x11_common.c:697) and every VO uninit sets
# XSetErrorHandler(NULL) (x11_common.c:914), leaving Xlib's default, which EXITS the
# process on any X error ([CT] finding 5, RUN on Xvfb: `_XDefaultError` after terminate).
# Restoring from ctypes is UNVERIFIED as a fix: spike S1 proves it or in-process VO
# re-creation is disabled (3.1).

def register_raw_stream_protocol(mpv_module: ModuleType, handle, name: str,
                                 open_adapter: Callable[[str], "MpvStreamAdapter | None"],
                                 keepalive: list) -> None
    # our own CFUNCTYPE/Structure definitions mirroring libmpv stream_cb.h (the C ABI;
    # the same shapes python-mpv uses at mpv.py:505-520), a PRIVATE prototype of
    # mpv_stream_cb_add_ro bound from mpv_module.backend (python-mpv's CDLL of the loaded
    # library) so python-mpv's own argtypes are untouched; read copies with
    # ctypes.memmove (0.003 ms per 128 KiB vs 10-16 ms for the byte loop, [CT] finding 4);
    # every CFUNCTYPE object of an open stream stays in `keepalive` until its close
    # callback ran; every callback is wrapped in try/except and never calls libmpv on the
    # same instance (deadlock, stream_cb.h:48-51)
```
Adapter parts:
```python
class RealtimeOps(Protocol):               # direct thread-safe libmpv calls, live-sched only
    def set_overlay(self, ass_events: str | None) -> None      # osd-overlay id=1
    def set_speed(self, x: float) -> None
    def set_pause(self, paused: bool) -> None                  # DelayController pauses only
    def set_duck(self, gain: float) -> None                    # AfDuck or VolumeDuck (4.13)

class PlayerBackend(Protocol):             # every method non-blocking (enqueues on mpv-cmd)
    rt: RealtimeOps
    mixer: VolumeMixer
    mpv_version: tuple[int, int] | None
    def load(self, uri: str, *, paused: bool, start: float | None = None,
             options: Mapping[str, str] | None = None) -> None
        # options (and `start`) are written as PROPERTIES before
        # command("loadfile", uri, "replace") and restored at the next load; nothing is
        # ever passed in loadfile's options argument, whose position moved in 0.38 (an
        # `index` argument was inserted; python-mpv 1.0.5 MPV.loadfile fails on 0.41 with
        # -4, [CT] finding 10). MPV.loadfile() is never called.
    def stop(self) -> None
    def set_pause(self, paused: bool) -> None
    def seek(self, seconds: float, mode: str = "exact") -> None  # exact | keyframes | relative
    def apply_mix(self) -> None             # writes volume/mute from mixer.snapshot() (owner cmd)
    def add_external_audio(self, path: str, title: str) -> None  # audio-add <path> auto <title>
    def select_audio(self, track_id: int | None) -> None         # aid
    def add_subtitles(self, path: str, title: str) -> None       # sub-add <path> select <title>
    def reload_subtitles(self) -> None
    def set_subtitles_visible(self, visible: bool) -> None
    def screenshot(self, path: str) -> None                      # command_async; reply on bridge
    def set_af(self, value: str) -> bool                         # "" clears; False if rejected
    def register_stream_protocol(self, name: str, open_adapter) -> None  # once per instance,
                                                    # through register_raw_stream_protocol
    def terminate(self, timeout_s: float) -> bool   # closes mpv-cmd, joins, mpv terminate;
                                                    # never on the mpv event thread nor Tk;
                                                    # the backend holds the ONLY reference
                                                    # to mpv.MPV, so MPV.__del__ (mpv.py:
                                                    # 1153-1155, a blocking terminate) can
                                                    # never run on Tk ([CT] C5)
class VoiceBackend(Protocol):              # owned by live-sched; local mp3 files only
    def preload(self, path: str, *, skip_s: float = 0.0) -> None
        # pause=yes, start=<skip_s> (the measured leading silence), then loadfile
    def start(self, speed: float) -> None   # speed, then pause=no
    def set_pause(self, paused: bool) -> None
    def stop(self) -> None
    def set_volume(self, value: float) -> None
    def set_speed(self, x: float) -> None
    def terminate(self, timeout_s: float) -> bool
def create_video_backend(*, wid: int, bridge: EventBridge, mixer: VolumeMixer,
                         vo_profile: str, mpv_module: ModuleType,
                         sys_platform: str = sys.platform, log) -> PlayerBackend
def create_voice_backend(*, bridge: EventBridge, mpv_module: ModuleType, log) -> VoiceBackend
class MpvBackend(PlayerBackend): ...        # wraps mpv.MPV; every callback try/except -> bridge
class MpvVoiceBackend(VoiceBackend): ...
class InMemoryBackend(PlayerBackend): ...   # records calls, simulates position/tracks; tests
class InMemoryVoice(VoiceBackend): ...      # and Tk tests without libmpv
```

`player_core.py`
```python
@dataclass(frozen=True)
class MediaItem:
    path: str
    kind: str                         # source | dubbed | live
    title: str
    source_path: str | None = None    # original, when it can be added as external audio
    srt_path: str | None = None
    temp: bool = False                # owned temp file (URL editor flow)

@dataclass(frozen=True)
class PlayerState:
    status: str       # unavailable | initializing | idle | loading | paused | playing | error | live
    item: MediaItem | None
    position: float; duration: float | None
    volume: int; muted: bool
    audio: str                        # dubbed | original
    ab_available: bool; subs_available: bool; subs_visible: bool
    message_key: str | None; message_params: dict

class PlayerController:               # Tk thread only
    def __init__(self, backend: PlayerBackend | None, settings: "PlayerSettings", *,
                 on_change: Callable[[PlayerState], None], save: Callable[[dict], None])
    def attach_backend(self, backend: PlayerBackend) -> None  # after player-init; replays
                                                              # the last pending load
    def load(self, item: MediaItem, *, paused: bool = True, start: float = 0.0) -> None
    def set_playlist(self, items: Sequence[MediaItem], index: int | None = None) -> None
    def play_pause(self) -> None; def stop(self) -> None
    def next(self) -> None; def previous(self) -> None
    def seek(self, seconds: float, *, dragging: bool = False) -> None  # keyframes while dragging
    def seek_relative(self, delta: float) -> None
    def set_volume(self, value: int) -> None; def toggle_mute(self) -> None
    def select_audio(self, which: str) -> bool
    def set_subtitles_visible(self, visible: bool) -> None
    def show_segments_as_subtitles(self, segments: Sequence[dict], srt_path: Path) -> None
    def snapshot(self, dest_dir: Path, now: datetime) -> Path
    def remove_items(self, paths: Sequence[str]) -> None   # Input list removal/clear: drop
                                              # them from the playlist; if the loaded item
                                              # is one of them, stop and lift the placeholder
    def release_for_job(self) -> bool         # stop if item.kind == "dubbed"; True if stopped
    def release(self, path: str) -> bool      # stop if item or its external audio is `path`
    def is_released(self, latest: Mapping) -> bool   # idle-active observed True
    def apply_events(self, snapshot: "BridgeSnapshot", clock_now: float | None) -> None
    state: PlayerState

STATUS_KEYS: dict[str, str]                   # message codes -> UI_STRINGS keys (tested)
def format_clock(seconds: float | None, *, hours: bool) -> str      # "--:--" when unknown
def x_to_seconds(x: float, width: float, start: float, end: float) -> float
def seconds_to_x(t: float, width: float, start: float, end: float) -> float
def pick_audio_track_ids(track_list: list[dict]) -> tuple[int | None, int | None]
    # (dubbed, original): by title "Dubbed"/"Original", then by external flag, then order
def snapshot_path(dest_dir: Path, media_title: str, position: float, now: datetime,
                  exists=os.path.exists) -> Path     # <stem>_<HH-MM-SS>.png, _2, _3
def controls_visible(width_px: int, scale: float) -> frozenset[str]
PLAYER_KEYS: dict[str, str]
    # keysym -> action: space play_pause, Left back_10, Right forward_10, Up volume_up,
    # Down volume_down, m mute, f fullscreen, Escape exit_fullscreen, s snapshot,
    # o open_folder, n next, p previous (the n/p pair follows VLC)
def handles_player_key(widget_class: str, keysym: str, *, focus_in_player: bool) -> bool
    # True when focus is inside the player pane (the panel's focusable controls return
    # "break" themselves for their own activation keys), or when the focus widget is
    # None, the toplevel, or a class without keyboard behaviour (Frame, Label, Canvas,
    # TFrame, TLabel). False for every interactive class: Entry, TEntry, Text, Listbox,
    # TCombobox, Spinbox, TSpinbox, Treeview, Button, TButton, Checkbutton, TCheckbutton,
    # Radiobutton, TRadiobutton, Scale, TScale, Menubutton, TMenubutton. Their class
    # bindings run before the toplevel tag and do not return "break"
    # (button.tcl:104-112, ttk/button.tcl:23,42-43, ttk/scale.tcl:29-33, [CC] G5), so a
    # global action would double-fire (space on Start = start a job AND toggle play).
def mouse_action(name: str, state: str) -> str | None
    # python-mpv key-binding callbacks give state strings such as "dm-", "um-", "p--"
    # ([CT] finding 14). MBTN_LEFT acts on the "u" state only (toggle pause);
    # MBTN_LEFT_DBL on "p" or "d" (toggle fullscreen); WHEEL_UP/WHEEL_DOWN on "p" or "d"
    # only (volume +-5); everything else None. A double click therefore toggles pause
    # twice (net unchanged) and then fullscreen, as VLC does.
def editor_geometry(right_x: int, right_w: int, main_x: int, main_y: int, main_h: int,
                    screen_w: int, screen_h: int) -> tuple[int, int, int, int]   # 3.5
def playlist_groups(sources: Sequence[MediaItem], results: Sequence[MediaItem], *,
                    job_running: bool) -> list[tuple[str, list[MediaItem], bool]]
    # ("player_playlist_sources", items, enabled), ("player_playlist_results", items,
    # enabled=not job_running): a running re-run may overwrite a result ([CC] G19)
```

`player_settings.py`
```python
@dataclass(frozen=True)
class PlayerSettings:
    volume: int; muted: bool; audio: str; subs_visible: bool
    autoload_result: bool; vo_profile: str | None; keep_original_audio: bool
@dataclass(frozen=True)
class LiveSettings:
    sync_mode: str; delay_s: float | None; file_ahead_s: float | None; delay_auto: bool
    engine: str
    dub_enabled: bool; subs_enabled: bool; duck_level: float
    max_height: int; buffer_max_mb: int
def normalize_player_settings(cfg: Mapping[str, object], *, sys_platform: str) -> PlayerSettings
def normalize_live_settings(cfg: Mapping[str, object]) -> LiveSettings
def settings_to_config(settings) -> dict[str, object]     # flat keys for save_config
```

`live_health.py`
```python
class CircuitBreaker:
    def __init__(self, *, threshold: int = 3, window_s: float = 30.0, cooldown_s: float = 30.0,
                 max_cooldown_s: float = 300.0, clock=time.monotonic)
    def allow(self) -> bool                 # closed: yes; open: no; half_open: one probe
    def record_success(self) -> None
    def record_failure(self, *, kind: str) -> str | None
        # kind: rate_limited | quota | timeout | error; returns a warning code when the
        # breaker opens (once per episode); quota opens for the rest of the session;
        # cooldown doubles 30, 60, 120, 300 s
    state: str; def retry_in_s(self) -> float
class RollingStats:                         # window 32: add(x), p50(), p90(), p95(), count
STATUS_KEYS: dict[str, str]; WARN_KEYS: dict[str, str]; ERROR_KEYS: dict[str, str]
LIVE_STATES: frozenset[str]                 # every LiveStatus.state; a test asserts
                                            # set(STATUS_KEYS) == LIVE_STATES ([CC] 4)
@dataclass(frozen=True)
class FaultRule: kind: str; count: int | None; at_s: float | None
def parse_fault_spec(spec: str) -> dict[str, FaultRule]
    # "mt_429:3,tts_fail:2,cuda_oom@60,ingest_stall@120" (dev only, env VTAI_LIVE_FAULTS)
def wrap_factories_with_faults(factories: "LiveFactories", rules, clock) -> "LiveFactories"
```

`live_segment.py`
```python
@dataclass(frozen=True)
class Utterance:
    gen: int; start: float; end: float         # session time (4.3)
    samples: "np.ndarray"                      # float32 mono 16 kHz
    forced_cut: bool
class UtteranceSegmenter:
    def __init__(self, *, on_threshold=0.5, off_threshold=0.35, min_silence_s=0.4,
                 pad_s=0.15, max_len_s=8.0, soft_cut_window_s=1.5, min_pause_s=0.1,
                 discontinuity_s=0.25, sample_rate=16000, frame=512)
    def push(self, block_start: float, samples, probs: Sequence[float]) -> list[Utterance]
    def flush(self) -> list[Utterance]
    def reset(self, gen: int) -> None
    def set_max_len(self, seconds: float) -> None
@dataclass(frozen=True)
class Sentence:
    seg_id: int; gen: int; start: float; end: float; text: str; flags: tuple[str, ...]
class SentenceAssembler:
    def __init__(self, *, hold_s: float, max_words: int = 30, max_span_s: float = 12.0,
                 max_chars: int = 300)
    def push(self, pieces: list[dict], gen: int) -> list[Sentence]
    def edge(self, media_edge: float) -> list[Sentence]   # hold timeout on MEDIA time
    def reset(self, gen: int) -> None
```

`live_asr.py`
```python
class StreamingVad:        # stateful Silero ONNX (faster-whisper asset); keeps h, c, the
                           # 64-sample context AND a remainder buffer between calls: a
                           # 0.25 s block (4000 samples) is not a multiple of 512 ([CT] C37
                           # RUN: identical to SileroVADModel.__call__, max abs diff 0.0
                           # over 625 frames, 0.047 ms per frame)
    def __init__(self, *, session_factory: Callable[[], object])
        # default factory: faster_whisper.vad.get_vad_model().session (cached loader,
        # vad.py:289-292; model file silero_vad_v6.onnx under
        # faster_whisper.utils.get_assets_path(), utils.py:39-41); ONNX inputs `input`
        # [N, 576] (64 context + 512 samples), `h` and `c` [1, 1, 128]
    def probs(self, samples) -> list[float]            # one value per complete 512-sample frame
class AudioDecoder:        # `import av` inside __init__ only
    def __init__(self, source: "str | TailReader", *, container_format: str | None,
                 start_at: float, time_domain: str, av_module: ModuleType | None = None,
                 seek_index: "SeekIndex | None" = None)
    # time_domain "rebased": frame.pts * frame.time_base
    #   - (container.start_time or 0) / av.time_base   (start_time is an int in
    #   MICROSECONDS, [CT] finding 13: 1001378667 on a 1001.38 s TS); "raw": pts (streams)
    first_pts: float | None
    def blocks(self, cancel: threading.Event) -> Iterator[tuple[float, "np.ndarray"]]
        # 0.25 s blocks, time anchored per decoded frame, never a running sample count
class PersistentWhisper:   # loaded once per session, on live-asr, freed there
    def __init__(self, *, device_policy: str, hotwords: str | None,
                 whisper_model_cls, torch_module, log)
    device: str; model_name: str; fell_back: bool
    def transcribe(self, utt: Utterance, *, language: str | None) -> tuple[list[dict], str | None, float]
        # segments in session time, detected language, probability; CUDA runtime error ->
        # reload small int8 on CPU once and retry this utterance
    def close(self) -> None                            # del model + torch.cuda.empty_cache()
class LanguageLock:
    def __init__(self, explicit: str | None)
    def observe(self, lang: str | None, prob: float, speech_s: float) -> str | None
        # lock at prob >= 0.8 with >= 5 s of speech, else a majority (>= 60 % of the
        # detections) over the first 30 s; still none after 60 s of speech -> "failed"
        # (live_err_need_source_lang)
    locked: str | None
def filter_hallucinations(segs: list[dict], recent: Sequence[str]) -> list[dict]
    # drop no_speech_prob > 0.6 and avg_logprob < -1.0; drop compression_ratio > 2.4;
    # drop exact repeats of the last 2 texts; flag with whisper_sanity (subtitle, no dub)
```

`live_translate.py`
```python
@dataclass(frozen=True)
class Outcome:
    text: str; ok: bool; latency_s: float
    error: str | None = None       # rate_limited | quota | timeout | unavailable | error
class LiveTranslateError(Exception):
    key: str; params: dict
class LiveTranslator(Protocol):
    name: str; online: bool
    def prepare(self, src: str, tgt: str) -> None      # load / warm-up; raises LiveTranslateError
    def translate(self, text: str, *, context: Sequence[tuple[str, str]],
                  timeout_s: float) -> Outcome          # never raises
    def close(self) -> None                             # free VRAM / keep_alive 0
class MarianLiveTranslator: ...   # one tokenizer + model per route leg, loaded once, cuda
                                  # if available, greedy, max_length 512; a pivot route runs
                                  # leg 1 then leg 2 inside the same timeout; a group model
                                  # gets its target token prepended to the source text
class OllamaLiveTranslator: ...   # health check once, warm-up keep_alive "30m",
                                  # close keep_alive 0; prompt via build_translation_prompt
                                  # (prev_text, next_text=None, global_context=None), think off
class GoogleLiveTranslator: ...   # deep_translator in a single-slot executor,
                                  # future.result(timeout); hung call abandoned; 0.3 s pacing
class DeeplLiveTranslator: ...    # requests.post(timeout=(3, 5)); 429 rate_limited,
                                  # 456 quota, 403 unavailable
def make_translator(engine: str, **deps) -> LiveTranslator
@dataclass(frozen=True)
class MarianLeg:
    model: str                      # e.g. "Helsinki-NLP/opus-mt-tc-big-en-pt"
    target_token_candidates: tuple[str, ...] = ()   # group models only, e.g. (">>por<<",
                                                    # ">>pt<<"); the first one present in
                                                    # tokenizer.supported_language_codes wins
@dataclass(frozen=True)
class MarianRoute:
    legs: tuple[MarianLeg, ...]     # 1 leg (direct) or 2 legs (pivot through English)
    pivot: bool
EN_LEGS: Mapping[str, tuple[MarianLeg | None, MarianLeg | None]]
    # per project language code: (X->en leg, en->X leg), a static table built from the
    # [FD] Hub query of 2026-09-25 (4.9); tested for all 25 non-English codes
def marian_route(src: str, tgt: str, *, hub_has: Callable[[str], bool] | None,
                 is_cached: Callable[[str], bool]) -> MarianRoute | None
    # order: cached direct opus-mt-{s}-{t}; cached tc-big; hub direct; hub tc-big (hub_has
    # is None when offline, then only cached models count); else pivot src->en->tgt from
    # EN_LEGS (each leg cached or on the hub); else None -> live_err_marian_pair
def marian_is_cached(route: MarianRoute, *, loader=None) -> bool   # local_files_only=True,
                                                                   # every leg
TIMEOUTS_S = {"marian": 5.0, "ollama_delayed": 8.0, "ollama_live": 3.0, "google": 5.0, "deepl": 5.0}
```

`live_tts.py`
```python
EDGE_BYTES_PER_SECOND = 6000       # 48 kbit/s CBR mono mp3 (edge-tts communicate.py:408);
                                   # [CT] C34 RUN: bytes/6000 equals the decoded duration
                                   # to the millisecond (it, en, ja voices, edge-tts 7.2.8)
@dataclass(frozen=True)
class Clip:
    seg_id: int; gen: int; path: str; duration: float; rate: str
    voice_start_s: float           # measured leading silence (0.16-0.21 s observed)
    voice_end_s: float             # end of audible speech (trailing silence 0.26-0.84 s)
    @property
    def audible_s(self) -> float   # voice_end_s - voice_start_s: what slot fitting uses
def measure_silence(path: str, *, av_module, threshold_dbfs: float = -45.0,
                    frame_s: float = 0.01) -> tuple[float, float] | None
    # decodes the mp3 with PyAV (already required by live mode) on live-tts; returns
    # (voice_start_s, voice_end_s) or None on failure (then 0.0 and duration are used)
class EdgeDurationModel:           # per session, per language
    def __init__(self, lang: str, *, seed_estimate: Callable[[str, str], float])
        # seed_estimate = timing.estimate_tts_duration_s (XTTS characters per second,
        # timing.py:13-20,56-64); [CT] C35 REFUTED it for Edge: +2 % it, -30 % en, -59 % ja
    def estimate(self, text: str, rate_pct: int) -> float
        # before any clip: seed; after: len(text) / cps_ema, divided by (1 + rate_pct/100)
    def observe(self, text: str, rate_pct: int, audible_s: float) -> None
        # cps_ema over rate-normalised audible durations, alpha 0.3
def choose_rate(text: str, slot_s: float, model: EdgeDurationModel, *,
                max_pct: int = 30) -> int
    # N = clamp(ceil((model.estimate(text, 0) / slot_s - 1) * 100), 0, max_pct); the
    # playback speed (1.0-1.3) corrects what the estimate misses
def mp3_cbr_duration_s(n_bytes: int) -> float
class EdgeClipSynth:               # thread "live-tts" with its own asyncio loop
    def __init__(self, voice: str, out_dir: Path, *, communicate_factory=None,
                 max_concurrent: int = 2, min_interval_s: float = 0.25,
                 connect_timeout: int = 3, receive_timeout: int = 5,
                 breaker: CircuitBreaker, clock=time.monotonic, av_module=None)
        # the timeouts MUST be int (edge-tts communicate.py:360-363 raises TypeError on a
        # float, [CT] C34); support for the keywords is detected once with
        # inspect.signature(Communicate), never by catching TypeError
    def start(self) -> None
    def submit(self, seg_id: int, gen: int, text: str, rate: str, deadline_mono: float) -> bool
    results: "queue.Queue[tuple[int, int, Clip | None, str | None]]"
    def stop(self, timeout_s: float) -> bool      # cancels tasks, removes .part files
```

`live_sync.py`
```python
@dataclass(frozen=True)
class EdgeEstimate:
    observed: float | None        # end of the last decoded audio block (session time)
    linear: float | None          # now_mono + max(edge_i - mono_i) over the window
    effective: float | None       # linear unless stalled, else observed
    stalled: bool                 # no block for > stall_factor * max_gap_s
    max_gap_s: float              # largest idle gap between bursts in the window
class EdgeEstimator:
    def __init__(self, *, window_s: float = 60.0, burst_gap_s: float = 0.5,
                 default_gap_s: float = 6.0, min_gaps: int = 3, stall_factor: float = 2.0,
                 warmup_s: float = 10.0)
    def observe(self, edge: float, mono: float) -> None    # live-decode, once per block
    def reset(self, mono: float) -> None                    # (re)connect, discontinuity
    def estimate(self, mono: float) -> EdgeEstimate

@dataclass(frozen=True)
class LiveTiming:
    umax_s: float; hold_s: float; min_ahead_s: float; resume_ahead_s: float
def derive_live_timing(delay_s: float, *, mode: str, device: str, engine: str,
                       dub: bool) -> LiveTiming                  # 5.8
def recommended_delay_s(*, device: str, dub: bool) -> float     # 12 / 9 GPU, 15 / 11 CPU
def live_distance_s(max_gap_s: float) -> float                  # clamp(1.5 * gap, 2, 8)

@dataclass(frozen=True)
class SyncAction:
    kind: str                     # none | speed | pause | resume | seek | reload
    value: float | None = None    # speed factor, or target time for seek/reload
class DelayController:            # streams (live and VOD URLs)
    def __init__(self, *, mode: str, delay_s: float, tolerance_s: float = 0.5,
                 band_s: float = 3.0, max_nudge: float = 0.03, hold_s: float = 2.0,
                 live_extra_s: float = 4.0)
    def step(self, *, mono: float, edge: EdgeEstimate, player: float | None,
             user_paused: bool, paused_for_cache: bool, self_paused: bool,
             cache_end: float | None) -> SyncAction
    def set_mode(self, mode: str, *, mono: float, edge: EdgeEstimate,
                 player: float | None, cache_end: float | None) -> SyncAction
    def set_delay(self, delay_s: float, *, immediate: bool) -> None
    def resume_action(self, *, edge: EdgeEstimate, player: float,
                      cache_end: float | None) -> SyncAction    # after a user pause
    def target_lag(self, edge: EdgeEstimate) -> float
class FilePacer:                  # local files played in real time
    def __init__(self, *, mode: str, min_ahead_s: float, resume_ahead_s: float)
    def step(self, *, player: float | None, ready_until: float, source_done: bool,
             user_paused: bool, self_paused: bool) -> SyncAction    # pause/resume/none only
```

`live_scheduler.py`
```python
@dataclass
class LiveSegment:
    seg_id: int; gen: int; start: float; end: float; text_src: str
    text_tgt: str | None = None; italic: bool = False; dub_ok: bool = False
    clip: Clip | None = None; state: str = "transcribed"
    # transcribed, translated, synth, ready, preloaded, playing, done, dropped
# actions (frozen dataclasses)
ShowSubtitle(seg_id, ass) | ClearSubtitle() | RequestTts(seg_id, gen, text, rate, deadline_mono)
PreloadClip(seg_id, path) | StartClip(seg_id, speed) | PauseClip() | ResumeClip()
StopClip(fade_s) | ClipSpeed(value) | Duck(gain) | Drop(seg_id, reason)
class DubScheduler:
    def __init__(self, *, mode: str, source: str, lead_s: float = 0.25,   # initial voice_lead
                 preload_s: float = 1.5,
                 late_tolerance_s: float = 0.5, max_live_lag_s: float = 4.0,
                 max_speed: float = 1.3, overhang_s: float = 0.6, merge_gap_s: float = 0.6,
                 unduck_tail_s: float = 0.2, duck_gain: float = 0.3, duck_ramp_s: float = 0.2,
                 duck_latency_s: float = 0.4,   # command -> audible attenuation; 0.19-0.39 s
                                                # measured with ao=pcm ([CT] C30); S3 sets
                                                # the value per platform
                 sub_min_display_s: float = 1.5, sub_grace_delayed_s: float = 1.5,
                 sub_grace_live_s: float = 6.0, dub: bool = True, subs: bool = True)
    def upsert(self, seg: LiveSegment) -> None
    def clip_ready(self, seg_id: int, gen: int, clip: Clip | None, reason: str | None) -> None
    def tick(self, now: float | None, mono: float, *, main_running: bool, main_speed: float,
             voice_state: str, clock_epoch: int) -> list[object]
        # now is None while the clock is invalid (2.2 PlaybackClock): nothing starts then
    def on_seek(self, now: float, gen: int) -> list[object]
        # called for explicit seeks and whenever clock_epoch changed with a jump > 1.0 s
    def on_discontinuity(self, now: float) -> list[object]
        # a jump > 1.0 s WITHOUT an epoch change (a PTS gap inside the stream, [CT] C20:
        # time-pos jumped 1009.36 -> 1011.80 across a +2.44 s gap): slots already passed
        # are dropped as late, the current clip stops only if its slot has passed; no ASR
        # restart, captions keep their rules
    def set_mode(self, mode: str) -> None; def set_dub(self, on: bool) -> list[object]
    def set_subs(self, on: bool) -> list[object]; def set_lead(self, lead_s: float) -> None
    def ready_until(self, now: float) -> float   # end of contiguous ready coverage from now
    def metrics(self) -> dict[str, float]         # voiced, dropped, late, margin_p90
def wrap_caption(text: str, max_chars: int = 42, max_lines: int = 2) -> list[str]
def paginate_caption(text: str, start: float, end: float) -> list[tuple[float, float, list[str]]]
def ass_escape(text: str) -> str
    # mirrors mpv's own OSD escaping (osd_libass.c:200-252, [CT] finding 12): every "\"
    # is followed by U+2060 WORD JOINER (so "\n" or "\N" typed in speech stays literal),
    # every "{" becomes "\{", nothing is doubled; line breaks are inserted as "\N" by
    # caption_ass AFTER escaping. (`escape-ass` exists only from mpv 0.38.)
def caption_ass(lines: Sequence[str], *, font_px: int, italic: bool) -> str
```

`live_store.py`
```python
TS_PACKET = 188
LIVE_TRANSPORT = "vtlive"          # "vtlive" | "lavf-follow" | "hls-event"; set by spike S2
class LiveStore:
    def __init__(self, directory: Path, *, chunk_bytes: int = 32 << 20,
                 cap_bytes: int = 1024 << 20, keep_margin_bytes: int = 16 << 20,
                 opener=open, remover=os.remove, disk_free=shutil.disk_usage)
    written: int; earliest: int; ended: bool
    def append(self, data: bytes) -> None                  # live-ingest only
    def mark_gap(self) -> None; def finish(self) -> None
    def register_reader(self, reader_id: str) -> None
    def set_low_water(self, reader_id: str, offset: int) -> None
    def min_low_water(self) -> int
    def read_at(self, offset: int, size: int, *, cancel: threading.Event | None = None,
                timeout: float | None = None) -> bytes | None
        # bytes when data is available; b"" ONLY at a true end (finished and offset ==
        # written) or after close/cancel; None when `timeout` expired (TailReader retries;
        # the mpv adapter never passes a timeout, see MpvStreamAdapter)
    def free_bytes(self) -> int
    def player_uri(self, session_id: str, *, offset: int | None = None) -> str
    def close(self) -> None                                 # wakes every reader with EOF
    def remove(self) -> bool                                # retries PermissionError (Windows)
class TailReader(io.RawIOBase): ...    # readinto/seek/tell/cancel; for av.open(..., format="mpegts")
class MpvStreamAdapter:                # behind register_raw_stream_protocol (player_engine)
    def __init__(self, store: LiveStore, base_offset: int, reader_id: str = "mpv")
    def read(self, size: int) -> bytes
        # blocks until data, true end, cancel or close; NEVER returns b"" on a timeout,
        # because one b"" is a permanent EOF for mpv ([CT] finding 7, RUN p13:
        # eof-reached=True, no resume when data arrived later)
    def seek(self, pos: int) -> int
        # pos is RELATIVE: mpv's first seek(0) defines base_offset as position 0
        # (stream_cb.h:111-115); returns pos exactly, or -1 (MPV_ERROR_GENERIC) when the
        # target is below `earliest` (evicted); a target beyond `written` blocks until
        # written, cancel or close. mpv ignores the returned value except its sign
        # (stream_cb.c:29-33), so a clamped position would silently desync
    size = None                        # never a size callback: python-mpv (mpv.py:1891)
                                       # and our registration read it only at open
    def cancel(self) -> None           # any thread, never blocks: sets the Event, notifies
    def close(self) -> None            # sets `closed` (threading.Event) and unregisters
                                       # the reader; the stop sequence waits on `closed`,
                                       # not on idle-active, which fires about 100 ms
                                       # earlier ([CT] finding 7, 3 runs)
    closed: threading.Event
class SeekIndex:                       # sparse (pts, byte offset), one entry per >= 0.5 s
    def add(self, pts: float, offset: int) -> None
    def offset_for(self, pts: float) -> int | None          # aligned to 188, minus 256 KiB
```

`live_source.py`
```python
@dataclass(frozen=True)
class ResolvedStream:
    title: str; is_live: bool; live_status: str | None
    video_url: str; audio_url: str | None; http_headers: dict[str, str]
    vcodec: str | None; acodec: str | None   # None when yt-dlp reports none (YouTube
                                             # live audio 233/234: acodec None, [CT] RUN)
    height: int | None; resolved_mono: float
class LiveSourceError(Exception):
    key: str; detail: str
def live_format_selector(max_height: int, is_live: bool) -> str
    # both live and VOD: f"bv*[height<={H}][vcodec^=avc1]+ba/b[height<={H}]"
    # ([CT] R2 RUN on a YouTube live stream with yt-dlp 2026.08.19: selects 232+234)
def is_ts_compatible(vcodec: str | None, acodec: str | None) -> str
    # "yes" | "no" | "unknown"; video avc1/h264 or hevc/hvc1/hev1; audio mp4a/aac or mp3;
    # None or an empty codec -> "unknown"
def probe_codecs(stream: ResolvedStream, *, run, timeout_s: float = 20.0) -> tuple[str | None, str | None]
    # only when is_ts_compatible(...) == "unknown": ffprobe -v error -rw_timeout 10000000
    # [-user_agent UA] [-headers ...] -show_entries stream=codec_type,codec_name -of json
    # <url> for the video URL and the audio URL; ffprobe ships with ffmpeg on both
    # systems and is already used by output_media.py:47-63; no_window_kwargs on Windows.
    # Still unknown after the probe -> live_err_codec ([CC] G9)
def ffmpeg_major_version(*, run) -> int | None      # parses `ffmpeg -version`, cached
def resolve_stream(url: str, *, max_height: int, ytdlp_cls, js_runtimes, log) -> ResolvedStream
def build_ingest_command(stream: ResolvedStream, *, ffmpeg: str = "ffmpeg",
                         ffmpeg_major: int | None,
                         output_ts_offset: float | None = None,
                         input_seek_s: float | None = None) -> list[str]
@dataclass(frozen=True)
class IngestDecision:
    kind: str                      # continue | restart | re_resolve_restart | finish | fail
    delay_s: float = 0.0
class IngestPolicy:                # pure; injected clock
    def __init__(self, *, stall_s: float = 15.0, backoff=(1, 2, 4, 8, 16, 30),
                 max_restarts: int = 10, restart_window_s: float = 600.0,
                 healthy_reset_s: float = 300.0, re_resolve_age_s: float = 4 * 3600.0)
    def on_bytes(self, mono: float) -> None
    def on_tick(self, mono: float) -> IngestDecision        # stall detection
    def on_exit(self, rc: int, stderr_tail: Sequence[str], *, is_live: bool,
                mono: float) -> IngestDecision
    def on_resolved(self, mono: float) -> None
class IngestWorker:
    def __init__(self, url: str, store: LiveStore, *, resolve, popen, register, unregister,
                 policy: IngestPolicy, last_edge: Callable[[], float | None],
                 vod_ahead_cap_bytes: int = 256 << 20, disk_floor_bytes: int = 512 << 20,
                 log, post)
    def start(self) -> None; def stop(self, timeout: float) -> None
```

`live_session.py`
```python
@dataclass(frozen=True)
class LiveConfig:
    source: str; source_kind: str            # file | url
    start_at: float; lang_source: str; lang_target: str; voice: str
    engine: str; settings: LiveSettings
    engine_opts: dict = field(repr=False)    # holds the DeepL key: never in a repr, a
                                             # traceback or the log ([CC] G25); configs
                                             # are never logged whole
    hotwords: str | None; session_dir: Path; device_policy: str    # auto | cpu
@dataclass(frozen=True)
class LiveTimeouts:                           # production defaults; tests inject ~0.1 s
    join_decode_s: float = 2.0; join_asr_s: float = 3.0; join_tts_s: float = 3.0
    mt_extra_s: float = 1.0; ingest_kill_s: float = 2.0; stream_closed_s: float = 2.0
@dataclass(frozen=True)
class LiveFactories:
    resolve: Callable; ingest: Callable; store: Callable; decoder: Callable; vad: Callable
    whisper: Callable; translator: Callable; tts: Callable; clock: Callable[[], float]
    timeouts: LiveTimeouts = LiveTimeouts()
@dataclass(frozen=True)
class LiveStatus:
    state: str   # starting | loading_models | connecting | detecting | buffering | waiting
                 # | running | reconnecting | stopping | ended | stopped | failed
    lag_s: float | None; target_delay_s: float | None; device: str; engine: str
    voiced: int; dropped: int; skipped_s: float
    warning_key: str | None; warning_params: dict; warning_action: str | None
    error_key: str | None; error_params: dict
class LiveSession:
    def __init__(self, cfg: LiveConfig, *, video: PlayerBackend, voice: VoiceBackend | None,
                 bridge: EventBridge, clock_view: PlaybackClock, factories: LiveFactories,
                 thread_factory=threading.Thread, log: Callable[[str], None])
        # the GUI passes App._redirecting_thread_factory (2.4), which wraps each target
        # so it installs the thread-local log redirect first ([CC] G2)
    def start(self) -> None                    # returns at once
    def request_stop(self) -> None; def join(self, timeout_s: float) -> bool   # idempotent
    def set_sync_mode(self, mode: str) -> None; def set_delay(self, seconds: float) -> None
    def set_engine(self, engine: str) -> None  # applied by live-mt at the next sentence
    def set_dub_enabled(self, on: bool) -> None; def set_subs_enabled(self, on: bool) -> None
    def set_user_volume(self, value: float) -> None
    def notify_user_seek(self, t: float) -> None      # file sources only
    def notify_user_pause(self, paused: bool) -> None
    def status(self) -> LiveStatus                    # copy under a lock, O(1)
def build_live_config(values: Mapping[str, object], *, settings: LiveSettings,
                      cache_dir: Path, now: datetime) -> LiveConfig          # pure
def write_session_lock(path: Path, *, pid: int, start_token: str | None) -> None
def cleanup_stale_sessions(root: Path, *, owner_alive: Callable[[int, str | None], bool],
                           now: float, max_age_h: float = 24.0,
                           remover=shutil.rmtree) -> list[Path]
    # removes a session dir only when owner_alive(pid, start_token) is False; the age
    # rule applies only when session.lock is missing or unreadable ([CC] G12)
```

`platforms.py` additions ([CC] G12):
```python
def pid_alive(pid: int, *, sys_platform: str = sys.platform, kernel32=None) -> bool
    # POSIX: os.kill(pid, 0) (ProcessLookupError -> False, PermissionError -> True).
    # Windows: NEVER os.kill, which is not a liveness probe there (CPython os.rst: any
    # value other than CTRL_C_EVENT/CTRL_BREAK_EVENT calls TerminateProcess); instead
    # OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION) + GetExitCodeProcess == STILL_ACTIVE
    # (259) through ctypes; a failed OpenProcess with ERROR_ACCESS_DENIED counts as alive
def process_start_token(pid: int, *, sys_platform: str = sys.platform) -> str | None
    # Linux: field 22 (starttime) of /proc/<pid>/stat; Windows: GetProcessTimes creation
    # time; used with the pid so a recycled pid is not taken for the owner
```

Setters called from Tk only enqueue control messages. `live-sched` applies them at its
next tick, at most 20 ms later.

### 2.3 Tk glue

`PlayerPanel(tk.Frame)` in `player_panel_tk.py`:
```python
class PlayerPanel(tk.Frame):
    def __init__(self, parent, *, ui_s, theme, make_button, keyboard_operable, on_command,
                 log, logo_path: Path | None)
        # on_command(name: str, args: dict): the panel never calls mpv or the controller;
        # keyboard_operable = App._keyboard_operable (video_translator_gui.py:6175-6188),
        # injected so the panel reuses the pattern of commit 4b3fb66
    def render(self, state: PlayerState, *, position: float | None) -> None
    def notify(self, key: str, params: dict, *, seconds: float = 4.0) -> None
        # transient notice (snapshot saved, VO fallback used, ...): replaces the "Now
        # playing" text for `seconds`, then restores it; this is the "status line"
    def render_live_range(self, start: float | None, played: float | None,
                          edge: float | None) -> None    # stream sessions: LIVE window
    def show_unavailable(self, status: LibmpvStatus, *, install_cmd: str | None) -> None
    def host_wid(self) -> int          # inner black frame; & 0xFFFFFFFF on Windows
    def relabel(self) -> None          # from App._apply_lang
    def apply_theme(self) -> None      # from App._apply_ui_settings
    def set_fullscreen_layout(self, on: bool) -> None
def icon_shapes(name: str, size: int) -> list[tuple[str, list[float]]]   # pure, tested
```

Widget tree inside the existing `self._player_area` (video_translator_gui.py:7009-7012,
FIELD with a BORDER highlight):
- `video_host`: `tk.Frame(bg="#000000", highlightthickness=0, bd=0)`, placed with
  `relwidth=1, relheight=1`. mpv's child window covers the whole parent ([04] 4.1).
- `placeholder`: a sibling frame at the same place, lifted when idle, initializing or
  unavailable. It holds the logo, the message label and the Install button.
  - Logo ([CC] G28): `assets/icon_256.png` through `tk.PhotoImage` (Tk 8.6 and later
    read PNG natively; `tkinter.TkVersion` is 8.6 here; the Tk version of the Windows
    Python build is UNVERIFIED),
    scaled with `subsample` to at most a third of the pane height; the installer already
    copies that file (setup_windows.bat:788) and the Linux checkout has it. When the file
    is missing or unreadable, a canvas-drawn play triangle in `#c3c3c3` on `#000000`.
  - Lifting a Tk sibling over mpv's child works on X11 ([CT] C3 RUN); on Windows the
    d3d11 flip model is an S4 item (fallback `d3d11_flip=no` in the Windows options).
- Seek row: a Canvas seek bar plus time labels in `VT.Mono`.
- Row A:
  - "Now playing" in `VT.Small`, ellipsized; transient notices use the same label
    (`notify`);
  - A/B segmented toggle (Dubbed | Original);
  - Subtitles toggle;
  - Playlist button;
  - "Translate in real time" button (`player_btn_live`).
- Row B:
  - six transport icons;
  - snapshot and open folder;
  - a spacer;
  - volume icon plus a `ttk.Scale` (`Horizontal.TScale`, themed by `ui_theme_tk.py:229`);
  - fullscreen.
- `LiveBar`: packed under row B whenever the player is ready (idle row) and grown while
  a session exists (below).

Keyboard operability ([CC] G6, the class of defect fixed in 4b3fb66):
- every Canvas control (six transport icons, snapshot, open folder, volume icon,
  fullscreen, the A/B segmented toggle, the Subtitles toggle, the LiveBar mode toggle)
  takes Tab focus through the injected `keyboard_operable(widget, action)`, draws a
  focus ring (`highlightthickness=2`, `highlightcolor` ACC, `highlightbackground` its own
  background) and activates on Return, KP_Enter and space (the helper returns "break");
- the seek bar Canvas takes focus and handles Left/Right (10 s) and Home/End itself,
  returning "break";
- segmented toggles move with Left/Right while focused;
- every icon has a tooltip naming its shortcut (3.7).

Theming:
- Colours: controls read `theme.palette` at build and in `apply_theme()` ([01] 3.1: a
  separate module would otherwise get stale copies of the GUI globals).
- The video host and the placeholder use only colours reserved in `TK_DEFAULT_COLORS`
  (`videotranslator/ui_theme.py:43-49`): background `#000000`, text `#a3a3a3`, logo
  `#c3c3c3`. The recolour walk never remaps them (`_ensure_distinct`).
- Icons are Canvas polygons from `icon_shapes()`, sized `round(16 * theme.scale)`. No
  Unicode transport glyphs (Windows font coverage, [01] 3.4). Canvas items are not covered
  by `recolor_widget_tree` (`ui_theme_tk.py:91`), so `apply_theme()` redraws them.

Seek bar (Canvas):
- trough BORDER, played part ACC, knob FG;
- stream sessions add a LIVE badge and the window from session start to the edge.
- Pure maths lives in `player_core`.
- While the user drags, the poll does not move the knob. Seeks go out as `keyframes` at
  most 10 per second, then one `exact` seek on release.

Reflow: `controls_visible(width, scale)`:
- hides back/forward 10 s below 440 px;
- hides snapshot and open folder below 380 px.
The 900 px window floor leaves about 377 px for the player ([01] 1.1). The hidden actions
stay reachable by keyboard: Left/Right are the same 10 s steps as the buttons, `s` takes a
snapshot and `o` opens the folder (3.7); the draft's claim was false before these keys
existed ([CC] 8 item 1).

Poll loop:
- `after(50, _tick)` while an item is loaded or a session exists, stopped otherwise;
- each tick: `snapshot = bridge.drain()`; `playback-restart` events go to
  `clock.on_playback_restart`; then `clock.observe(..., seeking=...)` (ignored while the
  value is invalid, 2.2); then `controller.apply_events(snapshot, clock.now(mono))`, then
  `panel.render(state, position=clock.now(mono))`; `click`/`dblclick`/`wheel` events go
  through `mouse_action` and then `video_host.focus_set()`, so a click on the video never
  leaves Tk shortcuts dead if the child window took focus ([CC] G17);
- every 5th tick it also renders `session.status()`.
The after id is kept and cancelled on close. Nothing in the app cancels `after` today
([01] 9).

`LiveBar(tk.Frame)` in `live_bar_tk.py`:
- idle row, shown whenever the player is ready, so mode, delay and engine are chosen
  BEFORE a start ([CC] G26): [Delayed | Live] [Delay slider plus "Delay: 12 s"] [engine
  combobox, readonly, four items] [privacy info icon with a tooltip]. The slider edits
  `live_delay_s` when the loaded item or the URL box points to a stream, and
  `live_file_ahead_s` for a local file (range 4-30 s); the label is the same.
- while a session runs, a second row appears: [Stop translation] [status label: lag,
  state]. At narrow widths the idle row wraps into two rows.
- A banner line appears under it for warnings, with an optional action button (for
  example "Switch to MarianMT") and a close button (canvas cross, keyboard operable,
  tooltip `live_tip_banner_close`).
- In a live session, the player's A/B toggle means dub on/off, and its Subtitles toggle
  means live subtitles on/off. The LiveBar does not duplicate them.
- It follows the same `relabel()` / `apply_theme()` contract.

GUI file changes (anchors at `c155227`):
- After `UI_STRINGS = {...}` (starts :358): `merge_into(UI_STRINGS)` from
  `ui_strings_player` (Q5).
- `_build_ui` (:6956-7060): P0 restructure (3.1).
- `_build_header` (:6421): a "Player" badge in the `_status_badge` pattern (:6126). Its
  colour comes from `quick_presence`, and its tooltip gives the reason.
- `_build_input_section`:
  - `_batch_listbox` (:6484) gets `exportselection=False` and `<<ListboxSelect>>` bound to
    `_on_input_select`;
  - new button `self._btn_live_url` (`btn_live_url`) next to Download, in a grid row with
    two `uniform` columns; both labels get `wraplength` equal to the column width
    (updated on `<Configure>`), so long translations (de, fi) wrap instead of clipping
    ([CC] G31; P6 screenshots in de and fi).
- `_add_files` / `_remove_file` / `_clear_files` (:7913-7930): call
  `_sync_player_playlist()`.
- `_apply_ui_settings` (:7338): call `apply_theme()` on the panel and the bar.
- `_apply_lang` (:7401): call `relabel()` on both.
- `_start` (:7943) and `_start_download` (:7791):
  - refuse while live is active (`live_err_busy_job`);
  - call `_release_player_then(dispatch)` (3.6).
- Workers:
  - `_dispatch_download.run` (:7831), `_run_with_segments.do` (:8153) and
    `_run_batch.run_all` (:8185) collect `JobOutput`s;
  - they post `after(0, self._on_job_outputs, outputs)` right before their existing
    `_on_done` call.
- `_open_editor` (:8109) and `SubtitleEditor.__init__` (:5315): `on_seek`, `on_change`,
  editor placement, source preview; `self._editor_open = True` while the editor exists
  (cleared by confirm, cancel and window close), because `_open_editor` sets
  `self._running = False` (:8113) ([CC] G1).
- `_GlobalRedirect` (:5238): `write` returns `len(s)` and `flush` does nothing when
  `self._original` is None (pythonw), `fileno` raises `io.UnsupportedOperation` then
  ([CC] G2, R9). Three lines.
- `_redirecting_thread_factory(target, name, daemon=True)`: returns a `threading.Thread`
  whose run installs `_thread_local.redirect = _TkStreamRedirect(self, self._log_write)`
  and removes it in `finally` (the pattern of :7852/:7906). Used for `player-init`, the
  installer worker, `live-stop`, `app-close` and passed to `LiveSession` as
  `thread_factory`.
- Settings window (:7250-7330, [CC] G22): a third section after Language, title
  `settings_player` (VT.SmallBold, upper case like the others), a card with the
  checkboxes `opt_player_autoload` and `opt_keep_original_audio`, then the footer label
  `player_credits {license}` in `VT.Small` FG2 above the Reset/Close buttons. relabelling
  goes into `_relabel_settings` (:7372-7384).
- `_on_close` (:8376): new sequence (6.4).
- New small methods:
  - `_ensure_player`, `_on_player_ready`, `_on_input_select`, `_sync_player_playlist`;
  - `_on_job_outputs`, `_on_player_command`, `_on_player_key`, `_toggle_fullscreen`;
  - `_install_player`, `_release_player_then`;
  - `_snapshot_live_config`, `_start_live_file`, `_start_live_url`, `_stop_live`,
    `_live_blocked_reason` (returns the key of the first failing guard, also used for
    the disabled buttons' tooltips);
  - `_begin_close`, `_finish_close`, `_redirecting_thread_factory`.
- New flags: `_editor_open`, `_installing` (set by `ComponentInstaller` starts and
  cleared in `on_done`; the existing `_install_deps` also sets it next to `_running`,
  one line, so a startup pip install reports `live_err_busy_install` instead of
  `live_err_busy`, [CC] G3).

Budget: +360 net lines in the GUI file over all phases, strings excluded; checked in
review.

### 2.4 Thread ownership

| Thread | Created by | May do | Must not |
|---|---|---|---|
| Tk main | Tk | all widgets; `PlayerController`; panels; `save_config`; `bridge.drain()`; `LiveSession` setters and `status()` | any synchronous libmpv call; block more than ~50 ms; `terminate()` |
| `MPVEventHandlerThread`, one per instance | python-mpv (`mpv.py:910-913`) | `bridge.set_latest/post` | Tk calls (including `after`); `terminate`; `wait_*`; sleeping |
| `mpv-cmd` (video instance) | `MpvBackend` | executes queued user commands (load, stop, seek, pause, volume/mute via `apply_mix` when the mixer owner is "cmd", tracks, subtitles, `af`, screenshot via `command_async`) | Tk |
| libmpv stream threads (not Python-created) | libmpv via `stream_cb` | `MpvStreamAdapter.read/seek` (blocking on the store Condition); `cancel` from another mpv thread about 0.1 s after `stop` (non-blocking, [CT] C13 RUN: thread `Dummy-N`); `close` (sets `closed`); `bridge.post` | Tk; ANY libmpv call on the same instance (deadlock, stream_cb.h:48-51); session state other than the store; printing |
| `player-init` (short) | `_ensure_player` via `_redirecting_thread_factory` | subprocess probe, `load_mpv`, `create_video_backend`, VO fallback re-creation (only if S1 proved `X11ErrorGuard.restore`, 3.1); posts `after(0, _on_player_ready, ...)` | widgets |
| `live-ingest` (+ stderr drain) | `LiveSession` | yt-dlp resolve, ffmpeg Popen (registered), `store.append`, `IngestPolicy`, free-space checks | Tk; mpv |
| `live-decode` | `LiveSession` | `AudioDecoder`, then `StreamingVad`, then `UtteranceSegmenter`; `edge.observe`; `SeekIndex.add`; never blocks on downstream for streams | Whisper; Tk; mpv |
| `live-asr` | `LiveSession` | owns `PersistentWhisper` (loads and frees it), `LanguageLock`, `SentenceAssembler` | Tk; mpv |
| `live-mt` | `LiveSession` | owns the `LiveTranslator` (loads/frees Marian, Ollama warm-up/unload, HTTP) | Tk; mpv |
| `live-tts` | `EdgeClipSynth`, with the session's `thread_factory` | its asyncio loop, Edge requests, clip files, `measure_silence` (PyAV) | Tk; mpv |
| `live-sched` | `LiveSession` | 50 Hz tick: `DubScheduler`; every 1 s `DelayController` or `FilePacer`; `video.rt` (overlay, speed, pause, duck); exclusive owner of the `VoiceBackend`; seeks via `video.seek` (queued on mpv-cmd); applies `VolumeMixer` in fallback mode; publishes `LiveStatus` at 4 Hz | Tk |
| `live-stop` / `app-close` (short) | Tk via `_redirecting_thread_factory` | `session.request_stop/join`, bridge close, `voice.terminate`, `video.terminate`, then `X11ErrorGuard.restore()` right after the video terminate returns | Tk |
| install worker (short) | `ComponentInstaller` via `_redirecting_thread_factory` | `install_windows`, `run_plan`, pip (`pip_install_command`), `refresh_import_paths`; logs via `_log_async` (:7588) | widgets; `App._running` |

Output rules:
- Our live and player code never `print`. It receives a `log` callback that the glue wraps
  around `_log_async`, rate-limited to one line per event kind per 10 s plus one summary
  line per minute. Long sessions therefore do not churn the 5,000-line log cap ([02] 10).
- Library code on those threads may still write (tqdm from huggingface_hub while a Marian
  model downloads, `warnings`, logging fallbacks). Every thread we create comes from
  `_redirecting_thread_factory`, so such writes reach the GUI log; that is the mechanism
  behind "download with progress in the log" (6.2 row 15).
- Threads we do not create (python-mpv's event thread, libmpv stream threads, asyncio
  internals) have no redirect: `_GlobalRedirect` then writes to the original stream, or
  drops the text under pythonw where that stream is None (R9). None of them can raise
  AttributeError any more ([CC] G2).
- All threads are daemons.

### 2.5 Config keys

The keys are flat and normalised by `player_settings`; bad values fall back to defaults.
Writes happen only on the Tk thread (`save_config` has no lock, [01] 7).

| Key | Type / range | Default | Notes |
|---|---|---|---|
| `player_volume` | int 0-130 | 100 | save debounced 1 s |
| `player_muted` | bool | false | |
| `player_audio` | dubbed / original | dubbed | reapplied on each load when A/B is available |
| `player_subs_visible` | bool | true | |
| `player_autoload_result` | bool | true | F2, settings checkbox `opt_player_autoload` |
| `player_vo_profile` | one of `VO_PROFILES[platform]` | first accepted entry | written only after a VO fallback worked |
| `player_probe` | object {fingerprint, ok, api, mpv_version, vo_profiles_ok} | absent | cache of the subprocess load check; internal |
| `keep_original_audio` | bool | true | pipeline option (Q3), `TranslationJobConfig` field, CLI `--no-original-audio`, checkbox `opt_keep_original_audio` |
| `live_sync_mode` | delayed / live | delayed | |
| `live_delay_s` | float 6-30, absent = recommended | absent | streams; written only when the user moves the slider |
| `live_file_ahead_s` | float 4-30, absent = 8 with the dub, 4 subtitles only | absent | local files: translated lead the pacer keeps ahead of the playhead in Delayed mode ([CC] G7); written only when the user moves the slider |
| `live_delay_auto` | bool | true | config only; raises the delay gradually, never lowers it (5.7) |
| `live_engine` | marian / ollama / google / deepl | marian | separate from `_translation_engine` (default "google" at video_translator_gui.py:5643, forced to google by profiles, [01] 7) |
| `live_dub_enabled` | bool | true | the A/B toggle while live |
| `live_subs_enabled` | bool | true | |
| `live_duck_level` | float 0.1-0.6 | 0.3 | config only |
| `live_max_height` | 480 / 720 / 1080 | 720 | ingest format cap |
| `live_buffer_max_mb` | int 256-8192 | 1024 | store cap (4.6) |

Settings "Reset" (`_reset_ui_settings`, :7357) keeps its current scope: theme and panel
order. It additionally clears `player_vo_profile` and `player_probe`.

### 2.6 UI strings and i18n mechanics

Mechanics (Q5):
- `ui_strings_player.py` holds `PLAYER_UI_STRINGS: dict[str, dict[str, str]]` for the 26
  codes of `UI_LANG_OPTIONS`, plus `merge_into(ui_strings)`. It is called once, right
  after `UI_STRINGS`. `merge_into` NEVER raises: a colliding key keeps the GUI file's
  value and an unknown language is skipped, each returned in a list that the GUI logs.
  Collisions and unknown languages are caught by a test instead, so one data slip cannot
  turn app start and every test import into an error ([CC] G27, T4).
- Runtime lookups keep using `App._s` (:5768) with its it -> en -> key fallback.
- `tests/test_ui_i18n_coverage.py` changes:
  - `SOURCE_PATH` (:8) becomes a list: the GUI file plus
    `sorted((ROOT / "videotranslator").glob("*_tk.py"))`;
  - all three scans run over that list: `_S_CALL_RE` (:17), `_FSTRING_RE` (:153) and
    `_CB_RE` (:154) ([CC] 4, last item; today :170 and :187 read only the GUI file);
  - a new test checks that every value of `libmpv_runtime.REASON_KEYS`,
    `player_core.STATUS_KEYS` and `live_health.STATUS_KEYS/WARN_KEYS/ERROR_KEYS` exists in
    every language, and that `set(live_health.STATUS_KEYS) == live_health.LIVE_STATES`
    and `set(REASON_KEYS) ==` every reason `LibmpvStatus` can carry;
  - a literal-key test: every string literal matching `^(player|live|deps|settings)_[a-z0-9_]+$`
    in `videotranslator/(libmpv_runtime|system_packages|player_*|live_*).py` (keys carried
    by `LiveSourceError.key`, `LiveTranslateError.key`, `LiveStatus.warning_key/error_key`,
    `PlayerState.message_key`) must exist in `UI_STRINGS` for all 26 languages, so a typo
    fails CI ([CC] 4);
  - `merge_into` over a copy of `UI_STRINGS` returns no collision and no unknown language.
- Message channels (each key's channel is fixed, [CC] 4):
  - start-time guard errors (`live_err_busy`, `live_err_busy_job`, `live_err_busy_install`,
    `live_err_editor_open`, `live_err_no_url`, `live_err_deps`, `live_err_disk` at start,
    `live_err_deepl_key`, `live_err_marian_pair`, `live_err_ollama`, `live_err_resolve`,
    `live_err_upcoming`, `live_err_codec`, `live_err_need_source_lang`): `messagebox`
    with the existing title key `msg_error_t` (video_translator_gui.py:422 and :547);
  - confirmations (`player_install_confirm`, `deps_install_confirm`,
    `live_confirm_download_pair`, `live_confirm_stop`): `askyesno` with the existing title
    key `msg_confirm` (:420 and :545);
  - runtime warnings (`live_warn_*`, `live_info_marian_pivot`): the LiveBar banner;
  - runtime fatal errors (`live_err_ingest`, `live_err_disk` mid-session, `live_err_asr`
    mid-session, `live_err_internal`): the banner in error style plus the status
    `live_status_failed`;
  - player availability (`player_missing_*`, `player_libmpv_*`, `player_vulkan_missing`,
    `player_probe_crashed`, `player_restart_required`): the placeholder;
  - transient notices (`player_snapshot_saved`, `player_snapshot_failed`,
    `player_vo_fallback_used`, `deps_install_ok`, `deps_install_failed`): `panel.notify`
    on the "Now playing" line for 4 s, plus one log line;
  - disabled-control reasons: tooltips (`live_tip_*`, `player_tip_*_unavailable`,
    `player_tip_results_busy`).
- Brand names stay untranslated: mpv, libmpv, python-mpv, MarianMT, Ollama, Google,
  DeepL, Edge-TTS, Vulkan, YouTube, Twitch.

Keys, with English source text. Placeholders are in braces. Each key lands with the phase
that uses it.

Player, P2 (30):
- `player_idle_hint` "Select a video in the Input list to preview it here"
- `player_initializing` "Starting the player..."
- `player_now_playing` "Now playing: {name}"
- `player_nothing_loaded` "No video loaded"
- `player_btn_playlist` "Playlist"
- `player_playlist_empty` "The playlist is empty"
- `player_playlist_sources` "Input files"
- `player_playlist_results` "Results"
- `player_tip_previous` "Previous (P)"
- `player_tip_rewind` "Back 10 s (Left)"
- `player_tip_stop` "Stop"
- `player_tip_play` "Play (Space)"
- `player_tip_pause` "Pause (Space)"
- `player_tip_forward` "Forward 10 s (Right)"
- `player_tip_next` "Next (N)"
- `player_tip_snapshot` "Save a snapshot of the current frame (S)"
- `player_tip_open_folder` "Open the folder of this video (O)"
- `player_tip_mute` "Mute (M)"
- `player_tip_unmute` "Unmute (M)"
- `player_tip_volume` "Volume"
- `player_tip_fullscreen` "Full screen (F)"
- `player_tip_exit_fullscreen` "Exit full screen (Esc)"
- `player_snapshot_saved` "Snapshot saved: {path}"
- `player_snapshot_failed` "Could not save the snapshot"
- `player_err_load` "Cannot play this file: {name}"
- `player_err_video_output` "The video output could not start on this system."
- `player_vo_fallback_used` "Hardware video output failed: using a slower fallback."
- `player_busy` "The player is busy, please wait."
- `player_badge` "Player"
- `player_tip_results_busy` "Results can be opened when the running job ends"

Job integration, P3 (8):
- `player_audio_dubbed` "Dubbed"
- `player_audio_original` "Original"
- `player_tip_ab_unavailable` "The original audio is not available for this video"
- `player_btn_subs` "Subtitles"
- `player_tip_subs_unavailable` "No subtitles for this video"
- `opt_player_autoload` "Load the result in the player when a job ends"
- `opt_keep_original_audio` "Keep the original audio as a second track"
- `settings_player` "Player" (Settings section title)

Availability and install, P1 (17):
- `player_unavailable_title` "Integrated player not available"
- `player_missing_pymod` "The python-mpv package is not installed."
- `player_missing_libmpv_linux` "libmpv is not installed. Install it with: {cmd}"
- `player_missing_libmpv_win` "libmpv is not installed. Run setup_windows.bat (Repair) or
  install it now."
- `player_libmpv_too_old` "The installed libmpv ({version}) is too old: 0.34 or newer is
  needed." (the tested floor, Q13)
- `player_libmpv_load_failed` "libmpv could not be loaded ({detail}). The file may be
  damaged or blocked by the antivirus."
- `player_vulkan_missing` "libmpv needs the Vulkan runtime (vulkan-1.dll): update the
  graphics driver or install the player again."
- `player_probe_crashed` "libmpv crashed while loading: the player stays disabled. See the
  log."
- `player_install_btn` "Install player"
- `player_install_confirm` "Download and install the video player components (about
  {size} MB)?"
- `player_installing` "Installing the player..."
- `player_install_ok` "Player installed."
- `player_install_failed` "Player installation failed: see the log."
- `player_credits` "Video playback: mpv (libmpv), {license}"
- `player_license_system` "system library"
- `player_badge_ok` "Player ready (mpv {version})" (badge tooltip for the reason `ok`)
- `player_restart_required` "Restart the application to finish enabling the player."

Live, P4-P6 (67):
- Entry points and controls:
  - `player_btn_live` "Translate in real time"
  - `btn_live_url` "Watch live"
  - `live_btn_stop` "Stop translation"
  - `live_mode_delayed` "Delayed video (in sync)"
  - `live_mode_live` "Live video (translation lags)"
  - `live_tip_mode` "Delayed video waits a few seconds so subtitles and voice match the
    speaker. Live video shows the picture at once and the translation arrives later."
  - `live_label_delay` "Delay: {s} s"
  - `live_label_engine` "Translation"
  - `live_engine_marian` "MarianMT (offline, recommended)"
  - `live_engine_ollama` "Ollama (local AI, better quality)"
  - `live_engine_google` "Google (online, rate limited)"
  - `live_engine_deepl` "DeepL Free (online, monthly quota)"
  - `live_tip_privacy` "Speech recognition runs on this computer. The dubbed voice
    (Edge-TTS) and the Google and DeepL engines send text to online services."
- Status:
  - `live_status_starting` "Starting..."
  - `live_status_loading_models` "Loading speech and translation models..."
  - `live_status_connecting` "Connecting to the stream..."
  - `live_status_detecting` "Detecting the spoken language..."
  - `live_status_buffering` "Buffering: {s} of {total} s"
  - `live_status_waiting` "Waiting for the translation..."
  - `live_status_running` "Translating in real time"
  - `live_status_lag` "Translation {s} s behind"
  - `live_status_reconnecting` "Connection lost, reconnecting ({n})..."
  - `live_status_stopping` "Stopping..."
  - `live_status_ended` "The stream has ended"
  - `live_status_stopped` "Stopped"
  - `live_status_failed` "Stopped because of an error"
  - `live_status_time_limit` "Stopped: a live session can last at most 12 hours."
  - `live_behind_live` "{s} s behind live"
  - `live_badge` "LIVE"
- Warnings (banner):
  - `live_warn_online_engine` "{engine} is an online service with request limits: long
    sessions can be blocked. MarianMT works offline."
  - `live_warn_rate_limited` "{engine} is limiting requests: subtitles stay in the
    original language for {s} s."
  - `live_btn_switch_marian` "Switch to MarianMT"
  - `live_warn_quota` "{engine} quota exhausted: subtitles stay in the original language."
  - `live_warn_engine_slow` "{engine} is not responding in time: subtitles stay in the
    original language."
  - `live_warn_tts_unavailable` "The dubbed voice is temporarily unavailable: subtitles
    only."
  - `live_warn_cpu_fallback` "GPU not available: running on the CPU with a longer delay."
  - `live_warn_falling_behind` "Translation is falling behind: delay raised to {s} s."
  - `live_tip_raise_delay` "Translation is often late: a delay of {s} s is recommended."
  - `live_warn_skipped` "Speech recognition skipped {s} s to stay in sync."
  - `live_info_marian_pivot` "No direct offline model for {src} to {tgt}: translating
    through English."
  - `live_tip_banner_close` "Close this message"
- Errors and confirmations:
  - `live_err_resolve` "Cannot open this stream: {detail}"
  - `live_err_upcoming` "This live stream has not started yet."
  - `live_err_codec` "This stream uses a format that real-time mode cannot read. Use
    Download instead."
  - `live_err_ingest` "The stream stopped and could not be resumed."
  - `live_err_asr` "Speech recognition could not start: {detail}"
  - `live_err_deps` "Real-time translation needs these components: {items}"
  - `live_err_marian_pair` "No offline model for {src} to {tgt}. Choose Ollama or an
    online engine."
  - `live_confirm_download_pair` "The offline model {name} (about {size} MB) is not on
    this computer. Download it now?"
  - `live_err_ollama` "Ollama is not reachable. Start it or choose another engine."
  - `live_err_deepl_key` "DeepL needs an API key."
  - `live_err_disk` "Not enough free disk space for the stream buffer (at least {gb} GB)."
  - `live_err_busy` "A dubbing job is running: wait for it to finish before starting
    real-time translation."
  - `live_err_busy_job` "Real-time translation is running: stop it before starting a job."
  - `live_err_busy_install` "An installation is running: wait for it to finish."
  - `live_err_editor_open` "Close the subtitle editor before starting real-time
    translation."
  - `live_err_need_source_lang` "The spoken language could not be detected: choose the
    source language and start again."
  - `live_tip_need_source` "Select a local video in the Input list first."
  - `live_tip_player_not_ready` "The player is not ready yet."
  - `live_err_no_url` "Enter a URL in the Input box first."
  - `live_err_internal` "Real-time translation stopped because of an internal error: see
    the log."
  - `live_confirm_stop` "Real-time translation is running. Stop it?"
- Component installs (live dependencies through `ComponentInstaller`, [CC] G4):
  - `live_btn_install_deps` "Install components"
  - `deps_install_confirm` "Install {items} now? This needs an internet connection."
  - `deps_installing` "Installing {items}..."
  - `deps_install_ok` "{items} installed."
  - `deps_install_failed` "Installing {items} failed: see the log."

Total: 122 keys x 26 languages (the draft's 104 plus 18 from the critiques). Dialog
titles reuse `msg_error_t` and `msg_confirm`; no new title key.

---

## 3 Data flow for files

### 3.1 Layout, lifecycle and options

Layout (P0, recommended by [01] 1.2). Today the player frame sits inside the scrolling
form canvas (video_translator_gui.py:6966-7012): its height follows the right column and
it scrolls away. The new root grid:
- row 0: header (fixed);
- row 1: body.
  - Column 0 is the player pane (weight 1, sticky nsew). It fills the window height.
  - Column 1 is a canvas plus scrollbar that scrolls only the 460 px card column.
- row 2: log;
- row 3: progress.

`_canvas_content_fits` (:7101) and the wheel binding (`_bind_mousewheel`, :7151) move to
the right canvas. The player pane is outside the canvas, so the wheel over the video is
free.

Fullscreen:
- `grid_remove()` hides rows 0, 2, 3 and column 1;
- the root gets `attributes("-fullscreen", True)`;
- the host frame is never unmapped and never reparented. mpv's own `fullscreen` does
  nothing when `wid` is used ([04] 11).

Lifecycle:
1. Startup: the panel shows the idle placeholder. A daemon thread runs
   `libmpv_runtime.quick_presence()` and posts the result with `after(0, ...)`, which sets
   the header badge and the placeholder mode. `quick_presence` loads no library: it checks
   file existence on Windows; on Linux it runs `ldconfig -p` once and parses the
   `libmpv.so.N => /path` line (`find_library` alone gives only a soname, [CC] G10).
2. First need (a file selected, a job result, a live start): `_ensure_player()` on Tk.
   - Tk side: `update_idletasks()`, `wid = panel.host_wid()`, controller state
     `initializing`; on Linux with `tk windowingsystem == "x11"`,
     `X11ErrorGuard.capture()` (once per app run, before any VO exists); then start
     `player-init`.
   - `player-init` step (a): if `player_probe.fingerprint` equals the library's current
     fingerprint and `ok` is true, skip the probe; otherwise run `probe_in_subprocess()`.
     A crash or a failed check ends with `PlayerUnavailable`, and the probe result
     (including `mpv_version` and `vo_profiles_ok`) is cached. A version below
     `TESTED_FLOOR` gives `libmpv-too-old`.
   - Step (b): `load_mpv()`. On Windows, `prepare_import` prepends the runtime dir during
     the import and restores it afterwards. A `pip --user` install made in this session
     is importable because `ComponentInstaller` ran `refresh_import_paths`; if the import
     still fails, the status is `restart-required` ([CC] G3).
   - Step (c): nothing to do for the locale: python-mpv itself sets `LC_NUMERIC=C` at
     import on non-Windows systems (mpv.py:62-68, [CT] 3), and no locale-sensitive call
     exists in the code base (grep).
   - Step (d): `create_video_backend(...)` with `player_vo_profile`, or the first profile
     of `vo_profiles_ok`. Because every profile was accepted by the probe, `MPV()` cannot
     raise the option error that leaks a half-created core ([CT] finding 2). It observes
     `EventBridge.LATEST`, registers `file-loaded`, `end-file` with its reason,
     `playback-restart`, and `log-message` at warn and above. It registers the mouse
     bindings `MBTN_LEFT`, `MBTN_LEFT_DBL`, `WHEEL_UP` and `WHEEL_DOWN` through python-mpv
     `register_key_binding`, which posts raw `(name, state)` pairs that Tk maps with
     `mouse_action`. That call uses `define-section` underneath: documented as deprecated
     "except for mpv-internal uses" in 0.34, 0.35, 0.41 and master, and RUN-confirmed on
     0.41 with keypress injection and real X11 clicks under Xvfb, with no deprecation
     warning at loglevel v ([CT] C4). The adapter is the single place to switch to
     `keybind` + `script-message` if a later mpv removes it.
   - Step (e): `after(0, self._on_player_ready, backend_or_status)`. Tk then calls
     `controller.attach_backend(backend)`, which replays the last pending load, saves
     `player_probe`, and starts the poll.
3. VO fallback chain ([sync] graft, corrected by [CT] findings 2 and 5).
   - Failure is detected by `detect_vo_failure`: a log line "Failed initializing any
     suitable GPU context" or "Error opening/initializing the selected video_out" (both
     strings confirmed in 0.41 and in the Windows DLL, [CT] C49), or no `video-params`
     5 s after `file-loaded` while `track-list` has a video track. After such a failure
     mpv keeps playing audio only.
   - Linux first: `X11ErrorGuard.restore()` runs on Tk as soon as the failure is detected,
     because the failed VO's uninit has just left Xlib's exiting default handler in place
     ([CT] finding 5). The exposure window is at most one poll (50 ms).
   - Then, ONLY IF spike S1 proved that `restore()` protects the process (the "S1-X"
     criterion in 9), `player-init` terminates the instance on its own thread, calls
     `restore()` again right after `terminate()` returns, recreates the instance with
     `next_vo_profile(..., accepted=vo_profiles_ok)`, reloads the item, and posts
     `player_vo_fallback_used`. On success the working profile is persisted in
     `player_vo_profile`. At most 2 re-creations per app run ([04] 5.2 rule 6).
   - If S1-X fails, no in-process re-creation happens on Linux: the instance is
     terminated on `player-init` (so mpv cannot retry a VO init at the next load and
     reset the handler again), `restore()` runs, the next accepted profile is persisted,
     the placeholder shows `player_restart_required`, and the new profile is used at the
     next app start. Windows has no X error handler issue and always re-creates
     in-process.
   - Linux chain: `x11egl` (default: Tk is X11-only and runs on XWayland; without it mpv
     opens a separate Wayland window, [04] 4.2), then `x11vk` (`gpu_api=vulkan`,
     `gpu_context=x11vk`), then `x11sw` (`vo=x11`, software). `x11glx` is gone:
     `gpu_context=x11` is rejected by the Kali 0.41 build and `gl-x11` is disabled by
     default in mpv's meson options since at least 0.35.1 ([CT] R1). Contexts compiled in
     the Kali build: auto, waylandvk, x11vk, wayland, x11egl, drm, displayvk ([CT] RUN).
   - Windows chain: `auto` (d3d11 first), then `d3d11-warp` (`gpu_api=d3d11`,
     `d3d11_warp=yes`: software rendering for VMs without 3D; UNVERIFIED with `wid`, S4).
     The Linux build rejects both options ([CT] C7 RUN), so `build_mpv_options` emits them
     only for win32.
   - When the chain is exhausted: `player_err_video_output`.
4. Steady state: the poll loop of 2.3.
5. X error handler, steady state: while a VO is alive, mpv's handler is installed: it logs
   X errors and returns 0 (non-fatal), and Tk's per-request handlers
   (`Tk_CreateErrorHandler`) do not run ([CT] C6 RUN: handler pointer = mpv's while the VO
   lives). Tk code that relies on its own handler to detect an expected error could
   misbehave in that state; no such path is known in this app (UNVERIFIED, residual risk
   in 11). `force_window=yes` keeps one VO for the whole run, so the displacement happens
   once and the exiting default can only appear at a VO failure or at terminate, both
   followed by `restore()`.

`build_mpv_options` (pure, unit-tested per platform, kind and profile):

| Kind | Options |
|---|---|
| video, all | `wid`, `vo=gpu`, `hwdec=auto-safe`, `keep_open=yes`, `idle=yes`, `force_window=yes` (VO created once, no flash between files; it does NOT keep Tk's X error handler, see step 5), `osc=no`, `osd_level=0` (the live `osd-overlay` still renders at level 0, [CT] C40 RUN), `input_default_bindings=no`, `input_vo_keyboard=no`, `load_scripts=no`, `config=no`, `ytdl=no`, `sub_auto=no`, `audio_file_auto=no`, `terminal=no`, `audio_buffer=0.2` (a MINIMUM: the device may use a larger buffer, mpv 0.41 man; the lead and duck latencies are therefore measured, not derived), `loglevel=warn`, `log_handler`. All accepted by 0.41 ([CT] 3 RUN). |
| video, Linux | `x11egl`: `gpu_context=x11egl`; `x11vk`: `gpu_api=vulkan`, `gpu_context=x11vk`; `x11sw`: `vo=x11` |
| video, Windows | `wid = winfo_id() & 0xFFFFFFFF` (mpv 0.41 man `--wid`: cast to uint32 on win32, [CT] 3); `d3d11-warp` adds `gpu_api=d3d11`, `d3d11_warp=yes`; `d3d11_flip=no` only if S4 shows that the flip model paints over the placeholder sibling |
| voice | `vid=no`, `force_window=no`, `idle=yes`, `keep_open=no`, `ytdl=no`, `load_scripts=no`, `config=no`, `terminal=no`, `cache=no`, `audio_buffer=0.2`; per clip the `start` property is set to the clip's leading silence before `loadfile` |
| stream session (set by mpv-cmd as properties before `loadfile`, restored at the next file load) | `rebase_start_time=no`, `cache=yes`, `force_seekable=yes` (seeking a live source fails without it, [04] 13.4 RUN; forward cache seeks on `vtlive` confirmed, [CT] C16 RUN), `demuxer_max_bytes=256MiB`, `demuxer_max_back_bytes=32MiB`, `cache_pause=yes`, `cache_pause_wait=1` |
| file session (live on a local file) | none; only the duck filter (4.13) |

Headless tests and Xvfb GUI checks use the `x11sw` profile.

### 3.2 F1 Preview

`<<ListboxSelect>>` calls `_on_input_select`:
- An empty `curselection()` is ignored. With `exportselection=False` the listbox no longer
  loses its selection to other widgets ([01] 4).
- While a live session runs or the editor is open, the selection is ignored: the session
  or the editor owns the player.
- Otherwise the handler calls `controller.set_playlist([MediaItem(p, "source",
  Path(p).name) for p in self._batch_files], index=i)`, then `load(item, paused=True)`.

The load is enqueued on `mpv-cmd` as `pause=yes`, then `loadfile <path> replace`, with the
coalesce key `loadfile`: rapid re-selection keeps only the latest request.
- On `file-loaded`, the event thread posts `track-list`.
- The controller computes `(dubbed_id, original_id)` with `pick_audio_track_ids`, adds the
  subtitles when `item.srt_path` exists, and applies the persisted audio preference.
- The placeholder is lowered when `video-params` is observed, not on `file-loaded`, so the
  logo never gives way to a black frame.

Removal ([CC] G20): `_remove_file` and `_clear_files` (:7923, :7928) call
`controller.remove_items(removed_paths)` before `_sync_player_playlist()`. If the loaded
item is kind "source" and among them, the player stops and the placeholder is lifted; a
loaded result (kind "dubbed") is unaffected. With a live file session on the removed item,
the removal first asks `live_confirm_stop`.

Transport:
- previous/next: playlist neighbours;
- back/forward: `seek_relative(-10/+10)` with keyframes (the same step as the Left/Right
  keys);
- stop: `backend.stop()`, then the placeholder is lifted;
- play/pause: toggles `pause`;
- volume slider: `mixer.set_user_volume`, then `backend.apply_mix()`, plus a debounced
  save;
- mute: toggles, and applies to both instances.

### 3.3 F2 Auto-load the result

```python
@dataclass(frozen=True)
class JobOutput:                        # videotranslator/jobs.py
    source_path: str | None             # None when the source was a deleted temp download
    output_path: str
    srt_path: str | None
    has_original_track: bool            # keep_original_audio was on for this job
def job_output_from_result(result: dict, *, source_path: str | None,
                           has_original_track: bool) -> JobOutput | None
    # uses TranslationJobResult.output_path (jobs.py:62-68) and result.get("srt")
```

Where the outputs come from:
- `_run_batch.run_all` (:8185): one `JobOutput` per successful file (`source_path=p`).
- `_dispatch_download.run` (:7831): the URL job. The temp source is deleted in `finally`,
  so `source_path=None`.
- `_run_with_segments.do` (:8153): keeps the result it discards today ([01] 5.2).
  `source_path=None` when `cleanup_path` is set.

Each worker posts `self.after(0, self._on_job_outputs, outputs)` immediately before its
existing `self.after(0, self._on_done, ...)`:
- `after(0)` callbacks run in FIFO order, so the player loads before the modal dialog;
- `_on_done` (:8356) keeps its signature, because `tests/test_ui_worker_outcomes.py:177,183`
  and `tests/test_ui_translation_warnings.py:49-74` assert its positional arguments;
- `_fake_app()` (:36-52) gains `_on_job_outputs=mock.Mock()`, and new tests assert the
  outputs passed.

`_on_job_outputs(outputs)` returns early when:
- `player_autoload_result` is off;
- there are no outputs;
- the player is unavailable;
- a live session runs.

Otherwise it calls `set_playlist([MediaItem(o.output_path, "dubbed", name,
source_path=o.source_path, srt_path=o.srt_path) ...], index=0)` and
`load(paused=True)`. If the player is still initializing, the controller keeps the request
and replays it on `attach_backend`.

### 3.4 F3 A/B original and dubbed

Today the output contains only the dubbed audio:
- `mux_video` maps `0:v:0` and `1:a:0` (`videotranslator/output_media.py:70-101`);
- URL jobs delete their source;
- the lip-sync branch replaces the output with Wav2Lip's file, whose audio is the
  vocals-only track (VERIFIED, see the preamble).

Pipeline change (Q3; small but shared code, so the coder gets exact diffs):
```python
def mux_video(video_input, audio_track, output_path, *, original_audio_input: str | None = None,
              run_ffmpeg=run_ffmpeg, log=print) -> None
# original_audio_input is None -> today's command, unchanged (existing tests keep meaning)
# else: ffmpeg -y -i <video_input> -i <audio_track> [-i <original_audio_input>]
#   -map 0:v:0 -map 1:a:0 -map <0|2>:a:0?        (0 when original == video_input)
#   -c:v copy -c:a:0 aac -b:a:0 192k -c:a:1 aac -b:a:1 160k
#   -disposition:a:0 default -disposition:a:1 0
#   -metadata:s:a:0 title=Dubbed -metadata:s:a:1 title=Original <output>
```
- Non lip-sync path (`pipeline_runner.py:479`): `mux_video(video_in, track, output,
  original_audio_input=video_in if keep_original_audio else None)`.
- Lip-sync path (`pipeline_runner.py:510-511`): replace `shutil.move(synced, output)` with
  `mux_video(synced, track, output, original_audio_input=video_in if keep_original_audio
  else None)`.
  - The output then carries the full dubbed mix (voice plus background) instead of
    Wav2Lip's vocals-only audio. This fixes the lost background music, but it is a
    behaviour change, so it is part of Q3.
  - If the operator keeps vocals-only lip-sync audio, the call passes `track_vocals`
    instead of `track`.
  - Either way the lip-sync output gets both tracks.
  - The URL temp source still exists here: it is deleted only after `translate_video`
    returns (video_translator_gui.py `_dispatch_download.run` `finally`).
- The `?` makes the original mapping a no-op for silent sources.
- The original is always re-encoded to AAC: stream-copying Opus or Vorbis into mp4 is
  UNVERIFIED ([02] 9). Cost: 30 minutes of stereo 48 kHz to AAC 160k took 27 s with the
  native encoder on this i7-10700K ([CT] C42 RUN); slower CPUs UNVERIFIED.
- The titles "Dubbed" and "Original" are file metadata ids read by `pick_audio_track_ids`.
  They are not UI text.

Player:
- 2 audio tracks: pick by title, then by order.
- 1 audio track and `item.source_path` exists: `audio-add <source> auto Original` after
  `file-loaded` ([04] 7: a video file is accepted as an audio source; the path is one
  array element, so no comma escaping is needed).
- Otherwise `ab_available=False`: the toggle is disabled with the tooltip
  `player_tip_ab_unavailable`.
- Switching sets `aid` on `mpv-cmd`. The position is kept ([04] 7 RUN: 6.52 s, then 7.04 s
  half a second later, no jump back). An audible gap is UNVERIFIED (headless run).

Known limit: the dubbed track is normalised to -23 LUFS and the original is not ([02] 9).
A loudness jump on switch is accepted in v1.

### 3.5 F4 Subtitles and editor seek

- Result: `sub-add <srt> select Translated`. Visibility comes from `player_subs_visible`
  and toggles `sub-visibility`, not `sid`, so re-enabling is instant. `sub_auto=no`
  prevents a stale SRT next to the file from being picked up. When there is no SRT (the
  "no subtitles" option), the toggle is disabled.
- Editor phase (`_open_editor`, :8109):
  - `_ensure_player()`;
  - load the source (`video_path`; for URLs the temp `stable` file) as
    `MediaItem(kind="source", temp=cleanup_path is not None)`;
  - `controller.show_segments_as_subtitles(segments, <cache>/editor_preview.srt)`. The file
    is written by a new pure `output_media.segments_to_srt()`, the text formatter extracted
    from `save_subtitles` (output_media.py:21-39), which then calls it.
- `SubtitleEditor(parent, segments, on_confirm, ui_s=None, on_seek=None, on_change=None)`
  (:5315):
  - `<<TreeviewSelect>>` gives an `iid`, then `float(self.segments[int(iid)]["start"])`,
    then `on_seek(t)`, then `controller.seek(t)` (exact; the player stays paused if
    paused);
  - iids are the original indexes (`_populate`), so the filter checkbox does not break the
    mapping ([01] 6);
  - a double click also emits a select first, which is harmless;
  - after `_on_edit` commits a change, `on_change(self.segments)` is debounced 500 ms (a
    Tk `after` whose id is kept), then the preview SRT is rewritten and `sub-reload` sent;
  - the defaults None keep every existing caller and test unchanged.
- Placement ([CC] G29): `_open_editor` makes the editor `transient(self)` and computes
  its geometry with a pure helper `player_core.editor_geometry(right_x, right_w,
  main_x, main_y, main_h, screen_w, screen_h)`: width `min(900, max(right_w, 520),
  screen_w - 40)`, x anchored at the right column (`self._right_pane.winfo_rootx()`) but
  clamped to `[0, screen_w - width]`, height `min(main_h, screen_h - 80)`. At the default
  1100 px window the editor then covers the right column and part of the video; the user
  can move it. Some Linux window managers may ignore the position (UNVERIFIED, C44), and
  multi-monitor offsets use the screen of the main window (`winfo_screenwidth`), which on
  X11 is the whole virtual screen (UNVERIFIED on the portrait second monitor, P3 manual).
- Confirm: the confirmed segments start phase 2, whose output then auto-loads through F2.

### 3.6 File lifecycle and Windows locks

`_release_player_then(dispatch)` runs in `_start` and `_start_download` before dispatch
([sync] graft):
1. `controller.release_for_job()` stops playback when the current item is kind "dubbed". A
   re-run may `ffmpeg -y` over it, or Wav2Lip's re-mux may write it. Sources stay loaded,
   because they are only read.
2. If a stop was issued, Tk polls with `after(50)` until the bridge shows
   `idle-active=True`, for at most 2 s, then calls `dispatch()`. This is never a blocking
   wait. Releasing makes the exact mpv share mode on Windows a moot question. For regular
   files the rule is sound: the file descriptor closes 2-7 ms after `stop`, before
   `idle-active` is observed ([CT] C41 RUN on Linux; Windows in S4).
3. Before the app deletes a file the player may hold (editor cancel, `_cleanup_editor_tempfile`
   :8098; phase 2 start with `cleanup_path`), it calls `controller.release(path)`, which
   has the same bounded wait.
4. At live stop, the video player `stop` comes before `store.remove()`, and the removal
   waits for the `MpvStreamAdapter.closed` Event, not for `idle-active`: for `vtlive://`
   the close callback arrives about 106 ms AFTER `idle-active` ([CT] finding 7) (4.15).
5. The player never opens files for writing; snapshots always get new names.

### 3.7 Snapshot, open folder, playlist, keys, mouse

- Snapshot: `controller.snapshot(default_videos_dir(), datetime.now())` issues
  `screenshot-to-file <path> video` through `command_async` on `mpv-cmd`. It works with
  `vo=null` ([04] 6 RUN). The reply comes back through the bridge and `panel.notify`
  shows `player_snapshot_saved` or `player_snapshot_failed`. Also enabled in stream
  sessions (the frame on screen is saved).
- Open folder: `platforms.reveal_in_file_manager(path, *, sys_platform, popen)`.
  - Windows ([CC] G18): the command line STRING `explorer /select,"<path>"`, passed to
    `Popen` without `shell=True`. A list argument would make `subprocess.list2cmdline`
    quote the whole `/select,<path>` token when the path has spaces, and explorer parses
    its own command line; `"` cannot occur in a Windows path. Return codes are ignored
    (their semantics are UNVERIFIED, C45). If `Popen` raises, `os.startfile(parent_dir)`.
  - Linux: `["xdg-open", parent_dir]` (the file is not selected, an accepted asymmetry);
    when `xdg-open` is missing (minimal systems) the button is disabled with the tooltip
    unchanged and the log names the folder.
  - stdin/stdout/stderr go to DEVNULL, with `no_window_kwargs` on Windows. Fire and
    forget; not registered.
  - Disabled for stream sessions (no file behind `vtlive://`, [CC] G21).
- Playlist: a small transient Toplevel with two groups from `playlist_groups` (Input
  files, Results). Double click or Return loads an item; the popup closes on focus out
  and on Escape. While a job runs, the Results group is disabled with the tooltip
  `player_tip_results_busy`, because the re-run may be overwriting one of them
  ([CC] G19).
- Keyboard ([CC] G5, G6): `App.bind("<Key>", self._on_player_key, add="+")` on the main
  toplevel. The editor and settings Toplevels do not get it.
  - `_on_player_key` computes `focus_in_player` (the focus widget's path starts with the
    panel's path) and calls `handles_player_key(focus.winfo_class(), keysym,
    focus_in_player=...)`; only then does it run `PLAYER_KEYS[keysym]`.
  - Keys: space play/pause, Left/Right 10 s (the same step as the buttons), Up/Down
    volume 5, `m` mute, `f` fullscreen, Escape exits fullscreen, `s` snapshot, `o` open
    folder, `n` next, `p` previous. Every action therefore has a key, including those
    hidden by the reflow.
  - Focus lands in the player pane when the user clicks the video (see mouse) or Tabs
    into the controls. It leaves when the user clicks an entry, a list or a combobox, or
    Tabs out; a mouse click on a plain Tk button does not take focus (Tk default), so
    space then still acts on the player and never also on that button. Typing in the URL
    box or pressing space on a Tab-focused Start button never reaches the player.
- Mouse over the video goes to mpv's child window ([CT] C1 RUN: child window
  `("x11" "mpv")` inside the Tk frame). python-mpv delivers two callbacks per click
  (`dm-`, then `um-`), and a double click delivers two clicks and then `MBTN_LEFT_DBL`
  (`p--`) ([CT] finding 14 RUN). `mouse_action` acts on one state only: click (on `u`)
  toggles pause, double click toggles fullscreen (so pause toggles twice, net unchanged,
  as in VLC), a wheel notch (on `p`/`d`) changes the volume by 5. After each mapped event
  Tk calls `video_host.focus_set()` ([CC] G17; whether the mpv child can hold keyboard
  focus is UNVERIFIED on Windows, S4).

---

## 4 Data flow for live mode

### 4.1 Overview

```
 URL --> IngestWorker (yt-dlp download=False; ffmpeg -c copy -f mpegts pipe:1)
              |  (IngestPolicy: stall, restart, re-resolve; VOD backpressure; disk floor)
              v
          LiveStore (32 MiB chunk files, absolute offsets, reader low-water retention)
           |                                   |
   player_uri() -> video mpv              TailReader
   (vtlive:// raw ctypes, primary;        |
    lavf follow                           |
    or HLS EVENT per spike S2)            |
                                          v
 local file ------------------------> AudioDecoder (PyAV, 16 kHz mono, per-frame PTS)
 (video mpv keeps playing it)             |  edge.observe(), SeekIndex.add()     [live-decode]
                                          v
                               StreamingVad -> UtteranceSegmenter                [live-decode]
                                          v   (utt_q 8: streams never block)
                               PersistentWhisper -> filter -> LanguageLock
                               -> SentenceAssembler                              [live-asr]
                                          v   (mt_q 64)
                               LiveTranslator (Marian | Ollama | Google | DeepL)
                               + CircuitBreaker                                  [live-mt]
                                          v   (sched_in 256)
 PlaybackClock(time-pos) ---> DubScheduler (50 Hz) + DelayController/FilePacer (1 Hz)
                                          |  RequestTts -> EdgeClipSynth         [live-tts]
                                          v                                      [live-sched]
       video mpv: osd-overlay subtitles, af-command duck, speed, pause, forward seeks
       voice mpv: preload clip paused, unpause at the slot, speed, stop
```

### 4.2 Entry points and start

Two explicit entry points ([mvp] graft; fixes F8):
- File: the player button "Translate in real time" (`player_btn_live`, row A) starts a
  session on the loaded item. It is enabled only when the item is kind "source" (a local
  file), the player is ready and `_live_blocked_reason()` is None; when disabled, its
  tooltip is that reason's key (`live_tip_need_source`, `live_tip_player_not_ready`,
  `live_err_busy`, `live_err_busy_install`, `live_err_editor_open`). The session starts
  at the current playhead.
- URL: the Input card button "Watch live" (`btn_live_url`, next to Download) starts a
  session on the first line of the URL box (`_get_urls()[0]`, :7783). If the box holds
  several URLs, the first is used and the log says so.

Start, on Tk (`_start_live_file` / `_start_live_url`):
1. Guards, in `_live_blocked_reason()` (the first failure shows its key and stops):
   - `self._editor_open` gives `live_err_editor_open`: `_open_editor` sets
     `self._running = False` while the editor is open (video_translator_gui.py:8113), so
     `_running` alone would let a session take over the editor's player ([CC] G1);
   - `self._installing` gives `live_err_busy_install` (a pip or player install is running;
     `_install_deps` sets `_running` too, :5945, which would otherwise read as a job);
   - `self._running` gives `live_err_busy` (Q4);
   - empty URL box gives `live_err_no_url`;
   - player unavailable: the placeholder states the reason;
   - missing modules (`find_spec` of `av`, `faster_whisper`, `onnxruntime`; `edge_tts` when
     the dub is on; `transformers` + `sentencepiece` for Marian) give `live_err_deps` with
     module names, in a dialog whose "Install components" action
     (`live_btn_install_deps`) asks `deps_install_confirm` and runs `ComponentInstaller`
     with the pip names (`av`, `faster-whisper`, `onnxruntime`, `edge-tts`,
     `transformers`, `sentencepiece`) and no system plan. The Italian-only
     `_check_optional_deps` popup is never used for this ([CC] G4). After `on_done` the
     user starts again;
   - URL sessions: free disk below `live_buffer_max_mb + 512 MB` gives `live_err_disk`;
   - DeepL without a key gives `live_err_deepl_key`.
2. Engine pre-flight on a worker, with the result back through `after(0)`:
   - Marian: `marian_route(src, tgt, hub_has=..., is_cached=...)` (4.9). No route gives
     `live_err_marian_pair`. A route that is not fully cached asks
     `live_confirm_download_pair {name} {size}` with every leg's name and the summed size
     (about 300 MB per direct model and 460 MB per `tc-big` model where measured, [CT]
     C39: 298-343 MB for opus-mt pairs, 464 MB for `opus-mt-tc-big-en-it`); No aborts. A
     pivot route also shows `live_info_marian_pivot` in the banner. With source "auto",
     the route and the question come after the language lock, and captions show the
     source text until then.
   - Ollama: the existing `_ensure_ollama_ready_async` (:7569).
   - Selecting Google or DeepL shows `live_warn_online_engine` in the banner (non-modal)
     and again at session start.
3. `_snapshot_live_config()` on Tk reads:
   - the source and target language and the voice from the Translation card (the voice
     is `self._voice` if it belongs to the target language, else
     `LANGUAGES[tgt]["voices"][0]`, video_translator_gui.py:41);
   - the live settings;
   - the hotwords;
   - the Ollama and DeepL settings.
   It then calls `build_live_config` (pure).
4. `_ensure_player()`. With the dub on, the voice backend is created lazily, once per app
   lifetime ([04] 5.2 rule 6).
5. `LiveSession(...).start()` returns at once. `live_active=True`. Start and Download are
   disabled, and the close prompt uses `live_confirm_stop`.

### 4.3 Time domains (one per session, [sync] graft; fixes F15)

- File sessions use the rebased player timeline.
  - The player: mpv `time-pos` with the default `rebase-start-time=yes`. mpv takes the
    start from `avfc->start_time` (demux_lavf.c:1138-1139 at v0.41.0; the draft's
    :1604-1605 cite was wrong, [CT] C18), the same lavf field PyAV exposes as
    `container.start_time`.
  - The decoder: `frame.pts * frame.time_base - (container.start_time or 0) /
    av.time_base`. `container.start_time` is an int in MICROSECONDS (RUN: 1001378667 for
    a TS starting at 1001.38 s, [CT] finding 13).
  - [CT] C18 RUN on a TS with a 1001.38 s start: mpv's rebased `time-pos` at load was
    0.0213 and the decoder's first audio time 0.0. The 21 ms is the audio/video start
    offset of that file, not a domain offset.
  - This is the domain of pipeline segments and the editor, and the file is not reloaded
    when a session starts.
- URL sessions use raw MPEG-TS PTS.
  - The player: `rebase-start-time=no`, so `time-pos` IS the raw PTS ([04] 13.5 RUN on
    HLS; [CT] C17 RUN on the same TS bytes: mpv first video PTS 1001.400, PyAV first audio
    PTS 1001.379, the same 21 ms A/V start offset, systematic and inside 50 ms).
  - The decoder: raw `frame.pts * time_base` ([05] 1.4 RUN).
  - `demuxer-cache-time` is in the same domain ([04] 13.4 RUN; [CT] C19 RUN on the custom
    stream: 1003.80 .. 1010.92, advancing with the writer).
  - The UI displays `t - first_pts`.
- Validity ([CT] finding 6): while a seek or a load is pending, mpv reports `time-pos`
  clamped to `[0, duration]` (playloop.c:553-561). RUN on the custom stream: a forward
  cache seek to 1007.52 first reported 7.14 (the duration) for 140 ms, then 1007.56; at
  load it reported 0.0 before 1001.44. `PlaybackClock` therefore ignores values while
  `seeking` is true, between our load/seek command and the next `playback-restart`
  event, and below `first_pts` in raw sessions (2.2). The scheduler sees `now=None` in
  those windows and starts nothing.
- Anchoring: every decoded frame anchors its own time ([05] 2.4). No time comes from a
  running sample count, so gaps never skew later times.
- PTS wrap after 2^33 / 90 kHz = 26.5 h ([05] 2.4): stream sessions stop at 12 h with
  `live_status_time_limit` (not `live_status_ended`, [CC] G30). A documented limit.

### 4.4 Source A: a local file played in real time

- The video mpv keeps playing the file: no reload, no option change except the duck
  filter.
- `AudioDecoder` opens the same path as a second read-only handle. It starts 0.5 s before
  the playhead and reads at most 45 s ahead of it, with stop-aware 200 ms waits. ASR, MT
  and TTS therefore work before playback reaches each sentence.
- For files the decoder may block on a full `utt_q`: the `FilePacer` pauses playback
  instead of dropping speech.
- User seek (`notify_user_seek(t)`):
  - inside the translated coverage: nothing is recomputed;
  - otherwise the generation counter increments (`gen += 1`). The decoder restarts at `t`,
    the segmenter and assembler reset, `DubScheduler.on_seek(t, gen)` runs, and every
    queued item with an older `gen` is dropped by its consumer ([mvp] graft).
- Segments are cached by `(round(start, 2), round(end, 2))`, up to 2,000 per session.
  Clips are KEPT for the whole file session (48 kbit/s is about 21 MB per hour, [mvp]
  graft), so seeking back replays them without new Edge-TTS requests.
- Pacing: `FilePacer` (5.5).

### 4.5 Source B: a URL through one ingest

Resolve (on `live-ingest`, never on Tk):
- `extract_info(url, download=False)` with `build_ytdlp_options` (input_source.py:40-73)
  minus `outtmpl` and the merge format;
- `js_runtimes` from `resolve_js_runtimes` after `ensure_js_runtime` (js_runtime.py:140,
  :205);
- `live_status` values ([02] 8): not_live, is_live, is_upcoming, was_live, post_live.
  - `is_upcoming` gives `live_err_upcoming`;
  - any exception gives `live_err_resolve {detail}` (the first line), plus the existing
    `emit_download_warnings` anti-bot advice in the log.

Format (pure; fixes F11, corrected by [CT] finding 3 and R2):
- one selector for live and VOD: `bv*[height<=H][vcodec^=avc1]+ba/b[height<=H]`,
  `H = live_max_height` (720). The draft's selectors selected NOTHING on a real YouTube
  live stream today: YouTube live exposes video-only avc1 HLS formats plus audio-only
  formats 233/234 whose `acodec` is None, so `[acodec^=mp4a]` never matches ([CT] RUN,
  yt-dlp 2026.08.19, stream 4xDzrJKXOOY). The new selector picked 232+234 there.
  yt-dlp's default `bestvideo*+bestaudio/best` picked 270+234 (1080p).
- the CHOSEN format's codecs go through `is_ts_compatible`:
  - "yes": ingest;
  - "no" (VP9, AV1, Opus, ...): `live_err_codec` before ffmpeg starts. MPEG-TS stream
    copy of those is out of v1;
  - "unknown" (yt-dlp reports None, as for 233/234, or an HLS playlist without a CODECS
    attribute): `probe_codecs` runs ffprobe on the video URL and the audio URL (with the
    resolved headers, `-rw_timeout 10000000`, a 20 s subprocess timeout, no console
    window) and re-checks; still unknown or incompatible gives `live_err_codec`
    ([CC] G9). The codec of 233/234 is UNVERIFIED (expected AAC; P6 records it).
- split video and audio inputs (the YouTube live case) are ingested with two `-i` and
  `-map 0:v:0 -map 1:a:0`. Whether the two HLS playlists stay in sync through
  `-c copy` into one TS is UNVERIFIED: spike S2 measures the A/V offset on 232+234.
  Twitch serves muxed variants (UNVERIFIED per stream).

Ingest command (pure builder, list arguments, [CT] finding 8 and R7):
```
ffmpeg -hide_banner -nostdin -loglevel warning [-user_agent UA] [-headers "K: V\r\n..."]
  -rw_timeout 15000000 [-seg_max_retry 3] [-ss <input_seek_s>]
  -i <video_url> [-rw_timeout 15000000 [-seg_max_retry 3] -i <audio_url>]
  -map 0:v:0? -map <0|1>:a:0 -c copy [-output_ts_offset <X>] -f mpegts pipe:1
```
- `-rw_timeout` is kept: the FFmpeg HLS demuxer copies `headers, user_agent, cookies,
  http_proxy, referer, rw_timeout, icy` to its segment requests (aviobuf.c:993-994,
  hls.c:2136,1409-1415 at n8.0).
- `-reconnect*` are dropped: they never reach segment fetches ([CT] C24 REFUTED), so
  they would only suggest a protection that does not exist.
- `-seg_max_retry 3` only when `ffmpeg_major_version() >= 6`: the option is absent in
  FFmpeg 5.1 (Debian 12's ffmpeg) and ffmpeg would reject the command. Input options are
  repeated per `-i` because they are per input.
- `IngestPolicy`'s own stall detection (no bytes for 15 s) stays the guard that works on
  every version.

Process:
- Popen with `stdin=DEVNULL` and binary `stdout=PIPE`;
- `stderr=PIPE`, drained by a small thread (created with the session's thread factory)
  into a 20-line ring used for the error detail and the re-resolve rules;
- `no_window_kwargs` on Windows (the pattern of ollama_runtime.py:693-703);
- registered in the `ActiveSubprocessRegistry` through injected hooks (the pattern of
  `set_subprocess_hooks`, ollama_runtime.py:20), so `_on_close` also kills it;
- the loop runs `data = stdout.read1(65536)`, then `store.append(data)`, then
  `policy.on_bytes(mono)`.

`IngestPolicy` (pure; fixes F10):
- Stall: no bytes for 15 s while running. Terminate, wait 2 s, kill, then restart.
- Exit with the stream still live: restart with backoff 1, 2, 4, 8, 16, 30, 30 ... s. At
  most 10 restarts in 10 minutes, then `live_err_ingest`. The counter resets after 5
  minutes of healthy ingest.
- Re-resolve before a restart when any of these holds:
  - the stderr tail shows 403, 404 or 410;
  - it is the second consecutive failure;
  - the resolution is older than 4 h. The YouTube live manifest URL carried
    `expire` = now + 6.00 h ([CT] C22 RUN), so 4 h leaves a 2 h margin.
- Restart continuity:
  - live: `-output_ts_offset = last_edge + 1.0`, so PTS stay monotonic across the gap.
    [CT] C20 RUN on a concatenated TS with a +2.44 s PTS gap: mpv played across it
    without stalling, but `time-pos` JUMPED by the gap (1009.36 -> 1011.80). The
    scheduler treats such a jump as a discontinuity, not a seek, because no
    `playback-restart` epoch change comes with it (4.11). Restart of a real ingest is an
    S2 item. Then `store.mark_gap()` and `edge.reset(mono)`;
  - VOD: `-ss <last_edge - first_pts>` plus the same offset.
- End: ffmpeg exits 0, then one re-resolve. `live_status` in {was_live, post_live,
  not_live}, or a VOD, means `store.finish()`. Playback drains to the edge, then the
  status is `live_status_ended`.

VOD backpressure ([sync] flaw F17). When `not is_live` and
`store.written - store.min_low_water() > 256 MiB`:
- the ingest thread stops reading, polling every 200 ms and staying stop-aware;
- ffmpeg then blocks on the full pipe, which becomes TCP backpressure;
- a server that times out the idle connection triggers the normal restart with `-ss`
  (UNVERIFIED per server, P6).
Live streams are never throttled: they cannot run ahead of real time by more than a few
segments.

Disk (fixes F9):
- the start check needs free space of at least `live_buffer_max_mb + 512 MB`;
- the ingest loop checks `store.free_bytes()` every 30 s: below 512 MB free, the session
  fails with `live_err_disk` and the store is removed;
- an `OSError` in `append` gives the same result.

### 4.6 LiveStore and the player transport

Store layout:
- append-only chunk files `<session_dir>/store/chunk_000000.ts`, ... of 32 MiB, with
  absolute byte offsets;
- the ingest writes whole 188-byte packets from offset 0.

Readers:
- they register ids ("mpv", "asr");
- each reports its low-water offset, which is its current read position.

Retention (fixes F9):
- A chunk is deleted when its end is below `min_low_water() - 16 MiB`. mpv's reader sits
  at its demuxer read position (at the edge in steady state, because the store serves
  everything up to the edge), and the ASR reader sits near the edge. So on disk the store
  holds little more than one chunk plus the margin.
- The cap `live_buffer_max_mb` only matters while a reader stands still, for example mpv
  after its forward cache filled during a long user pause. Over the cap, the oldest chunk
  is evicted anyway and the reader is clamped to `earliest`, aligned to 188. A clamped mpv
  reader triggers the reload rule (5.3).
- Chunk handles are refcounted, and an unlink is deferred until the count reaches zero.
  `PermissionError` on Windows is retried at the next append ([sync] graft).

Readers block in `read_at` on a `threading.Condition` until data arrives, the store ends,
a cancel comes, or the timeout runs out. `close()` wakes everyone with EOF.

`MpvStreamAdapter` ([CT] findings 4 and 7, R4; contract in 2.2):
- registration: `register_raw_stream_protocol(mpv, handle, "vtlive", open_adapter)` in
  `player_engine`, NOT python-mpv's `register_stream_protocol`, whose read callback
  copies one byte at a time in Python (mpv.py:1869-1870): about 8-13 MB/s, 10-16 ms per
  128 KiB read with the GIL held, 20 ms median with two busy Python threads; mpv issues
  64 KiB and 128 KiB reads ([CT] RUN). `ctypes.memmove` does the same copy in 0.003 ms;
- `open_adapter` parses `vtlive://<session_id>?offset=<n>` and returns an adapter whose
  `base_offset` is n; mpv's first `seek(0)` defines n as position 0 (stream_cb.h:111-115);
- `read(n)` blocks until data, true end, cancel or close, with NO timeout: a single
  `b""` is a permanent EOF for mpv ([CT] RUN p13: `eof-reached=True`, three retry
  reads, no resume when data arrived later) (`stream_cb.h` 92-96);
- `seek(pos)` is exact: it returns `pos`, or -1 below `earliest`; a target beyond
  `written` blocks until it is written, cancelled or closed. mpv ignores the returned
  value except its sign (stream_cb.c:29-33), so the draft's "clamp to
  [earliest, written]" would have desynced silently;
- `cancel()` is called by a non-Python libmpv thread about 0.1 s after `stop`, `loadfile`
  of another file or `terminate` ([CT] C13 RUN) and must not block (stream_cb.h:150-155):
  it sets the reader's Event and notifies the store Condition;
- `size` is never provided: python-mpv (mpv.py:1891) and our registration read it only
  at open, so the draft's "final byte count after `finish()`" (F13) was impossible
  without a reload. The end of a finished stream is signalled by `read` returning `b""`
  once `offset == written` after `finish()`;
- `close()` sets `closed`, unregisters the reader and drops the CFUNCTYPE references held
  for that stream. The stop sequence (4.15) waits on `closed`, because the close
  callback arrives about 106 ms after `idle-active` becomes true ([CT] RUN, 3 runs);
- every callback is wrapped in try/except, returns -1 (or 0 bytes only at a true end) and
  posts `stream-error` to the bridge: a Python exception must never cross the ctypes
  boundary, and no callback calls libmpv on the same instance (stream_cb.h:48-51);
- throughput budget: at 1 MB/s (about 8 Mbit/s, 1080p) the memmove path costs well
  under 1 % of wall time; a reload with D = 12 s of backlog copies 12 MB in milliseconds
  instead of 1-1.5 s.

`TailReader(io.RawIOBase)` wraps the same store for `av.open(reader, format="mpegts")`
([05] 1.4 RUN). It passes a 200 ms timeout to `read_at` and retries on None, so it stays
stop-aware.

`SeekIndex`: the decoder adds `(pts, reader.tell())` at most every 0.5 s. `offset_for(pts)`
returns the largest indexed offset at or below `pts`, minus 256 KiB, aligned to 188. It is
used only by the reload path (5.3). Accuracy is about lavf's read buffer, well under 1 s
of media.

Transport choice (spike S2 decides; fixes F6). `LiveStore.player_uri()` hides the choice
from the rest of the session. The candidates:

| Candidate | URI | Pros | Cons | Chosen if |
|---|---|---|---|---|
| B `vtlive` (default) | `vtlive://<id>?offset=<n>` | chunked store with retention; one reader class for mpv and PyAV; reload at an offset; blocking reads, paused delayed start and raw-domain seeks already RUN-confirmed on the custom stream ([CT] C13, C16, C19) | ctypes callbacks still take the GIL per read (short with memmove); relies on python-mpv internals `backend` and `handle` (2.2) | S2 passes (criteria in 9) |
| A `lavf-follow` | `lavf://file:<path>` with `stream-lavf-o=follow=1` | no Python in mpv's read path; [CT] C14 RUN on Linux: played past the initial end, sat in `paused-for-cache` at the end of a finished writer, `stop` to idle in 6 ms, `terminate` 0.107 s | single growing file: retention impossible; Windows path syntax UNVERIFIED | B fails the GIL or cancel criteria and A passes; the store then runs in single-file mode and rotates at the cap with a player reload (one short freeze per cap) |
| C `hls-event` | `<session>/hls/live.m3u8` (`-f hls -hls_playlist_type event -hls_time 2`) | only regular files; FFmpeg clears AVFMTCTX_UNSEEKABLE for EVENT playlists (n8.0 `hls.c:1098-1102`, same logic in n4.4, n5.1, n6.1, [CT] C15) | many small files; 2 s reload granularity; not run | A and B both fail |

### 4.7 Decode, VAD and segmentation (`live-decode`)

- `AudioDecoder` produces 0.25 s float32 blocks at 16 kHz mono. Each block goes to:
  - `edge.observe(block_end, mono)` (streams);
  - `SeekIndex.add`;
  - `StreamingVad.probs`: stateful ONNX Silero from the faster-whisper asset. The
    library's own wrapper resets its state on every call, hence the small wrapper ([05]
    3.4). It carries `h`, `c`, the 64-sample context and a remainder buffer; the session
    comes from `faster_whisper.vad.get_vad_model()` (vad.py:289-292) and the model file is
    `silero_vad_v6.onnx` under `faster_whisper.utils.get_assets_path()` (utils.py:39-41).
    [CT] C37 RUN: identical output to `SileroVADModel.__call__` (max abs diff 0.0 over 625
    frames), 0.047 ms per frame;
  - `UtteranceSegmenter.push`. It starts an utterance at probability 0.5 and continues
    while above 0.35. It ends after 0.4 s of silence, with 0.15 s padding. The maximum
    length is `timing.umax_s` (5.8). At the cap it cuts at the last pause of at least
    0.1 s within the last 1.5 s, else at the lowest-probability frame (`forced_cut=True`,
    no overlap in v1). A time jump over 0.25 s (a discontinuity) flushes the buffer.
- Streams never block downstream. The decoder uses `put_nowait` into `utt_q` (maxsize 8).
  On `Full`, or when `asr_lag = edge.observed - oldest_pending.start` exceeds
  `timing.umax_s + D - 3` (delayed) or 4 s (live):
  - the oldest pending utterances are dropped until the lag is back inside the bound;
  - `skipped_s` is counted;
  - `live_warn_skipped` is shown.
  The decoder therefore always reads at the edge, and the edge measurement stays correct
  ([sync] backpressure graft; also fixes [parity]'s blocking decoder, which froze the
  edge).
- Files: a blocking `put` with 200 ms stop-aware retries; the `FilePacer` handles
  lateness.

### 4.8 ASR (`live-asr`)

- `PersistentWhisper` is loaded once per session on this thread.
  - With CUDA: `large-v3-turbo` float16, beam 5 (0.14-0.22 s per utterance on the 3090,
    [05] 1.1).
  - Otherwise: `small` int8, beam 1 (1.2-1.7 s; medium and turbo fall behind on CPU).
  - kwargs come from `build_transcribe_kwargs` (transcription.py:20) with overrides:
    `vad_filter=False`, the locked `language`, `condition_on_previous_text=False`,
    `temperature=0`, and hotwords through `to_whisper_param`.
  - The batch `transcribe_audio` reloads the model on every call (transcription.py:92),
    which live mode cannot afford.
- Segment times are relative to the utterance; `utt.start` is added, which puts them in
  session time.
- `LanguageLock`:
  - an explicit source language is locked from the start;
  - "auto" locks at probability >= 0.8 with >= 5 s of speech, else a majority vote over
    the first 30 s of speech;
  - before the lock, lines are shown untranslated in italics (status
    `live_status_detecting`), and the translator is prepared after the lock;
  - the majority vote needs at least 60 % of the per-utterance detections; if no
    language has it after 60 s of speech (for example a mixed-language stream), the
    session stops
    with `live_err_need_source_lang` and the user picks the source language (the C38
    fallback, now with its own key, [CC] 4).
- `filter_hallucinations` ([sync] graft):
  - drop `no_speech_prob > 0.6 and avg_logprob < -1.0`;
  - drop `compression_ratio > 2.4`;
  - drop exact repeats of the last 2 texts;
  - lines flagged by `whisper_sanity` are subtitled but not dubbed.
- A CUDA runtime error (`is_cuda_runtime_error`):
  - close the model, reload `small` int8 on CPU once, and retry the utterance;
  - post `live_warn_cpu_fallback`;
  - raise the target delay by 3 s when `live_delay_auto` is on, else show
    `live_tip_raise_delay`.
- `SentenceAssembler`:
  - accumulates until end punctuation (`END_PUNCT_CHARS`, segments.py:7);
  - or until `hold_s` of MEDIA time passes without punctuation (delayed 1.5 s, live
    0.4 s). The hold runs on `edge(media_edge)` ticks every 0.5 s of decoded audio, so it
    is deterministic and pause-proof;
  - or until 30 words, 12 s or 300 characters;
  - multi-sentence text is split with proportional timing, as `split_on_punctuation`
    (segments.py:62) does.
- Output: `Sentence(seg_id, gen, start, end, text, flags)` into `mt_q`.

### 4.9 Translation (`live-mt`)

- The engine comes from `live_engine` (default marian). `prepare()` runs before the status
  becomes `running` (Marian: after the language lock).
  - Marian: the route from `marian_route` (below), every leg loaded once, on the GPU if
    available. Warm cost is 57-88 ms on the GPU and 178-311 ms on the CPU per sentence and
    leg ([05] 1.2), so a pivot costs about twice that. No route gives
    `live_err_marian_pair`.
  - Ollama: `_ollama_health_check` once, then a warm-up with `keep_alive: "30m"`, and
    `keep_alive: 0` at close (unload verified on this machine, [02] 5). Failure gives
    `live_err_ollama`. The prompt is `build_translation_prompt(text, slot, ...,
    prev_text=<last source>, next_text=None, global_context=None)` with thinking off, no
    CoVe and no length retries. Warm cost is 0.3-0.8 s.
  - Google and DeepL: as in 2.2.
MarianMT coverage and routes ([CT] C39 REFUTED, [CC] G8; [FD] Hub query of 2026-09-25,
HTTP 200 on `https://huggingface.co/api/models/Helsinki-NLP/<name>`):
- The draft assumed `opus-mt-{src}-{tgt}` exists for each pair. It does not: en->ja, ko,
  no, pl, pt, tr and el->en, no->en, pt->en, ro->en have no direct model; of the 25
  pairs it->X only ar, de, en, es, fr, sv, uk, vi exist, and of X->it only ar, de, en, es,
  fi, ja, uk, vi, zh.
- Every one of the 25 non-English project languages can reach English and be reached
  from English through SOME Helsinki-NLP model, so a pivot through English covers all
  26 x 25 pairs:

| Code | X -> en leg | en -> X leg |
|---|---|---|
| ar, cs, da, de, es, fi, fr, hi, hu, id, it, nl, ru, sv, uk, vi | `opus-mt-X-en` | `opus-mt-en-X` |
| zh (project `zh-CN`) | `opus-mt-zh-en` | `opus-mt-en-zh` |
| el | `opus-mt-tc-big-el-en` | `opus-mt-en-el` |
| ja | `opus-mt-ja-en` | `opus-tatoeba-en-ja` (the only one found; `opus-mt-en-jap` is a different model family, [CT] C39); loadability and quality UNVERIFIED |
| ko | `opus-mt-ko-en` | `opus-mt-tc-big-en-ko` |
| tr | `opus-mt-tr-en` | `opus-mt-tc-big-en-tr` |
| pt | `opus-mt-ROMANCE-en` (source group, no token) | `opus-mt-tc-big-en-pt` |
| ro | `opus-mt-ROMANCE-en` (source group, no token) | `opus-mt-en-ro` |
| pl | `opus-mt-pl-en` | `opus-mt-en-zlw` (target group, token for Polish) |
| no | `opus-mt-gmq-en` (source group, no token) | `opus-mt-tc-big-en-gmq` (target group, token for Bokmal) |

- Route order in `marian_route(src, tgt)`: (1) cached direct `opus-mt-{s}-{t}`; (2) cached
  `opus-mt-tc-big-{s}-{t}`; (3) the same two on the Hub (when online); (4) pivot
  `EN_LEGS[src][0]` then `EN_LEGS[tgt][1]`; (5) None. When src or tgt is `en`, the single
  `EN_LEGS` leg is the route. Project codes map to Marian codes through the existing
  helper in translation.py (read-only import, 2.1); `zh-CN` maps to `zh`.
- Target tokens: a target-group model (`en-zlw`, `tc-big-en-gmq`) needs a `>>xxx<<`
  prefix; the token is chosen at `prepare()` from `tokenizer.supported_language_codes`
  against the leg's candidates (for example `>>pol<<`, `>>nob<<`); none present gives
  `live_err_marian_pair`. Exact token strings per model are UNVERIFIED (P4 checks them).
- Sizes: `pytorch_model.bin` 298-343 MB for opus-mt pairs, 464 MB for
  `opus-mt-tc-big-en-it` ([CT] C39). A pivot needs two downloads.
- Licences: opus-mt models checked today are Apache-2.0 (`opus-mt-en-ROMANCE`,
  `opus-mt-en-mul`); `opus-mt-tc-big-en-pt` is CC-BY-4.0. Models are downloaded by the
  user's machine from the Hub, as the batch pipeline already does; the README notes
  their own licences (8.4). Nothing is redistributed by the project.
- Quality of pivot routes (two translation errors can compound) and of group models is
  UNVERIFIED; the operator decides whether pivots are enabled (Q12). With pivots off,
  pairs without a direct or `tc-big` model give `live_err_marian_pair` and suggest Ollama.

- Per sentence: `translate(text, context=<last 2 pairs>, timeout_s=TIMEOUTS_S[...])`, one
  attempt.
  - A failed `Outcome` keeps `text_src`, sets `italic=True` and
    `FLAG_TRANSLATION_FALLBACK`, and is never dubbed.
  - The engine never changes by itself.
- Breaker per engine (`live_health.CircuitBreaker`; fixes the parity RateLimitGate's
  missing half-open state):
  - 3 failures in 30 s open it;
  - a 429 counts as `rate_limited`;
  - a DeepL 456 is `quota` and opens it for the session;
  - while open, sentences skip the call and keep the source text;
  - the cooldown doubles 30, 60, 120, 300 s, and a half-open state lets one probe through.
  Opening shows `live_warn_rate_limited {engine} {s}` with the action
  `live_btn_switch_marian`, or `live_warn_quota`, or `live_warn_engine_slow` for
  Ollama/Marian timeouts.
- "Switch to MarianMT": Tk runs the Marian pre-flight (consent if the pair is not cached),
  then `session.set_engine("marian")`. `live-mt` closes the old translator and prepares
  the new one before the next sentence. `live_engine` is saved.
- Stale sentences in live mode: when `end < now - 6 s`, the translation still runs (so the
  subtitle shows) but TTS is skipped.

### 4.10 TTS (`live-tts`)

- TTS runs only when the dub is on, the outcome is ok, and the line is not flagged.
  `live-sched` sends `RequestTts` with `deadline_mono`:
  - delayed: the time the playhead reaches `slot.start - lead`, through `PlaybackClock`;
  - live: `slot.start + 4 s`.
- `EdgeClipSynth`:
  - `asyncio.Semaphore(2)` and 0.25 s minimum spacing between request starts (a new
    websocket per sentence can trigger throttling, edge-tts issue #347, [05] 5.1);
  - `Communicate(text, voice, rate=f"+{choose_rate(...)}%", connect_timeout=3,
    receive_timeout=5)` (edge-tts 7.2.8 signature, [02] 6). The timeouts are ints: a
    float raises TypeError (communicate.py:360-363), so the draft's "TypeError fallback
    without the timeouts" would have silently dropped both ([CT] C34). Whether the
    installed version accepts the keywords is decided once with
    `inspect.signature(Communicate)`; without them the whole request is bounded by
    `asyncio.wait_for` only;
  - chunks from `stream()` inside `asyncio.wait_for(..., deadline_remaining)`, written to
    `<session>/tts/clip_<gen>_<seg>.mp3.part`, then `os.replace` (mpv never sees a partial
    file);
  - duration = bytes / 6000, no probe subprocess: exact to the millisecond on it, en
    and ja clips ([CT] C34 RUN);
  - then `measure_silence` decodes the clip with PyAV and stores `voice_start_s` and
    `voice_end_s` (threshold -45 dBFS, 10 ms frames). Edge clips start with 0.16-0.21 s
    and end with 0.26-0.84 s of silence ([CT] finding 11 RUN, three voices); slot fitting,
    speed and the start time use the AUDIBLE span, and the voice instance skips the
    leading silence with its `start` property. On a decode failure the whole clip counts
    as audible;
  - `EdgeDurationModel.observe(text, rate, audible_s)` updates the per-language
    characters-per-second estimate;
  - text goes through `sanitize_for_tts` (tts_text_sanitizer.py:65);
  - one retry only when more than 3 s of the deadline remain.
- `choose_rate` uses `EdgeDurationModel`, not the XTTS table directly:
  `timing.estimate_tts_duration_s` is XTTS characters per second (timing.py:13-20,56-64)
  and against measured Edge clips it was +2 % (it), -30 % (en) and -59 % (ja) off; most of
  the en gap is trailing silence, ja stays about -33 % without it ([CT] C35 REFUTED). The
  seed is used only until the first clip of the session is measured; from then on the
  session's own rate-normalised audible durations drive the estimate (EMA, alpha 0.3). The
  playback speed clamp (1.0-1.3) absorbs the remaining error.
- Failure: the breaker opens after 3 failures in 60 s. The dub is then suspended (unduck,
  voice stopped) and `live_warn_tts_unavailable` shows. Subtitles continue, and a probe
  runs after the cooldown.
- Clips: file sessions keep every clip for the session (4.4). Stream sessions delete a
  clip once it is played or dropped.

### 4.11 Scheduling (`live-sched`)

Tick at 50 Hz (`Event.wait(0.02)`):
1. Drain the control queue (mode, delay, dub, subs, engine, user seek/pause, user volume)
   and `sched_in` (translated segments, TTS results, voice events). Drop stale `gen`
   items.
2. `now = clock_view.now(mono)` (None while the clock is invalid, 4.3) and
   `epoch = clock_view.epoch`; `main_running` and `main_speed` come from the bridge.
3. `actions = scheduler.tick(now, mono, ..., clock_epoch=epoch)` (pure), then execute
   them:
   - captions through `video.rt.set_overlay`;
   - clips through the `VoiceBackend`;
   - duck through a `DuckEnvelope`, then `video.rt.set_duck` (only when the change
     exceeds 0.02);
   - `RequestTts` through `EdgeClipSynth.submit`.
4. Every 1 s: `DelayController.step` (streams) or `FilePacer.step` (files). The resulting
   speed or pause goes through `video.rt`; a seek goes through `video.seek` (mpv-cmd); a
   reload goes through `video.load(store.player_uri(offset=...))`.
5. Every 0.25 s: publish a `LiveStatus` snapshot.
6. Every 250 ms, in fallback duck mode only: re-assert the mixer (4.13).

`DubScheduler` policy:
- Slot = `[seg.start, min(next.start, seg.end + overhang_s)]`, with `overhang_s = 0.6`.
- Captions (never dropped because the dub is late):
  - show at `max(start, arrival)` if `now < end + grace` (delayed 1.5 s, live 6 s);
  - clear at `max(end + 0.3, shown + 1.5)` or when the next caption shows;
  - paginate into at most 2 lines of 42 characters, with pages timed in proportion to
    their length ([sync] graft);
  - fallback lines render in italics.
- Voice, delayed mode (all times are media time; the target is that the dubbed voice
  becomes AUDIBLE at `seg.start`):
  - preload at `start - 1.5` when the voice player is idle and the clip is ready, with
    `skip_s = clip.voice_start_s` so the clip's leading silence is never played;
  - the duck ramp starts at `start - duck_latency_s - duck_ramp_s`, so the attenuation is
    heard complete when the voice starts. `duck_latency_s` is measured, not derived: the
    first attenuated sample came 0.19-0.39 s after the command with `ao=pcm` ([CT] C30;
    `audio-buffer` is only a minimum, the device may buffer more, mpv 0.41 man). Default
    0.4 s until S3 sets per-platform values. Ducking a little early is harmless; ducking
    late overlaps two voices;
  - `StartClip(speed)` at `start - voice_lead` with
    `speed = clamp(clip.audible_s / slot_len, 1.0, 1.3) * main_speed`. mpv keeps the pitch
    through scaletempo2 (RUN: "adding scaletempo2" at `speed=1.03` on 0.41, [CT] C32).
    The TTS speed follows the main speed, so a nudge never drifts voice from picture
    ([sync] graft);
  - a clip not started by `start - voice_lead + late_tolerance` (0.5 s) is dropped as
    `late`;
  - if a clip is still playing at the next start: remaining time up to 0.6 s makes the
    next clip wait; otherwise the current clip goes to `max_speed`, and if the wait would
    still exceed 1.0 s the clip stops with a 0.18 s fade.
- Voice, live mode:
  - FIFO: start the oldest ready clip when the voice player is idle and
    `now - start <= 4.0`;
  - `speed = clamp(1 + backlog_s / 8, 1.0, 1.3) * main_speed`;
  - older clips are dropped as `lag`.
- Unduck when the clip's audible end plus `unduck_tail_s` (0.2 s) minus `duck_latency_s`
  is reached, unless the next start is within 0.6 s (no pumping, [05] 5.4). Ramps are
  linear over 0.2 s on the 20 ms ticks: 10 steps, each at most 0.07 of gain for the
  default 1.0 -> 0.3 duck.
- Main player paused: `PauseClip`, envelope frozen. On resume the clip resumes if it is
  still inside its slot; otherwise it stops.
- Seeks and jumps ([CT] finding 6, C20):
  - an explicit seek (user seek on a file, controller seek or reload on a stream), or an
    epoch change (a `playback-restart` since the last tick) with a jump of more than
    1.0 s, triggers `on_seek`: stop the clip, unduck, clear the caption, mark unplayed
    segments after the new position `ready` again (their clips stay cached), and (files)
    restart the ASR at a new `gen`;
  - a jump of more than 1.0 s WITHOUT an epoch change is a PTS gap inside the stream (an
    ingest restart or an ad break): `on_discontinuity` drops the slots that were skipped
    as `late`, stops the current clip only if its slot has passed, and keeps the ASR;
  - raw `time-pos` values never trigger anything while the clock is invalid.
- Voice lead calibration: `voice_lead` starts at 0.25 s (`audio_buffer` 0.2 plus start
  latency). It is corrected from the requested unpause versus the first observed voice
  `audio-pts > skip_s` (monotonic stamps), as an exponential moving average over the
  first 5 clips, bounded to 0.1-0.6 s. `audio-pts` shows when mpv starts feeding the
  device, not when the sound leaves it, so the device part stays the nominal buffer
  value; S3 measures the real audible onset on a real audio output with a loopback
  recording and sets a per-platform offset. No config knob. [CT] C28 RUN (headless,
  `ao=null`): a preloaded voice reached `time-pos > 0.05` 0.146 s after unpause.
- Metrics:
  - `margin = start - voice_lead - ready_time` per dubbed segment (`RollingStats`, p90);
  - voiced, dropped, late, skipped.

### 4.12 Subtitle rendering

- Live sessions use `video.command("osd-overlay", id=1, format="ass-events", data=...,
  res_x=0, res_y=720, z=0, hidden=False)` ([04] 9 RUN form).
  - The python-mpv 1.0.8 `osd_overlay()` wrapper raises NameError (`res_Y`, mpv.py:1532,
    [CT] 3 RUN) and is never used; the direct `command(...)` form above works and
    `format="none"` removes it ([CT] 3 RUN). It renders with `osd_level=0` (1525 white
    text pixels at levels 0 and 1, [CT] C40 related RUN).
  - The text goes through `ass_escape`, which mirrors mpv's own escaping (2.2);
    (`escape-ass` exists only from 0.38).
  - Style: `{\an2\fs<px>\bord2\shad0}` with `px = round(40 * theme.scale)`; `{\i1}` marks
    fallback lines.
  - Removal: `format=none`.
  - The overlay is inside the video, so it also works in fullscreen, and it sits above
    file subtitles.
- File results use `sub-add` (3.5).
- Glyph coverage for CJK, Arabic, Hindi and Thai depends on fontconfig (Linux) and
  DirectWrite (Windows builds): UNVERIFIED per script, a P4 manual check.

### 4.13 Voice playback and ducking (fixes F3)

- The `voice` backend: a second MPV instance, created lazily and kept for the app
  lifetime. Two instances in one process play simultaneously ([CT] C28 RUN, headless:
  video 1.16 s and voice 1.09 s of progress after 1 s); real audio outputs are an S3
  item.
- Duck channel, chosen at session start by `duck_channel_for(backend.mpv_version)`:
  - AfDuck (primary, mpv >= 0.37 only). `mpv-cmd` sets
    `af=@vtduck:lavfi=[volume=volume=1.0]` before the first unpause (the label syntax is
    accepted and reads back as `label: vtduck`, `af=""` clears it, [CT] C29 RUN). A probe
    `af-command vtduck volume 1.0 volume` then runs from `live-sched`; it must return
    success. `set_duck(g)` sends `command(*af_duck_command(g))`, i.e.
    `af-command vtduck volume <g> volume`.
    - Why the trailing `volume`: mpv passes the `<target>` argument to
      `avfilter_graph_send_command` (0.41 `f_lavfi.c:818-821`), and FFmpeg overwrites the
      return code with the last matching filter's ENOSYS (avfiltergraph.c 1312-1334 at
      n7.1). Without a target (or with `all`) 0.41 returns MPV_ERROR_COMMAND (-12)
      although the gain IS applied (RMS 0.088 -> 0.022); with target `volume` it returns
      success; naming the instance `volume@duck` fails ([CT] C29 RUN, p1-p3).
    - `[<target>]` first appears in the 0.37.0 input.rst; 0.34.1, 0.35.1 and 0.36.0 have
      `af-command <label> <command> <argument>` only, and 0.35.1 hard-codes "all"
      (`f_lavfi.c:817-818`), so on those versions the command can never report success.
      They use VolumeDuck directly: treating -12 as "applied" would be blind, because no
      read-back exists.
    - The user `volume` property is never written by `live-sched`, so the slider has
      exactly one writer (`mpv-cmd`) and the race cannot happen. At stop, `af=""`.
  - VolumeDuck (mpv < 0.37, or when setting `af` or the probe fails). `VolumeMixer` has
    owner "sched" for the session:
    - the Tk slider calls `session.set_user_volume(v)`, which only updates the mixer
      state;
    - `live-sched` is the ONLY writer of `volume` (`user x duck`), when the mixer
      version changes;
    - it re-asserts every 250 ms, so a stale write at the ownership handoff heals within
      250 ms;
    - at stop, the owner goes back to "cmd" and `mpv-cmd` applies the mixer.
    Debian 12 (0.35.1) and Ubuntu 22.04 (0.34.1) users get VolumeDuck.
  - Both channels are subject to the device buffer, hence the measured `duck_latency_s`
    (4.11).
- Mute applies to both instances (voice volume 0). The voice volume follows the user
  volume.
- A/B in live mode:
  - "Dubbed" = dub on;
  - "Original" = dub off: unduck, voice stopped, no new TTS requests;
  - subtitles are independent (the Subtitles toggle).

### 4.14 Queues and backpressure

| Queue | Producer -> consumer | Bound | Overflow policy |
|---|---|---|---|
| bridge events | mpv event thread -> Tk | deque 512 | drop oldest, log entries first |
| bridge props | mpv event thread -> Tk, live-sched | 1 slot per property | latest wins |
| `mpv-cmd` | Tk, live-sched (seek/load) -> cmd thread | 64 | coalesce by key; still full: drop the new command, `player_busy` |
| `utt_q` | live-decode -> live-asr | 8 | streams: drop oldest + `live_warn_skipped`; files: bounded blocking wait |
| `mt_q` | live-asr -> live-mt | 64 | on full, the decoder's skip rule applies upstream (sync wins over completeness) |
| `sched_in` | live-mt, live-tts -> live-sched | 256 | drop the oldest translated segment (caption lost, counted) |
| TTS in flight | live-sched -> live-tts | 8 | only segments whose deadline is ahead are submitted |
| `LiveStore` | ingest -> readers | `live_buffer_max_mb` | evict oldest chunk, clamp reader, reload rule |
| segments in scheduler | - | 500 (streams) / 2,000 (files) | evict oldest done/dropped first |
| clip files | live-tts | streams: played or dropped are deleted; files: session | removed with the session dir |

### 4.15 Stop and stale sessions

Session dir: `runtime_app_paths(...).cache_dir / "live" / <session_id>` (platforms.py:141).
It holds:
- `session.lock` (pid, `process_start_token(pid)`, session start time; written by
  `write_session_lock`);
- `store/`;
- `tts/`;
- `ffmpeg.log` (the stderr ring, flushed at stop).

Stop (user, stream end, fatal error or app close) runs `request_stop()`, then a `live-stop`
helper thread runs `join(6 s)`. Tk shows `live_status_stopping` and polls every 100 ms:
1. `live-sched` on its next tick: clear the overlay, unduck, remove `af` (or restore the
   mixer owner), stop the clip, restore `speed=1.0`, then:
   - stream sessions: post `stop` for the video player through `mpv-cmd`;
   - file sessions: keep the file loaded, pause unchanged.
   Then it exits.
2. `IngestWorker.stop`: terminate ffmpeg, wait 2 s, kill, unregister; `store.finish()`.
3. `store.close()` wakes every `read_at` (mpv adapter, TailReader) with EOF.
4. Joins:
   - `live-decode` 2 s;
   - `live-asr` 3 s (frees Whisper and runs `empty_cache` on its own thread);
   - `live-mt` engine timeout + 1 s (Marian freed, Ollama `keep_alive: 0` with a 2 s
     timeout);
   - `live-tts` 3 s (tasks cancelled, `.part` files removed).
   A join timeout is logged with the thread name, and the sequence continues.
5. Streams: wait until `MpvStreamAdapter.closed` is set (at most
   `LiveTimeouts.stream_closed_s`, 2 s). `idle-active` is NOT the signal: it becomes true
   7 ms after `stop`, while mpv's `cancel`/`close` of a blocked stream arrive about 106 ms
   later ([CT] finding 7, 3 runs). A timeout is logged and the sequence continues (the
   store removal then retries, step 6).
6. `shutil.rmtree(session_dir)`, retried 3 times at 200 ms on Windows. On failure, the dir
   is left for the stale cleanup.
7. Status `stopped`. The voice backend is stopped, not terminated. File-mode options are
   restored at the next file load.

Stale cleanup ([sync] graft; fixes F7; corrected by [CC] G12): at each session start,
`cleanup_stale_sessions(root, owner_alive=...)` removes a session dir only when its owner
is dead: `platforms.pid_alive(pid)` is False, or the pid is alive but its
`process_start_token` differs from the one in `session.lock` (a recycled pid). The age
rule (24 h) applies only to dirs whose `session.lock` is missing or unreadable. On
Windows `pid_alive` uses `OpenProcess` + `GetExitCodeProcess` through ctypes, never
`os.kill`: CPython's os.rst states that on Windows any signal value other than
CTRL_C_EVENT/CTRL_BREAK_EVENT makes `os.kill` terminate the process
(https://github.com/python/cpython/blob/main/Doc/library/os.rst, as quoted by [CC] G12),
so the draft's
implicit POSIX idiom could have killed the other instance. With this rule a running
session of a second app instance is never touched (unit-tested with fake pids and tokens;
manual check in 7.6).

---

## 5 Sync modes

### 5.1 Semantics

| Source | Delayed video (default) | Live video |
|---|---|---|
| URL live stream | playhead kept D s behind the (estimated) ingest edge; subtitles and voice start with the speaker | playhead about L s behind the edge (5.4); subtitles about 1 s, voice about 1.6-2.6 s after the sentence ends |
| URL VOD | the same as live; the ingest runs ahead of real time up to the backpressure cap, and the controller never lets lag drop below D | at least L behind the edge |
| Local file | "wait for translation": playback keeps `live_file_ahead_s` seconds of translated material ready ahead (the slider, default 8 s with the dub and 4 s captions only) and pauses (`live_status_waiting`) when the translated region is about to run out | "keep playing": late dubs dropped, late subtitles shown late |

The LiveBar has one segmented toggle (`live_mode_delayed` / `live_mode_live`). It is
persisted as `live_sync_mode`, and `live_tip_mode` explains the trade-off.

### 5.2 Edge estimation (fixes F1)

Problem: HLS delivers whole segments. The ingest edge therefore stands still between
bursts while the playhead advances, so a raw `lag = edge - player` is a sawtooth with the
amplitude of one segment. YouTube live: `#EXT-X-TARGETDURATION:5`, every EXTINF 5.0, 720
segments (a 1 h window) in both the video and audio playlists, `.ts` segments ([CT] C21
RUN on one stream). Twitch UNVERIFIED.

`EdgeEstimator`:
- `observe(edge, mono)` runs for every decoded block. Consecutive blocks closer than
  `burst_gap_s` (0.5 s) belong to one burst. The idle time before each burst is a "gap".
- `linear(mono) = mono + max(edge_i - mono_i)` over the last 60 s. In steady state the
  source produces media at 1x, so the burst peaks lie on one straight line. The maximum
  offset is that line, and it advances smoothly with wall time.
- `max_gap_s` is the largest gap in the window. The first 10 s after a (re)connect are
  ignored (the initial catch-up of about 3 segments, [04] 13.2). The default is 6 s until
  3 gaps have been seen.
- `stalled = mono - last_block_mono > 2 * max_gap_s`. While stalled,
  `effective = observed` (frozen), so the lag shrinks honestly. Otherwise
  `effective = linear`.
- `reset(mono)` runs on (re)connect, `mark_gap` and PTS discontinuities (a time jump over
  0.25 s between decoded blocks, or backwards).

Cross-check: mpv's `demuxer-cache-time` should stay at or below `observed`. A persistent
difference over 2 s is logged as "mpv reader starved".

### 5.3 Delayed video (streams)

Start ([mvp] graft):
- the session does not load the player until `edge.observed - first_pts >= D`. Status:
  `live_status_buffering {s} of {total}`;
- it then loads `store.player_uri()` paused, and unpauses after `file-loaded` and
  `demuxer-cache-duration >= 1 s`;
- playback starts at `first_pts`, so lag = D with no initial seek, and the first delay
  never depends on seeking.

`DelayController.step`, every 1 s, with `lag = edge.effective - player`, `err = lag - D`:
```
if user_paused or paused_for_cache:              none (mpv waits; user owns the pause)
elif self_paused:                                resume when err >= -0.5, else none
elif |err| <= 0.5:                               speed 1.0 (only if not already 1.0)
elif |err| <= 3.0:                               speed 1 + clamp(0.01 * err, -0.03, +0.03)
elif err > 3.0:                                  seek to edge.effective - D if cache_end >= that
                                                 target (forward, inside the demuxer cache),
                                                 else reload at SeekIndex.offset_for(target)
else (err < -3.0):                               pause until err >= -0.5 (buffering)
hysteresis: a new action only when the band changes or 2 s after the previous action
```

Properties:
- Speed nudges are pitch-corrected by scaletempo2. A 3 s drift takes about 100 s to absorb
  at 3 %, which is inaudible.
- In steady state only speed is used. Every seek is FORWARD and lands inside mpv's forward
  demuxer cache, which the store keeps filled up to the edge. So no seek depends on
  unknown-size stream seeking; the only exception, a reload, is handled below.
- Nobody DVRs backwards. Pause and resume by the user:
  - on resume, `resume_action`: if `lag <= D + 3`, nothing (the controller nudges);
  - else if `cache_end >= edge.effective - D`, a forward cache seek;
  - else a `reload` at `SeekIndex.offset_for(edge.effective - D)`: the player loads
    `vtlive://<id>?offset=<n>`, a visible but short freeze that is acceptable after a user
    pause.
- Changing D (slider 6-30 s, step 1, applied and persisted on release) with
  `set_delay(D', immediate=True)`:
  - a larger D pauses for the difference (buffering);
  - a smaller D seeks forward inside the cache.
  The utterance cap follows D (5.8).

Auto raise (`live_delay_auto`, 5.7) uses `set_delay(immediate=False)`: speed 0.97 until
reached, with no pause and no seek.

### 5.4 Live video (streams; fixes F2)

- Target distance `L = live_distance_s(edge.max_gap_s) = clamp(1.5 * max_gap_s, 2.0, 8.0)`;
  about 7.5 s on YouTube live with its 5 s segments.
  Right before a burst, the data left ahead of the playhead is `L - gap`, at least
  `0.5 * gap`, so playback does not reach the observed edge between segments.
- Start: load when `edge.observed - first_pts >= L`, then seek forward to
  `edge.effective - L` once the cache covers it.
- Steady state: no speed nudges. If `lag > L + 4 s` (after a stall), seek forward to
  `edge.effective - L`. True starvation is left to mpv's cache-pause.
- L is recomputed every 10 s. A change of more than 1 s re-targets through the same seek
  rule; it never pauses.
- Sentence hold 0.4 s, utterance cap 5 s, dub FIFO with at most 4 s lag.

### 5.5 Files (`FilePacer`)

- Delayed ("wait for translation"):
  - pre-roll: stay paused at the current position until `ready_until - pos >= min_ahead`,
    where `min_ahead = live_file_ahead_s` (the Delayed slider for files, 4-30 s; absent =
    8 s with the dub, 4 s captions only, [CC] G7), capped at `min_ahead + 12 s` of wall
    time; after the cap it unpauses anyway and captions arrive late;
  - then pause (`live_status_waiting`) when `ready_until - pos < 2 s` and the decoder has
    not reached EOF, and resume at `>= min_ahead`;
  - `ready_until` comes from `DubScheduler.ready_until(now)`: the end of the contiguous
    coverage where every line is translated and (with the dub) has its clip.
- Live ("keep playing"): never pauses. Late clips follow the live-mode rules and late
  captions show late.
- The pacer never changes speed on files.

### 5.6 Switching at runtime

- Streams:
  - delayed to live: forward seek to `edge.effective - L`, then `DubScheduler.set_mode`
    and `on_seek`. Clips of the skipped segments are dropped;
  - live to delayed: pause until `lag >= D` (buffering, no backward seek, [mvp] graft);
    segments already processed stay valid because they are keyed by PTS.
- Files: only the pacing policy changes; no seek.

### 5.7 Automatic delay raise (`live_delay_auto`, default on)

- Every 8 dubbed segments (or 8 captions with the dub off): if `margin_p90 < 0.3 s`, or
  `late + dropped > 2` in that window, or `skipped_s > 0`, raise the target by 2 s (at most
  30 s) through `set_delay(immediate=False)` and show `live_warn_falling_behind {s}`.
- A CPU fallback raises the target by 3 s once.
- It never lowers the delay automatically in v1: stability wins over latency. The user can
  lower it with the slider at any time. With the key off, the status offers
  `live_tip_raise_delay {s}` with a p95-based value instead.

### 5.8 Latency budget

Per sentence, measured from the END of speech, p95 ([02] 1, [05] 1 and 6; RTX 3090 and
i7-10700K). The CPU column is `small` int8 plus Marian on the CPU. The hold H applies only
without end punctuation.

| Step | GPU Marian | GPU Ollama (warm) | CPU |
|---|---|---|---|
| endpoint (VAD silence) | 0.4 s | 0.4 s | 0.4 s |
| ASR decode | 0.25 s | 0.25 s | 1.8 s |
| sentence hold H (delayed / live) | 1.5 / 0.4 s | 1.5 / 0.4 s | 1.5 / 0.4 s |
| MT | 0.2 s | 0.8 s | 0.6 s |
| caption ready (delayed) | 2.35 s | 2.95 s | 4.3 s |
| Edge-TTS full clip | 1.25 s | 1.25 s | 1.25 s |
| lead (audio buffer + start) | 0.25 s | 0.25 s | 0.25 s |
| voice ready (delayed) | 3.85 s | 4.45 s | 5.8 s |

Typical values are much lower: caption ready about 0.6 s and voice about 1.6 s on the GPU
([05] 6).

`derive_live_timing(D, mode, device, engine, dub)`:
- Delayed: `umax = clamp(D - ready_p95 - 1.0, 4.0, 8.0)`, where `ready_p95` is the "voice
  ready" row with the dub and the "caption ready" row without it.
  - GPU Marian, D=12: umax 7.15.
  - GPU Ollama, D=12: umax 6.55.
  - CPU, D=15: umax 8.0.
  - Subtitles only, GPU, D=9: umax 5.65.
- If D is below the value that gives umax 4, the status shows `live_tip_raise_delay`. The
  value is accepted anyway and late clips are dropped by policy.
- `hold_s`: delayed 1.5 s, live 0.4 s. `min_ahead_s` (files): `live_file_ahead_s`,
  default 8 s with the dub, 4 s without. `resume_ahead_s = min_ahead_s`.
- A Marian pivot route roughly doubles the MT row (two legs); on the GPU it stays under
  0.2 s p95, on the CPU about 0.6 s ([05] 1.2 per-leg figures).
- Live: `umax = 5.0`. Captions appear about `U + 1 s` after the sentence starts (GPU); the
  voice follows about `U + 2.1-2.5 s` after.
- `recommended_delay_s`: 12 s GPU with the dub, 9 s GPU subtitles only, 15 s CPU with the
  dub, 11 s CPU subtitles only. It is used when `live_delay_s` is absent (Q8).
- The platform's own live latency (YouTube: "less than 10 seconds" for low latency and
  "less than 5 seconds" for ultra-low, no figure for normal latency,
  https://support.google.com/youtube/answer/7444635, [CT] R11) comes before our ingest
  edge and does not enter D.
- Cold paths are paid once at session start: Whisper turbo load 0.7-4.1 s, Marian 0.6 s,
  Ollama 1.8-18 s when evicted ([02] 1, [05] 1.2).

### 5.9 UI

- LiveBar idle row (whenever the player is ready): [Delayed | Live] [Delay slider plus
  "Delay: 12 s"] [engine] [privacy info]; the slider edits `live_delay_s` for streams and
  `live_file_ahead_s` for files. Running row: [Stop translation] [status: buffering /
  waiting / running / "Translation 3 s behind" / "12 s behind live"]. Warnings appear in
  the banner line.
- Stream sessions:
  - the seek bar shows the window from the session start to the edge, the played part and
    a LIVE badge; clicks are ignored;
  - transport: play/pause, and stop (which stops the session); previous, next, back and
    forward are disabled; snapshot stays enabled; open folder is disabled because no file
    backs `vtlive://` ([CC] G21).
- File sessions keep the full transport; seeks are forwarded to the session.

---

## 6 Error handling and degradation

### 6.1 Player conditions

| # | Condition | Detection | User sees | Recovery |
|---|---|---|---|---|
| 1 | python-mpv missing | `find_spec`/ImportError in `quick_presence` or the probe | placeholder `player_missing_pymod` + Install | `ComponentInstaller` with pip `mpv>=1.0.6,<2`, then `refresh_import_paths` and a re-probe; if `mpv` is still not importable (a user site dir created during this run and not addable), `player_restart_required` ([CC] G3). `_install_deps` is not used: it takes no callback, sets `_running` and chains the Italian-only optional popup (:5945, :6017-6030) |
| 2 | libmpv missing, Linux | `ldconfig -p` has no `libmpv.so` line | `player_missing_libmpv_linux {cmd}` + Install | `system_packages` plan (pkexec, then `sudo -n`; never plain `sudo`, [CT] R5), re-probe; both refused or unavailable: the placeholder keeps the manual `{cmd}`; may end in row 4 |
| 3 | libmpv missing, Windows | no DLL in the candidate dirs | `player_missing_libmpv_win` + Install | consent `player_install_confirm`, per-user install (Q6) |
| 4 | libmpv too old (Debian 11, Ubuntu 20.04: 0.32) | API < 1.108, or `mpv_version` < `TESTED_FLOOR` | `player_libmpv_too_old {version}` | none; no reinstall loop |
| 5 | DLL cannot load | OSError (WinError 126 or other) in the subprocess probe | `player_vulkan_missing` when `%SystemRoot%\System32\vulkan-1.dll` is absent, else `player_libmpv_load_failed` (possible antivirus quarantine, [06] 5) | installer Repair or per-user install (fetches the Vulkan fallback, Q2) |
| 6 | DLL crashes the probe process | non-zero exit without JSON, or timeout | `player_probe_crashed` | never loaded in-process; Repair or another build |
| 7 | video output cannot start | `detect_vo_failure` | nothing if the chain recovers (`player_vo_fallback_used` through `panel.notify`); else `player_err_video_output` | Linux: `X11ErrorGuard.restore()` at once; VO profile chain (3.1), persisted; in-process only if S1-X passed, else `player_restart_required` and the next profile at the next start |
| 7b | the probe accepted no VO profile | `vo_profiles_ok` empty | `player_err_video_output` | none; detail in the log |
| 8 | file not playable | `end-file` reason error | `player_err_load {name}` | stays idle; detail in the log |
| 9 | snapshot fails | `command_async` error reply | `player_snapshot_failed` | none |
| 10 | command stalls (for example a blocked stream open) | `mpv-cmd` watchdog > 5 s | `player_busy` while commands coalesce; Tk unaffected | clears when the command returns; no automatic re-creation (churn is a known leak/hang source, [04] 5.2) |
| 11 | event flood | bounded deque | nothing | oldest log events dropped |
| 12 | Windows lock on a loaded output | job start with a dubbed item loaded | nothing visible (player stops) | `_release_player_then` (3.6) |
| 13 | exception inside an mpv callback | try/except in every callback | one rate-limited log line | callback returns |
| 14 | callbacks after shutdown began | bridge closed | nothing | writes dropped |

### 6.2 Live conditions

| # | Condition | Detection | User sees | Recovery |
|---|---|---|---|---|
| 1 | job running at live start | `self._running` (and not `_installing`, not `_editor_open`) | `live_err_busy` | wait (Q4) |
| 1b | subtitle editor open | `self._editor_open` | `live_err_editor_open`; live buttons disabled with that tooltip | close the editor ([CC] G1) |
| 1c | an install running | `self._installing` | `live_err_busy_install` | wait |
| 2 | live running at job start | `live_active` | `live_err_busy_job`; Start and Download disabled | stop the session |
| 3 | missing modules | `find_spec` | `live_err_deps {items}` with `live_btn_install_deps` | `deps_install_confirm`, then `ComponentInstaller` (translated keys, progress in the log, `deps_install_ok/failed`); never the Italian-only optional popup ([CC] G4) |
| 4 | URL unresolvable (bot check, private, geo, network) | yt-dlp exception | `live_err_resolve {detail}` + anti-bot advice in the log | user retries |
| 5 | upcoming stream | `live_status == "is_upcoming"` | `live_err_upcoming` | none in v1 |
| 6 | codec not TS-compatible, or unknown after the ffprobe check | `is_ts_compatible`, `probe_codecs` | `live_err_codec` | use Download |
| 7 | network drop, stall, ingest exit | no bytes 15 s, ffmpeg rc != 0 | `live_status_reconnecting ({n})`; playback continues from buffered data, and mpv cache-pause freezes the clock so the scheduler pauses the clip | `IngestPolicy`; after the cap `live_err_ingest` |
| 8 | stream ended | rc 0 + re-resolve | `live_status_ended` once playback reaches the edge | session stops itself |
| 9 | PTS discontinuity (ads, rendition switch, restart) | decoder time jump | nothing (logged) | `edge.reset`, segmenter flush, pending clips before the jump dropped |
| 10 | store cap hit (reader standing still) | store size | nothing (logged) | evict, clamp, reload rule |
| 11 | disk low or write error | free < 512 MB, OSError | `live_err_disk {gb}` | session stops, store removed |
| 12 | Whisper / Marian load fails, or no Marian route | exception in `prepare`, `marian_route` None, no target token | `live_err_asr {detail}` / `live_err_marian_pair` | session does not start, nothing left running |
| 12b | Marian pivot route | `MarianRoute.pivot` | `live_info_marian_pivot {src} {tgt}` in the banner | none; the operator can disable pivots (Q12) |
| 12c | spoken language not detected | `LanguageLock` gives up after 60 s of speech | `live_err_need_source_lang` | the user picks the source language and restarts |
| 13 | CUDA error mid-session | `is_cuda_runtime_error` | `live_warn_cpu_fallback` | CPU `small` int8, delay +3 s |
| 14 | ASR too slow (streams) | `asr_lag` bound | `live_warn_skipped {s}` | skip ahead; auto raise |
| 15 | Marian route not cached | `marian_is_cached(route)` | `live_confirm_download_pair {name} {size}` | download on a `_redirecting_thread_factory` worker, so huggingface_hub's tqdm progress reaches the log (2.4), or abort |
| 16 | Ollama unreachable | health check | `live_err_ollama` | start Ollama or another engine (no auto-install in live) |
| 17 | MT timeout / error | `Outcome.ok=False` | italic source-language caption | breaker |
| 18 | Google / DeepL 429 | breaker `rate_limited` | `live_warn_rate_limited {engine} {s}` + `live_btn_switch_marian` | half-open probe; one-click switch; never automatic |
| 19 | DeepL 456 quota | status code | `live_warn_quota {engine}` | source-language captions for the rest of the session |
| 20 | Edge-TTS 403, throttling or no network | exceptions, timeouts | `live_warn_tts_unavailable` | dub suspended, subtitles continue, probe after cooldown |
| 21 | voice output failure | voice `end-file` error x3 | `live_warn_tts_unavailable` | dub disabled for the session |
| 22 | pipeline too slow for D | scheduler metrics | `live_warn_falling_behind {s}` (auto) or `live_tip_raise_delay {s}` | 5.7 |
| 23 | worker thread crash | top-level except in every loop + Tk `is_alive` check while running | `live_err_internal` | orderly stop (4.15), traceback in the log |
| 24 | stop step exceeds its bound | join/terminate timeouts, `closed` Event timeout | nothing | sequence continues; stale cleanup next time |
| 25 | 12 h reached on a stream | first PTS + 12 h | `live_status_time_limit` | session stops itself ([CC] G30) |
| 26 | worker thread output under pythonw | library writes | nothing | redirect or drop (R9) |

GPU summary:
- the player uses `hwdec=auto-safe` and falls back to software decoding by itself;
- ASR falls back to the CPU (row 13);
- Marian runs on the CPU when CUDA is not available at `prepare`;
- Ollama is unaffected;
- the dubbing pipeline keeps its own CUDA fallback;
- live mode and jobs are exclusive (Q4), so VRAM never has to hold Demucs, XTTS and live
  models at once.

### 6.3 Degradation ladder (live)

1. Everything works: subtitles and dub in sync.
2. The online MT is limited: italic source captions, no dub for those lines, a banner with
   "Switch to MarianMT".
3. Edge-TTS is down: subtitles only (the original is not ducked).
4. The GPU is lost: CPU ASR with a larger delay.
5. The ingest is lost: reconnect attempts, then a clean stop with a reason.
At no step does the app block, change the engine, or touch the dubbing pipeline.

### 6.4 App close (`_on_close`, :8376)

If `_running` or `live_active`, ask (`msg_confirm_stop` or `live_confirm_stop`). Then
`_begin_close()`:
1. `_destroying = True`. A re-entry flag ignores further WM close events.
   `after_cancel` runs on the poll, the volume-save debounce and the editor SRT debounce.
2. An `app-close` helper thread:
   - live `request_stop` + `join(6 s)` (4.15);
   - `bridge.close()`;
   - `voice.terminate(3 s)`;
   - `video.terminate(3 s)`, which first joins `mpv-cmd` for 2 s, then
     `mpv_terminate_destroy`;
   - `X11ErrorGuard.restore()` right after the video terminate returns: the VO uninit has
     just set Xlib's exiting default, and Tk keeps processing X events until `destroy()`
     ([CT] finding 5).
   `terminate()` never runs on the mpv event thread or on the Tk thread. [CT] C5 RUN:
   `terminate()` from a helper thread while Tk pumps took 10 ms on Linux; python-mpv joins
   its event thread without a timeout (mpv.py:1157-1173), which is safe only because our
   callbacks never block. The backend holds the only `mpv.MPV` reference, and
   `terminate()` clears `handle` first (mpv.py:1163), so `MPV.__del__` can never run a
   blocking terminate on the Tk thread later.
3. Tk keeps pumping (`after(50)` polls `_finish_close`) until the helper is done or 10 s
   pass. Windows needs this for the cross-thread HWND teardown ([04] 5.2 rule 5; a risk
   inferred, not observed).
4. The existing loop terminates the registered subprocesses, then `destroy()`. On timeout,
   log to stderr and destroy anyway (python-mpv's event thread is a daemon).

mpv always terminates BEFORE the host frame is destroyed ([04] 4.1): on Win32 a destroyed
parent HWND makes mpv post a close event, and on X11 it would render into a destroyed
window.

### 6.5 Logging

- Live threads log sparsely, through the rate-limited `log` callback: state transitions,
  warnings, and one summary per minute ("live: 14 seg, 0 drop, lag 11.9 s, asr p90 0.21 s,
  margin p90 3.1 s, max gap 4.0 s").
- mpv `log_handler` lines reach the log through the bridge, deduplicated per message in
  10 s windows.
- The ingest's stderr ring goes to `ffmpeg.log` in the session dir and, on failure, its
  first line goes to the user message.

---

## 7 Testing strategy

### 7.1 Principles

- CI installs only `requirements-dev.txt` (`setuptools`, `wheel`,
  `opencv-python-headless`, `numpy`, `soundfile`; `.github/workflows/tests.yml:39-42`,
  Python 3.11 and 3.12). There is no mpv, libmpv, torch, av, onnxruntime, edge_tts,
  deep_translator, requests, yt_dlp, network or display.
- Every new module must import in CI: heavy imports live inside factories. A test asserts
  that importing each new module leaves `mpv`, `av`, `faster_whisper`, `edge_tts`,
  `transformers`, `yt_dlp` and `onnxruntime` out of `sys.modules`. It runs each import in
  a fresh `subprocess.run([sys.executable, "-c", ...])`, so the result does not depend on
  which tests ran before in the same process ([CC] T3).
- Fakes are injected through constructor parameters, in the existing style:
  - `tests/test_transcription.py` FakeTorch;
  - `tests/test_js_runtime.py` fake downloader;
  - `tests/test_preflight.py` fake `find_spec`/`which`/`run`.
  The shared doubles are the public `player_engine.InMemoryBackend` and `InMemoryVoice`;
  other fakes stay inside each test file (the suite has no shared helper modules today).
- Threads in tests: either the code under test takes an injected `thread_factory` or
  executor, or the test drives the pure object directly with a fake clock. No sleeps
  above 50 ms. Real-thread tests (`test_live_session`, `test_live_store`) inject
  `LiveTimeouts` of about 0.1 s and translator timeouts of 0.1 s, so the "stop within
  bound while a fake translator blocks" case takes well under 1 s instead of 6 s, and
  `threading.enumerate()` is checked after joins with those short bounds ([CC] T2).
- The exact CI command is used locally: `python -m unittest discover -s tests`. Never
  pytest from the root (backup folders collide, project CLAUDE.md).

### 7.2 Hermetic unit tests

| Test file | Covers |
|---|---|
| `test_libmpv_runtime.py` | candidate dir order; `prepare_import` prepends, then restores only the passed env, and keeps the `add_dll_directory` handle; Vulkan dir added only when System32 lacks it; API parse and gate; `parse_mpv_version` ("mpv 0.41.0", "mpv v0.41.0-1050-ge76a35ec9", "mpv 0.34.1", garbage); `TESTED_FLOOR`; `parse_ldconfig` (a real `ldconfig -p` sample, missing line, several sonames); fingerprint from the resolved real path; reason classification (ImportError, OSError, RuntimeError, AttributeError); `probe_in_subprocess` with a fake runner (ok JSON with `mpv_version` and `vo_profiles_ok`, crash, timeout -> probe-crashed, `no_window_kwargs` passed on win32); `install_windows` with fake downloader/runner: source order, github-latest newest-first with digest check, pinned SHA mismatch rejected, size cap, `.part` + replace, 0-byte leftovers removed, BUILD.txt idempotence and mpv commit field, the next source tried after a failed load check, the Vulkan member path `VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll`; `main` exit codes 0/2/3; `REASON_KEYS` covers every reason including `ok` and `restart-required` |
| `test_system_packages.py` | manager detection; apt libmpv2/libmpv1 choice; zypper `libmpv2`; plans per manager, no `-Sy`; privilege order `pkexec`, `sudo -n`, and NO plain `sudo`; `manual_command`; `run_plan` with a fake runner and DEVNULL stdin; `pip_install_command` flags equal `_install_deps`'s; `refresh_import_paths` with fake `site`/`importlib` (user site added only when it exists and is missing from `sys.path`); `ComponentInstaller`: `on_done` posted once, `restart_required` when `find_spec` still fails, never touches a `_running` attribute |
| `test_subprocess_utils.py` (extend) | `no_window_kwargs("win32")` has `creationflags` CREATE_NO_WINDOW; `{}` on linux |
| `test_platforms.py` (extend) | `pid_alive` POSIX branch with a fake `os.kill` (ProcessLookupError, PermissionError); Windows branch with a fake kernel32 (STILL_ACTIVE 259, exited, access denied) and an assertion that `os.kill` is never called on win32; `process_start_token` from a fake `/proc/<pid>/stat`; `reveal_in_file_manager` builds `explorer /select,"C:\\a b\\c.mp4"` as one string on win32, `["xdg-open", dir]` on linux, falls back to `os.startfile` when Popen raises |
| `test_player_engine.py` | `build_mpv_options` per platform, kind and profile (x11egl/x11vk/x11sw, never `gpu_context=x11`, never d3d11 options off win32, unsigned wid, `ytdl=no`, `audio_buffer=0.2`); `next_vo_profile` skips profiles not in `accepted`; `detect_vo_failure` on the two exact 0.41 strings; `stream_session_options`; `duck_channel_for` ((0, 36) volume, (0, 37) af, None volume); `af_duck_command` ends with the target `volume`; `EventBridge` coalescing, stamps, bounded deque drop order, close; `PlaybackClock` extrapolation, freeze on pause/cache/seeking, speed, values ignored while seeking, while a restart is expected and below `first_pts`, epoch increments on `playback-restart` (the [CT] trace 1007.52 -> 7.14 -> 1007.56 replayed); `CommandQueue` coalescing and full policy; `VolumeMixer` maths, versions, owner switch, thread safety; `X11ErrorGuard` with a fake libX11 (capture reads and restores the pointer, restore sets it, no-op when not captured); `register_raw_stream_protocol` with a fake backend: open parses the offset, read copies with memmove into a ctypes buffer, CFUNCTYPE objects kept until close, a raising adapter returns -1 and posts `stream-error`; `MpvBackend` with a `FakeMpvModule` (records kwargs, commands, property writes, observers, key bindings, terminate): per-file options written as properties before `command("loadfile", uri, "replace")`, never `MPV.loadfile`; callbacks only touch the bridge, never raise; terminate refused on the event thread |
| `test_player_core.py` | load/playlist/next/previous; pending load replayed on `attach_backend`; A/B with 2 tracks, with external source, unavailable; audio preference reapplied; subtitle add/toggle/reload; seek maths and drag mode; `format_clock`; `snapshot_path` collisions; `release_for_job`/`release`/`is_released`; `remove_items` (loaded source removed -> stop, dubbed unaffected); `PLAYER_KEYS` complete; `handles_player_key` table (every interactive class False outside the player, True inside, True on Frame/Label/None); `mouse_action` table from the [CT] event traces (click `dm-`+`um-` = one toggle, double click = two toggles + fullscreen, wheel `p`/`d` once); `playlist_groups` with a running job; `editor_geometry` clamps (small screen, portrait screen, default window); `controls_visible` thresholds; `STATUS_KEYS` |
| `test_player_settings.py` | every key: defaults, clamping, wrong types, platform-specific `vo_profile`, `live_file_ahead_s` range and default by dub on/off |
| `test_live_health.py` | breaker transitions, doubling cooldown, half-open probe, quota lock, one warning per episode; `RollingStats`; `parse_fault_spec`; `set(STATUS_KEYS) == LIVE_STATES` |
| `test_live_segment.py` | segmenter over synthetic probability scripts: start/end, padding, soft cut, hard cut, discontinuity flush, reset with gen; assembler: punctuation, media-time hold, word/span/char caps, multi-sentence split |
| `test_live_asr.py` | `PersistentWhisper` with a fake model and FakeTorch: one load, session-time offsets, CUDA error -> CPU reload + one retry, `close` frees; `LanguageLock` rules including the 60 % majority and the 60 s give-up; `filter_hallucinations`; `StreamingVad` with a fake ONNX session: h/c carry, 64-sample context, remainder across 4000-sample blocks (frames counted exactly); `AudioDecoder` with a fake `av` module (rebased vs raw time domain with `start_time` in microseconds, per-frame anchoring, start offset, SeekIndex feed) |
| `test_live_translate.py` | each engine with fake transports: timeout, one attempt, 429/456/403 mapping, never another engine; `EN_LEGS` has both legs for all 25 non-English codes; `marian_route` order (cached direct, cached tc-big, hub direct, hub tc-big, pivot, None; offline = cached only); target-token choice from a fake `supported_language_codes`, none -> error; pivot translation calls leg 1 then leg 2 within one timeout; Ollama warm-up and unload payloads; Google hung call abandoned; `marian_is_cached(route)` with a fake loader |
| `test_live_tts.py` | `choose_rate` bounds with a fake model; `EdgeDurationModel` seed then EMA, rate normalisation; `mp3_cbr_duration_s`; `measure_silence` with a fake `av` (leading/trailing silence, all silence, decode error -> None); `EdgeClipSynth` with a fake Communicate: int timeouts passed, keywords omitted when `inspect.signature` lacks them, atomic write, deadline timeout gives no file, one retry rule, breaker suspension, `.part` cleanup on stop |
| `test_live_sync.py` | `EdgeEstimator` on synthetic burst traces (2 s, 4 s, 5 s and 6 s segments; initial catch-up; stall; reconnect reset): `linear` stays straight within 0.1 s, `max_gap_s` correct, `stalled` flag; `DelayController` table-driven: every band, hysteresis, NO pause and NO speed flapping on a 6 s sawtooth with D=12 (the F1 regression test), forward-only seeks, reload when the cache does not cover the target, resume rules, immediate vs gradual `set_delay`, mode switches; live mode with L from gap and no action on the sawtooth (the F2 regression test); `FilePacer` with `live_file_ahead_s`; `derive_live_timing` values from 5.8; `recommended_delay_s` |
| `test_live_scheduler.py` | fake-clock timelines: caption show/clear/pagination, italic fallback; delayed preload with `skip_s`, duck ramp starting `duck_latency_s + duck_ramp_s` before the slot, start at `start - voice_lead`, speed from `audible_s`, unduck timing, merge, late drop, overlap wait, stop; live FIFO, speed-up, lag drop; clip speed multiplied by main speed; pause/resume; `now=None` starts nothing; epoch change + jump -> `on_seek`; jump without epoch -> `on_discontinuity` (the C20 trace 1009.36 -> 1011.80); seek and gen drop; dub off and A/B original; `ready_until`; lead calibration; `ass_escape` (`\` gets U+2060, `{` -> `\{`, no doubling, a literal `\n` in text stays literal), `wrap_caption` |
| `test_live_store.py` | append/read across chunks; a blocking read woken by append; cancel; timeout returns None (never b""); finish then b"" at the end only; close gives EOF; low-water retention; cap eviction clamps a reader to 188 alignment; deferred unlink with a fake remover raising PermissionError (Windows style); `TailReader` retries on None; `MpvStreamAdapter`: relative positions after the first `seek(0)`, exact seek or -1 below `earliest`, seek beyond `written` blocks until append, read never returns b"" before finish, `closed` set by close, exceptions never escape; `SeekIndex`; `player_uri` for the three transports |
| `test_live_source.py` | the selector string; `is_ts_compatible` table including None -> "unknown"; `probe_codecs` with a fake runner (json parse, timeout, still unknown -> error); `ffmpeg_major_version` parsing ("ffmpeg version 5.1.6-0+deb12u1", "n8.0", "N-12345-g...", garbage); ingest command: headers, two inputs with per-input `-rw_timeout`, `-seg_max_retry` only when major >= 6, no `-reconnect*`, `-output_ts_offset`, `-ss`; `resolve_stream` with a fake YoutubeDL (live with split 232+234 and `acodec=None`, VOD DASH, upcoming, VP9 refused, errors -> keys); `IngestPolicy` with a fake clock: stall, backoff sequence, restart window cap, healthy reset, re-resolve on 403/404/410, second failure and age, end detection; `IngestWorker` with a fake Popen: bytes to the store, registry hooks called, stderr ring, VOD backpressure (stops reading above the cap), disk floor |
| `test_live_session.py` | end to end with fakes (`InMemoryBackend`, `InMemoryVoice`, fake decoder/VAD/Whisper/translator/TTS/clock, `LiveTimeouts` of 0.1 s) for a file source and a URL source: delayed start loads only at D, overlay and duck call order, dub inside its slot, rate-limit banner with its action, CPU fallback banner, pivot banner, engine switch at runtime, stop ordering (readers cancelled, ffmpeg stopped, models closed, player stopped, `closed` awaited before the store is removed), every `live-*` thread gone after `join` (`threading.enumerate()`), stop within bound even when a fake translator blocks; the injected `thread_factory` is used for every thread; `LiveConfig` repr contains no `engine_opts`; `cleanup_stale_sessions` with fake `owner_alive` (dead pid, live pid, recycled pid with another token, unreadable lock older and younger than 24 h); `build_live_config`; `wrap_factories_with_faults` scenarios |
| `test_output_media.py` (extend) | `mux_video` with `original_audio_input` (same input and separate input): maps, codecs, dispositions, titles; unchanged command when None; `segments_to_srt` output equals today's `save_subtitles` output |
| `test_pipeline_runner.py` / `test_jobs_pipeline.py` (extend) | `keep_original_audio` default and plumbing; the lip-sync branch calls `mux_video(synced, track, output, original_audio_input=video_in)` instead of `shutil.move` |
| `test_ui_worker_outcomes.py` (extend) | `_on_job_outputs` receives the right outputs for batch, URL and editor phase 2, and runs before `_on_done`; existing `_on_done` assertions unchanged |
| `test_ui_redirect.py` (new) | `_GlobalRedirect(None).write("x")` returns 1 and does not raise; `flush()` does not raise; `fileno()` raises `io.UnsupportedOperation`; with a thread-local redirect set, text goes to it ([CC] G2) |
| `test_ui_i18n_coverage.py` (extend) | all three scans over the GUI file and `*_tk.py`; the key maps; the literal-key scan of the new modules; `merge_into` without collisions or unknown languages |
| `test_preflight.py` (extend) | native probe ok / missing / too old / crashed; the `--preflight-player` promotion |
| `test_windows_installer_static.py` (extend) | `MPV_DIR=%INSTALL_DIR%\mpv-runtime`; `-m videotranslator.libmpv_runtime install`; `mpv>=1.0.6,<2` in its own pip call through a quoted variable; `mpv python-mpv` in both uninstall lists; `PACKAGES` unchanged (no `av` added, [CC] G15); no folder named `mpv`; ASCII only |
| `test_requirements_static.py` (extend) | `requirements-player.txt` referenced and pinned `mpv>=1.0.6,<2`; the same pin in the pyproject extra and the .bat; no other new requirement line (no `av`, no `onnxruntime`) |
| `test_no_long_dashes.py` (new) | no U+2014/U+2013 in the new modules, `ui_strings_player.py`, new tests and `setup_windows.bat` (the GUI file's historical occurrences belong to the separate approved clean-up) |

### 7.3 Fault injection ([sync] graft)

- `VTAI_LIVE_FAULTS="mt_429:3,tts_fail:2,cuda_oom@60,ingest_stall@120,afduck_off"` is
  parsed by `live_health.parse_fault_spec`, and `live_session` wraps the factories with
  it (`afduck_off` makes `duck_channel_for` return "volume").
- It is used by `test_live_session.py` and by manual checks. Dev only, no UI, ignored when
  empty.

### 7.4 Tk tests (skip without display)

Pattern: `tests/test_ui_theme_tk.py:9-17`. They ALWAYS skip in CI today (no display,
[CC] T1), so the phase gates in 9 require a local run under Xvfb (operator ruling) with the
output pasted into the plan; an optional CI job is Q14.
- `test_player_panel_tk.py`, with `InMemoryBackend`:
  - it builds in every theme and scale;
  - placeholder states;
  - `relabel()` after a language switch;
  - `apply_theme()` redraws icons and keeps the host `#000000`;
  - seek-bar drag guard;
  - reflow at 360, 460 and 700 px;
  - `on_command` fires for each button, by click AND by keyboard (Tab to the control,
    then Return and space), and the focus ring colour follows `apply_theme()`;
  - with focus on a `ttk.Button` outside the panel, space does NOT reach
    `_on_player_key`'s action; with focus on the panel it does ([CC] G5);
  - `notify()` replaces and then restores the "Now playing" text;
  - the logo loads from `assets/icon_256.png` and falls back to the canvas mark when the
    path is missing.
  `icon_shapes` is pure and runs without a display.
- `test_live_bar_tk.py`: builds, relabels, the idle row exists before any session, the
  slider switches between `live_delay_s` and `live_file_ahead_s` with the source kind,
  the running row appears and disappears, the banner shows an action and its close
  button is keyboard operable.
- `test_ui_layout_p0_tk.py`:
  - the player pane follows the window height;
  - the right column scrolls alone;
  - card drag still works;
  - the empty-band fix (fd7eacc) holds;
  - the Settings window has the Player section between Language and the buttons;
  - "Watch live" and Download wrap in German and Finnish at 460 px.

### 7.5 Opt-in real-library tests (never in CI)

- `test_player_real_mpv.py` runs only with `VTAI_REAL_MPV=1` and `find_library("mpv")`,
  headless with `vo=null ao=null`, on an ffmpeg-generated clip. It codifies spikes S1-S3
  as regressions:
  - load, observe, seek;
  - `audio-add` + `aid`;
  - `sub-add`;
  - `osd-overlay` through `command`;
  - screenshot;
  - `af=@vtduck` + `af-command ... volume` returns success on >= 0.37 (and the version
    gate picks VolumeDuck below);
  - two instances in one process;
  - `register_raw_stream_protocol` over a growing store with a concurrent PyAV reader
    (read latency p99 recorded);
  - `command("loadfile", ...)` with per-file options as properties;
  - `rebase-start-time=no` PTS equality, and `time-pos` ignored during a seek;
  - terminate under 1 s while an observer is busy.
- `test_player_real_x11.py` runs only with `VTAI_REAL_MPV=1` and a `DISPLAY` that is a
  private Xvfb (never the operator's `:0`): embedding, placeholder lift/lower,
  `mouse_action` with `xdotool` clicks, and the `X11ErrorGuard` check of S1-X.
- `test_live_av_reader.py` runs only when `av` and ffmpeg exist: ffmpeg writes a TS through
  `LiveStore` in bursts while `TailReader` + PyAV decode it (the [05] 1.4 prototype); PTS
  continuity and sample count.

### 7.6 Manual matrix (per phase, recorded in `_dev/CHANGELOG.md`)

- Platforms:
  - Kali XFCE X11 (this machine, dual monitor with a portrait screen), real display only
    when the operator allows it, otherwise Xvfb with `x11sw`;
  - GNOME Wayland and KDE Wayland (XWayland path);
  - Windows 10 22H2 and Windows 11 24H2 at 100 %, 125 % and 150 % DPI;
  - VirtualBox Windows guest without 3D (Vulkan loader, d3d11-warp);
  - Ubuntu 22.04 (libmpv1 0.34.1) and Debian 12 (libmpv2 0.35.1) in containers,
    headless (`vo=null`), for the S1/S3 command checks (Q13).
- Player checks:
  - embedding and resize;
  - accordion toggling and card drag while playing (the video must not resize);
  - the five themes and a light theme;
  - language switch (it, en, ja, ar);
  - fullscreen enter/exit on both monitors;
  - A/B audible gap and loudness jump;
  - subtitles for CJK and Arabic;
  - snapshot and open folder;
  - keyboard vs text focus (space on Start, Left on the volume slider, typing in the URL
    box), Tab through every player control;
  - click on the video, then a shortcut (focus not kept by the mpv child);
  - 20 closes during playback, each under 2 s;
  - close during a live session under 6 s;
  - re-running a job while its output is loaded (Windows);
  - placeholder states with libmpv removed.
- Live checks:
  - YouTube live and Twitch live, 60 min each, both modes;
  - a YouTube VOD URL;
  - local mp4, mkv and webm (including one with an audio start offset);
  - network unplugged for 20 s;
  - a Twitch ad break;
  - Google selected until a 429;
  - `VTAI_LIVE_FAULTS` scenarios;
  - a CPU-only run with `CUDA_VISIBLE_DEVICES=""`;
  - VRAM back to baseline after Stop (`nvidia-smi`);
  - two app instances, one of them live: the second instance's session start leaves the
    first one's session dir alone (Windows and Linux);
  - a Windows live session (file and YouTube live, 10 min each) under pythonw (the
    desktop shortcut), with a Marian model download during the session (tqdm output);
  - the `max gap` value from the log per platform.
- GUI checks follow the project rule: find the window with `wmctrl -l` before and after
  the launch and close it by id, never by name.

---

## 8 Installer and dependencies

### 8.1 Python dependencies (kept in sync by static tests)

1. `requirements-player.txt`: `mpv>=1.0.6,<2`. The floor is 1.0.6, not the draft's
   1.0.5: python-mpv 1.0.5 `MPV.loadfile()` fails on libmpv 0.41 with
   `ValueError('Invalid value for mpv parameter', -4)`, and 1.0.6+ handle the 0.38
   argument change ([CT] finding 10 RUN). The `libmpv-2.dll` name arrived in 1.0.5
   (1.0.4 `mpv.py:38` lacks it, [CT] R10). 1.0.8 (2025-04-25) is still the latest
   release (https://pypi.org/pypi/mpv/json), a pure wheel, licence "GPLv2+ or LGPLv2.1+"
   (wheel METADATA and `mpv.py:6-12`, [CT] R10). The code also never calls
   `MPV.loadfile` (2.2), so a future signature change cannot break loading.
   It is referenced from `requirements.txt`, which means updating
   `tests/test_requirements_static.py:17-31`, and listed in the README profile table.
   Never also `python-mpv` (the same `mpv.py`, [03] 2.1).
2. `requirements-core.txt`: unchanged. The draft added `av>=11`; the final design does
   not declare `av` or `onnxruntime`, because faster-whisper 1.2.1 already requires both
   (`av>=11`, `onnxruntime<2,>=1.14`, [FD]) and declaring only one was inconsistent
   ([CC] G14). `live_err_deps` covers an environment where either is missing.
3. `pyproject.toml`: extra `player = ["mpv>=1.0.6,<2"]`; core dependencies unchanged.
4. Not in `requirements-dev.txt`: an installed `mpv` without libmpv would turn an
   accidental import into an OSError in CI ([03] 3.4).
5. `setup_windows.bat`: its own non-fatal pip call for `mpv` through a quoted variable
   (`set "MPV_PIN="mpv>=1.0.6,<2""`, the `PYANNOTE_PIN` pattern of
   setup_windows.bat:805-810, never echoed expanded), and `mpv python-mpv` in both
   uninstall pip lists. `PACKAGES` is not touched ([CC] G15).
6. `preflight.py`:
   - `PackageProbe("mpv", "mpv", False, "integrated video player (python-mpv)")` in
     `DEFAULT_OPTIONAL_PACKAGES`;
   - a new injectable `native_checks: Sequence[Callable[[], PreflightCheck]] = ()`
     parameter of `run_preflight` (preflight.py:156), filled by the GUI and CLI with a
     `native:libmpv` check;
   - CLI `--preflight-player` (the pattern of `--preflight-lipsync`, cli.py:16-26) makes
     both required.
7. Not added to `OPTIONAL_PACKAGES` (video_translator_gui.py:284-298): that popup is
   hard-coded Italian ([03] 1.4). The player placeholder and `ComponentInstaller` own the
   install UX, with translated keys.
8. Live mode adds no other dependency.

### 8.2 Linux

| Distro | Package | Works with python-mpv |
|---|---|---|
| Kali rolling, Debian 12/13/sid | `libmpv2` (0.35.1 to 0.41.0) | yes (0.35/0.36 use VolumeDuck) |
| Debian 11 | `libmpv1` 0.32.0 | no (too old) |
| Ubuntu 22.04 | `libmpv1` 0.34.1 | yes if the S1/S3 container checks pass (Q13); AfDuck unavailable (< 0.37), VolumeDuck used |
| Ubuntu 24.04, 25.x | `libmpv2` 0.37.0 / 0.40.0 | yes |
| Ubuntu 20.04 | `libmpv1` 0.32.0 | no |
| Fedora 43/44 | `mpv-libs` (official repo) | yes |
| Arch | `mpv` | yes |
| openSUSE Tumbleweed / Leap 15.6 | `libmpv2` 0.41.0+git20260918 / 0.36.0 (backports) | yes ([CT] C48) |

Sources: [03] 2.3 and [06] 7 (Debian madison, Launchpad, Fedora mdapi, Arch JSON),
re-checked by [CT] R6 (Fedora f43 0.40.0 release, f44 0.41.0 updates-testing; Arch 0.41.0
extra; Debian 11 0.32.0-3, 12 0.35.1-4, trixie 0.40.0, sid 0.41.0; Ubuntu jammy 0.34.1).
Only the runtime package is needed: CPython `find_library` parses `ldconfig -p` and
matches `libmpv.so.2` ([06] 7); our `parse_ldconfig` reads the same output for the path.

GUI install:
- the Install button runs `_install_player()`, which starts a `ComponentInstaller`
  (2.2) on a `_redirecting_thread_factory` worker;
- the pip part uses `pip_install_command` (the same flags as `_install_deps`) and then
  `refresh_import_paths`; `_install_deps` itself is not reused ([CC] G3);
- the system part goes through `system_packages`: pkexec, then `sudo -n`, with
  `stdin=DEVNULL`, output streamed to the log, and never `pacman -Sy`. Plain `sudo` is not
  tried ([CT] R5). When both fail (no polkit agent, no cached sudo), the placeholder keeps
  showing the manual command;
- then a re-probe; `player_restart_required` if the module is still not importable.
The README Linux section documents `sudo apt install libmpv2` and
`pip install "mpv>=1.0.6,<2"`.

`_install_ffmpeg_linux` (:5810) is NOT refactored by this project ([CC] G24, out of
scope). Its `pacman -Sy` partial upgrade ([03] 1.5) stays a separate backlog item (Q11).

Wayland needs nothing extra: `gpu_context=x11egl` is the default profile (UNVERIFIED on a
Wayland session, C2, S5).

### 8.3 Windows

Location:
- `%ProgramFiles%\VideoTranslatorAI\mpv-runtime\` holds `mpv-2.dll` (renamed from
  `libmpv-2.dll`), `BUILD.txt`, the licence text and, only when needed,
  `vulkan-fallback\vulkan-1.dll`;
- the per-user fallback is `%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime\`
  (`js_runtime.app_data_dir`);
- never a folder named `mpv`: it would become a PEP 420 namespace package on `sys.path[0]`
  (verified in [03] 3.2);
- never on the machine or user PATH.

Installer step `:step_player`, after `:step_ffmpeg` in install and repair. Its label is
5/6, and the shortcut step becomes 6/6. The variable `set "MPV_DIR=%INSTALL_DIR%\mpv-runtime"`
goes next to the other paths (setup_windows.bat:13-21).
1. `"%PYTHON_EXE%" -m pip install %MPV_PIN% --quiet` with
   `set "MPV_PIN="mpv>=1.0.6,<2""` (the quoted `<` is not a redirection, and it is never
   echoed, [03] 1.1, the `PYANNOTE_PIN` pattern).
2. `pushd "%INSTALL_DIR%"`, then `"%PYTHON_EXE%" -m videotranslator.libmpv_runtime install
   --dest "%MPV_DIR%"`, then `popd`. Exit 2 or 3 gives the ASCII box "Integrated player
   disabled - everything else works", and the install continues.
3. After `validate_install`, `check` only warns.

All download, extraction and verification run in Python: urllib with the non-browser UA
"VideoTranslatorAI-Setup", timeouts, chunked reads and SHA256. This avoids the PowerShell
exit-code pitfall of the ffmpeg step ([03] 1.2). The file stays ASCII with CRLF
(`.gitattributes:5`).

Build sources as data ([mvp] graft; the licence choice is Q1). `WINDOWS_LIBMPV_SOURCES`,
recommended order:
1. `AssetSource(kind="github-latest", name="zhongfly-lgpl", licence="LGPL",
   repo="zhongfly/mpv-winbuild", asset_pattern=r"mpv-dev-lgpl-x86_64-\d{8}-git-[0-9a-f]+\.7z",
   max_releases=3)`. The newest 3 releases are tried, each verified by the GitHub asset
   `digest`. [CT] C46: the three newest releases (2026-09-23..25) carry a `sha256:` digest
   on every asset and the regex matches exactly one asset per release (the non-v3 LGPL
   x86_64 7z, 28.2 MB). The digest comes from the same API response as the URL, so it
   protects against transport errors only, not against a compromised upstream. If the
   API is rate-limited (60 per hour per IP, [06] 3), the fallback is the
   `/releases/latest` redirect plus that release's `sha256.txt` ([06] 3). zhongfly keeps
   30 days of builds, so a pin alone would rot ([06] 1.2).
2. `AssetSource(kind="pinned", name="shinchiro-gpl-20260920", licence="GPL",
   urls=("https://downloads.sourceforge.net/project/mpv-player-windows/libmpv/mpv-dev-x86_64-20260920-git-e76a35ec95.7z",
   <GitHub release URL while it exists>),
   sha256="60f9102db46aea8cef9bfb4345ee6a106f34fdbd1df9587e38f0660688039341",
   member_sha256="63e1fbb4ee890d153a9f5086410157174ee18582846bf35f6cc4e5d08d4bb662")`.
   This is the only durable pin: SourceForge keeps old builds ([06] 1.1, [03] 2.2).
   [CT] C47 RUN from Linux with the exact client (Python urllib, UA
   "VideoTranslatorAI-Setup"): `application/x-7z-compressed`, 31473132 bytes, both
   SHA256 values match. The build reports `mpv v0.41.0-1050-ge76a35ec9`: a master
   snapshot, not the 0.41.0 release ([CT] C10). zhongfly releases are daily master builds
   too. Windows users therefore run unreleased mpv master code, so S4 re-runs the S1/S3
   checks on the pinned snapshot and on the newest zhongfly build, and BUILD.txt records
   the mpv commit.

`install_windows` algorithm:
1. Idempotence: skip when BUILD.txt records a source still in the list and the DLL hash
   matches. Repair can upgrade when the list moves.
2. `7zr.exe` 26.03, pinned (https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe,
   SHA256 `ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d`, [06] 2,
   hash re-confirmed by [CT] C47), into a temp dir. py7zr cannot decode BCJ2 (tested,
   [06] 2). 7zr.exe is a console program: it always runs with `no_window_kwargs`, so a
   per-user install started from the pythonw GUI flashes no console ([CC] G16).
3. For each source in order: download (size cap 64 MiB), verify the archive hash, run
   `7zr e -y -o<tmp> <archive> libmpv-2.dll`, then check the PE `MZ` header, the size and
   the member hash when pinned.
4. Load check in a SUBPROCESS (`python -m videotranslator.libmpv_runtime check --dir
   <tmp>`): a crashing DLL cannot kill the installer. On failure, try the next source.
5. WinError 126 with no `%SystemRoot%\System32\vulkan-1.dll` (Q2): download the LunarG
   runtime zip 1.4.357.0
   (https://sdk.lunarg.com/sdk/download/1.4.357.0/windows/vulkan-runtime-components.zip,
   SHA256 `a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83`), extract
   the member `VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll` (the draft's
   `x64/vulkan-1.dll` path was wrong, [CT] C8; SHA256
   `cd862090370454630b31b174e3d4eb474fda38ea034998d1fe1767b0c99a8696`, both hashes
   re-confirmed by [CT] RUN) into `vulkan-fallback\`, and re-check ([06] 4.1). The pinned
   shinchiro DLL imports `vulkan-1.dll` in its import table with an empty Delay Import
   Directory ([CT] C8 objdump RUN).
6. Atomic `.part`, then `os.replace` to `mpv-2.dll`. Write BUILD.txt: source name, URL,
   release tag, archive and DLL SHA256, mpv commit, licence flavour, date. Fetch the
   licence text (LGPL or GPL) from the mpv repository at that commit ([06] 6.4).
7. Delete temp files, including a possible 0-byte DLL from a failed extraction ([06] 2).

Runtime (`prepare_import`):
- the runtime dir is PREPENDED to `os.environ["PATH"]` during `import mpv`, then restored
  (2.2 explains why not narrowed);
- the Vulkan fallback dir is added with `os.add_dll_directory` only when System32 lacks
  the loader. A local copy would shadow newer driver loaders ([06] 4.1). The returned
  handle is kept referenced for the process lifetime: libmpv's dependencies are resolved
  from the DLL dir, the app dir, `add_dll_directory` dirs and System32, never PATH
  (CPython `_load_library` with `LOAD_LIBRARY_SEARCH_DEFAULT_DIRS |
  LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR`; the mode flags python-mpv passes at mpv.py:55 are
  ignored on Windows, [CT] C9);
- `os.add_dll_directory` alone does not make python-mpv find libmpv ([03] 2.1).

Per-user install from the GUI (Q6): the Install button asks `player_install_confirm {size}`
(about 28-32 MB, plus 18 MB only when Vulkan is missing), then runs `install_windows` into
`%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime` on a worker, with progress in the log.

Uninstall:
- removing `%INSTALL_DIR%` covers the runtime;
- the per-user cleanup removes ONLY `%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime`, the
  folder this project adds. Deleting all of `%LOCALAPPDATA%\VideoTranslatorAI` (the
  deno bin, the 416 MB Wav2Lip fallback, caches) would fix a pre-existing gap ([03] 1.8)
  but is outside the player scope ([CC] G24): Q11.

Minimum: Windows 10 1607 (mpv README, [06] 4); x64 only (the installer refuses other
architectures, setup_windows.bat:541-558).

### 8.4 Licensing notices

The repository stays MIT in every scenario that does not re-host binaries. The installer
downloads third-party builds, as it already does for the GPLv3 gyan.dev ffmpeg ([06] 6.3;
a reading of the FSF FAQ, not legal advice).
- README "Third-party components" under `## License`:
  - libmpv (build source and flavour, https://github.com/mpv-player/mpv);
  - FFmpeg inside libmpv;
  - python-mpv (GPLv2+ or LGPLv2.1+);
  - 7-Zip `7zr.exe` (LGPL, used by the installer, not redistributed);
  - the Vulkan loader (MIT and Apache-2.0, only when fetched);
  - edge-tts (LGPLv3, already used).
- Next to the DLL: BUILD.txt (with the mpv commit) and the licence text.
- MarianMT models are downloaded by the user's machine from the Hugging Face Hub under
  their own licences (Apache-2.0 for the opus-mt models checked, CC-BY-4.0 for
  `opus-mt-tc-big-*`, [FD]); the README names them, as the batch pipeline already uses
  the same source.
- GUI: `player_credits {license}` in the Settings window footer. `{license}` comes from
  BUILD.txt ("LGPL" or "GPL"), or `player_license_system` on Linux.
- Installer echo, ASCII: `[*] Downloading libmpv (<name>, <licence> build) ...`.
- Never vendor `mpv.py` into the repository (a GPL/LGPL file, [04] 1.1). Never re-host the
  DLL unless the operator accepts the source obligations (Q1, option L2).

### 8.5 Repository hygiene

`.gitignore` gains `mpv-runtime/`, `*.dll` and `*.7z`. A dev running `install --dest` in
the checkout could otherwise stage a 100 MB DLL ([03] 3.7). `MANIFEST.in` needs no change:
it globs `requirements*.txt`.

### 8.6 New libraries: Windows status and installer workaround

Project rule (project CLAUDE.md, "Compatibilita Windows + Linux": state "ok / attenzione /
no" for every new library and the installer workaround; [CC] G23):

| Component | Kind | Windows | Linux | Installer workaround |
|---|---|---|---|---|
| python-mpv (`mpv` on PyPI) | pure Python wheel, optional | ok | ok | own non-fatal pip call in `setup_windows.bat` (quoted pin variable); GUI `ComponentInstaller` |
| libmpv | native library, optional | attenzione: not on PyPI, no official build; a third-party build is downloaded (Q1), unsigned, loaded only after a subprocess check | ok: distro package (`libmpv2`, `libmpv1`, `mpv-libs`, `mpv`) | `libmpv_runtime install` (installer step and GUI per-user fallback); Linux: package manager through pkexec or `sudo -n`, else the manual command |
| 7zr.exe 26.03 | installer-only tool | ok (pinned hash, run hidden) | not used | fetched into a temp dir, deleted after extraction |
| Vulkan loader (LunarG 1.4.357.0) | native DLL, only when System32 lacks it | attenzione: needed on VMs without 3D (Q2) | not used | extracted into `mpv-runtime\vulkan-fallback`, added with `add_dll_directory` |
| PyAV (`av`) | wheel, already installed with faster-whisper | ok (binary wheels) | ok | none (arrives with faster-whisper) |
| onnxruntime | wheel, already installed with faster-whisper | ok | ok | none |
| edge-tts, deep-translator, requests, yt-dlp | already core | ok | ok | none |
| transformers, sentencepiece | already optional profile | ok | ok | none; live `ComponentInstaller` if missing |
| Helsinki-NLP models | data, downloaded at first use | ok | ok | consent dialog, download on a redirected worker |
| ffprobe | tool shipped with ffmpeg | ok (the ffmpeg step copies `ffprobe.exe`, setup_windows.bat:1133-1134) | ok (distro ffmpeg) | none: the existing ffmpeg step |

No component needs a compiler on Windows.

---

## 9 Delivery phases

Common gates for every plan (project rules):
- one logical change per commit;
- conventional commit messages without a Co-Authored-By trailer;
- `python -m py_compile video_translator_gui.py videotranslator/*.py` and
  `python -m unittest discover -s tests` green;
- the Tk tests run locally under Xvfb (they always skip in CI, [CC] T1), output pasted
  into the plan;
- zero em/en dash in touched files;
- every new string in 26 languages;
- coder and reviewer on Opus, with the review only after the coder finishes;
- an empirical check (GUI launch under Xvfb, screenshot; the window found with
  `wmctrl -l` before and after the launch and closed by id) before a phase is called
  done;
- every acceptance item below names its measuring method; an item without a method is
  not accepted ([CC] 7);
- Windows parity by construction: from P2 on, each phase has at least one Windows item,
  run on the operator's Windows 11 machine or the VirtualBox guest;
- push only on operator request.

Plans live in `docs/superpowers/plans/2026-09-2x-player-*.md`. The approved design is
copied to `docs/superpowers/specs/` in P7.

Sequencing: the backlog work lands first, because it touches `_build_ui`,
`ui_theme_tk.py` and the card titles:
- the Task 5 review;
- Task 6;
- Task 7;
- the final review;
- the concurrent `translation.py` work.
Then this order:
- Plan 0 (spikes) runs first, in parallel with P0/P1;
- P2 needs S1 (S1-X decides in-process VO re-creation on Linux) and S5 for its Wayland
  item;
- P4 needs P2 only: the time-domain equality it depends on (C17/C18) is already
  confirmed within 25 ms by [CT] RUN, so the draft's hidden P4 -> S2 dependency is gone
  ([CC] 7);
- P5 needs S3;
- P6 needs S2;
- the Windows items of P1-P5 need S4.

### Plan 0: spikes (`_dev/spikes/player/`, gitignored; results in `_dev/CHANGELOG.md`)

Needs: `sudo apt install libmpv2` and `pip install "mpv>=1.0.6,<2"` on this machine (a dev
prerequisite; neither is installed system-wide today; the [CT] probes in
`_dev/research/player-2026-09-25/probe/` are the starting point). Ubuntu 22.04 and
Debian 12 containers for the 0.34.1 and 0.35.1 checks. X11 runs use a private Xvfb display
unless the operator allows the real one.

Already settled by [CT] (not repeated, only re-run as regressions in `test_player_real_*`):
embedding and child resize (C1), placeholder lift/lower on X11 (C3), `register_key_binding`
MBTN/WHEEL on 0.41 (C4), two instances (C28 headless), `lavf://file:` follow on Linux
(C14), blocking reads and raw-domain seeks on the custom stream (C13, C16, C19), time
domains (C17, C18), scaletempo2 (C32), Edge CBR duration (C34), the VAD wrapper (C37).

- S1 Embed on X11 (Kali 0.41; items (f) also on 0.34.1 and 0.35.1 headless):
  - (a) resize with accordion toggling and card drag: the video fills the host after each
    of 20 resizes (screenshot pixel check at the four corners of the host);
  - (b) root fullscreen enter/exit 10 times: the video fills the screen, no separate
    window appears (`wmctrl -l` count unchanged);
  - (c) `terminate()` from a helper thread while Tk pumps: 20 runs, each under 1 s, no
    hang;
  - (d) S1-X, the X error guard: `capture()`, create and terminate the video instance,
    `restore()`; then (1) the handler pointer equals the captured one, and (2) a
    deliberate X error on Tk's connection does not end the process (candidate trigger: a
    `tk.Toplevel(use=...)` on the id of a destroyed X window; the trigger itself is
    UNVERIFIED, alternative: `XGetWindowAttributes` through ctypes on Tk's `Display*`
    from `winfo` data). 20 runs, plus the same after a forced VO failure (`x11egl` on an
    Xvfb without EGL). PASS enables in-process VO re-creation on Linux (3.1);
  - (e) focus: after a click on the video, `focus_get()` is inside the player pane and a
    key reaches `_on_player_key` ([CC] G17);
  - (f) command checks on 0.34.1, 0.35.1 and 0.41: every option of 3.1 accepted,
    `register_key_binding` accepted, `osd-overlay` command form, `command("loadfile",
    uri, "replace")` with options as properties, `screenshot-to-file`, `audio-add`,
    `sub-add`, `playback-restart` events delivered. A failure on 0.34.1 moves
    `TESTED_FLOOR` to (0, 35) (Q13).
  - Go: (a)-(c) and (e) pass. (d) and (f) choose fallbacks, they do not stop the project.
- S2 Growing-store transport (gates P6):
  - candidates B (`vtlive://` with the raw ctypes registration), A (`lavf://file:` +
    `follow=1`) and C (local HLS EVENT), with ffmpeg writing a real YouTube live (split
    232+234 inputs) and a Twitch live for 20 min each while PyAV reads the same store;
  - criteria per candidate:
    (1) playback past the initial end, and a delayed start at D=12: lag at the first frame
        12 +- 0.5 s;
    (2) forward cache seeks inside the demuxer cache land within 0.1 s of the target
        (first valid `time-pos` after `playback-restart`);
    (3) `stop` while the reader is blocked: the adapter's `closed` Event (B) or the fd
        close (A, C) within 1 s;
    (4) valid `time-pos` equals the PyAV frame PTS within 50 ms on the live store;
    (5) zero `paused-for-cache` in steady state with the GPU ASR running, and read
        callback latency p99 under 20 ms, measured inside the callback from entry to
        return when data is already available (B only);
    (6) ingest restart with `-output_ts_offset`: monotonic PTS, mpv plays across the
        forward gap, and the scheduler sees a discontinuity, not a seek;
    (7) split inputs: the A/V offset of the ingested TS (first audio vs first video PTS
        after each restart, and mpv's `avsync` property) stays under 100 ms;
    (8) the codec of formats 233/234 is recorded (expected AAC);
    (9) on Windows (with S4): read-while-write sharing (C26) and deferred delete;
  - the first candidate passing all of them wins, in the order B, A, C, and
    `LIVE_TRANSPORT` is set. If (7) fails for every candidate, YouTube live is ingested
    through yt-dlp's muxed HLS fallback `b[height<=H]` when it exists, else refused with
    `live_err_codec` (documented).
- S3 Voice path (gates P5), Kali 0.41 with the real PipeWire/PulseAudio output; items
  (2) also on 0.34.1 and 0.35.1 headless:
  - (1) two instances playing together on the real output for 10 min: no underrun or
    AO error line in the log;
  - (2) AfDuck: on 0.41 `af-command vtduck volume <g> volume` returns success 100 times
    out of 100 and the gain applies (ao=pcm RMS); on 0.34.1/0.35.1 `duck_channel_for`
    picks VolumeDuck and the VolumeDuck path ducks;
  - (3) duck latency: 20 trials with ao=pcm and 20 with a loopback recording of the real
    output; PASS if p95 <= 0.6 s; `duck_latency_s` is set to p95 + 0.05 s per platform;
  - (4) ramps: 10-step ramps on speech material; objective part by construction (no step
    above 0.07 in the command log); subjective part: the operator's listening test
    recorded PASS or FAIL;
  - (5) voice start latency from a preloaded, paused clip on the real output: 20 trials,
    loopback audible onset minus unpause; PASS if stdev <= 50 ms and p95 <= 0.35 s; the
    median sets the per-platform device offset of `voice_lead`; FAIL: `gapless-audio` +
    appended clips (the fallback), then re-measure;
  - (6) `aid` switch on the real output: silence in the loopback recording <= 0.3 s in
    10 trials; else a documented limit (C33);
  - (7) the `start` property skips the leading silence: audible onset within 30 ms of
    the expected one on 10 clips.
- S4 Windows, the operator's Windows 11 machine and a Windows 10 or VirtualBox guest
  without 3D. Must pass (a FAIL blocks the Windows items of later phases until fixed or
  re-scoped with the operator):
  - (1) installer: `mpv-2.dll`, BUILD.txt with the mpv commit and licence, `check` exits
    0, a second Repair skips the download; for the pinned shinchiro snapshot AND the
    newest zhongfly build;
  - (2) the PATH-prepend import loads the runtime copy even with another
    `libmpv-2.dll` planted earlier on PATH;
  - (3) embedding, resize, root fullscreen, placeholder over the video (d3d11 flip model,
    C3); if the placeholder is hidden, `d3d11_flip=no` is set and (3) re-run;
  - (4) `terminate()` from a helper thread while Tk pumps: 20 runs, each under 2 s;
  - (5) guest without 3D: `vulkan-1.dll` absent, the fallback is fetched and the DLL
    loads; `d3d11-warp` plays in `wid` mode, or `player_err_video_output` shows; never a
    crash;
  - (6) DPI 125 % and 150 %: the video fills the host frame (screenshot);
  - (7) SourceForge serves the 7z to urllib on Windows (C47);
  - (8) under pythonw (the desktop shortcut), a forced `warnings.warn` and a tqdm bar in
    a worker thread do not raise (R9);
  - (9) S1 (e) and S3 (2), (5), (6) on WASAPI;
  - (10) `explorer /select,"<path with spaces>"` selects the file (C45, [CC] G18);
  - (11) `pid_alive` is True for a running pid and False for an exited one, and never
    terminates anything;
  - (12) the mpv child does not keep keyboard focus after a click (G17).
  Recorded, not pass/fail: Defender and Smart App Control reactions to the DLL (C12). A
  quarantine sends Q1 back to the operator.
- S5 Wayland session (GNOME and KDE): `gpu-context=x11egl` stays embedded (no separate
  window, `wmctrl -l`); the VO failure signal when EGL is missing. PASS puts Wayland in
  the matrix; FAIL documents "X11 session required", and the placeholder explains it
  (C2).

Acceptance: each spike is recorded PASS, or FAIL with the selected fallback, in
`_dev/CHANGELOG.md`, and the affected design sections are updated before the dependent
phase starts.

### P0 Layout (`...-player-p0-layout.md`)

- Scope:
  - root grid restructure (3.1);
  - the right column in its own scroll canvas;
  - the wheel binding only on the right column;
  - a fixed header;
  - `_player_area` stays the host.
  No new strings. Shippable alone: it only moves widgets.
- Acceptance:
  - at 900x600 and 1100x780 the left pane fills the window height and never scrolls
    (Tk layout test plus Xvfb screenshots);
  - expanding accordions or dragging cards does not resize it (widget geometry logged
    before and after in the Tk test);
  - fd7eacc and 0216809 still hold;
  - the Tk layout test is added and the suite is green;
  - screenshots (Xvfb) are attached to the plan.

### P1 Runtime detection and installation (`...-player-p1-runtime.md`)

- Scope:
  - `libmpv_runtime.py`, `system_packages.py` (with `ComponentInstaller`);
  - `subprocess_utils.no_window_kwargs`;
  - the `_GlobalRedirect` None fix and `_redirecting_thread_factory` (R9);
  - the preflight native check and `--preflight-player`;
  - `requirements-player.txt`, the pyproject extra;
  - README install and third-party sections;
  - `.gitignore`;
  - the `setup_windows.bat` step and uninstall lists;
  - the header "Player" badge and the placeholder with reason and Install;
  - the 17 availability/install keys.
  Shippable alone: the badge and the placeholder explain status; there is no playback yet.
- Acceptance:
  - `python -m videotranslator.libmpv_runtime check --json` exits 2 on Kali without
    libmpv and 0 with `libmpv2` + `mpv`, reporting API (2, 5), `mpv_version` (0, 41) and
    `vo_profiles_ok` containing `x11egl` and `x11sw` and not `x11glx`;
  - a crashing fake DLL in a test gives `probe-crashed`;
  - on a clean Windows VM the installer places `mpv-2.dll` + BUILD.txt, a second Repair
    run skips the download, and `check` exits 0 (S4 (1));
  - with the DLL removed the badge shows the reason;
  - Linux GUI install on a Debian 12 VM user without libmpv: the pkexec prompt appears,
    and after it the player is ready without an app restart; with pkexec cancelled, the
    placeholder shows the manual command;
  - pip part on an account whose `~/.local/lib/pythonX.Y/site-packages` did not exist at
    app start: after Install, `mpv` imports without a restart, or
    `player_restart_required` shows; never a crash;
  - Windows per-user install from the pythonw shortcut: no console window appears
    (visual check), progress in the log;
  - static tests: uninstall lists, requirement pins, `.gitignore` entries (`mpv-runtime/`,
    `*.dll`, `*.7z`), no long dashes;
  - the README third-party section matches the 8.4 list (review checklist item);
  - no path of the app crashes without the player: launch with python-mpv uninstalled,
    and with libmpv absent, on Kali and Windows;
  - CI green.

### P2 File player (`...-player-p2-file-player.md`), needs P0, P1, S1

- Scope:
  - `player_engine.py` (video, `X11ErrorGuard`), `player_core.py`, `player_settings.py`,
    `player_panel_tk.py`, `ui_strings_player.py` (player keys);
  - `platforms.reveal_in_file_manager`;
  - GUI wiring: panel build, F1 preview and removal, transport, seek bar, volume,
    snapshot, open folder, playlist popup, fullscreen, keyboard, mouse, focus, theme and
    language hooks, the VO chain, release before jobs (3.6), the close sequence (6.4).
- Acceptance (method in brackets):
  - mp4, mkv and webm preview on Kali X11 and on Windows 11: median of 10 selections
    under 1 s from `<<ListboxSelect>>` to the first `video-params` observation, with the
    player already ready [monotonic stamps in a debug log line];
  - every transport button and its key (space, Left/Right, Up/Down, m, f, Escape, s, o,
    n, p) does its action [Tk test with `InMemoryBackend`; manual on real mpv];
  - mouse: a click toggles pause once, a double click toggles fullscreen and leaves pause
    unchanged, a wheel notch changes the volume by 5 [`test_player_real_x11` on Xvfb;
    manual on Windows];
  - focus: space in the URL box types a space and does nothing in the player; space on a
    focused Start button does not toggle play; Left on the focused volume slider does
    not seek; Tab reaches every player control with a visible focus ring [Tk tests;
    manual];
  - playlist popup: both groups, load by double click and Return, Results disabled
    while a job runs [Tk test];
  - snapshot writes a PNG in the Videos folder, a second one gets `_2`; open folder
    opens the folder (Linux) and selects the file with a path containing spaces
    (Windows) [manual];
  - fullscreen enter/exit on both monitors of this machine [Xvfb plus manual when
    allowed];
  - VO chain: a `player_vo_profile` not in `vo_profiles_ok` is skipped; on an Xvfb
    without EGL the `x11egl` failure is detected, `restore()` runs, the fallback works
    (in-process if S1-X passed, else the restart message), and the process survives
    [opt-in real test];
  - reflow at 360, 460 and 700 px hides exactly the planned controls [Tk test];
  - a theme switch recolours the controls live while the video stays black; a language
    switch relabels every control and tooltip [Tk test plus screenshot];
  - with libmpv absent, the placeholder states the reason and Install works (Linux
    pkexec, Windows per-user);
  - removing the previewed file from the Input list stops it and lifts the placeholder
    [Tk test];
  - 20 closes during playback, each under 2 s [log stamps];
  - no Tk call on the mpv thread [bridge tests plus a review of every callback];
  - Wayland: GNOME embeds (S5 PASS) or shows the X11 message;
  - Windows item: the preview, transport, keyboard, mouse and close checks above on
    Windows 11 at 100 % and 150 % DPI;
  - GUI file growth within budget; CI green.

### P3 Job integration (`...-player-p3-job-integration.md`), needs P2

- Scope:
  - `JobOutput` plumbing and `_on_job_outputs` (F2);
  - `keep_original_audio`, `mux_video(original_audio_input=)` and the lip-sync re-mux
    (per Q3);
  - A/B (F3);
  - subtitles and toggle;
  - editor `on_seek`/`on_change`, source preview with live-updated subtitles, placement
    (F4), `_editor_open`;
  - the Settings "Player" section with `opt_player_autoload`, `opt_keep_original_audio`
    and the credits footer;
  - CLI `--no-original-audio`.
- Acceptance (method in brackets):
  - after a local job, a URL job and a URL job with lip sync on a source with background
    music, the output loads paused before the completion dialog [manual, log order];
  - each output has two audio streams titled Dubbed (default) and Original [ffprobe];
    the lip-sync output's dubbed track carries the music: in a 5 s music-only passage
    its RMS is within 6 dB of the Original track's [ffmpeg `astats`];
  - A/B keeps the position: over 10 switches per output, the valid `time-pos` after
    `playback-restart` minus the value before, corrected for elapsed time, is within
    0.3 s [bridge log]; an older single-track output whose source still exists uses the
    external audio;
  - `opt_player_autoload` off: nothing loads; a batch of 3 files fills the playlist with 3
    results and loads the first [manual];
  - CLI `--no-original-audio`: one audio stream [ffprobe];
  - the subtitles toggle hides and shows at once; without an SRT the toggle is disabled
    with its tooltip [Tk test];
  - editor: clicking a row seeks the player (valid `time-pos` within 0.1 s of the row
    start), an edit updates the on-screen subtitle within 1 s [bridge log, screenshot];
    confirming or cancelling a URL editor leaves no temp file [file listing];
  - editor placement stays on screen at 900x600 and on the 1080x1920 portrait monitor
    [screenshot];
  - re-running the same job while its output is loaded succeeds on Windows [Windows
    item];
  - the AAC encode of the Original track of a 30 min job takes under 60 s on the
    i7-10700K [log stamps];
  - the extended worker tests are green.

### P4 Real-time translation of local files, subtitles (`...-live-p4-files.md`), needs P2 (not P3, not S2)

- Scope:
  - `live_health`, `live_segment`, `live_asr`, `live_translate` (with Marian routes);
  - `live_sync` (the `FilePacer` part);
  - `live_scheduler` (captions);
  - `live_session` (file source);
  - `live_bar_tk` (idle and running rows);
  - the player button and its disabled tooltips;
  - the live keys in use, `ComponentInstaller` for live dependencies;
  - exclusivity with jobs, the editor and installs, the online-engine warning, the Marian
    consent and pivot banner, the CPU fallback.
- Caption timing method (used by P4 and P6): for every caption the scheduler logs
  `seg.start` and the media time `clock.now` at which `ShowSubtitle` ran, both in session
  time; offset = shown minus start.
- Acceptance:
  - a 10-minute EN to IT file in Delayed mode: after the pre-roll, p90 caption offset
    <= 0.3 s over all captions (at least 20); in Live mode, median offset <= 2.5 s on the
    GPU [caption log];
  - the `live_file_ahead_s` slider changes the pre-roll (4 s and 20 s runs) [log];
  - seeking back inside the covered region makes no new ASR or MT call [log counters];
  - `mt_429` faults: the banner with "Switch to MarianMT", italic source text, playback
    never paused by the fault; the switch works [fault injection];
  - `cuda_oom` fault: the banner, the session continues on the CPU, the delay rises by
    3 s [fault injection];
  - Ollama engine: 5 minutes of captions, then Stop unloads the model (`ollama ps`);
  - Google or DeepL selected: `live_warn_online_engine` before and at start;
  - auto source language: locks within 30 s on an IT and a JA sample; a mixed-language
    sample ends with `live_err_need_source_lang` [manual];
  - hallucination filter: a 60 s music-only passage produces no caption [manual plus
    unit test];
  - `FilePacer` Live mode never pauses [log];
  - exclusivity: job then live gives `live_err_busy`; live then job gives
    `live_err_busy_job`; the editor open disables the live buttons with
    `live_err_editor_open`; a startup pip install gives `live_err_busy_install` [Tk
    tests plus manual];
  - Marian routes: a direct pair (en to it), a `tc-big` pair (en to pt), a group pair
    (en to pl) and a pivot pair (it to pt) each translate a 2-minute file; the pivot
    shows `live_info_marian_pivot` [manual];
  - Stop returns VRAM to baseline +-100 MB (`nvidia-smi`) and no `live-*` thread is left
    [log, `threading.enumerate()` dump];
  - MarianMT is the default;
  - Windows item: the same 10-minute file in Delayed mode on Windows 11 from the pythonw
    shortcut, including a Marian model download: captions appear, the download progress
    reaches the log, Stop is clean and the session dir is removed;
  - CI green.

### P5 Live dub on local files (`...-live-p5-dub.md`), needs P4 and S3

- Scope:
  - `live_tts` (silence measurement, duration model);
  - the voice backend;
  - duck channel selection (AfDuck on >= 0.37, VolumeDuck otherwise);
  - the dub part of `DubScheduler` (duck latency, voice lead);
  - A/B as dub on/off;
  - lead calibration.
- Voice timing method: per clip the log records `seg.start`, the StartClip media time and
  the calibrated `voice_lead`; error = StartClip time + `voice_lead` - `seg.start`; 5
  clips per run are also checked against a loopback recording.
- Acceptance:
  - GPU, Delayed mode: at least 90 % of sentences voiced inside their slot, and
    |error| <= 150 ms for at least 90 % of 20 sampled clips; the 5 loopback clips agree
    with the log within 50 ms;
  - no overlapping clips [log];
  - ducking: the duck is complete before the voice onset on the 5 loopback clips; the
    operator's listening test on 3 minutes of speech recorded PASS or FAIL;
  - VolumeDuck: the same run with the fault `VTAI_LIVE_FAULTS="afduck_off"` passes, and
    moving the volume slider during the session never makes the level jump back [log of
    `volume` writes: one writer];
  - mute silences both instances, unmute restores both;
  - network off (firewall): captions continue with `live_warn_tts_unavailable` and
    recover within one breaker cooldown after the network returns;
  - pause and seek keep sync (the error rule holds on 5 clips after a seek);
  - seeking back replays clips without new Edge requests [log];
  - A/B "Original" stops the dub and unducks within 0.3 s [log];
  - the duration model converges: after 10 clips the median |estimate - audible| is at
    most 15 % for en and ja [log];
  - Windows item: 10 minutes EN to IT with the dub on Windows 11 (WASAPI): at least 80 %
    voiced in slot, clean Stop.

### P6 Live streams (`...-live-p6-streams.md`), needs P5 and S2

- Scope:
  - `live_store` (with the transport chosen by S2, raw ctypes registration);
  - `live_source` (selector, codec probe, ffmpeg version gate);
  - the stream parts of `live_session`;
  - `EdgeEstimator` and `DelayController`;
  - the delay slider, the lag indicator, the live seek-bar rendering;
  - "Watch live";
  - reconnect policy, VOD backpressure, disk checks, stale cleanup with `pid_alive`.
- Acceptance:
  - YouTube live and Twitch live, 60 min each in Delayed mode: lag within target +-1 s
    outside stalls, and at most 1 controller action per 10 s in steady state [log];
  - median caption offset <= 0.5 s [caption log, P4 method];
  - Live mode stays at L with zero `paused-for-cache` in steady state for 20 min [bridge
    log];
  - mode switching both ways, no backward seek [log];
  - a 20 s network pull recovers through `live_status_reconnecting` [manual];
  - an ended stream reaches `ended`;
  - disk stays under the cap [`du` of the session dir every minute];
  - a 2-hour YouTube VOD URL: the store never runs more than 256 MiB ahead of its readers
    [log];
  - `live_err_codec` for a stream whose codecs stay unknown or incompatible (a VP9-only
    source or a manual harness), before ffmpeg starts;
  - `live_err_upcoming` for a scheduled YouTube live;
  - Twitch ad break: behaviour recorded in the manual matrix (not pass/fail);
  - 12 h cap: unit test with fake PTS (no 12 h run);
  - the session folder is removed on Stop on Windows and Linux;
  - two instances: a second instance's session start never removes the first one's
    session dir [manual, Windows and Linux];
  - close during live takes at most 6 s;
  - "Watch live" and Download wrap in German and Finnish [screenshots];
  - Windows item: a YouTube live, 20 min in Delayed mode on Windows 11.

### P7 Parity pass and documentation (`...-player-p7-parity.md`)

- Scope:
  - the full manual matrix (7.6), including VirtualBox without 3D, Wayland, HiDPI and
    the 0.34/0.35 containers;
  - fixes found;
  - the README user guide (player, live mode, privacy, limits);
  - `_dev/CHANGELOG.md`;
  - the copy of the approved design to `docs/superpowers/specs/`;
  - a native-quality review of the new keys in 26 languages.
- Acceptance, must-pass floor ([CC] 7): these cells may not become "known limits":
  - Windows 10 and Windows 11: file playback, A/B, subtitles, snapshot, open folder,
    fullscreen, close under 2 s;
  - Windows 11: one local-file live session with the dub and one YouTube live session,
    10 minutes each, clean Stop;
  - VirtualBox guest without 3D: playback through `d3d11-warp`, or the documented
    `player_err_video_output`; never a crash;
  - Kali X11: P2-P6 end to end;
  - one Wayland desktop (GNOME or KDE): embedded playback, or the "X11 session required"
    message.
  Every other cell is recorded as pass or known limit (with an issue); CI green on 3.11
  and 3.12.

---

## 10 Open questions for the operator (decisions only)

Q1 (red zone, licence). Which Windows libmpv build, from where?
- Options:
  - L1: zhongfly LGPL latest, verified by the GitHub digest;
  - G1: shinchiro GPL, pinned on SourceForge with a SHA in the repo;
  - L2: a vetted LGPL DLL re-hosted in our own GitHub release (we then carry the source
    obligations).
- Recommended: `WINDOWS_LIBMPV_SOURCES = (L1, G1)`. L1 is primary (LGPL hygiene keeps
  future bundles open; the load check catches a broken nightly; BUILD.txt records what
  each user got). The pinned G1 is the fallback, used only if every L1 candidate fails,
  so installs stay reproducible when zhongfly or the API is down.
- If reproducibility matters more than licence hygiene, reverse the order. Avoid L2.
- In both cases the project conveys nothing, as with ffmpeg today.
- New fact ([CT] C10): both sources ship mpv MASTER snapshots (the pinned shinchiro build
  reports `mpv v0.41.0-1050-ge76a35ec9`; zhongfly builds daily). S4 therefore tests the
  pinned snapshot and the newest zhongfly build, and BUILD.txt records the commit each
  user received. A Defender quarantine seen in S4 reopens this question.

Q2. Download the Khronos Vulkan loader when a machine lacks `vulkan-1.dll`?
- Recommended: yes, installer and per-user install only, into a separate folder, and used
  only when System32 lacks the loader.
- Without it libmpv cannot load on VMs and on machines without a vendor driver ([06] 4.1;
  shinchiro issue #831).

Q3. Every new dubbed MP4 keeps the original audio as a second, non-default track
(`keep_original_audio`, default on; off in Settings or with `--no-original-audio`).
Lip-synced outputs are re-muxed with the full dubbed mix instead of Wav2Lip's vocals-only
audio.
- Recommended: yes to both.
  - Without the second track, A/B is impossible for URL jobs, whose source is deleted.
  - The lip-sync change fixes the verified loss of background music.
- Cost: about 1.2 MB per minute (160 kbit/s AAC) and one AAC encode per job (27 s for
  30 minutes of stereo audio on this i7-10700K, [CT] C42 RUN).

Q4. Should live mode be exclusive with dubbing jobs in v1?
- Recommended: yes. Whisper, Demucs, XTTS and Ollama together can exhaust VRAM and break
  the latency budget ([05] 9.7). The lock is two flags and can be relaxed later.

Q5. Player and live strings in a separate module (`ui_strings_player.py`) merged into
`UI_STRINGS`?
- This changes the "all strings in the GUI file" convention.
- Recommended: yes, with the collision check as a TEST (`merge_into` itself never
  raises, [CC] G27). Otherwise the GUI file grows by about 3,200 lines (122 keys x 26
  languages). `UI_STRINGS` stays the single runtime dict, and the existing tests keep
  working (they read `legacy.UI_STRINGS` from the imported module at run time,
  tests/test_ui_i18n_coverage.py:5,10, [CC] 4).

Q6. May the GUI download libmpv per user on Windows (about 30 MB, after explicit consent)
when the installer step failed or was skipped?
- Recommended: yes. It mirrors deno's Tier-2 behaviour (js_runtime.py) and avoids
  "re-run setup as admin" as the only way out.

Q7. How prominent should the live-mode privacy notice be? Edge-TTS sends the translated
text to Microsoft; Google and DeepL send the source text.
- Recommended: a permanent info icon with a tooltip in the LiveBar, plus the non-modal
  banner when an online engine is selected. No blocking dialog.

Q8. Default sync mode and delay.
- Recommended: "Delayed video".
- D = 12 s on GPU and 15 s on CPU with the dub (9 s / 11 s subtitles only); slider
  6-30 s.
- Local files: the same slider sets the translated lead kept ahead of the playhead
  (`live_file_ahead_s`, default 8 s with the dub, 4 s subtitles only, range 4-30 s). The
  draft had no adjustable value for files ([CC] G7); this reading follows the
  requirement's "adjustable number of seconds" literally at almost no cost.
- Automatic raise on (never lowers).

Q9. Auto source language with MarianMT in live mode.
- Recommended: allowed. The language locks after 5-30 s of speech, and lines before the
  lock show untranslated in italics. If the route is not cached, ask to download it
  (298-343 MB per opus-mt model, 464 MB per `tc-big` model where measured, [CT] C39; two
  models for a pivot). No lock after 60 s of speech stops the session with
  `live_err_need_source_lang`.

Q10. The dub always needs the network (Edge-TTS), even when Whisper and Marian are local.
Is that acceptable for "local by default"?
- Recommended: yes, with the privacy notice (Q7).
- An offline live voice (XTTS, Piper) is a v2 candidate.

Q11 (scope). Two useful changes found during the design are outside the player
([CC] G24; project rule "Non aggiungere feature non richieste"):
- moving `_install_ffmpeg_linux` (:5810) onto `system_packages`, which removes its
  `pacman -Sy` partial upgrade ([03] 1.5);
- making the Windows uninstaller delete all of `%LOCALAPPDATA%\VideoTranslatorAI` (the
  deno bin, the 416 MB Wav2Lip fallback, caches), a pre-existing gap ([03] 1.8).
- Recommended: keep both OUT of this project and log them as separate backlog items. The
  design already assumes this: the uninstaller removes only the `mpv-runtime` subfolder
  it adds, and the ffmpeg installer is untouched.

Q12. MarianMT pivot through English when no direct or `tc-big` model exists for a pair.
- Facts: direct models are missing for many pairs (it->X exists only for ar, de, en, es,
  fr, sv, uk, vi; X->it only for ar, de, en, es, fi, ja, uk, vi, zh; en->ja, ko, no, pl,
  pt, tr need `tc-big`, group or Tatoeba models, [FD] table in 4.9). Every project
  language has an X->en and an en->X route.
- Options: (a) pivot allowed, with the banner `live_info_marian_pivot`; (b) no pivot:
  those pairs give `live_err_marian_pair` and the user must pick Ollama or an online
  engine.
- Recommended: (a). Without it, "local by default" fails for most pairs involving
  Italian, the operator's main language. Cost: two downloads and about twice the MT
  latency (still under 0.2 s p95 on the GPU). Pivot quality is UNVERIFIED; P4 reviews
  one pivot pair by ear and eye.

Q13. Lowest supported libmpv on Linux ([CC] G11).
- Facts: python-mpv imports with API >= 1.108 (mpv 0.33); Ubuntu 22.04 ships libmpv1
  0.34.1 (Launchpad, [CT] R6) and is still in standard support (until 2027, UNVERIFIED
  here); AfDuck needs 0.37, so 0.34-0.36 always use
  VolumeDuck; the draft tested only 0.35 and 0.41.
- Options: (a) `TESTED_FLOOR = (0, 34)`, conditional on the S1 (f) and S3 (2) container
  checks on 0.34.1; (b) `TESTED_FLOOR = (0, 35)` (Debian 12 and newer only).
- Recommended: (a), falling back to (b) automatically if the 0.34.1 checks fail.

Q14. CI coverage of the Tk tests ([CC] T1).
- Facts: every Tk test skips in CI today (no display, `tests/test_ui_theme_tk.py:9-17`),
  so P0, P2 and P4 GUI regressions are guarded only by local Xvfb runs.
- Options: (a) keep CI as is, local Xvfb runs are a phase gate (already in 9); (b) add a
  second CI job on ubuntu-latest that installs `xvfb` with apt and runs only the
  `*_tk` tests under `xvfb-run` (Python 3.12). Whether the setup-python build's tkinter
  works under Xvfb on the runner is UNVERIFIED.
- Recommended: (b) in P2, with (a) as the fallback if the job is flaky. It changes the CI
  configuration, hence an operator decision.

---

## 11 Verified claims and residual risks

### 11.1 Claims and their final status

Every technical claim the design depends on, with its status after the two critiques and
the [FD] checks.
- Status values: CONFIRMED (RUN or SRC as stated), PARTLY (confirmed in one setting, the
  rest open), REFUTED (the draft was wrong; the correction is already in this design),
  UNVERIFIED (neither run nor primary source; a spike or phase item settles it).
- "Settled in": the spike item (9, Plan 0) or phase acceptance that closes it.
- "If false": the pre-specified fallback.
- Sources: [CT] = critique-technical.md (probe scripts under `probe/`), [CC] =
  critique-completeness.md, [FD] = checks of this final design (preamble).

Claims C1-C49 (from the draft):

| # | Claim | Used in | Final status and source | Settled in | If false |
|---|---|---|---|---|---|
| C1 | mpv `wid` embedding in a Tk frame on X11 works and mpv resizes its child | 3.1 | CONFIRMED: RUN [CT] p10 (Xvfb, `vo=x11`, child `("x11" "mpv")` resized 640x400 -> 900x560); SRC `x11_common.c:1262-1266, 1778-1788` (v0.41.0). GPU VOs not run | S1 (a) with `x11egl` | render API (v2); stop at S1 |
| C2 | Under Wayland, Tk on XWayland with `gpu-context=x11egl` stays embedded | 3.1 | UNVERIFIED (no Wayland session here; third-party report only, [04] 4.2) | S5 | "X11 session required", explained in the placeholder |
| C3 | A Tk sibling placeholder stacks above mpv's child and can be lowered | 2.3 | CONFIRMED on X11: RUN [CT] p10 (centre pixel = placeholder colour when lifted, video when lowered). Windows d3d11 flip model UNVERIFIED | S4 (3) | `d3d11_flip=no`; else idle logo via `osd-overlay` |
| C4 | `register_key_binding` (define-section) delivers MBTN/WHEEL on 0.41 | 3.1, 3.7 | CONFIRMED: RUN [CT] p1 (keypress) and p11 (real xdotool clicks); no deprecation warning at loglevel v; documented deprecated "except for mpv-internal uses" in 0.34, 0.35, 0.41, master | S1 (f) on 0.34/0.35 | `keybind` + `script-message` in the adapter |
| C5 | `terminate()` on a helper thread while Tk pumps never hangs | 6.4 | PARTLY: RUN [CT] Linux 10 ms; Windows UNVERIFIED; issue #114 open (https://api.github.com/repos/jaseg/python-mpv/issues/114); `__del__` risk closed by single ownership (mpv.py:1153-1155, 1163) | S1 (c), S4 (4) | longer bounded wait, destroy anyway (daemon thread) |
| C6 | `force_window=yes` keeps Tk's X error handler until exit | 3.1 | REFUTED: RUN [CT] p10 (mpv's handler from the first VO init, Xlib default after terminate); SRC `x11_common.c:697, 914`, tkError.c:24,102-104. Corrected by `X11ErrorGuard` (C50) | S1 (d) | no in-process VO re-creation; restart message |
| C7 | `d3d11-warp` works in `wid` mode on a VM without 3D | 3.1 | UNVERIFIED; the Linux build rejects the options (RUN [CT]), emitted only on win32 | S4 (5) | `player_err_video_output` (documented) |
| C8 | `vulkan-1.dll` is a hard import and the LunarG loader satisfies it | 8.3 | PARTLY: hard import CONFIRMED (objdump RUN [CT], empty delay-import directory); archive and DLL hashes CONFIRMED (RUN [CT]); member path CORRECTED to `VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll`; absence on VMs UNVERIFIED (shinchiro issue #831 open) | S4 (5) | `player_vulkan_missing` |
| C9 | The renamed `mpv-2.dll` in a prepended PATH dir is found first | 2.2, 8.3 | CONFIRMED by SRC: python-mpv tries `mpv-2.dll`, `libmpv-2.dll`, `mpv-1.dll` over PATH (mpv.py:39-45); CPython nt `find_library` returns the first PATH hit (ctypes/util.py 49-62); dependencies resolve via `add_dll_directory`, never PATH ([CT] C9). Not run on Windows | S4 (2) | narrow PATH while no job runs |
| C10 | Licence of the Windows builds (zhongfly LGPL; shinchiro effectively GPL) | 8.4, Q1 | facts CONFIRMED ([06] 1.2; shinchiro pin = `mpv v0.41.0-1050-ge76a35ec9`, a master snapshot, [CT]); the legal conclusion UNVERIFIED | operator (Q1) | switch the source order (data only) |
| C11 | Fetching third-party GPL/LGPL binaries at install time is not distribution by the project | 8.4 | UNVERIFIED legally (reading of the FSF FAQ, [06] 6.3) | operator | re-hosting (L2) with source obligations, or no Windows player |
| C12 | Defender / Smart App Control accept the unsigned DLL | 8.3 | UNVERIFIED ([06] 5) | S4 (recorded) | pinned build first; reopen Q1 |
| C13 | Custom stream over a growing store: blocking read, cancel from another thread, size None, playback past the end, delayed start | 4.6, 5.3 | CONFIRMED with corrections: RUN [CT] p5, p6, p7, p13 (paused load buffers ahead; cancel from `Dummy-N` about 0.1 s after stop). Corrections applied: seek return ignored except its sign, `b""` = permanent EOF, size only at open, close after `idle-active`, relative positions (4.6) | S2 | candidate A, then C |
| C14 | `lavf://file:` + `follow=1` plays a growing file and stops promptly | 4.6 | CONFIRMED on Linux: RUN [CT] p9 (stop to idle 6 ms, terminate 0.107 s); Windows path syntax UNVERIFIED | S2 (9) | candidate B or C |
| C15 | A local HLS EVENT playlist is seekable | 4.6 | CONFIRMED by SRC: n8.0 `hls.c:1098-1102`, same logic in n4.4, n5.1, n6.1 (the draft's cite was wrong) ([CT]); not run | S2 (only if B and A fail) | no stream support on that platform |
| C16 | Forward seeks inside the demuxer cache work on the custom stream | 5.3, 5.4 | CONFIRMED: RUN [CT] p6 (target `demuxer-cache-time - 1.0` reached +0.04 s); `time-pos` transiently clamped during the seek (handled, 4.3) | S2 (2) | reload at a `SeekIndex` offset |
| C17 | Raw domain: mpv `time-pos` equals PyAV PTS within 50 ms | 4.3 | CONFIRMED within tolerance: RUN [CT] (1001.400 vs 1001.379, a systematic 21 ms A/V start offset) | S2 (4) re-check | one-time offset measurement |
| C18 | Files: rebased `time-pos` equals PyAV `pts - start_time` | 4.3 | CONFIRMED within tolerance after the units fix: RUN [CT] (0.0213 vs 0.0); `start_time` is in microseconds (REFUTED formula corrected); cite corrected to `demux_lavf.c:1138-1139` | done | one-time offset measurement |
| C19 | `demuxer-cache-time` is in the `time-pos` domain and tracks the edge | 5.2 | CONFIRMED: RUN [CT] p5/p6 (1003.80 .. 1010.92) | done | `edge.observed` only |
| C20 | `-output_ts_offset` restarts keep PTS monotonic and mpv plays across the gap | 4.5 | PARTLY: RUN [CT] on a concatenated TS (+2.44 s gap: no stall, `time-pos` jumps by the gap); handled as a discontinuity (4.11); a real ingest restart not run | S2 (6) | player reload at the gap |
| C21 | Segment bursts are 2-6 s apart | 5.4 | PARTLY: RUN [CT] YouTube live 5 s segments, 720 per playlist; Twitch UNVERIFIED | P6 log | clamp covers 2-8 s; above 8 s live mode may stall (documented) |
| C22 | Manifest URLs expire after about 6 h | 4.5 | CONFIRMED: RUN [CT] (`expire` = now + 6.00 h on YouTube live) | done | re-resolve on 403/404/410 |
| C23 | Twitch ad breaks give PTS discontinuities that ffmpeg smooths above 10 s | 4.5, 6.2 | UNVERIFIED (SRC `-dts_delta_threshold`, [05] 2.2) | P6 manual | discontinuity path |
| C24 | `-reconnect*`/`-rw_timeout` reach HLS segment fetches | 4.5 | REFUTED for `-reconnect*` (removed), CONFIRMED for `-rw_timeout` by SRC (aviobuf.c:993-994, hls.c:2136,1409-1415 at n8.0, [CT]); `-seg_max_retry` gated on FFmpeg >= 6 | done | `IngestPolicy` stall detection |
| C25 | A VOD ingest blocked on a full pipe survives server idle timeouts or recovers with `-ss` | 4.5 | UNVERIFIED | P6 (2 h VOD) | disable VOD backpressure, let the cap evict |
| C26 | Windows allows reading a chunk while another handle writes it; deletion after close | 4.6 | UNVERIFIED (CPython opens with `_wopen`, fileio.c:387; share mode not stated in the MS doc, [CT]) | S2 (9) with S4 | explicit share mode via `msvcrt`/`os.open` |
| C27 | ctypes stream callbacks are not starved (read p99 < 20 ms) | 4.6 | REFUTED for python-mpv's helper (byte loop, RUN [CT]: 10-16 ms per 128 KiB); corrected by the raw memmove registration (0.003 ms per copy); the new path under load UNVERIFIED | S2 (5) | candidate A |
| C28 | Two libmpv instances in one process | 4.13 | CONFIRMED headless: RUN [CT] (both advanced about 1.1 s in 1 s; voice start 0.146 s with `ao=null`); real outputs UNVERIFIED | S3 (1) | subtitles only; voice through lavfi-complex (v2) |
| C29 | `af=@vtduck:lavfi=[...]` and `af-command vtduck volume <g>` work on 0.35 and 0.41 | 4.13 | REFUTED: RUN [CT] p1-p3 (-12 without target on 0.41; no target argument before 0.37). Label syntax CONFIRMED. Corrected: target `volume` on >= 0.37, VolumeDuck below | S3 (2) | VolumeDuck |
| C30 | A duck change is heard about 0.2 s later | 4.11 | REFUTED as a derivation (`audio-buffer` is a minimum): RUN [CT] p4 0.19-0.39 s with `ao=pcm`; corrected: `duck_latency_s` measured per platform | S3 (3) | duck earlier (harmless) |
| C31 | Voice start latency from a preloaded clip is stable for +-150 ms | 4.11 | UNVERIFIED; leading silence (0.16-0.21 s, RUN [CT]) now skipped | S3 (5), P5 | `gapless-audio` + append; widen the target |
| C32 | scaletempo2 is inserted automatically when `speed != 1` | 4.11, 5.3 | CONFIRMED: RUN [CT] ("adding scaletempo2" at 1.03 on 0.41); 0.34.1/0.35.1 docs agree | done | explicit `af` scaletempo2 |
| C33 | Switching `aid` is gapless enough for A/B | 3.4 | UNVERIFIED audibly (position kept: RUN [04] 7) | S3 (6), P3 | documented short gap |
| C34 | Edge clip duration = bytes / 6000 | 4.10 | CONFIRMED: RUN [CT] (it, en, ja, exact to the ms); includes 0.26-0.84 s trailing silence (handled); timeouts must be int (handled) | done | tiny mp3 frame parser |
| C35 | `estimate_tts_duration_s` fits Edge voices | 4.10 | REFUTED: RUN [CT] +2 % it, -30 % en, -59 % ja; corrected by `EdgeDurationModel` (C70) | P5 | speed clamp absorbs the error |
| C36 | Edge-TTS sustains one request every 3-5 s for hours | 4.10 | UNVERIFIED; throttling and blocks reported (edge-tts issues #347, #452 503, #458 403, https://api.github.com/repos/rany2/edge-tts/issues/347) | P6 long sessions | breaker, subtitles-only degradation |
| C37 | A stateful wrapper drives faster-whisper's Silero ONNX frame by frame | 4.7 | CONFIRMED: RUN [CT] (with a remainder buffer: max abs diff 0.0 over 625 frames; helpers `get_vad_model`, `get_assets_path`) | done | `get_speech_timestamps` on a rolling window |
| C38 | Language detection locks correctly with the 0.8 / 5 s / 30 s rule | 4.8 | UNVERIFIED; fallback now has a key (`live_err_need_source_lang`) and a 60 % / 60 s rule | P4 | explicit source language |
| C39 | `opus-mt-{src}-{tgt}` exists for each pair, about 300 MB | 4.9 | REFUTED: HF API ([CT], [FD] table); sizes 298-343 MB, 464 MB for tc-big; corrected by routes and pivot (Q12) | P4 | `live_err_marian_pair`, suggest Ollama |
| C40 | libass renders CJK, Arabic, Hindi and Thai with default fonts | 4.12 | UNVERIFIED (the overlay renders at `osd_level=0`: RUN [CT] p14) | P4 manual | `osd-font` per script |
| C41 | mpv's Windows share mode would block `ffmpeg -y` over a loaded output | 3.6 | moot by release-before-job; for files on Linux the fd closes 2-7 ms after `stop`, before `idle-active` (RUN [CT] p8); NOT true for `vtlive` (closed Event used) | S4 (Windows files) | n/a |
| C42 | The AAC re-encode of the original costs well under a minute for 30 min | 3.4, Q3 | CONFIRMED on this CPU: RUN [CT] 27 s | P3 log | stream copy when the source is AAC |
| C43 | Tk and libmpv are both DPI-unaware on Windows | 3.1 | SUPPORTED by SRC (`w32_common.c` only queries DPI, 198-206, 667-689; python.manifest declares only longPathAware; no `SetProcessDpiAwareness` in the repo); not run | S4 (6) | document a soft picture |
| C44 | Linux WMs honour the editor position | 3.5 | UNVERIFIED | P3 | the user moves it |
| C45 | `explorer /select` opens and selects; return codes ignored | 3.7 | UNVERIFIED (now built as a native command-line string, C71) | S4 (10) | `os.startfile(dir)` |
| C46 | The GitHub asset `digest` is present for zhongfly releases | 8.3 | CONFIRMED today for the 3 newest releases (RUN [CT] via the API); future presence UNVERIFIED; integrity against transport errors only | P1 | `sha256.txt`, then the pinned G1 |
| C47 | SourceForge serves the 7z to Python urllib | 8.3 | CONFIRMED from Linux with the exact client and UA (RUN [CT], hashes match); Windows UNVERIFIED | S4 (7) | GitHub mirror; content-type check |
| C48 | openSUSE ships `libmpv2` | 8.2 | CONFIRMED: Tumbleweed 0.41.0+git20260918, Leap 15.6 0.36.0 backports ([CT]) | done | generic `{cmd}` hint |
| C49 | The VO failure log strings reliably signal a VO failure | 3.1 | CONFIRMED as strings and path: RUN [CT] without a display (`MPV()` does not raise, audio-only playback continues, `video-params` None); both strings in the Windows DLL | S1, S5 | hidden "Change video output" command (v1.1) |

Claims introduced by the final design (C50-C73):

| # | Claim | Used in | Final status and source | Settled in | If false |
|---|---|---|---|---|---|
| C50 | `X11ErrorGuard.restore()` (ctypes `XSetErrorHandler`) restores Tk's handler and keeps the process alive after a VO uninit | 2.2, 3.1, 6.4 | UNVERIFIED as a fix; reading the pointer RUN [CT] | S1 (d) | no in-process VO re-creation on Linux; `player_restart_required` |
| C51 | While mpv's VO is alive (mpv's X error handler installed, Tk's per-request handlers not running) Tk works normally in this app | 3.1 step 5 | UNVERIFIED | S1, P2 soak (the 20-close and theme/language checks) | render API (v2); nothing else can keep both handlers |
| C52 | mpv's `XInitThreads()` at VO init, after Tk opened its display, is harmless | 3.1 | harmless with libX11 >= 1.8 per [CT] (UNVERIFIED on older libX11, possibly Ubuntu 22.04) | P7 on an Ubuntu 22.04 desktop if Q13 keeps 0.34 | `TESTED_FLOOR = (0, 35)` |
| C53 | A raw ctypes `vtlive` registration through `mpv.backend` and `MPV.handle` works on python-mpv 1.0.6-1.0.8 | 2.2, 4.6 | SRC (mpv.py:55,73 `backend`; :505-520 types; :617 and :1913 the add call); not run | S2 (B) | python-mpv's helper (byte loop), then S2 (5) likely picks A |
| C54 | The probe subprocess can validate each VO profile's options on an uninitialised handle and read `mpv-version` after initialising with `vo=null` | 2.2, 3.1 | PARTLY: an invalid `gpu_context` fails at option-set time (RUN [CT] finding 2); reading `mpv-version` UNVERIFIED | P1 acceptance | read the version from `mpv_client_api_version` mapping only; validate profiles in-process under `try` and accept the leak once |
| C55 | mpv emits `playback-restart` after every seek and load, also on `vtlive` | 2.2, 4.3, 4.11 | SRC (event id 21, mpv.py:305; input.rst); not run for this purpose | S1 (f), S2 (2) | validity from `seeking` plus a 300 ms settle timer |
| C56 | The mouse state strings (`dm-`, `um-`, `p--`) are the same on 0.34-0.41 and on Windows | 3.7 | RUN on 0.41 X11 only ([CT] finding 14) | S1 (f), S4 (9) | per-version table in `mouse_action` |
| C57 | Button/Radiobutton/Scale class bindings double-fire with a toplevel `<Key>` binding | 3.7 | SRC (button.tcl:104-112, ttk/button.tcl:23,42-43, ttk/scale.tcl:29-33, bindtags man page, [CC] G5); not run | P2 Tk test | n/a (the filter is then only stricter than needed) |
| C58 | Under pythonw the original `sys.stdout`/`sys.stderr` are None, so `_GlobalRedirect` would raise on library writes | 1.3 R9, 2.4 | SRC (CPython Doc/library/sys.rst; video_translator_gui.py:5248-5252, 5711-5712, [CC] G2, [FD]); end to end UNVERIFIED | S4 (8) | n/a (the fix is harmless if the premise is false) |
| C59 | `refresh_import_paths` makes a package installed into a user site dir created during this run importable without a restart | 2.2, 6.1 | SRC (site.py:380, `importlib.invalidate_caches`); not run | P1 acceptance | `player_restart_required` |
| C60 | `pid_alive` (OpenProcess + GetExitCodeProcess) and `process_start_token` (GetProcessTimes, /proc stat) identify a live owner | 4.15 | UNVERIFIED on Windows (Win32 API behaviour from memory, not fetched); Linux `/proc/<pid>/stat` field 22 standard | S4 (11), unit tests | keep a dir whose owner state is unknown (never delete on doubt) |
| C61 | ffprobe identifies the codecs of formats 233/234 and of HLS playlists without CODECS within 20 s | 4.5 | UNVERIFIED | S2 (8), P6 | `live_err_codec` |
| C62 | Separate video (232) and audio (234) HLS inputs stay in A/V sync through `-c copy` into one TS | 4.5 | UNVERIFIED | S2 (7) | muxed `b[height<=H]` when offered, else refuse |
| C63 | `-seg_max_retry` is absent in FFmpeg 5.1 and present from 6.0 | 4.5 | SRC ([CT] R7: n5.1 hls.c lacks it, n6.0 has it) | unit test of the gate; P6 | drop the option |
| C64 | The Marian coverage table of 4.9 | 4.9 | RUN [FD] (Hub API, 2026-09-25); can change over time | P4 re-query; the resolver asks the Hub at run time | `live_err_marian_pair` |
| C65 | `opus-tatoeba-en-ja` loads with the Marian classes and translates usably | 4.9 | UNVERIFIED (exists on the Hub, [FD]) | P4 | en->ja (and pivots into ja) need Ollama or an online engine |
| C66 | The group models expose target tokens for Polish and Norwegian Bokmal in `supported_language_codes` | 4.9 | UNVERIFIED | P4 | no offline route for en->pl / en->no |
| C67 | Pivot translations through English are good enough for subtitles and dub | 4.9, Q12 | UNVERIFIED | P4 review, Q12 | disable pivots (Q12 option b) |
| C68 | `measure_silence` (PyAV, -45 dBFS) finds Edge's leading and trailing silence within 20 ms | 4.10 | silence durations RUN [CT]; the detector UNVERIFIED | P5 unit test with real clips, S3 (7) | fixed trims per voice measured once |
| C69 | The voice instance's `start` property skips the leading silence precisely | 4.11 | UNVERIFIED (mp3 seek accuracy) | S3 (7) | keep the silence and add `voice_start_s` to the lead |
| C70 | `EdgeDurationModel` converges within 10 clips to 15 % | 4.10 | UNVERIFIED | P5 | wider speed clamp (1.0-1.4) |
| C71 | `explorer /select,"<path>"` as one command-line string selects paths with spaces | 3.7 | UNVERIFIED | S4 (10) | `os.startfile(dir)` |
| C72 | setup-python's tkinter works under `xvfb-run` on ubuntu-latest | Q14 | UNVERIFIED | Q14 trial job | keep local Xvfb gates |
| C73 | The pinned shinchiro snapshot and current zhongfly builds behave like the 0.41.0 release for every command used | 8.3 | UNVERIFIED (master snapshots, [CT] C10) | S4 (1), (3), (9) | pin the source whose S4 run passes; reopen Q1 |

Already verified and needing no action:
- Wav2Lip muxes its `--audio` input (local `inference.py:276`);
- faster-whisper 1.2.1 requires `av>=11` and `onnxruntime<2,>=1.14` ([FD]);
- no locale-sensitive calls exist in the code base, and python-mpv sets `LC_NUMERIC=C`
  itself (mpv.py:62-68);
- `_on_done` argument assertions in the worker tests (`tests/test_ui_worker_outcomes.py:177,183`);
- the reserved colours `#000000`, `#a3a3a3`, `#c3c3c3` in `TK_DEFAULT_COLORS`
  (`videotranslator/ui_theme.py:43-49`);
- python-mpv `osd_overlay()` NameError and the working `command("osd-overlay", ...)` form;
  `escape-ass` from 0.38; mpv `fullscreen` is a no-op with `wid`; `--wid` cast to uint32
  on win32; the event thread is a daemon; `terminate()` joins without a timeout ([CT] 3);
- every 3.1 option other than `gpu_context=x11` is accepted by 0.41 ([CT] 3 RUN);
- repo anchors re-checked by both critiques and [FD] at `c155227`.

### 11.2 Residual risks (ranked)

1. Windows libmpv provenance. Both sources ship unsigned, unreleased mpv master
   snapshots (C73, C10); Defender or Smart App Control may quarantine them (C12); the
   licence conclusion is not legal advice (C10, C11). Mitigation: subprocess load check,
   BUILD.txt, S4 on both sources, Q1. Residual: a future nightly can break behaviour
   that S4 did not cover.
2. X11 error handling inside one process. While the VO lives, Tk's own X error handlers
   never run (C51); the restore after a VO uninit is unproven (C50); older libX11 may
   mind the late `XInitThreads` (C52). Mitigation: S1 (d), no in-process re-creation
   without proof, restart message. Residual: an X error in a Tk path that expects its
   own handler is only logged by mpv, with unknown effects.
3. YouTube live ingest fragility. The draft's selector already broke on today's YouTube
   formats ([CT] finding 3); split HLS inputs may drift apart (C62); audio codecs are
   unreported (C61). yt-dlp and YouTube change often, so the selector and codec probe
   need maintenance; Twitch is untested (C21, C23).
4. Live transport internals. Candidate B depends on python-mpv module internals
   (`backend`, `handle`, C53) and on GIL behaviour under GPU ASR load (C27, S2 (5));
   candidate A has no retention and an unknown Windows path syntax (C14).
5. Offline translation coverage and quality. en->ja depends on one Tatoeba model (C65),
   Polish and Norwegian on group tokens (C66), most Italian pairs on pivots whose
   quality is unknown (C67, Q12); every route costs 300-930 MB of downloads.
6. Real-device timing. Duck latency, voice start latency and the `aid` gap are measured
   only with `ao=pcm`/`ao=null` so far (C30, C31, C33); WASAPI and PipeWire may differ,
   and the per-platform offsets from S3 may not transfer between machines.
7. Edge-TTS is an unofficial Microsoft endpoint (C36): throttling, 403/503 blocks or a
   protocol change silence the dub (subtitles continue); there is no offline live voice
   in v1 (Q10).
8. Platform corners: Wayland (C2), VMs without 3D (C7, C8), Windows focus and DPI (C43,
   C56 on Windows), and the Windows-only helpers verified only by reading (C58, C60,
   C71).
9. Test coverage gaps: GUI behaviour is guarded by local Xvfb runs, not CI (Q14, C72);
   real mpv, audio and network behaviour are opt-in or manual.
10. Size. 18 new modules, a +300-line GUI budget, and 122 keys x 26 languages = 3,172
    strings that need native-quality translation (R7, P7 review); the delivery spans
    eight plans after the pending backlog work.
