"""Main translation pipeline runner.

The legacy GUI module still owns several concrete helpers while the monolith
is being reduced. This module contains the pipeline orchestration and receives
those helpers through :class:`PipelineRuntime`, avoiding circular imports while
making the runner independently testable.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from videotranslator.output_media import get_duration, mux_video, save_subtitles

DEFAULT_LANG = "it"


@dataclass(frozen=True)
class PipelineRuntime:
    languages: dict[str, Any]
    lang_expansion: dict[str, float]
    suggest_xtts_speed: Any
    default_videos_dir: Any
    extract_audio: Any
    separate_audio: Any
    run_ffmpeg: Any
    transcribe: Any
    split_on_punctuation: Any
    diarize_audio: Any
    assign_speakers: Any
    merge_short_segments: Any
    repair_split_sentences: Any
    expand_tight_slots: Any
    add_quality_flag: Any
    flag_whisper_suspicious: str
    estimate_p90_ratio: Any
    tts_speed_factor_for: Any
    classify_difficulty: Any
    resolve_difficulty_profile: Any
    format_profile_log: Any
    translate_segments: Any
    generate_tts_cosyvoice: Any
    generate_tts_xtts: Any
    generate_tts: Any
    build_dubbed_track: Any
    has_enough_faces: Any
    apply_lipsync: Any


def translate_video(
    video_in: str,
    output: str | None = None,
    model: str = "small",
    lang_source: str = "auto",
    lang_target: str = DEFAULT_LANG,
    voice: str | None = None,
    tts_rate: str = "+0%",
    no_subs: bool = False,
    subs_only: bool = False,
    no_demucs: bool = False,
    translation_engine: str = "google",
    deepl_key: str = "",
    segments_override: list[dict] | None = None,
    tts_engine: str = "edge",   # "edge" | "xtts" | "cosyvoice" (v2.3)
    use_diarization: bool = False,
    hf_token: str = "",
    use_lipsync: bool = False,
    xtts_speed: float | None = None,
    ollama_model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    ollama_slot_aware: bool = True,
    ollama_thinking: bool = False,
    ollama_document_context: bool = True,
    slot_expansion: bool = True,
    sentence_repair: bool = True,
    overlap_fade_enabled: bool = True,
    whisper_sanity: bool = True,
    difficulty_profile_enabled: bool = True,
    difficulty_override: str | None = None,
    hotwords: list[str] | None = None,
    ollama_use_cove: bool = True,
    *,
    runtime: PipelineRuntime,
) -> dict:
    """
    Main pipeline. Returns dict with output paths and segments.
    segments_override: skip transcription+translation and use these segments (GUI editor).

    `xtts_speed`: se None (default) viene calcolato via `_suggest_xtts_speed`
    in base alla coppia (lang_source, lang_target). Se fornito esplicitamente
    (config JSON con chiave presente / CLI --xtts-speed / parametro GUI futuro)
    viene rispettato senza modifiche. Questa è la leva principale per ridurre
    l'atempo post-processing su coppie asimmetriche tipo EN→IT.
    """

    LANGUAGES = runtime.languages
    LANG_EXPANSION = runtime.lang_expansion
    _suggest_xtts_speed = runtime.suggest_xtts_speed
    _default_videos_dir = runtime.default_videos_dir
    extract_audio = runtime.extract_audio
    separate_audio = runtime.separate_audio
    _run_ffmpeg = runtime.run_ffmpeg
    transcribe = runtime.transcribe
    _split_on_punctuation = runtime.split_on_punctuation
    diarize_audio = runtime.diarize_audio
    assign_speakers = runtime.assign_speakers
    _merge_short_segments = runtime.merge_short_segments
    _repair_split_sentences = runtime.repair_split_sentences
    _expand_tight_slots = runtime.expand_tight_slots
    _add_quality_flag = runtime.add_quality_flag
    _FLAG_WHISPER_SUSPICIOUS = runtime.flag_whisper_suspicious
    _estimate_p90_ratio = runtime.estimate_p90_ratio
    _tts_speed_factor_for = runtime.tts_speed_factor_for
    _classify_difficulty = runtime.classify_difficulty
    _resolve_difficulty_profile = runtime.resolve_difficulty_profile
    _format_profile_log = runtime.format_profile_log
    translate_segments = runtime.translate_segments
    generate_tts_cosyvoice = runtime.generate_tts_cosyvoice
    generate_tts_xtts = runtime.generate_tts_xtts
    generate_tts = runtime.generate_tts
    build_dubbed_track = runtime.build_dubbed_track
    _has_enough_faces = runtime.has_enough_faces
    apply_lipsync = runtime.apply_lipsync

    if lang_target not in LANGUAGES:
        raise ValueError(f"Unsupported target language: {lang_target}")
    if not os.path.exists(video_in):
        raise FileNotFoundError(f"Video not found: {video_in}")

    # Autotune dello speed XTTS in base alla coppia di lingue. Rispetta sempre
    # un override esplicito (xtts_speed non-None). Calcolato qui, una sola volta
    # per chiamata, così sia il log iniziale sia l'invocazione di generate_tts_xtts
    # usano lo stesso valore.
    effective_xtts_speed, lang_ratio, speed_auto = _suggest_xtts_speed(
        lang_source, lang_target, xtts_speed,
    )
    # Caso "target molto più lungo del source" (ratio >= 1.20): oltre allo speed
    # auto-tuned, rendiamo anche il merge dei segmenti più aggressivo, così
    # l'italiano/francese tradotto ha slot più capienti da riempire. Il
    # gate `speed_auto` assicura che un utente v1.4 con `xtts_speed` pinnato
    # in config non veda cambiare silenziosamente anche il merge (i due dial
    # si muovono insieme: o entrambi auto, o entrambi a default).
    merge_aggressive = speed_auto and lang_ratio >= 1.20

    voice = voice or LANGUAGES[lang_target]["voices"][0]
    stem  = Path(video_in).stem
    if not output:
        input_dir = Path(video_in).parent
        tmp_root  = Path(tempfile.gettempdir())
        try:
            input_dir.relative_to(tmp_root)
            is_tmp = True
        except ValueError:
            is_tmp = False
        if is_tmp:
            videos_dir = _default_videos_dir()
            videos_dir.mkdir(parents=True, exist_ok=True)
            output = str(videos_dir / f"{stem}_{lang_target}.mp4")
        else:
            output = str(input_dir / f"{stem}_{lang_target}.mp4")
    output_base = str(Path(output).with_suffix(""))

    print(f"[i] {Path(video_in).name} | {lang_source}→{lang_target} | {voice}", flush=True)
    if tts_engine in ("xtts", "cosyvoice"):
        # Log esplicito di cosa ha deciso l'autotune. Utile in bug report / debug
        # di atempo artifacts. CosyVoice riusa lo stesso autotune (lo speed
        # range è equivalente; il ceiling è speso allo stesso modo nel loop
        # adattivo per-segmento).
        if speed_auto:
            _ratio_note = f"auto-tuned for {lang_source}→{lang_target}, ratio={lang_ratio:.2f}"
        else:
            _ratio_note = f"user override (ratio={lang_ratio:.2f})"
        _engine_label = "XTTS" if tts_engine == "xtts" else "CosyVoice"
        print(f"[i] {_engine_label} speed={effective_xtts_speed:.2f} ({_ratio_note}){' [aggressive merge]' if merge_aggressive else ''}", flush=True)

    with tempfile.TemporaryDirectory(prefix="vidtrans_") as tmp_dir:
        audio_raw = os.path.join(tmp_dir, "audio_raw.wav")
        extract_audio(video_in, audio_raw)

        bg_path = None
        vocals_path = audio_raw

        if not no_demucs:
            try:
                vocals_path, bg_path = separate_audio(audio_raw, tmp_dir)
            except Exception as e:
                print(f"     ! Demucs failed ({e}), proceeding without separation", flush=True)
                vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
                _run_ffmpeg([
                    "ffmpeg", "-y", "-i", audio_raw, "-ar", "16000", "-ac", "1", vocals_16k
                ], step="resample audio")
                vocals_path = vocals_16k
        else:
            vocals_16k = os.path.join(tmp_dir, "audio_16k.wav")
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", audio_raw, "-ar", "16000", "-ac", "1", vocals_16k
            ], step="resample audio")
            vocals_path = vocals_16k

        diar_segments: list[dict] = []
        # TASK 2G v2: resolved profile, computed lazily in the branch that
        # has the pre-translation segments (raw_segs from Whisper, or the
        # editor override). Stays None until the first compute path
        # executes; defaults to MEDIUM downstream when None.
        _resolved_profile: _DifficultyProfile | None = None
        if segments_override is not None:
            segments = segments_override
            # Editor override path: estimate P90 from the override
            # segments themselves (text_src or text). The user has
            # already accepted/edited the source side of the segments,
            # so this estimate is as good as the Whisper-driven one.
            if difficulty_profile_enabled:
                _src_for_p = (
                    lang_source if lang_source and lang_source != "auto"
                    else (segments[0].get("lang_source") if segments else "en") or "en"
                )
                _exp_tgt_o = LANG_EXPANSION.get(
                    lang_target,
                    LANG_EXPANSION.get(lang_target.split("-")[0], 1.0),
                )
                _exp_src_o = LANG_EXPANSION.get(
                    _src_for_p,
                    LANG_EXPANSION.get((_src_for_p or "").split("-")[0], 1.0),
                ) or 1.0
                _expansion_factor_o = (
                    _exp_tgt_o / _exp_src_o if _exp_src_o > 0 else 1.0
                )
                _est_p90_o = _estimate_p90_ratio(
                    segments, lang_target, _expansion_factor_o,
                    tts_speed_factor=_tts_speed_factor_for(lang_target),
                )
                if difficulty_override:
                    _classification_o = difficulty_override.lower()
                    print(
                        f"     [difficulty] manual override: "
                        f"using {_classification_o.upper()} profile "
                        f"(estimated P90 was {_est_p90_o:.2f})",
                        flush=True,
                    )
                else:
                    _classification_o = _classify_difficulty(_est_p90_o)
                _resolved_profile = _resolve_difficulty_profile(_classification_o)
                print(
                    f"     {_format_profile_log(_classification_o, _resolved_profile, _est_p90_o)}",
                    flush=True,
                )
        else:
            raw_segs, detected_lang = transcribe(
                vocals_path, model, lang_source, hotwords=hotwords,
            )
            effective_src = detected_lang if lang_source == "auto" else lang_source
            # Re-split su punteggiatura forte: dà a XTTS frasi complete invece di
            # cut mid-sentence di Whisper. Riduce hallucinations.
            pre_split = len(raw_segs)
            raw_segs = _split_on_punctuation(raw_segs)
            if len(raw_segs) > pre_split:
                print(f"     → Split on punctuation: {pre_split} → {len(raw_segs)}", flush=True)
            # Speaker diarization (before translation so speaker info propagates)
            if use_diarization and hf_token.strip():
                try:
                    diar_segments = diarize_audio(vocals_path, hf_token.strip())
                    raw_segs = assign_speakers(raw_segs, diar_segments)
                except Exception as e:
                    print(f"     ! Diarization failed ({e.__class__.__name__}: {e}), continuing without speaker info.", flush=True)
                    diar_segments = []
            # Merge dei segmenti troppo brevi per ridurre hallucinations XTTS
            # e produrre frasi più naturali per la traduzione. Su coppie con
            # target molto più lungo della source (ratio >= 1.20, es. EN→IT)
            # usiamo bound più generosi per dare al TTS slot più capienti.
            pre_merge = len(raw_segs)
            raw_segs = _merge_short_segments(raw_segs, aggressive=merge_aggressive)
            if len(raw_segs) < pre_merge:
                _note = " (aggressive)" if merge_aggressive else ""
                print(f"     → Merged short segments{_note}: {pre_merge} → {len(raw_segs)}", flush=True)
            # TASK 2L: ricompone frasi spezzate da Whisper (es. "sto per." +
            # "Parlare di...") prima della traduzione, così qwen3 vede frasi
            # coerenti invece di frammenti. Pure function, ritorna nuova lista.
            # Disabilitabile con --no-sentence-repair per A/B test.
            if sentence_repair:
                _pre_repair = len(raw_segs)
                raw_segs = _repair_split_sentences(
                    raw_segs, src_lang_hint=effective_src,
                )
                _repaired = _pre_repair - len(raw_segs)
                if _repaired > 0:
                    print(
                        f"     → Repaired {_repaired} split sentences from Whisper output",
                        flush=True,
                    )
            # TASK 2E: smart slot expansion / time borrowing. Tight segments
            # (expected pre_stretch_ratio > 1.50) "rubano" tempo dai gap
            # silenziosi successivi e — se il vicino è sotto-utilizzato —
            # anche dall'inizio del suo slot. Riduce l'atempo udibile senza
            # toccare il testo o la traduzione. Disabilitabile con
            # --no-slot-expansion per A/B test in caso di regressioni.
            if slot_expansion:
                _exp_tgt = LANG_EXPANSION.get(
                    lang_target,
                    LANG_EXPANSION.get(lang_target.split("-")[0], 1.0),
                )
                _exp_src = LANG_EXPANSION.get(
                    effective_src,
                    LANG_EXPANSION.get((effective_src or "").split("-")[0], 1.0),
                ) or 1.0
                _expansion_factor = _exp_tgt / _exp_src if _exp_src > 0 else 1.0
                _orig_segs = [dict(s) for s in raw_segs]
                raw_segs = _expand_tight_slots(
                    raw_segs, lang_target, expansion_factor=_expansion_factor,
                )
                _n_expanded = sum(
                    1 for a, b in zip(_orig_segs, raw_segs)
                    if (b["end"] - b["start"]) > (a["end"] - a["start"]) + 1e-6
                )
                if _n_expanded > 0:
                    print(
                        f"     → Expanded {_n_expanded}/{len(raw_segs)} tight segments "
                        f"by borrowing silence",
                        flush=True,
                    )
            # TASK 2M: post-Whisper sanity check. Flag segments con token
            # sospetti (parole inglesi non standard di 1-3 char, ripetizioni
            # immediate). NON corregge automaticamente — stamparli a console
            # aiuta l'utente a sapere quali segmenti rivedere nell'editor
            # sottotitoli prima del doppiaggio. Disabilitabile con
            # --no-whisper-sanity per pipeline silenziosa.
            if whisper_sanity:
                try:
                    from videotranslator.whisper_sanity import (
                        sanity_score_segments as _sanity_score_segments,
                    )
                    _flagged = _sanity_score_segments(raw_segs)
                except Exception as _e:  # pragma: no cover - defensive
                    print(
                        f"     ! Whisper sanity check skipped "
                        f"({_e.__class__.__name__}: {_e})",
                        flush=True,
                    )
                    _flagged = {}
                if _flagged:
                    print(
                        f"     ⚠ Whisper sanity: {len(_flagged)} segment(s) "
                        f"with suspicious tokens — review in editor:",
                        flush=True,
                    )
                    # TASK 5C: persist the sanity hit on the segment dict so
                    # the subtitle editor can colourise the row. The pipeline
                    # carries the flag through translate_segments because the
                    # Ollama path copies _quality_flags from seg → entry.
                    for _idx, _info in _flagged.items():
                        if 0 <= _idx < len(raw_segs):
                            _add_quality_flag(
                                raw_segs[_idx], _FLAG_WHISPER_SUSPICIOUS,
                            )
                    for _idx, _info in list(_flagged.items())[:5]:
                        _susp = _info.get("suspicious", [])
                        _reps = _info.get("repeats", [])
                        _details = []
                        if _susp:
                            _details.append(f"susp={_susp}")
                        if _reps:
                            _details.append(f"repeat={_reps}")
                        print(
                            f"        seg #{_idx}: {' '.join(_details)}",
                            flush=True,
                        )
                    if len(_flagged) > 5:
                        print(
                            f"        ... and {len(_flagged) - 5} more",
                            flush=True,
                        )
            # TASK 2G v2: pre-translation difficulty profile resolution.
            # Estimate P90 of pre_stretch_ratio from the current segments
            # (post-merge, post-repair, post-expand) BEFORE TTS+stretch.
            # The classification (easy/medium/hard) drives a Profile that
            # configures length retry threshold (Ollama re-prompt),
            # atempo cap, Rubber Band band and XTTS speed cap.
            #
            # Manual override (--difficulty-override) bypasses the auto
            # estimate — useful for A/B testing or for users who already
            # know the source content profile (e.g. fast comedy).
            #
            # --no-difficulty-profile (difficulty_profile_enabled=False)
            # forces MEDIUM, reproducing the v1.7 / pre-2G v2 hardcoded
            # constants exactly.
            if difficulty_profile_enabled:
                _exp_tgt_p = LANG_EXPANSION.get(
                    lang_target,
                    LANG_EXPANSION.get(lang_target.split("-")[0], 1.0),
                )
                _exp_src_p = LANG_EXPANSION.get(
                    effective_src,
                    LANG_EXPANSION.get((effective_src or "").split("-")[0], 1.0),
                ) or 1.0
                _expansion_factor_p = (
                    _exp_tgt_p / _exp_src_p if _exp_src_p > 0 else 1.0
                )
                _est_p90_p = _estimate_p90_ratio(
                    raw_segs, lang_target, _expansion_factor_p,
                    tts_speed_factor=_tts_speed_factor_for(lang_target),
                )
                if difficulty_override:
                    _classification_p = difficulty_override.lower()
                    print(
                        f"     [difficulty] manual override: "
                        f"using {_classification_p.upper()} profile "
                        f"(estimated P90 was {_est_p90_p:.2f})",
                        flush=True,
                    )
                else:
                    _classification_p = _classify_difficulty(_est_p90_p)
                _resolved_profile = _resolve_difficulty_profile(_classification_p)
                print(
                    f"     {_format_profile_log(_classification_p, _resolved_profile, _est_p90_p)}",
                    flush=True,
                )

            segments = translate_segments(
                raw_segs, effective_src, lang_target,
                engine=translation_engine, deepl_key=deepl_key,
                ollama_model=ollama_model, ollama_url=ollama_url,
                ollama_slot_aware=ollama_slot_aware,
                ollama_thinking=ollama_thinking,
                ollama_document_context=ollama_document_context,
                difficulty_profile=_resolved_profile,
                ollama_use_cove=ollama_use_cove,
            )

        if not no_subs:
            save_subtitles(segments, output_base)

        if subs_only:
            print("\n[+] --subs-only mode complete.")
            return {"srt": output_base + ".srt", "segments": segments}

        # TASK 2G v2: clamp the autotuned XTTS ceiling by the resolved
        # Profile's xtts_speed_cap. EASY: 1.30 cap (ridotto da 1.40),
        # MEDIUM: 1.35 (legacy), HARD: 1.45 (esteso). Si applica solo
        # quando l'utente NON ha pinnato xtts_speed esplicitamente
        # (speed_auto=True) — un override CLI/config viene rispettato
        # come prima per non sorprendere chi ha tuning manuale. Log
        # esplicito quando il cap effettivamente cambia, così il
        # diagnostic XTTS adaptive speed coincide con l'aspettativa.
        if speed_auto and _resolved_profile is not None:
            _orig_speed = effective_xtts_speed
            _capped = min(effective_xtts_speed, _resolved_profile.xtts_speed_cap)
            if abs(_capped - _orig_speed) > 1e-6:
                print(
                    f"     [difficulty] XTTS speed clamp: "
                    f"{_orig_speed:.2f} → {_capped:.2f} "
                    f"(profile cap {_resolved_profile.xtts_speed_cap:.2f})",
                    flush=True,
                )
            effective_xtts_speed = _capped

        # TTS generation — Edge-TTS, Coqui XTTS v2 o CosyVoice (v2.3).
        # Cascata di fallback: cosyvoice → xtts → edge. Se l'utente ha scelto
        # cosyvoice e fallisce, proviamo XTTS prima di degradare a Edge-TTS,
        # così l'utente che sceglie un voice-cloning engine non si ritrova
        # automaticamente con voci sintetiche piatte.
        tts_files = None
        if tts_engine == "cosyvoice":
            try:
                tts_files = generate_tts_cosyvoice(
                    segments, vocals_path, lang_target, tmp_dir,
                    diar_segments=diar_segments,
                    speed=effective_xtts_speed,  # ceiling condiviso con XTTS
                )
            except Exception as e:
                print(f"     ! CosyVoice failed ({e}), falling back to XTTS.", flush=True)
                tts_files = None
            # Fallback intra-clone: prima di scendere a Edge-TTS, tentiamo XTTS
            # (l'utente ha esplicitamente chiesto voice cloning).
            if tts_files is None:
                try:
                    tts_files = generate_tts_xtts(
                        segments, vocals_path, lang_target, tmp_dir,
                        diar_segments=diar_segments,
                        speed=effective_xtts_speed,
                    )
                except Exception as e:
                    print(f"     ! XTTS fallback failed ({e}), falling back to Edge-TTS.", flush=True)
                    tts_files = None
        elif tts_engine == "xtts":
            try:
                tts_files = generate_tts_xtts(
                    segments, vocals_path, lang_target, tmp_dir,
                    diar_segments=diar_segments,
                    speed=effective_xtts_speed,
                )
            except Exception as e:
                print(f"     ! XTTS failed ({e}), falling back to Edge-TTS.", flush=True)
                tts_files = None
        if tts_files is None:
            tts_files = generate_tts(segments, voice, tmp_dir, rate=tts_rate)
        duration  = get_duration(video_in)
        track     = build_dubbed_track(
            segments, tts_files, bg_path, duration, tmp_dir,
            metrics_csv_path=output_base + "_metrics.csv",
            overlap_fade_enabled=overlap_fade_enabled,
            difficulty_profile=_resolved_profile,
        )
        mux_video(video_in, track, output)

        if use_lipsync:
            # TASK 2H: pre-check faces with cv2 Haar Cascade. Wav2Lip would
            # otherwise spend 30-60s reading every frame just to fail with
            # "Face not detected" on voice-only content (podcasts, screen
            # recordings, voice-over animations). The pre-check samples 15
            # frames in ~1s and skips Wav2Lip cleanly when no face is present.
            _face_dir = os.path.join(tmp_dir, "_face_check")
            _has_face, _face_ratio, _face_n, _face_total = _has_enough_faces(
                video_in, _face_dir
            )
            if not _has_face:
                print(
                    f"     [face-check] {_face_n}/{_face_total} sampled frames "
                    f"contain a face (ratio {_face_ratio:.2f}); skipping Wav2Lip "
                    f"— voice-only or no-face video",
                    flush=True,
                )
            else:
                print(
                    f"     [face-check] {_face_n}/{_face_total} sampled frames "
                    f"contain a face (ratio {_face_ratio:.2f}); proceeding with Wav2Lip",
                    flush=True,
                )
                try:
                    # Build a vocals-only track (no background music) for accurate lip sync
                    track_vocals = build_dubbed_track(segments, tts_files, None, duration, tmp_dir,
                                                       label="[6/6] Assembling vocals track for lip-sync...",
                                                       overlap_fade_enabled=overlap_fade_enabled,
                                                       difficulty_profile=_resolved_profile)
                    synced = apply_lipsync(output, track_vocals, tmp_dir)
                    shutil.move(synced, output)
                except Exception as e:
                    print(f"     ! Lip sync failed ({e.__class__.__name__}: {e}), keeping video without lip sync.", flush=True)

    print(f"\n[✓] Done: {output}")
    return {"video": output, "srt": output_base + ".srt", "segments": segments}
