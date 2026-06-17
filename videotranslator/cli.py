"""Installable command-line entry point for VideoTranslatorAI."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence


def _build_parser(legacy) -> argparse.ArgumentParser:
    """Build the CLI argument parser using constants from the legacy module."""
    parser = argparse.ArgumentParser(description="Video Translator AI")
    parser.add_argument("input", nargs="?", help="Input video")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run local diagnostics and exit without starting translation",
    )
    parser.add_argument(
        "--preflight-lipsync",
        action="store_true",
        help="When used with --preflight, require Wav2Lip lip-sync packages "
             "(dlib, facexlib, basicsr) instead of reporting them as optional warnings",
    )
    parser.add_argument("--model", default=legacy.DEFAULT_WHISPER_MODEL, choices=legacy.WHISPER_MODELS)
    parser.add_argument("--lang-source", default="auto")
    parser.add_argument("--lang-target", default=legacy.DEFAULT_LANG, choices=list(legacy.LANGUAGES.keys()))
    parser.add_argument("--voice", default=None)
    parser.add_argument("--tts-rate", default="+0%")
    parser.add_argument("--no-subs", action="store_true")
    parser.add_argument("--subs-only", action="store_true")
    parser.add_argument("--no-demucs", action="store_true")
    parser.add_argument("--translation-engine", default="google",
                        choices=["google", "deepl", "marian", "llm_ollama"])
    parser.add_argument("--deepl-key", default="")
    parser.add_argument("--ollama-model", default=None,
                        help="Ollama model tag (default: qwen3:8b — Qwen3 with thinking mode "
                             "auto-disabled to avoid <think> blocks. Use qwen2.5:7b-instruct "
                             "for legacy behaviour)")
    parser.add_argument("--ollama-url", default=None,
                        help="Ollama daemon URL (default: http://localhost:11434)")
    parser.add_argument("--ollama-no-slot-aware", action="store_true", default=None,
                        help="Disable slot-aware prompting (faster, less constrained)")
    parser.add_argument("--ollama-thinking", action="store_true",
                        help="Enable Qwen3 thinking mode: deliberates step-by-step "
                             "(~10x slower, fewer idiom/grammar errors). Default off.")
    parser.add_argument("--no-document-context", action="store_true",
                        help="Disable TASK 2K document-level context. By default the "
                             "Ollama engine generates one summary of the whole "
                             "transcript up front and injects it as GLOBAL CONTEXT "
                             "into every per-segment prompt to anchor terminology "
                             "and tone across long videos. Disable for fastest runs "
                             "on short clips.")
    parser.add_argument("--diarize", action="store_true",
                        help="Enable pyannote speaker diarization")
    parser.add_argument("--hf-token", default="",
                        help="HuggingFace token (falls back to the platform "
                             "config file, e.g. "
                             "~/.config/videotranslatorai/config.json on Linux)")
    parser.add_argument("--lipsync", action="store_true",
                        help="Apply Wav2Lip lip sync after dubbing (first run: downloads ~416MB)")
    parser.add_argument("--xtts-speed", type=float, default=None,
                        help="XTTS v2 native speed factor (0.5–2.0). "
                             "If omitted, auto-tuned per language pair "
                             "(e.g. EN→IT=1.35, IT→EN=1.25).")
    parser.add_argument("--no-slot-expansion", action="store_true",
                        help="Disable smart slot expansion / time borrowing for "
                             "tight segments (TASK 2E). Default ON: tight segments "
                             "borrow time from neighbouring silence/easy slots so "
                             "ffmpeg atempo can stay below audible thresholds.")
    parser.add_argument("--no-sentence-repair", action="store_true",
                        help="Disable smart sentence-boundary repair (TASK 2L). "
                             "Default ON: pairs of segments where the first ends "
                             "with a connector (to/for/della/...) and the second "
                             "starts in lowercase are re-joined before translation, "
                             "so the LLM sees full sentences instead of mid-clause "
                             "fragments.")
    parser.add_argument("--no-whisper-sanity", action="store_true",
                        help="Disable post-Whisper sanity check (TASK 2M). "
                             "Default ON: scans transcribed segments for "
                             "suspicious 1-3 char tokens (e.g. 'ay' in place "
                             "of 'okay') and immediate word repetitions, "
                             "logging the segment indexes so the user knows "
                             "what to review in the subtitle editor.")
    parser.add_argument("--no-overlap-fade", action="store_true",
                        help="Disable TASK 2P overlap fade and revert to legacy "
                             "hard-truncate when the TTS still overshoots its "
                             "slot after atempo/rubberband. Default OFF: tails "
                             "are allowed to spill up to 400 ms into the next "
                             "slot and crossfade via the memmap mix, which "
                             "drops audible 'audio mozzato' artefacts on dense "
                             "voice-only content.")
    # TASK 2G v2: difficulty profile orchestrator.
    parser.add_argument("--difficulty-override",
                        choices=("easy", "medium", "hard"),
                        default=None,
                        help="Force the TASK 2G v2 difficulty profile instead "
                             "of computing it from the segment density. Useful "
                             "for A/B testing or when you already know the "
                             "source content profile (e.g. fast comedy → hard).")
    parser.add_argument("--no-difficulty-profile", action="store_true",
                        help="Disable the TASK 2G v2 profile orchestrator and "
                             "fall back to the default MEDIUM quality profile. "
                             "Default OFF: the pipeline auto-tunes length retry "
                             "budget, atempo cap, Rubber Band band and XTTS speed cap "
                             "based on the predicted P90 stretch ratio.")
    # TASK 2U: Chain-of-Verification opt-out.
    parser.add_argument("--no-cove", action="store_true",
                        help="Disable TASK 2U Chain-of-Verification second-pass "
                             "for the Ollama LLM engine. Default OFF: when the "
                             "source segment contains a negation or a quantifier "
                             "(all/some/none/every), a second Ollama call asks "
                             "the model to verify those specific aspects and "
                             "correct the translation if needed (~+30%% Ollama "
                             "calls on dense talks, ~+5%% on light content). "
                             "Use this flag on slow CPUs or for A/B testing.")
    # TTS engine choice via CLI.
    parser.add_argument("--xtts", action="store_true",
                        help="Use Coqui XTTS v2 voice cloning (~1.8GB first run)")
    parser.add_argument(
        "--hotwords", type=str, default=None,
        help="Comma-separated hotwords to bias Whisper decoding "
             "(proper nouns, brand names, technical jargon). "
             "Reduces Biased-WER ~43%% on rare words. "
             "Example: --hotwords \"Strix, pipx, Docker\"",
    )
    parser.add_argument(
        "--hotwords-file", type=str, default=None,
        help="Path to JSON file with hotwords. Accepts a flat list "
             "[\"Strix\", \"pipx\"] or a per-language dict "
             "{\"en\": [...], \"it\": [...]}. Merged with --hotwords "
             "(both can be passed; CLI string wins on duplicates).",
    )
    parser.add_argument("--batch", nargs="+", metavar="FILE")
    return parser


def _cli(argv: Sequence[str] | None = None) -> None:
    """Full CLI implementation (extracted from the legacy monolith)."""
    import video_translator_gui as legacy
    from videotranslator.jobs import TranslationJobConfig
    from videotranslator.pipeline import run_translation_job

    parser = _build_parser(legacy)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.preflight:
        report = legacy._run_preflight(
            required_packages=legacy.REQUIRED_PACKAGES,
            required_optional_modules=("dlib", "facexlib", "basicsr")
            if args.preflight_lipsync else (),
        )
        print(legacy._format_preflight_report(report))
        sys.exit(0 if report.ok else 1)

    files = args.batch if args.batch else ([args.input] if args.input else [])
    if not files:
        parser.print_help()
        sys.exit(0)

    missing_pkgs, missing_bins = legacy.check_dependencies()
    if missing_pkgs or missing_bins:
        all_missing = missing_pkgs + missing_bins
        print(f"[!] Missing dependencies: {', '.join(all_missing)}", file=sys.stderr)
        print("    Install with: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    cfg_cli = legacy.load_config()
    hf_token_cli = args.hf_token or legacy.load_hf_token() or cfg_cli.get("hf_token", "")
    # CLI takes priority, then JSON config (if the key exists), otherwise None
    # -> autotune kicks in inside translate_video().
    if args.xtts_speed is not None:
        xtts_speed_cli: float | None = args.xtts_speed
    elif "xtts_speed" in cfg_cli:
        try:
            xtts_speed_cli = float(cfg_cli["xtts_speed"])
        except (TypeError, ValueError):
            xtts_speed_cli = None
    else:
        xtts_speed_cli = None
    # TTS engine selection: --xtts flag or default Edge-TTS.
    tts_engine_cli = "xtts" if args.xtts else "edge"
    ollama_slot_aware_cli = (
        False
        if args.ollama_no_slot_aware is True
        else bool(cfg_cli.get("ollama_slot_aware", True))
    )

    # Hotwords: merge --hotwords (string) and --hotwords-file (JSON). CLI
    # string takes precedence on duplicates (passed first to merge_hotwords,
    # which preserves first-seen order).
    hotwords_cli: list[str] | None = None
    try:
        from videotranslator.hotwords import (
            load_hotwords_file,
            merge_hotwords,
            parse_hotwords_string,
        )
        cli_list = parse_hotwords_string(args.hotwords)
        file_list: list[str] = []
        if args.hotwords_file:
            file_list = load_hotwords_file(
                args.hotwords_file, src_lang=args.lang_source,
            )
        merged = merge_hotwords(cli_list, file_list)
        hotwords_cli = merged or None
        if hotwords_cli:
            print(
                f"[whisper] hotwords loaded: {len(hotwords_cli)} entries",
                flush=True,
            )
    except (FileNotFoundError, ValueError) as exc:
        print(f"[!] Hotwords config error: {exc}", flush=True)
        sys.exit(2)

    for f in files:
        if not os.path.exists(f):
            print(f"[!] File not found: {f}")
            continue
        job = TranslationJobConfig(
            video_in=f,
            output=args.output if len(files) == 1 else None,
            model=args.model,
            lang_source=args.lang_source,
            lang_target=args.lang_target,
            voice=args.voice,
            tts_rate=args.tts_rate,
            no_subs=args.no_subs,
            subs_only=args.subs_only,
            no_demucs=args.no_demucs,
            translation_engine=args.translation_engine,
            deepl_key=args.deepl_key,
            tts_engine=tts_engine_cli,
            use_diarization=args.diarize,
            hf_token=hf_token_cli,
            use_lipsync=args.lipsync,
            xtts_speed=xtts_speed_cli,
            ollama_model=args.ollama_model or cfg_cli.get("ollama_model") or "qwen3:8b",
            ollama_url=args.ollama_url or cfg_cli.get("ollama_url") or "http://localhost:11434",
            ollama_slot_aware=ollama_slot_aware_cli,
            ollama_thinking=args.ollama_thinking or bool(cfg_cli.get("ollama_thinking", False)),
            ollama_document_context=not args.no_document_context,
            slot_expansion=not args.no_slot_expansion,
            sentence_repair=not args.no_sentence_repair,
            overlap_fade_enabled=not args.no_overlap_fade,
            whisper_sanity=not args.no_whisper_sanity,
            difficulty_profile_enabled=not args.no_difficulty_profile,
            difficulty_override=args.difficulty_override,
            hotwords=hotwords_cli,
            ollama_use_cove=not args.no_cove,
        )
        run_translation_job(job, runner=legacy.translate_video)


def main(argv: Sequence[str] | None = None) -> int | None:
    """Run the legacy-compatible CLI, or launch the GUI when no args are given."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        import video_translator_gui as legacy
        legacy.App().mainloop()
        return 0
    _cli(args)
    return 0
