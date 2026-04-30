# Next Claude Code Note

Do not push unless Fabio explicitly asks for it in writing.

Current local follow-up:

- Last Codex task extracted shared TTS/audio helpers into `videotranslator/tts_audio.py`.
- Edge-TTS generation is now in `videotranslator/edge_tts_engine.py` with network-free unit tests.
- Speaker reference extraction is now in `videotranslator/tts_reference.py` with ffmpeg mocked in tests.
- VAD global reference extraction is also in `videotranslator/tts_reference.py`; pure VAD selection helpers are unit-tested without Silero.
- Wav2Lip runtime `apply_lipsync` is now in `videotranslator/lipsync.py`; the GUI wrapper passes legacy path globals and subprocess/timer hooks.
- Audio mix primitives are now in `videotranslator/audio_mix.py`; `build_dubbed_track` still owns orchestration/diagnostics.
- CosyVoice install/cache/download helpers are now in `videotranslator/cosyvoice_runtime.py`; the actual synthesis function still lives in the GUI facade for now.
- XTTS core synthesis is now in `videotranslator/xtts_engine.py` with fake-model unit tests.
- Before touching TTS engines, keep `video_translator_gui.py` as compatibility facade and move behavior in small, testable slices.
- Next recommended target: move XTTS/CosyVoice only with compatibility aliases and full import/test checks as user `kali`.
- The Wav2Lip Linux path tests were made deterministic because they previously depended on the real writability of `/opt/VideoTranslatorAI/wav2lip`.
- Run `python3 -m pytest -q` before any next commit.
- `.claude/settings.local.json` is local permission state and should not be committed.
- `.claude/scheduled_tasks.json` is currently untracked local state; do not add it unless Fabio explicitly asks.

Architecture note:

- `videotranslator.platforms.resolve_wav2lip_paths()` may now return a fully populated system `asset_dir` even when it is read-only.
- `apply_lipsync()` runs Wav2Lip with `cwd=WAV2LIP_WORK_DIR` and cleans `WAV2LIP_WORK_DIR/temp`, so `Program Files` / `/opt` assets are no longer used for scratch IO.
- If you touch this area again, keep this contract: complete assets can be read-only; fresh installs and partial installs must use a writable fallback asset directory.
