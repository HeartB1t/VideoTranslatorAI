import subprocess
import unittest
from types import SimpleNamespace

from videotranslator.preflight import (
    GB,
    BinaryProbe,
    PackageProbe,
    default_required_packages,
    find_missing_dependencies,
    format_preflight_report,
    run_preflight,
)


class PreflightDependencyTests(unittest.TestCase):
    def test_find_missing_dependencies_uses_injected_probes(self):
        def fake_find_spec(name):
            return object() if name == "edge_tts" else None

        def fake_which(name):
            return "/usr/bin/ffmpeg" if name == "ffmpeg" else None

        missing_pkgs, missing_bins = find_missing_dependencies(
            {"edge_tts": "edge-tts", "demucs": "demucs"},
            required_binaries=("ffmpeg", "ffprobe"),
            find_spec=fake_find_spec,
            which=fake_which,
        )

        self.assertEqual(missing_pkgs, ["demucs"])
        self.assertEqual(missing_bins, ["ffprobe"])

    def test_default_required_packages_adds_audioop_on_python_313(self):
        self.assertEqual(default_required_packages((3, 12, 9)).get("audioop"), None)
        self.assertEqual(default_required_packages((3, 13, 0))["audioop"], "audioop-lts")

    def test_empty_required_packages_are_honoured(self):
        missing_pkgs, missing_bins = find_missing_dependencies(
            {},
            required_binaries=(),
            find_spec=lambda _name: None,
            which=lambda _name: None,
        )

        self.assertEqual(missing_pkgs, [])
        self.assertEqual(missing_bins, [])


class PreflightReportTests(unittest.TestCase):
    def test_report_fails_only_on_required_missing_checks(self):
        def fake_find_spec(name):
            return object() if name == "present_mod" else None

        def fake_which(_name):
            return None

        def fake_run(*_args, **_kwargs):
            return subprocess.CompletedProcess(["nvidia-smi"], 0, stdout="")

        def fake_disk_usage(_path):
            return SimpleNamespace(free=25 * GB)

        report = run_preflight(
            required_packages={
                "present_mod": "present-pkg",
                "missing_mod": "missing-pkg",
            },
            optional_packages=(PackageProbe("optional_mod", "optional-pkg", False),),
            required_binaries=("ffmpeg",),
            optional_binaries=(BinaryProbe("ollama", False),),
            version_info=(3, 11, 8),
            sys_platform="linux",
            find_spec=fake_find_spec,
            which=fake_which,
            run=fake_run,
            disk_usage=fake_disk_usage,
        )

        self.assertFalse(report.ok)
        self.assertEqual(
            [check.name for check in report.required_failures],
            ["python:missing_mod", "binary:ffmpeg"],
        )

    def test_format_report_lists_result_and_failures(self):
        def fake_find_spec(_name):
            return None

        def fake_which(_name):
            return None

        def fake_disk_usage(_path):
            return SimpleNamespace(free=30 * GB)

        report = run_preflight(
            required_packages={"missing_mod": "missing-pkg"},
            optional_packages=(),
            required_binaries=(),
            optional_binaries=(),
            version_info=(3, 11, 8),
            sys_platform="linux",
            find_spec=fake_find_spec,
            which=fake_which,
            disk_usage=fake_disk_usage,
        )
        text = format_preflight_report(report)

        self.assertIn("VideoTranslatorAI preflight", text)
        self.assertIn("[MISSING] python:missing_mod", text)
        self.assertIn("Result: FAILED", text)

    def test_required_optional_modules_fail_report_when_missing(self):
        def fake_find_spec(_name):
            return None

        def fake_which(_name):
            return "/usr/bin/tool"

        def fake_disk_usage(_path):
            return SimpleNamespace(free=30 * GB)

        report = run_preflight(
            required_packages={},
            optional_packages=(PackageProbe("dlib", "dlib", False, "face stack"),),
            required_optional_modules=("dlib",),
            required_binaries=(),
            optional_binaries=(),
            version_info=(3, 11, 8),
            sys_platform="linux",
            find_spec=fake_find_spec,
            which=fake_which,
            disk_usage=fake_disk_usage,
        )

        self.assertFalse(report.ok)
        self.assertEqual([check.name for check in report.required_failures], ["python:dlib"])


if __name__ == "__main__":
    unittest.main()
