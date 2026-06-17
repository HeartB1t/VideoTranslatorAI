import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


RUN_HEAVY = os.environ.get("VTAI_RUN_HEAVY_SMOKE") == "1"


@unittest.skipUnless(RUN_HEAVY, "set VTAI_RUN_HEAVY_SMOKE=1 to run real AI/GPU smoke tests")
class HeavySmokeTests(unittest.TestCase):
    def test_torch_cuda_is_usable(self):
        import torch

        self.assertTrue(torch.cuda.is_available(), "torch CUDA is not available")
        self.assertGreater(torch.cuda.device_count(), 0)

    def test_ollama_daemon_responds(self):
        if shutil.which("ollama") is None:
            self.skipTest("ollama binary not found")

        proc = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_wav2lip_face_stack_imports(self):
        from videotranslator.wav2lip_runtime import (
            missing_wav2lip_base_packages,
            missing_wav2lip_face_packages,
        )

        self.assertEqual(missing_wav2lip_base_packages(), [])
        self.assertEqual(missing_wav2lip_face_packages(), [])

    def test_whisper_tiny_transcribes_synthetic_speech(self):
        if shutil.which("espeak") is None:
            self.skipTest("espeak not found")

        from videotranslator.transcription import transcribe_audio

        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "whisper_smoke.wav"
            subprocess.run(
                [
                    "espeak",
                    "-w",
                    str(wav_path),
                    "hello world this is a smoke test",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )

            segments, lang = transcribe_audio(str(wav_path), "tiny", "en")

        joined = " ".join(seg.get("text", "") for seg in segments).lower()
        self.assertEqual(lang, "en")
        self.assertIn("hello", joined)
        self.assertIn("smoke", joined)


if __name__ == "__main__":
    unittest.main()
