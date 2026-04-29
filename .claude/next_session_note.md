# Next Claude Code Note

Do not push unless Fabio explicitly asks for it in writing.

Current local follow-up:

- The Wav2Lip Linux path tests were made deterministic because they previously depended on the real writability of `/opt/VideoTranslatorAI/wav2lip`.
- Run `python3 -m pytest -q` before any next commit.
- `.claude/settings.local.json` is local permission state and should not be committed.

Architecture note:

- `videotranslator.platforms.resolve_wav2lip_paths()` may now return a fully populated system `asset_dir` even when it is read-only.
- `apply_lipsync()` runs Wav2Lip with `cwd=WAV2LIP_WORK_DIR` and cleans `WAV2LIP_WORK_DIR/temp`, so `Program Files` / `/opt` assets are no longer used for scratch IO.
- If you touch this area again, keep this contract: complete assets can be read-only; fresh installs and partial installs must use a writable fallback asset directory.
