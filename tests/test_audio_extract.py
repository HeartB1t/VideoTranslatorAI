import importlib.util
import os
import shutil
import subprocess
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

    def test_instrumental_decodes_the_source_to_a_44k_stereo_wav_first(self):
        # Demucs loads through torchaudio, whose soundfile backend cannot open
        # video or web containers (mp4, webm, m4a), and htdemucs is a 2-channel
        # 44.1 kHz model: the separator gets ffmpeg's decoded WAV, never the
        # source itself.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "concert.mp4"
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
                out, os.path.join(str(out_dir), "concert (instrumental).flac"))
            self.assertEqual(len(cmds), 2)
            decode, convert = cmds
            self.assertEqual(decode[3], str(src))
            self.assertEqual(decode[decode.index("-ar") + 1], "44100")
            self.assertEqual(decode[decode.index("-ac") + 1], "2")
            self.assertTrue(decode[-1].endswith(".wav"))
            # A temp file: nothing lands next to the source or in the output.
            self.assertFalse(decode[-1].startswith(tmp))
            self.assertEqual(len(sep_calls), 1)
            # Demucs reads the decoded WAV, and ffmpeg converts its output.
            self.assertEqual(sep_calls[0][0], decode[-1])
            self.assertEqual(convert[3], sep_calls[0][1])
            self.assertEqual(convert[-1], out)

    def test_source_named_like_the_output_is_never_overwritten(self):
        # Field bug (ultrareview 2026-10-20): `--extract-audio song.mp3` writes
        # next to the source, so the output was the source itself. ffmpeg -y
        # truncated the file it was reading (5 s -> 1.3 s) when the two paths
        # were spelled differently, and refused to write when they matched.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "song.mp3"
            src.write_bytes(b"x")
            expected = os.path.join(tmp, "song (extracted).mp3")
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                for spelling in ("song.mp3", str(src),
                                 os.path.join(tmp, ".", "song.mp3")):
                    with self.subTest(source=spelling):
                        cmds: list[list[str]] = []
                        out = extract_music(
                            spelling, tmp, fmt="mp3",
                            ffmpeg_runner=lambda cmd, step: cmds.append(cmd),
                        )
                        self.assertEqual(out, expected)
                        self.assertEqual(cmds[0][-1], expected)
            finally:
                os.chdir(old_cwd)      # Windows cannot delete the current dir

    def test_same_format_in_another_folder_keeps_the_plain_name(self):
        # Only the source itself is protected: a same-format output elsewhere
        # keeps the plain name.
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "song.mp3"
            src.write_bytes(b"x")
            out_dir = Path(tmp) / "out"

            out = extract_music(
                str(src), str(out_dir), fmt="mp3",
                ffmpeg_runner=lambda cmd, step: None,
            )

            self.assertEqual(out, os.path.join(str(out_dir), "song.mp3"))

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


@unittest.skipUnless(
    shutil.which("ffmpeg") and importlib.util.find_spec("soundfile"),
    "ffmpeg and soundfile are required for the real decode test",
)
class ExtractMusicRealDecodeTests(unittest.TestCase):
    def test_separator_reads_a_44k_stereo_wav_decoded_from_a_5_1_video(self):
        # Field bug (ultrareview 2026-10-20): "Instrumental only" on an mp4
        # failed with "Format not recognised" (Demucs loads through torchaudio,
        # whose soundfile backend cannot open video containers) and a 5.1 track
        # crashed the 2-channel htdemucs. Real ffmpeg, real soundfile.
        import numpy
        import soundfile

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "concert.mp4"
            self._create_5_1_video(src)
            seen: list[tuple[int, int]] = []

            def probing_sep(audio_path, out_path, *, log_cb=None):
                try:
                    info = soundfile.info(audio_path)
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"Demucs cannot read its input "
                              f"{os.path.basename(audio_path)}: {exc}")
                seen.append((info.samplerate, info.channels))
                soundfile.write(out_path,
                                numpy.zeros((info.frames, 2), dtype="float32"),
                                info.samplerate)
                return out_path

            out = extract_music(str(src), str(Path(tmp) / "out"), fmt="wav",
                                instrumental=True, separator=probing_sep)

            self.assertEqual(seen, [(44100, 2)])
            self.assertTrue(os.path.isfile(out))

    def _create_5_1_video(self, output: Path) -> None:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=96x64:rate=10:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
            "-filter:a", "pan=5.1|c0=c0|c1=c0|c2=c0|c3=c0|c4=c0|c5=c0",
            "-shortest", "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(output),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=20)
        if proc.returncode != 0:
            self.skipTest(f"ffmpeg 5.1 fixture failed: {proc.stderr.strip()}")


if __name__ == "__main__":
    unittest.main()
