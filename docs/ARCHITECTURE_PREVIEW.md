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

## Migration Rule

The legacy file can keep private function names during the transition. New
modules should expose neutral names, and the legacy file can bind them back to
the old names until call sites are moved.

## Platform Contract

- Supported: Windows 10/11 x64, Debian/Ubuntu/Kali-like Linux.
- Best effort: other Linux distributions.
- Experimental: macOS, until real testing exists.

## Next Safe Steps

1. Move keyring/HF token helpers into `videotranslator.secrets`.
2. Move active subprocess registry and cleanup into `videotranslator.subprocess_utils`.
3. Move translation engines one at a time.
4. Leave Tkinter GUI as the last large extraction.
