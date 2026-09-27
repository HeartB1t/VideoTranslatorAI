"""Opt-in real libmpv smoke test for the file-player adapter.

Runs with VTAI_PLAYER_REAL=1 on an X11 display (Xvfb is enough). It needs
nothing outside a clean checkout but the player's own requirements: libmpv
with python-mpv, loaded the way the app loads them, and ffmpeg, which makes
the clip. The clip is video only, so the test never plays a sound. Once the
test is requested, a missing libmpv or ffmpeg fails it with the reason
instead of skipping it.
"""

import ctypes
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from videotranslator.player_engine import (
    EventBridge,
    VolumeMixer,
    X11ErrorGuard,
    create_video_backend,
    detect_vo_failure,
)


def _load_mpv():
    from videotranslator import libmpv_runtime
    return libmpv_runtime.load_mpv()       # PlayerUnavailable carries the reason


def _make_clip(folder: Path) -> Path:
    """Two seconds of test pattern, no audio track."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AssertionError("VTAI_PLAYER_REAL=1 needs ffmpeg on PATH to make the clip")
    clip = folder / "clip.mp4"
    subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=2",
                    "-an", "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p", str(clip)],
                   check=True, capture_output=True, timeout=60)
    return clip


@unittest.skipUnless(os.environ.get("VTAI_PLAYER_REAL") == "1",
                     "set VTAI_PLAYER_REAL=1 for the native libmpv smoke test")
class RealMpvSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.clip = _make_clip(Path(cls._tmp.name))

    @staticmethod
    def _close_with_tk_pump(root, backend):
        result = []
        started = time.monotonic()
        closer = threading.Thread(
            target=lambda: result.append(backend.terminate(2.0)), daemon=True,
        )
        closer.start()
        while closer.is_alive() and time.monotonic() - started < 2.5:
            root.update()
            time.sleep(0.01)
        closer.join(0.1)
        return result, time.monotonic() - started

    def test_embedded_load_seek_snapshot_and_bounded_terminate(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("an X11 display is required")
        import tkinter as tk

        mpv_module = _load_mpv()
        root = tk.Tk()
        root.geometry("640x400+0+0")
        host = tk.Frame(root, bg="#000000")
        host.pack(fill="both", expand=True)
        root.update()
        guard = X11ErrorGuard(load_libx11=lambda: ctypes.CDLL("libX11.so.6"))
        guard.capture()
        bridge = EventBridge()
        backend = create_video_backend(
            wid=host.winfo_id(), bridge=bridge, mixer=VolumeMixer(),
            vo_profile="x11sw", mpv_module=mpv_module, sys_platform="linux",
        )
        media = self.clip
        result = []
        try:
            backend.load(str(media), paused=True)
            deadline = time.monotonic() + 5.0
            loaded = False
            while time.monotonic() < deadline and not loaded:
                root.update()
                loaded = any(event.kind == "file-loaded"
                             for event in bridge.drain().events)
                time.sleep(0.01)
            self.assertTrue(loaded)
            backend.set_pause(False)
            backend.seek(0.2)
            with tempfile.TemporaryDirectory() as tmp:
                shot = Path(tmp) / "frame.png"
                backend.screenshot(str(shot))
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline and not shot.is_file():
                    root.update()
                    time.sleep(0.01)
                self.assertTrue(shot.is_file())

            result, elapsed = self._close_with_tk_pump(root, backend)
            self.assertEqual(result, [True])
            self.assertLess(elapsed, 2.0)
        finally:
            if result != [True]:
                backend.terminate(2.0)
            guard.restore()
            root.destroy()

    def test_forced_egl_failure_falls_back_and_tk_survives_x_error(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("an X11 display is required")
        import tkinter as tk

        mpv_module = _load_mpv()
        root = tk.Tk()
        root.geometry("640x400+0+0")
        host = tk.Frame(root, bg="#000000")
        host.pack(fill="both", expand=True)
        root.update()
        guard = X11ErrorGuard(load_libx11=lambda: ctypes.CDLL("libX11.so.6"))
        guard.capture()
        self.assertTrue(guard.captured)
        bridge = EventBridge()
        previous_egl = os.environ.get("__EGL_VENDOR_LIBRARY_FILENAMES")
        os.environ["__EGL_VENDOR_LIBRARY_FILENAMES"] = "/nonexistent/none.json"
        failed = create_video_backend(
            wid=host.winfo_id(), bridge=bridge, mixer=VolumeMixer(),
            vo_profile="x11egl", mpv_module=mpv_module, sys_platform="linux",
        )
        fallback = None
        failed_closed = False
        fallback_closed = False
        try:
            failed.load(str(self.clip), paused=True)
            lines = []
            deadline = time.monotonic() + 5.0
            detected = False
            while time.monotonic() < deadline and not detected:
                root.update()
                events = bridge.drain().events
                lines.extend(str(event.payload) for event in events if event.kind == "log")
                detected = detect_vo_failure(
                    lines, video_params_seen=False, has_video_track=True,
                    seconds_since_loaded=0.1,
                )
                time.sleep(0.01)
            self.assertTrue(detected)
            guard.restore()
            result, _elapsed = self._close_with_tk_pump(root, failed)
            self.assertEqual(result, [True])
            failed_closed = True
            guard.restore()

            fallback = create_video_backend(
                wid=host.winfo_id(), bridge=EventBridge(), mixer=VolumeMixer(),
                vo_profile="x11sw", mpv_module=mpv_module, sys_platform="linux",
            )
            fallback.load(str(self.clip), paused=True)
            for _ in range(20):
                root.update()
                time.sleep(0.01)
            result, _elapsed = self._close_with_tk_pump(root, fallback)
            self.assertEqual(result, [True])
            fallback_closed = True
            guard.restore()

            dead = tk.Frame(root, width=10, height=10)
            dead.place(x=0, y=0)
            root.update_idletasks()
            dead_wid = dead.winfo_id()
            dead.destroy()
            root.update()
            try:
                probe = tk.Toplevel(root, use=hex(dead_wid))
                probe.destroy()
            except tk.TclError:
                pass
            root.update()
            self.assertTrue(root.winfo_exists())
        finally:
            if fallback is not None and not fallback_closed:
                self._close_with_tk_pump(root, fallback)
            if not failed_closed:
                self._close_with_tk_pump(root, failed)
            guard.restore()
            if previous_egl is None:
                os.environ.pop("__EGL_VENDOR_LIBRARY_FILENAMES", None)
            else:
                os.environ["__EGL_VENDOR_LIBRARY_FILENAMES"] = previous_egl
            root.destroy()


if __name__ == "__main__":
    unittest.main()
