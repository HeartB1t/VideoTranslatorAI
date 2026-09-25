"""Linux package plans and ComponentInstaller (spec 2.2, 6.1, 8.2). Hermetic."""

import inspect
import subprocess
import threading
import types
import unittest
from pathlib import Path

from videotranslator import system_packages as sp
from videotranslator.libmpv_runtime import PYTHON_MPV_REQUIREMENT, LibmpvStatus


def _which(*present):
    return lambda name: f"/usr/bin/{name}" if name in present else None


class _InlineThread:
    def __init__(self, target, name=None, daemon=None):
        self.target, self.name, self.daemon = target, name, daemon

    def start(self):
        self.target()


class ManagerAndPackageTests(unittest.TestCase):
    def test_manager_detection_order(self):
        self.assertEqual(sp.detect_manager(_which("apt-get", "dnf")), "apt-get")
        self.assertEqual(sp.detect_manager(_which("dnf")), "dnf")
        self.assertEqual(sp.detect_manager(_which("pacman")), "pacman")
        self.assertEqual(sp.detect_manager(_which("zypper")), "zypper")
        self.assertIsNone(sp.detect_manager(_which()))

    def test_apt_prefers_libmpv2_then_libmpv1(self):
        self.assertEqual(sp.libmpv_packages("apt-get", apt_has=lambda p: p == "libmpv2"), ("libmpv2",))
        self.assertEqual(sp.libmpv_packages("apt-get", apt_has=lambda p: False), ("libmpv1",))

    def test_other_managers(self):
        self.assertEqual(sp.libmpv_packages("dnf", apt_has=None), ("mpv-libs",))
        self.assertEqual(sp.libmpv_packages("pacman", apt_has=None), ("mpv",))
        self.assertEqual(sp.libmpv_packages("zypper", apt_has=None), ("libmpv2",))

    def test_apt_cache_has(self):
        calls = []

        def found(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0, stdout="Package: libmpv2\n", stderr="")

        def missing(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 100, stdout="", stderr="E: No packages found")

        def broken(cmd, **kwargs):
            raise OSError("no apt-cache")

        self.assertTrue(sp.apt_cache_has("libmpv2", run=found))
        self.assertEqual(calls[0][0], ["apt-cache", "show", "libmpv2"])
        self.assertIs(calls[0][1]["stdin"], subprocess.DEVNULL)
        self.assertFalse(sp.apt_cache_has("libmpv2", run=missing))
        self.assertFalse(sp.apt_cache_has("libmpv2", run=broken))


class PlanTests(unittest.TestCase):
    def test_privilege_chain_is_pkexec_then_sudo_n_never_plain_sudo(self):
        prefixes = sp.privilege_prefixes(_which("pkexec", "sudo"), is_root=False)
        self.assertEqual(prefixes, [["pkexec"], ["sudo", "-n"]])
        self.assertNotIn(["sudo"], prefixes)
        self.assertEqual(sp.privilege_prefixes(_which("sudo"), is_root=False), [["sudo", "-n"]])
        self.assertEqual(sp.privilege_prefixes(_which(), is_root=False), [])
        self.assertEqual(sp.privilege_prefixes(_which("pkexec"), is_root=True), [[]])

    def test_plans_per_manager(self):
        self.assertEqual(sp.build_install_plan("apt-get", ["libmpv2"], ["pkexec"]), [
            ["pkexec", "apt-get", "update"], ["pkexec", "apt-get", "install", "-y", "libmpv2"]])
        self.assertEqual(sp.build_install_plan("dnf", ["mpv-libs"], ["sudo", "-n"]),
                         [["sudo", "-n", "dnf", "install", "-y", "mpv-libs"]])
        pacman = sp.build_install_plan("pacman", ["mpv"], [])
        self.assertEqual(pacman, [["pacman", "-S", "--needed", "--noconfirm", "mpv"]])
        self.assertFalse(any("-Sy" in cmd for cmd in pacman))
        self.assertEqual(sp.build_install_plan("zypper", ["libmpv2"], ["pkexec"]),
                         [["pkexec", "zypper", "--non-interactive", "install", "libmpv2"]])
        with self.assertRaises(ValueError):
            sp.build_install_plan("emerge", ["mpv"], [])

    def test_manual_command(self):
        self.assertEqual(sp.manual_command("apt-get", ["libmpv2"]), "sudo apt install libmpv2")
        self.assertEqual(sp.manual_command("dnf", ["mpv-libs"]), "sudo dnf install mpv-libs")
        self.assertEqual(sp.manual_command("pacman", ["mpv"]), "sudo pacman -S mpv")
        self.assertEqual(sp.manual_command("zypper", ["libmpv2"]), "sudo zypper install libmpv2")
        self.assertEqual(sp.manual_command(None, ()), sp.GENERIC_PACKAGE_HINT)

    def test_pip_command_uses_the_flags_of_install_deps(self):
        self.assertEqual(sp.pip_install_command("py", [PYTHON_MPV_REQUIREMENT]),
                         ["py", "-m", "pip", "install", "--break-system-packages", "--no-color",
                          "mpv>=1.0.6,<2"])


class _FakePopen:
    last = None

    def __init__(self, argv, **kwargs):
        _FakePopen.last = (argv, kwargs)
        self.stdout = iter(["line one\n", "\n", "line two\n"])
        self.returncode = None

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def kill(self):
        pass


class _HangingPopen:
    def __init__(self, argv, **kwargs):
        self.killed = threading.Event()
        self.returncode = None
        self.stdout = self._lines()

    def _lines(self):
        self.killed.wait(5)
        yield from ()

    def wait(self, timeout=None):
        self.returncode = -9
        return -9

    def kill(self):
        self.killed.set()


class RunStreamingTests(unittest.TestCase):
    def test_output_lines_reach_the_log_and_stdin_is_devnull(self):
        lines = []
        code = sp.run_streaming(["apt-get", "update"], log=lines.append, popen=_FakePopen,
                                sys_platform="linux")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["    Running: apt-get update", "    line one", "    line two"])
        argv, kwargs = _FakePopen.last
        self.assertEqual(argv, ["apt-get", "update"])
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.STDOUT)
        self.assertNotIn("creationflags", kwargs)

    def test_windows_children_have_no_console(self):
        sp.run_streaming(["py", "-m", "pip"], log=lambda line: None, popen=_FakePopen,
                         sys_platform="win32")
        self.assertEqual(_FakePopen.last[1]["creationflags"], 0x08000000)
        self.assertEqual(_FakePopen.last[1]["encoding"], "utf-8")

    def test_a_start_failure_is_minus_one(self):
        def popen(argv, **kwargs):
            raise OSError("pkexec not found")

        lines = []
        self.assertEqual(sp.run_streaming(["pkexec", "x"], log=lines.append, popen=popen), -1)
        self.assertIn("pkexec not found", lines[-1])

    def test_the_watchdog_kills_a_stalled_child(self):
        lines = []
        code = sp.run_streaming(["pkexec", "apt-get", "update"], log=lines.append,
                                popen=_HangingPopen, timeout_s=0.01)
        self.assertEqual(code, -1)
        self.assertTrue(any("timed out" in line for line in lines))

    def test_run_plan_stops_at_the_first_failure(self):
        seen = []

        def runner(cmd):
            seen.append(cmd)
            return 1 if cmd[0] == "b" else 0

        lines = []
        self.assertFalse(sp.run_plan([["a"], ["b"], ["c"]], runner=runner, log=lines.append))
        self.assertEqual(seen, [["a"], ["b"]])
        self.assertIn("exited with code 1", lines[-1])
        self.assertTrue(sp.run_plan([["a"]], runner=runner, log=lines.append))


class RefreshImportPathsTests(unittest.TestCase):
    def _fakes(self, *, enabled=True):
        calls = []
        importlib_fake = types.SimpleNamespace(invalidate_caches=lambda: calls.append("invalidate"))
        site_fake = types.SimpleNamespace(
            ENABLE_USER_SITE=enabled,
            getusersitepackages=lambda: "/home/u/.local/lib/python3.13/site-packages",
            addsitedir=lambda d: calls.append(("add", d)))
        return calls, importlib_fake, site_fake

    def test_a_user_site_created_during_the_run_is_added(self):
        calls, imp, site = self._fakes()
        sp.refresh_import_paths(importlib_module=imp, site_module=site,
                                sys_path=["/usr/lib/python3"], isdir=lambda p: True)
        self.assertEqual(calls, ["invalidate", ("add", "/home/u/.local/lib/python3.13/site-packages")])

    def test_existing_missing_or_disabled_user_site_is_left_alone(self):
        calls, imp, site = self._fakes()
        sp.refresh_import_paths(importlib_module=imp, site_module=site,
                                sys_path=["/home/u/.local/lib/python3.13/site-packages"],
                                isdir=lambda p: True)
        sp.refresh_import_paths(importlib_module=imp, site_module=site, sys_path=[],
                                isdir=lambda p: False)
        self.assertEqual(calls, ["invalidate", "invalidate"])
        calls, imp, site = self._fakes(enabled=False)
        sp.refresh_import_paths(importlib_module=imp, site_module=site, sys_path=[],
                                isdir=lambda p: True)
        self.assertEqual(calls, ["invalidate"])


class ComponentInstallerTests(unittest.TestCase):
    def _installer(self, *, failing=(), importable=("mpv",)):
        self.commands, self.lines, self.refreshed = [], [], []
        failing = set(failing)

        def runner(cmd):
            self.commands.append(list(cmd))
            return 1 if failing.intersection(cmd) else 0

        return sp.ComponentInstaller(
            runner=runner, thread_factory=_InlineThread,
            find_spec=lambda name: object() if name in importable else None,
            refresh=lambda: self.refreshed.append(True), log=self.lines.append,
            post=lambda fn: fn(), python="py")

    def _install(self, installer, **kwargs):
        results = []
        installer.install(on_done=results.append, **kwargs)
        self.assertEqual(len(results), 1)  # on_done exactly once
        return results[0]

    def test_pip_then_the_system_plan_then_refresh(self):
        result = self._install(
            self._installer(), pip_packages=[PYTHON_MPV_REQUIREMENT],
            system_plans=[[["pkexec", "apt-get", "update"],
                           ["pkexec", "apt-get", "install", "-y", "libmpv2"]]],
            expect_modules=["mpv"])
        self.assertEqual(result, sp.InstallResult(ok=True, restart_required=False, failed_step=None))
        self.assertEqual(self.commands[0], ["py", "-m", "pip", "install", "--break-system-packages",
                                            "--no-color", "mpv>=1.0.6,<2"])
        self.assertEqual(self.commands[1:], [["pkexec", "apt-get", "update"],
                                             ["pkexec", "apt-get", "install", "-y", "libmpv2"]])
        self.assertEqual(self.refreshed, [True])

    def test_the_next_privilege_plan_runs_when_the_first_fails(self):
        result = self._install(self._installer(failing={"pkexec"}),
                               system_plans=[[["pkexec", "apt-get", "update"]],
                                             [["sudo", "-n", "apt-get", "update"]]],
                               expect_modules=["mpv"])
        self.assertTrue(result.ok)
        self.assertEqual(self.commands, [["pkexec", "apt-get", "update"],
                                         ["sudo", "-n", "apt-get", "update"]])

    def test_every_plan_failing_is_a_system_failure(self):
        result = self._install(self._installer(failing={"pkexec", "sudo"}),
                               system_plans=[[["pkexec", "x"]], [["sudo", "-n", "x"]]])
        self.assertEqual(result, sp.InstallResult(ok=False, restart_required=False, failed_step="system"))
        self.assertEqual(self.refreshed, [])

    def test_a_pip_failure_stops_before_the_system_step(self):
        result = self._install(self._installer(failing={"pip"}), pip_packages=["mpv"],
                               system_plans=[[["pkexec", "x"]]])
        self.assertEqual(result.failed_step, "pip")
        self.assertEqual(len(self.commands), 1)

    def test_a_module_still_missing_after_refresh_needs_a_restart(self):
        result = self._install(self._installer(importable=()), pip_packages=["mpv"],
                               expect_modules=["mpv"])
        self.assertEqual(result, sp.InstallResult(ok=True, restart_required=True, failed_step=None))

    def test_the_windows_install_status_decides(self):
        good = LibmpvStatus(ok=True, reason="ok")
        mpv_missing = LibmpvStatus(ok=False, reason="python-mpv-missing")
        bad = LibmpvStatus(ok=False, reason="libmpv-missing", detail="no build")
        self.assertTrue(self._install(self._installer(), windows_install=lambda: good).ok)
        self.assertTrue(self._install(self._installer(), windows_install=lambda: mpv_missing).ok)
        self.assertEqual(self._install(self._installer(), windows_install=lambda: bad).failed_step,
                         "windows")

    def test_an_exception_is_reported_once_as_the_failed_step(self):
        def boom():
            raise RuntimeError("disk full")

        result = self._install(self._installer(), windows_install=boom)
        self.assertEqual(result, sp.InstallResult(ok=False, restart_required=False, failed_step="windows"))
        self.assertTrue(any("disk full" in line for line in self.lines))

    def test_it_runs_on_the_injected_thread_and_posts_the_callback(self):
        started, posted = [], []

        class RecordingThread(_InlineThread):
            def start(self):
                started.append((self.name, self.daemon))
                super().start()

        installer = sp.ComponentInstaller(
            runner=lambda cmd: 0, thread_factory=RecordingThread, find_spec=lambda n: object(),
            refresh=lambda: None, log=lambda line: None, post=posted.append)
        called = []
        installer.install(on_done=called.append)
        self.assertEqual(started, [("component-install", True)])
        self.assertEqual(len(posted), 1)
        self.assertEqual(called, [])  # only through post, never directly from the worker
        posted[0]()
        self.assertEqual(len(called), 1)

    def test_the_installer_never_touches_the_gui_running_flag(self):
        self.assertNotIn("_running", inspect.getsource(sp))


class PlayerInstallRequestTests(unittest.TestCase):
    def _request(self, reason, platform, *, importable=False, which=None, env=None):
        return sp.player_install_request(
            LibmpvStatus(ok=reason == "ok", reason=reason), sys_platform=platform,
            mpv_importable=importable, which=which or _which("apt-get", "pkexec", "sudo"),
            apt_has=lambda p: p == "libmpv2", is_root=False,
            env=env or {"LOCALAPPDATA": "C:/Users/u/AppData/Local"})

    def test_linux_missing_library(self):
        req = self._request("libmpv-missing", "linux")
        self.assertEqual(req.pip_packages, (PYTHON_MPV_REQUIREMENT,))
        self.assertEqual(req.system_plans, (
            (("pkexec", "apt-get", "update"), ("pkexec", "apt-get", "install", "-y", "libmpv2")),
            (("sudo", "-n", "apt-get", "update"), ("sudo", "-n", "apt-get", "install", "-y", "libmpv2")),
        ))
        self.assertEqual(req.manual_command, "sudo apt install libmpv2")
        self.assertIsNone(req.windows_dest)
        self.assertFalse(req.empty)
        self.assertEqual(self._request("libmpv-missing", "linux", importable=True).pip_packages, ())

    def test_linux_without_a_package_manager_keeps_the_generic_hint(self):
        req = self._request("libmpv-missing", "linux", which=_which("pkexec"))
        self.assertEqual(req.system_plans, ())
        self.assertEqual(req.manual_command, sp.GENERIC_PACKAGE_HINT)

    def test_linux_python_mpv_only(self):
        req = self._request("python-mpv-missing", "linux")
        self.assertEqual(req.pip_packages, (PYTHON_MPV_REQUIREMENT,))
        self.assertEqual(req.system_plans, ())
        self.assertIsNone(req.manual_command)

    def test_windows_per_user_install_sizes(self):
        req = self._request("libmpv-missing", "win32")
        self.assertEqual(req.windows_dest,
                         Path("C:/Users/u/AppData/Local") / "VideoTranslatorAI" / "mpv-runtime")
        self.assertEqual(req.download_mb, 32)
        self.assertEqual(req.system_plans, ())
        self.assertEqual(self._request("vulkan-loader-missing", "win32").download_mb, 50)
        only_pip = self._request("python-mpv-missing", "win32")
        self.assertIsNone(only_pip.windows_dest)
        self.assertEqual(only_pip.pip_packages, (PYTHON_MPV_REQUIREMENT,))

    def test_nothing_to_install(self):
        for reason, platform in (("ok", "linux"), ("libmpv-too-old", "linux"),
                                 ("libmpv-load-failed", "win32"), ("probe-crashed", "win32"),
                                 ("vulkan-loader-missing", "linux")):
            with self.subTest(reason=reason, platform=platform):
                self.assertTrue(self._request(reason, platform).empty)


if __name__ == "__main__":
    unittest.main()
