import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


class RequirementsStaticTests(unittest.TestCase):
    def test_aggregate_requirements_reference_existing_profiles(self):
        lines = _requirement_lines(ROOT / "requirements.txt")
        refs = [line.split(maxsplit=1)[1] for line in lines if line.startswith("-r ")]

        self.assertEqual(
            refs,
            [
                "requirements-core.txt",
                "requirements-optional.txt",
                "requirements-wav2lip.txt",
                "requirements-gpu-cu124.txt",
            ],
        )
        for ref in refs:
            self.assertTrue((ROOT / ref).exists(), ref)

    def test_dev_requirements_match_ci_lightweight_dependencies(self):
        lines = set(_requirement_lines(ROOT / "requirements-dev.txt"))

        self.assertIn("opencv-python-headless", lines)
        self.assertIn("numpy>=2.0,<2.4", lines)
        self.assertIn("soundfile", lines)

    def test_core_and_optional_profiles_keep_expected_runtime_families(self):
        core = set(_requirement_lines(ROOT / "requirements-core.txt"))
        optional = set(_requirement_lines(ROOT / "requirements-optional.txt"))
        wav2lip = set(_requirement_lines(ROOT / "requirements-wav2lip.txt"))
        gpu = set(_requirement_lines(ROOT / "requirements-gpu-cu124.txt"))

        self.assertIn("faster-whisper", core)
        self.assertIn("edge-tts", core)
        self.assertIn("requests", core)
        self.assertIn("coqui-tts>=0.27.5", optional)
        self.assertIn("pyannote.audio>=3.1,<4.0", optional)
        self.assertIn("new-basicsr", wav2lip)
        self.assertIn("facexlib", wav2lip)
        self.assertIn("dlib", wav2lip)
        self.assertIn("torch>=2.6.0,<2.8", gpu)
        self.assertIn("torchaudio==2.6.0", gpu)


if __name__ == "__main__":
    unittest.main()
