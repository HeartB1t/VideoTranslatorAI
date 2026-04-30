# Next Claude Code Note

Do not push unless Fabio explicitly asks for it in writing.

Current local follow-up:

- Subtitle/duration/mux helpers are now in `videotranslator/output_media.py`; `PipelineRuntime` no longer carries `save_subtitles`, `get_duration`, or `mux_video`.
- New focused coverage: `tests/test_output_media.py`.
- Next recommended target: extract CLI to `videotranslator/cli.py`, keeping `video_translator_gui.py` as the GUI/launcher facade.
- `translate_video(...)` orchestration is now in `videotranslator/pipeline_runner.py`; `video_translator_gui.translate_video(...)` builds a legacy `PipelineRuntime` and delegates.
- New focused coverage: `tests/test_pipeline_runner.py`.
- Dubbed track assembly is now in `videotranslator/audio_assembly.py`; `video_translator_gui.build_dubbed_track(...)` is only a compatibility wrapper.
- New focused coverage: `tests/test_audio_assembly.py`.
- Last Codex task extracted shared TTS/audio helpers into `videotranslator/tts_audio.py`.
- Edge-TTS generation is now in `videotranslator/edge_tts_engine.py` with network-free unit tests.
- Speaker reference extraction is now in `videotranslator/tts_reference.py` with ffmpeg mocked in tests.
- VAD global reference extraction is also in `videotranslator/tts_reference.py`; pure VAD selection helpers are unit-tested without Silero.
- Wav2Lip runtime `apply_lipsync` is now in `videotranslator/lipsync.py`; the GUI wrapper passes legacy path globals and subprocess/timer hooks.
- Audio mix primitives are in `videotranslator/audio_mix.py`; final dubbed-track orchestration/diagnostics now live in `videotranslator/audio_assembly.py`.
- CosyVoice install/cache/download helpers are now in `videotranslator/cosyvoice_runtime.py`; the actual synthesis function still lives in the GUI facade for now.
- XTTS core synthesis is now in `videotranslator/xtts_engine.py` with fake-model unit tests.
- CosyVoice core synthesis is now in `videotranslator/cosyvoice_engine.py` with fake runtime unit tests.
- Ollama setup/runtime helpers are now in `videotranslator/ollama_runtime.py`; translation dispatcher lives in `videotranslator/translation.py`.
- Keep `video_translator_gui.py` as compatibility facade and move behavior in small, testable slices.
- The Wav2Lip Linux path tests were made deterministic because they previously depended on the real writability of `/opt/VideoTranslatorAI/wav2lip`.
- Run `python3 -m pytest -q` before any next commit.
- `.claude/settings.local.json` is local permission state and should not be committed.
- `.claude/scheduled_tasks.json` is currently untracked local state; do not add it unless Fabio explicitly asks.

Architecture note:

- `videotranslator.platforms.resolve_wav2lip_paths()` may now return a fully populated system `asset_dir` even when it is read-only.
- `apply_lipsync()` runs Wav2Lip with `cwd=WAV2LIP_WORK_DIR` and cleans `WAV2LIP_WORK_DIR/temp`, so `Program Files` / `/opt` assets are no longer used for scratch IO.
- If you touch this area again, keep this contract: complete assets can be read-only; fresh installs and partial installs must use a writable fallback asset directory.
