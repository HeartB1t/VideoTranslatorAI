import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from videotranslator import app_log


class FileSinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "logs"

    def read(self, sink):
        sink.close()
        return sink.path.read_text(encoding="utf-8").splitlines()

    def test_lines_get_date_and_time_and_events_keep_their_time(self):
        sink = app_log.FileSink(self.dir)
        self.assertTrue(sink.ok)
        sink.write("[+] step one\npart")
        sink.write("ial line\n12:00:01 [voicebox] check\n\n")
        lines = self.read(sink)
        self.assertEqual(len(lines), 3)
        self.assertRegex(lines[0], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[\+\] step one$")
        self.assertRegex(lines[1], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} partial line$")
        self.assertRegex(lines[2], r"^\d{4}-\d{2}-\d{2} 12:00:01 \[voicebox\] check$")

    def test_progress_bars_keep_their_last_state_and_close_flushes(self):
        sink = app_log.FileSink(self.dir)
        sink.write("10%\r50%\r100%\nunterminated")
        lines = self.read(sink)
        self.assertTrue(lines[0].endswith(" 100%"))
        self.assertTrue(lines[1].endswith(" unterminated"))

    def test_daily_rotation_keeps_seven_days(self):
        sink = app_log.FileSink(self.dir)
        handler = sink._handler
        self.assertEqual((handler.when, handler.backupCount), ("MIDNIGHT", app_log.KEEP_DAYS))
        self.assertEqual(sink.path, self.dir / "videotranslator.log")
        self.assertEqual(app_log.log_dir_for(Path("/x/cfg/config.json")), Path("/x/cfg/logs"))
        sink.close()

    def test_unwritable_folder_disables_the_file_quietly(self):
        blocker = Path(self.tmp.name) / "file"
        blocker.write_text("x")
        sink = app_log.FileSink(blocker / "logs")
        self.assertFalse(sink.ok)
        sink.write("nothing happens\n")
        sink.close()

    def test_helpers(self):
        self.assertRegex(app_log.stamp("x"), r"^\d{2}:\d{2}:\d{2} x$")
        self.assertEqual(app_log.short("a\n  b"), "a b")
        self.assertEqual(len(app_log.short("x" * 100, 10)), 10)

    @staticmethod
    def _bar(label, pct, total=100):
        done = pct * total // 100
        return (f"{label}: {pct:3d}%|{'#' * (pct // 10):<10}| {done}/{total} "
                f"[00:00<00:01, 90.0it/s]\n")

    def _bodies(self, sink):
        return [line.split(" ", 2)[2] for line in self.read(sink)]

    def test_progress_updates_are_thinned_to_start_quarter_steps_and_end(self):
        now = [1000.0]
        sink = app_log.FileSink(self.dir, clock=lambda: now[0])
        for pct in range(0, 101):
            sink.write(self._bar("Loading weights", pct))
        sink.write(self._bar("Loading weights", 100))     # tqdm repeats the final state
        sink.write("[+] done\n")
        bodies = self._bodies(sink)
        self.assertEqual(bodies[-1], "[+] done")
        written = [int(app_log.progress_of(body).percent) for body in bodies[:-1]]
        self.assertEqual(written, [0, 25, 50, 75, 100])

    def test_time_passes_progress_through_and_an_interrupted_bar_keeps_its_last_state(self):
        now = [0.0]
        sink = app_log.FileSink(self.dir, clock=lambda: now[0])
        sink.write(self._bar("a.bin", 0))
        now[0] += app_log.PROGRESS_MIN_INTERVAL_S + 0.5
        sink.write(self._bar("a.bin", 3))                 # due by time
        sink.write(self._bar("a.bin", 5))                 # withheld
        sink.write(self._bar("a.bin", 7))                 # withheld, then the last state
        sink.write("[+] cancelled\n")
        bodies = self._bodies(sink)
        self.assertEqual([app_log.progress_of(b).percent for b in bodies[:-1]], [0, 3, 7])
        self.assertEqual(bodies[-1], "[+] cancelled")

    def test_a_new_activity_starts_its_own_bar_and_close_flushes_the_pending_state(self):
        now = [0.0]
        sink = app_log.FileSink(self.dir, clock=lambda: now[0])
        sink.write(self._bar("x.bin", 0))
        sink.write(self._bar("x.bin", 10))                # withheld
        sink.write(self._bar("y.bin", 0))                 # flushes x 10%, starts y
        sink.write(self._bar("y.bin", 40))                # withheld until close
        bodies = self._bodies(sink)
        self.assertEqual([(app_log.progress_of(b).label, app_log.progress_of(b).percent)
                          for b in bodies], [("x.bin", 0), ("x.bin", 10), ("y.bin", 0), ("y.bin", 40)])



class ProgressLineTests(unittest.TestCase):
    """tqdm style updates (transformers, huggingface_hub, faster-whisper, Demucs)."""

    def test_tqdm_and_hub_download_lines_are_progress(self):
        first = app_log.progress_of(
            "Loading weights:  12%|#1        | 24/200 [00:00<00:03, 52.10it/s]")
        self.assertEqual((first.label, first.percent, first.done), ("Loading weights", 12, False))
        last = app_log.progress_of(
            "Loading weights: 100%|##########| 200/200 [00:03<00:00, 60.00it/s]")
        self.assertEqual(last.key, first.key)
        self.assertTrue(last.done)
        download = app_log.progress_of(
            "model.safetensors:  40%|████      | 120M/300M [00:10<00:15, 12.0MB/s]")
        self.assertEqual((download.label, download.percent), ("model.safetensors", 40))
        self.assertNotEqual(download.key, first.key)
        bare = app_log.progress_of("100%|██████████| 5/5 [00:00<00:00, 12.3it/s]")
        self.assertEqual((bare.label, bare.percent, bare.done), ("", 100, True))
        demucs = app_log.progress_of(
            " 45%|████▌     | 90.0/200.0 [00:20<00:25, 4.5seconds/s]")
        self.assertEqual(demucs.percent, 45)
        no_total = app_log.progress_of("Frames: 24it [00:01, 20.0it/s]")
        self.assertEqual((no_total.label, no_total.percent, no_total.done),
                         ("Frames", None, False))
        self.assertEqual(app_log.progress_of("Frames: 25it [00:01, 20.0it/s]").key,
                         no_total.key)

    def test_the_panel_prefix_does_not_change_the_activity(self):
        raw = "Loading weights:  12%|#1        | 24/200 [00:00<00:03, 52.10it/s]"
        expected = app_log.progress_of(raw)
        for prefix in ("12:00:01 INFO    [app] ", "12:00:01 CẢNH BÁO [live] "):
            found = app_log.progress_of(prefix + raw)
            self.assertEqual((found.key, found.label, found.percent),
                             (expected.key, expected.label, expected.percent), prefix)
        self.assertEqual(app_log.progress_of("10%\r" + raw).key, expected.key)

    def test_ordinary_lines_are_not_progress(self):
        for line in ("[3/6] Translating 120 segments", "CPU at 50% for 10s", "Volume 80%",
                     "Downloading model (1.2 GB)", "     3/10...", "", "   ", "done [ok]",
                     "12:00:01 INFO    [app] MarianMT loaded", "quality 100% [checked]"):
            self.assertIsNone(app_log.progress_of(line), line)


class LineFormatTests(unittest.TestCase):
    def test_classify_reads_level_and_area_from_the_line_start(self):
        c = app_log.classify
        self.assertEqual(c("[!] Voicebox not available"), ("warn", "app", "Voicebox not available"))
        self.assertEqual(c("[+] Ollama trovato"), ("info", "app", "Ollama trovato"))
        self.assertEqual(c("[3/6] Translating EN->IT"), ("info", "job", "[3/6] Translating EN->IT"))
        self.assertEqual(c("live: 3.6s You -> Tu (1.1 s)"), ("info", "live", "3.6s You -> Tu (1.1 s)"))
        self.assertEqual(c("live: voice line 4 lost (rejected)")[0], "warn")
        self.assertEqual(c("live: 36.1s kept original (timeout, 5.0 s): long")[0], "warn")
        self.assertEqual(c("live: start failed: boom")[0], "error")

    def test_the_words_of_a_subtitle_never_set_the_level(self):
        # Seen in a live stress test: a lyric with "crash" became an ERROR line.
        c = app_log.classify
        self.assertEqual(c("live: 177.5s kept original (google paused after errors): "
                           "another face pops the crash.")[0], "warn")
        self.assertEqual(c("live: 3.0s It failed again -> Ha fallito ancora (0.2 s)")[0], "info")
        self.assertEqual(c("live: 4.0s I lost my keys -> Ho perso le chiavi (0.1 s)")[0], "info")

    def test_classify_reads_other_line_starts(self):
        c = app_log.classify
        self.assertEqual(c("[live] start failed: boom"), ("error", "live", "start failed: boom"))
        self.assertEqual(c("[mpv] X11 error: BadWindow"), ("info", "mpv", "X11 error: BadWindow"))
        self.assertEqual(c("Traceback (most recent call last):")[0], "error")
        self.assertEqual(c("ZeroDivisionError: division by zero")[0], "error")
        self.assertEqual(c('  File "x.py", line 3')[0], None)        # traceback frame
        self.assertEqual(c("Connessione allo stream..."), ("info", "app", "Connessione allo stream..."))

    def test_level_words_are_padded_and_prefix_is_complete(self):
        words = app_log.level_words({"info": "INFO", "warn": "AVVISO", "error": "ERRORE"})
        self.assertEqual({len(w) for w in words.values()}, {6})
        line = app_log.prefix("warn", "live", words)
        self.assertRegex(line, r"^\d{2}:\d{2}:\d{2} AVVISO \[live\] $")

    def test_git_commit_reads_the_checkout(self):
        with TemporaryDirectory() as tmp:
            git = Path(tmp) / ".git"
            (git / "refs" / "heads").mkdir(parents=True)
            (git / "HEAD").write_text("ref: refs/heads/main\n")
            (git / "refs" / "heads" / "main").write_text("1dabb3581510c3ec\n")
            self.assertEqual(app_log.git_commit(Path(tmp)), "1dabb35")
            (git / "refs" / "heads" / "main").unlink()
            (git / "packed-refs").write_text("# pack\nabcdef0123 refs/heads/main\n")
            self.assertEqual(app_log.git_commit(Path(tmp)), "abcdef0")
            (git / "HEAD").write_text("0123456789abcdef\n")      # detached
            self.assertEqual(app_log.git_commit(Path(tmp)), "0123456")
            self.assertEqual(app_log.git_commit(Path(tmp) / "none"), "")



class SystemFactsTests(unittest.TestCase):
    def test_os_description_per_platform(self):
        rel = 'NAME="Kali GNU/Linux"\nPRETTY_NAME="Kali GNU/Linux Rolling"\n'
        self.assertEqual(app_log.os_description("linux", os_release=rel), "Kali GNU/Linux Rolling")
        self.assertEqual(app_log.os_description("linux", os_release="NAME=x\n"), "Linux")
        self.assertTrue(app_log.os_description(
            "win32", win_ver=("11", "10.0.26100", "SP0", "Multiprocessor Free"))
            .startswith("Windows 11 (10.0.26100)"))
        self.assertEqual(app_log.os_description("darwin", mac_ver=("15.1", ("", "", ""), "")),
                         "macOS 15.1")

    def test_library_versions_skip_missing(self):
        versions = {"torch": "2.6.0+cu124", "yt-dlp": "2026.8.19"}

        def version(name):
            if name not in versions:
                raise LookupError(name)
            return versions[name]

        self.assertEqual(app_log.library_versions(("torch", "missing", "yt-dlp"), version=version),
                         "torch 2.6.0+cu124, yt-dlp 2026.8.19")

    def test_nvidia_banner_ffmpeg_and_tools(self):
        banner = ("+----+\n| NVIDIA-SMI 580.173.02   Driver Version: 580.173.02   "
                  "CUDA Version: 13.0 |\n")
        self.assertEqual(app_log.parse_nvidia_smi_banner(banner), ("580.173.02", "13.0"))
        self.assertEqual(app_log.parse_nvidia_smi_banner(""), ("", ""))
        self.assertEqual(app_log.ffmpeg_version("ffmpeg version 8.1.2-2+b3 Copyright (c)"),
                         "8.1.2-2+b3")
        self.assertEqual(app_log.ffmpeg_version(""), "")

        class Out:
            stdout = "first\nsecond\n"

        self.assertEqual(app_log.tool_first_line(["x"], run=lambda *a, **k: Out()), "first")

        def missing(*a, **k):
            raise FileNotFoundError("x")

        self.assertEqual(app_log.tool_output(["x"], run=missing), "")


if __name__ == "__main__":
    unittest.main()
