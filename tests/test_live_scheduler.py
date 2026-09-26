import unittest

from videotranslator.live_scheduler import (
    ass_escape,
    caption_ass,
    paginate_caption,
    wrap_caption,
)

WJ = "⁠"


class WrapCaptionTests(unittest.TestCase):
    def test_short_text_is_one_line(self):
        self.assertEqual(wrap_caption("hello world"), ["hello world"])

    def test_wraps_at_max_chars(self):
        lines = wrap_caption("aaaa bbbb cccc dddd", max_chars=9)
        self.assertTrue(all(len(line) <= 9 for line in lines))
        self.assertEqual(lines, ["aaaa bbbb", "cccc dddd"])

    def test_caps_at_max_lines(self):
        text = " ".join(["word"] * 40)
        self.assertLessEqual(len(wrap_caption(text, max_chars=10, max_lines=2)), 2)


class PaginateCaptionTests(unittest.TestCase):
    def test_short_caption_single_page(self):
        pages = paginate_caption("hello world", 0.0, 2.0)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][0], 0.0)
        self.assertEqual(pages[0][1], 2.0)
        self.assertEqual(pages[0][2], ["hello world"])

    def test_long_caption_paginates_contiguously(self):
        text = " ".join(f"w{i}" for i in range(60))
        pages = paginate_caption(text, 0.0, 10.0)
        self.assertGreater(len(pages), 1)
        # contiguous coverage from start to end
        self.assertEqual(pages[0][0], 0.0)
        self.assertEqual(pages[-1][1], 10.0)
        for a, b in zip(pages, pages[1:]):
            self.assertAlmostEqual(a[1], b[0], places=6)
        # every page has at most two lines
        self.assertTrue(all(len(lines) <= 2 for _, _, lines in pages))

    def test_empty_text_no_pages(self):
        self.assertEqual(paginate_caption("   ", 0.0, 1.0), [])


class AssEscapeTests(unittest.TestCase):
    def test_backslash_gets_word_joiner(self):
        self.assertEqual(ass_escape("a\\nb"), "a\\" + WJ + "nb")

    def test_brace_is_escaped(self):
        self.assertEqual(ass_escape("{bold}"), "\\{bold}")

    def test_plain_text_unchanged(self):
        self.assertEqual(ass_escape("ciao mondo"), "ciao mondo")


class CaptionAssTests(unittest.TestCase):
    def test_style_and_line_break(self):
        out = caption_ass(["line one", "line two"], font_px=40, italic=False)
        self.assertTrue(out.startswith("{\\an2\\fs40\\bord2\\shad0}"))
        self.assertIn("line one\\Nline two", out)
        self.assertNotIn("{\\i1}", out)

    def test_italic_marks_fallback(self):
        out = caption_ass(["x"], font_px=48, italic=True)
        self.assertIn("{\\i1}", out)
        self.assertIn("\\fs48", out)

    def test_content_is_escaped(self):
        out = caption_ass(["a{b}"], font_px=40, italic=False)
        self.assertIn("a\\{b}", out)


if __name__ == "__main__":
    unittest.main()
