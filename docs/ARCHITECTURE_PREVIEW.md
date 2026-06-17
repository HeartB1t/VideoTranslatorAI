# Architecture Preview

This preview keeps `video_translator_gui.py` as the public entry point while
moving pure logic into small modules that can be tested without GPU models,
network access, Tkinter, ffmpeg, or platform-specific installers.

## Current Extraction

- `videotranslator.segments`: Whisper/subtitle segment splitting and merging.
- `videotranslator.timing`: XTTS timing and speed heuristics.
- `videotranslator.platforms`: support policy and path resolution.
- `videotranslator.config`: side-effect-light JSON config loading/writing.
- `videotranslator.subprocess_utils`: command normalization and text-mode policy.
- `videotranslator.subprocess_utils.ActiveSubprocessRegistry`: thread-safe
  subprocess tracking used by the legacy GUI shutdown path.
- `videotranslator.secrets`: keyring-first token migration with JSON fallback.
- `videotranslator.preflight`: side-effect-free environment diagnostics shared
  by CLI `--preflight` and the GUI log-panel diagnostics button.
- `videotranslator.cli`: installable command entry point (`videotranslatorai`,
  `python -m videotranslator`) that preserves the legacy no-args GUI behavior.
- `pyproject.toml`: PEP 517/621 package metadata, console scripts, extras and
  editable-install validation in CI.

## Migration Rule

The legacy file can keep private function names during the transition. New
modules should expose neutral names, and the legacy file can bind them back to
the old names until call sites are moved.

## Platform Contract

- Supported: Windows 10/11 x64, Debian/Ubuntu and derivatives.
- Best effort: other Linux distributions.
- Experimental: macOS, until real testing exists.
- `resolve_app_paths(sys_platform, env, home)` is the pure policy resolver. It
  returns `PureWindowsPath` or `PurePosixPath` values and is safe for synthetic
  cross-platform tests, including Windows path fixtures on Linux.
- `runtime_app_paths(sys_platform, env, home)` is the runtime IO resolver. It
  returns concrete `Path` values and rejects a `sys_platform` that does not
  match the current host, so tests do not accidentally treat pure Windows
  fixtures as filesystem paths on POSIX.

## Next Safe Steps

1. Move CLI parser and job construction out of `video_translator_gui.py` into
   `videotranslator.cli`, so `--help` no longer imports Tk/config side effects.
2. Make the GUI construct `TranslationJobConfig` directly and pass every field
   through the same runner used by the CLI.
3. Inject output helpers (`save_subtitles`, `get_duration`, `mux_video`) through
   the pipeline runtime to complete the testable boundary.
4. Move translation engines one at a time.
5. Keep Tkinter layout and widgets as the final large extraction.
