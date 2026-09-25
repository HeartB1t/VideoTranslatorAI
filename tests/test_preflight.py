import subprocess
import unittest
from types import SimpleNamespace

from videotranslator.preflight import (
    DEFAULT_OPTIONAL_PACKAGES,
    GB,
    MISSING,
    OK,
    WARN,
    BinaryProbe,
    PackageProbe,
    default_required_packages,
    find_missing_dependencies,
    format_preflight_report,
    libmpv_native_check,
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


from videotranslator.libmpv_runtime import LibmpvStatus

LOADED = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                      path="/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0",
                      vo_profiles_ok=("x11egl", "x11sw"), detail="mpv 0.41.0, client API 2.5")


class LibmpvNativeCheckTests(unittest.TestCase):
    def test_a_loadable_library_is_ok(self):
        check = libmpv_native_check(probe=lambda: LOADED)
        self.assertEqual((check.name, check.status, check.required), ("native:libmpv", OK, False))
        self.assertIn("libmpv.so.2.5.0", check.detail)
        self.assertIn("x11egl", check.detail)

    def test_python_mpv_missing_still_reports_the_library_as_ok(self):
        status = LibmpvStatus(ok=False, reason="python-mpv-missing", path="/usr/lib/libmpv.so.2",
                              detail="mpv 0.41.0, client API 2.5")
        self.assertEqual(libmpv_native_check(probe=lambda: status).status, OK)

    def test_missing_library_warns_when_optional_and_fails_when_required(self):
        missing = LibmpvStatus(ok=False, reason="libmpv-missing", detail="no libmpv.so in ldconfig -p")
        optional = libmpv_native_check(probe=lambda: missing)
        self.assertEqual(optional.status, WARN)
        self.assertTrue(optional.passes)
        required = libmpv_native_check(required=True, probe=lambda: missing)
        self.assertEqual(required.status, MISSING)
        self.assertFalse(required.passes)
        self.assertIn("libmpv-missing", required.detail)
        self.assertTrue(required.hint)

    def test_too_old_and_crashed_carry_their_reason(self):
        for reason in ("libmpv-too-old", "probe-crashed"):
            with self.subTest(reason=reason):
                check = libmpv_native_check(probe=lambda r=reason: LibmpvStatus(ok=False, reason=r))
                self.assertTrue(check.detail.startswith(reason))

    def test_python_mpv_is_an_optional_package_probe(self):
        probes = [p for p in DEFAULT_OPTIONAL_PACKAGES if p.module == "mpv"]
        self.assertEqual(len(probes), 1)
        self.assertEqual((probes[0].pip_name, probes[0].required), ("mpv", False))


class NativeChecksInRunPreflightTests(unittest.TestCase):
    def _report(self, native_checks):
        return run_preflight(
            required_packages={}, optional_packages=(), required_binaries=(), optional_binaries=(),
            version_info=(3, 11, 8), sys_platform="linux", find_spec=lambda name: None,
            which=lambda name: None, disk_usage=lambda path: SimpleNamespace(free=30 * GB),
            native_checks=native_checks)

    def test_native_checks_are_reported_and_can_fail_the_report(self):
        missing = LibmpvStatus(ok=False, reason="libmpv-missing")
        report = self._report((lambda: libmpv_native_check(required=True, probe=lambda: missing),))
        self.assertIn("native:libmpv", [check.name for check in report.checks])
        self.assertFalse(report.ok)
        self.assertTrue(self._report((lambda: libmpv_native_check(probe=lambda: missing),)).ok)

    def test_a_raising_native_check_becomes_a_warning(self):
        def broken():
            raise RuntimeError("boom")

        report = self._report((broken,))
        check = [c for c in report.checks if c.name == "native:check"][0]
        self.assertEqual(check.status, WARN)
        self.assertIn("boom", check.detail)
        self.assertTrue(report.ok)


class PreflightPlayerOptionTests(unittest.TestCase):
    def _options(self, **kwargs):
        from videotranslator.cli import preflight_options

        calls = []
        options = preflight_options(native_check=lambda *, required: calls.append(required) or "check",
                                    **kwargs)
        self.assertEqual(options["native_checks"][0](), "check")
        return options, calls

    def test_the_player_flag_requires_python_mpv_and_libmpv(self):
        options, calls = self._options(lipsync=False, player=True)
        self.assertEqual(options["required_optional_modules"], ("mpv",))
        self.assertEqual(calls, [True])

    def test_lipsync_and_player_combine(self):
        options, _ = self._options(lipsync=True, player=True)
        self.assertEqual(options["required_optional_modules"], ("dlib", "facexlib", "basicsr", "mpv"))

    def test_by_default_the_player_stays_optional(self):
        options, calls = self._options(lipsync=False, player=False)
        self.assertEqual(options["required_optional_modules"], ())
        self.assertEqual(calls, [False])


if __name__ == "__main__":
    unittest.main()
