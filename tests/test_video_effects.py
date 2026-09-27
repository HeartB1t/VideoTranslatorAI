import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from videotranslator import video_effects as ve
from videotranslator.ui_theme import SKIN_CHOICES


class ShaderTests(unittest.TestCase):
    def test_only_the_crt_skins_have_a_video_effect(self):
        self.assertEqual(set(ve.CRT_TINTS), {s for s in SKIN_CHOICES if s.startswith("crt")})
        with TemporaryDirectory() as tmp:
            for theme in ("graphite", "light", "dex", "handheld", "auto"):
                self.assertIsNone(ve.shader_for_theme(theme, Path(tmp)))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_shader_is_a_valid_mpv_hook_with_the_skin_tint(self):
        source = ve.crt_shader_source(ve.CRT_TINTS["crt_amber"])
        self.assertTrue(source.startswith("//!HOOK OUTPUT\n//!BIND HOOKED\n"))
        self.assertIn("vec3(1.04, 0.97, 0.86)", source)
        self.assertEqual(source.count("{"), source.count("}"))

    def test_file_is_written_once_and_rewritten_if_changed(self):
        with TemporaryDirectory() as tmp:
            path = Path(ve.shader_for_theme("crt", Path(tmp) / "cache"))
            self.assertEqual(path.name, "crt.glsl")
            self.assertEqual(path.read_text(encoding="utf-8"),
                             ve.crt_shader_source(ve.CRT_TINTS["crt"]))
            stamp = path.stat().st_mtime_ns
            self.assertEqual(ve.shader_for_theme("crt", Path(tmp) / "cache"), str(path))
            self.assertEqual(path.stat().st_mtime_ns, stamp)
            path.write_text("old", encoding="utf-8")
            ve.shader_for_theme("crt", Path(tmp) / "cache")
            self.assertIn("//!HOOK OUTPUT", path.read_text(encoding="utf-8"))
            self.assertNotEqual(ve.shader_for_theme("crt_amber", Path(tmp) / "cache"), str(path))

    def test_unwritable_cache_gives_no_effect(self):
        with TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "file"
            blocker.write_text("x")
            self.assertIsNone(ve.shader_for_theme("crt", blocker))


if __name__ == "__main__":
    unittest.main()
