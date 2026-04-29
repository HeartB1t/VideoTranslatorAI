"""Pre-Wav2Lip face detection.

Wav2Lip reads every video frame, runs face detection on each, and aborts
with ``ValueError("Face not detected!")`` after ~30-60 seconds when none
of the frames contains a face. For voice-only content (podcasts, screen
recordings, presentations with slides, voice-over animations, audio with
title cards) this is a guaranteed failure that wastes compute and
confuses the user.

This module front-loads the check by sampling N frames from the video
and running OpenCV's pre-trained Haar Cascade frontal face classifier
on each. The classifier is fast (~10-20ms per 720p frame on CPU),
ships with ``opencv-python`` (already a Wav2Lip dependency), and has
no startup cost beyond loading the cascade XML once.

The module exposes a single decision helper, ``has_enough_faces()``, that
returns a boolean and the underlying ratio so callers can both gate
Wav2Lip and report the reason in logs.

The implementation is kept I/O-thin (pure OpenCV calls + ``ffmpeg``
subprocess for sampling) so it can be exercised by unit tests with
synthetic frames without spinning up the full pipeline.
"""

from __future__ import annotations

import os
import subprocess
from typing import Iterable

# Default fraction of sampled frames that must contain at least one face
# for the video to be considered "face content". 0.20 keeps the check
# tolerant of hybrid videos (e.g. interview with cutaway b-roll) while
# still skipping voice-only material with high confidence.
DEFAULT_MIN_FACE_RATIO = 0.20

# Default number of frames to sample. 15 is enough to land at least one
# face in any video where the speaker is on camera most of the time,
# and small enough to keep the check under a second on CPU.
DEFAULT_SAMPLE_FRAMES = 15


def _haar_cascade_path() -> str:
    """Locate the bundled Haar Cascade XML.

    Imported lazily so the module can be loaded by unit tests on
    machines without OpenCV. When OpenCV is installed (the production
    case, since cv2 is already required by Wav2Lip), the cascade ships
    with the wheel.
    """
    import cv2  # local import to keep the module importable without cv2

    return os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")


def count_faces_in_frame(frame_path: str) -> int:
    """Return the number of faces detected in ``frame_path``.

    Returns 0 if the file is missing or unreadable: callers treat
    "couldn't read frame" the same as "no face here".
    """
    import cv2

    if not os.path.exists(frame_path):
        return 0
    img = cv2.imread(frame_path)
    if img is None:
        return 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(_haar_cascade_path())
    if cascade.empty():
        return 0
    # scaleFactor 1.1 / minNeighbors 5 are the OpenCV docs defaults and
    # keep false-positives low enough for our gating purpose. We are
    # not measuring face area, just presence/absence.
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
    )
    return len(faces)


def count_face_frames(frame_paths: Iterable[str]) -> tuple[int, int]:
    """Count how many frames in ``frame_paths`` contain at least one face.

    Returns ``(face_frames, total_frames)``.
    """
    face = 0
    total = 0
    for path in frame_paths:
        total += 1
        if count_faces_in_frame(path) > 0:
            face += 1
    return face, total


def compute_face_ratio(face_frames: int, total_frames: int) -> float:
    """Return ``face_frames / total_frames`` clamped to ``[0.0, 1.0]``.

    A separate helper so callers and tests can reason about the ratio
    without owning a frame list. Returns ``0.0`` for empty input rather
    than raising — "no frames sampled" should not be a hard error.
    """
    if total_frames <= 0:
        return 0.0
    if face_frames < 0:
        return 0.0
    if face_frames > total_frames:
        return 1.0
    return face_frames / total_frames


def decide_has_faces(
    face_ratio: float,
    min_face_ratio: float = DEFAULT_MIN_FACE_RATIO,
) -> bool:
    """Decision rule on the sampled face ratio.

    Pure boolean policy — kept separate from the I/O so unit tests can
    exercise the threshold without sampling real frames.
    """
    if min_face_ratio <= 0:
        return face_ratio > 0
    return face_ratio >= min_face_ratio


def sample_frames_via_ffmpeg(
    video_path: str,
    out_dir: str,
    n_samples: int = DEFAULT_SAMPLE_FRAMES,
) -> list[str]:
    """Extract ``n_samples`` evenly distributed JPEG frames from ``video_path``.

    Uses ``ffmpeg`` with the ``select`` filter so the output frames are
    spread uniformly through the video duration. Returns the list of
    written frame paths (only those that ffmpeg actually produced — some
    videos may yield fewer frames than requested if very short).
    """
    if n_samples <= 0:
        return []
    if not os.path.exists(video_path):
        return []
    os.makedirs(out_dir, exist_ok=True)

    # ffprobe duration to compute uniform timestamps. If ffprobe fails
    # we fall back to a "1 frame every N frames" filter instead, which
    # is cheaper but less uniform.
    duration_s = _probe_duration_seconds(video_path)
    pattern = os.path.join(out_dir, "frame_%03d.jpg")

    if duration_s and duration_s > 0:
        # Uniform sampling at fixed timestamps
        interval = duration_s / (n_samples + 1)
        timestamps = [interval * (i + 1) for i in range(n_samples)]
        # Build a single-pass ffmpeg select filter that keeps only the
        # frames closest to our target timestamps. Simpler: extract one
        # frame per ffmpeg call, more robust on weird containers.
        produced: list[str] = []
        for idx, ts in enumerate(timestamps):
            out = os.path.join(out_dir, f"frame_{idx:03d}.jpg")
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", f"{ts:.3f}", "-i", video_path,
                "-frames:v", "1", "-q:v", "3", out,
            ]
            try:
                subprocess.run(
                    cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    timeout=15,
                )
            except (subprocess.SubprocessError, OSError):
                continue
            if os.path.exists(out) and os.path.getsize(out) > 0:
                produced.append(out)
        return produced

    # Duration unknown: use a select filter that picks every Nth frame
    # of the input stream. We do not know how many frames will land, so
    # we cap to n_samples by trusting ffmpeg to honour the count.
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", video_path,
        "-vf", f"select='not(mod(n\\,{max(1, 10)}))',setpts=N/FRAME_RATE/TB",
        "-frames:v", str(n_samples), "-q:v", "3", pattern,
    ]
    try:
        subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    return sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir)
        if f.startswith("frame_") and f.endswith(".jpg")
    )


def _probe_duration_seconds(video_path: str) -> float:
    """Return video duration in seconds via ``ffprobe``, or ``0.0``."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=10,
        )
        if proc.returncode == 0:
            return float((proc.stdout or "").strip() or 0.0)
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return 0.0


def has_enough_faces(
    video_path: str,
    out_dir: str,
    n_samples: int = DEFAULT_SAMPLE_FRAMES,
    min_face_ratio: float = DEFAULT_MIN_FACE_RATIO,
) -> tuple[bool, float, int, int]:
    """End-to-end decision: does ``video_path`` contain enough faces for Wav2Lip?

    Returns a tuple ``(has_faces, ratio, face_frames, total_frames)``.
    Caller can log all four values regardless of the decision.

    The ``out_dir`` is used as a working directory for the sampled JPEGs
    and is left in place — caller is expected to put it under a temp
    directory that gets cleaned up at the end of the pipeline.
    """
    frames = sample_frames_via_ffmpeg(video_path, out_dir, n_samples=n_samples)
    face, total = count_face_frames(frames)
    ratio = compute_face_ratio(face, total)
    decision = decide_has_faces(ratio, min_face_ratio=min_face_ratio)
    return decision, ratio, face, total
