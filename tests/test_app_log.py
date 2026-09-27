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



class LineFormatTests(unittest.TestCase):
    def test_classify_reads_level_and_area_from_the_line_start(self):
        c = app_log.classify
        self.assertEqual(c("[!] Voicebox not available"), ("warn", "app", "Voicebox not available"))
        self.assertEqual(c("[+] Ollama trovato"), ("info", "app", "Ollama trovato"))
        self.assertEqual(c("[3/6] Translating EN->IT"), ("info", "job", "[3/6] Translating EN->IT"))
        self.assertEqual(c("live: 3.6s You -> Tu (1.1 s)"), ("info", "live", "3.6s You -> Tu (1.1 s)"))
        self.assertEqual(c("live: voice line 4 lost (rejected)")[0], "warn")
        self.assertEqual(c("live: 36.1s kept original (timeout, 5.0 s): long")[0], "warn")
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
