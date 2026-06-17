# Action Plan

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
