import tempfile
import unittest
from pathlib import Path

from videotranslator.input_source import (
    build_ytdlp_options,
    download_url,
    is_probable_url,
    normalize_input_path,
    resolve_downloaded_filename,
)


class InputSourceTests(unittest.TestCase):
    def test_build_ytdlp_options_contains_project_policy(self):
        opts = build_ytdlp_options("/tmp/videos")

        self.assertEqual(opts["merge_output_format"], "mp4")
        self.assertTrue(opts["noplaylist"])
        self.assertIn("player_client", opts["extractor_args"]["youtube"])
        self.assertIn("%(title).80s.%(ext)s", opts["outtmpl"])

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

            result = download_url(
                "https://youtu.be/example",
                tmp_str,
                ytdlp_cls=FakeYoutubeDL,
                log_cb=logs.append,
            )

        self.assertEqual(result, str(final))
        self.assertEqual(seen_opts["merge_output_format"], "mp4")
        self.assertEqual(logs, [f"[+] Downloaded: {final}"])


if __name__ == "__main__":
    unittest.main()
