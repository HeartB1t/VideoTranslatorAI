# Integrated Player P1: Runtime Detection and Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect, probe and install libmpv and python-mpv on Linux and Windows, and show the result in the GUI (a header "Player" badge plus a placeholder in the left pane that states the reason and offers Install). No playback yet: P1 ships alone and only explains status.

**Architecture:** Two new pure modules carry the logic with every side effect injected: `videotranslator/libmpv_runtime.py` (find, subprocess probe, Windows installer, the only `import mpv`, a `python -m` CLI) and `videotranslator/system_packages.py` (Linux package-manager plans, the privilege chain, `ComponentInstaller`). The Tk glue lives in `videotranslator/player_panel_tk.py`, the strings in `videotranslator/ui_strings_player.py`, and `video_translator_gui.py` receives wiring only. In P1 libmpv is loaded ONLY in a child process (`python -m videotranslator.libmpv_runtime check`), never in the GUI process.

**Tech Stack:** Python 3.10-3.13 standard library (ctypes, subprocess, urllib, zipfile, hashlib, json, argparse, importlib, site), Tkinter, unittest; cmd.exe batch (`setup_windows.bat`); external runtime pieces: libmpv 0.34 or newer, python-mpv (`mpv>=1.0.6,<2` on PyPI), 7-Zip `7zr.exe` 26.03 (Windows installer only), Khronos Vulkan loader 1.4.357.0 (Windows, only when missing).

**Spec:** `docs/superpowers/specs/2026-09-25-video-player-live-design.md` (approved 2026-09-25; every section 10 question takes its recommended answer, Q1 included). P1 is defined in section 9 ("P1 Runtime detection and installation"). Read with it: 1.3 (R1, R2, R7, R8, R9), 2.1, 2.2 (`libmpv_runtime.py`, `system_packages.py`), 2.3 (placeholder, GUI file changes, `_GlobalRedirect`, `_redirecting_thread_factory`, flags), 2.4, 2.5 (`player_probe`), 2.6 (mechanics and the P1 key list), 3.1 (lifecycle step 1 and 2a), 6.1, 7.1, 7.2, 7.4, 8.1-8.6, 10 (Q1, Q2, Q6, Q11, Q13), 11 (C9, C46, C47, C54, C58, C59).

## Amendments (2026-09-25 evening, before execution)

These override the text below where they differ.

- Execution mode (operator decision): no subagents. The controller implements, reviews, verifies, commits and PUSHES each task itself, then checks CI. "Local only, never push", the "other agents commit at the same time" rules and the per-task "Review level" lines are superseded; delicate points (native library loading, Windows installer, threads) get a targeted Codex second opinion instead of a multi-agent review.
- The plan was written at HEAD `ab9a167`, before P0. P0 (`0fa0a13`..`ef913f0`) rebuilt `_build_ui` and the header (root rows, `_header_frame`, `_left_pane`, `_player_area`, `_right_column`): Task 8 wires the badge and the placeholder into that layout, adapting its code blocks.
- Task 4 fix (plan review): when BUILD.txt shows the installed build is current, `install_windows` still runs the Vulkan-loader fallback step before `check(dest)`, so a machine that lost `System32\vulkan-1.dll` after install is repaired by Repair (spec 6.1 row 5).
- Task 8 addition (plan review, spec 2.5): Settings Reset (`_reset_ui_settings`) also removes `player_probe` from the config, through `_write_config_raw` (`save_config` merges and cannot delete keys), with a Tk test.
- GUI budget (plan review): the P1 GUI wiring measures about +181 net lines, half of the +360 all-phase budget; recorded here, and Task 8 keeps the status logic in `player_panel_tk.py` / `libmpv_runtime.py` wherever possible.
- Evidence (plan review): like P0, the Xvfb Tk-test output and the GUI screenshots of Task 8 are pasted into an `## Evidence` section at the end of this plan, with the window ids listed before and after each launch.

## Global Constraints

Project rules (verbatim from the controller and the project CLAUDE.md; every task implicitly includes them):

- Commits directly on `main`, local only, never push.
- Conventional commits (`feat`, `fix`, `docs`, `ui`, `refactor`, `test`, `chore`), imperative, explaining what and why.
- No `Co-Authored-By` trailer in any commit message (this project rule overrides any session attribution reminder).
- No em dash (U+2014) or en dash (U+2013) anywhere: code, comments, docstrings, strings, docs, commit messages, test data. Use `-`, a comma, a colon or parentheses. Tests that need the characters use `"\u2014"` escapes.
- Every user-visible string in all 26 languages (it, en, ar, zh, cs, da, nl, fi, fr, de, el, hi, hu, id, ja, ko, no, pl, pt, ro, ru, es, sv, tr, uk, vi) in the module the spec designates (`videotranslator/ui_strings_player.py`, operator decision Q5), with the coverage test (`tests/test_ui_i18n_coverage.py`) green. Correct accents and spelling per language; brand names stay untranslated (mpv, libmpv, python-mpv, Vulkan, setup_windows.bat).
- Windows + Linux parity. For P1 this is the Windows installer story in `setup_windows.bat`: ASCII only, CRLF line endings, the libmpv DLL (`mpv-2.dll` in `mpv-runtime`), `7zr.exe`, the Vulkan loader fallback per Q1/Q2/Q6, and the static installer tests (`tests/test_windows_installer_static.py`).
- Tests run with `python3 -m unittest discover -s tests` (the exact CI command). Never `pytest` from the repo root (backup folders collide). `tests/` is not a package: run single modules as `env PYTHONPATH=tests python3 -m unittest test_a test_b -v` from the repo root (never `tests.test_a`).
- CI installs only `requirements-dev.txt`, so tests are hermetic: no libmpv, no python-mpv, no network, lazy import of `mpv` (only inside `libmpv_runtime.load_mpv`), Tk tests skip without a display (pattern: `tests/test_ui_theme_tk.py` `HAS_DISPLAY`).
- Before each commit: `python3 -m py_compile video_translator_gui.py videotranslator/*.py` and the full suite green, zero em/en dash in the touched files.
- GUI checks only on a private Xvfb (the operator is working on the real display): `xvfb-run -a`, never `:0`.
- Real libmpv checks use the unpacked libmpv 0.41 and python-mpv under `/home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI/_dev/research/player-2026-09-25/probe/` (`lib/` for the library, `wheel/` for `mpv.py`, `mpv-1.0.8-py3-none-any.whl` for pip tests) through `LD_LIBRARY_PATH` / `PYTHONPATH` / `VTAI_LIBMPV_DIR`, never a system-wide install and never `sudo`.
- One logical change per commit. No feature beyond the task. The GUI file grows by wiring only (spec budget: +360 net lines over all phases, strings excluded; P1 uses about 140).

Environment rules for every executor on this machine:

- Start EVERY shell command with `unset DISPLAY WAYLAND_DISPLAY;` (nothing here needs the real display; Xvfb runs set their own `DISPLAY`).
- Other agents commit in this repo at the same time: stage only the files your task lists (`git add <path> ...`), never `git add .`/`-A`, never `git stash`, `git checkout`, `git reset`. Never stage `core.*`, `_backup_ui_redesign_20260617/`, `_demo_styles.py` or anything under `_dev/`.
- Never run `pkexec`, `sudo` or a real package install on this machine: a pkexec prompt would open on the operator's display. The Linux install path is verified with fakes here and on a Debian 12 VM by the operator.
- Never provoke a real segmentation fault in tests (core files land in the repo root): a crashed child is simulated with `os._exit(134)`.
- Refer to code by symbol name: line numbers in this plan are hints at HEAD `9440a05` and drift while others commit.

## Decisions and spec refinements made by this plan

The spec is binding; where it left a detail open or where the code forced a choice, this plan decides as follows (each item is small and reviewable):

1. P1 lands 19 keys, not 17: the 17 availability/install keys of spec 2.6 plus `player_badge` (listed under P2, but the badge ships in P1) and `live_err_busy_install` (listed under P4, used by P1 to refuse a second concurrent install). Spec 2.6: "Each key lands with the phase that uses it". `player_credits` and `player_license_system` are used by the ready text (badge tooltip and placeholder), so no key is dead.
2. P1 has no "first need" (no playback), so the startup status worker runs the subprocess probe itself when `quick_presence` finds the library and the `player_probe` cache (spec 2.5) is missing or stale. This only ever loads libmpv in a child process (F14 holds) and leaves P2 a valid cache. `quick_presence` alone still decides the missing cases.
3. `ComponentInstaller.install` takes `system_plans` (alternative plans tried in order, one per privilege prefix: pkexec, then `sudo -n`) instead of one `system_plan`; the chain of spec 8.2 needs more than one plan.
4. Batch pin quoting: `set "MPV_PIN=mpv>=1.0.6,<2"` and `pip install "%MPV_PIN%"`. The spec text (`set "MPV_PIN="mpv>=1.0.6,<2""`, "the PYANNOTE_PIN pattern") puts `<` OUTSIDE quotes: cmd.exe toggles its quote flag on every `"` in phase 2, so the inner quotes close the quoting and `<` becomes a redirection. The chosen form keeps the whole assignment quoted and quotes the expansion where it is used (percent expansion happens in phase 1, before redirection parsing). The existing `PYANNOTE_PIN` line is suspect for the same reason: it is NOT changed here (out of scope), it is reported to the operator as an S4 check.
5. `VTAI_LIBMPV_DIR` is honoured on Linux too (dev override, first candidate), so the real-library and Xvfb checks run on Kali with the unpacked library and no system install. `check --dir DIR` works on both systems.
6. The Vulkan fallback directory is searched next to the DLL and in the per-user runtime dir (`%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime\vulkan-fallback`), so the GUI per-user install (Q6) also repairs a machine-wide install that lacks the loader.
7. The VO profile option table lives in `libmpv_runtime.VO_PROFILE_OPTIONS` (the probe needs it in P1); P2's `player_engine.VO_PROFILES` must derive its names from it.
8. `install_windows` has no `system32` parameter: the load-check subprocess decides whether the Vulkan loader is missing (reason `vulkan-loader-missing`).
9. `probe_in_subprocess` gains `cwd` (default: the folder that contains `videotranslator/`) and `sys_platform` keyword parameters, so `python -m` works from the desktop shortcut and the no-window flag is testable.
10. The install decision is a pure function, `system_packages.player_install_request(...)`, computed on the status worker (it may run `apt-cache show`), never on the Tk thread.
11. `_installing` is also set by `_install_ffmpeg` (it runs apt through pkexec: a concurrent player install would hit the dpkg lock) and cleared in `_ffmpeg_done`.
12. Installer children (pip, apt, dnf, pacman, zypper, 7zr) are not put in the kill-on-close registry: killing a package manager mid-install can leave a broken package state; they finish on their own.
13. `PlayerPanel` in P1 is the subset needed now: constructor `(parent, *, ui_s, make_button, on_command, logo_path, sys_platform)`, `show_unavailable`, `show_ready`, `show_install_progress`, `status_text`, `relabel`, plus `HoverTip`. P2 extends the constructor with `theme`, `keyboard_operable` and `log`, and adds `apply_theme`, `render`, `notify`, `host_wid` (P1 uses only reserved colours and walk-recoloured buttons, so it needs no theme hook).
14. The uninstaller's custom menu gets its own `Q_MPV` prompt for `mpv python-mpv` (the "both uninstall lists" of spec 8.1 item 5 are the full list and the custom menu).
15. `App._post_if_alive` ignores the `RuntimeError` Tkinter raises when a worker posts after `mainloop` ended (the same tolerance `_TkStreamRedirect` already has).

Validation already done while writing this plan (2026-09-25, HEAD `ab9a167`, on a scratch copy of the repo, never on the working tree): every code block of Tasks 1-8 was applied by script; `python3 -m unittest discover -s tests` passed headless (917 tests, 58 skipped) and on a private Xvfb (917 tests, 4 skipped); `check --json` against the unpacked libmpv 0.41 gave exit 2 / `libmpv-missing` without it, and exit 0 with API `[2, 5]`, `mpv_version` `[0, 41]` (`mpv v0.41.0`, so claim C54 holds on 0.41) and `vo_profiles_ok` `["x11egl", "x11vk", "x11sw"]` with it; `--preflight --preflight-player` listed both required failures; the four Xvfb GUI states of Task 8 Step 6 gave exactly the expected reasons, badge colours and cache behaviour. Executors still run every step: the tree moves while others commit.

## File map

| File | Status | Responsibility |
|---|---|---|
| `videotranslator/subprocess_utils.py` | modify | `CREATE_NO_WINDOW`, `no_window_kwargs()` |
| `videotranslator/ui_strings_player.py` | create | `PLAYER_UI_STRINGS` (19 keys x 26 languages), `PLAYER_KEYS`, `merge_into()` |
| `videotranslator/libmpv_runtime.py` | create | status type, detection, probe, subprocess probe, cache, import gate, UI helpers, Windows installer, CLI |
| `videotranslator/system_packages.py` | create | Linux plans, privilege chain, streaming runner, pip command, import-path refresh, `ComponentInstaller`, `player_install_request` |
| `videotranslator/player_panel_tk.py` | create | `PlayerPanel` (video host + placeholder), `HoverTip` |
| `videotranslator/preflight.py` | modify | `native_checks` parameter, `libmpv_native_check`, python-mpv optional probe |
| `videotranslator/cli.py` | modify | `--preflight-player`, `preflight_options()` |
| `video_translator_gui.py` | modify | `_GlobalRedirect` None fix, `_redirecting_thread_factory`, string merge, badge, panel, status refresh, install flow, `_installing`, diagnostics wiring |
| `setup_windows.bat` | modify | `:step_player`, `:player_check`, step labels x/6, uninstall lists, per-user runtime cleanup |
| `requirements-player.txt` | create | `mpv>=1.0.6,<2` |
| `requirements.txt`, `pyproject.toml`, `.gitignore`, `README.md` | modify | profile reference, `player` extra, ignores, install/diagnostics/third-party docs |
| `tests/test_ui_redirect.py`, `tests/test_libmpv_runtime.py`, `tests/test_libmpv_install.py`, `tests/test_system_packages.py`, `tests/test_player_panel_tk.py`, `tests/test_import_hygiene.py`, `tests/test_no_long_dashes.py` | create | see each task |
| `tests/test_subprocess_utils.py`, `tests/test_ui_i18n_coverage.py`, `tests/test_preflight.py`, `tests/test_cli_smoke.py`, `tests/test_requirements_static.py`, `tests/test_windows_installer_static.py`, `tests/test_ui_theme_tk.py` | modify | see each task |

Task order and dependencies: 1 and 2 are independent; 3 needs 1 and 2; 4 needs 3; 5 needs 3; 6 needs 3; 7 needs 4 and 6; 8 needs all.

---

## Task 1: Hidden child consoles and pythonw-safe output

Review level: full

(Threads, the process-wide stdout/stderr redirect and a Windows-only pythonw behaviour that cannot be run here.)

**Files:**
- Modify: `videotranslator/subprocess_utils.py` (append after `common_subprocess_kwargs`)
- Modify: `video_translator_gui.py` (`class _GlobalRedirect`, about line 5501; new method `App._redirecting_thread_factory` right after `App._log_async`, about line 7914)
- Modify: `tests/test_subprocess_utils.py`
- Create: `tests/test_ui_redirect.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `videotranslator.subprocess_utils.CREATE_NO_WINDOW: int` (`0x08000000`)
  - `videotranslator.subprocess_utils.no_window_kwargs(sys_platform: str) -> dict[str, int]` (`{"creationflags": CREATE_NO_WINDOW}` on `"win32"`, `{}` elsewhere)
  - `App._redirecting_thread_factory(self, target: Callable[[], None], name: str | None = None, daemon: bool = True) -> threading.Thread`: the thread's run installs `_thread_local.redirect = _TkStreamRedirect(self, self._log_write)` and removes it in `finally`. It is call-compatible with `threading.Thread(target=..., name=..., daemon=...)`, so later code passes it as `thread_factory`.
  - `_GlobalRedirect(None)`: `write` returns `len(s)`, `flush` does nothing, `fileno` raises `io.UnsupportedOperation` (pythonw has no console streams, spec R9, C58).

- [ ] **Step 1: Write the failing tests for `no_window_kwargs`**

Append to `tests/test_subprocess_utils.py` (extend the import list at the top with `CREATE_NO_WINDOW, no_window_kwargs`):

```python
class NoWindowKwargsTests(unittest.TestCase):
    def test_windows_children_start_without_a_console(self):
        self.assertEqual(no_window_kwargs("win32"), {"creationflags": 0x08000000})

    def test_other_systems_get_no_extra_kwargs(self):
        self.assertEqual(no_window_kwargs("linux"), {})
        self.assertEqual(no_window_kwargs("darwin"), {})

    def test_constant_matches_subprocess_when_it_exists(self):
        self.assertEqual(
            CREATE_NO_WINDOW, getattr(subprocess, "CREATE_NO_WINDOW", CREATE_NO_WINDOW))
```

- [ ] **Step 2: Write the failing redirect tests**

Create `tests/test_ui_redirect.py`:

```python
"""_GlobalRedirect under pythonw and the redirecting thread factory (spec R9, [CC] G2).

No display needed: the factory is bound to a stand-in object that has the
two attributes _TkStreamRedirect uses (after, _log_write).
"""

import io
import threading
import types
import unittest

import video_translator_gui as legacy


class _FakeApp:
    def __init__(self):
        self.scheduled = []
        self.written = []

    def after(self, _delay, callback, *args):
        self.scheduled.append((callback, args))

    def run_scheduled(self):
        """Play the Tk callbacks the redirect scheduled, as the Tk loop would."""
        for callback, args in self.scheduled:
            callback(*args)

    def _log_write(self, text):
        self.written.append(text)


class GlobalRedirectWithoutConsoleTests(unittest.TestCase):
    def setUp(self):
        legacy._thread_local.redirect = None

    def test_write_without_an_original_stream_drops_the_text(self):
        redirect = legacy._GlobalRedirect(None)
        self.assertEqual(redirect.write("x"), 1)
        self.assertEqual(redirect.write(""), 0)

    def test_flush_without_an_original_stream_does_not_raise(self):
        legacy._GlobalRedirect(None).flush()

    def test_fileno_without_an_original_stream_is_unsupported(self):
        with self.assertRaises(io.UnsupportedOperation):
            legacy._GlobalRedirect(None).fileno()

    def test_a_thread_local_redirect_still_wins(self):
        sink = io.StringIO()
        legacy._thread_local.redirect = sink
        try:
            legacy._GlobalRedirect(None).write("hello")
        finally:
            legacy._thread_local.redirect = None
        self.assertEqual(sink.getvalue(), "hello")

    def test_the_original_stream_is_used_when_present(self):
        original = io.StringIO()
        legacy._GlobalRedirect(original).write("abc")
        self.assertEqual(original.getvalue(), "abc")


class RedirectingThreadFactoryTests(unittest.TestCase):
    def setUp(self):
        legacy._thread_local.redirect = None
        self.app = _FakeApp()
        self.factory = types.MethodType(legacy.App._redirecting_thread_factory, self.app)

    def test_the_thread_installs_the_gui_redirect_for_its_target(self):
        seen = {}

        def target():
            seen["redirect"] = legacy._thread_local.redirect
            legacy._GlobalRedirect(None).write("from a worker")

        thread = self.factory(target, name="player-status")
        self.assertIsInstance(thread, threading.Thread)
        self.assertTrue(thread.daemon)
        self.assertEqual(thread.name, "player-status")
        thread.start()
        thread.join(5)
        self.assertIsInstance(seen["redirect"], legacy._TkStreamRedirect)
        # The text reaches the log through Tk callbacks (the throttled flush,
        # or the final flush when the dropped redirect object is closed).
        self.app.run_scheduled()
        self.assertEqual("".join(self.app.written), "from a worker")

    def test_the_redirect_is_removed_even_when_the_target_raises(self):
        def target():
            raise RuntimeError("boom")

        thread = self.factory(target, name="t")
        with self.assertRaises(RuntimeError):
            thread.run()  # runs here, so this thread's local is observable
        self.assertIsNone(legacy._thread_local.redirect)

    def test_keyword_call_like_threading_thread(self):
        thread = self.factory(target=lambda: None, name="t", daemon=False)
        self.assertFalse(thread.daemon)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_subprocess_utils test_ui_redirect -v`
Expected: FAIL/ERROR (`ImportError: cannot import name 'CREATE_NO_WINDOW'`, `AttributeError: 'NoneType' object has no attribute 'write'`, `AttributeError: type object 'App' has no attribute '_redirecting_thread_factory'`).

- [ ] **Step 4: Implement `no_window_kwargs`**

Append to `videotranslator/subprocess_utils.py`, after `common_subprocess_kwargs`:

```python
# Win32 process creation flag: start a console program without opening a
# console window (a pythonw parent has no console to share, so every child
# would otherwise flash one). Fixed by the Win32 API; subprocess exposes the
# name only on Windows.
CREATE_NO_WINDOW = 0x08000000


def no_window_kwargs(sys_platform: str) -> dict[str, int]:
    """Return subprocess kwargs that keep a child's console hidden on Windows."""
    if sys_platform == "win32":
        return {"creationflags": CREATE_NO_WINDOW}
    return {}
```

- [ ] **Step 5: Make `_GlobalRedirect` tolerate a None stream**

In `video_translator_gui.py`, replace the three methods of `class _GlobalRedirect` (keep `__init__` and `writable`):

```python
    def write(self, s):
        redir = getattr(_thread_local, "redirect", None)
        if redir is not None:
            return redir.write(s)
        if self._original is None:
            # pythonw: sys.stdout/sys.stderr are None, so library output from
            # threads without a GUI redirect (tqdm, warnings) is dropped
            # instead of raising (spec R9).
            return len(s)
        return self._original.write(s)

    def flush(self):
        redir = getattr(_thread_local, "redirect", None)
        if redir is not None:
            redir.flush()
        elif self._original is not None:
            self._original.flush()

    def fileno(self):
        if self._original is None:
            raise io.UnsupportedOperation("fileno")
        return self._original.fileno()
```

- [ ] **Step 6: Add `_redirecting_thread_factory`**

In `video_translator_gui.py`, right after `def _log_async(...)` in `class App`:

```python
    def _redirecting_thread_factory(self, target, name=None, daemon=True):
        """Return a Thread that runs ``target`` with the GUI log redirect installed.

        Library output of worker threads (pip, tqdm, warnings) then reaches
        the log panel instead of the original stream, which is None under
        pythonw (spec 2.4, R9). Call-compatible with threading.Thread.
        """
        def run():
            _thread_local.redirect = _TkStreamRedirect(self, self._log_write)
            try:
                target()
            finally:
                _thread_local.redirect = None

        return threading.Thread(target=run, name=name, daemon=daemon)
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_subprocess_utils test_ui_redirect -v`
Expected: all OK.

- [ ] **Step 8: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' videotranslator/subprocess_utils.py video_translator_gui.py tests/test_subprocess_utils.py tests/test_ui_redirect.py || echo "no long dashes"
git add videotranslator/subprocess_utils.py video_translator_gui.py tests/test_subprocess_utils.py tests/test_ui_redirect.py
git commit -m "fix(gui): keep worker output safe under pythonw and hide child consoles

_GlobalRedirect now drops text when the original stream is None (pythonw)
instead of raising, and App._redirecting_thread_factory gives every new
worker the thread-local log redirect, so library output reaches the log.
no_window_kwargs() adds CREATE_NO_WINDOW for Windows children started by
the player runtime (probe, 7zr, installers)."
```

---

## Task 2: Player strings module in 26 languages

Review level: light

(Pure data plus a merge helper and test extensions; mechanical.)

**Files:**
- Create: `videotranslator/ui_strings_player.py`
- Modify: `video_translator_gui.py` (after `UI_LANG_CODES = ...`, about line 3831; `App.__init__` right after `self._build_ui()` and the log-visibility block)
- Modify: `tests/test_ui_i18n_coverage.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `videotranslator.ui_strings_player.PLAYER_UI_STRINGS: dict[str, dict[str, str]]` (language code -> key -> text; the 26 codes of `UI_LANG_OPTIONS`)
  - `videotranslator.ui_strings_player.PLAYER_KEYS: tuple[str, ...]` (sorted keys)
  - `videotranslator.ui_strings_player.merge_into(ui_strings: dict[str, dict[str, str]]) -> list[str]` (never raises; a colliding key with a different value keeps the existing value and reports `"collision <lang>.<key>"`; a language missing from `ui_strings` is skipped and reported as `"unknown language '<lang>'"`)
  - `video_translator_gui._PLAYER_STRING_PROBLEMS: list[str]`
  - The 19 keys: `player_badge`, `player_badge_ok {version}`, `player_unavailable_title`, `player_missing_pymod`, `player_missing_libmpv_linux {cmd}`, `player_missing_libmpv_win`, `player_libmpv_too_old {version}`, `player_libmpv_load_failed {detail}`, `player_vulkan_missing`, `player_probe_crashed`, `player_restart_required`, `player_install_btn`, `player_install_confirm {size}`, `player_installing`, `player_install_ok`, `player_install_failed`, `player_credits {license}`, `player_license_system`, `live_err_busy_install`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ui_i18n_coverage.py`:

1. Replace `SOURCE_PATH = ROOT / "video_translator_gui.py"` with:

```python
GUI_PATH = ROOT / "video_translator_gui.py"
# Tk glue modules call ui_s(...) too (spec 2.6): every key scan covers them.
SOURCE_PATHS = [GUI_PATH, *sorted((ROOT / "videotranslator").glob("*_tk.py"))]


def _source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in SOURCE_PATHS)
```

2. In `UIStringsUsedKeysTests.test_keys_called_in_source_exist_in_it_and_en` and in both `UIStringsDynamicKeyFamiliesTests` tests, replace `SOURCE_PATH.read_text(encoding="utf-8")` with `_source_text()`. In `PanelAndAccordionTitleSourceTests._title_calls`, replace both `SOURCE_PATH` occurrences with `GUI_PATH` (that AST check is about the GUI file only).

3. Add `from videotranslator import ui_strings_player` to the imports and append these classes before `if __name__ == "__main__":`:

```python
class PlayerStringsModuleTests(unittest.TestCase):
    """ui_strings_player (spec 2.6, Q5): complete, merged, never colliding."""

    def test_every_player_key_exists_in_all_26_languages(self):
        codes = {code for code, _ in UI_LANG_OPTIONS}
        self.assertEqual(set(ui_strings_player.PLAYER_UI_STRINGS), codes)
        keys = set(ui_strings_player.PLAYER_KEYS)
        self.assertEqual(len(keys), 19)
        for lang, bucket in ui_strings_player.PLAYER_UI_STRINGS.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(bucket), keys)

    def test_merged_values_are_the_module_values(self):
        for lang, bucket in ui_strings_player.PLAYER_UI_STRINGS.items():
            for key, value in bucket.items():
                self.assertEqual(UI_STRINGS[lang][key], value,
                                 f"{lang}.{key} collides with a GUI file value")

    def test_merge_into_a_clean_copy_reports_nothing(self):
        keys = set(ui_strings_player.PLAYER_KEYS)
        clean = {lang: {k: v for k, v in bucket.items() if k not in keys}
                 for lang, bucket in UI_STRINGS.items()}
        self.assertEqual(ui_strings_player.merge_into(clean), [])
        self.assertEqual(clean["ja"]["player_badge"],
                         ui_strings_player.PLAYER_UI_STRINGS["ja"]["player_badge"])

    def test_merge_into_never_raises_and_reports_problems(self):
        target = {"it": {"player_badge": "diverso"}}
        problems = ui_strings_player.merge_into(target)
        self.assertEqual(target["it"]["player_badge"], "diverso")  # existing value wins
        self.assertIn("collision it.player_badge", problems)
        self.assertIn("unknown language 'en'", problems)
        self.assertEqual(set(target), {"it"})

    def test_merge_is_idempotent(self):
        copy = {lang: dict(bucket) for lang, bucket in UI_STRINGS.items()}
        self.assertEqual(ui_strings_player.merge_into(copy), [])

    def test_gui_file_does_not_define_player_keys(self):
        source = GUI_PATH.read_text(encoding="utf-8")
        defined = [key for key in ui_strings_player.PLAYER_KEYS
                   if re.search(rf'"{re.escape(key)}"\s*:', source)]
        self.assertEqual(defined, [])

    def test_no_problem_was_reported_at_import(self):
        self.assertEqual(legacy._PLAYER_STRING_PROBLEMS, [])


class PlayerModuleLiteralKeyTests(unittest.TestCase):
    """Keys carried as plain literals by the player and live modules exist in
    all 26 languages, so a typo fails CI (spec 2.6). The module list grows
    with the phases; a pattern with no match yet is fine."""

    _KEY_RE = re.compile(r"^(player|live|deps|settings)_[a-z0-9_]+$")
    _PATTERNS = ("libmpv_runtime.py", "system_packages.py", "player_*.py", "live_*.py")

    @classmethod
    def _modules(cls):
        base = ROOT / "videotranslator"
        found = set()
        for pattern in cls._PATTERNS:
            found.update(base.glob(pattern))
        return sorted(found)

    def test_literal_keys_exist_in_every_language(self):
        missing = []
        for path in self._modules():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and self._KEY_RE.match(node.value)):
                    missing.extend((path.name, node.value, lang)
                                   for lang in sorted(UI_STRINGS)
                                   if node.value not in UI_STRINGS[lang])
        self.assertEqual(missing, [])
```

Note for later tasks: the scanned modules must never contain a string literal that matches `^(player|live|deps|settings)_...$` and is NOT a UI key (for example the config key `player_probe`): config keys stay in the GUI file.

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_ui_i18n_coverage -v`
Expected: ERROR `ModuleNotFoundError: No module named 'videotranslator.ui_strings_player'`.

- [ ] **Step 3: Create `videotranslator/ui_strings_player.py`**

```python
"""UI strings of the integrated player and of live mode (spec 2.6, operator decision Q5).

They live here instead of in video_translator_gui.py so the GUI file does not
grow by thousands of lines; the GUI merges them into UI_STRINGS at import, so
UI_STRINGS stays the single runtime dictionary and App._s keeps its
it -> en -> key fallback. Keys land with the phase that uses them.

Placeholders ({version}, {cmd}, {detail}, {size}, {license}) must be the same
in every language (tests/test_ui_i18n_coverage.py checks it). Brand names
(mpv, libmpv, python-mpv, Vulkan, setup_windows.bat) are not translated.
"""

from __future__ import annotations

PLAYER_UI_STRINGS: dict[str, dict[str, str]] = {
    "it": {
        "player_badge": "Player",
        "player_badge_ok": "Player pronto (mpv {version})",
        "player_unavailable_title": "Player integrato non disponibile",
        "player_missing_pymod": "Il pacchetto python-mpv non è installato.",
        "player_missing_libmpv_linux": "libmpv non è installata. Installala con: {cmd}",
        "player_missing_libmpv_win": "libmpv non è installata. Esegui setup_windows.bat (Repair) oppure installala ora.",
        "player_libmpv_too_old": "La libmpv installata ({version}) è troppo vecchia: serve la 0.34 o successiva.",
        "player_libmpv_load_failed": "Impossibile caricare libmpv ({detail}). Il file potrebbe essere danneggiato o bloccato dall'antivirus.",
        "player_vulkan_missing": "libmpv richiede il runtime Vulkan (vulkan-1.dll): aggiorna il driver grafico o reinstalla il player.",
        "player_probe_crashed": "libmpv si è arrestata in modo anomalo durante il caricamento: il player resta disattivato. Vedi il log.",
        "player_restart_required": "Riavvia l'applicazione per completare l'attivazione del player.",
        "player_install_btn": "Installa player",
        "player_install_confirm": "Scaricare e installare i componenti del player video (circa {size} MB)?",
        "player_installing": "Installazione del player...",
        "player_install_ok": "Player installato.",
        "player_install_failed": "Installazione del player non riuscita: vedi il log.",
        "player_credits": "Riproduzione video: mpv (libmpv), {license}",
        "player_license_system": "libreria di sistema",
        "live_err_busy_install": "È in corso un'installazione: attendi che finisca.",
    },
    "en": {
        "player_badge": "Player",
        "player_badge_ok": "Player ready (mpv {version})",
        "player_unavailable_title": "Integrated player not available",
        "player_missing_pymod": "The python-mpv package is not installed.",
        "player_missing_libmpv_linux": "libmpv is not installed. Install it with: {cmd}",
        "player_missing_libmpv_win": "libmpv is not installed. Run setup_windows.bat (Repair) or install it now.",
        "player_libmpv_too_old": "The installed libmpv ({version}) is too old: 0.34 or newer is needed.",
        "player_libmpv_load_failed": "libmpv could not be loaded ({detail}). The file may be damaged or blocked by the antivirus.",
        "player_vulkan_missing": "libmpv needs the Vulkan runtime (vulkan-1.dll): update the graphics driver or install the player again.",
        "player_probe_crashed": "libmpv crashed while loading: the player stays disabled. See the log.",
        "player_restart_required": "Restart the application to finish enabling the player.",
        "player_install_btn": "Install player",
        "player_install_confirm": "Download and install the video player components (about {size} MB)?",
        "player_installing": "Installing the player...",
        "player_install_ok": "Player installed.",
        "player_install_failed": "Player installation failed: see the log.",
        "player_credits": "Video playback: mpv (libmpv), {license}",
        "player_license_system": "system library",
        "live_err_busy_install": "An installation is running: wait for it to finish.",
    },
    "ar": {
        "player_badge": "المشغل",
        "player_badge_ok": "المشغل جاهز (mpv {version})",
        "player_unavailable_title": "المشغل المدمج غير متاح",
        "player_missing_pymod": "حزمة python-mpv غير مثبتة.",
        "player_missing_libmpv_linux": "مكتبة libmpv غير مثبتة. ثبّتها باستخدام: {cmd}",
        "player_missing_libmpv_win": "مكتبة libmpv غير مثبتة. شغّل setup_windows.bat (Repair) أو ثبّتها الآن.",
        "player_libmpv_too_old": "إصدار libmpv المثبت ({version}) قديم جدًا: يلزم الإصدار 0.34 أو أحدث.",
        "player_libmpv_load_failed": "تعذّر تحميل libmpv ({detail}). قد يكون الملف تالفًا أو محظورًا من برنامج مكافحة الفيروسات.",
        "player_vulkan_missing": "تحتاج libmpv إلى بيئة تشغيل Vulkan (vulkan-1.dll): حدّث برنامج تشغيل الرسومات أو أعد تثبيت المشغل.",
        "player_probe_crashed": "تعطلت libmpv أثناء التحميل: سيبقى المشغل معطّلًا. راجع السجل.",
        "player_restart_required": "أعد تشغيل التطبيق لإكمال تفعيل المشغل.",
        "player_install_btn": "تثبيت المشغل",
        "player_install_confirm": "هل تريد تنزيل مكونات مشغل الفيديو وتثبيتها (حوالي {size} ميغابايت)؟",
        "player_installing": "جارٍ تثبيت المشغل...",
        "player_install_ok": "تم تثبيت المشغل.",
        "player_install_failed": "فشل تثبيت المشغل: راجع السجل.",
        "player_credits": "تشغيل الفيديو: mpv (libmpv)، {license}",
        "player_license_system": "مكتبة النظام",
        "live_err_busy_install": "هناك عملية تثبيت جارية: انتظر حتى تنتهي.",
    },
    "zh": {
        "player_badge": "播放器",
        "player_badge_ok": "播放器已就绪 (mpv {version})",
        "player_unavailable_title": "内置播放器不可用",
        "player_missing_pymod": "未安装 python-mpv 软件包。",
        "player_missing_libmpv_linux": "未安装 libmpv。请使用以下命令安装: {cmd}",
        "player_missing_libmpv_win": "未安装 libmpv。请运行 setup_windows.bat (Repair) 或立即安装。",
        "player_libmpv_too_old": "已安装的 libmpv ({version}) 版本过旧: 需要 0.34 或更高版本。",
        "player_libmpv_load_failed": "无法加载 libmpv ({detail})。文件可能已损坏或被杀毒软件拦截。",
        "player_vulkan_missing": "libmpv 需要 Vulkan 运行时 (vulkan-1.dll): 请更新显卡驱动或重新安装播放器。",
        "player_probe_crashed": "libmpv 在加载时崩溃: 播放器保持禁用。请查看日志。",
        "player_restart_required": "请重新启动应用程序以完成播放器的启用。",
        "player_install_btn": "安装播放器",
        "player_install_confirm": "是否下载并安装视频播放器组件 (约 {size} MB)？",
        "player_installing": "正在安装播放器...",
        "player_install_ok": "播放器已安装。",
        "player_install_failed": "播放器安装失败: 请查看日志。",
        "player_credits": "视频播放: mpv (libmpv), {license}",
        "player_license_system": "系统库",
        "live_err_busy_install": "正在进行安装: 请等待其完成。",
    },
    "cs": {
        "player_badge": "Přehrávač",
        "player_badge_ok": "Přehrávač je připraven (mpv {version})",
        "player_unavailable_title": "Vestavěný přehrávač není k dispozici",
        "player_missing_pymod": "Balíček python-mpv není nainstalován.",
        "player_missing_libmpv_linux": "Knihovna libmpv není nainstalována. Nainstalujte ji příkazem: {cmd}",
        "player_missing_libmpv_win": "Knihovna libmpv není nainstalována. Spusťte setup_windows.bat (Repair) nebo ji nainstalujte nyní.",
        "player_libmpv_too_old": "Nainstalovaná knihovna libmpv ({version}) je příliš stará: je potřeba verze 0.34 nebo novější.",
        "player_libmpv_load_failed": "Knihovnu libmpv nelze načíst ({detail}). Soubor může být poškozený nebo blokovaný antivirem.",
        "player_vulkan_missing": "Knihovna libmpv vyžaduje běhové prostředí Vulkan (vulkan-1.dll): aktualizujte ovladač grafické karty nebo přehrávač nainstalujte znovu.",
        "player_probe_crashed": "Knihovna libmpv při načítání spadla: přehrávač zůstává vypnutý. Podívejte se do protokolu.",
        "player_restart_required": "Restartujte aplikaci, aby se aktivace přehrávače dokončila.",
        "player_install_btn": "Nainstalovat přehrávač",
        "player_install_confirm": "Stáhnout a nainstalovat součásti videopřehrávače (přibližně {size} MB)?",
        "player_installing": "Instalace přehrávače...",
        "player_install_ok": "Přehrávač byl nainstalován.",
        "player_install_failed": "Instalace přehrávače selhala: podívejte se do protokolu.",
        "player_credits": "Přehrávání videa: mpv (libmpv), {license}",
        "player_license_system": "systémová knihovna",
        "live_err_busy_install": "Probíhá instalace: počkejte, až skončí.",
    },
    "da": {
        "player_badge": "Afspiller",
        "player_badge_ok": "Afspilleren er klar (mpv {version})",
        "player_unavailable_title": "Den indbyggede afspiller er ikke tilgængelig",
        "player_missing_pymod": "Pakken python-mpv er ikke installeret.",
        "player_missing_libmpv_linux": "libmpv er ikke installeret. Installer det med: {cmd}",
        "player_missing_libmpv_win": "libmpv er ikke installeret. Kør setup_windows.bat (Repair), eller installer det nu.",
        "player_libmpv_too_old": "Den installerede libmpv ({version}) er for gammel: version 0.34 eller nyere kræves.",
        "player_libmpv_load_failed": "libmpv kunne ikke indlæses ({detail}). Filen kan være beskadiget eller blokeret af antivirusprogrammet.",
        "player_vulkan_missing": "libmpv kræver Vulkan-runtime (vulkan-1.dll): opdater grafikdriveren, eller installer afspilleren igen.",
        "player_probe_crashed": "libmpv gik ned under indlæsningen: afspilleren forbliver deaktiveret. Se loggen.",
        "player_restart_required": "Genstart programmet for at fuldføre aktiveringen af afspilleren.",
        "player_install_btn": "Installer afspiller",
        "player_install_confirm": "Vil du downloade og installere videoafspillerens komponenter (ca. {size} MB)?",
        "player_installing": "Installerer afspilleren...",
        "player_install_ok": "Afspilleren er installeret.",
        "player_install_failed": "Installationen af afspilleren mislykkedes: se loggen.",
        "player_credits": "Videoafspilning: mpv (libmpv), {license}",
        "player_license_system": "systembibliotek",
        "live_err_busy_install": "En installation er i gang: vent, til den er færdig.",
    },
    "nl": {
        "player_badge": "Speler",
        "player_badge_ok": "Speler gereed (mpv {version})",
        "player_unavailable_title": "Ingebouwde speler niet beschikbaar",
        "player_missing_pymod": "Het pakket python-mpv is niet geïnstalleerd.",
        "player_missing_libmpv_linux": "libmpv is niet geïnstalleerd. Installeer het met: {cmd}",
        "player_missing_libmpv_win": "libmpv is niet geïnstalleerd. Voer setup_windows.bat (Repair) uit of installeer het nu.",
        "player_libmpv_too_old": "De geïnstalleerde libmpv ({version}) is te oud: versie 0.34 of nieuwer is vereist.",
        "player_libmpv_load_failed": "libmpv kon niet worden geladen ({detail}). Het bestand is mogelijk beschadigd of geblokkeerd door de antivirus.",
        "player_vulkan_missing": "libmpv heeft de Vulkan-runtime nodig (vulkan-1.dll): werk het grafische stuurprogramma bij of installeer de speler opnieuw.",
        "player_probe_crashed": "libmpv is vastgelopen tijdens het laden: de speler blijft uitgeschakeld. Zie het logboek.",
        "player_restart_required": "Start de applicatie opnieuw om het inschakelen van de speler te voltooien.",
        "player_install_btn": "Speler installeren",
        "player_install_confirm": "De onderdelen van de videospeler downloaden en installeren (ongeveer {size} MB)?",
        "player_installing": "Speler wordt geïnstalleerd...",
        "player_install_ok": "Speler geïnstalleerd.",
        "player_install_failed": "Installatie van de speler mislukt: zie het logboek.",
        "player_credits": "Videoweergave: mpv (libmpv), {license}",
        "player_license_system": "systeembibliotheek",
        "live_err_busy_install": "Er loopt een installatie: wacht tot deze klaar is.",
    },
    "fi": {
        "player_badge": "Soitin",
        "player_badge_ok": "Soitin on valmis (mpv {version})",
        "player_unavailable_title": "Sisäänrakennettu soitin ei ole käytettävissä",
        "player_missing_pymod": "python-mpv-pakettia ei ole asennettu.",
        "player_missing_libmpv_linux": "libmpv-kirjastoa ei ole asennettu. Asenna se komennolla: {cmd}",
        "player_missing_libmpv_win": "libmpv-kirjastoa ei ole asennettu. Suorita setup_windows.bat (Repair) tai asenna se nyt.",
        "player_libmpv_too_old": "Asennettu libmpv ({version}) on liian vanha: tarvitaan versio 0.34 tai uudempi.",
        "player_libmpv_load_failed": "libmpv-kirjastoa ei voitu ladata ({detail}). Tiedosto voi olla vioittunut tai virustorjunnan estämä.",
        "player_vulkan_missing": "libmpv tarvitsee Vulkan-ajonaikaisympäristön (vulkan-1.dll): päivitä näytönohjaimen ajuri tai asenna soitin uudelleen.",
        "player_probe_crashed": "libmpv kaatui latauksen aikana: soitin pysyy poissa käytöstä. Katso loki.",
        "player_restart_required": "Käynnistä sovellus uudelleen, jotta soittimen käyttöönotto valmistuu.",
        "player_install_btn": "Asenna soitin",
        "player_install_confirm": "Ladataanko ja asennetaanko videosoittimen osat (noin {size} Mt)?",
        "player_installing": "Asennetaan soitinta...",
        "player_install_ok": "Soitin asennettu.",
        "player_install_failed": "Soittimen asennus epäonnistui: katso loki.",
        "player_credits": "Videotoisto: mpv (libmpv), {license}",
        "player_license_system": "järjestelmäkirjasto",
        "live_err_busy_install": "Asennus on käynnissä: odota, että se valmistuu.",
    },
    "fr": {
        "player_badge": "Lecteur",
        "player_badge_ok": "Lecteur prêt (mpv {version})",
        "player_unavailable_title": "Lecteur intégré indisponible",
        "player_missing_pymod": "Le paquet python-mpv n'est pas installé.",
        "player_missing_libmpv_linux": "libmpv n'est pas installée. Installez-la avec : {cmd}",
        "player_missing_libmpv_win": "libmpv n'est pas installée. Lancez setup_windows.bat (Repair) ou installez-la maintenant.",
        "player_libmpv_too_old": "La libmpv installée ({version}) est trop ancienne : la version 0.34 ou plus récente est requise.",
        "player_libmpv_load_failed": "Impossible de charger libmpv ({detail}). Le fichier est peut-être endommagé ou bloqué par l'antivirus.",
        "player_vulkan_missing": "libmpv a besoin du runtime Vulkan (vulkan-1.dll) : mettez à jour le pilote graphique ou réinstallez le lecteur.",
        "player_probe_crashed": "libmpv a planté pendant le chargement : le lecteur reste désactivé. Consultez le journal.",
        "player_restart_required": "Redémarrez l'application pour terminer l'activation du lecteur.",
        "player_install_btn": "Installer le lecteur",
        "player_install_confirm": "Télécharger et installer les composants du lecteur vidéo (environ {size} Mo) ?",
        "player_installing": "Installation du lecteur...",
        "player_install_ok": "Lecteur installé.",
        "player_install_failed": "L'installation du lecteur a échoué : consultez le journal.",
        "player_credits": "Lecture vidéo : mpv (libmpv), {license}",
        "player_license_system": "bibliothèque système",
        "live_err_busy_install": "Une installation est en cours : attendez qu'elle se termine.",
    },
    "de": {
        "player_badge": "Player",
        "player_badge_ok": "Player bereit (mpv {version})",
        "player_unavailable_title": "Integrierter Player nicht verfügbar",
        "player_missing_pymod": "Das Paket python-mpv ist nicht installiert.",
        "player_missing_libmpv_linux": "libmpv ist nicht installiert. Installieren Sie es mit: {cmd}",
        "player_missing_libmpv_win": "libmpv ist nicht installiert. Führen Sie setup_windows.bat (Repair) aus oder installieren Sie es jetzt.",
        "player_libmpv_too_old": "Die installierte libmpv ({version}) ist zu alt: Version 0.34 oder neuer wird benötigt.",
        "player_libmpv_load_failed": "libmpv konnte nicht geladen werden ({detail}). Die Datei ist möglicherweise beschädigt oder vom Virenschutz blockiert.",
        "player_vulkan_missing": "libmpv benötigt die Vulkan-Laufzeitumgebung (vulkan-1.dll): Aktualisieren Sie den Grafiktreiber oder installieren Sie den Player erneut.",
        "player_probe_crashed": "libmpv ist beim Laden abgestürzt: Der Player bleibt deaktiviert. Siehe Protokoll.",
        "player_restart_required": "Starten Sie die Anwendung neu, um die Aktivierung des Players abzuschließen.",
        "player_install_btn": "Player installieren",
        "player_install_confirm": "Die Komponenten des Videoplayers herunterladen und installieren (etwa {size} MB)?",
        "player_installing": "Player wird installiert...",
        "player_install_ok": "Player installiert.",
        "player_install_failed": "Installation des Players fehlgeschlagen: siehe Protokoll.",
        "player_credits": "Videowiedergabe: mpv (libmpv), {license}",
        "player_license_system": "Systembibliothek",
        "live_err_busy_install": "Eine Installation läuft: Warten Sie, bis sie abgeschlossen ist.",
    },
    "el": {
        "player_badge": "Αναπαραγωγέας",
        "player_badge_ok": "Ο αναπαραγωγέας είναι έτοιμος (mpv {version})",
        "player_unavailable_title": "Ο ενσωματωμένος αναπαραγωγέας δεν είναι διαθέσιμος",
        "player_missing_pymod": "Το πακέτο python-mpv δεν είναι εγκατεστημένο.",
        "player_missing_libmpv_linux": "Η libmpv δεν είναι εγκατεστημένη. Εγκαταστήστε τη με: {cmd}",
        "player_missing_libmpv_win": "Η libmpv δεν είναι εγκατεστημένη. Εκτελέστε το setup_windows.bat (Repair) ή εγκαταστήστε τη τώρα.",
        "player_libmpv_too_old": "Η εγκατεστημένη libmpv ({version}) είναι πολύ παλιά: απαιτείται η έκδοση 0.34 ή νεότερη.",
        "player_libmpv_load_failed": "Δεν ήταν δυνατή η φόρτωση της libmpv ({detail}). Το αρχείο μπορεί να είναι κατεστραμμένο ή να έχει αποκλειστεί από το πρόγραμμα προστασίας από ιούς.",
        "player_vulkan_missing": "Η libmpv χρειάζεται το περιβάλλον εκτέλεσης Vulkan (vulkan-1.dll): ενημερώστε το πρόγραμμα οδήγησης γραφικών ή εγκαταστήστε ξανά τον αναπαραγωγέα.",
        "player_probe_crashed": "Η libmpv κατέρρευσε κατά τη φόρτωση: ο αναπαραγωγέας παραμένει απενεργοποιημένος. Δείτε το ημερολόγιο.",
        "player_restart_required": "Επανεκκινήστε την εφαρμογή για να ολοκληρωθεί η ενεργοποίηση του αναπαραγωγέα.",
        "player_install_btn": "Εγκατάσταση αναπαραγωγέα",
        "player_install_confirm": "Λήψη και εγκατάσταση των στοιχείων του αναπαραγωγέα βίντεο (περίπου {size} MB);",
        "player_installing": "Εγκατάσταση του αναπαραγωγέα...",
        "player_install_ok": "Ο αναπαραγωγέας εγκαταστάθηκε.",
        "player_install_failed": "Η εγκατάσταση του αναπαραγωγέα απέτυχε: δείτε το ημερολόγιο.",
        "player_credits": "Αναπαραγωγή βίντεο: mpv (libmpv), {license}",
        "player_license_system": "βιβλιοθήκη συστήματος",
        "live_err_busy_install": "Εκτελείται μια εγκατάσταση: περιμένετε να ολοκληρωθεί.",
    },
    "hi": {
        "player_badge": "प्लेयर",
        "player_badge_ok": "प्लेयर तैयार है (mpv {version})",
        "player_unavailable_title": "अंतर्निहित प्लेयर उपलब्ध नहीं है",
        "player_missing_pymod": "python-mpv पैकेज इंस्टॉल नहीं है।",
        "player_missing_libmpv_linux": "libmpv इंस्टॉल नहीं है। इसे इस कमांड से इंस्टॉल करें: {cmd}",
        "player_missing_libmpv_win": "libmpv इंस्टॉल नहीं है। setup_windows.bat (Repair) चलाएँ या इसे अभी इंस्टॉल करें।",
        "player_libmpv_too_old": "इंस्टॉल की गई libmpv ({version}) बहुत पुरानी है: 0.34 या नया संस्करण आवश्यक है।",
        "player_libmpv_load_failed": "libmpv लोड नहीं हो सकी ({detail})। फ़ाइल क्षतिग्रस्त हो सकती है या एंटीवायरस ने उसे ब्लॉक किया हो सकता है।",
        "player_vulkan_missing": "libmpv को Vulkan रनटाइम (vulkan-1.dll) चाहिए: ग्राफ़िक्स ड्राइवर अपडेट करें या प्लेयर को फिर से इंस्टॉल करें।",
        "player_probe_crashed": "लोड करते समय libmpv क्रैश हो गई: प्लेयर अक्षम रहेगा। लॉग देखें।",
        "player_restart_required": "प्लेयर को सक्षम करने की प्रक्रिया पूरी करने के लिए एप्लिकेशन को पुनः आरंभ करें।",
        "player_install_btn": "प्लेयर इंस्टॉल करें",
        "player_install_confirm": "वीडियो प्लेयर के घटक डाउनलोड और इंस्टॉल करें (लगभग {size} MB)?",
        "player_installing": "प्लेयर इंस्टॉल हो रहा है...",
        "player_install_ok": "प्लेयर इंस्टॉल हो गया।",
        "player_install_failed": "प्लेयर इंस्टॉल नहीं हो सका: लॉग देखें।",
        "player_credits": "वीडियो प्लेबैक: mpv (libmpv), {license}",
        "player_license_system": "सिस्टम लाइब्रेरी",
        "live_err_busy_install": "एक इंस्टॉलेशन चल रहा है: उसके पूरा होने तक प्रतीक्षा करें।",
    },
    "hu": {
        "player_badge": "Lejátszó",
        "player_badge_ok": "A lejátszó kész (mpv {version})",
        "player_unavailable_title": "A beépített lejátszó nem érhető el",
        "player_missing_pymod": "A python-mpv csomag nincs telepítve.",
        "player_missing_libmpv_linux": "A libmpv nincs telepítve. Telepítse ezzel a paranccsal: {cmd}",
        "player_missing_libmpv_win": "A libmpv nincs telepítve. Futtassa a setup_windows.bat fájlt (Repair), vagy telepítse most.",
        "player_libmpv_too_old": "A telepített libmpv ({version}) túl régi: 0.34-es vagy újabb verzió szükséges.",
        "player_libmpv_load_failed": "A libmpv nem tölthető be ({detail}). Lehet, hogy a fájl sérült, vagy a víruskereső blokkolja.",
        "player_vulkan_missing": "A libmpv-nek szüksége van a Vulkan futtatókörnyezetre (vulkan-1.dll): frissítse a grafikus illesztőprogramot, vagy telepítse újra a lejátszót.",
        "player_probe_crashed": "A libmpv betöltés közben összeomlott: a lejátszó letiltva marad. Nézze meg a naplót.",
        "player_restart_required": "Indítsa újra az alkalmazást a lejátszó bekapcsolásának befejezéséhez.",
        "player_install_btn": "Lejátszó telepítése",
        "player_install_confirm": "Letölti és telepíti a videolejátszó összetevőit (kb. {size} MB)?",
        "player_installing": "A lejátszó telepítése...",
        "player_install_ok": "A lejátszó telepítve.",
        "player_install_failed": "A lejátszó telepítése nem sikerült: nézze meg a naplót.",
        "player_credits": "Videolejátszás: mpv (libmpv), {license}",
        "player_license_system": "rendszerkönyvtár",
        "live_err_busy_install": "Telepítés van folyamatban: várja meg, amíg befejeződik.",
    },
    "id": {
        "player_badge": "Pemutar",
        "player_badge_ok": "Pemutar siap (mpv {version})",
        "player_unavailable_title": "Pemutar bawaan tidak tersedia",
        "player_missing_pymod": "Paket python-mpv belum terpasang.",
        "player_missing_libmpv_linux": "libmpv belum terpasang. Pasang dengan: {cmd}",
        "player_missing_libmpv_win": "libmpv belum terpasang. Jalankan setup_windows.bat (Repair) atau pasang sekarang.",
        "player_libmpv_too_old": "libmpv yang terpasang ({version}) terlalu lama: diperlukan versi 0.34 atau yang lebih baru.",
        "player_libmpv_load_failed": "libmpv tidak dapat dimuat ({detail}). Berkas mungkin rusak atau diblokir oleh antivirus.",
        "player_vulkan_missing": "libmpv memerlukan runtime Vulkan (vulkan-1.dll): perbarui driver grafis atau pasang ulang pemutar.",
        "player_probe_crashed": "libmpv mengalami crash saat dimuat: pemutar tetap dinonaktifkan. Lihat log.",
        "player_restart_required": "Mulai ulang aplikasi untuk menyelesaikan pengaktifan pemutar.",
        "player_install_btn": "Pasang pemutar",
        "player_install_confirm": "Unduh dan pasang komponen pemutar video (sekitar {size} MB)?",
        "player_installing": "Memasang pemutar...",
        "player_install_ok": "Pemutar terpasang.",
        "player_install_failed": "Pemasangan pemutar gagal: lihat log.",
        "player_credits": "Pemutaran video: mpv (libmpv), {license}",
        "player_license_system": "pustaka sistem",
        "live_err_busy_install": "Sedang ada pemasangan: tunggu hingga selesai.",
    },
    "ja": {
        "player_badge": "プレーヤー",
        "player_badge_ok": "プレーヤー準備完了 (mpv {version})",
        "player_unavailable_title": "内蔵プレーヤーは利用できません",
        "player_missing_pymod": "python-mpv パッケージがインストールされていません。",
        "player_missing_libmpv_linux": "libmpv がインストールされていません。次のコマンドでインストールしてください: {cmd}",
        "player_missing_libmpv_win": "libmpv がインストールされていません。setup_windows.bat (Repair) を実行するか、今すぐインストールしてください。",
        "player_libmpv_too_old": "インストールされている libmpv ({version}) は古すぎます: 0.34 以降が必要です。",
        "player_libmpv_load_failed": "libmpv を読み込めませんでした ({detail})。ファイルが破損しているか、ウイルス対策ソフトにブロックされている可能性があります。",
        "player_vulkan_missing": "libmpv には Vulkan ランタイム (vulkan-1.dll) が必要です: グラフィックドライバーを更新するか、プレーヤーを再インストールしてください。",
        "player_probe_crashed": "libmpv が読み込み中にクラッシュしました: プレーヤーは無効のままです。ログを確認してください。",
        "player_restart_required": "プレーヤーの有効化を完了するには、アプリケーションを再起動してください。",
        "player_install_btn": "プレーヤーをインストール",
        "player_install_confirm": "ビデオプレーヤーのコンポーネント (約 {size} MB) をダウンロードしてインストールしますか？",
        "player_installing": "プレーヤーをインストール中...",
        "player_install_ok": "プレーヤーをインストールしました。",
        "player_install_failed": "プレーヤーのインストールに失敗しました: ログを確認してください。",
        "player_credits": "動画再生: mpv (libmpv), {license}",
        "player_license_system": "システムライブラリ",
        "live_err_busy_install": "インストールを実行中です: 完了するまでお待ちください。",
    },
    "ko": {
        "player_badge": "플레이어",
        "player_badge_ok": "플레이어 준비 완료 (mpv {version})",
        "player_unavailable_title": "내장 플레이어를 사용할 수 없습니다",
        "player_missing_pymod": "python-mpv 패키지가 설치되어 있지 않습니다.",
        "player_missing_libmpv_linux": "libmpv가 설치되어 있지 않습니다. 다음 명령으로 설치하세요: {cmd}",
        "player_missing_libmpv_win": "libmpv가 설치되어 있지 않습니다. setup_windows.bat (Repair)를 실행하거나 지금 설치하세요.",
        "player_libmpv_too_old": "설치된 libmpv ({version})가 너무 오래되었습니다: 0.34 이상이 필요합니다.",
        "player_libmpv_load_failed": "libmpv를 불러올 수 없습니다 ({detail}). 파일이 손상되었거나 백신 프로그램에 의해 차단되었을 수 있습니다.",
        "player_vulkan_missing": "libmpv에는 Vulkan 런타임 (vulkan-1.dll)이 필요합니다: 그래픽 드라이버를 업데이트하거나 플레이어를 다시 설치하세요.",
        "player_probe_crashed": "libmpv가 로드 중에 충돌했습니다: 플레이어가 비활성화된 상태로 유지됩니다. 로그를 확인하세요.",
        "player_restart_required": "플레이어 활성화를 완료하려면 애플리케이션을 다시 시작하세요.",
        "player_install_btn": "플레이어 설치",
        "player_install_confirm": "비디오 플레이어 구성 요소를 다운로드하여 설치할까요 (약 {size} MB)?",
        "player_installing": "플레이어 설치 중...",
        "player_install_ok": "플레이어가 설치되었습니다.",
        "player_install_failed": "플레이어 설치에 실패했습니다: 로그를 확인하세요.",
        "player_credits": "동영상 재생: mpv (libmpv), {license}",
        "player_license_system": "시스템 라이브러리",
        "live_err_busy_install": "설치가 진행 중입니다: 완료될 때까지 기다리세요.",
    },
    "no": {
        "player_badge": "Spiller",
        "player_badge_ok": "Spilleren er klar (mpv {version})",
        "player_unavailable_title": "Den innebygde spilleren er ikke tilgjengelig",
        "player_missing_pymod": "Pakken python-mpv er ikke installert.",
        "player_missing_libmpv_linux": "libmpv er ikke installert. Installer den med: {cmd}",
        "player_missing_libmpv_win": "libmpv er ikke installert. Kjør setup_windows.bat (Repair), eller installer den nå.",
        "player_libmpv_too_old": "Den installerte libmpv ({version}) er for gammel: versjon 0.34 eller nyere kreves.",
        "player_libmpv_load_failed": "libmpv kunne ikke lastes inn ({detail}). Filen kan være skadet eller blokkert av antivirusprogrammet.",
        "player_vulkan_missing": "libmpv trenger Vulkan-kjøretiden (vulkan-1.dll): oppdater grafikkdriveren, eller installer spilleren på nytt.",
        "player_probe_crashed": "libmpv krasjet under innlasting: spilleren forblir deaktivert. Se loggen.",
        "player_restart_required": "Start programmet på nytt for å fullføre aktiveringen av spilleren.",
        "player_install_btn": "Installer spiller",
        "player_install_confirm": "Vil du laste ned og installere komponentene til videospilleren (ca. {size} MB)?",
        "player_installing": "Installerer spilleren...",
        "player_install_ok": "Spilleren er installert.",
        "player_install_failed": "Installasjonen av spilleren mislyktes: se loggen.",
        "player_credits": "Videoavspilling: mpv (libmpv), {license}",
        "player_license_system": "systembibliotek",
        "live_err_busy_install": "En installasjon pågår: vent til den er ferdig.",
    },
    "pl": {
        "player_badge": "Odtwarzacz",
        "player_badge_ok": "Odtwarzacz gotowy (mpv {version})",
        "player_unavailable_title": "Wbudowany odtwarzacz jest niedostępny",
        "player_missing_pymod": "Pakiet python-mpv nie jest zainstalowany.",
        "player_missing_libmpv_linux": "Biblioteka libmpv nie jest zainstalowana. Zainstaluj ją poleceniem: {cmd}",
        "player_missing_libmpv_win": "Biblioteka libmpv nie jest zainstalowana. Uruchom setup_windows.bat (Repair) lub zainstaluj ją teraz.",
        "player_libmpv_too_old": "Zainstalowana biblioteka libmpv ({version}) jest zbyt stara: wymagana jest wersja 0.34 lub nowsza.",
        "player_libmpv_load_failed": "Nie można załadować biblioteki libmpv ({detail}). Plik może być uszkodzony lub zablokowany przez program antywirusowy.",
        "player_vulkan_missing": "Biblioteka libmpv wymaga środowiska uruchomieniowego Vulkan (vulkan-1.dll): zaktualizuj sterownik karty graficznej lub zainstaluj odtwarzacz ponownie.",
        "player_probe_crashed": "Biblioteka libmpv uległa awarii podczas ładowania: odtwarzacz pozostaje wyłączony. Sprawdź dziennik.",
        "player_restart_required": "Uruchom ponownie aplikację, aby dokończyć włączanie odtwarzacza.",
        "player_install_btn": "Zainstaluj odtwarzacz",
        "player_install_confirm": "Pobrać i zainstalować składniki odtwarzacza wideo (około {size} MB)?",
        "player_installing": "Instalowanie odtwarzacza...",
        "player_install_ok": "Odtwarzacz zainstalowany.",
        "player_install_failed": "Instalacja odtwarzacza nie powiodła się: sprawdź dziennik.",
        "player_credits": "Odtwarzanie wideo: mpv (libmpv), {license}",
        "player_license_system": "biblioteka systemowa",
        "live_err_busy_install": "Trwa instalacja: poczekaj, aż się zakończy.",
    },
    "pt": {
        "player_badge": "Player",
        "player_badge_ok": "Player pronto (mpv {version})",
        "player_unavailable_title": "Player integrado indisponível",
        "player_missing_pymod": "O pacote python-mpv não está instalado.",
        "player_missing_libmpv_linux": "A libmpv não está instalada. Instale-a com: {cmd}",
        "player_missing_libmpv_win": "A libmpv não está instalada. Execute setup_windows.bat (Repair) ou instale-a agora.",
        "player_libmpv_too_old": "A libmpv instalada ({version}) é antiga demais: é necessária a versão 0.34 ou mais recente.",
        "player_libmpv_load_failed": "Não foi possível carregar a libmpv ({detail}). O arquivo pode estar danificado ou bloqueado pelo antivírus.",
        "player_vulkan_missing": "A libmpv precisa do runtime Vulkan (vulkan-1.dll): atualize o driver gráfico ou instale o player novamente.",
        "player_probe_crashed": "A libmpv travou durante o carregamento: o player continua desativado. Veja o registro.",
        "player_restart_required": "Reinicie o aplicativo para concluir a ativação do player.",
        "player_install_btn": "Instalar player",
        "player_install_confirm": "Baixar e instalar os componentes do player de vídeo (cerca de {size} MB)?",
        "player_installing": "Instalando o player...",
        "player_install_ok": "Player instalado.",
        "player_install_failed": "A instalação do player falhou: veja o registro.",
        "player_credits": "Reprodução de vídeo: mpv (libmpv), {license}",
        "player_license_system": "biblioteca do sistema",
        "live_err_busy_install": "Há uma instalação em andamento: aguarde a conclusão.",
    },
    "ro": {
        "player_badge": "Player",
        "player_badge_ok": "Playerul este pregătit (mpv {version})",
        "player_unavailable_title": "Playerul integrat nu este disponibil",
        "player_missing_pymod": "Pachetul python-mpv nu este instalat.",
        "player_missing_libmpv_linux": "libmpv nu este instalată. Instalați-o cu: {cmd}",
        "player_missing_libmpv_win": "libmpv nu este instalată. Rulați setup_windows.bat (Repair) sau instalați-o acum.",
        "player_libmpv_too_old": "libmpv instalată ({version}) este prea veche: este necesară versiunea 0.34 sau mai nouă.",
        "player_libmpv_load_failed": "libmpv nu a putut fi încărcată ({detail}). Fișierul poate fi deteriorat sau blocat de antivirus.",
        "player_vulkan_missing": "libmpv are nevoie de mediul de rulare Vulkan (vulkan-1.dll): actualizați driverul plăcii grafice sau reinstalați playerul.",
        "player_probe_crashed": "libmpv s-a oprit neașteptat în timpul încărcării: playerul rămâne dezactivat. Consultați jurnalul.",
        "player_restart_required": "Reporniți aplicația pentru a finaliza activarea playerului.",
        "player_install_btn": "Instalează playerul",
        "player_install_confirm": "Descărcați și instalați componentele playerului video (aproximativ {size} MB)?",
        "player_installing": "Se instalează playerul...",
        "player_install_ok": "Playerul a fost instalat.",
        "player_install_failed": "Instalarea playerului a eșuat: consultați jurnalul.",
        "player_credits": "Redare video: mpv (libmpv), {license}",
        "player_license_system": "bibliotecă de sistem",
        "live_err_busy_install": "O instalare este în curs: așteptați să se termine.",
    },
    "ru": {
        "player_badge": "Плеер",
        "player_badge_ok": "Плеер готов (mpv {version})",
        "player_unavailable_title": "Встроенный плеер недоступен",
        "player_missing_pymod": "Пакет python-mpv не установлен.",
        "player_missing_libmpv_linux": "libmpv не установлена. Установите её командой: {cmd}",
        "player_missing_libmpv_win": "libmpv не установлена. Запустите setup_windows.bat (Repair) или установите её сейчас.",
        "player_libmpv_too_old": "Установленная libmpv ({version}) слишком старая: нужна версия 0.34 или новее.",
        "player_libmpv_load_failed": "Не удалось загрузить libmpv ({detail}). Возможно, файл повреждён или заблокирован антивирусом.",
        "player_vulkan_missing": "Для libmpv нужна среда выполнения Vulkan (vulkan-1.dll): обновите драйвер видеокарты или установите плеер заново.",
        "player_probe_crashed": "libmpv аварийно завершилась при загрузке: плеер остаётся отключённым. См. журнал.",
        "player_restart_required": "Перезапустите приложение, чтобы завершить включение плеера.",
        "player_install_btn": "Установить плеер",
        "player_install_confirm": "Скачать и установить компоненты видеоплеера (около {size} МБ)?",
        "player_installing": "Установка плеера...",
        "player_install_ok": "Плеер установлен.",
        "player_install_failed": "Не удалось установить плеер: см. журнал.",
        "player_credits": "Воспроизведение видео: mpv (libmpv), {license}",
        "player_license_system": "системная библиотека",
        "live_err_busy_install": "Идёт установка: дождитесь её завершения.",
    },
    "es": {
        "player_badge": "Reproductor",
        "player_badge_ok": "Reproductor listo (mpv {version})",
        "player_unavailable_title": "Reproductor integrado no disponible",
        "player_missing_pymod": "El paquete python-mpv no está instalado.",
        "player_missing_libmpv_linux": "libmpv no está instalada. Instálala con: {cmd}",
        "player_missing_libmpv_win": "libmpv no está instalada. Ejecuta setup_windows.bat (Repair) o instálala ahora.",
        "player_libmpv_too_old": "La libmpv instalada ({version}) es demasiado antigua: se necesita la versión 0.34 o posterior.",
        "player_libmpv_load_failed": "No se pudo cargar libmpv ({detail}). Puede que el archivo esté dañado o bloqueado por el antivirus.",
        "player_vulkan_missing": "libmpv necesita el runtime de Vulkan (vulkan-1.dll): actualiza el controlador gráfico o vuelve a instalar el reproductor.",
        "player_probe_crashed": "libmpv se bloqueó durante la carga: el reproductor sigue desactivado. Consulta el registro.",
        "player_restart_required": "Reinicia la aplicación para terminar de activar el reproductor.",
        "player_install_btn": "Instalar reproductor",
        "player_install_confirm": "¿Descargar e instalar los componentes del reproductor de vídeo (unos {size} MB)?",
        "player_installing": "Instalando el reproductor...",
        "player_install_ok": "Reproductor instalado.",
        "player_install_failed": "La instalación del reproductor falló: consulta el registro.",
        "player_credits": "Reproducción de vídeo: mpv (libmpv), {license}",
        "player_license_system": "biblioteca del sistema",
        "live_err_busy_install": "Hay una instalación en curso: espera a que termine.",
    },
    "sv": {
        "player_badge": "Spelare",
        "player_badge_ok": "Spelaren är redo (mpv {version})",
        "player_unavailable_title": "Den inbyggda spelaren är inte tillgänglig",
        "player_missing_pymod": "Paketet python-mpv är inte installerat.",
        "player_missing_libmpv_linux": "libmpv är inte installerat. Installera det med: {cmd}",
        "player_missing_libmpv_win": "libmpv är inte installerat. Kör setup_windows.bat (Repair) eller installera det nu.",
        "player_libmpv_too_old": "Den installerade libmpv ({version}) är för gammal: version 0.34 eller senare krävs.",
        "player_libmpv_load_failed": "libmpv kunde inte läsas in ({detail}). Filen kan vara skadad eller blockerad av antivirusprogrammet.",
        "player_vulkan_missing": "libmpv behöver Vulkan-körmiljön (vulkan-1.dll): uppdatera grafikdrivrutinen eller installera om spelaren.",
        "player_probe_crashed": "libmpv kraschade vid inläsningen: spelaren förblir inaktiverad. Se loggen.",
        "player_restart_required": "Starta om programmet för att slutföra aktiveringen av spelaren.",
        "player_install_btn": "Installera spelare",
        "player_install_confirm": "Vill du hämta och installera videospelarens komponenter (cirka {size} MB)?",
        "player_installing": "Installerar spelaren...",
        "player_install_ok": "Spelaren är installerad.",
        "player_install_failed": "Installationen av spelaren misslyckades: se loggen.",
        "player_credits": "Videouppspelning: mpv (libmpv), {license}",
        "player_license_system": "systembibliotek",
        "live_err_busy_install": "En installation pågår: vänta tills den är klar.",
    },
    "tr": {
        "player_badge": "Oynatıcı",
        "player_badge_ok": "Oynatıcı hazır (mpv {version})",
        "player_unavailable_title": "Yerleşik oynatıcı kullanılamıyor",
        "player_missing_pymod": "python-mpv paketi yüklü değil.",
        "player_missing_libmpv_linux": "libmpv yüklü değil. Şu komutla yükleyin: {cmd}",
        "player_missing_libmpv_win": "libmpv yüklü değil. setup_windows.bat (Repair) çalıştırın veya şimdi yükleyin.",
        "player_libmpv_too_old": "Yüklü libmpv ({version}) çok eski: 0.34 veya daha yeni bir sürüm gerekiyor.",
        "player_libmpv_load_failed": "libmpv yüklenemedi ({detail}). Dosya bozuk olabilir veya virüsten koruma yazılımı tarafından engellenmiş olabilir.",
        "player_vulkan_missing": "libmpv, Vulkan çalışma zamanına (vulkan-1.dll) ihtiyaç duyuyor: grafik sürücüsünü güncelleyin veya oynatıcıyı yeniden yükleyin.",
        "player_probe_crashed": "libmpv yüklenirken çöktü: oynatıcı devre dışı kalıyor. Günlüğe bakın.",
        "player_restart_required": "Oynatıcının etkinleştirilmesini tamamlamak için uygulamayı yeniden başlatın.",
        "player_install_btn": "Oynatıcıyı yükle",
        "player_install_confirm": "Video oynatıcı bileşenleri indirilip yüklensin mi (yaklaşık {size} MB)?",
        "player_installing": "Oynatıcı yükleniyor...",
        "player_install_ok": "Oynatıcı yüklendi.",
        "player_install_failed": "Oynatıcı yüklenemedi: günlüğe bakın.",
        "player_credits": "Video oynatma: mpv (libmpv), {license}",
        "player_license_system": "sistem kitaplığı",
        "live_err_busy_install": "Bir yükleme devam ediyor: bitmesini bekleyin.",
    },
    "uk": {
        "player_badge": "Плеєр",
        "player_badge_ok": "Плеєр готовий (mpv {version})",
        "player_unavailable_title": "Вбудований плеєр недоступний",
        "player_missing_pymod": "Пакет python-mpv не встановлено.",
        "player_missing_libmpv_linux": "libmpv не встановлено. Встановіть її командою: {cmd}",
        "player_missing_libmpv_win": "libmpv не встановлено. Запустіть setup_windows.bat (Repair) або встановіть її зараз.",
        "player_libmpv_too_old": "Встановлена libmpv ({version}) занадто стара: потрібна версія 0.34 або новіша.",
        "player_libmpv_load_failed": "Не вдалося завантажити libmpv ({detail}). Можливо, файл пошкоджено або заблоковано антивірусом.",
        "player_vulkan_missing": "Для libmpv потрібне середовище виконання Vulkan (vulkan-1.dll): оновіть драйвер відеокарти або встановіть плеєр знову.",
        "player_probe_crashed": "libmpv аварійно завершила роботу під час завантаження: плеєр залишається вимкненим. Див. журнал.",
        "player_restart_required": "Перезапустіть застосунок, щоб завершити увімкнення плеєра.",
        "player_install_btn": "Встановити плеєр",
        "player_install_confirm": "Завантажити та встановити компоненти відеоплеєра (близько {size} МБ)?",
        "player_installing": "Встановлення плеєра...",
        "player_install_ok": "Плеєр встановлено.",
        "player_install_failed": "Не вдалося встановити плеєр: див. журнал.",
        "player_credits": "Відтворення відео: mpv (libmpv), {license}",
        "player_license_system": "системна бібліотека",
        "live_err_busy_install": "Триває встановлення: зачекайте, доки воно завершиться.",
    },
    "vi": {
        "player_badge": "Trình phát",
        "player_badge_ok": "Trình phát đã sẵn sàng (mpv {version})",
        "player_unavailable_title": "Trình phát tích hợp không khả dụng",
        "player_missing_pymod": "Gói python-mpv chưa được cài đặt.",
        "player_missing_libmpv_linux": "libmpv chưa được cài đặt. Hãy cài đặt bằng lệnh: {cmd}",
        "player_missing_libmpv_win": "libmpv chưa được cài đặt. Hãy chạy setup_windows.bat (Repair) hoặc cài đặt ngay.",
        "player_libmpv_too_old": "libmpv đã cài đặt ({version}) quá cũ: cần phiên bản 0.34 trở lên.",
        "player_libmpv_load_failed": "Không thể tải libmpv ({detail}). Tệp có thể bị hỏng hoặc bị phần mềm diệt virus chặn.",
        "player_vulkan_missing": "libmpv cần môi trường chạy Vulkan (vulkan-1.dll): hãy cập nhật trình điều khiển đồ họa hoặc cài đặt lại trình phát.",
        "player_probe_crashed": "libmpv bị lỗi khi tải: trình phát vẫn bị tắt. Xem nhật ký.",
        "player_restart_required": "Hãy khởi động lại ứng dụng để hoàn tất việc bật trình phát.",
        "player_install_btn": "Cài đặt trình phát",
        "player_install_confirm": "Tải xuống và cài đặt các thành phần của trình phát video (khoảng {size} MB)?",
        "player_installing": "Đang cài đặt trình phát...",
        "player_install_ok": "Đã cài đặt trình phát.",
        "player_install_failed": "Cài đặt trình phát thất bại: xem nhật ký.",
        "player_credits": "Phát video: mpv (libmpv), {license}",
        "player_license_system": "thư viện hệ thống",
        "live_err_busy_install": "Đang có một quá trình cài đặt: hãy chờ đến khi hoàn tất.",
    },
}

PLAYER_KEYS: tuple[str, ...] = tuple(sorted(PLAYER_UI_STRINGS["en"]))


def merge_into(ui_strings: dict[str, dict[str, str]]) -> list[str]:
    """Add the player strings to ``ui_strings`` in place and return the problems found.

    Never raises (spec 2.6, [CC] G27): a key that already exists with a
    different value keeps the existing value and is reported as
    ``"collision <lang>.<key>"``; a language the target does not have is
    skipped and reported as ``"unknown language '<lang>'"``. Merging twice is
    harmless (equal values are not collisions).
    """
    problems: list[str] = []
    for lang, entries in PLAYER_UI_STRINGS.items():
        bucket = ui_strings.get(lang)
        if bucket is None:
            problems.append(f"unknown language {lang!r}")
            continue
        for key, value in entries.items():
            existing = bucket.get(key)
            if existing is not None and existing != value:
                problems.append(f"collision {lang}.{key}")
                continue
            bucket[key] = value
    return problems
```

- [ ] **Step 4: Merge the strings in the GUI file and log problems**

In `video_translator_gui.py`, right after the line `UI_LANG_CODES = {code for code, _ in UI_LANG_OPTIONS}`:

```python
# Player and live-mode strings live in their own module (spec 2.6, Q5) and are
# merged here, so UI_STRINGS stays the single runtime dictionary. merge_into
# never raises: problems are logged at startup and caught by the i18n tests.
from videotranslator.ui_strings_player import merge_into as _merge_player_strings  # noqa: E402
_PLAYER_STRING_PROBLEMS = _merge_player_strings(UI_STRINGS)
```

In `App.__init__`, right before `self.protocol("WM_DELETE_WINDOW", self._on_close)` (the log widget exists by then):

```python
        for problem in _PLAYER_STRING_PROBLEMS:
            self._log_write(f"[!] Player strings: {problem}\n")
```

- [ ] **Step 5: Run the i18n tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_ui_i18n_coverage -v`
Expected: all OK (the display-dependent classes skip without a display). The placeholder-consistency test now also covers the 19 keys.

- [ ] **Step 6: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' videotranslator/ui_strings_player.py video_translator_gui.py tests/test_ui_i18n_coverage.py || echo "no long dashes"
git add videotranslator/ui_strings_player.py video_translator_gui.py tests/test_ui_i18n_coverage.py
git commit -m "i18n: add the integrated player strings module in 26 languages

The player and live-mode strings live in videotranslator/ui_strings_player.py
(operator decision Q5) and are merged into UI_STRINGS at import; merge_into
never raises and reports collisions and unknown languages instead. The i18n
scans now also cover the *_tk.py modules, and a literal-key test guards the
keys carried by the pure player modules. This adds the 19 keys used by P1
(availability, install, badge)."
```

---
## Task 3: libmpv detection, subprocess probe and import gate

Review level: full

(Native library loading through ctypes, a crash-isolating subprocess, process-wide PATH and DLL-directory changes on Windows.)

**Files:**
- Create: `videotranslator/libmpv_runtime.py`
- Create: `tests/test_libmpv_runtime.py`
- Create: `tests/test_import_hygiene.py`
- Modify: `tests/test_ui_i18n_coverage.py` (reason-key coverage)

**Interfaces:**
- Consumes: `videotranslator.subprocess_utils.no_window_kwargs` (Task 1), `videotranslator.js_runtime.app_data_dir`, the 19 keys of Task 2.
- Produces (all in `videotranslator.libmpv_runtime`):
  - constants `MIN_API = (1, 108)`, `TESTED_FLOOR = (0, 34)`, `AF_TARGET_MIN = (0, 37)`, `RUNTIME_DIR_NAME = "mpv-runtime"`, `WINDOWS_DLL_TARGET = "mpv-2.dll"`, `WINDOWS_DLL_NAMES`, `LINUX_SONAMES`, `VULKAN_DIR_NAME = "vulkan-fallback"`, `VULKAN_DLL = "vulkan-1.dll"`, `PYTHON_MPV_REQUIREMENT = "mpv>=1.0.6,<2"`, `PROBE_TIMEOUT_S = 20.0`, `PACKAGE_ROOT: Path`, `REASONS: tuple[str, ...]`, `LIBRARY_OK_REASONS: frozenset[str]`, `REASON_KEYS: dict[str, str]`, `REASON_KEYS_WIN32: dict[str, str]`, `VO_PROFILE_OPTIONS: dict[str, dict[str, dict[str, str]]]`
  - `@dataclass(frozen=True) class LibmpvStatus(ok: bool, reason: str, api_version: tuple[int, int] | None = None, mpv_version: tuple[int, int] | None = None, path: str | None = None, vo_profiles_ok: tuple[str, ...] = (), detail: str = "", build: Mapping[str, str] = {}, fingerprint: str | None = None)`
  - `class PlayerUnavailable(Exception)` with attribute `status: LibmpvStatus`
  - UI helpers: `library_loaded(status) -> bool`, `reason_key(reason, sys_platform) -> str`, `format_version(status) -> str`, `status_message(status, *, sys_platform, install_cmd=None) -> tuple[str, dict[str, str]]`, `badge_level(status) -> str` (`"ok" | "warn" | "error"`), `offers_install(status, *, sys_platform) -> bool`, `windows_download_mb(*, vulkan: bool) -> int`
  - paths: `per_user_runtime_dir(env=None) -> Path`, `windows_candidate_dirs(env, app_dir) -> list[Path]`, `find_vulkan_fallback(runtime_dir, env) -> Path | None`, `default_system32(env) -> Path`
  - parsing: `parse_api_version(raw) -> tuple[int, int]`, `parse_mpv_version(text) -> tuple[int, int] | None`, `parse_ldconfig(output, soname_prefix="libmpv.so", *, want_64bit=...) -> str | None`, `parse_maps(text, marker="libmpv.so") -> str | None`, `library_fingerprint(path) -> str | None`, `read_build_txt(directory) -> dict[str, str]`, `read_ldconfig_cache(*, run, which) -> str`
  - `classify_import_error(exc, *, sys_platform, vulkan_present) -> str`
  - `quick_presence(*, sys_platform, env, app_dir, find_library, run_ldconfig, find_spec, isfile) -> LibmpvStatus` (no library load)
  - `probe_libmpv(*, sys_platform, env, app_dir, runtime_dir, find_library, cdll, run_ldconfig, read_maps, isfile, add_dll_directory, system32) -> LibmpvStatus` (loads; runs only inside the `check` subprocess)
  - `status_to_json(status) -> str`, `status_from_json(text) -> LibmpvStatus | None`
  - `probe_in_subprocess(*, run=subprocess.run, python=sys.executable, timeout=PROBE_TIMEOUT_S, runtime_dir=None, cwd=PACKAGE_ROOT, sys_platform=sys.platform) -> LibmpvStatus`
  - cache: `cache_entry(status) -> dict | None`, `status_from_cache(quick, cached) -> LibmpvStatus | None`, `resolve_status(*, cached=None, force_probe=False, quick=None, probe=None) -> LibmpvStatus`
  - import gate: `prepare_import(env, *, sys_platform, runtime_dir, add_dll_directory, system32_has_vulkan) -> Callable[[], None]`, `load_mpv(*, importer=importlib.import_module, sys_platform=sys.platform, env=None, app_dir=None, add_dll_directory=None, system32=None) -> ModuleType`
  - CLI: `main(argv=None, *, sys_platform=sys.platform) -> int` with `check [--dir DIR] [--json]` (exit 0 ok, 2 unavailable, 3 unexpected error, never 1)

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_libmpv_runtime.py`:

```python
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
```

Create `tests/test_import_hygiene.py`:

```python
"""Importing the player modules never pulls a heavy or native dependency (spec 7.1).

Each import runs in a fresh interpreter, so the result does not depend on
which tests ran before in this process ([CC] T3).
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "videotranslator.libmpv_runtime",
    "videotranslator.subprocess_utils",
    "videotranslator.ui_strings_player",
)
FORBIDDEN = ("mpv", "av", "faster_whisper", "edge_tts", "transformers", "yt_dlp", "onnxruntime")


class ImportHygieneTests(unittest.TestCase):
    def test_player_modules_import_without_heavy_dependencies(self):
        for module in MODULES:
            with self.subTest(module=module):
                code = ("import importlib, json, sys; importlib.import_module(%r); "
                        "print(json.dumps(sorted(m for m in %r if m in sys.modules)))"
                        % (module, FORBIDDEN))
                proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]), [])


if __name__ == "__main__":
    unittest.main()
```

Append to `tests/test_ui_i18n_coverage.py` (add `from videotranslator import libmpv_runtime` to the imports):

```python
class PlayerReasonKeyTests(unittest.TestCase):
    """Every LibmpvStatus reason maps to a key that exists in 26 languages (spec 2.6)."""

    def test_reason_maps_cover_every_reason(self):
        self.assertEqual(set(libmpv_runtime.REASON_KEYS), set(libmpv_runtime.REASONS))
        self.assertEqual(set(libmpv_runtime.REASON_KEYS_WIN32), set(libmpv_runtime.REASONS))

    def test_reason_keys_exist_in_every_language(self):
        keys = set(libmpv_runtime.REASON_KEYS.values()) | set(libmpv_runtime.REASON_KEYS_WIN32.values())
        missing = [(lang, key) for key in sorted(keys) for lang in sorted(UI_STRINGS)
                   if key not in UI_STRINGS[lang]]
        self.assertEqual(missing, [])
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_libmpv_runtime test_import_hygiene test_ui_i18n_coverage -v`
Expected: ERROR `ModuleNotFoundError: No module named 'videotranslator.libmpv_runtime'`.

- [ ] **Step 3: Create `videotranslator/libmpv_runtime.py`**

```python
"""Find, probe and import libmpv for the integrated player (spec 2.2, 3.1, 6.1).

Policy:

* ``quick_presence`` loads nothing: it looks for the library file (Windows)
  or asks ``ldconfig -p`` (Linux). It feeds the startup badge.
* ``probe_libmpv`` loads the library with ctypes, reads the client API and
  the mpv version and checks which video-output profiles this build accepts.
  It runs ONLY inside ``python -m videotranslator.libmpv_runtime check``
  (``probe_in_subprocess``), so a library that crashes on load cannot take
  the application down.
* ``load_mpv`` is the only ``import mpv`` in the code base; it must run off
  the Tk thread (P2).

Every side effect is a parameter, so the tests run without libmpv,
python-mpv, network or display. Log and detail text stays English; the GUI
shows translated keys (REASON_KEYS).
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import dataclasses
import importlib
import importlib.util
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from .js_runtime import app_data_dir
from .subprocess_utils import no_window_kwargs

MIN_API = (1, 108)          # python-mpv refuses older libmpv at import (mpv.py:565)
TESTED_FLOOR = (0, 34)      # lowest mpv release covered by the S1/S3 checks (Q13)
AF_TARGET_MIN = (0, 37)     # `af-command ... <target>` exists from 0.37 ([CT] C29)
RUNTIME_DIR_NAME = "mpv-runtime"   # a hyphen: never importable as a package
WINDOWS_DLL_TARGET = "mpv-2.dll"   # python-mpv tries this name first
WINDOWS_DLL_NAMES = (WINDOWS_DLL_TARGET, "libmpv-2.dll")
LINUX_SONAMES = ("libmpv.so.2", "libmpv.so.1", "libmpv.so")
VULKAN_DIR_NAME = "vulkan-fallback"
VULKAN_DLL = "vulkan-1.dll"
PYTHON_MPV_REQUIREMENT = "mpv>=1.0.6,<2"
PROBE_TIMEOUT_S = 20.0
# The folder that contains the videotranslator package: the working directory
# of `python -m videotranslator...` children (the desktop shortcut may start
# the GUI from anywhere).
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

REASONS: tuple[str, ...] = (
    "ok", "python-mpv-missing", "libmpv-missing", "libmpv-too-old",
    "libmpv-load-failed", "vulkan-loader-missing", "probe-crashed", "restart-required",
)
# The library itself loads in these states (python-mpv is judged separately).
LIBRARY_OK_REASONS = frozenset({"ok", "python-mpv-missing"})
REASON_KEYS: dict[str, str] = {
    "ok": "player_badge_ok",
    "python-mpv-missing": "player_missing_pymod",
    "libmpv-missing": "player_missing_libmpv_linux",
    "libmpv-too-old": "player_libmpv_too_old",
    "libmpv-load-failed": "player_libmpv_load_failed",
    "vulkan-loader-missing": "player_vulkan_missing",
    "probe-crashed": "player_probe_crashed",
    "restart-required": "player_restart_required",
}
REASON_KEYS_WIN32: dict[str, str] = {**REASON_KEYS, "libmpv-missing": "player_missing_libmpv_win"}
_ERROR_REASONS = frozenset({"libmpv-too-old", "libmpv-load-failed", "probe-crashed"})
_INSTALLABLE_REASONS = frozenset({"python-mpv-missing", "libmpv-missing"})

# Video-output profiles, in fallback order, with libmpv option names (dashes).
# P2's player_engine derives VO_PROFILES from this table. x11glx is absent on
# purpose: gpu-context=x11 is rejected by the Kali 0.41 build ([CT] R1).
VO_PROFILE_OPTIONS: dict[str, dict[str, dict[str, str]]] = {
    "linux": {
        "x11egl": {"vo": "gpu", "gpu-context": "x11egl"},
        "x11vk": {"vo": "gpu", "gpu-api": "vulkan", "gpu-context": "x11vk"},
        "x11sw": {"vo": "x11"},
    },
    "win32": {
        "auto": {"vo": "gpu"},
        "d3d11-warp": {"vo": "gpu", "gpu-api": "d3d11", "d3d11-warp": "yes"},
    },
}
_VERSION_PROBE_OPTIONS = (
    ("vo", "null"), ("ao", "null"), ("idle", "yes"), ("load-scripts", "no"),
    ("ytdl", "no"), ("config", "no"), ("terminal", "no"),
)

# Handles returned by os.add_dll_directory must stay referenced for the whole
# process: closing one drops the directory while libmpv may still resolve
# imports from it ([CT] C9).
_DLL_DIR_HANDLES: list[Any] = []
_MPV_MODULE: ModuleType | None = None
_MPV_LOCK = threading.Lock()


@dataclass(frozen=True)
class LibmpvStatus:
    ok: bool
    reason: str
    api_version: tuple[int, int] | None = None
    mpv_version: tuple[int, int] | None = None
    path: str | None = None
    vo_profiles_ok: tuple[str, ...] = ()
    detail: str = ""
    build: Mapping[str, str] = field(default_factory=dict)
    fingerprint: str | None = None


def _status(reason: str, **fields: Any) -> LibmpvStatus:
    return LibmpvStatus(ok=reason == "ok", reason=reason, **fields)


class PlayerUnavailable(Exception):
    """Raised by load_mpv; ``status`` says why."""

    def __init__(self, status: LibmpvStatus) -> None:
        super().__init__(f"{status.reason}: {status.detail}")
        self.status = status


# -- UI helpers (pure) ---------------------------------------------------

def library_loaded(status: LibmpvStatus) -> bool:
    return status.reason in LIBRARY_OK_REASONS


def reason_key(reason: str, sys_platform: str) -> str:
    keys = REASON_KEYS_WIN32 if sys_platform == "win32" else REASON_KEYS
    return keys[reason]


def format_version(status: LibmpvStatus) -> str:
    if status.mpv_version:
        return f"{status.mpv_version[0]}.{status.mpv_version[1]}"
    if status.api_version:
        return f"API {status.api_version[0]}.{status.api_version[1]}"
    return "?"


def _shorten(text: str, limit: int = 120) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def status_message(status: LibmpvStatus, *, sys_platform: str,
                   install_cmd: str | None = None) -> tuple[str, dict[str, str]]:
    """Return (UI_STRINGS key, format params) that explain ``status``."""
    params: dict[str, str] = {}
    if status.reason in ("ok", "libmpv-too-old"):
        params["version"] = format_version(status)
    elif status.reason == "libmpv-load-failed":
        params["detail"] = _shorten(status.detail or status.reason)
    elif status.reason == "libmpv-missing" and sys_platform != "win32":
        params["cmd"] = install_cmd or "libmpv2"
    return reason_key(status.reason, sys_platform), params


def badge_level(status: LibmpvStatus) -> str:
    if status.ok:
        return "ok"
    if status.reason in _ERROR_REASONS:
        return "error"
    return "warn"


def offers_install(status: LibmpvStatus, *, sys_platform: str) -> bool:
    """True when an Install action can fix ``status`` (spec 6.1)."""
    if status.reason in _INSTALLABLE_REASONS:
        return True
    return status.reason == "vulkan-loader-missing" and sys_platform == "win32"


def windows_download_mb(*, vulkan: bool) -> int:
    """Download size announced by player_install_confirm (spec 8.3)."""
    return 32 + (18 if vulkan else 0)


# -- paths -----------------------------------------------------------------

def per_user_runtime_dir(env: Mapping[str, str] | None = None) -> Path:
    """%LOCALAPPDATA%\\VideoTranslatorAI\\mpv-runtime (the GUI per-user install, Q6)."""
    return app_data_dir(system="win32", env=dict(env) if env is not None else None) / RUNTIME_DIR_NAME


def windows_candidate_dirs(env: Mapping[str, str], app_dir: Path) -> list[Path]:
    """Folders searched for mpv-2.dll, in order (spec 2.2)."""
    dirs: list[Path] = []
    if env.get("VTAI_LIBMPV_DIR"):
        dirs.append(Path(env["VTAI_LIBMPV_DIR"]))
    dirs.append(Path(app_dir) / RUNTIME_DIR_NAME)
    if env.get("ProgramFiles"):
        dirs.append(Path(env["ProgramFiles"]) / "VideoTranslatorAI" / RUNTIME_DIR_NAME)
    if env.get("LOCALAPPDATA"):
        dirs.append(Path(env["LOCALAPPDATA"]) / "VideoTranslatorAI" / RUNTIME_DIR_NAME)
    unique: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        key = os.path.normcase(str(directory))
        if key not in seen:
            seen.add(key)
            unique.append(directory)
    return unique


def find_vulkan_fallback(runtime_dir: Path | None, env: Mapping[str, str]) -> Path | None:
    """The folder holding our vulkan-1.dll copy: next to the DLL, then per user."""
    candidates = []
    if runtime_dir is not None:
        candidates.append(Path(runtime_dir) / VULKAN_DIR_NAME)
    candidates.append(per_user_runtime_dir(env) / VULKAN_DIR_NAME)
    for candidate in candidates:
        if (candidate / VULKAN_DLL).is_file():
            return candidate
    return None


def default_system32(env: Mapping[str, str]) -> Path:
    root = env.get("SystemRoot") or env.get("SYSTEMROOT") or "C:\\Windows"
    return Path(root) / "System32"


# -- parsing ---------------------------------------------------------------

def parse_api_version(raw: int) -> tuple[int, int]:
    raw = int(raw)
    return raw >> 16, raw & 0xFFFF


_MPV_VERSION_RE = re.compile(r"\bmpv\s+v?(\d+)\.(\d+)")


def parse_mpv_version(text: str) -> tuple[int, int] | None:
    """"mpv 0.41.0" or "mpv v0.41.0-1050-ge76a35ec9" -> (0, 41)."""
    match = _MPV_VERSION_RE.search(text or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


_LDCONFIG_RE = re.compile(r"^\s*(?P<name>\S+)\s+\((?P<flags>[^)]*)\)\s+=>\s+(?P<path>\S.*?)\s*$")


def parse_ldconfig(output: str, soname_prefix: str = "libmpv.so", *,
                   want_64bit: bool = sys.maxsize > 2**32) -> str | None:
    """Path of the newest ``soname_prefix`` entry for this architecture in ``ldconfig -p``."""
    best: tuple[tuple[int, ...], str] | None = None
    for line in (output or "").splitlines():
        match = _LDCONFIG_RE.match(line)
        if not match:
            continue
        name = match.group("name")
        if name != soname_prefix and not name.startswith(soname_prefix + "."):
            continue
        if ("64" in match.group("flags")) != want_64bit:
            continue
        version = tuple(int(part) for part in name[len(soname_prefix):].split(".") if part.isdigit())
        if best is None or version > best[0]:
            best = (version, match.group("path"))
    return best[1] if best else None


def parse_maps(text: str, marker: str = "libmpv.so") -> str | None:
    """Path of the mapped library from /proc/self/maps text."""
    for line in (text or "").splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and marker in os.path.basename(parts[5].strip()):
            return parts[5].strip()
    return None


def library_fingerprint(path: str | None) -> str | None:
    """"<realpath>|<size>|<mtime_ns>": an apt upgrade or a new DLL changes it."""
    if not path:
        return None
    try:
        real = os.path.realpath(path)
        stat = os.stat(real)
    except (OSError, TypeError, ValueError):
        return None
    return f"{real}|{stat.st_size}|{stat.st_mtime_ns}"


def read_build_txt(directory: Path) -> dict[str, str]:
    """BUILD.txt written by install_windows (key=value lines), {} when absent."""
    try:
        text = (Path(directory) / "BUILD.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    return fields


def read_ldconfig_cache(*, run: Callable[..., Any] = subprocess.run,
                        which: Callable[[str], str | None] = shutil.which) -> str:
    """Output of ``ldconfig -p`` (it lives in /sbin, often off a user's PATH)."""
    for exe in (which("ldconfig"), "/sbin/ldconfig", "/usr/sbin/ldconfig"):
        if not exe or not os.path.isfile(exe):
            continue
        try:
            proc = run([exe, "-p"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=10, check=False, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            continue
        return proc.stdout or ""
    return ""


def _read_self_maps() -> str:
    try:
        return Path("/proc/self/maps").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def classify_import_error(exc: BaseException, *, sys_platform: str, vulkan_present: bool) -> str:
    """Map a load or ``import mpv`` failure to a LibmpvStatus reason (spec 6.1)."""
    if isinstance(exc, ImportError):
        return "python-mpv-missing"
    if isinstance(exc, OSError):
        if "Cannot find" in str(exc):   # python-mpv's own "not found" messages
            return "libmpv-missing"
        if sys_platform == "win32":
            code = getattr(exc, "winerror", None) or getattr(exc.__cause__, "winerror", None)
            if code == 126 and not vulkan_present:
                return "vulkan-loader-missing"
        return "libmpv-load-failed"
    if isinstance(exc, AttributeError):
        return "libmpv-too-old"
    if isinstance(exc, RuntimeError) and "API version" in str(exc):
        return "libmpv-too-old"
    return "libmpv-load-failed"


def _module_present(name: str, find_spec: Callable[[str], Any]) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _locate_library(*, sys_platform: str, env: Mapping[str, str], app_dir: Path,
                    runtime_dir: Path | None, find_library: Callable[[str], str | None],
                    run_ldconfig: Callable[[], str],
                    isfile: Callable[[str], bool]) -> tuple[str | None, dict[str, str]]:
    """(library path or soname, BUILD.txt fields) without loading anything."""
    if sys_platform == "win32":
        dirs = [Path(runtime_dir)] if runtime_dir is not None else windows_candidate_dirs(env, app_dir)
        for directory in dirs:
            for name in WINDOWS_DLL_NAMES:
                candidate = directory / name
                if isfile(str(candidate)):
                    return str(candidate), read_build_txt(directory)
        return None, {}
    if runtime_dir is not None:
        dirs = [Path(runtime_dir)]
    elif env.get("VTAI_LIBMPV_DIR"):
        dirs = [Path(env["VTAI_LIBMPV_DIR"])]   # dev override (plan decision 5)
    else:
        dirs = []
    for directory in dirs:
        for name in LINUX_SONAMES:
            candidate = directory / name
            if isfile(str(candidate)):
                return str(candidate), {}
    if runtime_dir is not None:
        return None, {}
    path = parse_ldconfig(run_ldconfig())
    if path:
        return path, {}
    return find_library("mpv"), {}


# -- detection -------------------------------------------------------------

def quick_presence(*, sys_platform: str = sys.platform, env: Mapping[str, str] | None = None,
                   app_dir: Path | None = None,
                   find_library: Callable[[str], str | None] = ctypes.util.find_library,
                   run_ldconfig: Callable[[], str] = read_ldconfig_cache,
                   find_spec: Callable[[str], Any] = importlib.util.find_spec,
                   isfile: Callable[[str], bool] = os.path.isfile) -> LibmpvStatus:
    """Startup status without loading libmpv: the library first, then python-mpv."""
    env = os.environ if env is None else env
    app_dir = PACKAGE_ROOT if app_dir is None else Path(app_dir)
    path, build = _locate_library(sys_platform=sys_platform, env=env, app_dir=app_dir,
                                  runtime_dir=None, find_library=find_library,
                                  run_ldconfig=run_ldconfig, isfile=isfile)
    if path is None:
        if sys_platform == "win32":
            where = ", ".join(str(d) for d in windows_candidate_dirs(env, app_dir))
            return _status("libmpv-missing", detail=f"no {WINDOWS_DLL_TARGET} in {where}")
        return _status("libmpv-missing", detail="no libmpv.so in ldconfig -p")
    fingerprint = library_fingerprint(path)
    if not _module_present("mpv", find_spec):
        return _status("python-mpv-missing", path=path, build=build, fingerprint=fingerprint,
                       detail="python-mpv (module mpv) is not importable")
    return _status("ok", path=path, build=build, fingerprint=fingerprint,
                   detail="library found (not loaded)")


def _declare_prototypes(lib: Any) -> None:
    lib.mpv_client_api_version.restype = ctypes.c_ulong
    lib.mpv_create.restype = ctypes.c_void_p
    lib.mpv_set_option_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.mpv_set_option_string.restype = ctypes.c_int
    lib.mpv_initialize.argtypes = [ctypes.c_void_p]
    lib.mpv_initialize.restype = ctypes.c_int
    lib.mpv_get_property_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.mpv_get_property_string.restype = ctypes.c_void_p
    lib.mpv_free.argtypes = [ctypes.c_void_p]
    lib.mpv_free.restype = None
    lib.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
    lib.mpv_terminate_destroy.restype = None


def _vo_profiles_for(sys_platform: str) -> dict[str, dict[str, str]]:
    return VO_PROFILE_OPTIONS["win32" if sys_platform == "win32" else "linux"]


def _accepted_vo_profiles(lib: Any, sys_platform: str) -> tuple[str, ...]:
    """Profiles whose options this build accepts, each on a fresh uninitialised handle.

    An invalid choice fails at option-set time, so the in-process MPV() of P2
    never gets an option that leaks a half-created core ([CT] finding 2).
    """
    accepted = []
    for name, options in _vo_profiles_for(sys_platform).items():
        handle = lib.mpv_create()
        if not handle:
            continue
        try:
            ok = all(lib.mpv_set_option_string(handle, key.encode(), value.encode()) >= 0
                     for key, value in options.items())
        finally:
            lib.mpv_terminate_destroy(handle)
        if ok:
            accepted.append(name)
    return tuple(accepted)


def _read_mpv_version(lib: Any) -> str | None:
    """The `mpv-version` property of a headless, initialised handle (C54)."""
    handle = lib.mpv_create()
    if not handle:
        return None
    try:
        for key, value in _VERSION_PROBE_OPTIONS:
            lib.mpv_set_option_string(handle, key.encode(), value.encode())
        if lib.mpv_initialize(handle) < 0:
            return None
        pointer = lib.mpv_get_property_string(handle, b"mpv-version")
        if not pointer:
            return None
        try:
            return ctypes.string_at(pointer).decode("utf-8", "replace")
        finally:
            lib.mpv_free(pointer)
    finally:
        lib.mpv_terminate_destroy(handle)


def probe_libmpv(*, sys_platform: str = sys.platform, env: Mapping[str, str] | None = None,
                 app_dir: Path | None = None, runtime_dir: Path | None = None,
                 find_library: Callable[[str], str | None] = ctypes.util.find_library,
                 cdll: Callable[[str], Any] = ctypes.CDLL,
                 run_ldconfig: Callable[[], str] = read_ldconfig_cache,
                 read_maps: Callable[[], str] | None = None,
                 isfile: Callable[[str], bool] = os.path.isfile,
                 add_dll_directory: Callable[[str], Any] | None = None,
                 system32: Path | None = None) -> LibmpvStatus:
    """Load libmpv and report what it is. ONLY for the `check` subprocess.

    The python-mpv verdict is not part of this result: ``main`` adds it for
    the CLI, and resolve_status takes it from the calling process.
    """
    env = os.environ if env is None else env
    app_dir = PACKAGE_ROOT if app_dir is None else Path(app_dir)
    path, build = _locate_library(sys_platform=sys_platform, env=env, app_dir=app_dir,
                                  runtime_dir=runtime_dir, find_library=find_library,
                                  run_ldconfig=run_ldconfig, isfile=isfile)
    if path is None:
        return _status("libmpv-missing", detail="library not found")
    vulkan_present = True
    if sys_platform == "win32":
        vulkan_present = ((system32 or default_system32(env)) / VULKAN_DLL).is_file()
        if not vulkan_present:
            fallback = find_vulkan_fallback(Path(path).parent, env)
            adder = add_dll_directory or getattr(os, "add_dll_directory", None)
            if fallback is not None and adder is not None:
                _DLL_DIR_HANDLES.append(adder(str(fallback)))
                vulkan_present = True
    try:
        lib = cdll(path)
    except OSError as exc:
        reason = classify_import_error(exc, sys_platform=sys_platform, vulkan_present=vulkan_present)
        return _status(reason, path=path, build=build, detail=f"{type(exc).__name__}: {exc}")
    try:
        _declare_prototypes(lib)
        api = parse_api_version(lib.mpv_client_api_version())
    except AttributeError as exc:
        return _status("libmpv-too-old", path=path, build=build, detail=f"missing symbol: {exc}")
    real_path = path
    if sys_platform != "win32":
        real_path = parse_maps((read_maps or _read_self_maps)()) or path
    fingerprint = library_fingerprint(real_path)
    if api < MIN_API:
        return _status("libmpv-too-old", api_version=api, path=real_path, build=build,
                       fingerprint=fingerprint,
                       detail=f"client API {api[0]}.{api[1]} is older than "
                              f"{MIN_API[0]}.{MIN_API[1]}")
    profiles = _accepted_vo_profiles(lib, sys_platform)
    version_text = _read_mpv_version(lib)
    mpv_version = parse_mpv_version(version_text or "")
    detail = f"{version_text or 'mpv version unknown'}, client API {api[0]}.{api[1]}"
    if mpv_version is not None and mpv_version < TESTED_FLOOR:
        return _status("libmpv-too-old", api_version=api, mpv_version=mpv_version,
                       path=real_path, build=build, fingerprint=fingerprint, detail=detail)
    return _status("ok", api_version=api, mpv_version=mpv_version, path=real_path,
                   vo_profiles_ok=profiles, detail=detail, build=build, fingerprint=fingerprint)


# -- the check subprocess --------------------------------------------------

def status_to_json(status: LibmpvStatus) -> str:
    data = dataclasses.asdict(status)
    data["build"] = dict(status.build)
    return json.dumps(data, ensure_ascii=True, sort_keys=True)


def _pair(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    first, second = value
    return int(first), int(second)


def status_from_json(text: str) -> LibmpvStatus | None:
    """The status printed by `check --json` (last JSON line), None when absent or invalid."""
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            reason = str(data["reason"])
            if reason not in REASONS:
                return None
            return LibmpvStatus(
                ok=bool(data["ok"]) and reason == "ok", reason=reason,
                api_version=_pair(data.get("api_version")),
                mpv_version=_pair(data.get("mpv_version")),
                path=data.get("path"),
                vo_profiles_ok=tuple(str(item) for item in data.get("vo_profiles_ok") or ()),
                detail=str(data.get("detail", "")),
                build={str(k): str(v) for k, v in (data.get("build") or {}).items()},
                fingerprint=data.get("fingerprint"))
        except (KeyError, TypeError, ValueError):
            return None
    return None


def probe_in_subprocess(*, run: Callable[..., Any] = subprocess.run, python: str = sys.executable,
                        timeout: float = PROBE_TIMEOUT_S, runtime_dir: Path | None = None,
                        cwd: Path = PACKAGE_ROOT, sys_platform: str = sys.platform) -> LibmpvStatus:
    """Run `check --json` in a child: a crash or a hang becomes `probe-crashed`."""
    cmd = [python, "-m", "videotranslator.libmpv_runtime", "check", "--json"]
    if runtime_dir is not None:
        cmd += ["--dir", str(runtime_dir)]
    try:
        proc = run(cmd, cwd=str(cwd), capture_output=True, stdin=subprocess.DEVNULL, text=True,
                   encoding="utf-8", errors="replace", timeout=timeout, check=False,
                   **no_window_kwargs(sys_platform))
    except subprocess.TimeoutExpired:
        return _status("probe-crashed", detail=f"libmpv probe timed out after {timeout:.0f} s")
    except OSError as exc:
        return _status("probe-crashed", detail=f"libmpv probe could not start: {exc}")
    status = status_from_json(proc.stdout)
    if status is None or proc.returncode not in (0, 2):
        tail = (proc.stderr or "").strip().splitlines()[-1:]
        detail = f"libmpv probe exit code {proc.returncode}"
        if tail:
            detail += f": {_shorten(tail[0])}"
        return _status("probe-crashed", detail=detail)
    return status


# -- probe cache (config key player_probe, written by the GUI) -------------

def cache_entry(status: LibmpvStatus) -> dict[str, Any] | None:
    """What the GUI stores under `player_probe` (spec 2.5); None when not cacheable."""
    if not library_loaded(status) or status.api_version is None or not status.fingerprint:
        return None
    return {
        "fingerprint": status.fingerprint,
        "ok": True,
        "api": list(status.api_version),
        "mpv_version": list(status.mpv_version) if status.mpv_version else None,
        "vo_profiles_ok": list(status.vo_profiles_ok),
    }


def status_from_cache(quick: LibmpvStatus, cached: Any) -> LibmpvStatus | None:
    """``quick`` completed with a cached probe of the same library file, else None."""
    if not isinstance(cached, Mapping) or cached.get("ok") is not True:
        return None
    if not quick.fingerprint or cached.get("fingerprint") != quick.fingerprint:
        return None
    try:
        api = tuple(int(part) for part in cached["api"])
        raw_version = cached.get("mpv_version")
        mpv_version = tuple(int(part) for part in raw_version) if raw_version else None
        profiles = tuple(str(name) for name in cached.get("vo_profiles_ok") or ())
    except (KeyError, TypeError, ValueError):
        return None
    if len(api) != 2 or (mpv_version is not None and len(mpv_version) != 2):
        return None
    return dataclasses.replace(quick, api_version=api, mpv_version=mpv_version,
                               vo_profiles_ok=profiles, detail="cached probe result")


def resolve_status(*, cached: Any = None, force_probe: bool = False,
                   quick: Callable[[], LibmpvStatus] | None = None,
                   probe: Callable[[], LibmpvStatus] | None = None) -> LibmpvStatus:
    """Worker-thread status for the GUI (plan decision 2). Never loads libmpv here."""
    quick_status = (quick or quick_presence)()
    if not library_loaded(quick_status):
        return quick_status
    if not force_probe:
        hit = status_from_cache(quick_status, cached)
        if hit is not None:
            return hit
    probed = (probe or probe_in_subprocess)()
    if not library_loaded(probed):
        return probed
    # Library facts from the child, python-mpv verdict from this process (a
    # user site created during this run is importable in a fresh child only).
    return dataclasses.replace(probed, ok=quick_status.ok, reason=quick_status.reason,
                               fingerprint=quick_status.fingerprint or probed.fingerprint,
                               build=quick_status.build or probed.build)


# -- import gate (P2 calls load_mpv on its player-init thread) -------------

def prepare_import(env: MutableMapping[str, str], *, sys_platform: str,
                   runtime_dir: Path | None, add_dll_directory: Callable[[str], Any] | None,
                   system32_has_vulkan: bool) -> Callable[[], None]:
    """Windows: PREPEND ``runtime_dir`` to PATH for the import; return a restore callable.

    Prepending (not narrowing) keeps ffmpeg visible to a job that starts at
    the same instant (spec 2.2). The Vulkan fallback dir is added through
    add_dll_directory only when System32 lacks the loader, and its handle is
    kept for the process lifetime. Linux: no-op.
    """
    if sys_platform != "win32" or runtime_dir is None:
        return lambda: None
    old = env.get("PATH")
    env["PATH"] = str(runtime_dir) + (";" + old if old else "")
    if not system32_has_vulkan and add_dll_directory is not None:
        fallback = find_vulkan_fallback(Path(runtime_dir), env)
        if fallback is not None:
            _DLL_DIR_HANDLES.append(add_dll_directory(str(fallback)))

    def restore() -> None:
        if old is None:
            env.pop("PATH", None)
        else:
            env["PATH"] = old

    return restore


def load_mpv(*, importer: Callable[[str], ModuleType] = importlib.import_module,
             sys_platform: str = sys.platform, env: MutableMapping[str, str] | None = None,
             app_dir: Path | None = None, add_dll_directory: Callable[[str], Any] | None = None,
             system32: Path | None = None) -> ModuleType:
    """The only `import mpv` of the code base; cached; raises PlayerUnavailable. Off the Tk thread."""
    global _MPV_MODULE
    with _MPV_LOCK:
        if _MPV_MODULE is not None:
            return _MPV_MODULE
        env = os.environ if env is None else env
        runtime_dir = None
        vulkan_ok = True
        if sys_platform == "win32":
            path, _ = _locate_library(sys_platform=sys_platform, env=env,
                                      app_dir=PACKAGE_ROOT if app_dir is None else Path(app_dir),
                                      runtime_dir=None, find_library=lambda name: None,
                                      run_ldconfig=lambda: "", isfile=os.path.isfile)
            runtime_dir = Path(path).parent if path else None
            vulkan_ok = ((system32 or default_system32(env)) / VULKAN_DLL).is_file()
        restore = prepare_import(env, sys_platform=sys_platform, runtime_dir=runtime_dir,
                                 add_dll_directory=add_dll_directory or getattr(os, "add_dll_directory", None),
                                 system32_has_vulkan=vulkan_ok)
        try:
            module = importer("mpv")
        except Exception as exc:  # python-mpv raises OSError/RuntimeError at import time
            reason = classify_import_error(exc, sys_platform=sys_platform, vulkan_present=vulkan_ok)
            raise PlayerUnavailable(_status(reason, detail=f"{type(exc).__name__}: {exc}")) from exc
        finally:
            restore()
        _MPV_MODULE = module
        return module


# -- command line ----------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m videotranslator.libmpv_runtime",
        description="Probe libmpv for the integrated video player.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="load libmpv in this process and report its status")
    check.add_argument("--dir", help="probe the library in this folder only")
    check.add_argument("--json", action="store_true", help="print the status as one JSON line")
    return parser


def _cmd_check(args: argparse.Namespace, *, sys_platform: str) -> int:
    if sys_platform != "win32":
        # libmpv refuses to create a handle under a non-C LC_NUMERIC.
        locale.setlocale(locale.LC_NUMERIC, "C")
    status = probe_libmpv(sys_platform=sys_platform,
                          runtime_dir=Path(args.dir) if args.dir else None)
    if status.ok and not _module_present("mpv", importlib.util.find_spec):
        status = dataclasses.replace(status, ok=False, reason="python-mpv-missing",
                                     detail=status.detail + "; python-mpv (module mpv) is not importable")
    if args.json:
        print(status_to_json(status))
    else:
        print(f"{status.reason}: {status.detail} [{status.path or 'no library'}]")
    return 0 if status.ok else 2


def main(argv: list[str] | None = None, *, sys_platform: str = sys.platform) -> int:
    """Exit codes: 0 ok, 2 unavailable, 3 unexpected error; never 1."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 3
    try:
        return _cmd_check(args, sys_platform=sys_platform)
    except Exception:
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_libmpv_runtime test_import_hygiene test_ui_i18n_coverage -v`
Expected: all OK. If `test_fingerprint_uses_the_real_path_size_and_mtime` fails on a filesystem without symlinks, that is a real environment limit: report it, do not skip it.

- [ ] **Step 5: Real-library checks on Kali (unpacked libmpv 0.41, no system install)**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
PROBE=/home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI/_dev/research/player-2026-09-25/probe
python3 -m videotranslator.libmpv_runtime check --json; echo "exit=$?"
LD_LIBRARY_PATH="$PROBE/lib" VTAI_LIBMPV_DIR="$PROBE/lib" PYTHONPATH="$PROBE/wheel" python3 -m videotranslator.libmpv_runtime check --json; echo "exit=$?"
LD_LIBRARY_PATH="$PROBE/lib" python3 -m videotranslator.libmpv_runtime check --json --dir "$PROBE/lib"; echo "exit=$?"
```

Expected (spec 9 P1 first acceptance item):
1. `"reason": "libmpv-missing"`, `exit=2` (this machine has no system libmpv).
2. `"ok": true`, `"api_version": [2, 5]`, `"mpv_version": [0, 41]`, `"vo_profiles_ok"` containing `"x11egl"` and `"x11sw"` (and `"x11vk"` for this build), never `"x11glx"`, `exit=0`.
3. The same library facts with `"reason": "python-mpv-missing"`, `exit=2`.

If `mpv_version` is `null` in run 2, claim C54 ("reading `mpv-version` on a vo=null handle") failed on 0.41: stop and report it to the controller with the stderr of the run (the spec fallback changes the version source, which is a design decision). Record the three outputs in the task report.

- [ ] **Step 6: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' videotranslator/libmpv_runtime.py tests/test_libmpv_runtime.py tests/test_import_hygiene.py tests/test_ui_i18n_coverage.py || echo "no long dashes"
git add videotranslator/libmpv_runtime.py tests/test_libmpv_runtime.py tests/test_import_hygiene.py tests/test_ui_i18n_coverage.py
git commit -m "feat(player): detect and probe libmpv without loading it in the app

libmpv_runtime finds the library (ldconfig on Linux, the mpv-runtime
folders on Windows) and probes it only in a child process started with
python -m videotranslator.libmpv_runtime check, so a crashing DLL cannot
take the GUI down. The probe reports the client API, the mpv version and
the VO profiles the build accepts; resolve_status caches it by library
fingerprint. load_mpv is the single guarded import of python-mpv for P2."
```

---
## Task 4: Windows libmpv installer and the `install` command

Review level: full

(Windows-only download, extraction and DLL placement that cannot be run here; checksum and licence-source handling decided by Q1/Q2.)

**Files:**
- Modify: `videotranslator/libmpv_runtime.py` (imports, a new installer section before `# -- command line`, the parser and `main`)
- Create: `tests/test_libmpv_install.py`

**Interfaces:**
- Consumes (Task 3): `LibmpvStatus`, `_status`, `library_loaded`, `format_version`, `read_build_txt`, `probe_in_subprocess`, `_shorten`, `WINDOWS_DLL_TARGET`, `VULKAN_DIR_NAME`, `VULKAN_DLL`; (Task 1) `no_window_kwargs`.
- Produces (all in `videotranslator.libmpv_runtime`):
  - `USER_AGENT = "VideoTranslatorAI-Setup"`, `DOWNLOAD_TIMEOUT_S = 60.0`, `BUILD_FILE = "BUILD.txt"`, `STAGING_DIR_NAME = "_staging"`
  - `@dataclass(frozen=True) class AssetSource(kind, name, licence, urls=(), sha256=None, member="libmpv-2.dll", member_sha256=None, repo=None, asset_pattern=None, max_releases=3, max_bytes=64 << 20)`
  - `WINDOWS_LIBMPV_SOURCES: tuple[AssetSource, ...]` (Q1 order: zhongfly LGPL latest, then pinned shinchiro GPL 20260920), `SEVENZR: AssetSource`, `VULKAN_RUNTIME: AssetSource`
  - `@dataclass(frozen=True) class DownloadCandidate(source, url, sha256, release, asset)`, `class DownloadError(Exception)`
  - `class HttpClient` with `get_json(url)`, `get_text(url)`, `resolve(url) -> str`, `fetch(url, dest, *, max_bytes) -> str` (sha256 hex)
  - `pinned_candidates(source) -> list[DownloadCandidate]`, `github_candidates(source, http, log) -> list[DownloadCandidate]`
  - `sha256_file(path) -> str`, `run_hidden(cmd, *, timeout_s=300.0, run=subprocess.run, sys_platform=sys.platform) -> int`
  - `installed_build_is_current(dest, sources) -> bool`, `write_build_txt(dest, cand, status, *, vulkan_fallback, now) -> None`
  - `install_windows(dest, *, sources=WINDOWS_LIBMPV_SOURCES, sevenzr=SEVENZR, vulkan=VULKAN_RUNTIME, downloader=None, runner=None, probe=None, log=print, now=None) -> LibmpvStatus`
  - CLI: `install --dest DIR` (exit 0 when the library loads, 2 otherwise or off Windows, 3 on an unexpected error)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_libmpv_install.py`:

```python
"""Windows libmpv installer (spec 8.3, Q1, Q2, Q6). Every download, 7zr run and
load check is faked: no network, no Windows, no real DLL."""

import contextlib
import hashlib
import io
import re
import subprocess
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from videotranslator import libmpv_runtime as rt
from videotranslator.libmpv_runtime import AssetSource, DownloadError, LibmpvStatus


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeHttp:
    def __init__(self, files=None, api=None, text=None, redirects=None):
        self.files = dict(files or {})
        self.api = dict(api or {})
        self.text = dict(text or {})
        self.redirects = dict(redirects or {})
        self.fetched = []

    def get_json(self, url):
        if url not in self.api:
            raise OSError(f"HTTP 403 rate limit exceeded: {url}")
        return self.api[url]

    def get_text(self, url):
        if url not in self.text:
            raise OSError(f"HTTP 404: {url}")
        return self.text[url]

    def resolve(self, url):
        if url not in self.redirects:
            raise OSError(f"HTTP 404: {url}")
        return self.redirects[url]

    def fetch(self, url, dest, *, max_bytes):
        self.fetched.append(url)
        if url not in self.files:
            raise OSError(f"HTTP 404: {url}")
        data = self.files[url]
        if len(data) > max_bytes:
            raise DownloadError(f"{url} is larger than {max_bytes} bytes")
        Path(dest).write_bytes(data)
        return _sha(data)


def fake_7zr(cmd):
    """`7zr e -y -o<dir> <archive> <member>`: a good archive is b"7z:" + the member bytes."""
    out_dir = Path(next(part[2:] for part in cmd if part.startswith("-o")))
    archive, member = Path(cmd[-2]), cmd[-1]
    data = archive.read_bytes()
    if not data.startswith(b"7z:"):
        (out_dir / member).write_bytes(b"")  # a failed real extraction can leave a 0-byte file
        return 2
    (out_dir / member).write_bytes(data[3:])
    return 0


def fake_probe(directory):
    """Load check by DLL content: MZgood loads; MZvulkan needs vulkan-fallback; else it crashes."""
    directory = Path(directory)
    data = (directory / "mpv-2.dll").read_bytes()
    loaded = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                          path=str(directory / "mpv-2.dll"), detail="mpv 0.41.0, client API 2.5")
    if data == b"MZgood":
        return loaded
    if data == b"MZvulkan":
        if (directory / "vulkan-fallback" / "vulkan-1.dll").is_file():
            return loaded
        return LibmpvStatus(ok=False, reason="vulkan-loader-missing", detail="WinError 126")
    return LibmpvStatus(ok=False, reason="probe-crashed", detail="exit code 3221225477")


SEVENZR_URL = "https://example.test/7zr.exe"
SEVENZR = AssetSource(kind="pinned", name="7zr-test", licence="LGPL", urls=(SEVENZR_URL,),
                      sha256=_sha(b"MZ7zr"), member="7zr.exe", max_bytes=1 << 20)
VULKAN_MEMBER = "VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll"


def _vulkan_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        bundle.writestr(VULKAN_MEMBER, b"MZvk")
    return buf.getvalue()


VULKAN_ZIP = _vulkan_zip()
VULKAN_URL = "https://example.test/vulkan.zip"
VULKAN = AssetSource(kind="pinned", name="vulkan-test", licence="MIT and Apache-2.0",
                     urls=(VULKAN_URL,), sha256=_sha(VULKAN_ZIP), member=VULKAN_MEMBER,
                     member_sha256=_sha(b"MZvk"), max_bytes=1 << 20)

REPO = "zhongfly/mpv-winbuild"
API_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=3"
GH = AssetSource(kind="github-latest", name="zhongfly-lgpl", licence="LGPL", repo=REPO,
                 asset_pattern=r"mpv-dev-lgpl-x86_64-\d{8}-git-[0-9a-f]+\.7z", max_releases=3,
                 max_bytes=1 << 20)


def _release(tag, date, commit, dll, *, digest=True):
    name = f"mpv-dev-lgpl-x86_64-{date}-git-{commit}.7z"
    archive = b"7z:" + dll
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    asset = {"name": name, "browser_download_url": url}
    if digest:
        asset["digest"] = "sha256:" + _sha(archive)
    decoys = [  # the v3 and the GPL builds of the same release must never match
        {"name": f"mpv-dev-lgpl-x86_64-v3-{date}-git-{commit}.7z",
         "browser_download_url": url + ".v3", "digest": "sha256:" + "0" * 64},
        {"name": f"mpv-dev-x86_64-{date}-git-{commit}.7z",
         "browser_download_url": url + ".gpl", "digest": "sha256:" + "1" * 64},
    ]
    return {"tag_name": tag, "assets": decoys + [asset]}, url, archive, name


def _pinned(name, urls, *, member_sha256=None):
    return AssetSource(kind="pinned", name=name, licence="GPL", urls=tuple(urls),
                       sha256=_sha(b"7z:MZgood"), member_sha256=member_sha256, max_bytes=1 << 20)


class SourceDataTests(unittest.TestCase):
    def test_q1_order_lgpl_latest_first_then_the_pinned_gpl_build(self):
        first, second = rt.WINDOWS_LIBMPV_SOURCES
        self.assertEqual((first.kind, first.name, first.licence, first.repo, first.max_releases),
                         ("github-latest", "zhongfly-lgpl", "LGPL", "zhongfly/mpv-winbuild", 3))
        pattern = re.compile(first.asset_pattern)
        self.assertTrue(pattern.fullmatch("mpv-dev-lgpl-x86_64-20260925-git-2a4eb8067c.7z"))
        self.assertIsNone(pattern.fullmatch("mpv-dev-lgpl-x86_64-v3-20260925-git-2a4eb8067c.7z"))
        self.assertIsNone(pattern.fullmatch("mpv-dev-x86_64-20260925-git-2a4eb8067c.7z"))
        self.assertEqual((second.kind, second.name, second.licence),
                         ("pinned", "shinchiro-gpl-20260920", "GPL"))
        self.assertTrue(second.urls[0].startswith("https://downloads.sourceforge.net/"))
        self.assertTrue(all(url.endswith("/mpv-dev-x86_64-20260920-git-e76a35ec95.7z")
                            for url in second.urls))
        self.assertEqual(second.sha256,
                         "60f9102db46aea8cef9bfb4345ee6a106f34fdbd1df9587e38f0660688039341")
        self.assertEqual(second.member_sha256,
                         "63e1fbb4ee890d153a9f5086410157174ee18582846bf35f6cc4e5d08d4bb662")

    def test_pinned_tools(self):
        self.assertEqual(rt.SEVENZR.urls,
                         ("https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe",))
        self.assertEqual(rt.SEVENZR.sha256,
                         "ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d")
        self.assertEqual(rt.VULKAN_RUNTIME.member,
                         "VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll")
        self.assertEqual(rt.VULKAN_RUNTIME.sha256,
                         "a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83")
        self.assertEqual(rt.VULKAN_RUNTIME.member_sha256,
                         "cd862090370454630b31b174e3d4eb474fda38ea034998d1fe1767b0c99a8696")


class InstallWindowsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self._tmp.name) / "mpv-runtime"
        self.log = []

    def tearDown(self):
        self._tmp.cleanup()

    def _install(self, sources, http, probe=fake_probe):
        return rt.install_windows(
            self.dest, sources=sources, sevenzr=SEVENZR, vulkan=VULKAN, downloader=http,
            runner=fake_7zr, probe=probe, log=self.log.append,
            now=lambda: datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc))

    def _leftovers(self):
        return sorted(p.name for p in self.dest.rglob("*")
                      if p.name.endswith(".part") or p.name in ("libmpv-2.dll", "_staging"))

    def test_the_newest_github_release_with_a_digest_is_installed(self):
        new, new_url, new_archive, new_name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood")
        old, old_url, old_archive, _ = _release("2026-09-24-bbbbbbb", "20260924", "bbbbbbb", b"MZgood")
        licence_url = "https://raw.githubusercontent.com/mpv-player/mpv/aaaaaaa/LICENSE.LGPL"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", new_url: new_archive, old_url: old_archive},
                        api={API_URL: [new, old]}, text={licence_url: "LGPL TEXT"})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, new_url])
        self.assertEqual((self.dest / "mpv-2.dll").read_bytes(), b"MZgood")
        build = rt.read_build_txt(self.dest)
        self.assertEqual(build["source"], "zhongfly-lgpl")
        self.assertEqual(build["licence"], "LGPL")
        self.assertEqual(build["release"], "2026-09-25-aaaaaaa")
        self.assertEqual(build["archive"], new_name)
        self.assertEqual(build["mpv_commit"], "aaaaaaa")
        self.assertEqual(build["mpv_version"], "0.41")
        self.assertEqual(build["dll_sha256"], _sha(b"MZgood"))
        self.assertEqual(build["vulkan_fallback"], "no")
        self.assertEqual(build["installed"], "2026-09-25T12:00:00Z")
        self.assertEqual((self.dest / "LICENSE.LGPL").read_text(encoding="utf-8"), "LGPL TEXT")
        self.assertEqual(self._leftovers(), [])

    def test_a_failed_load_check_falls_back_to_the_next_release(self):
        bad, bad_url, bad_archive, bad_name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZcrash")
        good, good_url, good_archive, _ = _release("2026-09-24-bbbbbbb", "20260924", "bbbbbbb", b"MZgood")
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", bad_url: bad_archive, good_url: good_archive},
                        api={API_URL: [bad, good]})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(rt.read_build_txt(self.dest)["release"], "2026-09-24-bbbbbbb")
        self.assertTrue(any(bad_name in line and "probe-crashed" in line for line in self.log))
        self.assertEqual(self._leftovers(), [])

    def test_api_failure_uses_the_latest_redirect_and_sha256_txt(self):
        _, url, archive, name = _release("2026-09-24-2a4eb80", "20260924", "2a4eb80", b"MZgood")
        tag_url = f"https://github.com/{REPO}/releases/tag/2026-09-24-2a4eb80"
        sums_url = f"https://github.com/{REPO}/releases/download/2026-09-24-2a4eb80/sha256.txt"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive},
                        redirects={f"https://github.com/{REPO}/releases/latest": tag_url},
                        text={sums_url: f"{'0' * 64}  mpv-dev-x86_64-20260924-git-2a4eb80.7z\n"
                                        f"{_sha(archive)}  {name}\n"})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, url])

    def test_a_missing_digest_is_looked_up_in_sha256_txt(self):
        rel, url, archive, name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood",
                                           digest=False)
        sums_url = f"https://github.com/{REPO}/releases/download/2026-09-25-aaaaaaa/sha256.txt"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive}, api={API_URL: [rel]},
                        text={sums_url: f"{_sha(archive)} *{name}\n"})
        self.assertTrue(self._install([GH], http).ok)

    def test_an_asset_without_any_checksum_is_never_downloaded(self):
        rel, url, archive, _ = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood",
                                        digest=False)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive}, api={API_URL: [rel]})
        status = self._install([GH], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertNotIn(url, http.fetched)

    def test_a_pinned_sha_mismatch_is_rejected_and_the_next_mirror_used(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z", "https://mirror2.test/a.7z"])
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZevil",
                               "https://mirror2.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, "https://mirror1.test/a.7z",
                                        "https://mirror2.test/a.7z"])
        self.assertEqual(rt.read_build_txt(self.dest)["url"], "https://mirror2.test/a.7z")
        self.assertEqual(self._leftovers(), [])

    def test_a_member_sha_mismatch_is_rejected(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z"], member_sha256="f" * 64)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("SHA256 mismatch", status.detail)
        self.assertFalse((self.dest / "mpv-2.dll").exists())

    def test_the_size_cap_is_enforced(self):
        source = AssetSource(kind="pinned", name="big", licence="GPL", urls=("https://big.test/a.7z",),
                             sha256=_sha(b"7z:MZgood"), max_bytes=4)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://big.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("larger than 4 bytes", status.detail)
        self.assertEqual(self._leftovers(), [])

    def test_the_vulkan_loader_is_fetched_when_missing(self):
        source = AssetSource(kind="pinned", name="needs-vulkan", licence="GPL",
                             urls=("https://v.test/a.7z",), sha256=_sha(b"7z:MZvulkan"),
                             max_bytes=1 << 20)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://v.test/a.7z": b"7z:MZvulkan",
                               VULKAN_URL: VULKAN_ZIP})
        status = self._install([source], http)
        self.assertTrue(status.ok)
        self.assertIn(VULKAN_URL, http.fetched)
        self.assertEqual((self.dest / "vulkan-fallback" / "vulkan-1.dll").read_bytes(), b"MZvk")
        self.assertEqual(rt.read_build_txt(self.dest)["vulkan_fallback"], "yes")
        self.assertEqual(self._leftovers(), [])

    def test_a_second_run_skips_every_download(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z"])
        first = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZgood"})
        self.assertTrue(self._install([source], first).ok)
        second = FakeHttp()
        status = self._install([source], second)
        self.assertTrue(status.ok)
        self.assertEqual(second.fetched, [])
        self.assertTrue(any("skipping the download" in line for line in self.log))

    def test_a_build_from_a_source_no_longer_listed_is_replaced(self):
        old = _pinned("old-source", ["https://old.test/a.7z"])
        new = _pinned("new-source", ["https://new.test/a.7z"])
        self.assertTrue(self._install([old], FakeHttp(files={
            SEVENZR_URL: b"MZ7zr", "https://old.test/a.7z": b"7z:MZgood"})).ok)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://new.test/a.7z": b"7z:MZgood"})
        self.assertTrue(self._install([new], http).ok)
        self.assertIn("https://new.test/a.7z", http.fetched)
        self.assertEqual(rt.read_build_txt(self.dest)["source"], "new-source")

    def test_a_failed_extraction_leaves_no_zero_byte_dll(self):
        source = AssetSource(kind="pinned", name="broken", licence="GPL", urls=("https://b.test/a.7z",),
                             sha256=_sha(b"not an archive"), max_bytes=1 << 20)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://b.test/a.7z": b"not an archive"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("7zr could not extract", status.detail)
        self.assertEqual(self._leftovers(), [])
        self.assertFalse((self.dest / "mpv-2.dll").exists())

    def test_every_source_failing_reports_libmpv_missing(self):
        status = self._install([_pinned("a", ["https://a.test/a.7z"]),
                                _pinned("b", ["https://b.test/b.7z"])],
                               FakeHttp(files={SEVENZR_URL: b"MZ7zr"}))
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("a.7z", status.detail)
        self.assertIn("b.7z", status.detail)

    def test_a_7zr_download_failure_stops_the_install(self):
        http = FakeHttp()
        status = self._install([_pinned("a", ["https://a.test/a.7z"])], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("7zr.exe", status.detail)
        self.assertEqual(http.fetched, [SEVENZR_URL])
        self.assertFalse((self.dest / "_staging").exists())


class _FakeResponse:
    def __init__(self, data, *, url="https://final.test/x", ctype="application/octet-stream"):
        self._buf = io.BytesIO(data)
        self._url = url
        self.headers = {"Content-Type": ctype}

    def read(self, n=-1):
        return self._buf.read(n)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class HttpClientTests(unittest.TestCase):
    def _client(self, response, seen):
        def opener(request, timeout):
            seen.append((request.full_url, request.get_header("User-agent"), timeout))
            return response

        return rt.HttpClient(opener=opener, timeout=7, chunk=4)

    def test_fetch_streams_hashes_and_sends_the_installer_agent(self):
        seen = []
        client = self._client(_FakeResponse(b"0123456789"), seen)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "f.part"
            self.assertEqual(client.fetch("https://x.test/f", target, max_bytes=100),
                             _sha(b"0123456789"))
            self.assertEqual(target.read_bytes(), b"0123456789")
        self.assertEqual(seen, [("https://x.test/f", "VideoTranslatorAI-Setup", 7)])

    def test_fetch_enforces_the_cap_and_refuses_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DownloadError):
                self._client(_FakeResponse(b"0123456789"), []).fetch(
                    "https://x.test/f", Path(tmp) / "a", max_bytes=5)
            with self.assertRaises(DownloadError):
                self._client(_FakeResponse(b"<html>", ctype="text/html; charset=utf-8"), []).fetch(
                    "https://x.test/f", Path(tmp) / "b", max_bytes=100)

    def test_json_text_and_redirect(self):
        self.assertEqual(self._client(_FakeResponse(b'[{"tag_name": "t"}]'), []).get_json(
            "https://api.test/r"), [{"tag_name": "t"}])
        self.assertEqual(self._client(_FakeResponse(b"abc"), []).get_text("https://x.test/t"), "abc")
        self.assertEqual(self._client(_FakeResponse(
            b"", url="https://github.com/r/releases/tag/v1"), []).resolve("https://x.test/latest"),
            "https://github.com/r/releases/tag/v1")


class RunHiddenTests(unittest.TestCase):
    def test_windows_tools_run_without_a_console(self):
        seen = {}

        def run(cmd, **kwargs):
            seen["cmd"], seen["kwargs"] = cmd, kwargs
            return subprocess.CompletedProcess(cmd, 0)

        self.assertEqual(rt.run_hidden(["7zr.exe", "e"], run=run, sys_platform="win32"), 0)
        self.assertEqual(seen["kwargs"]["creationflags"], 0x08000000)
        self.assertIs(seen["kwargs"]["stdin"], subprocess.DEVNULL)

    def test_a_timeout_or_a_start_failure_is_minus_one(self):
        def slow(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 1)

        def missing(cmd, **kwargs):
            raise OSError("no 7zr")

        self.assertEqual(rt.run_hidden(["7zr.exe"], run=slow), -1)
        self.assertEqual(rt.run_hidden(["7zr.exe"], run=missing), -1)


class InstallCommandTests(unittest.TestCase):
    def test_install_is_windows_only(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="linux"), 2)

    def test_install_exit_codes(self):
        cases = ((LibmpvStatus(ok=True, reason="ok", path="p"), 0),
                 (LibmpvStatus(ok=False, reason="python-mpv-missing", path="p"), 0),
                 (LibmpvStatus(ok=False, reason="libmpv-missing"), 2))
        with contextlib.redirect_stdout(io.StringIO()):
            for status, code in cases:
                with self.subTest(reason=status.reason), \
                        mock.patch.object(rt, "install_windows", return_value=status):
                    self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="win32"), code)
            with mock.patch.object(rt, "install_windows", side_effect=RuntimeError("boom")), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="win32"), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_libmpv_install -v`
Expected: ERROR `ImportError: cannot import name 'AssetSource'`.

- [ ] **Step 3: Extend the imports of `libmpv_runtime.py`**

Add to the import block: `import contextlib`, `import hashlib`, `import urllib.request`, `import zipfile`, `from datetime import datetime, timezone`, and extend `from collections.abc import Callable, Mapping, MutableMapping` with `Sequence`.

- [ ] **Step 4: Add the installer section**

Insert this section in `videotranslator/libmpv_runtime.py` right before the `# -- command line` comment:

```python
# -- Windows installer (spec 8.3; setup_windows.bat and the GUI per-user install) --

USER_AGENT = "VideoTranslatorAI-Setup"   # SourceForge serves HTML to browser-like agents
DOWNLOAD_TIMEOUT_S = 60.0
BUILD_FILE = "BUILD.txt"
STAGING_DIR_NAME = "_staging"
LICENCE_URL = "https://raw.githubusercontent.com/mpv-player/mpv/{ref}/LICENSE.{flavour}"


@dataclass(frozen=True)
class AssetSource:
    kind: str                            # "github-latest" | "pinned"
    name: str
    licence: str
    urls: tuple[str, ...] = ()           # pinned: mirrors in order
    sha256: str | None = None            # pinned: the archive
    member: str = "libmpv-2.dll"
    member_sha256: str | None = None     # pinned: the extracted file
    repo: str | None = None              # github-latest: "owner/name"
    asset_pattern: str | None = None     # github-latest: full-match regex on asset names
    max_releases: int = 3                # github-latest: newest N tried in order
    max_bytes: int = 64 << 20


# Operator decision Q1: the zhongfly LGPL build first (newest 3 daily
# releases, each verified by its GitHub digest), the pinned shinchiro GPL
# snapshot as the reproducible fallback. A licence choice changes this data,
# not the code. Both are mpv master snapshots: BUILD.txt records the commit.
WINDOWS_LIBMPV_SOURCES: tuple[AssetSource, ...] = (
    AssetSource(kind="github-latest", name="zhongfly-lgpl", licence="LGPL",
                repo="zhongfly/mpv-winbuild",
                asset_pattern=r"mpv-dev-lgpl-x86_64-\d{8}-git-[0-9a-f]+\.7z",
                max_releases=3),
    AssetSource(kind="pinned", name="shinchiro-gpl-20260920", licence="GPL",
                urls=("https://downloads.sourceforge.net/project/mpv-player-windows/libmpv/"
                      "mpv-dev-x86_64-20260920-git-e76a35ec95.7z",
                      "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/"
                      "20260920/mpv-dev-x86_64-20260920-git-e76a35ec95.7z"),
                sha256="60f9102db46aea8cef9bfb4345ee6a106f34fdbd1df9587e38f0660688039341",
                member_sha256="63e1fbb4ee890d153a9f5086410157174ee18582846bf35f6cc4e5d08d4bb662"),
)
# py7zr cannot decode the BCJ2 filter of both archives ([06] 2): 7zr.exe does.
SEVENZR = AssetSource(kind="pinned", name="7zr-26.03", licence="LGPL",
                      urls=("https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe",),
                      sha256="ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d",
                      member="7zr.exe", max_bytes=4 << 20)
# Q2: fetched only when the load check reports a missing vulkan-1.dll.
VULKAN_RUNTIME = AssetSource(
    kind="pinned", name="vulkan-runtime-1.4.357.0", licence="MIT and Apache-2.0",
    urls=("https://sdk.lunarg.com/sdk/download/1.4.357.0/windows/vulkan-runtime-components.zip",),
    sha256="a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83",
    member="VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll",
    member_sha256="cd862090370454630b31b174e3d4eb474fda38ea034998d1fe1767b0c99a8696")

_SUMS_LINE_RE = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(\S+)\s*$")
_COMMIT_RE = re.compile(r"-git-([0-9a-f]{7,40})\.7z$")


@dataclass(frozen=True)
class DownloadCandidate:
    source: AssetSource
    url: str
    sha256: str
    release: str
    asset: str


class DownloadError(Exception):
    """A download, a checksum or an extraction failed; the next candidate is tried."""


class HttpClient:
    """urllib with the installer's user agent, a timeout and chunked, hashed reads."""

    def __init__(self, *, opener: Callable[..., Any] = urllib.request.urlopen,
                 timeout: float = DOWNLOAD_TIMEOUT_S, chunk: int = 1 << 16) -> None:
        self._opener = opener
        self._timeout = timeout
        self._chunk = chunk

    def _open(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        return self._opener(request, timeout=self._timeout)

    def get_json(self, url: str) -> Any:
        with self._open(url) as response:
            return json.loads(response.read(4 << 20).decode("utf-8"))

    def get_text(self, url: str) -> str:
        with self._open(url) as response:
            return response.read(1 << 20).decode("utf-8", "replace")

    def resolve(self, url: str) -> str:
        """The final URL after redirects (GitHub /releases/latest -> /releases/tag/<tag>)."""
        with self._open(url) as response:
            return response.geturl()

    def fetch(self, url: str, dest: Path, *, max_bytes: int) -> str:
        """Stream ``url`` into ``dest``; return its SHA256 hex digest."""
        digest = hashlib.sha256()
        size = 0
        with self._open(url) as response:
            headers = getattr(response, "headers", None) or {}
            if str(headers.get("Content-Type", "")).lower().startswith("text/html"):
                raise DownloadError(f"{url} returned an HTML page instead of a file")
            with open(dest, "wb") as out:
                while True:
                    block = response.read(self._chunk)
                    if not block:
                        break
                    size += len(block)
                    if size > max_bytes:
                        raise DownloadError(f"{url} is larger than {max_bytes} bytes")
                    digest.update(block)
                    out.write(block)
        return digest.hexdigest()


def pinned_candidates(source: AssetSource) -> list[DownloadCandidate]:
    if not source.sha256:
        return []   # never install an unverified pinned file
    return [DownloadCandidate(source, url, source.sha256.lower(), source.name,
                              url.rstrip("/").rsplit("/", 1)[-1]) for url in source.urls]


def _release_sums(http: Any, repo: str, tag: str) -> dict[str, str]:
    text = http.get_text(f"https://github.com/{repo}/releases/download/{tag}/sha256.txt")
    sums: dict[str, str] = {}
    for line in text.splitlines():
        match = _SUMS_LINE_RE.match(line.strip())
        if match:
            sums[match.group(2)] = match.group(1).lower()
    return sums


def github_candidates(source: AssetSource, http: Any,
                      log: Callable[[str], None]) -> list[DownloadCandidate]:
    """Newest-first candidates of a github-latest source, each with a SHA256 to verify.

    Primary: the releases API and each asset's `digest`. When the API fails
    (60 requests per hour per IP): the /releases/latest redirect and that
    release's sha256.txt. An asset without a checksum is skipped. The digest
    comes from the same origin as the file: it guards against transport
    errors, not against a compromised upstream (spec 8.3, C46).
    """
    pattern = re.compile(source.asset_pattern or r"(?!)")
    base = f"https://github.com/{source.repo}/releases/download"
    try:
        releases = http.get_json(
            f"https://api.github.com/repos/{source.repo}/releases?per_page={source.max_releases}")
    except (OSError, ValueError) as exc:
        log(f"[!] GitHub API unavailable for {source.repo} ({exc}): using the latest release page")
        releases = None
    candidates: list[DownloadCandidate] = []
    if isinstance(releases, list):
        for release in releases[: source.max_releases]:
            tag = str(release.get("tag_name", ""))
            for asset in release.get("assets") or []:
                name = str(asset.get("name", ""))
                if not pattern.fullmatch(name):
                    continue
                digest = str(asset.get("digest") or "")
                sha = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None
                if sha is None:
                    try:
                        sha = _release_sums(http, source.repo, tag).get(name)
                    except (OSError, ValueError):
                        sha = None
                if not sha:
                    log(f"[!] {name}: no published checksum, skipped")
                    continue
                url = str(asset.get("browser_download_url") or f"{base}/{tag}/{name}")
                candidates.append(DownloadCandidate(source, url, sha, tag, name))
        return candidates
    try:
        tag = http.resolve(f"https://github.com/{source.repo}/releases/latest").rstrip("/").rsplit("/", 1)[-1]
        sums = _release_sums(http, source.repo, tag)
    except (OSError, ValueError) as exc:
        log(f"[!] Cannot resolve the latest {source.repo} release: {exc}")
        return []
    for name, sha in sorted(sums.items()):
        if pattern.fullmatch(name):
            candidates.append(DownloadCandidate(source, f"{base}/{tag}/{name}", sha, tag, name))
    return candidates


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_hidden(cmd: Sequence[str], *, timeout_s: float = 300.0,
               run: Callable[..., Any] = subprocess.run, sys_platform: str = sys.platform) -> int:
    """Run a console tool (7zr.exe) with no window and no stdin; its exit code, -1 on failure."""
    try:
        proc = run([str(part) for part in cmd], capture_output=True, stdin=subprocess.DEVNULL,
                   timeout=timeout_s, check=False, **no_window_kwargs(sys_platform))
    except (OSError, subprocess.SubprocessError):
        return -1
    return int(proc.returncode)


def _fetch_verified(http: Any, url: str, target: Path, sha256: str, max_bytes: int) -> None:
    """Download to ``target.part``, check the hash, then rename; never leaves a .part behind."""
    part = target.with_name(target.name + ".part")
    try:
        got = http.fetch(url, part, max_bytes=max_bytes)
        if got.lower() != sha256.lower():
            raise DownloadError(f"SHA256 mismatch for {url}")
        os.replace(part, target)
    finally:
        with contextlib.suppress(OSError):
            part.unlink()


def _fetch_pinned(source: AssetSource, target: Path, http: Any, log: Callable[[str], None]) -> Path:
    errors = []
    for url in source.urls:
        try:
            _fetch_verified(http, url, target, source.sha256 or "", source.max_bytes)
            return target
        except (OSError, ValueError, DownloadError) as exc:
            log(f"[!] {source.name}: {url} failed: {exc}")
            errors.append(str(exc))
    raise DownloadError(f"{source.name}: " + "; ".join(errors or ["no URL"]))


def _extract_member(tool: Path, archive: Path, member: str, work: Path,
                    runner: Callable[[Sequence[str]], int]) -> Path:
    code = runner([str(tool), "e", "-y", f"-o{work}", str(archive), member])
    out = work / Path(member).name
    if code != 0 or not out.is_file() or out.stat().st_size == 0:
        with contextlib.suppress(OSError):
            out.unlink()   # a failed extraction can leave a 0-byte file ([06] 2)
        raise DownloadError(f"7zr could not extract {member} (exit code {code})")
    return out


def _fetch_vulkan(vulkan: AssetSource, target_dir: Path, work: Path, http: Any,
                  log: Callable[[str], None]) -> None:
    archive = _fetch_pinned(vulkan, work / "vulkan-runtime.zip", http, log)
    target_dir.mkdir(parents=True, exist_ok=True)
    part = target_dir / (VULKAN_DLL + ".part")
    try:
        with zipfile.ZipFile(archive) as bundle, bundle.open(vulkan.member) as src, \
                open(part, "wb") as dst:
            shutil.copyfileobj(src, dst)
        if vulkan.member_sha256 and sha256_file(part) != vulkan.member_sha256:
            raise DownloadError("vulkan-1.dll SHA256 mismatch")
        os.replace(part, target_dir / VULKAN_DLL)
    except (KeyError, zipfile.BadZipFile) as exc:
        raise DownloadError(f"Vulkan runtime archive: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            part.unlink()
        with contextlib.suppress(OSError):
            archive.unlink()


def _seed_vulkan(dest: Path, work: Path, vulkan: AssetSource) -> None:
    """Reuse a verified vulkan-1.dll of a previous install instead of downloading it again."""
    existing = dest / VULKAN_DIR_NAME / VULKAN_DLL
    if not existing.is_file():
        return
    if vulkan.member_sha256 and sha256_file(existing) != vulkan.member_sha256:
        return
    (work / VULKAN_DIR_NAME).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(existing, work / VULKAN_DIR_NAME / VULKAN_DLL)


def _clean_work(work: Path, keep: set[str]) -> None:
    for entry in work.iterdir():
        if entry.name in keep:
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                entry.unlink()


def _try_candidate(cand: DownloadCandidate, work: Path, tool: Path, http: Any,
                   runner: Callable[[Sequence[str]], int], check: Callable[[Path], LibmpvStatus],
                   vulkan: AssetSource, dest: Path, log: Callable[[str], None]) -> LibmpvStatus:
    archive = work / cand.asset
    _fetch_verified(http, cand.url, archive, cand.sha256, cand.source.max_bytes)
    try:
        dll = _extract_member(tool, archive, cand.source.member, work, runner)
    finally:
        with contextlib.suppress(OSError):
            archive.unlink()
    with open(dll, "rb") as handle:
        if handle.read(2) != b"MZ":
            raise DownloadError(f"{cand.source.member} is not a Windows DLL")
    if cand.source.member_sha256 and sha256_file(dll) != cand.source.member_sha256:
        raise DownloadError(f"{cand.source.member} SHA256 mismatch")
    os.replace(dll, work / WINDOWS_DLL_TARGET)
    _seed_vulkan(dest, work, vulkan)
    # The load check runs in a child process: a crashing DLL cannot kill the installer.
    status = check(work)
    if status.reason == "vulkan-loader-missing" and not (work / VULKAN_DIR_NAME / VULKAN_DLL).is_file():
        log("[*] vulkan-1.dll is missing on this system: downloading the Vulkan runtime ...")
        _fetch_vulkan(vulkan, work / VULKAN_DIR_NAME, work, http, log)
        status = check(work)
    return status


def _promote(work: Path, dest: Path) -> bool:
    """Move the checked files from the staging folder (same volume) into ``dest``."""
    vulkan_src = work / VULKAN_DIR_NAME / VULKAN_DLL
    if vulkan_src.is_file():
        (dest / VULKAN_DIR_NAME).mkdir(parents=True, exist_ok=True)
        os.replace(vulkan_src, dest / VULKAN_DIR_NAME / VULKAN_DLL)
    os.replace(work / WINDOWS_DLL_TARGET, dest / WINDOWS_DLL_TARGET)
    return (dest / VULKAN_DIR_NAME / VULKAN_DLL).is_file()


def write_build_txt(dest: Path, cand: DownloadCandidate, status: LibmpvStatus, *,
                    vulkan_fallback: bool, now: datetime) -> None:
    """Record what this user received (source, flavour, mpv commit, hashes) next to the DLL."""
    match = _COMMIT_RE.search(cand.asset)
    lines = [
        "# Written by: python -m videotranslator.libmpv_runtime install",
        f"source={cand.source.name}",
        f"licence={cand.source.licence}",
        f"url={cand.url}",
        f"release={cand.release}",
        f"archive={cand.asset}",
        f"archive_sha256={cand.sha256}",
        f"dll_sha256={sha256_file(dest / WINDOWS_DLL_TARGET)}",
        f"mpv_commit={match.group(1) if match else 'unknown'}",
        f"mpv_version={format_version(status)}",
        f"vulkan_fallback={'yes' if vulkan_fallback else 'no'}",
        f"installed={now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]
    part = dest / (BUILD_FILE + ".part")
    part.write_text("\n".join(lines) + "\n", encoding="ascii", errors="replace")
    os.replace(part, dest / BUILD_FILE)


def _fetch_licence(dest: Path, cand: DownloadCandidate, http: Any, log: Callable[[str], None]) -> None:
    flavour = "LGPL" if cand.source.licence.upper().startswith("LGPL") else "GPL"
    match = _COMMIT_RE.search(cand.asset)
    for ref in ([match.group(1)] if match else []) + ["master"]:
        try:
            text = http.get_text(LICENCE_URL.format(ref=ref, flavour=flavour))
        except (OSError, ValueError):
            continue
        if text.strip():
            (dest / f"LICENSE.{flavour}").write_text(text, encoding="utf-8")
            return
    log(f"[!] Could not fetch LICENSE.{flavour}; see "
        "https://github.com/mpv-player/mpv/blob/master/Copyright")


def installed_build_is_current(dest: Path, sources: Sequence[AssetSource]) -> bool:
    """True when BUILD.txt names a listed source and the DLL hash matches (Repair skips the download)."""
    build = read_build_txt(dest)
    dll = Path(dest) / WINDOWS_DLL_TARGET
    if not build or not dll.is_file():
        return False
    if build.get("source") not in {source.name for source in sources}:
        return False
    return sha256_file(dll) == build.get("dll_sha256", "").lower()


def install_windows(dest: Path, *, sources: Sequence[AssetSource] = WINDOWS_LIBMPV_SOURCES,
                    sevenzr: AssetSource = SEVENZR, vulkan: AssetSource = VULKAN_RUNTIME,
                    downloader: Any = None, runner: Callable[[Sequence[str]], int] | None = None,
                    probe: Callable[[Path], LibmpvStatus] | None = None,
                    log: Callable[[str], None] = print,
                    now: Callable[[], datetime] | None = None) -> LibmpvStatus:
    """Download, verify, extract, load-check and install libmpv into ``dest`` (spec 8.3).

    Every candidate is load-checked in a child process inside a staging
    folder before it replaces anything in ``dest``. Idempotent: a current
    BUILD.txt skips every download. Returns the status of ``dest``.
    """
    http = downloader or HttpClient()
    runner = runner or run_hidden
    check = probe or (lambda directory: probe_in_subprocess(runtime_dir=directory))
    clock = now or (lambda: datetime.now(timezone.utc))
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if installed_build_is_current(dest, sources):
        log(f"[+] libmpv already installed ({read_build_txt(dest).get('source')}), "
            "skipping the download.")
        return check(dest)
    work = dest / STAGING_DIR_NAME
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    failures: list[str] = []
    try:
        try:
            log("[*] Downloading 7zr.exe (7-Zip extractor, used only during the install) ...")
            tool = _fetch_pinned(sevenzr, work / "7zr.exe", http, log)
        except DownloadError as exc:
            return _status("libmpv-missing", detail=f"7zr.exe could not be downloaded: {exc}")
        for source in sources:
            candidates = (github_candidates(source, http, log) if source.kind == "github-latest"
                          else pinned_candidates(source))
            for cand in candidates:
                log(f"[*] Downloading libmpv ({source.name}, {source.licence} build): {cand.asset} ...")
                try:
                    status = _try_candidate(cand, work, tool, http, runner, check, vulkan, dest, log)
                except (OSError, ValueError, DownloadError) as exc:
                    failures.append(f"{cand.asset}: {exc}")
                    log(f"[!] {cand.asset}: {exc}")
                    _clean_work(work, keep={"7zr.exe", VULKAN_DIR_NAME})
                    continue
                if not library_loaded(status):
                    failures.append(f"{cand.asset}: {status.reason} ({status.detail})")
                    log(f"[!] {cand.asset} failed the load check: {status.reason}")
                    _clean_work(work, keep={"7zr.exe", VULKAN_DIR_NAME})
                    continue
                try:
                    vulkan_used = _promote(work, dest)
                except OSError as exc:
                    return _status("libmpv-load-failed", detail=(
                        f"could not replace {WINDOWS_DLL_TARGET} ({exc}): close VideoTranslatorAI "
                        "and run the installer again"))
                write_build_txt(dest, cand, status, vulkan_fallback=vulkan_used, now=clock())
                _fetch_licence(dest, cand, http, log)
                log(f"[+] libmpv installed in {dest}")
                return check(dest)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return _status("libmpv-missing", detail=_shorten(
        "no libmpv build could be installed: " + "; ".join(failures or ["no candidate"]), 500))
```

- [ ] **Step 5: Add the `install` command**

In `_build_parser`, change the description to `"Probe libmpv for the integrated video player, or install it on Windows."` and add after the `check` subparser:

```python
    install = sub.add_parser("install", help="Windows: download, verify and install libmpv")
    install.add_argument("--dest", required=True, help="target folder (the mpv-runtime directory)")
```

Add after `_cmd_check`:

```python
def _cmd_install(args: argparse.Namespace, *, sys_platform: str) -> int:
    if sys_platform != "win32":
        print("[!] install is for Windows only: on Linux install libmpv with the package manager.")
        return 2
    status = install_windows(Path(args.dest))
    if library_loaded(status):
        print(f"[+] libmpv ready: {status.path} ({status.detail})")
        return 0
    print(f"[!] libmpv not installed: {status.reason} ({status.detail})")
    return 2
```

In `main`, replace `return _cmd_check(args, sys_platform=sys_platform)` with:

```python
        if args.command == "install":
            return _cmd_install(args, sys_platform=sys_platform)
        return _cmd_check(args, sys_platform=sys_platform)
```

- [ ] **Step 6: Run the tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_libmpv_install test_libmpv_runtime -v`
Expected: all OK.

- [ ] **Step 7: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' videotranslator/libmpv_runtime.py tests/test_libmpv_install.py || echo "no long dashes"
git add videotranslator/libmpv_runtime.py tests/test_libmpv_install.py
git commit -m "feat(player): install libmpv on Windows from verified third-party builds

python -m videotranslator.libmpv_runtime install --dest DIR downloads the
zhongfly LGPL build (newest 3 releases, GitHub digest or sha256.txt) and
falls back to the pinned shinchiro GPL snapshot (operator decision Q1). It
extracts with a pinned 7zr.exe, load-checks each candidate in a child
process, fetches the Khronos Vulkan loader only when it is missing (Q2),
and writes BUILD.txt with the source, flavour, hashes and mpv commit. A
current BUILD.txt skips every download on Repair."
```

---
## Task 5: Linux package plans and the component installer

Review level: full

(Worker threads, subprocess lifetime with a watchdog, privilege escalation through pkexec, and the import-path refresh that decides "ready without restart".)

**Files:**
- Create: `videotranslator/system_packages.py`
- Create: `tests/test_system_packages.py`
- Modify: `tests/test_import_hygiene.py` (add the module)

**Interfaces:**
- Consumes (Task 1): `no_window_kwargs`; (Task 3) `libmpv_runtime.LibmpvStatus`, `library_loaded`, `offers_install`, `per_user_runtime_dir`, `windows_download_mb`, `PYTHON_MPV_REQUIREMENT`; existing `subprocess_utils.command_for_log`, `normalize_command`, `text_subprocess_kwargs`.
- Produces (all in `videotranslator.system_packages`):
  - `MANAGERS = ("apt-get", "dnf", "pacman", "zypper")`, `GENERIC_PACKAGE_HINT = "libmpv2 / mpv-libs / mpv"`, `INSTALL_TIMEOUT_S = 900.0`
  - `detect_manager(which=shutil.which) -> str | None`
  - `apt_cache_has(package, *, run=subprocess.run) -> bool`
  - `libmpv_packages(manager, *, apt_has) -> tuple[str, ...]`
  - `privilege_prefixes(which=shutil.which, *, is_root=False) -> list[list[str]]` (`[["pkexec"], ["sudo", "-n"]]`, never plain `sudo`; `[[]]` as root)
  - `build_install_plan(manager, packages, prefix) -> list[list[str]]`
  - `manual_command(manager, packages) -> str`
  - `run_streaming(cmd, *, log, timeout_s=INSTALL_TIMEOUT_S, popen=subprocess.Popen, sys_platform=sys.platform) -> int`
  - `run_plan(plan, *, runner, log) -> bool`
  - `pip_install_command(python, packages) -> list[str]`
  - `refresh_import_paths(*, importlib_module=importlib, site_module=site, sys_path=None, isdir=os.path.isdir) -> None`
  - `@dataclass(frozen=True) class InstallResult(ok: bool, restart_required: bool, failed_step: str | None)`
  - `class ComponentInstaller(*, runner, thread_factory, find_spec, refresh, log, post, python=sys.executable)` with `install(*, pip_packages=(), system_plans=(), windows_install=None, expect_modules=(), on_done) -> None` (worker named `component-install`; `on_done(InstallResult)` goes through `post` exactly once; `failed_step` is `"pip" | "system" | "windows" | "refresh" | None`)
  - `@dataclass(frozen=True) class PlayerInstallRequest(pip_packages=(), system_plans=(), windows_dest=None, download_mb=0, manual_command=None)` with property `empty`
  - `player_install_request(status, *, sys_platform, mpv_importable, which=shutil.which, apt_has=None, is_root=None, env=None) -> PlayerInstallRequest`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_system_packages.py`:

```python
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
```

In `tests/test_import_hygiene.py` add `"videotranslator.system_packages",` to `MODULES`.

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_system_packages -v`
Expected: ERROR `ModuleNotFoundError: No module named 'videotranslator.system_packages'`.

- [ ] **Step 3: Create `videotranslator/system_packages.py`**

```python
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
```

- [ ] **Step 4: Run the tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_system_packages test_import_hygiene -v`
Expected: all OK.

- [ ] **Step 5: Real check of "importable without a restart" (C59), no network, no system change**

The pip part installs the local python-mpv wheel into a throw-away user base whose site folder does not exist at interpreter start:

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
WHEEL=/home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI/_dev/research/player-2026-09-25/probe/mpv-1.0.8-py3-none-any.whl
WORK=$(mktemp -d -t vtai-p1-pip-XXXX)
env -u PYTHONPATH PYTHONUSERBASE="$WORK/userbase" PIP_NO_INDEX=1 python3 - "$WHEEL" <<'PYEOF'
import importlib.util, os, site, sys, types
from videotranslator import system_packages as sp
print("user site exists at start:", os.path.isdir(site.getusersitepackages()))
print("mpv importable at start:", importlib.util.find_spec("mpv") is not None)
done = []
installer = sp.ComponentInstaller(
    runner=lambda cmd: sp.run_streaming(cmd, log=print),
    thread_factory=lambda target, name=None, daemon=True: types.SimpleNamespace(start=target),
    find_spec=importlib.util.find_spec, refresh=sp.refresh_import_paths, log=print,
    post=lambda fn: fn())
installer.install(pip_packages=[sys.argv[1]], expect_modules=("mpv",), on_done=done.append)
print("result:", done[0])
print("mpv importable after:", importlib.util.find_spec("mpv") is not None)
PYEOF
rm -rf "$WORK"
```

Expected: `user site exists at start: False`, `mpv importable at start: False`, pip output lines (with "Defaulting to user installation"), `result: InstallResult(ok=True, restart_required=False, failed_step=None)`, `mpv importable after: True`. Record the output in the task report. If pip refuses without network even with the local wheel, record the message and stop (report it).

- [ ] **Step 6: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' videotranslator/system_packages.py tests/test_system_packages.py tests/test_import_hygiene.py || echo "no long dashes"
git add videotranslator/system_packages.py tests/test_system_packages.py tests/test_import_hygiene.py
git commit -m "feat(player): plan Linux libmpv installs and run component installs

system_packages builds the package-manager plan for libmpv (apt libmpv2 or
libmpv1, dnf mpv-libs, pacman mpv, zypper libmpv2) behind pkexec, then
sudo -n, never plain sudo. ComponentInstaller runs pip, the system plan or
the Windows DLL install on a worker, refreshes the import paths so a new
user site is importable without a restart, and reports once through the
Tk callback; it never touches the GUI's _running flag. The install request
for the player placeholder is a pure function computed off the Tk thread."
```

---
## Task 6: Requirements, preflight, CLI flag and documentation

Review level: light

(Declarative files, one optional diagnostic and docs; the only runtime code calls the Task 3 probe.)

**Files:**
- Create: `requirements-player.txt`
- Modify: `requirements.txt`, `pyproject.toml`, `.gitignore`, `README.md`
- Modify: `videotranslator/preflight.py` (`DEFAULT_OPTIONAL_PACKAGES`, `run_preflight`, new `libmpv_native_check`)
- Modify: `videotranslator/cli.py` (`--preflight-player`, new `preflight_options`, the `if args.preflight:` block of `_cli`)
- Modify: `video_translator_gui.py` (the `from videotranslator.preflight import (...)` block, about line 257; `_run_gui_preflight` worker, about line 8593)
- Modify: `tests/test_requirements_static.py`, `tests/test_preflight.py`, `tests/test_cli_smoke.py`
- Create: `tests/test_no_long_dashes.py`

**Interfaces:**
- Consumes (Task 3): `libmpv_runtime.probe_in_subprocess`, `library_loaded`, `LibmpvStatus`, `PYTHON_MPV_REQUIREMENT`.
- Produces:
  - `videotranslator.preflight.libmpv_native_check(*, required: bool = False, probe: Callable[[], LibmpvStatus] | None = None) -> PreflightCheck` (check name `native:libmpv`)
  - `videotranslator.preflight.LIBMPV_HINT: str`
  - `run_preflight(..., native_checks: Sequence[Callable[[], PreflightCheck]] = (), ...)` (a raising check becomes a `WARN` named `native:check`)
  - `PackageProbe("mpv", "mpv", False, "integrated video player (python-mpv)")` in `DEFAULT_OPTIONAL_PACKAGES`
  - `videotranslator.cli.preflight_options(*, lipsync: bool, player: bool, native_check=None) -> dict` with keys `required_optional_modules` and `native_checks`
  - CLI flag `--preflight-player`
  - `requirements-player.txt` with the single line `mpv>=1.0.6,<2`; pyproject extra `player`

- [ ] **Step 1: Write the failing tests**

In `tests/test_requirements_static.py`: add `import re` and `import tomllib` at the top, change the expected list of `test_aggregate_requirements_reference_existing_profiles` to

```python
            [
                "requirements-core.txt",
                "requirements-optional.txt",
                "requirements-wav2lip.txt",
                "requirements-gpu-cu124.txt",
                "requirements-player.txt",
            ],
```

and append to `RequirementsStaticTests`:

```python
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
```

Append to `tests/test_preflight.py` (extend the preflight import with `DEFAULT_OPTIONAL_PACKAGES, MISSING, OK, WARN, libmpv_native_check`):

```python
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
```

In `tests/test_cli_smoke.py` `test_help_does_not_require_runtime_dependencies`, add `self.assertIn("--preflight-player", proc.stdout)`.

Create `tests/test_no_long_dashes.py`:

```python
"""No em dash (U+2014) or en dash (U+2013) in code, tests, docs or the installer (project rule)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG_DASHES = ("\u2014", "\u2013")


def _checked_files():
    files = [ROOT / name for name in ("video_translator_gui.py", "setup_windows.bat", "README.md",
                                      "pyproject.toml", ".gitignore")]
    files += sorted((ROOT / "videotranslator").glob("*.py"))
    files += sorted((ROOT / "tests").glob("*.py"))
    files += sorted(ROOT.glob("requirements*.txt"))
    return files


class NoLongDashesTests(unittest.TestCase):
    def test_no_long_dash_anywhere(self):
        offenders = []
        for path in _checked_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if any(dash in line for dash in LONG_DASHES):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(offenders, [], "long dashes found:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_requirements_static test_preflight test_cli_smoke test_no_long_dashes -v`
Expected: FAIL/ERROR (missing `requirements-player.txt`, `ImportError: cannot import name 'libmpv_native_check'`, no `--preflight-player` in the help). `test_no_long_dashes` already passes (the tree is clean today); it guards the rest of the phase.

- [ ] **Step 3: Requirements, pyproject and .gitignore**

Create `requirements-player.txt`:

```text
# Integrated video player (optional).
#
# python-mpv ("mpv" on PyPI) is a pure-Python wheel that loads the native
# libmpv library:
#   Linux: the distribution package (Debian, Ubuntu, Kali: libmpv2 or
#   libmpv1; Fedora: mpv-libs; Arch: mpv; openSUSE: libmpv2).
#   Windows: setup_windows.bat installs a libmpv build into mpv-runtime.
# Never also install "python-mpv": it ships the same mpv.py module.

mpv>=1.0.6,<2
```

Append to `requirements.txt` (after the gpu line): `-r requirements-player.txt`

In `pyproject.toml`, under `[project.optional-dependencies]` after the `wav2lip` list add:

```toml
player = [
  "mpv>=1.0.6,<2",
]
```

Append to `.gitignore`:

```text

# Integrated player runtime: DLLs and archives fetched by
# `python -m videotranslator.libmpv_runtime install` must never be committed.
mpv-runtime/
*.dll
*.7z
```

- [ ] **Step 4: Preflight native check**

In `videotranslator/preflight.py`:

1. Add `from . import libmpv_runtime` next to `from .platforms import platform_info`.
2. Add to the end of `DEFAULT_OPTIONAL_PACKAGES`: `PackageProbe("mpv", "mpv", False, "integrated video player (python-mpv)"),`
3. Add the parameter `native_checks: Sequence[Callable[[], PreflightCheck]] = (),` to `run_preflight` (right after `optional_binaries`), and right after the `for probe in optional_binaries:` loop:

```python
    for native_check in native_checks:
        checks.append(_run_native_check(native_check))
```

4. Add after `_nvidia_gpu_check` (end of file):

```python
LIBMPV_HINT = ("Linux: install the libmpv2 package (mpv-libs on Fedora, mpv on Arch); "
               "Windows: run setup_windows.bat Repair or use Install in the player pane")


def libmpv_native_check(*, required: bool = False,
                        probe: Callable[[], Any] | None = None) -> PreflightCheck:
    """native:libmpv through the subprocess probe, so a crashing library cannot end the report."""
    status = (probe or libmpv_runtime.probe_in_subprocess)()
    if libmpv_runtime.library_loaded(status):
        profiles = ", ".join(status.vo_profiles_ok) or "none"
        return PreflightCheck("native:libmpv", OK, required,
                              f"{status.path} ({status.detail}; VO profiles: {profiles})")
    return PreflightCheck("native:libmpv", MISSING if required else WARN, required,
                          f"{status.reason}: {status.detail}", LIBMPV_HINT)


def _run_native_check(native_check: Callable[[], PreflightCheck]) -> PreflightCheck:
    try:
        return native_check()
    except Exception as exc:  # a diagnostic must never abort the whole report
        return PreflightCheck("native:check", WARN, False, f"native check failed: {exc}")
```

- [ ] **Step 5: CLI flag and GUI diagnostics**

In `videotranslator/cli.py`: add `from typing import Any` and extend `from collections.abc import Sequence` to `from collections.abc import Callable, Sequence`. After the `--preflight-lipsync` argument add:

```python
    parser.add_argument(
        "--preflight-player",
        action="store_true",
        help="When used with --preflight, require the integrated video player "
             "(python-mpv and a loadable libmpv) instead of reporting it as optional",
    )
```

Add after `_build_parser`:

```python
def preflight_options(*, lipsync: bool, player: bool,
                      native_check: Callable[..., Any] | None = None) -> dict[str, Any]:
    """run_preflight kwargs for --preflight-lipsync and --preflight-player (spec 8.1 item 6)."""
    check = native_check
    if check is None:
        from videotranslator.preflight import libmpv_native_check
        check = libmpv_native_check
    modules: list[str] = []
    if lipsync:
        modules += ["dlib", "facexlib", "basicsr"]
    if player:
        modules.append("mpv")
    return {
        "required_optional_modules": tuple(modules),
        "native_checks": (lambda: check(required=player),),
    }
```

Replace the `if args.preflight:` block of `_cli` with:

```python
    if args.preflight:
        report = legacy._run_preflight(
            required_packages=legacy.REQUIRED_PACKAGES,
            **preflight_options(lipsync=args.preflight_lipsync, player=args.preflight_player),
        )
        print(legacy._format_preflight_report(report))
        sys.exit(0 if report.ok else 1)
```

In `video_translator_gui.py`: add `libmpv_native_check as _libmpv_native_check,` to the `from videotranslator.preflight import (...)` block, and in `_run_gui_preflight`'s worker change `report = _run_preflight(required_packages=REQUIRED_PACKAGES)` to:

```python
                report = _run_preflight(required_packages=REQUIRED_PACKAGES,
                                        native_checks=(_libmpv_native_check,))
```

- [ ] **Step 6: README**

In `README.md`:

1. In `### Windows`, after the line `   - Downloads and installs ffmpeg`, add:

```markdown
   - Installs the integrated video player (python-mpv plus a libmpv build in `mpv-runtime`). The step is optional: if it fails, everything else works and the player pane explains what is missing
```

2. In the `### Linux / macOS` code block, after the `pip install --break-system-packages -r requirements.txt` line, add:

```bash

# Optional: the integrated video player (libmpv from the distribution, python-mpv from PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt
```

3. After the blockquote that starts with `> On first launch the GUI detects any missing packages`, add:

```markdown
> The header shows a **Player** badge. When libmpv or python-mpv is missing, the left pane says what is missing and offers **Install player**: on Linux it uses the package manager through pkexec (then `sudo -n`) and shows the manual command when neither works; on Windows it asks before downloading libmpv for the current user (about 32 MB).
```

4. In `### Requirement profiles`, after the `requirements-gpu-cu124.txt` row, add:

```markdown
| `requirements-player.txt` | Integrated video player: python-mpv (needs libmpv from the system or from the Windows installer). |
```

5. In `### Linux / macOS` of `## Uninstall`, append ` mpv` to the end of the pip uninstall list (after `ctranslate2`).

6. In `### Diagnostics`, add the line `python video_translator_gui.py --preflight --preflight-player` after the `--preflight-lipsync` line of the code block, and append to the paragraph below it: `` `--preflight-player` treats the integrated video player (python-mpv and a loadable libmpv) as required. `python -m videotranslator.libmpv_runtime check` probes libmpv alone (exit 0 ready, 2 unavailable). ``

7. Replace the `## License` section body (`MIT`) with:

```markdown
MIT

### Third-party components

The repository code is MIT. The installers download the components below from their own sources at install time; the project does not redistribute them.

- **libmpv** (https://github.com/mpv-player/mpv), the engine of the integrated video player. Windows: the LGPL build by zhongfly (https://github.com/zhongfly/mpv-winbuild) is tried first; a pinned GPL build by shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) is the fallback. `mpv-runtime\BUILD.txt` records the source, the licence flavour and the mpv commit, and the licence text sits next to the DLL. Linux: the distribution package (`libmpv2`, `libmpv1`, `mpv-libs` or `mpv`).
- **FFmpeg** inside libmpv (LGPL or GPL, following the libmpv build).
- **python-mpv** (`mpv` on PyPI), GPLv2+ or LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), used by the Windows installer to extract libmpv and deleted afterwards.
- **Vulkan loader** (Khronos, MIT and Apache-2.0), downloaded on Windows only when `vulkan-1.dll` is missing.
- **edge-tts** (LGPLv3), used by the dubbing pipeline.
- **MarianMT models** (Helsinki-NLP), downloaded from the Hugging Face Hub at first use under their own licences (Apache-2.0 for the `opus-mt` models, CC-BY-4.0 for `opus-mt-tc-big`).
```

- [ ] **Step 7: Run the tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_requirements_static test_preflight test_cli_smoke test_packaging test_no_long_dashes -v`
Expected: all OK. Also run the real diagnostics once: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && python3 video_translator_gui.py --preflight --preflight-player; echo "exit=$?"` and check that the report lists `[MISSING] python:mpv (required)` and `[MISSING] native:libmpv (required)` with the hint, and `exit=1` (this machine has neither); record the two lines in the task report.

- [ ] **Step 8: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
python3 -m pip install --dry-run --break-system-packages --no-build-isolation --no-deps -e . >/dev/null && echo "metadata ok"
grep -nP '[\x{2013}\x{2014}]' requirements-player.txt requirements.txt pyproject.toml .gitignore README.md videotranslator/preflight.py videotranslator/cli.py video_translator_gui.py tests/test_requirements_static.py tests/test_preflight.py tests/test_cli_smoke.py tests/test_no_long_dashes.py || echo "no long dashes"
git add requirements-player.txt requirements.txt pyproject.toml .gitignore README.md videotranslator/preflight.py videotranslator/cli.py video_translator_gui.py tests/test_requirements_static.py tests/test_preflight.py tests/test_cli_smoke.py tests/test_no_long_dashes.py
git commit -m "feat(player): declare python-mpv as an optional profile and diagnose libmpv

requirements-player.txt and the pyproject extra 'player' pin mpv>=1.0.6,<2
(1.0.5 cannot load files on libmpv 0.41). Preflight gains a native:libmpv
check that probes the library in a child process, python-mpv becomes an
optional package probe, and --preflight-player makes both required. The
README documents the install on Linux and Windows and the third-party
components; .gitignore keeps DLLs and archives out of git, and a static
test guards the no-long-dash rule."
```

If the dry-run metadata step fails because of the local environment (not the pyproject), note it and rely on the CI step.

---
## Task 7: Windows installer step, uninstall lists and static installer tests

Review level: full

(cmd.exe batch that cannot run here: quoting of the pin, step order, error levels, per-user cleanup.)

**Files:**
- Modify: `setup_windows.bat`
- Modify: `tests/test_windows_installer_static.py`

**Interfaces:**
- Consumes (Task 4): `python -m videotranslator.libmpv_runtime install --dest DIR` (exit 0 ready, 2 unavailable, 3 error) and `check --dir DIR` (exit 0 ready); (Task 6) the pin `mpv>=1.0.6,<2` in `requirements-player.txt`.
- Produces: batch labels `:step_player`, `:step_player_disabled`, `:player_check`; variables `MPV_DIR`, `USER_MPV_RUNTIME`, `MPV_PIN`; step labels `1/6` to `6/6` in install and repair.

Rules for this file: ASCII only; CRLF line endings (`.gitattributes` has `*.bat text eol=crlf`; git stores LF, so rewriting line endings in the working copy is invisible to git); never `echo` a line that contains `<` or `>` outside quotes; keep `!` out of echo text except the existing `[!]` prefix style (delayed expansion is on).

- [ ] **Step 1: Write the failing static tests**

Replace `tests/test_windows_installer_static.py` with:

```python
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup_windows.bat"
PIN = "mpv>=1.0.6,<2"


class WindowsInstallerStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SETUP.read_bytes()
        cls.text = cls.raw.decode("ascii")  # raises on any non-ASCII byte
        cls.flat = cls.text.replace("\r\n", "\n")
        cls.lines = cls.flat.split("\n")

    def test_installer_copies_python_package(self):
        self.assertIn(r"%SCRIPT_DIR%videotranslator", self.text)
        self.assertIn(r"%INSTALL_DIR%\videotranslator", self.text)
        self.assertIn(r"videotranslator\*.py", self.text)

    def test_validate_install_imports_application(self):
        self.assertIn('pushd "%INSTALL_DIR%"', self.text)
        self.assertIn('"import video_translator_gui"', self.text)
        self.assertIn("Application importable.", self.text)

    def test_every_line_ends_with_crlf(self):
        lf_only = [number for number, line in enumerate(self.raw.split(b"\n")[:-1], 1)
                   if not line.endswith(b"\r")]
        self.assertEqual(lf_only, [])

    def test_player_runtime_paths(self):
        self.assertIn(r'set "MPV_DIR=%INSTALL_DIR%\mpv-runtime"', self.text)
        self.assertIn(r'set "USER_MPV_RUNTIME=%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime"', self.text)

    def test_player_step_runs_after_ffmpeg_in_install_and_repair(self):
        self.assertRegex(self.flat, r'call :step_ffmpeg "4/6" "0"\s+call :step_player "5/6"\s+'
                                    r'call :step_shortcut "6/6"')
        self.assertRegex(self.flat, r'call :step_ffmpeg "4/6" "1"\s+call :step_player "5/6"')
        self.assertIn('echo [6/6] Desktop shortcut already present, skipping.', self.text)
        self.assertNotRegex(self.flat, r'"\d/5"')
        self.assertNotIn("[5/5]", self.text)

    def _label_body(self, label, end_pattern):
        """Text from the line ``:label`` up to the first line matching ``end_pattern``."""
        match = re.search(rf"\n:{label}\n(.*?)\n{end_pattern}\n", self.flat, re.S)
        self.assertIsNotNone(match, f":{label} not found")
        return match.group(1)

    def test_the_player_check_only_warns_after_validation(self):
        pattern = r'call :validate_install\nif errorlevel 1 \( pause & exit /b 1 \)\ncall :player_check\n'
        self.assertEqual(len(re.findall(pattern, self.flat)), 2)
        body = self._label_body("player_check", "goto :eof")  # the final line, not the early `if`
        self.assertIn('-m videotranslator.libmpv_runtime check --dir "%MPV_DIR%"', body)
        self.assertNotIn("exit /b 1", body)

    def test_the_pin_has_its_own_quoted_variable_and_is_never_echoed(self):
        self.assertIn(f'set "MPV_PIN={PIN}"', self.text)
        self.assertIn('-m pip install "%MPV_PIN%" --quiet', self.text)
        for line in self.lines:
            if line.lstrip().lower().startswith("echo"):
                self.assertNotIn("MPV_PIN", line)
        self.assertIn(PIN, (ROOT / "requirements-player.txt").read_text(encoding="utf-8"))

    def test_libmpv_install_runs_from_the_install_dir_and_never_fails_the_setup(self):
        self.assertIn('-m videotranslator.libmpv_runtime install --dest "%MPV_DIR%"', self.text)
        body = self._label_body("step_player", ":player_check")
        self.assertIn('pushd "%INSTALL_DIR%"', body)
        self.assertIn("Integrated player disabled - everything else works", body)
        self.assertNotIn("exit /b 1", body)

    def test_both_uninstall_lists_remove_python_mpv(self):
        # Full list: right before its last line; custom menu: its own prompt.
        self.assertIn("    mpv python-mpv ^\n    yt-dlp edge-tts deep-translator pydub pyloudnorm "
                      "soundfile sacremoses sentencepiece 2>nul", self.flat)
        self.assertIn('if /i "!Q_MPV!"=="Y" "%PYTHON_EXE%" -m pip uninstall -y mpv python-mpv', self.text)

    def test_per_user_cleanup_removes_only_the_player_runtime(self):
        self.assertIn('rmdir /S /Q "%USER_MPV_RUNTIME%"', self.text)
        self.assertIn(r'rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI\mpv-runtime"', self.text)
        self.assertNotIn(r'rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI"', self.text)
        self.assertNotIn(r'rmdir /S /Q "%LOCALAPPDATA%\VideoTranslatorAI"', self.text)

    def test_pipeline_packages_line_is_unchanged(self):
        self.assertIn('set "PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub '
                      'yt-dlp pyloudnorm sentencepiece sacremoses torchcodec silero-vad keyring"',
                      self.text)
        self.assertNotRegex(self.text, r"\bav>=|onnxruntime")

    def test_no_folder_named_mpv(self):
        self.assertIsNone(re.search(r'\\mpv(["\\\s]|$)', self.text, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_windows_installer_static -v`
Expected: FAIL on every new test (and `test_every_line_ends_with_crlf` lists the LF-only lines of the current working copy, around the `:validate_install` block).

- [ ] **Step 3: Edit `setup_windows.bat`**

Apply these replacements (use Python or the Edit tool; the normalisation in Step 4 fixes any line ending an editor writes).

a) Paths. After `set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"` add:

```bat
set "MPV_DIR=%INSTALL_DIR%\mpv-runtime"
```

After `set "USER_XTTS_CACHE=%LOCALAPPDATA%\tts"` add:

```bat
set "USER_MPV_RUNTIME=%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime"
```

b) `:mode_install`: replace

```bat
call :step_python   "1/5"
if errorlevel 1 ( pause & exit /b 1 )

call :step_copy_files "2/5"
if errorlevel 1 ( pause & exit /b 1 )

call :step_install_deps "3/5" "0"
if errorlevel 1 ( pause & exit /b 1 )

call :step_ffmpeg "4/5" "0"
call :step_shortcut "5/5"

call :validate_install
if errorlevel 1 ( pause & exit /b 1 )
call :print_done "Installation complete"
```

with

```bat
call :step_python   "1/6"
if errorlevel 1 ( pause & exit /b 1 )

call :step_copy_files "2/6"
if errorlevel 1 ( pause & exit /b 1 )

call :step_install_deps "3/6" "0"
if errorlevel 1 ( pause & exit /b 1 )

call :step_ffmpeg "4/6" "0"
call :step_player "5/6"
call :step_shortcut "6/6"

call :validate_install
if errorlevel 1 ( pause & exit /b 1 )
call :player_check
call :print_done "Installation complete"
```

c) `:mode_repair`: after `echo    - Re-run pip install to pick up new/missing packages` add

```bat
echo    - Install or re-check the integrated video player (optional)
```

and replace

```bat
call :step_python   "1/5"
if errorlevel 1 ( pause & exit /b 1 )

call :step_copy_files "2/5"
if errorlevel 1 ( pause & exit /b 1 )

call :step_install_deps "3/5" "1"

call :step_ffmpeg "4/5" "1"

if exist "%PUBLIC_SHORTCUT%" (
    echo.
    echo [5/5] Desktop shortcut already present, skipping.
) else (
    call :step_shortcut "5/5"
)

call :validate_install
if errorlevel 1 ( pause & exit /b 1 )
call :print_done "Repair complete"
```

with

```bat
call :step_python   "1/6"
if errorlevel 1 ( pause & exit /b 1 )

call :step_copy_files "2/6"
if errorlevel 1 ( pause & exit /b 1 )

call :step_install_deps "3/6" "1"

call :step_ffmpeg "4/6" "1"

call :step_player "5/6"

if exist "%PUBLIC_SHORTCUT%" (
    echo.
    echo [6/6] Desktop shortcut already present, skipping.
) else (
    call :step_shortcut "6/6"
)

call :validate_install
if errorlevel 1 ( pause & exit /b 1 )
call :player_check
call :print_done "Repair complete"
```

d) Insert right before the lines `:: %~1 = step label` / `:step_shortcut` (after the `:step_ffmpeg_skip` block and its blank lines):

```bat
:: %~1 = step label
:: Optional integrated video player: python-mpv (pip) plus a libmpv build in
:: %MPV_DIR%. Download, SHA256 checks, 7zr extraction and the load check all
:: run in Python (videotranslator\libmpv_runtime.py), so no PowerShell exit
:: code is involved. Any failure only disables the player: always exit 0.
:step_player
echo.
echo [%~1] Installing the integrated video player (optional)...
:: The pin lives in its own variable, quoted where it is used and never
:: echoed: cmd.exe would read the comparison signs as redirections.
set "MPV_PIN=mpv>=1.0.6,<2"
"%PYTHON_EXE%" -m pip install "%MPV_PIN%" --quiet
if errorlevel 1 goto step_player_disabled
pushd "%INSTALL_DIR%" >nul 2>&1
"%PYTHON_EXE%" -m videotranslator.libmpv_runtime install --dest "%MPV_DIR%"
set "MPV_RC=%ERRORLEVEL%"
popd >nul 2>&1
if not "%MPV_RC%"=="0" goto step_player_disabled
echo  [+] Integrated video player ready.
exit /b 0

:step_player_disabled
echo.
echo  ============================================
echo    Integrated player disabled - everything else works
echo  ============================================
echo.
echo   The application works without the player.
echo   To retry, run setup_windows.bat again and
echo   choose option [2] Repair / Update.
echo.
exit /b 0


:: Runs after :validate_install. A failed check only warns: the application
:: works without the integrated player.
:player_check
if not exist "%MPV_DIR%\mpv-2.dll" goto :eof
pushd "%INSTALL_DIR%" >nul 2>&1
"%PYTHON_EXE%" -m videotranslator.libmpv_runtime check --dir "%MPV_DIR%" >nul 2>&1
set "MPV_CHECK_RC=%ERRORLEVEL%"
popd >nul 2>&1
if "%MPV_CHECK_RC%"=="0" (
    echo  [+] Integrated video player check passed.
) else (
    echo  [!] Integrated video player check failed, code %MPV_CHECK_RC%. The application works without it.
)
goto :eof


```

e) `:remove_user_caches_all`: change `echo  [*] Removing HF + XTTS model caches for all users ...` to `echo  [*] Removing HF + XTTS model caches and the player runtime for all users ...`, and inside the `for /d %%U` loop, after the XTTS `if exist ... ( ... )` block, add:

```bat
    if exist "%%~U\AppData\Local\VideoTranslatorAI\mpv-runtime" (
        echo      - %%~nxU : player runtime
        rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI\mpv-runtime" 2>nul
    )
```

f) `:remove_user_cache_current`: change its first echo to `echo  [*] Removing HF + XTTS model cache and the player runtime for %USERNAME% ...` and after `if exist "%USER_XTTS_CACHE%" rmdir /S /Q "%USER_XTTS_CACHE%" 2>nul` add:

```bat
if exist "%USER_MPV_RUNTIME%" rmdir /S /Q "%USER_MPV_RUNTIME%" 2>nul
```

(Only the `mpv-runtime` subfolder: deleting all of `%LOCALAPPDATA%\VideoTranslatorAI` is out of scope, spec Q11.)

i) Above `:step_python`, change the comment `:: %~1 = step label e.g. "1/5"` to `:: %~1 = step label e.g. "1/6"` (the static test rejects any leftover `"x/5"`).

g) `:remove_python_packages_all`: in the `pip uninstall -y ^` list, insert before the last line (`    yt-dlp edge-tts ... sentencepiece 2>nul`):

```bat
    mpv python-mpv ^
```

h) Custom uninstall: after the `Q_MIS` block (the `if /i "!Q_MIS!"=="Y" ...` line) add:

```bat

set "Q_MPV="
set /p "Q_MPV=Remove the integrated video player package (mpv / python-mpv) ? [Y/N]: "
if /i "!Q_MPV!"=="Y" "%PYTHON_EXE%" -m pip uninstall -y mpv python-mpv
```

- [ ] **Step 4: Normalise line endings to CRLF and check ASCII**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 - <<'PYEOF'
from pathlib import Path
path = Path("setup_windows.bat")
data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
data.decode("ascii")  # fails loudly on any non-ASCII byte
path.write_bytes(data)
print("CRLF lines:", data.count(b"\r\n"))
PYEOF
git diff --stat setup_windows.bat
```

Expected: `git diff --stat` shows only the lines you edited (git normalises line endings, so the CRLF rewrite of older LF-only lines is invisible).

- [ ] **Step 5: Run the tests**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && env PYTHONPATH=tests python3 -m unittest test_windows_installer_static test_no_long_dashes -v`
Expected: all OK.

- [ ] **Step 6: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
grep -nP '[\x{2013}\x{2014}]' setup_windows.bat tests/test_windows_installer_static.py || echo "no long dashes"
git add setup_windows.bat tests/test_windows_installer_static.py
git commit -m "feat(installer): install the integrated video player on Windows

A new optional step 5/6 installs python-mpv through its own quoted pin
variable and runs python -m videotranslator.libmpv_runtime install into
%INSTALL_DIR%\\mpv-runtime; any failure prints 'Integrated player disabled -
everything else works' and the setup continues. After validation a load
check only warns. Uninstall removes mpv and python-mpv in both package
lists and only the per-user mpv-runtime folder. The file stays ASCII with
CRLF line endings, guarded by the static tests."
```

The Windows run of this step is an operator item (spec S4 (1) and P1 acceptance): recorded in the final acceptance list.

---
## Task 8: Header badge, status placeholder and the GUI install flow

Review level: full

(Worker threads posting to Tk, the shared `_installing` flag, the install flow that runs pip and a package manager, and config writes.)

**Files:**
- Create: `videotranslator/player_panel_tk.py`
- Modify: `video_translator_gui.py`: imports (after `from videotranslator.ui_theme_tk import ThemeManager as _ThemeManager`, about line 317); `App.__init__` (flags near `self._preflight_running = False`, scheduling near `self.after(800, self._upgrade_ytdlp_in_background)`); `_install_ffmpeg`, `_ffmpeg_done`, `_install_deps`, `_install_done` (one line each); `_build_header` (badge); `_build_ui` (panel inside `self._player_area`); `_apply_lang` (relabel); a new method block after `_redirecting_thread_factory`
- Modify: `tests/test_ui_theme_tk.py` (`built_app` patches `App._refresh_player_status`)
- Modify: `tests/test_import_hygiene.py` (add the module)
- Create: `tests/test_player_panel_tk.py`

**Interfaces:**
- Consumes: Task 1 `App._redirecting_thread_factory`; Task 2 keys; Task 3 `LibmpvStatus`, `resolve_status`, `status_message`, `badge_level`, `offers_install`, `cache_entry`; Task 4 `install_windows`; Task 5 `ComponentInstaller`, `InstallResult`, `PlayerInstallRequest`, `player_install_request`, `run_streaming`, `refresh_import_paths`; existing `App._flat_btn(parent, primary=False, **kwargs) -> (wrap, button)`, `App._status_badge(parent, text, color) -> Frame` (children: dot label, text label), `App._log_async`, `load_config`, `save_config`, palette globals `OK`, `WARN`, `ERR`, `FG2`, `SEL`, `FG`.
- Produces:
  - `videotranslator.player_panel_tk.VIDEO_BG = "#000000"`, `TEXT_FG = "#a3a3a3"`, `LOGO_FG = "#c3c3c3"`, `INSTALL_STATE_KEYS: dict[str, str]`
  - `class HoverTip(widget, text_fn: Callable[[], str], *, colors_fn: Callable[[], tuple[str, str]], delay_ms=500)` with `hide()`
  - `class PlayerPanel(tk.Frame)(parent, *, ui_s, make_button, on_command, logo_path, sys_platform=sys.platform)` with attributes `video_host`, `placeholder`, `logo`, `title_label`, `message_label`, `install_label`, `install_button`, and methods `show_unavailable(status, *, install_cmd)`, `show_ready(status)`, `show_install_progress(state: str | None)` (`"installing" | "ok" | "failed" | None`), `relabel()`, `status_text() -> str`
  - App attributes: `_installing: bool`, `_player_status: LibmpvStatus | None`, `_player_install_request: PlayerInstallRequest | None`, `_player_panel`, `_player_badge`, `_player_badge_dot`, `_player_badge_label`, `_player_badge_tip`
  - App methods: `_player_log(line)`, `_post_if_alive(fn)`, `_player_status_text() -> str`, `_refresh_player_status(*, force_probe=False)`, `_on_player_status(status, request)`, `_update_player_badge()`, `_on_player_command(name, args)`, `_install_player()`, `_player_installer() -> ComponentInstaller`, `_on_player_install_done(result)`
  - Config key written by the GUI only: `player_probe` (spec 2.5)

If Plan P0 (layout) has already landed, `self._player_area` is still the host of the left pane (P0 keeps it): insert the panel right after it is created, wherever `_build_ui` builds it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ui_theme_tk.py`, inside `built_app`, add one more patch to the `with mock.patch.object(...)` chain, as a new line right before the last one (`mock.patch.object(gui.App, "_fit_to_screen", lambda self: None):`), because the status worker would otherwise start a probe subprocess in every GUI test:

```python
                    mock.patch.object(gui.App, "_refresh_player_status", lambda self, **kw: None), \
```

In the same file, `BuiltAppStreamsTests.test_streams_restored_when_app_constructor_raises` swaps `App` for a stub class whose attributes `built_app` patches; give the stub the new attribute too (mock.patch.object raises AttributeError on a missing attribute):

```python
        class ExplodingApp:
            _check_deps_on_start = _upgrade_ytdlp_in_background = _fit_to_screen = \
                _refresh_player_status = lambda self, **kw: None
```

In `tests/test_import_hygiene.py` add `"videotranslator.player_panel_tk",` to `MODULES`.

Create `tests/test_player_panel_tk.py`:

```python
"""PlayerPanel placeholder, HoverTip and the GUI player wiring (spec 2.3, 3.1, 6.1).

Tk tests: they skip without a display (CI) and run locally under Xvfb.
"""

import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from test_ui_theme_tk import HAS_DISPLAY, built_app
from videotranslator.libmpv_runtime import LibmpvStatus
from videotranslator.system_packages import InstallResult, PlayerInstallRequest
from videotranslator.ui_strings_player import PLAYER_UI_STRINGS

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "assets" / "icon_256.png"
CMD = "sudo apt install libmpv2"
MISSING = LibmpvStatus(ok=False, reason="libmpv-missing", detail="no libmpv.so in ldconfig -p")
TOO_OLD = LibmpvStatus(ok=False, reason="libmpv-too-old", api_version=(1, 109), mpv_version=(0, 32))
READY = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                     path="/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0",
                     vo_profiles_ok=("x11egl", "x11sw"), detail="mpv 0.41.0, client API 2.5",
                     fingerprint="/usr/lib/x86_64-linux-gnu/libmpv.so.2.5.0|10|20")


def _make_button(parent, **kwargs):
    kwargs.pop("primary", None)
    wrap = tk.Frame(parent)
    button = tk.Button(wrap, **kwargs)
    button.pack()
    return wrap, button


def _en(key):
    return PLAYER_UI_STRINGS["en"][key]


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class PlayerPanelTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.lang = "en"
        self.commands = []
        self.panel = self._panel(LOGO, "linux")

    def tearDown(self):
        self.root.destroy()

    def _panel(self, logo, platform):
        from videotranslator.player_panel_tk import PlayerPanel

        panel = PlayerPanel(self.root, ui_s=lambda key: PLAYER_UI_STRINGS[self.lang][key],
                            make_button=_make_button,
                            on_command=lambda name, args: self.commands.append((name, args)),
                            logo_path=logo, sys_platform=platform)
        panel.pack(fill="both", expand=True)
        self.root.update_idletasks()
        return panel

    def test_before_any_status_only_the_logo_shows(self):
        self.assertEqual(self.panel.title_label.cget("text"), "")
        self.assertEqual(self.panel.message_label.cget("text"), "")
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")
        self.assertEqual(self.panel.status_text(), _en("player_badge"))

    def test_a_missing_library_shows_reason_command_and_install(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.assertEqual(self.panel.title_label.cget("text"), _en("player_unavailable_title"))
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_missing_libmpv_linux").format(cmd=CMD))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "pack")
        self.assertEqual(self.panel.install_button.cget("text"), _en("player_install_btn"))

    def test_too_old_has_no_install_button(self):
        self.panel.show_unavailable(TOO_OLD, install_cmd=None)
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_libmpv_too_old").format(version="0.32"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")

    def test_ready_shows_the_version_and_the_system_credits(self):
        self.panel.show_ready(READY)
        self.assertEqual(self.panel.title_label.cget("text"), "")
        self.assertEqual(self.panel.message_label.cget("text"),
                         _en("player_badge_ok").format(version="0.41") + "\n"
                         + _en("player_credits").format(license=_en("player_license_system")))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")

    def test_windows_texts(self):
        panel = self._panel(LOGO, "win32")
        panel.show_ready(LibmpvStatus(ok=True, reason="ok", mpv_version=(0, 41),
                                      build={"licence": "LGPL"}))
        self.assertTrue(panel.status_text().endswith(_en("player_credits").format(license="LGPL")))
        panel.show_unavailable(LibmpvStatus(ok=False, reason="libmpv-missing"), install_cmd=None)
        self.assertEqual(panel.message_label.cget("text"), _en("player_missing_libmpv_win"))
        self.assertEqual(panel._install_wrap.winfo_manager(), "pack")

    def test_the_install_button_sends_the_install_command(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.panel.install_button.invoke()
        self.assertEqual(self.commands, [("install", {})])

    def test_install_progress_line_and_button(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.panel.show_install_progress("installing")
        self.assertEqual(self.panel.install_label.cget("text"), _en("player_installing"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "")
        self.panel.show_install_progress("failed")
        self.assertEqual(self.panel.install_label.cget("text"), _en("player_install_failed"))
        self.assertEqual(self.panel._install_wrap.winfo_manager(), "pack")
        self.assertIn(CMD, self.panel.message_label.cget("text"))  # the manual command stays
        self.panel.show_install_progress(None)
        self.assertEqual(self.panel.install_label.cget("text"), "")

    def test_relabel_follows_the_language(self):
        self.panel.show_unavailable(MISSING, install_cmd=CMD)
        self.lang = "ja"
        self.panel.relabel()
        self.assertEqual(self.panel.title_label.cget("text"),
                         PLAYER_UI_STRINGS["ja"]["player_unavailable_title"])
        self.assertEqual(self.panel.install_button.cget("text"),
                         PLAYER_UI_STRINGS["ja"]["player_install_btn"])

    def test_logo_image_and_canvas_fallback(self):
        self.assertIsInstance(self.panel.logo, tk.Label)
        self.assertTrue(self.panel.logo.cget("image"))
        fallback = self._panel(ROOT / "assets" / "missing.png", "linux")
        self.assertIsInstance(fallback.logo, tk.Canvas)
        self.assertEqual(fallback.logo.itemcget(fallback.logo.find_all()[0], "fill"), "#c3c3c3")

    def test_only_reserved_colours(self):
        for widget in (self.panel, self.panel.video_host, self.panel.placeholder):
            self.assertEqual(widget.cget("bg"), "#000000")
        self.assertEqual(self.panel.message_label.cget("fg"), "#a3a3a3")


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class HoverTipTests(unittest.TestCase):
    def test_show_reads_text_and_colours_each_time_and_hide_destroys(self):
        from videotranslator.player_panel_tk import HoverTip

        root = tk.Tk()
        root.withdraw()
        try:
            label = tk.Label(root, text="x")
            label.pack()
            texts = iter(["first", "second"])
            tip = HoverTip(label, lambda: next(texts), colors_fn=lambda: ("#111111", "#eeeeee"))
            tip._show()
            shown = tip._tip.winfo_children()[0]
            self.assertEqual(shown.cget("text"), "first")
            self.assertEqual(shown.cget("bg"), "#111111")
            tip.hide()
            self.assertIsNone(tip._tip)
            tip._show()
            self.assertEqual(tip._tip.winfo_children()[0].cget("text"), "second")
            tip.hide()
        finally:
            root.destroy()


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class GuiPlayerWiringTests(unittest.TestCase):
    def test_badge_and_placeholder_follow_the_status(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "en"}) as (gui, app, _):
            self.assertEqual(app._player_badge_label.cget("text"), gui.UI_STRINGS["en"]["player_badge"])
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.FG2)
            app._on_player_status(MISSING, PlayerInstallRequest(manual_command=CMD))
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.WARN)
            self.assertIn(CMD, app._player_panel.message_label.cget("text"))
            self.assertEqual(app._player_status_text(), app._player_panel.status_text())
            app._on_player_status(TOO_OLD, PlayerInstallRequest())
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.ERR)
            app._on_player_status(READY, PlayerInstallRequest())
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.OK)

    def test_a_probed_ready_status_is_cached_in_the_config(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            app._on_player_status(READY, PlayerInstallRequest())
            self.assertEqual(gui.load_config()["player_probe"]["fingerprint"], READY.fingerprint)

    def test_the_language_switch_relabels_badge_and_placeholder(self):
        with built_app({"ui_lang": "it"}) as (gui, app, _):
            app._on_player_status(MISSING, PlayerInstallRequest(manual_command=CMD))
            app._ui_lang.set("ja")
            app._apply_lang()
            self.assertEqual(app._player_badge_label.cget("text"), gui.UI_STRINGS["ja"]["player_badge"])
            self.assertEqual(app._player_panel.title_label.cget("text"),
                             gui.UI_STRINGS["ja"]["player_unavailable_title"])

    def test_a_second_install_is_refused_while_one_runs(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            app._installing = True
            with mock.patch.object(gui.messagebox, "showerror") as showerror:
                app._install_player()
            showerror.assert_called_once()
            self.assertEqual(showerror.call_args.args[1], gui.UI_STRINGS["en"]["live_err_busy_install"])

    def _run_install(self, app, result):
        request = PlayerInstallRequest(pip_packages=("mpv>=1.0.6,<2",),
                                       system_plans=((("pkexec", "apt-get", "update"),),),
                                       manual_command=CMD)
        app._on_player_status(MISSING, request)
        calls = []

        class FakeInstaller:
            saw_installing = None

            def install(self, **kwargs):
                calls.append(kwargs)
                self.saw_installing = app._installing
                kwargs["on_done"](result)

        fake = FakeInstaller()
        with mock.patch.object(app, "_player_installer", return_value=fake), \
                mock.patch.object(app, "_refresh_player_status") as refresh:
            app._install_player()
        return calls, fake, refresh

    def test_install_runs_the_request_then_reprobes(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            calls, fake, refresh = self._run_install(app, InstallResult(True, False, None))
            self.assertEqual(calls[0]["pip_packages"], ("mpv>=1.0.6,<2",))
            self.assertEqual(calls[0]["system_plans"], ((("pkexec", "apt-get", "update"),),))
            self.assertIsNone(calls[0]["windows_install"])
            self.assertEqual(calls[0]["expect_modules"], ("mpv",))
            self.assertTrue(fake.saw_installing)
            self.assertFalse(app._installing)
            refresh.assert_called_once_with(force_probe=True)
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_ok"])

    def test_an_install_that_needs_a_restart_says_so(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            _, _, refresh = self._run_install(app, InstallResult(True, True, None))
            refresh.assert_not_called()
            self.assertEqual(app._player_status.reason, "restart-required")
            self.assertEqual(app._player_panel.message_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_restart_required"])
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_ok"])
            self.assertEqual(app._player_badge_dot.cget("fg"), gui.WARN)

    def test_a_failed_install_keeps_the_reason_and_the_manual_command(self):
        with built_app({"ui_lang": "en"}) as (gui, app, _):
            _, _, refresh = self._run_install(app, InstallResult(False, False, "system"))
            refresh.assert_not_called()
            self.assertIn(CMD, app._player_panel.message_label.cget("text"))
            self.assertEqual(app._player_panel.install_label.cget("text"),
                             gui.UI_STRINGS["en"]["player_install_failed"])
            self.assertEqual(app._player_panel._install_wrap.winfo_manager(), "pack")
            self.assertFalse(app._installing)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests on a private Xvfb to see them fail**

Run: `unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI && timeout 600 xvfb-run -a -s "-screen 0 1280x800x24" env PYTHONPATH=tests python3 -m unittest test_player_panel_tk test_import_hygiene -v`
Expected: ERROR `ModuleNotFoundError: No module named 'videotranslator.player_panel_tk'`. (Without Xvfb the Tk classes would only skip.)

- [ ] **Step 3: Create `videotranslator/player_panel_tk.py`**

```python
"""Tk glue of the integrated player pane (spec 2.3).

P1 builds the video host and the placeholder that explains the player
status: the logo, a title and the reason when the player is unavailable (or
the "ready" line with the credits), the install state and an Install
button. P2 adds the seek bar, the controls, the theme hook and playback.

Only colours reserved in ui_theme.TK_DEFAULT_COLORS are used here (#000000,
#a3a3a3, #c3c3c3), so the live recolour walk never remaps them; the Install
button comes from the GUI's own button factory and follows the theme
through that walk.
"""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import libmpv_runtime
from .libmpv_runtime import LibmpvStatus

VIDEO_BG = "#000000"
TEXT_FG = "#a3a3a3"
LOGO_FG = "#c3c3c3"
INSTALL_STATE_KEYS = {
    "installing": "player_installing",
    "ok": "player_install_ok",
    "failed": "player_install_failed",
}
_MIN_WRAP = 200


class HoverTip:
    """A small borderless window that shows text while the pointer rests on a widget.

    The text and the colours are read when the tip opens, so they follow
    language and theme changes without a refresh call.
    """

    def __init__(self, widget: tk.Misc, text_fn: Callable[[], str], *,
                 colors_fn: Callable[[], tuple[str, str]], delay_ms: int = 500) -> None:
        self._widget = widget
        self._text_fn = text_fn
        self._colors_fn = colors_fn
        self._delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        for target in (widget, *widget.winfo_children()):
            target.bind("<Enter>", self._schedule, add="+")
            target.bind("<Leave>", self.hide, add="+")
            target.bind("<ButtonPress>", self.hide, add="+")

    def _schedule(self, _event: Any = None) -> None:
        self._cancel()
        self._after_id = self._widget.after(self._delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        text = self._text_fn()
        if not text or self._tip is not None:
            return
        bg, fg = self._colors_fn()
        tip = tk.Toplevel(self._widget)
        tip.wm_overrideredirect(True)
        tk.Label(tip, text=text, bg=bg, fg=fg, font="VT.Small", justify="left",
                 wraplength=360, padx=6, pady=4).pack()
        x = self._widget.winfo_rootx()
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip

    def hide(self, _event: Any = None) -> None:
        self._cancel()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


class PlayerPanel(tk.Frame):
    """The left pane of the main window: the video host and the status placeholder."""

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str],
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 on_command: Callable[[str, dict], None], logo_path: Path | None,
                 sys_platform: str = sys.platform) -> None:
        super().__init__(parent, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self._ui_s = ui_s
        self._on_command = on_command
        self._sys_platform = sys_platform
        self._status: LibmpvStatus | None = None
        self._install_cmd: str | None = None
        self._install_state: str | None = None
        # From P2 on, mpv's child window covers video_host (spec 2.3).
        self.video_host = tk.Frame(self, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self.video_host.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.placeholder = tk.Frame(self, bg=VIDEO_BG, highlightthickness=0, bd=0)
        self.placeholder.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.placeholder.lift()
        box = tk.Frame(self.placeholder, bg=VIDEO_BG)
        box.place(relx=0.5, rely=0.5, anchor="center")
        self._logo_base = self._load_logo(logo_path)
        self._logo_factor = 1
        self._logo_image = None
        if self._logo_base is not None:
            self._logo_factor = 2
            self._logo_image = self._logo_base.subsample(2)
            self.logo: tk.Widget = tk.Label(box, image=self._logo_image, bg=VIDEO_BG, bd=0)
        else:  # spec 2.3 [CC] G28: a canvas play mark when the PNG is missing or unreadable
            self.logo = tk.Canvas(box, width=96, height=96, bg=VIDEO_BG, highlightthickness=0, bd=0)
            self.logo.create_polygon(32, 20, 32, 76, 80, 48, fill=LOGO_FG, outline="")
        self.logo.pack(pady=(0, 12))
        self.title_label = tk.Label(box, text="", bg=VIDEO_BG, fg=LOGO_FG, font="VT.Bold")
        self.title_label.pack()
        self.message_label = tk.Label(box, text="", bg=VIDEO_BG, fg=TEXT_FG, font="VT.Base",
                                      justify="center", wraplength=360)
        self.message_label.pack(pady=(6, 0))
        self.install_label = tk.Label(box, text="", bg=VIDEO_BG, fg=TEXT_FG, font="VT.Small",
                                      justify="center", wraplength=360)
        self.install_label.pack(pady=(4, 0))
        self._install_wrap, self.install_button = make_button(
            box, primary=True, text=ui_s("player_install_btn"), command=self._request_install)
        self.bind("<Configure>", self._on_resize)
        self._render()

    # -- public API ---------------------------------------------------------

    def show_unavailable(self, status: LibmpvStatus, *, install_cmd: str | None) -> None:
        self._status = status
        self._install_cmd = install_cmd
        self._render()

    def show_ready(self, status: LibmpvStatus) -> None:
        self._status = status
        self._install_cmd = None
        self._render()

    def show_install_progress(self, state: str | None) -> None:
        """``state``: "installing", "ok", "failed" or None (no install line)."""
        self._install_state = state
        self._render()

    def relabel(self) -> None:
        """Called by App._apply_lang after a language switch."""
        self._render()

    def status_text(self) -> str:
        """The translated status: the placeholder message and the badge tooltip."""
        status = self._status
        if status is None:
            return self._ui_s("player_badge")
        key, params = libmpv_runtime.status_message(
            status, sys_platform=self._sys_platform, install_cmd=self._install_cmd)
        text = self._ui_s(key).format(**params)
        if status.ok:
            licence = status.build.get("licence") or self._ui_s("player_license_system")
            text += "\n" + self._ui_s("player_credits").format(license=licence)
        return text

    # -- internals ----------------------------------------------------------

    def _load_logo(self, path: Path | None) -> tk.PhotoImage | None:
        if path is None:
            return None
        try:
            return tk.PhotoImage(master=self, file=str(path))
        except (tk.TclError, OSError):
            return None

    def _request_install(self) -> None:
        self._on_command("install", {})

    def _on_resize(self, event: Any) -> None:
        wrap = max(_MIN_WRAP, event.width - 48)
        self.message_label.configure(wraplength=wrap)
        self.install_label.configure(wraplength=wrap)
        if self._logo_base is None:
            return
        limit = max(32, event.height // 3)   # the logo takes at most a third of the pane
        factor = max(1, -(-self._logo_base.height() // limit))
        if factor != self._logo_factor:
            self._logo_factor = factor
            self._logo_image = self._logo_base.subsample(factor)
            self.logo.configure(image=self._logo_image)

    def _render(self) -> None:
        status = self._status
        if status is None:
            title, message = "", ""
        elif status.ok:
            title, message = "", self.status_text()
        else:
            title, message = self._ui_s("player_unavailable_title"), self.status_text()
        self.title_label.configure(text=title)
        self.message_label.configure(text=message)
        state_key = INSTALL_STATE_KEYS.get(self._install_state or "")
        self.install_label.configure(text=self._ui_s(state_key) if state_key else "")
        self.install_button.configure(text=self._ui_s("player_install_btn"))
        show = (status is not None and not status.ok and self._install_state != "installing"
                and libmpv_runtime.offers_install(status, sys_platform=self._sys_platform))
        if show and not self._install_wrap.winfo_manager():
            self._install_wrap.pack(pady=(10, 0))
        elif not show and self._install_wrap.winfo_manager():
            self._install_wrap.pack_forget()
```

- [ ] **Step 4: Wire the GUI**

In `video_translator_gui.py`:

a) Imports, right after `from videotranslator.ui_theme_tk import ThemeManager as _ThemeManager  # noqa: E402`:

```python
from videotranslator import libmpv_runtime as _libmpv_runtime  # noqa: E402
from videotranslator import system_packages as _system_packages  # noqa: E402
from videotranslator.player_panel_tk import HoverTip as _HoverTip  # noqa: E402
from videotranslator.player_panel_tk import PlayerPanel as _PlayerPanel  # noqa: E402
```

b) `App.__init__`, right after `self._preflight_running = False`:

```python
        # Integrated player (spec 9 P1): the last availability status, the
        # install request computed with it, and the flag shared by every
        # component install (startup ffmpeg/pip installs set it too).
        self._installing = False
        self._player_status = None
        self._player_install_request = None
```

and right after `self.after(800, self._upgrade_ytdlp_in_background)`:

```python
        self.after(1500, self._refresh_player_status)
```

c) One line each: in `_install_ffmpeg` add `self._installing = True` after `self._running = True`; in `_ffmpeg_done` add `self._installing = False` after `self._running = False`; in `_install_deps` add `self._installing = True` after `self._running = True`; in `_install_done` add `self._installing = False` after `self._running = False`.

d) `_build_header`, right after the Wav2Lip badge (`self._status_badge(badges, "Wav2Lip", ...).pack(side="left", padx=(0, 4))`):

```python
        # Integrated player: grey until the background status check reports
        # (_on_player_status); the tooltip gives the reason (spec 2.3).
        self._player_badge = self._status_badge(badges, self._s("player_badge"), FG2)
        self._player_badge.pack(side="left", padx=(8, 4))
        self._player_badge_dot, self._player_badge_label = self._player_badge.winfo_children()
        self._player_badge_tip = _HoverTip(self._player_badge, self._player_status_text,
                                           colors_fn=lambda: (SEL, FG))
```

e) `_build_ui`: replace the comment `# Left pane: reserved for the video player (backlog). Until it exists, a dark surface in the FIELD colour marks the area.` with `# Left pane: the integrated player (P1 shows its status and Install).`, and right after `self._player_area.pack(fill="both", expand=True)` add:

```python
        self._player_panel = _PlayerPanel(
            self._player_area, ui_s=self._s, make_button=self._flat_btn,
            on_command=self._on_player_command,
            logo_path=Path(__file__).resolve().parent / "assets" / "icon_256.png")
        self._player_panel.pack(fill="both", expand=True)
```

f) `_apply_lang`, right after `self._relabel_settings()`:

```python
        self._player_badge_label.configure(text=self._s("player_badge"))
        self._player_panel.relabel()
```

g) New methods, right after `_redirecting_thread_factory` (Task 1):

```python
    # -- Integrated player: availability and install (spec 9 P1) ------------

    def _player_log(self, line: str) -> None:
        """Log callback of the player modules: one English line without newline."""
        self._log_async(line + "\n")

    def _post_if_alive(self, fn) -> None:
        """Run ``fn`` on the Tk thread unless the window is closing.

        Called from worker threads. Tkinter raises RuntimeError ("main thread
        is not in main loop") once mainloop has ended during shutdown; the
        result is then dropped, as _TkStreamRedirect already does.
        """
        if not self._destroying:
            with contextlib.suppress(RuntimeError):
                self.after(0, fn)

    def _player_status_text(self) -> str:
        panel = getattr(self, "_player_panel", None)
        return panel.status_text() if panel is not None else self._s("player_badge")

    def _refresh_player_status(self, *, force_probe: bool = False) -> None:
        """Check libmpv and python-mpv on a worker. libmpv is never loaded here.

        quick_presence only looks for the files; the probe runs in a child
        process (a crashing library cannot take the app down) and only when
        the cached result does not match the library on disk, or after an
        install (plan decision 2).
        """
        cached = load_config().get("player_probe")

        def work():
            try:
                status = _libmpv_runtime.resolve_status(cached=cached, force_probe=force_probe)
                request = _system_packages.player_install_request(
                    status, sys_platform=sys.platform,
                    mpv_importable=importlib.util.find_spec("mpv") is not None)
            except Exception as exc:  # the badge must never stay grey without a reason
                status = _libmpv_runtime.LibmpvStatus(
                    ok=False, reason="probe-crashed", detail=f"status check failed: {exc}")
                request = _system_packages.PlayerInstallRequest()
            self._post_if_alive(lambda: self._on_player_status(status, request))

        self._redirecting_thread_factory(work, name="player-status").start()

    def _on_player_status(self, status, request) -> None:
        self._player_status = status
        self._player_install_request = request
        entry = _libmpv_runtime.cache_entry(status)
        if entry is not None and load_config().get("player_probe") != entry:
            save_config({"player_probe": entry})  # config writes stay on the Tk thread
        self._update_player_badge()
        if status.ok:
            self._player_panel.show_ready(status)
        else:
            self._player_panel.show_unavailable(status, install_cmd=request.manual_command)

    def _update_player_badge(self) -> None:
        level = _libmpv_runtime.badge_level(self._player_status) if self._player_status else None
        self._player_badge_dot.configure(fg={"ok": OK, "warn": WARN, "error": ERR}.get(level, FG2))

    def _on_player_command(self, name: str, args: dict) -> None:
        """Every PlayerPanel action arrives here (P2 adds the transport commands)."""
        if name == "install":
            self._install_player()

    def _install_player(self) -> None:
        if self._installing:
            messagebox.showerror(self._s("msg_error_t"), self._s("live_err_busy_install"),
                                 parent=self)
            return
        request = self._player_install_request
        if request is None or request.empty:
            self._refresh_player_status(force_probe=True)
            return
        windows_install = None
        if request.windows_dest is not None:
            question = self._s("player_install_confirm").format(size=request.download_mb)
            if not messagebox.askyesno(self._s("msg_confirm"), question, parent=self):
                return
            dest = request.windows_dest

            def windows_install():
                return _libmpv_runtime.install_windows(dest, log=self._player_log)

        self._installing = True
        self._player_panel.show_install_progress("installing")
        self._player_log("[*] Installing the integrated video player...")
        self._player_installer().install(
            pip_packages=request.pip_packages, system_plans=request.system_plans,
            windows_install=windows_install, expect_modules=("mpv",),
            on_done=self._on_player_install_done)

    def _player_installer(self):
        return _system_packages.ComponentInstaller(
            runner=lambda cmd: _system_packages.run_streaming(cmd, log=self._player_log),
            thread_factory=self._redirecting_thread_factory,
            find_spec=importlib.util.find_spec,
            refresh=_system_packages.refresh_import_paths,
            log=self._player_log,
            post=self._post_if_alive)

    def _on_player_install_done(self, result) -> None:
        self._installing = False
        if not result.ok:
            # The placeholder keeps the reason and, on Linux, the manual command.
            self._player_panel.show_install_progress("failed")
            self._player_log(f"[!] Player installation failed at step: {result.failed_step}")
            return
        self._player_panel.show_install_progress("ok")
        if result.restart_required:
            status = dataclasses.replace(
                self._player_status, ok=False, reason="restart-required",
                detail="installed, but not importable until the application restarts")
            self._on_player_status(status, _system_packages.PlayerInstallRequest())
            return
        self._refresh_player_status(force_probe=True)
```

- [ ] **Step 5: Run the tests on a private Xvfb**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
timeout 600 xvfb-run -a -s "-screen 0 1280x800x24" env PYTHONPATH=tests python3 -m unittest test_player_panel_tk test_ui_theme_tk test_ui_i18n_coverage test_import_hygiene -v 2>&1 | tail -30
```

Expected: all OK, no skips in `test_player_panel_tk`. Paste the summary lines into the task report (spec 9: Tk tests run under Xvfb, output recorded).

- [ ] **Step 6: Empirical GUI check on a private Xvfb (three states)**

Write the helper script into a fresh temp folder (never into the repo) and run it for each state. It builds the real `App` in-process (so it is closed deterministically, by object, never searched by window name), patches only the startup dependency installer and the yt-dlp upgrade, runs the real `mainloop()` (workers post with `after(0, ...)`, which Tkinter refuses unless the main thread is inside `mainloop`: an `update()` loop is not enough), waits for the player status, prints it, screenshots the Xvfb root window and destroys the app from a Tk callback.

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
REPO=$PWD
PROBE=$REPO/_dev/research/player-2026-09-25/probe
WORK=$(mktemp -d -t vtai-p1-gui-XXXX)
cat > "$WORK/p1_gui_check.py" <<'PYEOF'
import json, subprocess, sys, time
from pathlib import Path
from unittest import mock

repo, shot = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
import video_translator_gui as gui  # noqa: E402

with mock.patch.object(gui.App, "_check_deps_on_start", lambda self: None), \
        mock.patch.object(gui.App, "_upgrade_ytdlp_in_background", lambda self: None):
    app = gui.App()
    app.geometry("1100x780+0+0")
    deadline = time.monotonic() + 60

    def finish():
        status = app._player_status
        print(json.dumps({
            "reason": status.reason if status else None,
            "mpv_version": status.mpv_version if status else None,
            "vo_profiles_ok": status.vo_profiles_ok if status else None,
            "detail": status.detail if status else None,
            "badge_fg": app._player_badge_dot.cget("fg"),
            "palette": {"OK": gui.OK, "WARN": gui.WARN, "ERR": gui.ERR},
            "title": app._player_panel.title_label.cget("text"),
            "message": app._player_panel.message_label.cget("text"),
            "install_button_mapped": app._player_panel._install_wrap.winfo_ismapped() == 1,
        }, ensure_ascii=False, indent=1), flush=True)
        subprocess.run(["import", "-window", "root", str(shot)], check=True)
        app._destroying = True
        for after_id in app.tk.splitlist(app.tk.call("after", "info")):
            app.after_cancel(after_id)
        app.destroy()  # ends mainloop

    def poll():
        if app._player_status is None and time.monotonic() < deadline:
            app.after(100, poll)
        else:
            app.after(1000, finish)  # let the layout settle before the screenshot

    app.after(100, poll)
    app.mainloop()
PYEOF
# (a) this machine as it is: no libmpv, no python-mpv
env -u PYTHONPATH XDG_CONFIG_HOME="$WORK/cfg-a" timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" python3 "$WORK/p1_gui_check.py" "$REPO" "$WORK/p1-a-missing.png"
# (b) libmpv 0.41 available (unpacked), python-mpv missing
env -u PYTHONPATH XDG_CONFIG_HOME="$WORK/cfg-b" LD_LIBRARY_PATH="$PROBE/lib" VTAI_LIBMPV_DIR="$PROBE/lib" timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" python3 "$WORK/p1_gui_check.py" "$REPO" "$WORK/p1-b-pymod.png"
# (c) both available: ready, probed in a child process and cached
XDG_CONFIG_HOME="$WORK/cfg-c" LD_LIBRARY_PATH="$PROBE/lib" VTAI_LIBMPV_DIR="$PROBE/lib" PYTHONPATH="$PROBE/wheel" timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" python3 "$WORK/p1_gui_check.py" "$REPO" "$WORK/p1-c-ready.png"
# (c2) the same again: the cached probe is used (no second child probe)
XDG_CONFIG_HOME="$WORK/cfg-c" LD_LIBRARY_PATH="$PROBE/lib" VTAI_LIBMPV_DIR="$PROBE/lib" PYTHONPATH="$PROBE/wheel" timeout 180 xvfb-run -a -s "-screen 0 1280x800x24" python3 "$WORK/p1_gui_check.py" "$REPO" "$WORK/p1-c2-cached.png"
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['player_probe'])" "$WORK/cfg-c/videotranslatorai/config.json"
echo "screenshots in $WORK"
```

Expected (the UI language is the default of an empty config, Italian, unless a legacy config is copied in; check the facts, not the language):
- (a) `reason` `libmpv-missing`, `badge_fg` equal to `palette.WARN`, the message contains `sudo apt install libmpv2`, `install_button_mapped` true.
- (b) `reason` `python-mpv-missing`, `badge_fg` WARN, `install_button_mapped` true.
- (c) `reason` `ok`, `mpv_version` `[0, 41]`, `vo_profiles_ok` containing `x11egl` and `x11sw`, `badge_fg` equal to `palette.OK`, the message contains `mpv 0.41` and `(libmpv)`, `install_button_mapped` false; `player_probe` printed with the fingerprint of `libmpv.so.2.5.0`.
- (c2) the same result as (c).
- No run crashes, hangs or leaves a process behind (`timeout` would report 124).

Open each PNG with the Read tool and check: the left pane is black with the logo and the centred texts; the header shows the "Player" badge after Wav2Lip. Attach the four PNG paths and the four JSON outputs to the task report. Remove `$WORK` afterwards.

Layout note (observed while this plan was validated on a scratch copy): until Plan P0 lands, the left pane lives inside the scrolling form canvas and follows the height of the right column (spec 3.1), so it is taller than the window; the placeholder, centred in the pane as the spec asks, then sits partly below the visible area (the logo shows, the texts and Install need a scroll). This is the layout P0 fixes: record it in the task report and do not work around it in P1 (no top anchoring, no fixed logo size). If P0 has landed, the whole placeholder must be visible without scrolling at 1100x780.

- [ ] **Step 7: Full gate and commit**

```bash
unset DISPLAY WAYLAND_DISPLAY; cd /home/kali/Scrivania/PROGETTI_ATTIVI/VideoTranslatorAI
python3 -m py_compile video_translator_gui.py videotranslator/*.py
python3 -m unittest discover -s tests
timeout 900 xvfb-run -a -s "-screen 0 1280x800x24" python3 -m unittest discover -s tests 2>&1 | tail -5
grep -nP '[\x{2013}\x{2014}]' videotranslator/player_panel_tk.py video_translator_gui.py tests/test_player_panel_tk.py tests/test_ui_theme_tk.py tests/test_import_hygiene.py || echo "no long dashes"
git add videotranslator/player_panel_tk.py video_translator_gui.py tests/test_player_panel_tk.py tests/test_ui_theme_tk.py tests/test_import_hygiene.py
git commit -m "feat(player): show the player status in the header and the left pane

A Player badge in the header (grey, then green, amber or red with the
reason in a tooltip) and a placeholder in the left pane report whether
libmpv and python-mpv are usable. The status is computed on a worker:
quick_presence looks for the files and the libmpv probe runs in a child
process, cached by library fingerprint in player_probe. Install player
runs the pip part and the package manager (pkexec, then sudo -n) or the
per-user Windows download after confirmation, then re-probes: the player
becomes ready without a restart, or the placeholder says a restart is
needed. No playback yet (P2)."
```

- [ ] **Step 8: Record the phase in the dev changelog**

Append a `[player-p1]` section to `_dev/CHANGELOG.md` (gitignored, not committed): the eight commit hashes, the real-library outputs of Task 3 Step 5, the pip check of Task 5 Step 5, the diagnostics lines of Task 6 Step 7, the Xvfb results and screenshot paths of this task, the `PYANNOTE_PIN` quoting suspicion (plan decision 4) for the S4 run, and the operator items still open (list below).

---

## P1 acceptance map (spec 9, P1)

| Acceptance item (spec) | Where and how it is measured |
|---|---|
| `check --json` exits 2 on Kali without libmpv and 0 with libmpv2 + mpv, API (2, 5), `mpv_version` (0, 41), `vo_profiles_ok` with `x11egl` and `x11sw`, not `x11glx` | Task 3 Step 5 (unpacked 0.41 through `VTAI_LIBMPV_DIR`/`LD_LIBRARY_PATH`/`PYTHONPATH`, no system install) |
| a crashing fake DLL gives `probe-crashed` | Task 3 tests: fake runner with exit -11, timeout, and a real child that exits abnormally without JSON |
| clean Windows VM: `mpv-2.dll` + BUILD.txt, a second Repair skips the download, `check` exits 0 (S4 (1)) | Operator, Windows VM (spec S4 (1)); logic covered by Task 4 tests (idempotence, BUILD.txt fields) and Task 7 static tests |
| with the DLL removed the badge shows the reason | Operator on Windows; Linux equivalent in Task 8 Step 6 (a) and the Tk tests |
| Linux GUI install on a Debian 12 VM without libmpv: pkexec prompt, then ready without a restart; pkexec cancelled: the manual command stays | Operator, Debian 12 VM; flow covered by Task 5 and Task 8 tests (plans, fallback chain, failure keeps the command, re-probe) |
| pip part with a user site created during the run: `mpv` imports without a restart, or `player_restart_required`; never a crash | Task 5 Step 5 (real pip of the local wheel into a fresh `PYTHONUSERBASE`); restart path in the Task 8 Tk test |
| Windows per-user install from the pythonw shortcut: no console window, progress in the log | Operator, Windows 11; `no_window_kwargs` on every child (Tasks 1, 3, 4, 5 tests), output through `_redirecting_thread_factory` (Task 1 tests) |
| static tests: uninstall lists, requirement pins, `.gitignore` entries, no long dashes | Tasks 6 and 7 |
| the README third-party section matches the 8.4 list | Task 6 Step 6 (review checklist item for the Task 6 reviewer) |
| no path of the app crashes without the player (python-mpv uninstalled, libmpv absent) | Task 8 Step 6 (a) and (b) on Kali; operator on Windows |
| CI green | the full gate of every task; push only on operator request |

Operator items to hand over at the end (not runnable on this machine): the Windows 11 and VirtualBox runs of `setup_windows.bat` install and Repair (S4 (1), including the `PYANNOTE_PIN` quoting check), the Windows per-user install from the pythonw shortcut, the "DLL removed" badge on Windows, and the Debian 12 VM pkexec install with and without cancelling.
