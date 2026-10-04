import os
import tempfile
import unittest
from pathlib import Path

from videotranslator.audio_extract import (
    AUDIO_FORMATS,
    allowed_bitrates,
    build_convert_cmd,
    default_bitrate,
    extract_music,
    format_keys,
    format_label,
    is_lossy,
    resolve_output_path,
)


class AudioFormatCatalogTests(unittest.TestCase):
    def test_catalog_is_ordered_and_covers_every_required_format(self):
        self.assertEqual(
            format_keys(), ["mp3", "m4a", "opus", "ogg", "flac", "wav"]
        )

    def test_every_format_exposes_a_label_and_extension(self):
        for key in format_keys():
            fmt = AUDIO_FORMATS[key]
            self.assertTrue(format_label(key))
            self.assertTrue(fmt.ext.startswith("."))

    def test_lossy_flags_and_bitrate_tables(self):
        self.assertTrue(is_lossy("mp3"))
        self.assertTrue(is_lossy("m4a"))
        self.assertTrue(is_lossy("opus"))
        self.assertTrue(is_lossy("ogg"))
        self.assertFalse(is_lossy("flac"))
        self.assertFalse(is_lossy("wav"))

        self.assertEqual(allowed_bitrates("mp3"), (128, 192, 256, 320))
        self.assertEqual(allowed_bitrates("m4a"), (128, 192, 256))
        self.assertEqual(allowed_bitrates("opus"), (96, 128, 160, 192))
        self.assertEqual(allowed_bitrates("ogg"), (128, 192, 256))
        self.assertEqual(allowed_bitrates("flac"), ())
        self.assertEqual(allowed_bitrates("wav"), ())

    def test_default_bitrate_is_inside_the_allowed_table(self):
        for key in ("mp3", "m4a", "opus", "ogg"):
            self.assertIn(default_bitrate(key), allowed_bitrates(key))
        self.assertIsNone(default_bitrate("flac"))
        self.assertIsNone(default_bitrate("wav"))

    def test_unknown_format_helpers_raise(self):
        with self.assertRaises(ValueError):
            format_label("aiff")
        with self.assertRaises(ValueError):
            is_lossy("aiff")
        with self.assertRaises(ValueError):
            allowed_bitrates("aiff")


class BuildConvertCmdTests(unittest.TestCase):
    def test_lossy_command_drops_video_and_sets_bitrate(self):
        cmd = build_convert_cmd("in.mp4", "out.mp3", "mp3", bitrate=256)
        self.assertEqual(cmd[:4], ["ffmpeg", "-y", "-i", "in.mp4"])
        self.assertIn("-vn", cmd)
        self.assertIn("libmp3lame", cmd)
        self.assertIn("-b:a", cmd)
        self.assertIn("256k", cmd)
        self.assertEqual(cmd[-1], "out.mp3")

    def test_lossy_command_uses_default_bitrate_when_omitted(self):
        cmd = build_convert_cmd("in.webm", "out.opus", "opus")
        self.assertIn("-b:a", cmd)
        self.assertIn(f"{default_bitrate('opus')}k", cmd)

    def test_lossless_command_has_no_bitrate(self):
        cmd = build_convert_cmd("in.mov", "out.flac", "flac")
        self.assertIn("-vn", cmd)
        self.assertIn("flac", cmd)
        self.assertNotIn("-b:a", cmd)

        wav = build_convert_cmd("in.mov", "out.wav", "wav")
        self.assertIn("pcm_s16le", wav)
        self.assertNotIn("-b:a", wav)

    def test_lossless_ignores_a_stray_bitrate(self):
        cmd = build_convert_cmd("in.mov", "out.flac", "flac", bitrate=320)
        self.assertNotIn("-b:a", cmd)

    def test_unknown_format_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_convert_cmd("in.mp4", "out.aiff", "aiff")

    def test_disallowed_bitrate_raises_with_a_clear_message(self):
        with self.assertRaises(ValueError) as ctx:
            build_convert_cmd("in.mp4", "out.mp3", "mp3", bitrate=111)
        self.assertIn("111", str(ctx.exception))
        self.assertIn("mp3", str(ctx.exception))


class ResolveOutputPathTests(unittest.TestCase):
    def test_full_audio_keeps_the_stem_and_swaps_extension(self):
        out = resolve_output_path("/clips/My Talk.mkv", "/out", "mp3")
        self.assertEqual(out, os.path.join("/out", "My Talk.mp3"))

    def test_instrumental_adds_a_suffix(self):
        out = resolve_output_path("/clips/My Talk.mkv", "/out", "flac",
                                  instrumental=True)
        self.assertEqual(out, os.path.join("/out", "My Talk (instrumental).flac"))

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            resolve_output_path("/clips/x.mp4", "/out", "aiff")


class ExtractMusicOrchestratorTests(unittest.TestCase):
    def test_local_full_audio_converts_the_source_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "lecture.mp4"
            src.write_bytes(b"x")
            out_dir = Path(tmp) / "out"
            cmds: list[list[str]] = []

            def fake_runner(cmd, step):
                cmds.append(cmd)

            def fail_sep(*_a, **_k):
                raise AssertionError("separator must not run for full audio")

            def fail_dl(*_a, **_k):
                raise AssertionError("downloader must not run for a local file")

            out = extract_music(
                str(src), str(out_dir), fmt="mp3", bitrate=320,
                ffmpeg_runner=fake_runner, separator=fail_sep, downloader=fail_dl,
            )

            self.assertEqual(out, os.path.join(str(out_dir), "lecture.mp3"))
            self.assertEqual(len(cmds), 1)
            self.assertEqual(cmds[0][3], str(src))
            self.assertIn("320k", cmds[0])
            self.assertTrue(out_dir.is_dir())

    def test_instrumental_runs_the_separator_then_converts_the_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "song.wav"
            src.write_bytes(b"x")
            out_dir = Path(tmp) / "out"
            cmds: list[list[str]] = []
            sep_calls: list[tuple[str, str]] = []

            def fake_runner(cmd, step):
                cmds.append(cmd)

            def fake_sep(audio_path, out_path, *, log_cb=None):
                sep_calls.append((audio_path, out_path))
                return out_path

            out = extract_music(
                str(src), str(out_dir), fmt="flac", instrumental=True,
                ffmpeg_runner=fake_runner, separator=fake_sep,
            )

            self.assertEqual(
                out, os.path.join(str(out_dir), "song (instrumental).flac"))
            self.assertEqual(len(sep_calls), 1)
            self.assertEqual(sep_calls[0][0], str(src))
            # ffmpeg converts the separator output, not the original source.
            self.assertEqual(cmds[0][3], sep_calls[0][1])

    def test_url_source_is_downloaded_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            cmds: list[list[str]] = []
            dl_calls: list[str] = []

            def fake_runner(cmd, step):
                cmds.append(cmd)

            def fake_dl(url, download_dir, *, ytdlp_cls=None, log_cb=None):
                dl_calls.append(url)
                path = os.path.join(download_dir, "Remote Clip.m4a")
                with open(path, "wb") as handle:
                    handle.write(b"x")
                return path

            out = extract_music(
                "https://youtu.be/abc", str(out_dir), fmt="m4a",
                ffmpeg_runner=fake_runner, downloader=fake_dl,
            )

            self.assertEqual(dl_calls, ["https://youtu.be/abc"])
            self.assertEqual(out, os.path.join(str(out_dir), "Remote Clip.m4a"))
            self.assertEqual(len(cmds), 1)

    def test_unknown_format_raises_before_any_work(self):
        with self.assertRaises(ValueError):
            extract_music("/x/y.mp4", "/out", fmt="aiff")


if __name__ == "__main__":
    unittest.main()
