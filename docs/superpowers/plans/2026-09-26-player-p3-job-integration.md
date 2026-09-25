# Integrated Player P3: Job Integration

**Status:** implementation in progress, local automated tests green. Manual
Linux/libmpv and Windows acceptance remains. See `_dev/CHANGELOG.md` for the live handoff.

**Goal:** feed translated artifacts into the integrated player's Results playlist; optionally
load the first result paused before the completion dialog; preserve source audio as a selectable
track; expose A/B audio and subtitle controls; preview and update subtitles while editing.

**Binding spec:** `docs/superpowers/specs/2026-09-25-video-player-live-design.md`, section 9,
P3 and section 3.4-3.6. P3 depends on P2.

## Implemented

- `JobOutput` normalizes the legacy `video` / `output` and `srt` result fields.
- GUI worker output handoff is connected for local batches, URL batches and editor phase 2.
  It adds results to the playlist and loads the first result paused when autoload is enabled.
- Player settings now include result autoload and original audio preservation. The settings
  dialog persists both options and has an mpv/libmpv credits footer.
- Output muxing embeds Dubbed (default) and optional Original audio. CLI supports
  `--no-original-audio`. Lip-sync re-muxes the synchronized video with the full dubbed mix.
- Player exposes A/B and CC controls. The subtitle editor loads a source preview, seeks to a
  selected row, reflects edits in the subtitle preview (500 ms debounce), clamps its placement
  to the screen and removes its temporary SRT at close.
- Added tests for result normalization, worker output-before-completion order, original audio
  ffmpeg maps, subtitle preview reload, editor geometry, CLI help and settings keyboard order.

## File-by-file handoff

- `videotranslator/jobs.py`: `TranslationJobConfig.keep_original_audio`, normalized
  `TranslationJobResult.subtitle_path`, and immutable `JobOutput.from_result()` for legacy
  output dictionaries / result wrappers.
- `videotranslator/output_media.py`: optional `original_audio_input` for `mux_video`. With the
  option enabled, all inputs precede output options; the dubbed stream is default, the original
  is optional, and MP4 uses `handler_name` (`Dubbed` / `Original`) because ffprobe does not expose
  MP4 stream `title` metadata as a title tag. With None, the old ffmpeg argument behavior stays.
- `videotranslator/pipeline_runner.py`: defaults source-audio retention on; regular outputs mux
  it as an alternate stream. Lip sync re-muxes the synchronized video with the complete dubbed
  mix (voice and background) and optional original audio instead of moving the vocals-only file
  over the output.
- `video_translator_gui.py`: legacy `translate_video` forwards `keep_original_audio`; GUI job
  config reads the Player preference; batch, URL and editor phase-2 workers build `JobOutput`s
  and schedule `_on_job_outputs` before `_on_done`; URL downloads do not retain a temporary
  source path in the playlist item. `_on_job_outputs` deduplicates Results, syncs controller
  playlist, and loads first video paused when autoload is enabled. Settings has the two P3
  checkboxes, persistence, localized labels and mpv/libmpv credit footer. Editor preview uses a
  temporary SRT, responds to row selection with seek, reloads changed subtitles, clamps its
  Toplevel rectangle using `player_core.editor_geometry`, sets transient ownership, and cleans
  the SRT/player state when closed. `_editor_open` marks editor lifetime. Command routing handles
  the A/B and CC buttons.
- `videotranslator/player_core.py`: `editor_geometry()` clamps position and size to the screen;
  `update_segments_as_subtitles()` rewrites the active SRT and requests `sub-reload`.
- `videotranslator/player_panel_tk.py`: A/B and CC controls, disabled unless both audio tracks
  or an SRT are available; CC reflects visible state and both controls follow theme colors.
- `videotranslator/player_settings.py`: named config key constants for autoload and original
  audio, normalization and serialization use those constants.
- `videotranslator/cli.py`: `--no-original-audio`; existing config can also turn source audio
  retention off, with the CLI switch always able to disable it.
- `videotranslator/ui_strings_player.py`: P3 settings labels added in all 26 UI languages.
- Tests changed: `test_jobs_pipeline.py`, `test_legacy_bridges.py`, `test_output_media.py`,
  `test_player_core.py`, `test_ui_worker_outcomes.py`, `test_ui_theme_tk.py`, and
  `test_cli_smoke.py`. `test_pipeline_runner.py` was run and remains green without edits.

## Handoff instructions

1. Inspect `git status` and the complete working diff. The current base is `39949ec`; all P3
   changes are local and uncommitted. The user wants the work written down before switching back
   to Claude. No P3 commit or push has been made.
2. Do not delete, stage or rewrite the pre-existing untracked `_backup_ui_redesign_20260617/`
   or `_demo_styles.py`.
3. Continue only with the remaining acceptance checks below. The worktree itself is shared, so
   the implementation is already present; do not re-implement it.
4. When P3 acceptance is satisfied, update `_dev/CHANGELOG.md` and this plan, run checks, then
   follow the project's commit/push rules in `CLAUDE.md`. Current CI status is only the base
   commit's green CI; no CI has run for the uncommitted P3 changes.

## Remaining acceptance checks

- Completed: py_compile; `env -u DISPLAY python -m unittest discover -s tests` (1048 tests,
  89 skipped); `xvfb-run -a python -m unittest discover -s tests` (1048 tests, 6 skipped);
  `git diff --check`.
- With real libmpv, confirm local and URL outputs enter Results and the first loads paused before
  completion UI; confirm a three-item batch, autoload disabled and subtitles-only behavior.
- Exercise A/B repeatedly and verify playhead position stays within the spec tolerance; confirm
  the subtitle toggle is instant and unavailable without an SRT.
- Open the subtitle editor: click a row and check the seek position; edit translated text and
  verify the on-screen line changes; cancel and confirm the URL source and temporary SRT are gone.
- On Windows, verify output overwrite while previously loaded, ffprobe sees both named audio
  tracks, no-original-audio yields one track, and lip-sync output retains background music.
- Keep P3 uncommitted and unpushed until the above checks are reviewed. Do not modify or delete
  the existing backup directory or `_demo_styles.py`.
