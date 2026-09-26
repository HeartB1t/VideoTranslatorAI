import unittest

from types import SimpleNamespace

from videotranslator.live_scheduler import (
    ClearSubtitle,
    Drop,
    DubScheduler,
    Duck,
    DuckEnvelope,
    FadeRamp,
    LiveSegment,
    PauseClip,
    PreloadClip,
    RequestTts,
    ResumeClip,
    ShowSubtitle,
    StartClip,
    StopClip,
    ass_escape,
    caption_ass,
    paginate_caption,
    wrap_caption,
)


def _clip(path="c.mp3", *, audible=1.8, vstart=0.1):
    return SimpleNamespace(path=path, audible_s=audible, voice_start_s=vstart)


def _dub_sched(**kw):
    opts = dict(mode="delayed", dub=True, subs=False, lead_s=0.25, preload_s=1.5,
                late_tolerance_s=0.5, duck_gain=0.3, duck_ramp_s=0.2,
                duck_latency_s=0.4, overhang_s=0.6, rate_for=lambda t, s: 10)
    opts.update(kw)
    return DubScheduler(**opts)


def _types(actions):
    return [type(a).__name__ for a in actions]

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


class DubSchedulerDubPathTests(unittest.TestCase):
    def test_preloaded_clip_waits_for_resume_in_both_modes(self):
        for mode in ("live", "delayed"):
            s = _dub_sched(mode=mode)
            s.upsert(self._seg())
            s.clip_ready(0, 0, _clip())
            s.tick(4.8, main_running=False)
            acts = s.tick(4.8, main_running=False, voice_state="preloaded")
            self.assertNotIn("StartClip", _types(acts))
            acts = s.tick(4.8, main_running=True, voice_state="preloaded")
            self.assertIn("StartClip", _types(acts))

    def test_seek_does_not_duplicate_an_inflight_request(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.tick(1.0)
        s.on_seek(4.0, 1)
        self.assertNotIn("RequestTts", _types(s.tick(4.0)))
        s.clip_ready(0, 0, _clip())
        self.assertIn("PreloadClip", _types(s.tick(4.0)))

    def test_restart_event_without_jump_does_not_abandon_preload(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.clip_ready(0, 0, _clip())
        s.tick(4.0)
        s.tick(None, clock_epoch=1, voice_state="preloaded")
        acts = s.tick(4.8, clock_epoch=1, voice_state="preloaded")
        self.assertIn("StartClip", _types(acts))

    def _seg(self, seg_id=0, *, start=5.0, end=7.0, gen=0):
        return LiveSegment(seg_id, gen, start, end, "hello", text_tgt="ciao",
                           dub_ok=True)

    def test_requests_tts_for_a_translated_segment(self):
        s = _dub_sched()
        s.upsert(self._seg())
        acts = s.tick(1.0, mono=100.0, voice_state="idle")
        reqs = [a for a in acts if isinstance(a, RequestTts)]
        self.assertEqual(len(reqs), 1)
        self.assertEqual((reqs[0].seg_id, reqs[0].rate_pct), (0, 10))
        self.assertGreater(reqs[0].deadline_mono, 100.0)
        # no second request while it is being synthesized
        self.assertFalse([a for a in s.tick(1.1, mono=100.1, voice_state="idle")
                          if isinstance(a, RequestTts)])

    def test_full_flow_preload_duck_start_unduck(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.tick(1.0, mono=100.0, voice_state="idle")           # -> RequestTts
        s.clip_ready(0, 0, _clip(audible=1.8, vstart=0.1))
        # preload while the voice device is idle and we are inside the window
        acts = s.tick(4.0, mono=103.0, voice_state="idle")
        pre = [a for a in acts if isinstance(a, PreloadClip)]
        self.assertEqual(len(pre), 1)
        self.assertEqual((pre[0].seg_id, pre[0].skip_s), (0, 0.1))
        # duck ramp begins before the clip becomes audible
        acts = s.tick(4.5, mono=103.5, voice_state="preloaded")
        self.assertIn(0.3, [a.gain for a in acts if isinstance(a, Duck)])
        # start at start - lead
        acts = s.tick(4.8, mono=103.8, voice_state="preloaded")
        starts = [a for a in acts if isinstance(a, StartClip)]
        self.assertEqual(len(starts), 1)
        self.assertAlmostEqual(starts[0].speed, 1.0, places=3)
        self.assertEqual(s.metrics()["voiced"], 1.0)
        # clip ends -> unduck
        acts = s.tick(7.0, mono=106.0, voice_state="idle")
        self.assertIn(1.0, [a.gain for a in acts if isinstance(a, Duck)])

    def test_clip_none_drops_the_segment(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, None, reason="error")
        acts = s.tick(4.0, mono=103.0, voice_state="idle")
        self.assertFalse([a for a in acts if isinstance(a, PreloadClip)])
        self.assertEqual(s.metrics()["dropped"], 1.0)

    def test_late_clip_is_dropped(self):
        s = _dub_sched()
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        # never preloaded/started; now well past start - lead + tol (5.25)
        acts = s.tick(6.0, mono=105.0, voice_state="idle")
        self.assertIn("Drop", _types(acts))
        self.assertEqual(s.metrics()["late"], 1.0)

    def test_late_clip_is_recovered_while_the_pacer_holds_the_playhead(self):
        s = _dub_sched(max_live_lag_s=4.0)
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())

        acts = s.tick(6.0, mono=105.0, main_running=False,
                      voice_state="idle", pacer_paused=True)

        self.assertNotIn("Drop", _types(acts))
        self.assertIn("PreloadClip", _types(acts))
        self.assertTrue(s.pacer_recovery_pending)

        acts = s.tick(6.0, mono=105.02, main_running=False,
                      voice_state="preloaded", pacer_paused=True)
        self.assertIn("StartClip", _types(acts))
        self.assertTrue(s.pacer_recovery_pending)

        s.tick(6.0, mono=107.0, main_running=False,
               voice_state="idle", pacer_paused=True)
        self.assertFalse(s.pacer_recovery_pending)

    def test_late_clip_is_still_dropped_if_buffer_pause_is_too_old(self):
        s = _dub_sched(max_live_lag_s=4.0)
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        acts = s.tick(10.0, mono=109.0, main_running=False,
                      voice_state="idle", pacer_paused=True)
        self.assertIn("Drop", _types(acts))

    def test_a_dropped_clip_does_not_block_ready_until(self):
        # P0 (review finding 1): a dropped segment between two ready ones must not
        # stop coverage, or the FilePacer stalls the video at that hole.
        s = _dub_sched()
        for sid, st, en in [(0, 0.5, 2.0), (1, 2.0, 4.0), (2, 4.0, 6.0)]:
            s.upsert(LiveSegment(sid, 0, st, en, "h", text_tgt="ciao", dub_ok=True))
        s.clip_ready(0, 0, _clip())
        s.clip_ready(1, 0, None, reason="error")     # the middle clip failed
        s.clip_ready(2, 0, _clip())
        self.assertEqual(s.ready_until(0.0), 6.0)

    def test_a_stuck_synth_segment_expires(self):
        # review finding 1: a request that never returns must expire, not keep the
        # segment "synth" (and coverage blocked) forever.
        s = _dub_sched()
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")  # -> RequestTts, state synth
        self.assertEqual(s.ready_until(0.0), 0.0)     # blocked while pending
        s.tick(8.0, mono=107.0, voice_state="idle")  # past slot end (7.6): expires
        self.assertEqual(s.metrics()["dropped"], 1.0)

    def test_preloaded_clip_dropped_emits_stopclip(self):
        # review finding 4: a preloaded clip dropped as late must free the voice
        # device (StopClip), or the session's voice_state stays "preloaded".
        s = _dub_sched()
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        acts = s.tick(4.0, mono=103.0, voice_state="idle")   # preload (window 3.5..5.25)
        self.assertIn("PreloadClip", _types(acts))
        late = s.tick(6.0, mono=105.0, voice_state="idle")   # long stall, now late
        self.assertIn("StopClip", _types(late))
        self.assertIn("Drop", _types(late))

    def test_pause_and_resume_with_main_transport(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip(audible=1.8))
        s.tick(4.0, mono=103.0, voice_state="idle")           # preload
        s.tick(4.8, mono=103.8, voice_state="preloaded")      # start (expected_end 6.8)
        paused = s.tick(5.5, mono=104.5, main_running=False, voice_state="playing")
        self.assertIn("PauseClip", _types(paused))
        resumed = s.tick(5.6, mono=104.6, main_running=True, voice_state="paused")
        self.assertIn("ResumeClip", _types(resumed))

    def test_set_dub_off_stops_and_unducks(self):
        s = _dub_sched()
        s.upsert(self._seg())
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        s.tick(4.0, mono=103.0, voice_state="idle")           # preload
        s.tick(4.5, mono=103.5, voice_state="preloaded")      # duck starts (0.3)
        acts = s.set_dub(False)
        self.assertIn("StopClip", _types(acts))
        self.assertIn(1.0, [a.gain for a in acts if isinstance(a, Duck)])

    def test_ready_until_requires_the_clip_when_dub_is_on(self):
        s = _dub_sched()
        s.upsert(self._seg(start=0.5, end=2.0))
        # no clip yet: coverage does not extend past now
        self.assertEqual(s.ready_until(0.0), 0.0)
        s.tick(0.0, mono=100.0, voice_state="idle")           # requests tts
        s.clip_ready(0, 0, _clip())
        self.assertEqual(s.ready_until(0.0), 2.0)             # now the clip covers it

    def test_cache_replay_after_seek_avoids_a_new_request(self):
        s = _dub_sched()
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(1.0, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        s.on_seek(4.0, gen=1)                                  # seek back before it
        acts = s.tick(4.0, mono=110.0, voice_state="idle")
        self.assertFalse([a for a in acts if isinstance(a, RequestTts)])  # cached

    def test_live_mode_starts_asap_with_catchup_speed(self):
        s = _dub_sched(mode="live", max_live_lag_s=4.0)
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(6.0, mono=100.0, voice_state="idle")           # 1 s behind -> request
        s.clip_ready(0, 0, _clip(audible=2.0))
        acts = s.tick(6.1, mono=100.1, voice_state="idle")    # preload + duck together
        self.assertIn("PreloadClip", _types(acts))
        self.assertIn(0.3, [a.gain for a in acts if isinstance(a, Duck)])
        acts = s.tick(6.2, mono=100.2, voice_state="preloaded")
        starts = [a for a in acts if isinstance(a, StartClip)]
        self.assertEqual(len(starts), 1)
        self.assertGreater(starts[0].speed, 1.0)              # catch-up speed

    def test_live_mode_drops_segments_too_far_behind(self):
        s = _dub_sched(mode="live", max_live_lag_s=4.0)
        s.upsert(self._seg(start=5.0, end=7.0))
        s.tick(5.5, mono=100.0, voice_state="idle")
        s.clip_ready(0, 0, _clip())
        acts = s.tick(10.0, mono=104.5, voice_state="idle")   # 5 s behind > 4 s lag
        drops = [a for a in acts if isinstance(a, Drop)]
        self.assertTrue(drops and drops[0].reason == "lag")


class DuckEnvelopeTests(unittest.TestCase):
    def test_ramps_to_target_in_about_ten_small_steps(self):
        env = DuckEnvelope(ramp_s=0.2, tick_s=0.02)
        env.set_target(0.3)
        vals = []
        for _ in range(30):
            v = env.step()
            if v is None:
                break
            vals.append(v)
        self.assertAlmostEqual(vals[-1], 0.3, places=6)
        self.assertLessEqual(len(vals), 12)            # ~10 steps
        deltas = [abs(b - a) for a, b in zip([1.0, *vals], vals)]
        self.assertLessEqual(max(deltas), 0.07 + 1e-9)  # each step small

    def test_step_returns_none_at_target_and_when_frozen(self):
        env = DuckEnvelope()
        self.assertIsNone(env.step())                  # already at 1.0
        env.set_target(0.3)
        self.assertIsNone(env.step(frozen=True))       # frozen: no write
        self.assertEqual(env.current, 1.0)

    def test_snap_jumps_immediately(self):
        env = DuckEnvelope()
        env.set_target(0.3)
        env.step()
        self.assertEqual(env.snap(1.0), 1.0)
        self.assertIsNone(env.step())                  # nothing more to write

    def test_retarget_midramp_reaches_new_target(self):
        env = DuckEnvelope(ramp_s=0.2, tick_s=0.02)
        env.set_target(0.3)
        env.step()
        env.set_target(1.0)                            # unduck mid-ramp
        last = None
        for _ in range(30):
            v = env.step()
            if v is None:
                break
            last = v
        self.assertAlmostEqual(last, 1.0, places=6)


class FadeRampTests(unittest.TestCase):
    def test_fades_to_zero_over_steps(self):
        ramp = FadeRamp(1.0, fade_s=0.1, tick_s=0.02)   # ~5 steps
        vals = []
        while not ramp.done:
            vals.append(ramp.step())
        self.assertEqual(vals[-1], 0.0)
        self.assertLessEqual(len(vals), 6)
        self.assertTrue(all(b <= a for a, b in zip([1.0, *vals], vals)))

    def test_zero_fade_is_immediate(self):
        ramp = FadeRamp(0.8, fade_s=0.0)
        self.assertTrue(ramp.done)
        self.assertEqual(ramp.step(), 0.0)


if __name__ == "__main__":
    unittest.main()
