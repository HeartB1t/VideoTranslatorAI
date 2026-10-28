"""Window setup and dependency installers (mixin of ``video_translator_gui.App``).

Host-module globals are read through ``_g`` (see ``app_host``).
"""

from .app_host import host as _g


class SetupMixin:
    def _set_window_icon(self) -> None:
        """Set the window icon from the bundled assets folder.

        Gracefully falls back to the default Tk icon if assets/ is missing or
        the image cannot be loaded - common e.g. when the GUI is launched
        from a source checkout without the assets committed yet.
        """
        here = _g.Path(_g.__file__).resolve().parent
        assets = _g._assets_dir()
        candidates_ico = [assets / "icon.ico", here / "icon.ico"]
        candidates_png = [assets / "icon.png",
                          assets / "icon_256.png",
                          here / "icon.png"]

        # Windows honours .ico best via iconbitmap
        if _g.sys.platform.startswith("win"):
            for p in candidates_ico:
                if p.exists():
                    try:
                        self.iconbitmap(default=str(p))
                        return
                    except _g.tk.TclError:
                        pass

        # Cross-platform fallback: iconphoto with a PNG (requires PhotoImage)
        for p in candidates_png:
            if p.exists():
                try:
                    img = _g.tk.PhotoImage(file=str(p))
                    self.iconphoto(True, img)
                    # Keep a reference to prevent GC
                    self._icon_img = img
                    return
                except _g.tk.TclError:
                    continue

    def _fit_to_screen(self):
        self.update_idletasks()
        # Center on the monitor the window opens on (the one under the pointer),
        # not the middle of the whole virtual desktop, which on a multi-monitor
        # setup straddles two screens or lands on the wrong one.
        full = (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
        try:
            px, py = self.winfo_pointerxy()
        except _g.tk.TclError:
            px, py = full[2] // 2, full[3] // 2
        mx, my, mw, mh = _g._platforms.monitor_bounds_at(px, py, fallback=full)
        # Prefer the explicit geometry hint (1100x780) over reqsize, because the
        # form lives inside a Canvas-wrapped frame and reqwidth from the Canvas
        # under-reports the form's actual width. Clamp to this monitor, floor at
        # a usable minimum (matches `self.minsize`) unless the monitor is smaller.
        win_w = min(max(1100, self.winfo_reqwidth()), mw - 40)
        win_w = max(win_w, min(900, mw - 40))
        win_h = min(max(780, self.winfo_reqheight()), mh - 80)
        win_h = max(win_h, min(600, mh - 80))
        x = mx + max(0, (mw - win_w) // 2)
        y = my + max(0, (mh - win_h) // 2 - 20)
        # Center first so the window sits on the right monitor, keeping this as
        # the restore size, then maximize to fill THAT screen.
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.update_idletasks()
        self._maximize_window((mx, my, mw, mh))

    def _maximize_window(self, bounds) -> None:
        """Expand to fill the current monitor, cross-platform.

        On Windows ``state("zoomed")`` maximizes and keeps the taskbar visible.
        On X11 the ``-zoomed`` hint is unreliable (xfwm4 accepts it silently
        without maximizing), so the window is sized to the monitor explicitly,
        which always works and stays on the screen it was centered on.

        Note (review S1): the explicit geometry uses the full xrandr rect, so on
        X11 the window can sit under the desktop panel. Letting the WM maximize
        via ``-zoomed`` after the window is mapped would respect the panel, but
        that needs verification on a real WM (Xvfb reports -zoomed applied while
        not resizing), so it is deferred to an operator check to avoid regressing
        the accepted fill behavior.
        """
        try:
            self.state("zoomed")
            return
        except _g.tk.TclError:
            pass
        mx, my, mw, mh = bounds
        self.geometry(f"{mw}x{mh}+{mx}+{my}")

    # ── Dependency check ─────────────────────────────────────────────────────

    def _check_deps_on_start(self):
        missing_pkgs, missing_bins = _g.check_dependencies()
        if not missing_pkgs and not missing_bins:
            # Nothing required to install - safe to check optional now
            self.after(300, self._check_optional_deps)
            return
        if missing_pkgs and not _g._system_packages.python_supported():
            # The pinned torch has no wheels for this interpreter: pip would
            # fail twice (demucs build, "no matching distribution: torch") and
            # the log would hide the cause. Say it, and offer the interpreter
            # on this PC that has torch.
            self._explain_unsupported_python(missing_pkgs)
            return
        # Serialize: install ffmpeg first, then pip packages in _ffmpeg_done callback
        self._pending_pkgs_after_ffmpeg = missing_pkgs
        if missing_bins:
            self._install_ffmpeg()
        elif missing_pkgs:
            self._install_deps(missing_pkgs)

    def _explain_unsupported_python(self, missing: list[str]) -> None:
        """Tk thread: this Python is outside the pinned torch's range and no
        supported interpreter was found before the window opened
        (system_packages.relaunch_on_unsupported_python): say what to install."""
        version = f"{_g.sys.version_info[0]}.{_g.sys.version_info[1]}"
        text = self._s("msg_python_unsupported").format(
            version=version, torch=_g._system_packages.TORCH_RANGE_LABEL,
            supported=_g._system_packages.PYTHON_RANGE_LABEL)
        self._log_line("app", text)
        self._log_line("app", f"missing: {', '.join(missing)}; no pip install attempted")
        _g.messagebox.showwarning(
            "Python", text + "\n\n" + self._s("msg_python_none").format(
                supported=_g._system_packages.PYTHON_RANGE_LABEL), parent=self)

    def _relaunch_note(self, environ=None) -> str | None:
        """The log line for a start that was relaunched from an unsupported Python."""
        came_from = (_g.os.environ if environ is None else environ).get(_g._system_packages.RELAUNCH_ENV)
        if not came_from:
            return None
        return self._s("msg_python_relaunched").format(
            version=came_from, torch=_g._system_packages.TORCH_RANGE_LABEL, python=_g.sys.executable)

    def _install_ffmpeg(self):
        self._running = True
        self._installing = True
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write("[*] ffmpeg not found - installing automatically...\n")

        def do():
            ok = False
            if _g.sys.platform == "win32":
                ok = self._install_ffmpeg_windows()
            else:
                ok = self._install_ffmpeg_linux()
            self.after(0, self._ffmpeg_done, ok)

        _g.threading.Thread(target=do, daemon=True).start()

    def _install_ffmpeg_linux(self) -> bool:
        # Detect package manager
        for mgr, update_cmd, install_cmd in [
            ("apt-get", ["apt-get", "update"], ["apt-get", "install", "-y", "ffmpeg"]),
            ("dnf",     ["dnf",     "makecache"], ["dnf", "install", "-y", "ffmpeg"]),
            ("pacman",  ["pacman",  "-Sy"],     ["pacman", "-S", "--noconfirm", "ffmpeg"]),
        ]:
            if not _g.shutil.which(mgr):
                continue
            # Try pkexec first (graphical sudo), fall back to sudo
            for prefix in (["pkexec"], ["sudo", "-n"], ["sudo"]):
                # Step 1: update package cache
                update = prefix + update_cmd
                self.after(0, self._log_write, f"    Running: {' '.join(update)}\n")
                with _g.subprocess.Popen(
                    update, stdout=_g.subprocess.PIPE, stderr=_g.subprocess.STDOUT,
                    stdin=_g.subprocess.DEVNULL, text=True,
                    encoding="utf-8", errors="replace",
                ) as proc:
                    try:
                        for line in proc.stdout:
                            line = line.rstrip()
                            if line:
                                self.after(0, self._log_write, f"    {line}\n")
                        proc.wait()
                    except Exception:
                        proc.kill(); proc.wait()
                    rc_update = proc.returncode
                if rc_update != 0:
                    continue  # try next prefix (stdout already closed by context manager)
                # Step 2: install ffmpeg
                full_cmd = prefix + install_cmd
                self.after(0, self._log_write, f"    Running: {' '.join(full_cmd)}\n")
                with _g.subprocess.Popen(
                    full_cmd, stdout=_g.subprocess.PIPE, stderr=_g.subprocess.STDOUT,
                    stdin=_g.subprocess.DEVNULL, text=True,
                    encoding="utf-8", errors="replace",
                ) as proc:
                    try:
                        for line in proc.stdout:
                            line = line.rstrip()
                            if line:
                                self.after(0, self._log_write, f"    {line}\n")
                        proc.wait()
                    except Exception:
                        proc.kill(); proc.wait()
                    rc_install = proc.returncode
                if rc_install == 0:
                    return True
        return False

    def _install_ffmpeg_windows(self) -> bool:
        import hashlib
        import urllib.request
        import zipfile
        import ctypes
        from videotranslator.libmpv_runtime import sha256_from_checksums
        # Download ffmpeg essentials build from GitHub releases
        release_url = "https://github.com/BtbN/ffmpeg-builds/releases/download/latest"
        zip_name    = "ffmpeg-master-latest-win64-gpl.zip"
        ffmpeg_url  = f"{release_url}/{zip_name}"
        install_dir = _g.Path.home() / ".local" / "bin" / "ffmpeg"
        install_dir.mkdir(parents=True, exist_ok=True)
        zip_path    = install_dir / "ffmpeg.zip"

        self.after(0, self._log_write, "    Downloading ffmpeg (~200 MB)...\n")
        try:
            # Stream download via urlopen + copyfileobj so we can enforce a
            # per-read timeout. urlretrieve has no timeout knob and will hang
            # indefinitely on a slow/stalled mirror.
            from urllib.request import Request, urlopen
            headers = {"User-Agent": "VideoTranslatorAI/1.0"}
            # "latest" is rebuilt daily: its digest comes from the same release.
            with urlopen(Request(f"{release_url}/checksums.sha256", headers=headers),
                         timeout=60) as r:
                expected = sha256_from_checksums(
                    r.read(1 << 20).decode("utf-8", "replace"), zip_name)
            if not expected:
                raise RuntimeError(f"no published SHA256 for {zip_name}")
            digest = hashlib.sha256()
            downloaded = 0
            with urlopen(Request(ffmpeg_url, headers=headers), timeout=120) as r, \
                    open(zip_path, "wb") as out:
                total = int(r.headers.get("Content-Length") or 0)
                chunk = 64 * 1024
                while True:
                    buf = r.read(chunk)
                    if not buf:
                        break
                    out.write(buf)
                    digest.update(buf)
                    downloaded += len(buf)
                    if total > 0:
                        pct = min(100, downloaded * 100 // total)
                        self.after(0, self._log_write, f"\r    Downloading... {pct}%")
            if digest.hexdigest() != expected:
                raise RuntimeError(f"{zip_name} does not match its published SHA256")
            self.after(0, self._log_write, "\n    Extracting...\n")
            install_dir_resolved = install_dir.resolve()
            with zipfile.ZipFile(zip_path, "r") as z:
                for member in z.namelist():
                    if member.endswith(("ffmpeg.exe", "ffprobe.exe")):
                        # Guard against zip slip
                        # NOTE: Path.is_relative_to() requires Python 3.9+
                        member_resolved = (install_dir / member).resolve()
                        if not member_resolved.is_relative_to(install_dir_resolved):
                            continue
                        z.extract(member, install_dir)
                        src = install_dir / member
                        dst = install_dir / _g.Path(member).name
                        if src != dst:
                            _g.shutil.move(str(src), str(dst))
            zip_path.unlink(missing_ok=True)
            # Add to user PATH via registry
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
            try:
                old_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                old_path = ""
            if str(install_dir) not in old_path:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ,
                                  old_path + ";" + str(install_dir))
            winreg.CloseKey(key)
            _g.os.environ["PATH"] += _g.os.pathsep + str(install_dir)
            return True
        except Exception as e:
            zip_path.unlink(missing_ok=True)
            self.after(0, self._log_write, f"    ! ffmpeg download failed: {e}\n")
            return False

    def _ffmpeg_done(self, ok: bool):
        self._running = False
        self._installing = False
        self._progress.stop()
        if ok:
            self._log_write("[✓] ffmpeg installed successfully.\n")
        else:
            self._log_write(
                "[✗] Could not install ffmpeg automatically.\n"
                "    Linux:   sudo apt install ffmpeg\n"
                "    Windows: https://ffmpeg.org/download.html\n"
            )
        # Chain: install pending Python packages now that ffmpeg is done
        pending = self._pending_pkgs_after_ffmpeg
        self._pending_pkgs_after_ffmpeg = []
        if pending:
            self._install_deps(pending)
        else:
            self._btn.configure(state="normal", text=self._s("btn_start"))
            self.after(300, self._check_optional_deps)

    def _install_deps(self, packages):
        self._running = True
        self._installing = True
        self._btn.configure(state="disabled", text=self._s("btn_installing"))
        self._progress.start(12)
        self._log_write(f"[*] Installing: {', '.join(packages)}\n")

        def do():
            # Profiles as constraints: this install cannot upgrade the tested
            # torch, numpy or transformers (system_packages.pip_install_command).
            cmd = _g._system_packages.pip_install_command(_g.sys.executable, packages)
            # encoding="utf-8" + errors="replace" is critical on Windows:
            # without it, text=True falls back to locale.getpreferredencoding()
            # (cp1252 on Italian/English installs) and pip's tqdm progress bars
            # or non-ASCII package URLs trigger UnicodeDecodeError mid-install.
            # stdin=DEVNULL avoids inheriting a None stdin from pythonw.exe
            # on Windows (the GUI launcher has no console).
            proc = _g.subprocess.Popen(
                cmd, stdout=_g.subprocess.PIPE, stderr=_g.subprocess.STDOUT,
                stdin=_g.subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace",
            )
            _g._register_subprocess(proc)
            ok = True
            # 10-minute ceiling: covers large Torch wheels on slow mirrors
            # without letting the GUI freeze forever if pip stalls.
            # NB: proc.wait(timeout=…) does not fire if pip stalls without
            # closing stdout, because the for-loop on proc.stdout blocks there.
            # A Timer that kills the process guarantees the unblock (the
            # stdout iterator raises or returns EOF as soon as the process dies).
            PIP_TIMEOUT = 600
            timed_out = {"fired": False}

            def _on_timeout():
                timed_out["fired"] = True
                with _g.contextlib.suppress(Exception):
                    proc.kill()
                # On Windows, TerminateProcess does not always unblock a
                # pending read on the child's stdout pipe immediately -
                # close our end so the for-loop wakes up even if the OS
                # is slow to tear down the pipe.
                with _g.contextlib.suppress(Exception):
                    if proc.stdout is not None:
                        proc.stdout.close()

            watchdog = _g.threading.Timer(PIP_TIMEOUT, _on_timeout)
            watchdog.daemon = True
            watchdog.start()
            try:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.after(0, self._log_write, f"    {line}\n")
                with _g.contextlib.suppress(Exception):
                    proc.wait(timeout=30)
                if timed_out["fired"]:
                    self.after(0, self._log_write,
                               f"    ! pip install timed out after {PIP_TIMEOUT}s - aborting.\n")
                    ok = False
                else:
                    ok = proc.returncode == 0
            except Exception:
                # If the timeout watchdog closed stdout the iterator raises
                # here - still print the timeout message so the user sees the
                # cause instead of a generic "Installation failed".
                if timed_out["fired"]:
                    self.after(0, self._log_write,
                               f"    ! pip install timed out after {PIP_TIMEOUT}s - aborting.\n")
                with _g.contextlib.suppress(Exception):
                    proc.kill()
                    proc.wait(timeout=30)
                ok = False
            finally:
                watchdog.cancel()
                _g._unregister_subprocess(proc)
            self.after(0, self._install_done, ok, packages)

        _g.threading.Thread(target=do, daemon=True).start()

    def _install_done(self, ok, packages):
        self._running = False
        self._installing = False
        self._progress.stop()
        self._btn.configure(state="normal", text=self._s("btn_start"))
        if ok:
            self._log_write(f"[✓] Installed: {', '.join(packages)}\n")
        else:
            self._log_write("[✗] Installation failed. Check the log above for details.\n")
        # Required install chain finished - safe to check optional packages now
        self.after(300, self._check_optional_deps)

    def _upgrade_ytdlp_in_background(self):
        """Silently upgrade yt-dlp in a daemon thread; logs only if a new version is installed.

        Respects the `yt_dlp_auto_upgrade` flag in config (default True). If the user
        sets it to False (e.g. on PEP 668 systems where they do not want the env
        modified), the upgrade is skipped silently.
        """
        # Check user consent via config flag (default: enabled for backwards compat)
        try:
            _cfg = _g.load_config()
        except Exception:
            _cfg = {}
        if not _cfg.get("yt_dlp_auto_upgrade", True):
            return  # user opted out

        import re as _re

        def do():
            try:
                result = _g.subprocess.run(
                    [_g.sys.executable, "-m", "pip", "install", "--upgrade",
                     "--break-system-packages", "--no-color",
                     *_g._system_packages.pip_constraint_args(), "yt-dlp"],
                    stdout=_g.subprocess.PIPE, stderr=_g.subprocess.STDOUT, text=True,
                    timeout=120,
                )
                for line in (result.stdout or "").splitlines():
                    if "Successfully installed" in line:
                        # m3: regex that avoids a trailing dot (e.g. "yt-dlp-2024.10.")
                        m = _re.search(r"yt[-_]dlp-([0-9]+(?:\.[0-9]+)+)", line)
                        if m and not self._destroying:
                            self.after(0, self._log_write,
                                       f"[✓] yt-dlp aggiornato a {m.group(1)}\n")
                        break
            except Exception:
                pass  # upgrade failure is non-fatal

        _g.threading.Thread(target=do, daemon=True).start()

    def _check_optional_deps(self):
        """Show one-time popup if optional packages are missing; let user choose to install."""
        if self._optional_checked:
            return
        self._optional_checked = True

        # TASK 2C-2: non-blocking hint for Rubber Band CLI on Linux.
        # It is a system binary (apt/dnf/pacman), not installable via pip,
        # so it does not belong in the OPTIONAL_PACKAGES popup. Log only:
        # if missing, build_dubbed_track will still use atempo (no regression).
        if _g.sys.platform.startswith("linux") and _g.shutil.which("rubberband") is None:
            self._log_write(
                "[i] Optional: install Rubber Band CLI for higher-quality "
                "audio stretching in the 1.15-1.50 ratio band:\n"
                "    sudo apt install rubberband-cli  "
                "(or your distro equivalent)\n"
            )

        def _is_present(mod: str) -> bool:
            aliases = _g._OPTIONAL_ALIASES.get(mod, [mod])
            return any(_g.importlib.util.find_spec(a) is not None for a in aliases)

        missing = [
            (mod, pip_pkgs, desc)
            for mod, (pip_pkgs, desc) in _g.OPTIONAL_PACKAGES.items()
            if not _is_present(mod)
        ]
        if not missing:
            return

        # Deduplicate by primary pip package name; collect all requirements to install
        seen: set[str] = set()
        items: list[tuple[list[str], str]] = []
        for _mod, pip_pkgs, desc in missing:
            key = pip_pkgs[0]
            if key not in seen:
                seen.add(key)
                items.append((pip_pkgs, desc))

        names_str = "\n".join(f"  • {pkgs[0]} - {desc}" for pkgs, desc in items)
        answer = _g.messagebox.askyesno(
            "Pacchetti opzionali mancanti",
            f"I seguenti pacchetti opzionali non sono installati:\n\n{names_str}\n\n"
            "Vuoi installarli adesso? (operazione in background)",
            parent=self,
        )
        if answer:
            all_pkgs = [pkg for pkgs, _ in items for pkg in pkgs]
            self._install_deps(all_pkgs)
        else:
            self._log_write("[i] Pacchetti opzionali saltati. Puoi installarli manualmente.\n")
