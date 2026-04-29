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
- `videotranslator.secrets`: keyring-first token migration with JSON fallback.

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

1. Wire the legacy HF token functions to `videotranslator.secrets`.
2. Move active subprocess registry and cleanup into `videotranslator.subprocess_utils`.
3. Move translation engines one at a time.
4. Leave Tkinter GUI as the last large extraction.
