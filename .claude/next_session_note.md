# Next Claude Code Note

Do not push unless Fabio explicitly asks for it in writing.

Current local follow-up:

- The Wav2Lip Linux path tests were made deterministic because they previously depended on the real writability of `/opt/VideoTranslatorAI/wav2lip`.
- Run `python3 -m pytest -q` before any next commit.
- `.claude/settings.local.json` is local permission state and should not be committed.

Architecture note:

- `videotranslator.platforms.resolve_wav2lip_paths()` currently chooses a writable `asset_dir` when assets are missing or when Wav2Lip needs patch/temp writes.
- A true read-only system `asset_dir` + writable `work_dir` split is not complete yet because `apply_lipsync()` still runs Wav2Lip with `cwd=WAV2LIP_REPO` and cleans `Wav2Lip/temp`.
- If you continue that refactor, route Wav2Lip scratch/temp output into `WAV2LIP_WORK_DIR` first, then loosen the resolver so fully populated system assets can be read-only.
