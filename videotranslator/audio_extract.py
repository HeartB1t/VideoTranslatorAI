"""Audio/music extraction: a format catalogue, pure ffmpeg command builders
and an orchestrator that ties URL download, optional Demucs vocal removal and
the final ffmpeg conversion together.

This module keeps every decision testable: the catalogue is data, the command
builders are pure, and ``extract_music`` takes injectable runners so the tests
never touch the network, ffmpeg or Demucs.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from videotranslator.input_source import (
    download_audio_url,
    is_probable_url,
    normalize_input_path,
)
from videotranslator.media import run_ffmpeg, separate_instrumental


@dataclass(frozen=True)
class AudioFormat:
    """One output format in the extraction catalogue."""

    key: str
    label: str
    ext: str
    codec: str
    lossy: bool
    default_bitrate: int | None = None
    bitrates: tuple[int, ...] = field(default_factory=tuple)


# Ordered catalogue (dict preserves insertion order). The order is the one the
# GUI dropdown and the CLI ``--audio-format`` choices present to the user.
AUDIO_FORMATS: dict[str, AudioFormat] = {
    "mp3": AudioFormat("mp3", "MP3", ".mp3", "libmp3lame", True, 192,
                       (128, 192, 256, 320)),
    "m4a": AudioFormat("m4a", "M4A (AAC)", ".m4a", "aac", True, 192,
                       (128, 192, 256)),
    "opus": AudioFormat("opus", "Opus", ".opus", "libopus", True, 128,
                        (96, 128, 160, 192)),
    "ogg": AudioFormat("ogg", "OGG (Vorbis)", ".ogg", "libvorbis", True, 192,
                       (128, 192, 256)),
    "flac": AudioFormat("flac", "FLAC (lossless)", ".flac", "flac", False),
    "wav": AudioFormat("wav", "WAV (lossless)", ".wav", "pcm_s16le", False),
}


def _format(fmt_key: str) -> AudioFormat:
    """Return the catalogue entry or raise a clear ValueError."""
    try:
        return AUDIO_FORMATS[fmt_key]
    except KeyError:
        raise ValueError(
            f"unknown audio format {fmt_key!r}; choose one of "
            f"{', '.join(AUDIO_FORMATS)}"
        ) from None


def format_keys() -> list[str]:
    """Return the format keys in catalogue order."""
    return list(AUDIO_FORMATS)


def format_label(fmt_key: str) -> str:
    """Return the UI label for a format."""
    return _format(fmt_key).label


def is_lossy(fmt_key: str) -> bool:
    """Return True when the format is a lossy codec (has a bitrate)."""
    return _format(fmt_key).lossy


def default_bitrate(fmt_key: str) -> int | None:
    """Return the default bitrate in kbps, or None for lossless formats."""
    return _format(fmt_key).default_bitrate


def allowed_bitrates(fmt_key: str) -> tuple[int, ...]:
    """Return the bitrates (kbps) a lossy format accepts, () for lossless."""
    return _format(fmt_key).bitrates


def _resolve_bitrate(fmt: AudioFormat, bitrate: int | None) -> int | None:
    """Pick the bitrate to use. None -> default. An explicit value outside the
    allowed table is a mistake and raises, so the user is never silently given
    a different quality than they asked for."""
    if not fmt.lossy:
        return None
    if bitrate is None:
        return fmt.default_bitrate
    if bitrate not in fmt.bitrates:
        raise ValueError(
            f"bitrate {bitrate}k is not allowed for {fmt.key}; "
            f"allowed: {', '.join(str(b) for b in fmt.bitrates)}"
        )
    return bitrate


def build_convert_cmd(
    input_path: str,
    output_path: str,
    fmt_key: str,
    *,
    bitrate: int | None = None,
) -> list[str]:
    """Return a pure ffmpeg command converting one input to the target format.

    ``-vn`` always drops any video stream. Lossy formats get ``-b:a <n>k``;
    lossless formats (flac, wav) get no bitrate and ignore a stray ``bitrate``.
    An unknown format or a disallowed explicit bitrate raises ValueError.
    """
    fmt = _format(fmt_key)
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-c:a", fmt.codec]
    resolved = _resolve_bitrate(fmt, bitrate)
    if resolved is not None:
        cmd += ["-b:a", f"{resolved}k"]
    cmd.append(output_path)
    return cmd


def resolve_output_path(
    input_path: str,
    out_dir: str,
    fmt_key: str,
    *,
    instrumental: bool = False,
) -> str:
    """Return the output path: input stem + optional ' (instrumental)' suffix +
    the format extension, inside ``out_dir``."""
    fmt = _format(fmt_key)
    stem = os.path.splitext(os.path.basename(str(input_path)))[0]
    if instrumental:
        stem = f"{stem} (instrumental)"
    return os.path.join(str(out_dir), stem + fmt.ext)


def extract_music(
    source: str,
    out_dir: str,
    *,
    fmt: str = "mp3",
    bitrate: int | None = None,
    instrumental: bool = False,
    log_cb: Callable[[str], None] | None = None,
    ytdlp_cls: Callable[[dict[str, Any]], Any] | None = None,
    ffmpeg_runner: Callable[[list[str], str], Any] = run_ffmpeg,
    downloader: Callable[..., str] = download_audio_url,
    separator: Callable[..., str] = separate_instrumental,
) -> str:
    """Extract audio from a local file or URL into ``out_dir`` and return the
    final output path.

    - A URL source is downloaded audio-only into a temp dir first.
    - ``instrumental=True`` removes the voice with Demucs (a temp wav), then the
      ffmpeg conversion runs on that wav; otherwise it runs on the source.
    - Temporary files live in a TemporaryDirectory and are cleaned up on exit.

    ``ffmpeg_runner``, ``downloader`` and ``separator`` are injectable so tests
    never run ffmpeg, the network or Demucs.
    """
    _format(fmt)  # validate before any download/conversion work
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vtai-extract-") as tmp:
        if is_probable_url(source):
            media_path = downloader(source, tmp, ytdlp_cls=ytdlp_cls, log_cb=log_cb)
        else:
            media_path = normalize_input_path(source)

        out_path = resolve_output_path(media_path, out_dir, fmt,
                                       instrumental=instrumental)

        if instrumental:
            instrumental_wav = os.path.join(tmp, "instrumental.wav")
            convert_source = separator(media_path, instrumental_wav, log_cb=log_cb)
        else:
            convert_source = media_path

        ffmpeg_runner(
            build_convert_cmd(convert_source, out_path, fmt, bitrate=bitrate),
            "extract audio",
        )

    if log_cb is not None:
        log_cb(f"     -> {out_path}")
    return out_path
