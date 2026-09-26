import unittest

from videotranslator.live_scheduler import (
    ClearSubtitle,
    DubScheduler,
    LiveSegment,
    ShowSubtitle,
    ass_escape,
    caption_ass,
    paginate_caption,
    wrap_caption,
)

WJ = "⁠"


def _seg(seg_id, start, end, *, tgt=None, italic=False, src="hello"):
    return LiveSegment(seg_id, 0, start, end, src, text_tgt=tgt, italic=italic)


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


class DubSchedulerCaptionTests(unittest.TestCase):
    def test_shows_then_clears_a_translated_caption(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="ciao"))
        self.assertEqual(sch.tick(0.5), [])
        acts = sch.tick(1.0)
        self.assertEqual(len(acts), 1)
        self.assertIsInstance(acts[0], ShowSubtitle)
        self.assertEqual(acts[0].seg_id, 0)
        self.assertIn("ciao", acts[0].ass)
        self.assertEqual(sch.tick(2.0), [])                 # unchanged
        acts = sch.tick(3.4)                                 # past clear time
        self.assertEqual([type(a).__name__ for a in acts], ["ClearSubtitle"])

    def test_next_caption_takes_over(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="uno"))
        sch.upsert(_seg(1, 3.0, 5.0, tgt="due"))
        sch.tick(1.0)
        acts = sch.tick(3.0)
        self.assertEqual(len(acts), 1)
        self.assertIsInstance(acts[0], ShowSubtitle)
        self.assertEqual(acts[0].seg_id, 1)

    def test_captions_off_clears_and_suppresses(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="ciao"))
        sch.tick(1.0)
        self.assertEqual([type(a).__name__ for a in sch.set_subs(False)], ["ClearSubtitle"])
        self.assertEqual(sch.tick(2.0), [])

    def test_fallback_line_is_italic_source_text(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, italic=True, src="untranslated"))
        acts = sch.tick(1.0)
        self.assertIn("untranslated", acts[0].ass)
        self.assertIn("{\\i1}", acts[0].ass)

    def test_untranslated_segment_is_not_shown(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0))          # no tgt, not italic
        self.assertEqual(sch.tick(1.0), [])

    def test_invalid_clock_clears(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="ciao"))
        sch.tick(1.0)
        self.assertEqual([type(a).__name__ for a in sch.tick(None)], ["ClearSubtitle"])

    def test_ready_until_contiguous_coverage(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="a"))
        sch.upsert(_seg(1, 3.0, 5.0, tgt="b"))
        sch.upsert(_seg(2, 8.0, 10.0, tgt="c"))   # gap
        self.assertEqual(sch.ready_until(1.0), 5.0)

    def test_on_seek_clears_and_reshows(self):
        sch = DubScheduler(mode="delayed")
        sch.upsert(_seg(0, 1.0, 3.0, tgt="ciao"))
        sch.tick(1.0)
        self.assertEqual([type(a).__name__ for a in sch.on_seek(0.0, 1)], ["ClearSubtitle"])
        acts = sch.tick(1.0)                        # shows again after the seek
        self.assertEqual([type(a).__name__ for a in acts], ["ShowSubtitle"])


if __name__ == "__main__":
    unittest.main()
