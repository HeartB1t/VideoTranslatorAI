import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from videotranslator.media import extract_audio
from videotranslator.output_media import get_duration, mux_video, save_subtitles


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "ffmpeg and ffprobe are required for e2e-lite media smoke test",
)
class E2ELiteMediaTests(unittest.TestCase):
    def test_synthetic_video_extract_subtitle_and_mux_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            source = tmp / "source.mp4"
            extracted_audio = tmp / "audio.wav"
            output_base = tmp / "dubbed"
            output_video = tmp / "dubbed.mp4"

            self._create_synthetic_video(source)

            logs: list[str] = []
            extract_audio(str(source), str(extracted_audio), log_cb=logs.append)
            srt_path = save_subtitles(
                [{"start": 0.0, "end": 1.0, "text_tgt": "ciao"}],
                str(output_base),
                log=lambda *_args, **_kwargs: None,
            )
            mux_video(
                str(source),
                str(extracted_audio),
                str(output_video),
                log=lambda *_args, **_kwargs: None,
            )

            self.assertTrue(extracted_audio.exists())
            self.assertGreater(extracted_audio.stat().st_size, 1024)
            self.assertTrue(output_video.exists())
            self.assertGreater(output_video.stat().st_size, 1024)
            self.assertTrue(Path(srt_path).exists())
            self.assertGreater(get_duration(str(output_video)), 0.5)
            self.assertIn("[1/6] Extracting audio from: source.mp4", logs)
            self.assertIn("00:00:00,000 --> 00:00:01,000", Path(srt_path).read_text())

    def _create_synthetic_video(self, output: Path) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=96x64:rate=10:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1",
            "-shortest",
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        if proc.returncode != 0:
            self.skipTest(f"ffmpeg synthetic fixture failed: {proc.stderr.strip()}")


if __name__ == "__main__":
    unittest.main()
