import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from videotranslator import ui_fonts


class RegisterFontsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "fonts"
        self.src.mkdir()
        for name in ui_fonts.FONT_FILES:
            (self.src / name).write_bytes(b"font:" + name.encode())
        self.home = Path(self.tmp.name) / "home"

    def test_bundled_files_exist_with_their_licences(self):
        for name in ui_fonts.FONT_FILES:
            self.assertTrue((ui_fonts.FONTS_DIR / name).is_file(), name)
        for name in ("OFL-PixelifySans.txt", "OFL-VT323.txt"):
            text = (ui_fonts.FONTS_DIR / name).read_text(encoding="utf-8")
            self.assertIn("SIL Open Font License", text)

    def test_linux_copies_into_the_user_font_dir_once(self):
        done = ui_fonts.register_bundled_fonts(self.src, sys_platform="linux", home=self.home)
        self.assertEqual(done, list(ui_fonts.FONT_FILES))
        target = self.home / ".local" / "share" / "fonts" / "VideoTranslatorAI"
        for name in ui_fonts.FONT_FILES:
            self.assertEqual((target / name).read_bytes(), (self.src / name).read_bytes())
        stamp = (target / ui_fonts.FONT_FILES[0]).stat().st_mtime_ns
        self.assertEqual(ui_fonts.register_bundled_fonts(
            self.src, sys_platform="linux", home=self.home), list(ui_fonts.FONT_FILES))
        self.assertEqual((target / ui_fonts.FONT_FILES[0]).stat().st_mtime_ns, stamp)
        self.assertEqual([p.name for p in target.iterdir() if p.suffix == ".part"], [])

    def test_changed_font_is_replaced(self):
        ui_fonts.register_bundled_fonts(self.src, sys_platform="linux", home=self.home)
        (self.src / ui_fonts.FONT_FILES[1]).write_bytes(b"a newer and longer font")
        ui_fonts.register_bundled_fonts(self.src, sys_platform="linux", home=self.home)
        target = self.home / ".local" / "share" / "fonts" / "VideoTranslatorAI"
        self.assertEqual((target / ui_fonts.FONT_FILES[1]).read_bytes(),
                         b"a newer and longer font")

    def test_macos_uses_library_fonts(self):
        ui_fonts.register_bundled_fonts(self.src, sys_platform="darwin", home=self.home)
        self.assertTrue((self.home / "Library" / "Fonts" / ui_fonts.FONT_FILES[0]).is_file())

    def test_windows_adds_private_fonts_without_copying(self):
        added = []

        def add(path):
            added.append(path)
            return not path.endswith("VT323-Regular.ttf")

        done = ui_fonts.register_bundled_fonts(self.src, sys_platform="win32",
                                               home=self.home, add_font=add)
        self.assertEqual(done, ["PixelifySans.ttf"])
        self.assertEqual([Path(p).name for p in added], list(ui_fonts.FONT_FILES))
        self.assertFalse(self.home.exists())

    def test_never_raises(self):
        self.assertEqual(ui_fonts.register_bundled_fonts(
            Path(self.tmp.name) / "missing", sys_platform="linux", home=self.home), [])

        def boom(path):
            raise OSError("gdi")

        self.assertEqual(ui_fonts.register_bundled_fonts(
            self.src, sys_platform="win32", add_font=boom), [])
        blocker = Path(self.tmp.name) / "file-home"
        blocker.write_text("x")
        self.assertEqual(ui_fonts.register_bundled_fonts(
            self.src, sys_platform="linux", home=blocker), [])


if __name__ == "__main__":
    unittest.main()
