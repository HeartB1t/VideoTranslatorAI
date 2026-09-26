import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.input_source import (
    build_ytdlp_options,
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
        self.assertTrue(normalize_input_path("~/Videos/input.mp4").endswith("Videos/input.mp4"))

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
        # Final download line is the contract; advisory warnings precede it.
        self.assertEqual(logs[-1], f"[+] Downloaded: {final}")
        self.assertTrue(any("anti-bot" in line for line in logs))

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

    def test_emit_download_warnings_advises_on_vpn(self):
        logs: list[str] = []
        emit_download_warnings(logs.append)

        self.assertTrue(any("VPN" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
