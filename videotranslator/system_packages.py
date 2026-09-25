"""Linux package plans for libmpv and the component installer (spec 2.2, 6.1, 8.2).

Pure planning (package manager, package names, privilege chain, commands)
plus side-effecting helpers that take their runner as a parameter:
run_streaming (one command, each output line to the log) and
ComponentInstaller (pip, then a system plan or the Windows DLL install, then
an import-path refresh, on a worker thread, reporting once on Tk).

Plain `sudo` is never tried: it reads the password from the terminal, which
a GUI app does not have ([CT] R5). `pacman -Sy` is never used (partial
upgrades). Installer children are not registered for kill-on-close: killing
a package manager mid-install can leave a broken package state.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import shutil
import site
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import libmpv_runtime
from .subprocess_utils import (
    command_for_log,
    no_window_kwargs,
    normalize_command,
    text_subprocess_kwargs,
)

MANAGERS = ("apt-get", "dnf", "pacman", "zypper")
GENERIC_PACKAGE_HINT = "libmpv2 / mpv-libs / mpv"
INSTALL_TIMEOUT_S = 900.0   # a pkexec password prompt plus a slow mirror
_MANUAL = {
    "apt-get": "sudo apt install {packages}",
    "dnf": "sudo dnf install {packages}",
    "pacman": "sudo pacman -S {packages}",
    "zypper": "sudo zypper install {packages}",
}


def detect_manager(which: Callable[[str], str | None] = shutil.which) -> str | None:
    for manager in MANAGERS:
        if which(manager):
            return manager
    return None


def apt_cache_has(package: str, *, run: Callable[..., Any] = subprocess.run) -> bool:
    """True when `apt-cache show <package>` knows the package."""
    try:
        proc = run(["apt-cache", "show", package], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=20, check=False,
                   stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def libmpv_packages(manager: str, *, apt_has: Callable[[str], bool] | None) -> tuple[str, ...]:
    """The runtime package that provides libmpv (spec 8.2 table)."""
    if manager == "apt-get":
        has = apt_has or apt_cache_has
        return ("libmpv2",) if has("libmpv2") else ("libmpv1",)
    return {"dnf": ("mpv-libs",), "pacman": ("mpv",), "zypper": ("libmpv2",)}[manager]


def privilege_prefixes(which: Callable[[str], str | None] = shutil.which, *,
                       is_root: bool = False) -> list[list[str]]:
    """The privilege chain of a GUI app: pkexec, then `sudo -n` (cached credentials only)."""
    if is_root:
        return [[]]
    prefixes: list[list[str]] = []
    if which("pkexec"):
        prefixes.append(["pkexec"])
    if which("sudo"):
        prefixes.append(["sudo", "-n"])
    return prefixes


def build_install_plan(manager: str, packages: Sequence[str], prefix: Sequence[str]) -> list[list[str]]:
    base, pkgs = list(prefix), list(packages)
    if manager == "apt-get":
        return [base + ["apt-get", "update"], base + ["apt-get", "install", "-y", *pkgs]]
    if manager == "dnf":
        return [base + ["dnf", "install", "-y", *pkgs]]
    if manager == "pacman":
        return [base + ["pacman", "-S", "--needed", "--noconfirm", *pkgs]]
    if manager == "zypper":
        return [base + ["zypper", "--non-interactive", "install", *pkgs]]
    raise ValueError(f"unknown package manager: {manager}")


def manual_command(manager: str | None, packages: Sequence[str]) -> str:
    """The command shown to the user: the {cmd} of player_missing_libmpv_linux."""
    template = _MANUAL.get(manager or "")
    if template is None or not packages:
        return GENERIC_PACKAGE_HINT
    return template.format(packages=" ".join(packages))


def run_streaming(cmd: Sequence[str], *, log: Callable[[str], None],
                  timeout_s: float = INSTALL_TIMEOUT_S,
                  popen: Callable[..., Any] = subprocess.Popen,
                  sys_platform: str = sys.platform) -> int:
    """Run one command (stdin=DEVNULL, no console window), each output line to ``log``.

    Returns the exit code, or -1 when the command cannot start or the
    watchdog kills it after ``timeout_s``. The watchdog also closes our end of
    the pipe, so a child that stalls without closing stdout cannot block the
    read loop (the pattern of App._install_deps).
    """
    argv = normalize_command(cmd)
    log(f"    Running: {command_for_log(argv)}")
    try:
        proc = popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, **text_subprocess_kwargs(sys_platform),
                     **no_window_kwargs(sys_platform))
    except OSError as exc:
        log(f"    ! cannot start {argv[0]}: {exc}")
        return -1
    timed_out = threading.Event()

    def _kill() -> None:
        timed_out.set()
        with contextlib.suppress(Exception):
            proc.kill()
        with contextlib.suppress(Exception):
            proc.stdout.close()

    watchdog = threading.Timer(timeout_s, _kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"    {line}")
        proc.wait(timeout=30)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()
            proc.wait(timeout=30)
    finally:
        watchdog.cancel()
    if timed_out.is_set():
        log(f"    ! {argv[0]} timed out after {timeout_s:.0f} s")
        return -1
    return proc.returncode if proc.returncode is not None else -1


def run_plan(plan: Sequence[Sequence[str]], *, runner: Callable[[Sequence[str]], int],
             log: Callable[[str], None]) -> bool:
    """Run the commands in order; stop at the first non-zero exit."""
    for cmd in plan:
        code = runner(cmd)
        if code != 0:
            log(f"    ! {command_for_log(cmd)} exited with code {code}")
            return False
    return True


def pip_install_command(python: str, packages: Sequence[str]) -> list[str]:
    """The flags of App._install_deps, so the package lands where today's installs land."""
    return [python, "-m", "pip", "install", "--break-system-packages", "--no-color", *packages]


def refresh_import_paths(*, importlib_module: Any = importlib, site_module: Any = site,
                         sys_path: list[str] | None = None,
                         isdir: Callable[[str], bool] = os.path.isdir) -> None:
    """Make a package installed during this run importable without a restart ([CC] G3, C59).

    A user site folder created by this pip run did not exist at interpreter
    start, so site.py did not put it on sys.path.
    """
    sys_path = sys.path if sys_path is None else sys_path
    importlib_module.invalidate_caches()
    if not getattr(site_module, "ENABLE_USER_SITE", False):
        return
    user_site = site_module.getusersitepackages()
    if user_site and isdir(user_site) and user_site not in sys_path:
        site_module.addsitedir(user_site)


def _present(find_spec: Callable[[str], Any], name: str) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


@dataclass(frozen=True)
class InstallResult:
    ok: bool
    restart_required: bool
    failed_step: str | None


class ComponentInstaller:
    """Installs optional components on a worker and reports once through ``post``.

    It never touches the GUI flag of a running job and never chains the
    Italian-only optional popup (spec 2.2): the GUI keeps its own
    `_installing` flag. (A test greps this module for the job flag's name.)
    """

    def __init__(self, *, runner: Callable[[Sequence[str]], int],
                 thread_factory: Callable[..., Any], find_spec: Callable[[str], Any],
                 refresh: Callable[[], None], log: Callable[[str], None],
                 post: Callable[[Callable[[], None]], None], python: str = sys.executable) -> None:
        self._runner = runner
        self._thread_factory = thread_factory
        self._find_spec = find_spec
        self._refresh = refresh
        self._log = log
        self._post = post
        self._python = python

    def install(self, *, pip_packages: Sequence[str] = (),
                system_plans: Sequence[Sequence[Sequence[str]]] = (),
                windows_install: Callable[[], libmpv_runtime.LibmpvStatus] | None = None,
                expect_modules: Sequence[str] = (),
                on_done: Callable[[InstallResult], None]) -> None:
        """Start the worker; ``system_plans`` are alternatives tried in order (one per privilege prefix)."""
        def work() -> None:
            result = self._run(tuple(pip_packages), tuple(system_plans), windows_install,
                               tuple(expect_modules))
            self._post(lambda: on_done(result))

        self._thread_factory(target=work, name="component-install", daemon=True).start()

    def _run(self, pip_packages, system_plans, windows_install, expect_modules) -> InstallResult:
        step = "pip"
        try:
            if pip_packages:
                self._log(f"[*] Installing: {' '.join(pip_packages)}")
                if self._runner(pip_install_command(self._python, pip_packages)) != 0:
                    return InstallResult(False, False, "pip")
            step = "system"
            if system_plans and not any(run_plan(plan, runner=self._runner, log=self._log)
                                        for plan in system_plans):
                return InstallResult(False, False, "system")
            step = "windows"
            if windows_install is not None:
                status = windows_install()
                if not libmpv_runtime.library_loaded(status):
                    self._log(f"[!] libmpv install: {status.reason} ({status.detail})")
                    return InstallResult(False, False, "windows")
            step = "refresh"
            self._refresh()
            missing = [name for name in expect_modules if not _present(self._find_spec, name)]
            if missing:
                self._log(f"[!] Installed, but not importable until a restart: {', '.join(missing)}")
            return InstallResult(True, bool(missing), None)
        except Exception as exc:
            self._log(f"[!] Installation step '{step}' failed: {exc}")
            return InstallResult(False, False, step)


@dataclass(frozen=True)
class PlayerInstallRequest:
    """What the Install button of the player placeholder does (computed off the Tk thread)."""

    pip_packages: tuple[str, ...] = ()
    system_plans: tuple[tuple[tuple[str, ...], ...], ...] = ()
    windows_dest: Path | None = None
    download_mb: int = 0
    manual_command: str | None = None

    @property
    def empty(self) -> bool:
        return not (self.pip_packages or self.system_plans or self.windows_dest is not None)


def player_install_request(status: libmpv_runtime.LibmpvStatus, *, sys_platform: str,
                           mpv_importable: bool,
                           which: Callable[[str], str | None] = shutil.which,
                           apt_has: Callable[[str], bool] | None = None,
                           is_root: bool | None = None,
                           env: dict[str, str] | None = None) -> PlayerInstallRequest:
    """The install actions for ``status`` (spec 6.1 rows 1-3, 5; Q6). May run apt-cache: call off Tk."""
    manual = None
    plans: tuple[tuple[tuple[str, ...], ...], ...] = ()
    if sys_platform != "win32" and status.reason == "libmpv-missing":
        manager = detect_manager(which)
        packages = libmpv_packages(manager, apt_has=apt_has) if manager else ()
        manual = manual_command(manager, packages)
        if manager:
            if is_root is None:
                is_root = hasattr(os, "geteuid") and os.geteuid() == 0
            plans = tuple(tuple(tuple(cmd) for cmd in build_install_plan(manager, packages, prefix))
                          for prefix in privilege_prefixes(which, is_root=bool(is_root)))
    if not libmpv_runtime.offers_install(status, sys_platform=sys_platform):
        return PlayerInstallRequest(manual_command=manual)
    pip = () if mpv_importable else (libmpv_runtime.PYTHON_MPV_REQUIREMENT,)
    if sys_platform == "win32":
        if status.reason in ("libmpv-missing", "vulkan-loader-missing"):
            return PlayerInstallRequest(
                pip_packages=pip, windows_dest=libmpv_runtime.per_user_runtime_dir(env),
                download_mb=libmpv_runtime.windows_download_mb(
                    vulkan=status.reason == "vulkan-loader-missing"))
        return PlayerInstallRequest(pip_packages=pip)
    return PlayerInstallRequest(pip_packages=pip, system_plans=plans, manual_command=manual)
