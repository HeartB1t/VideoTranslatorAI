"""Dubbed-track audio assembly orchestration.

This module owns the final audio assembly step of the dubbing pipeline:
stretch policy, overlap handling, streaming mix, optional background mix,
metrics export and LUFS normalization. The legacy GUI keeps a small wrapper
so older call sites still import ``build_dubbed_track`` from the launcher.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from videotranslator.audio_mix import apply_tail_fade, overlay_pcm, read_segment_to_pcm
from videotranslator.audio_stretch import (
    build_rubberband_command,
    compute_overlap_strategy,
    select_stretch_engine,
)
from videotranslator.difficulty_profile import MEDIUM, Profile
from videotranslator.media import run_ffmpeg
from videotranslator.metrics_csv import dump_segment_metrics
from videotranslator.tts_audio import build_atempo_chain, probe_duration_ms


def build_dubbed_track(
    segments: list[dict],
    tts_files: list[str],
    bg_path: str | None,
    total_duration: float,
    tmp_dir: str,
    bg_volume: float = 0.15,
    label: str = "[6/6] Assembling dubbed track...",
    metrics_csv_path: str | None = None,
    overlap_fade_enabled: bool = True,
    difficulty_profile: Profile | None = None,
    *,
    run_ffmpeg=run_ffmpeg,
    rubberband_available: bool | None = None,
    log=print,
) -> str:
    """Assembla la traccia doppiata in streaming via numpy memmap.
    Evita di accumulare AudioSegment in RAM (~600 MB per video 1h+): il mix avviene
    in-place su un file PCM 16-bit 44.1 kHz stereo che coincide 1:1 con il formato
    di output storico.
    """
    import numpy as np
    import soundfile as sf

    log(label, flush=True)
    SR = 44100
    CH = 2
    total_frames = int(total_duration * SR)
    out = os.path.join(tmp_dir, "track_dubbed.wav")

    # DIAGNOSTIC: traccia per-segment metrics — alimenta sia il diagnostic
    # aggregato (distribuzione bucket + top 10 worst) sia il dump CSV
    # opzionale per analisi P90/P95 cross-video. Lista di dict invece di
    # tuple anonime per evolverla senza rompere consumer esistenti.
    _atempo_stats: list[dict] = []

    # TASK 2G v2: profile orchestrator. None = legacy MEDIUM behaviour
    # (atempo cap 4.0, rubberband band 1.15-1.50). Caller passes a Profile
    # resolved from the difficulty classification when profile orchestration
    # is enabled (translate_video → here).
    _profile = difficulty_profile or MEDIUM
    _atempo_cap = _profile.atempo_cap
    _rb_min = _profile.rubberband_min
    _rb_max = _profile.rubberband_max

    # Tier strategy per stretch audio (TASK 2C-2, TASK 2G v2):
    # - ratio <= rb_min → atempo (default, ok per stretch leggeri)
    # - rb_min < ratio <= rb_max → rubberband CLI se disponibile (no chipmunk)
    # - ratio > rb_max → atempo (rubberband stesso degrada oltre il band)
    # Probe del binario UNA volta sola: select_stretch_engine() falla cleanly
    # ad atempo se il binary manca, quindi nessuna regressione.
    _rubberband_available = (
        shutil.which("rubberband") is not None
        if rubberband_available is None
        else bool(rubberband_available)
    )
    if _rubberband_available:
        print(
            f"     [info] Rubber Band CLI available — using for ratio "
            f"{_rb_min:.2f}-{_rb_max:.2f} band",
            flush=True,
        )
    rubberband_used = 0
    atempo_used = 0

    # TASK 2P (overlap fade): when the post-stretch TTS still overshoots
    # the slot, instead of hard-truncating we let the tail spill up to
    # MAX_OVERLAP_FRAMES into the next segment's slot. The memmap mix
    # below sums int32 samples, so the tail naturally crossfades with
    # whatever gets written there next. Counters drive the diagnostic.
    MAX_OVERLAP_FRAMES = int(0.40 * SR)  # 400 ms — perception-safe ceiling
    overlap_clean_count = 0      # full pcm preserved, mild overshoot
    overlap_truncate_count = 0   # capped at slot+max_overlap, fade-out
    last_seg_index = len(segments) - 1

    # Raw PCM int32 in memmap: serve headroom per sommare senza saturare durante
    # gli overlay, si clampa a int16 alla fine.
    raw_path = os.path.join(tmp_dir, "_track_mix.raw")
    mix = np.memmap(raw_path, dtype=np.int32, mode="w+", shape=(total_frames, CH))
    # Azzera esplicitamente (memmap 'w+' lo fa, ma su alcuni FS conviene forzare).
    mix[:] = 0

    for i, (seg, tts_file) in enumerate(zip(segments, tts_files)):
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)
        slot_ms = max(end_ms - start_ms, 1)

        # Per-segment engine record. 'none' means TTS fit the slot already.
        # Distinguishes 'atempo' (chosen by policy) from 'atempo_fallback'
        # (rubberband attempted and failed) for the metrics CSV.
        _seg_engine_used = "none"

        # Se il TTS eccede lo slot (più 50 ms di margine), applica atempo via ffmpeg.
        src_path = tts_file
        tts_ms_probed = 0
        ratio_raw = 1.0
        if os.path.exists(tts_file) and os.path.getsize(tts_file) > 0:
            tts_ms_probed = probe_duration_ms(tts_file)
            if slot_ms > 0:
                ratio_raw = tts_ms_probed / slot_ms
            if tts_ms_probed > slot_ms + 50:
                ratio = max(1.0, min(ratio_raw, _atempo_cap))
                sped = os.path.join(tmp_dir, f"seg_{i:04d}_sped.wav")
                # Dispatch: la policy pura sceglie engine in base al ratio
                # (ed alla disponibilità del binary rubberband). Outside del
                # range rb_min-rb_max, oppure quando rubberband manca, ricade
                # su atempo. Il band viene dal Profile (default 1.15-1.50,
                # esteso a 1.15-1.80 su HARD).
                engine = select_stretch_engine(
                    ratio, _rubberband_available,
                    rb_min=_rb_min, rb_max=_rb_max,
                )
                _initial_engine = engine
                stretch_ok = False
                if engine == "rubberband":
                    cmd = build_rubberband_command(tts_file, sped, ratio)
                    try:
                        proc = subprocess.run(
                            cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                        )
                        if proc.returncode != 0:
                            err_tail = (proc.stderr or "").strip().splitlines()[-10:]
                            raise RuntimeError(
                                f"rubberband seg {i} failed (exit {proc.returncode}):\n"
                                + "\n".join(err_tail)
                            )
                        # Rubber Band conserva il sample rate dell'input;
                        # read_segment_to_pcm gestisce la conversione a SR/CH
                        # quando differisce, quindi non serve un ffmpeg extra qui.
                        rubberband_used += 1
                        src_path = sped
                        stretch_ok = True
                        _seg_engine_used = "rubberband"
                    except Exception as e:
                        # FALLBACK: nessuna regressione vs comportamento legacy.
                        # Se rubberband fallisce per qualsiasi motivo, riproviamo
                        # con atempo come se il binary non esistesse.
                        print(f"     ! rubberband failed seg {i}: {e}; retrying with atempo", flush=True)
                        engine = "atempo"

                if engine == "atempo":
                    chain = build_atempo_chain(ratio, max_ratio=_atempo_cap)
                    try:
                        run_ffmpeg([
                            "ffmpeg", "-y", "-i", tts_file,
                            "-filter:a", chain,
                            "-ar", str(SR), "-ac", str(CH), "-sample_fmt", "s16", sped,
                        ], step=f"atempo seg {i}")
                        src_path = sped
                        atempo_used += 1
                        stretch_ok = True
                        # Mark as fallback if rubberband had been the initial choice.
                        _seg_engine_used = (
                            "atempo_fallback" if _initial_engine == "rubberband" else "atempo"
                        )
                    except Exception as e:
                        print(f"     ! atempo failed seg {i}: {e}", flush=True)
                # Se entrambi gli engine sono falliti, src_path resta tts_file
                # (audio non compresso); il successivo hard-truncate con fade-out
                # gestirà l'overshoot. Comportamento storico.
                _ = stretch_ok  # lint: variabile usata solo per leggibilità del flow

        pcm = read_segment_to_pcm(
            src_path,
            tmp_dir=tmp_dir,
            sample_rate=SR,
            channels=CH,
            sf_module=sf,
            run_ffmpeg=run_ffmpeg,
            log=print,
        )
        if pcm is None:
            continue

        # TASK 2P 2026-04-29: instead of hard-truncating segments that
        # overshoot the slot, allow up to MAX_OVERLAP_FRAMES of overflow
        # into the next segment's slot via a tail crossfade. Pre-fix
        # diagnostic on real videos showed 15-25% of segments truncated
        # → audible "audio mozzato" at end of phrase. The np.memmap mix
        # accumulates int32 samples so the spill-over is summed with the
        # next segment's pcm naturally; no explicit cross-fade-in needed.
        # TASK 2S (2026-04-29) bump fade-out 80ms → 200ms is preserved as
        # the LEGACY truncate fade length when overlap is disabled or for
        # the last segment of the video.
        slot_frames = int(slot_ms * SR / 1000)
        is_last_seg = (i == last_seg_index)
        strategy, target_frames, fade_len = compute_overlap_strategy(
            pcm_frames=pcm.shape[0],
            slot_frames=slot_frames,
            max_overlap_frames=MAX_OVERLAP_FRAMES,
            is_last_segment=is_last_seg,
            overlap_enabled=overlap_fade_enabled,
        )
        # Trim/keep pcm according to the strategy; "fit" is a no-op.
        truncated = False         # legacy semantics: hard-cut at slot
        overlap_used = False      # TASK 2P new flag
        if strategy == "truncate":
            pcm = pcm[:target_frames].copy()
            truncated = True
        elif strategy == "overlap_clean":
            # Full pcm preserved. The tail will spill into the next
            # segment's slot and crossfade via the memmap sum.
            overlap_used = True
            overlap_clean_count += 1
        elif strategy == "overlap_truncate":
            pcm = pcm[:target_frames].copy()
            truncated = True
            overlap_used = True
            overlap_truncate_count += 1
        # else: "fit" — no slicing, no fade.

        if strategy != "fit":
            # Apply the trailing fade-out on whatever is left of pcm.
            # The helper already returns a fade_frames sized to pcm, but
            # this clamp is a runtime safety net: pcm.shape[0] could differ
            # from what the helper reasoned about if upstream resampling
            # kicked in (very short segments < SR/4 frames). Keep the
            # fade <= 1/4 of the kept pcm so short segments don't get a
            # fade longer than their content (audible as a click).
            pcm = apply_tail_fade(pcm, fade_len)

        # Diagnostic: registra sempre (anche i segmenti "fit", ratio <=1.0).
        _atempo_stats.append({
            "segment_index": i,
            "start_s": seg["start"],
            "end_s": seg["end"],
            "slot_s": slot_ms / 1000.0,
            "src_chars": len((seg.get("text_src") or "")),
            "tgt_chars": len((seg.get("text_tgt") or "")),
            "target_chars": seg.get("_target_chars", 0),
            "length_retry_attempted": bool(seg.get("_length_retry_attempted", False)),
            "length_retry_succeeded": bool(seg.get("_length_retry_succeeded", False)),
            "tts_duration_ms": tts_ms_probed,
            "pre_stretch_ratio": round(ratio_raw, 4),
            "stretch_engine": _seg_engine_used,
            "stretch_truncated": truncated,
            "overlap_used": overlap_used,
            "text_src": seg.get("text_src", ""),
            "text_tgt": seg.get("text_tgt", ""),
        })

        start_frame = int(start_ms * SR / 1000)
        overlay_pcm(mix, pcm, start_frame, total_frames)

    # DIAGNOSTIC: stampa distribuzione atempo (attivo sempre, output sintetico).
    if _atempo_stats:
        _buckets = [
            ("ratio <= 1.00  (no atempo needed):  ", lambda r: r <= 1.00),
            ("1.00 < ratio <= 1.10 (imperceptible):", lambda r: 1.00 < r <= 1.10),
            ("1.10 < ratio <= 1.30 (mild):         ", lambda r: 1.10 < r <= 1.30),
            ("1.30 < ratio <= 1.50 (noticeable):   ", lambda r: 1.30 < r <= 1.50),
            ("1.50 < ratio <= 2.00 (strong):       ", lambda r: 1.50 < r <= 2.00),
            ("ratio > 2.00   (severe):             ", lambda r: r > 2.00),
        ]
        total = len(_atempo_stats)
        trunc_count = sum(1 for s in _atempo_stats if s["stretch_truncated"])
        print(f"     --- ATEMPO DIAGNOSTIC: {total} segments ---", flush=True)
        for label_b, pred in _buckets:
            n = sum(1 for s in _atempo_stats if pred(s["pre_stretch_ratio"]))
            pct = 100.0 * n / total if total else 0.0
            print(f"       {label_b} {n:>4d}  ({pct:5.1f}%)", flush=True)
        print(f"       truncated after atempo:              {trunc_count:>4d}  ({100.0*trunc_count/total:.1f}%)", flush=True)
        # Top 10 worst per ratio
        worst = sorted(_atempo_stats, key=lambda s: -s["pre_stretch_ratio"])[:10]
        print(f"     --- Top 10 worst segments (highest ratio) ---", flush=True)
        for s in worst:
            mm, ss = divmod(int(s["start_s"]), 60)
            t_mark = "TRUNC" if s["stretch_truncated"] else "     "
            slot_ms_v = int(s["slot_s"] * 1000)
            print(
                f"       #{s['segment_index']:04d} @ {mm:02d}:{ss:02d}  "
                f"slot={slot_ms_v:>5d}ms  tts={s['tts_duration_ms']:>5d}ms  "
                f"ratio={s['pre_stretch_ratio']:5.2f}  {t_mark}",
                flush=True,
            )
        print(f"     --- end diagnostic ---", flush=True)
        # TASK 2C-2: stampa la ripartizione engine usati per stretch.
        # Utile in produzione per verificare che la tier strategy funzioni
        # come atteso (rubberband concentrato nel band 1.15–1.50).
        if rubberband_used + atempo_used > 0:
            print(
                f"     -> Stretch engines: {rubberband_used} rubberband, "
                f"{atempo_used} atempo",
                flush=True,
            )
        # TASK 2P: report how often the overlap fade saved a phrase tail
        # from being truncated. overlap_clean = full pcm preserved (best
        # case); overlap_truncate = capped at slot+max_overlap (still
        # better than hard-cut at slot).
        overlap_total = overlap_clean_count + overlap_truncate_count
        if overlap_total > 0:
            print(
                f"     -> Overlap fade applied to {overlap_total} segments "
                f"({overlap_clean_count} clean, {overlap_truncate_count} "
                f"capped at slot+{int(MAX_OVERLAP_FRAMES * 1000 / SR)}ms) "
                f"instead of hard truncate",
                flush=True,
            )
        elif not overlap_fade_enabled:
            print(
                "     -> Overlap fade disabled (--no-overlap-fade); "
                "legacy hard-truncate active",
                flush=True,
            )

        # STEP 1: dump per-segment metrics CSV for cross-video P90/P95 analysis.
        # Best effort: never fail the dubbing pipeline if the file is unwritable.
        if metrics_csv_path:
            try:
                n = dump_segment_metrics(_atempo_stats, metrics_csv_path)
                print(
                    f"     -> Metrics CSV: {n} rows -> {metrics_csv_path}",
                    flush=True,
                )
            except Exception as _csv_err:
                print(
                    f"     ! Metrics CSV dump failed ({_csv_err}); pipeline continues",
                    flush=True,
                )

    # Mix background se disponibile (stessa semantica storica: bg_volume in ampiezza).
    if bg_path and os.path.exists(bg_path) and bg_volume > 0:
        bg_conv = os.path.join(tmp_dir, "_bg_pcm.wav")
        try:
            run_ffmpeg([
                "ffmpeg", "-y", "-i", bg_path,
                "-ar", str(SR), "-ac", str(CH), "-sample_fmt", "s16", bg_conv,
            ], step="bg pcm conv")
            # Streaming read/write per tenere il background fuori dalla RAM.
            CHUNK = SR * 10  # 10s
            with sf.SoundFile(bg_conv, "r") as bgf:
                # Scala su int32 in-place. Ampiezza lineare: 1.0 = unity,
                # >1.0 amplifica (coerente con semantica storica pydub+dB).
                scale = float(bg_volume)
                pos = 0
                while pos < total_frames:
                    want = min(CHUNK, total_frames - pos)
                    block = bgf.read(want, dtype="int16", always_2d=True)
                    if block.shape[0] == 0:
                        break
                    if scale != 1.0:
                        scaled = (block.astype(np.float32) * scale).astype(np.int32)
                    else:
                        scaled = block.astype(np.int32)
                    end_pos = pos + scaled.shape[0]
                    mix[pos:end_pos] += scaled
                    pos = end_pos
        except Exception as e:
            print(f"     ! Background mix failed: {e}", flush=True)

    # Clamp int32 → int16 e serializza in WAV.
    with sf.SoundFile(out, "w", samplerate=SR, channels=CH, subtype="PCM_16") as outf:
        CHUNK = SR * 10
        pos = 0
        while pos < total_frames:
            end = min(pos + CHUNK, total_frames)
            block = mix[pos:end]
            clipped = np.clip(block, -32768, 32767).astype(np.int16)
            outf.write(clipped)
            pos = end

    # Libera la memmap prima di unlink per evitare warning su Windows.
    del mix
    try:
        os.remove(raw_path)
    except OSError:
        pass

    # Normalize to -23 LUFS (EBU R128 broadcast standard).
    # Leggiamo in float32 (dimezza la RAM rispetto al default float64).
    # Per video molto lunghi (>30 min o >1.5 GB) logghiamo un warning: l'intero
    # buffer resta comunque in memoria perché pyln.normalize.loudness richiede
    # l'array completo, ma almeno con float32 siamo gestibili (~1.2 GB per 1h).
    try:
        import pyloudnorm as pyln
        try:
            track_bytes = os.path.getsize(out)
        except OSError:
            track_bytes = 0
        long_track = (total_duration > 1800.0) or (track_bytes > 1_500_000_000)
        if long_track:
            print(
                f"     ! Long track detected (duration={total_duration:.0f}s, "
                f"size={track_bytes/1e6:.0f} MB): LUFS normalization will use "
                f"float32 in-memory buffer.",
                flush=True,
            )
        data, rate = sf.read(out, dtype="float32")
        meter = pyln.Meter(rate)
        loudness = meter.integrated_loudness(data)
        if loudness > -70:
            normalized = pyln.normalize.loudness(data, loudness, -23.0)
            sf.write(out, normalized, rate)
            print(f"     → Normalized: {loudness:.1f} LUFS → -23.0 LUFS", flush=True)
    except Exception as e:
        print(f"     ! Loudness normalization skipped: {e}", flush=True)

    print(f"     → Track: {out}", flush=True)
    return out


