import re
import tomllib
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
                "requirements-player.txt",
            ],
        )
        for ref in refs:
            self.assertTrue((ROOT / ref).exists(), ref)

    def test_dev_requirements_match_ci_lightweight_dependencies(self):
        lines = set(_requirement_lines(ROOT / "requirements-dev.txt"))

        self.assertIn("opencv-python-headless", lines)
        self.assertIn("numpy>=2.0,<2.4", lines)
        self.assertIn("soundfile", lines)
        # The CI "validate package metadata" step runs pip with
        # --no-build-isolation, so the [build-system] backend must be
        # installed explicitly: Python 3.12+ venvs no longer ship setuptools.
        self.assertIn("setuptools>=69", lines)
        self.assertIn("wheel", lines)

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


    def test_player_profile_pins_python_mpv_everywhere_the_same(self):
        from videotranslator.libmpv_runtime import PYTHON_MPV_REQUIREMENT

        self.assertEqual(PYTHON_MPV_REQUIREMENT, "mpv>=1.0.6,<2")
        self.assertEqual(_requirement_lines(ROOT / "requirements-player.txt"), [PYTHON_MPV_REQUIREMENT])
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["optional-dependencies"]["player"], [PYTHON_MPV_REQUIREMENT])

    def test_no_other_new_requirement_file_or_package(self):
        names = sorted(path.name for path in ROOT.glob("requirements*.txt"))
        self.assertEqual(names, [
            "requirements-core.txt", "requirements-dev.txt", "requirements-gpu-cu124.txt",
            "requirements-optional.txt", "requirements-player.txt", "requirements-wav2lip.txt",
            "requirements.txt",
        ])
        for name in names:
            for line in _requirement_lines(ROOT / name):
                package = re.split(r"[<>=!~;\[\s]", line, maxsplit=1)[0].lower()
                with self.subTest(file=name, line=line):
                    # av and onnxruntime arrive with faster-whisper (spec R8);
                    # python-mpv would install a second mpv.py.
                    self.assertNotIn(package, {"av", "onnxruntime", "python-mpv"})
        dev = {re.split(r"[<>=!~;\[\s]", line, maxsplit=1)[0].lower()
               for line in _requirement_lines(ROOT / "requirements-dev.txt")}
        self.assertNotIn("mpv", dev)  # CI must never import a python-mpv without libmpv

    def test_gitignore_keeps_player_binaries_out_of_git(self):
        lines = {line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
        for entry in ("mpv-runtime/", "*.dll", "*.7z"):
            self.assertIn(entry, lines)

if __name__ == "__main__":
    unittest.main()
