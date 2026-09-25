"""libmpv detection, probe and import gate (spec 2.2, 3.1, 6.1, 7.2).

Hermetic: every side effect is faked. The two tests that start a real child
interpreter use a garbage library file (a clean OSError, never a crash) and
os._exit (an abnormal exit without a core file).
"""

import contextlib
import ctypes
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

from videotranslator import libmpv_runtime as rt
from videotranslator.libmpv_runtime import LibmpvStatus

LDCONFIG_SAMPLE = (
    "1234 libs found in cache `/etc/ld.so.cache'\n"
    "\tlibmpv.so.2 (libc6,x86-64) => /lib/x86_64-linux-gnu/libmpv.so.2\n"
    "\tlibmpv.so.1 (libc6,x86-64) => /usr/lib/x86_64-linux-gnu/libmpv.so.1\n"
    "\tlibmpv.so.2 (libc6) => /usr/lib/i386-linux-gnu/libmpv.so.2\n"
    "\tlibmpv.so (libc6,x86-64) => /lib/x86_64-linux-gnu/libmpv.so\n"
    "\tlibmpg123.so.0 (libc6,x86-64) => /lib/x86_64-linux-gnu/libmpg123.so.0\n"
)


class FakeLib:
    """ctypes-like stand-in. Plain functions, so the probe can set restype/argtypes."""

    def __init__(self, *, api=(2, 5), version=b"mpv 0.41.0", rejected=("x11vk",), init_rc=0):
        self.handles = 0
        self.destroyed = []
        self.options = {}
        self.freed = []
        self._buf = ctypes.create_string_buffer(version) if version is not None else None
        raw_api = (api[0] << 16) | api[1]
        rejected = set(rejected)

        def mpv_client_api_version():
            return raw_api

        def mpv_create():
            self.handles += 1
            return self.handles

        def mpv_set_option_string(handle, name, value):
            self.options.setdefault(handle, {})[name.decode()] = value.decode()
            return -7 if value.decode() in rejected else 0

        def mpv_initialize(handle):
            return init_rc

        def mpv_get_property_string(handle, name):
            if self._buf is None or name != b"mpv-version":
                return None
            return ctypes.addressof(self._buf)

        def mpv_free(ptr):
            self.freed.append(ptr)

        def mpv_terminate_destroy(handle):
            self.destroyed.append(handle)

        for fn in (mpv_client_api_version, mpv_create, mpv_set_option_string,
                   mpv_initialize, mpv_get_property_string, mpv_free,
                   mpv_terminate_destroy):
            setattr(self, fn.__name__, fn)


def _garbage_library(directory: Path) -> Path:
    name = "mpv-2.dll" if sys.platform == "win32" else "libmpv.so.2"
    path = directory / name
    path.write_bytes(b"this is not a shared library")
    return path


class ParsingTests(unittest.TestCase):
    def test_api_version_splits_major_and_minor(self):
        self.assertEqual(rt.parse_api_version((2 << 16) | 5), (2, 5))
        self.assertEqual(rt.parse_api_version((1 << 16) | 108), (1, 108))

    def test_mpv_version_accepts_releases_and_master_snapshots(self):
        self.assertEqual(rt.parse_mpv_version("mpv 0.41.0"), (0, 41))
        self.assertEqual(rt.parse_mpv_version("mpv v0.41.0-1050-ge76a35ec9"), (0, 41))
        self.assertEqual(rt.parse_mpv_version("mpv 0.34.1"), (0, 34))
        self.assertIsNone(rt.parse_mpv_version("mpv git-master"))
        self.assertIsNone(rt.parse_mpv_version(""))

    def test_ldconfig_picks_the_newest_soname_of_this_architecture(self):
        self.assertEqual(rt.parse_ldconfig(LDCONFIG_SAMPLE, want_64bit=True),
                         "/lib/x86_64-linux-gnu/libmpv.so.2")
        self.assertEqual(rt.parse_ldconfig(LDCONFIG_SAMPLE, want_64bit=False),
                         "/usr/lib/i386-linux-gnu/libmpv.so.2")

    def test_ldconfig_without_libmpv(self):
        self.assertIsNone(rt.parse_ldconfig("\tlibc.so.6 (libc6,x86-64) => /lib/libc.so.6\n"))
        self.assertIsNone(rt.parse_ldconfig(""))

    def test_maps_line_gives_the_mapped_path(self):
        text = ("7f00-7f10 r--p 00000000 08:02 123 /usr/lib/x86_64-linux-gnu/libc.so.6\n"
                "7f20-7f30 r-xp 00001000 08:02 456 /usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0\n")
        self.assertEqual(rt.parse_maps(text), "/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0")
        self.assertIsNone(rt.parse_maps("7f00-7f10 r--p 00000000 00:00 0 [heap]\n"))

    def test_fingerprint_uses_the_real_path_size_and_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "libmpv.so.2.5.0"
            real.write_bytes(b"12345")
            link = Path(tmp) / "libmpv.so.2"
            link.symlink_to(real)
            stat = real.stat()
            self.assertEqual(rt.library_fingerprint(str(link)),
                             f"{os.path.realpath(real)}|5|{stat.st_mtime_ns}")
        self.assertIsNone(rt.library_fingerprint("/no/such/libmpv.so.2"))
        self.assertIsNone(rt.library_fingerprint(None))

    def test_build_txt_is_read_as_key_value_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "BUILD.txt").write_text(
                "# comment\nsource=zhongfly-lgpl\nlicence=LGPL\nbroken line\n", encoding="utf-8")
            self.assertEqual(rt.read_build_txt(Path(tmp)),
                             {"source": "zhongfly-lgpl", "licence": "LGPL"})
            self.assertEqual(rt.read_build_txt(Path(tmp) / "missing"), {})

    def test_ldconfig_cache_reader_tries_the_known_paths(self):
        calls = []

        def run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0, stdout=LDCONFIG_SAMPLE, stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "ldconfig"
            exe.write_text("", encoding="utf-8")
            out = rt.read_ldconfig_cache(run=run, which=lambda name: str(exe))
        self.assertEqual(out, LDCONFIG_SAMPLE)
        self.assertEqual(calls[0][0], [str(exe), "-p"])
        self.assertIs(calls[0][1]["stdin"], subprocess.DEVNULL)


class PathTests(unittest.TestCase):
    def test_windows_candidates_in_order_without_duplicates(self):
        app_dir = Path("C:/Program Files/VideoTranslatorAI")
        env = {"VTAI_LIBMPV_DIR": "D:/dev/mpv", "ProgramFiles": "C:/Program Files",
               "LOCALAPPDATA": "C:/Users/u/AppData/Local"}
        self.assertEqual(rt.windows_candidate_dirs(env, app_dir), [
            Path("D:/dev/mpv"),
            app_dir / "mpv-runtime",
            Path("C:/Users/u/AppData/Local") / "VideoTranslatorAI" / "mpv-runtime",
        ])

    def test_per_user_runtime_dir_is_under_localappdata(self):
        self.assertEqual(rt.per_user_runtime_dir({"LOCALAPPDATA": "C:/Users/u/AppData/Local"}),
                         Path("C:/Users/u/AppData/Local") / "VideoTranslatorAI" / "mpv-runtime")

    def test_vulkan_fallback_next_to_the_dll_then_per_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "machine"
            user = Path(tmp) / "user"
            env = {"LOCALAPPDATA": str(user)}
            self.assertIsNone(rt.find_vulkan_fallback(runtime, env))
            per_user = user / "VideoTranslatorAI" / "mpv-runtime" / "vulkan-fallback"
            per_user.mkdir(parents=True)
            (per_user / "vulkan-1.dll").write_bytes(b"MZ")
            self.assertEqual(rt.find_vulkan_fallback(runtime, env), per_user)
            local = runtime / "vulkan-fallback"
            local.mkdir(parents=True)
            (local / "vulkan-1.dll").write_bytes(b"MZ")
            self.assertEqual(rt.find_vulkan_fallback(runtime, env), local)


class QuickPresenceTests(unittest.TestCase):
    def test_windows_finds_the_runtime_dll_and_its_build_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "VideoTranslatorAI" / "mpv-runtime"
            runtime.mkdir(parents=True)
            (runtime / "mpv-2.dll").write_bytes(b"MZ" + b"0" * 10)
            (runtime / "BUILD.txt").write_text("licence=LGPL\n", encoding="utf-8")
            status = rt.quick_presence(sys_platform="win32", env={"ProgramFiles": tmp},
                                       app_dir=Path(tmp) / "app", find_spec=lambda name: object())
        self.assertTrue(status.ok)
        self.assertEqual(status.reason, "ok")
        self.assertTrue(status.path.endswith("mpv-2.dll"))
        self.assertEqual(status.build, {"licence": "LGPL"})
        self.assertIn("|12|", status.fingerprint)
        self.assertIsNone(status.api_version)  # nothing was loaded

    def test_windows_without_dll(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = rt.quick_presence(sys_platform="win32", env={"ProgramFiles": tmp},
                                       app_dir=Path(tmp), find_spec=lambda name: object())
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertFalse(status.ok)

    def test_library_is_reported_before_python_mpv(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = rt.quick_presence(sys_platform="linux", env={}, app_dir=Path(tmp),
                                       run_ldconfig=lambda: "", find_library=lambda name: None,
                                       find_spec=lambda name: None)
        self.assertEqual(status.reason, "libmpv-missing")

    def test_linux_uses_ldconfig_and_checks_python_mpv(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Path(tmp) / "libmpv.so.2"
            lib.write_bytes(b"\x7fELF")
            sample = f"\tlibmpv.so.2 (libc6,x86-64) => {lib}\n"
            status = rt.quick_presence(sys_platform="linux", env={}, app_dir=Path(tmp),
                                       run_ldconfig=lambda: sample,
                                       find_library=lambda name: None,
                                       find_spec=lambda name: None)
        self.assertEqual(status.reason, "python-mpv-missing")
        self.assertEqual(status.path, str(lib))
        self.assertIsNotNone(status.fingerprint)

    def test_linux_dev_override_directory_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "libmpv.so.2").write_bytes(b"\x7fELF")
            status = rt.quick_presence(sys_platform="linux", env={"VTAI_LIBMPV_DIR": tmp},
                                       app_dir=Path(tmp), run_ldconfig=lambda: "",
                                       find_library=lambda name: None,
                                       find_spec=lambda name: object())
        self.assertTrue(status.ok)
        self.assertEqual(status.path, str(Path(tmp) / "libmpv.so.2"))

    def test_linux_find_library_is_the_last_resort(self):
        status = rt.quick_presence(sys_platform="linux", env={}, app_dir=Path("/nonexistent"),
                                   run_ldconfig=lambda: "",
                                   find_library=lambda name: "libmpv.so.2",
                                   find_spec=lambda name: object())
        self.assertTrue(status.ok)
        self.assertEqual(status.path, "libmpv.so.2")
        self.assertIsNone(status.fingerprint)  # a bare soname cannot be fingerprinted


class ProbeTests(unittest.TestCase):
    def _probe_linux(self, lib, tmp, **kwargs):
        path = Path(tmp) / "libmpv.so.2"
        path.write_bytes(b"\x7fELF")
        maps = f"7f20-7f30 r-xp 00001000 08:02 456 {path}\n"
        return rt.probe_libmpv(sys_platform="linux", env={"VTAI_LIBMPV_DIR": tmp},
                               app_dir=Path(tmp), cdll=lambda p: lib,
                               run_ldconfig=lambda: "", find_library=lambda n: None,
                               read_maps=lambda: maps, **kwargs)

    def test_a_good_library_reports_api_version_and_accepted_profiles(self):
        lib = FakeLib()
        with tempfile.TemporaryDirectory() as tmp:
            status = self._probe_linux(lib, tmp)
        self.assertTrue(status.ok)
        self.assertEqual(status.api_version, (2, 5))
        self.assertEqual(status.mpv_version, (0, 41))
        self.assertEqual(status.vo_profiles_ok, ("x11egl", "x11sw"))
        self.assertNotIn("x11glx", status.vo_profiles_ok)
        self.assertIn("mpv 0.41.0", status.detail)
        # Every handle the probe created was destroyed, and the string freed.
        self.assertEqual(sorted(lib.destroyed), list(range(1, lib.handles + 1)))
        self.assertEqual(len(lib.freed), 1)
        # The version handle ran headless.
        self.assertEqual(lib.options[lib.handles]["vo"], "null")
        self.assertEqual(lib.options[lib.handles]["ao"], "null")

    def test_profiles_use_libmpv_option_names(self):
        lib = FakeLib(rejected=())
        with tempfile.TemporaryDirectory() as tmp:
            self._probe_linux(lib, tmp)
        self.assertEqual(lib.options[1], {"vo": "gpu", "gpu-context": "x11egl"})
        self.assertEqual(lib.options[2], {"vo": "gpu", "gpu-api": "vulkan", "gpu-context": "x11vk"})
        self.assertEqual(lib.options[3], {"vo": "x11"})

    def test_old_api_stops_before_creating_handles(self):
        lib = FakeLib(api=(1, 107))
        with tempfile.TemporaryDirectory() as tmp:
            status = self._probe_linux(lib, tmp)
        self.assertEqual(status.reason, "libmpv-too-old")
        self.assertEqual(status.api_version, (1, 107))
        self.assertEqual(lib.handles, 0)

    def test_release_below_the_tested_floor_is_too_old(self):
        lib = FakeLib(api=(1, 109), version=b"mpv 0.32.0")
        with tempfile.TemporaryDirectory() as tmp:
            status = self._probe_linux(lib, tmp)
        self.assertEqual(status.reason, "libmpv-too-old")
        self.assertEqual(status.mpv_version, (0, 32))

    def test_unknown_mpv_version_keeps_the_library_usable(self):
        lib = FakeLib(init_rc=-1)
        with tempfile.TemporaryDirectory() as tmp:
            status = self._probe_linux(lib, tmp)
        self.assertTrue(status.ok)
        self.assertIsNone(status.mpv_version)
        self.assertIn("mpv version unknown", status.detail)

    def test_missing_symbol_means_too_old(self):
        lib = FakeLib()
        del lib.mpv_client_api_version
        with tempfile.TemporaryDirectory() as tmp:
            status = self._probe_linux(lib, tmp)
        self.assertEqual(status.reason, "libmpv-too-old")

    def test_load_error_is_classified(self):
        def cdll(path):
            raise OSError("invalid ELF header")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "libmpv.so.2").write_bytes(b"x")
            status = rt.probe_libmpv(sys_platform="linux", env={}, app_dir=Path(tmp),
                                     runtime_dir=Path(tmp), cdll=cdll)
        self.assertEqual(status.reason, "libmpv-load-failed")
        self.assertIn("invalid ELF header", status.detail)

    def test_windows_126_without_vulkan_loader(self):
        def cdll(path):
            exc = OSError("[WinError 126] The specified module could not be found")
            exc.winerror = 126
            raise exc

        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "rt"
            runtime.mkdir()
            (runtime / "mpv-2.dll").write_bytes(b"MZ")
            status = rt.probe_libmpv(sys_platform="win32", env={"LOCALAPPDATA": tmp},
                                     app_dir=Path(tmp), runtime_dir=runtime, cdll=cdll,
                                     add_dll_directory=lambda d: None,
                                     system32=Path(tmp) / "System32")
        self.assertEqual(status.reason, "vulkan-loader-missing")

    def test_windows_vulkan_fallback_is_added_before_loading(self):
        added = []
        lib = FakeLib(rejected=())
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "rt"
            (runtime / "vulkan-fallback").mkdir(parents=True)
            (runtime / "vulkan-fallback" / "vulkan-1.dll").write_bytes(b"MZ")
            (runtime / "mpv-2.dll").write_bytes(b"MZ")
            status = rt.probe_libmpv(sys_platform="win32", env={"LOCALAPPDATA": tmp},
                                     app_dir=Path(tmp), runtime_dir=runtime,
                                     cdll=lambda p: lib, add_dll_directory=added.append,
                                     system32=Path(tmp) / "System32")
        self.assertTrue(status.ok)
        self.assertEqual(added, [str(runtime / "vulkan-fallback")])
        self.assertEqual(status.vo_profiles_ok, ("auto", "d3d11-warp"))
        rt._DLL_DIR_HANDLES.clear()


class ClassifyTests(unittest.TestCase):
    def test_classification_table(self):
        c = rt.classify_import_error
        self.assertEqual(c(ModuleNotFoundError("No module named 'mpv'"), sys_platform="linux",
                           vulkan_present=True), "python-mpv-missing")
        self.assertEqual(c(OSError("Cannot find libmpv in the usual places"), sys_platform="linux",
                           vulkan_present=True), "libmpv-missing")
        self.assertEqual(c(OSError("libfoo.so: cannot open shared object file"),
                           sys_platform="linux", vulkan_present=True), "libmpv-load-failed")
        self.assertEqual(c(AttributeError("mpv_render_context_create"), sys_platform="linux",
                           vulkan_present=True), "libmpv-too-old")
        self.assertEqual(c(RuntimeError("python-mpv requires libmpv with an API version of 1.108"),
                           sys_platform="linux", vulkan_present=True), "libmpv-too-old")
        self.assertEqual(c(RuntimeError("other"), sys_platform="linux", vulkan_present=True),
                         "libmpv-load-failed")

    def test_windows_126_depends_on_the_vulkan_loader(self):
        cause = OSError("[WinError 126]")
        cause.winerror = 126
        wrapped = OSError("ctypes.find_library found mpv.dll at X, but ctypes.CDLL could not load it.")
        wrapped.__cause__ = cause
        self.assertEqual(rt.classify_import_error(wrapped, sys_platform="win32",
                                                  vulkan_present=False), "vulkan-loader-missing")
        self.assertEqual(rt.classify_import_error(wrapped, sys_platform="win32",
                                                  vulkan_present=True), "libmpv-load-failed")


OK_JSON = rt.status_to_json(LibmpvStatus(
    ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
    path="/usr/lib/libmpv.so.2.5.0", vo_profiles_ok=("x11egl", "x11sw"),
    detail="mpv 0.41.0, client API 2.5", fingerprint="/usr/lib/libmpv.so.2.5.0|1|2"))


class JsonAndSubprocessTests(unittest.TestCase):
    def test_json_round_trip(self):
        status = rt.status_from_json("some warning\n" + OK_JSON + "\n")
        self.assertEqual(status.api_version, (2, 5))
        self.assertEqual(status.vo_profiles_ok, ("x11egl", "x11sw"))
        self.assertTrue(status.ok)

    def test_unknown_reason_or_garbage_is_rejected(self):
        self.assertIsNone(rt.status_from_json('{"ok": true, "reason": "maybe"}'))
        self.assertIsNone(rt.status_from_json("{not json"))
        self.assertIsNone(rt.status_from_json(""))

    def test_probe_in_subprocess_parses_the_child_output(self):
        seen = {}

        def run(cmd, **kwargs):
            seen["cmd"], seen["kwargs"] = cmd, kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout=OK_JSON + "\n", stderr="")

        status = rt.probe_in_subprocess(run=run, python="py", runtime_dir=Path("/rt"),
                                        cwd=Path("/app"), sys_platform="linux")
        self.assertTrue(status.ok)
        self.assertEqual(seen["cmd"], ["py", "-m", "videotranslator.libmpv_runtime", "check",
                                       "--json", "--dir", str(Path("/rt"))])
        self.assertEqual(seen["kwargs"]["cwd"], str(Path("/app")))
        self.assertIs(seen["kwargs"]["stdin"], subprocess.DEVNULL)
        self.assertEqual(seen["kwargs"]["timeout"], rt.PROBE_TIMEOUT_S)
        self.assertNotIn("creationflags", seen["kwargs"])

    def test_unavailable_exit_code_still_carries_the_status(self):
        missing = rt.status_to_json(LibmpvStatus(ok=False, reason="libmpv-missing"))

        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 2, stdout=missing, stderr="")

        self.assertEqual(rt.probe_in_subprocess(run=run).reason, "libmpv-missing")

    def test_windows_child_gets_no_console(self):
        seen = {}

        def run(cmd, **kwargs):
            seen.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout=OK_JSON, stderr="")

        rt.probe_in_subprocess(run=run, sys_platform="win32")
        self.assertEqual(seen["creationflags"], 0x08000000)

    def test_crash_without_json_is_probe_crashed(self):
        def run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, -11, stdout="", stderr="Segmentation fault")

        status = rt.probe_in_subprocess(run=run)
        self.assertEqual(status.reason, "probe-crashed")
        self.assertIn("-11", status.detail)

    def test_timeout_and_start_failure_are_probe_crashed(self):
        def slow(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        def missing(cmd, **kwargs):
            raise OSError("no python")

        self.assertEqual(rt.probe_in_subprocess(run=slow).reason, "probe-crashed")
        self.assertEqual(rt.probe_in_subprocess(run=missing).reason, "probe-crashed")

    def test_a_real_child_that_dies_is_probe_crashed(self):
        def run(cmd, **kwargs):
            # A real abnormal exit with no JSON (os._exit leaves no core file).
            return subprocess.run([sys.executable, "-c", "import os; os._exit(134)"], **kwargs)

        self.assertEqual(rt.probe_in_subprocess(run=run).reason, "probe-crashed")

    def test_real_check_subprocess_on_a_garbage_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            _garbage_library(Path(tmp))
            status = rt.probe_in_subprocess(runtime_dir=Path(tmp))
        self.assertEqual(status.reason, "libmpv-load-failed")


class MainTests(unittest.TestCase):
    def test_check_json_on_a_garbage_library_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            _garbage_library(Path(tmp))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = rt.main(["check", "--json", "--dir", tmp])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue().strip().splitlines()[-1])["reason"],
                         "libmpv-load-failed")

    def test_usage_errors_exit_3_and_help_exits_0(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(rt.main([]), 3)
            self.assertEqual(rt.main(["check", "--bogus"]), 3)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rt.main(["--help"]), 0)


QUICK_OK = LibmpvStatus(ok=True, reason="ok", path="/usr/lib/libmpv.so.2",
                        fingerprint="/usr/lib/libmpv.so.2.5.0|10|20")
PROBE_OK = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                        path="/usr/lib/libmpv.so.2.5.0", vo_profiles_ok=("x11egl", "x11sw"),
                        detail="mpv 0.41.0, client API 2.5",
                        fingerprint="/usr/lib/libmpv.so.2.5.0|10|20")
CACHED = {"fingerprint": "/usr/lib/libmpv.so.2.5.0|10|20", "ok": True, "api": [2, 5],
          "mpv_version": [0, 41], "vo_profiles_ok": ["x11egl", "x11sw"]}


class ResolveStatusTests(unittest.TestCase):
    def _resolve(self, quick, probe=PROBE_OK, **kwargs):
        calls = []

        def probe_fn():
            calls.append(1)
            return probe

        status = rt.resolve_status(quick=lambda: quick, probe=probe_fn, **kwargs)
        return status, calls

    def test_missing_library_never_probes(self):
        status, calls = self._resolve(LibmpvStatus(ok=False, reason="libmpv-missing"))
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertEqual(calls, [])

    def test_a_matching_cache_skips_the_probe(self):
        status, calls = self._resolve(QUICK_OK, cached=CACHED)
        self.assertEqual(calls, [])
        self.assertEqual(status.mpv_version, (0, 41))
        self.assertEqual(status.vo_profiles_ok, ("x11egl", "x11sw"))

    def test_a_stale_cache_or_force_probe_runs_the_probe(self):
        stale = dict(CACHED, fingerprint="/usr/lib/libmpv.so.2.4.0|9|9")
        self.assertEqual(self._resolve(QUICK_OK, cached=stale)[1], [1])
        self.assertEqual(self._resolve(QUICK_OK, cached=CACHED, force_probe=True)[1], [1])

    def test_a_failed_probe_wins(self):
        crashed = LibmpvStatus(ok=False, reason="probe-crashed", detail="exit code -11")
        status, _ = self._resolve(QUICK_OK, probe=crashed)
        self.assertEqual(status.reason, "probe-crashed")

    def test_python_mpv_verdict_comes_from_this_process(self):
        quick = LibmpvStatus(ok=False, reason="python-mpv-missing", path=QUICK_OK.path,
                             fingerprint=QUICK_OK.fingerprint)
        status, _ = self._resolve(quick)
        self.assertEqual(status.reason, "python-mpv-missing")
        self.assertFalse(status.ok)
        self.assertEqual(status.api_version, (2, 5))

    def test_cache_entry_only_for_probed_loadable_libraries(self):
        self.assertEqual(rt.cache_entry(PROBE_OK), CACHED)
        self.assertIsNone(rt.cache_entry(QUICK_OK))
        self.assertIsNone(rt.cache_entry(LibmpvStatus(ok=False, reason="probe-crashed")))

    def test_malformed_cache_is_ignored(self):
        for bad in (None, [], {"ok": True}, dict(CACHED, api="2.5"), dict(CACHED, ok=False)):
            with self.subTest(bad=bad):
                self.assertIsNone(rt.status_from_cache(QUICK_OK, bad))


class ImportGateTests(unittest.TestCase):
    def setUp(self):
        rt._DLL_DIR_HANDLES.clear()
        rt._MPV_MODULE = None

    tearDown = setUp

    def test_windows_prepends_the_runtime_dir_and_restores_path(self):
        env = {"PATH": "C:/Windows;C:/Python311"}
        restore = rt.prepare_import(env, sys_platform="win32", runtime_dir=Path("C:/VT/mpv-runtime"),
                                    add_dll_directory=None, system32_has_vulkan=True)
        self.assertTrue(env["PATH"].startswith(str(Path("C:/VT/mpv-runtime")) + ";"))
        restore()
        self.assertEqual(env, {"PATH": "C:/Windows;C:/Python311"})

    def test_vulkan_fallback_dir_only_when_system32_lacks_the_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            (runtime / "vulkan-fallback").mkdir()
            (runtime / "vulkan-fallback" / "vulkan-1.dll").write_bytes(b"MZ")
            added = []
            rt.prepare_import({"LOCALAPPDATA": tmp}, sys_platform="win32", runtime_dir=runtime,
                              add_dll_directory=lambda d: added.append(d) or "handle",
                              system32_has_vulkan=True)
            self.assertEqual(added, [])
            restore = rt.prepare_import({"LOCALAPPDATA": tmp}, sys_platform="win32",
                                        runtime_dir=runtime,
                                        add_dll_directory=lambda d: added.append(d) or "handle",
                                        system32_has_vulkan=False)
            restore()
            self.assertEqual(added, [str(runtime / "vulkan-fallback")])
            self.assertEqual(rt._DLL_DIR_HANDLES, ["handle"])  # kept after restore

    def test_linux_is_a_no_op(self):
        env = {"PATH": "/usr/bin"}
        rt.prepare_import(env, sys_platform="linux", runtime_dir=Path("/x"),
                          add_dll_directory=None, system32_has_vulkan=True)()
        self.assertEqual(env, {"PATH": "/usr/bin"})

    def test_load_mpv_imports_once(self):
        module = types.ModuleType("mpv")
        calls = []

        def importer(name):
            calls.append(name)
            return module

        self.assertIs(rt.load_mpv(importer=importer, sys_platform="linux"), module)
        self.assertIs(rt.load_mpv(importer=importer, sys_platform="linux"), module)
        self.assertEqual(calls, ["mpv"])

    def test_load_mpv_failure_raises_player_unavailable_and_restores_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "mpv-runtime"
            runtime.mkdir()
            (runtime / "mpv-2.dll").write_bytes(b"MZ")
            env = {"PATH": "C:/Windows", "LOCALAPPDATA": tmp}

            def importer(name):
                self.assertTrue(env["PATH"].startswith(str(runtime)))
                raise OSError("Cannot find mpv-1.dll, mpv-2.dll or libmpv-2.dll in your system %PATH%.")

            with self.assertRaises(rt.PlayerUnavailable) as ctx:
                rt.load_mpv(importer=importer, sys_platform="win32", env=env, app_dir=Path(tmp),
                            add_dll_directory=lambda d: None, system32=Path(tmp))
        self.assertEqual(ctx.exception.status.reason, "libmpv-missing")
        self.assertEqual(env["PATH"], "C:/Windows")
        self.assertIsNone(rt._MPV_MODULE)


class MessageHelperTests(unittest.TestCase):
    def test_version_text(self):
        self.assertEqual(rt.format_version(PROBE_OK), "0.41")
        self.assertEqual(rt.format_version(LibmpvStatus(ok=True, reason="ok", api_version=(2, 5))),
                         "API 2.5")
        self.assertEqual(rt.format_version(QUICK_OK), "?")

    def test_status_message_keys_and_params(self):
        msg = rt.status_message
        self.assertEqual(msg(PROBE_OK, sys_platform="linux"), ("player_badge_ok", {"version": "0.41"}))
        missing = LibmpvStatus(ok=False, reason="libmpv-missing")
        self.assertEqual(msg(missing, sys_platform="linux", install_cmd="sudo apt install libmpv2"),
                         ("player_missing_libmpv_linux", {"cmd": "sudo apt install libmpv2"}))
        self.assertEqual(msg(missing, sys_platform="win32"), ("player_missing_libmpv_win", {}))
        old = LibmpvStatus(ok=False, reason="libmpv-too-old", mpv_version=(0, 32))
        self.assertEqual(msg(old, sys_platform="linux"), ("player_libmpv_too_old", {"version": "0.32"}))
        failed = LibmpvStatus(ok=False, reason="libmpv-load-failed", detail="x" * 300)
        key, params = msg(failed, sys_platform="win32")
        self.assertEqual(key, "player_libmpv_load_failed")
        self.assertLessEqual(len(params["detail"]), 120)
        for reason in ("python-mpv-missing", "vulkan-loader-missing", "probe-crashed",
                       "restart-required"):
            self.assertEqual(msg(LibmpvStatus(ok=False, reason=reason), sys_platform="linux")[1], {})

    def test_badge_levels(self):
        self.assertEqual(rt.badge_level(PROBE_OK), "ok")
        for reason in ("libmpv-too-old", "libmpv-load-failed", "probe-crashed"):
            self.assertEqual(rt.badge_level(LibmpvStatus(ok=False, reason=reason)), "error")
        for reason in ("python-mpv-missing", "libmpv-missing", "vulkan-loader-missing",
                       "restart-required"):
            self.assertEqual(rt.badge_level(LibmpvStatus(ok=False, reason=reason)), "warn")

    def test_install_is_offered_only_where_it_can_help(self):
        def offers(reason, platform):
            return rt.offers_install(LibmpvStatus(ok=False, reason=reason), sys_platform=platform)

        self.assertTrue(offers("python-mpv-missing", "linux"))
        self.assertTrue(offers("libmpv-missing", "linux"))
        self.assertTrue(offers("libmpv-missing", "win32"))
        self.assertTrue(offers("vulkan-loader-missing", "win32"))
        for reason in ("libmpv-too-old", "libmpv-load-failed", "probe-crashed", "restart-required"):
            self.assertFalse(offers(reason, "win32"))
            self.assertFalse(offers(reason, "linux"))
        self.assertFalse(rt.offers_install(PROBE_OK, sys_platform="linux"))

    def test_download_size_includes_vulkan_only_when_needed(self):
        self.assertEqual(rt.windows_download_mb(vulkan=False), 32)
        self.assertEqual(rt.windows_download_mb(vulkan=True), 50)


if __name__ == "__main__":
    unittest.main()
