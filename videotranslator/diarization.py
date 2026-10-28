"""Speaker diarization (pyannote) and speaker assignment to Whisper segments."""

from __future__ import annotations

import contextlib

DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"


def diarize_audio(audio_path: str, hf_token: str) -> list[dict]:
    """Run pyannote speaker-diarization-3.1. Returns [{start,end,speaker}, ...]."""
    from pyannote.audio import Pipeline
    print("[3b] Running speaker diarization (pyannote)...", flush=True)
    # None before the try, so the finally block works if from_pretrained raises.
    pipeline = None
    try:
        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=hf_token)
        try:
            import torch
            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
        except Exception:
            pass
        diarization = pipeline(audio_path)
        segments: list[dict] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({"start": float(turn.start), "end": float(turn.end), "speaker": str(speaker)})
        speakers = sorted({s["speaker"] for s in segments})
        print(f"     → {len(segments)} diarization turns | {len(speakers)} speakers: {', '.join(speakers)}", flush=True)
        return segments
    finally:
        with contextlib.suppress(Exception):
            if pipeline is not None:
                del pipeline
            import torch
            torch.cuda.empty_cache()


def assign_speakers(whisper_segments: list[dict], diar_segments: list[dict]) -> list[dict]:
    """For each Whisper segment, assign the speaker with the largest temporal overlap."""
    if not diar_segments:
        return whisper_segments
    for seg in whisper_segments:
        s_start = seg["start"]
        s_end = seg["end"]
        best_speaker = None
        best_overlap = 0.0
        for d in diar_segments:
            overlap = max(0.0, min(s_end, d["end"]) - max(s_start, d["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d["speaker"]
        if best_speaker is not None:
            seg["speaker"] = best_speaker
    return whisper_segments
