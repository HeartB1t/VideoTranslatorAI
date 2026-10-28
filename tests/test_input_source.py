import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.input_source import (
    build_ytdlp_audio_options,
    build_ytdlp_options,
    download_audio_url,
    download_url,
    emit_download_warnings,
    is_probable_url,
    normalize_input_path,
    resolve_downloaded_filename,
    resolve_stream_url,
)


class InputSourceTests(unittest.TestCase):
    def test_build_ytdlp_options_contains_project_policy(self):
        with mock.patch(
            "videotranslator.js_runtime.resolve_js_runtimes", return_value=None
        ):
            opts = build_ytdlp_options("/tmp/videos")

        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertTrue(opts["noplaylist"])
        self.assertIn("player_client", opts["extractor_args"]["youtube"])
        clients = opts["extractor_args"]["youtube"]["player_client"]
        self.assertEqual(clients[0], "default")
        self.assertIn("tv", clients)
        self.assertIn("android_vr", clients)
        self.assertLess(clients.index("tv"), clients.index("android_vr"))
        self.assertIn("%(title).80s.%(ext)s", opts["outtmpl"])
        self.assertNotIn("js_runtimes", opts)

    def test_build_ytdlp_options_injects_js_runtimes(self):
        opts = build_ytdlp_options(
            "/tmp/videos", js_runtimes={"node": {"path": "/usr/bin/node"}}
        )

        self.assertEqual(opts["js_runtimes"], {"node": {"path": "/usr/bin/node"}})

    def test_resolve_downloaded_filename_returns_existing_prepared_file(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            path = Path(tmp_str) / "video.webm"
            path.write_bytes(b"x")

            self.assertEqual(resolve_downloaded_filename(path), str(path))

    def test_resolve_downloaded_filename_finds_merged_mp4(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            prepared = Path(tmp_str) / "video.webm"
            merged = Path(tmp_str) / "video.mp4"
            merged.write_bytes(b"x")

            self.assertEqual(resolve_downloaded_filename(prepared), str(merged))

    def test_resolve_downloaded_filename_raises_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            with self.assertRaises(RuntimeError):
                resolve_downloaded_filename(Path(tmp_str) / "missing.webm")

    def test_url_and_path_helpers(self):
        self.assertTrue(is_probable_url("https://youtu.be/example"))
        self.assertFalse(is_probable_url("~/Videos/input.mp4"))
        self.assertTrue(normalize_input_path("~/Videos/input.mp4")
                        .endswith(os.path.join("Videos", "input.mp4")))

    def test_download_url_uses_injected_ytdlp_and_logs_final_path(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            final = Path(tmp_str) / "clip.mp4"
            logs: list[str] = []
            seen_opts = {}

            class FakeYoutubeDL:
                def __init__(self, opts):
                    seen_opts.update(opts)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return None

                def extract_info(self, url, download):
                    self.url = url
                    self.download = download
                    final.write_bytes(b"x")
                    return {"title": "clip"}

                def prepare_filename(self, info):
                    return str(Path(tmp_str) / "clip.webm")

            # Keep the test hermetic: never resolve/install a real JS runtime.
            with mock.patch(
                "videotranslator.js_runtime.ensure_js_runtime", return_value=None
            ), mock.patch(
                "videotranslator.js_runtime.resolve_js_runtimes", return_value=None
            ):
                result = download_url(
                    "https://youtu.be/example",
                    tmp_str,
                    ytdlp_cls=FakeYoutubeDL,
                    log_cb=logs.append,
                )

        self.assertEqual(result, str(final))
        self.assertEqual(seen_opts["merge_output_format"], "mp4")
        # Final download line is the contract.
        self.assertEqual(logs[-1], f"[+] Downloaded: {final}")
        # the anti-bot / VPN advice appears only after a bot-block error
        self.assertFalse(any("anti-bot" in line for line in logs))

    def _fake_ydl(self, info):
        captured = {}

        class FakeYoutubeDL:
            def __init__(self, opts):
                captured["opts"] = opts

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def extract_info(self, url, download):
                captured["url"] = url
                captured["download"] = download
                return info

        return FakeYoutubeDL, captured

    def _resolve(self, info, **kw):
        cls, captured = self._fake_ydl(info)
        with mock.patch(
            "videotranslator.js_runtime.ensure_js_runtime", return_value=None
        ):
            result = resolve_stream_url("https://youtu.be/x", ytdlp_cls=cls, **kw)
        return result, captured

    def test_resolve_stream_url_uses_selected_progressive_format(self):
        info = {"title": "Song", "url": "https://cdn/prog.mp4",
                "acodec": "mp4a", "vcodec": "avc1"}
        (url, title), captured = self._resolve(info)
        self.assertEqual(url, "https://cdn/prog.mp4")
        self.assertEqual(title, "Song")
        self.assertFalse(captured["download"])           # never downloads
        self.assertIn("acodec!=none", captured["opts"]["format"])

    def test_resolve_stream_url_scans_formats_for_tallest_muxed(self):
        info = {"title": "Clip", "formats": [
            {"url": "a", "acodec": "aac", "vcodec": "none", "height": 0},     # audio only
            {"url": "v", "acodec": "none", "vcodec": "avc1", "height": 1080},  # video only
            {"url": "sd", "acodec": "aac", "vcodec": "avc1", "height": 360},
            {"url": "hd", "acodec": "aac", "vcodec": "avc1", "height": 720},
        ]}
        (url, _title), _ = self._resolve(info, max_height=720)
        self.assertEqual(url, "hd")

    def test_resolve_stream_url_respects_max_height(self):
        info = {"title": "Clip", "formats": [
            {"url": "sd", "acodec": "aac", "vcodec": "avc1", "height": 360},
            {"url": "hd", "acodec": "aac", "vcodec": "avc1", "height": 1080},
        ]}
        (url, _title), _ = self._resolve(info, max_height=480)
        self.assertEqual(url, "sd")

    def test_resolve_stream_url_uses_first_playlist_entry(self):
        info = {"entries": [
            None,
            {"title": "First", "url": "https://cdn/first.mp4",
             "acodec": "aac", "vcodec": "avc1"},
        ]}
        (url, title), _ = self._resolve(info)
        self.assertEqual(url, "https://cdn/first.mp4")
        self.assertEqual(title, "First")

    def test_resolve_stream_url_raises_without_a_stream(self):
        with self.assertRaises(RuntimeError):
            self._resolve({"title": "x", "formats": []})

    def test_resolve_stream_url_rejects_a_video_only_top_url(self):
        # A known video-only top URL must not pass (it would play muted and make
        # the live audio decoder fail with a cryptic IndexError).
        info = {"title": "x", "url": "https://cdn/videoonly.m4s",
                "acodec": "none", "vcodec": "avc1"}
        with self.assertRaises(RuntimeError):
            self._resolve(info)

    def test_resolve_stream_url_passes_a_direct_url_without_codec_metadata(self):
        # A direct media link often carries no codec info; it must still pass.
        info = {"title": "Direct", "url": "https://cdn/clip.mp4"}
        (url, _title), _ = self._resolve(info)
        self.assertEqual(url, "https://cdn/clip.mp4")

    def test_emit_download_warnings_is_noop_without_callback(self):
        # Must not raise when there is no log sink.
        emit_download_warnings(None)

    def test_advice_follows_the_real_error(self):
        from videotranslator.input_source import emit_download_advice
        cases = (
            ("ERROR: Sign in to confirm you're not a bot", "VPN"),
            ("HTTP Error 429: Too Many Requests", "VPN"),
            ("ERROR: unable to download video data: HTTP Error 403: Forbidden", "VPN"),
            ("ERROR: Join this channel to get access to members-only content", "members"),
            ("ERROR: Video unavailable", None),
        )
        for message, expected in cases:
            logs: list[str] = []
            emit_download_advice(RuntimeError(message), logs.append)
            if expected is None:
                self.assertEqual(logs, [], message)
            else:
                self.assertTrue(any(expected in line for line in logs), message)
                if expected == "members":
                    self.assertFalse(any("switching IP" in line for line in logs))

    def test_no_vpn_advice_before_a_download_that_works(self):
        class _Ydl:
            def __init__(self, opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def extract_info(self, url, download):
                return {"title": "T", "url": "https://cdn/x.mp4", "acodec": "aac",
                        "vcodec": "h264"}
        logs: list[str] = []
        with mock.patch("videotranslator.js_runtime.ensure_js_runtime", return_value={}):
            resolve_stream_url("https://youtu.be/x", ytdlp_cls=_Ydl, log_cb=logs.append)
        self.assertFalse(any("VPN" in line for line in logs))

    def test_emit_download_warnings_advises_on_vpn(self):
        logs: list[str] = []
        emit_download_warnings(logs.append)

        self.assertTrue(any("VPN" in line for line in logs))


class AudioDownloadTests(unittest.TestCase):
    def test_build_ytdlp_audio_options_requests_bestaudio_without_mp4_merge(self):
        with mock.patch(
            "videotranslator.js_runtime.resolve_js_runtimes", return_value=None
        ):
            opts = build_ytdlp_audio_options("/tmp/videos")

        self.assertEqual(opts["format"], "bestaudio/best")
        self.assertNotIn("merge_output_format", opts)
        # The rest of the project's policy is preserved.
        self.assertTrue(opts["noplaylist"])
        self.assertTrue(opts["restrictfilenames"])
        self.assertIn("%(title).80s.%(ext)s", opts["outtmpl"])

    def test_build_ytdlp_audio_options_injects_js_runtimes(self):
        opts = build_ytdlp_audio_options(
            "/tmp/videos", js_runtimes={"node": {"path": "/usr/bin/node"}}
        )
        self.assertEqual(opts["js_runtimes"], {"node": {"path": "/usr/bin/node"}})

    def test_resolve_downloaded_filename_finds_audio_extension(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            prepared = Path(tmp_str) / "track.webm"
            audio = Path(tmp_str) / "track.m4a"
            audio.write_bytes(b"x")

            self.assertEqual(
                resolve_downloaded_filename(
                    prepared, extensions=(".m4a", ".opus", ".mp3")),
                str(audio),
            )

    def test_download_audio_url_uses_injected_ytdlp_and_returns_path(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            final = Path(tmp_str) / "track.m4a"
            logs: list[str] = []
            seen_opts: dict = {}

            class FakeYoutubeDL:
                def __init__(self, opts):
                    seen_opts.update(opts)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return None

                def extract_info(self, url, download):
                    final.write_bytes(b"x")
                    return {"title": "track"}

                def prepare_filename(self, info):
                    return str(Path(tmp_str) / "track.webm")

            with mock.patch(
                "videotranslator.js_runtime.ensure_js_runtime", return_value=None
            ), mock.patch(
                "videotranslator.js_runtime.resolve_js_runtimes", return_value=None
            ):
                result = download_audio_url(
                    "https://youtu.be/example",
                    tmp_str,
                    ytdlp_cls=FakeYoutubeDL,
                    log_cb=logs.append,
                )

            self.assertEqual(result, str(final))
            self.assertEqual(seen_opts["format"], "bestaudio/best")
            self.assertNotIn("merge_output_format", seen_opts)
            self.assertTrue(any(str(final) in line for line in logs))

    def test_download_audio_url_emits_advice_then_reraises(self):
        class FailingYoutubeDL:
            def __init__(self, opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def extract_info(self, url, download):
                raise RuntimeError("Sign in to confirm you're not a bot")

        logs: list[str] = []
        with mock.patch(
            "videotranslator.js_runtime.ensure_js_runtime", return_value=None
        ):
            with self.assertRaises(RuntimeError):
                download_audio_url(
                    "https://youtu.be/x", "/tmp",
                    ytdlp_cls=FailingYoutubeDL, log_cb=logs.append)
        self.assertTrue(any("VPN" in line for line in logs))


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


class DetectBrowserTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def detect(self, platform, env=None):
        from videotranslator.input_source import _detect_browser

        return _detect_browser(platform, env or {}, self.home)

    def test_nothing_found_without_a_cookie_database(self):
        (self.home / ".config" / "google-chrome").mkdir(parents=True)
        (self.home / ".mozilla" / "firefox" / "abc.default").mkdir(parents=True)
        self.assertIsNone(self.detect("linux"))

    def test_linux_firefox_profile_is_found(self):
        _touch(self.home / ".mozilla" / "firefox" / "abc.default" / "cookies.sqlite")
        self.assertEqual(self.detect("linux"), ("firefox",))

    def test_linux_snap_firefox_and_xdg_chromium(self):
        _touch(self.home / "snap" / "firefox" / "common" / ".mozilla" / "firefox"
               / "x.default" / "cookies.sqlite")
        self.assertEqual(self.detect("linux"), ("firefox",))

    def test_linux_xdg_config_home_is_honoured(self):
        xdg = self.home / "xdg"
        _touch(xdg / "chromium" / "Default" / "Cookies")
        self.assertEqual(self.detect("linux", {"XDG_CONFIG_HOME": str(xdg)}), ("chromium",))

    def test_windows_browsers_are_found_by_profile_not_by_path(self):
        local, roaming = self.home / "Local", self.home / "Roaming"
        env = {"LOCALAPPDATA": str(local), "APPDATA": str(roaming)}
        _touch(local / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies")
        self.assertEqual(self.detect("win32", env), ("edge",))
        _touch(roaming / "Mozilla" / "Firefox" / "Profiles" / "p.default" / "cookies.sqlite")
        self.assertEqual(self.detect("win32", env), ("firefox",))

    def test_chrome_comes_after_the_other_chromium_browsers(self):
        local = self.home / "Local"
        env = {"LOCALAPPDATA": str(local), "APPDATA": str(self.home / "Roaming")}
        _touch(local / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies")
        self.assertEqual(self.detect("win32", env), ("chrome",))
        _touch(local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cookies")
        self.assertEqual(self.detect("win32", env), ("brave",))

    def test_macos_profile_is_found(self):
        _touch(self.home / "Library" / "Application Support" / "Vivaldi" / "Default" / "Cookies")
        self.assertEqual(self.detect("darwin"), ("vivaldi",))

    def test_only_browsers_yt_dlp_supports_are_returned(self):
        from videotranslator.input_source import _browser_profile_roots

        supported = {"brave", "chrome", "chromium", "edge", "opera", "vivaldi", "whale",
                     "firefox", "safari"}
        for platform in ("linux", "win32", "darwin"):
            names = {name for name, _, _ in _browser_profile_roots(platform, {}, self.home)}
            self.assertLessEqual(names, supported, platform)


class CookiesFileTests(unittest.TestCase):
    def test_existing_cookies_file_replaces_browser_cookies(self):
        with tempfile.TemporaryDirectory() as tmp:
            cookies = _touch(Path(tmp) / "cookies.txt")
            with mock.patch("videotranslator.input_source._detect_browser",
                            return_value=("firefox",)):
                opts = build_ytdlp_options(tmp, js_runtimes={}, cookies_file=str(cookies))
        self.assertEqual(opts["cookiefile"], str(cookies))
        self.assertNotIn("cookiesfrombrowser", opts)

    def test_missing_cookies_file_is_reported_and_browser_used(self):
        logs = []
        with mock.patch("videotranslator.input_source._detect_browser",
                        return_value=("firefox",)):
            opts = build_ytdlp_options("/tmp", js_runtimes={},
                                       cookies_file="/nowhere/cookies.txt", log_cb=logs.append)
        self.assertNotIn("cookiefile", opts)
        self.assertEqual(opts["cookiesfrombrowser"], ("firefox",))
        self.assertTrue(any("yt_dlp_cookies_file" in line for line in logs))

    def test_cookies_file_is_read_from_the_user_config(self):
        from videotranslator import input_source

        with mock.patch("videotranslator.config.load_user_config",
                        return_value={"yt_dlp_cookies_file": " ~/c.txt "}):
            self.assertEqual(input_source._configured_cookies_file(), "~/c.txt")
        with mock.patch("videotranslator.config.load_user_config", return_value={}):
            self.assertIsNone(input_source._configured_cookies_file())


class _CookieLoadError(Exception):
    pass


_CookieLoadError.__name__ = "CookieLoadError"


class _FlakyCookiesYDL:
    """Fails like yt-dlp when browser cookies cannot be read."""

    calls = []

    def __init__(self, opts):
        self.opts = opts
        type(self).calls.append(dict(opts))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def extract_info(self, url, download):
        if "cookiesfrombrowser" in self.opts:
            try:
                raise _CookieLoadError("failed to load cookies")
            except _CookieLoadError as cause:
                raise RuntimeError("ERROR: could not copy Chrome cookie database") from cause
        return {"title": "t", "url": "https://media/x", "acodec": "aac", "vcodec": "h264"}


class CookieFallbackTests(unittest.TestCase):
    def setUp(self):
        _FlakyCookiesYDL.calls = []
        patches = [
            mock.patch("videotranslator.js_runtime.ensure_js_runtime", return_value={}),
            mock.patch("videotranslator.input_source._detect_browser", return_value=("chrome",)),
            mock.patch("videotranslator.input_source._configured_cookies_file", return_value=None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_unreadable_browser_cookies_retry_without_them(self):
        logs = []
        url, title = resolve_stream_url("https://youtu.be/x", ytdlp_cls=_FlakyCookiesYDL,
                                        log_cb=logs.append)
        self.assertEqual(url, "https://media/x")
        self.assertEqual(len(_FlakyCookiesYDL.calls), 2)
        self.assertIn("cookiesfrombrowser", _FlakyCookiesYDL.calls[0])
        self.assertNotIn("cookiesfrombrowser", _FlakyCookiesYDL.calls[1])
        self.assertTrue(any("chrome cookies" in line for line in logs))

    def test_other_errors_are_not_retried(self):
        class Blocked(_FlakyCookiesYDL):
            def extract_info(self, url, download):
                raise RuntimeError("Sign in to confirm you're not a bot")

        logs = []
        with self.assertRaises(RuntimeError):
            resolve_stream_url("https://youtu.be/x", ytdlp_cls=Blocked, log_cb=logs.append)
        self.assertEqual(len(Blocked.calls), 1)
        self.assertTrue(any("VPN" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
