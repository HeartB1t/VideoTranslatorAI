"""Unit tests for the pure audio-stretch policy helpers.

These tests intentionally do not invoke any subprocess: they exercise
only the decision logic and the argv builder. The runtime fallback that
catches a missing or failing ``rubberband`` binary lives in
``video_translator_gui.build_dubbed_track`` and is covered separately by
the smoke tests run on real videos.
"""

import unittest

from videotranslator.audio_stretch import (
    build_rubberband_command,
    compute_overlap_strategy,
    select_stretch_engine,
)


class SelectStretchEngineTests(unittest.TestCase):
    # ── Below the band ──────────────────────────────────────────────────
    def test_below_band_returns_atempo_even_if_rubberband_present(self):
        self.assertEqual(select_stretch_engine(1.05, True), "atempo")

    def test_below_band_without_rubberband_returns_atempo(self):
        self.assertEqual(select_stretch_engine(1.05, False), "atempo")

    # ── Inside the band ─────────────────────────────────────────────────
    def test_inside_band_with_rubberband_picks_rubberband(self):
        self.assertEqual(select_stretch_engine(1.30, True), "rubberband")

    def test_inside_band_without_rubberband_falls_back_to_atempo(self):
        # Critical no-regression invariant: missing binary must never
        # crash the pipeline, it just degrades to the legacy engine.
        self.assertEqual(select_stretch_engine(1.30, False), "atempo")

    # ── Edges of the band (inclusive) ───────────────────────────────────
    def test_lower_edge_inclusive_with_rubberband(self):
        self.assertEqual(select_stretch_engine(1.15, True), "rubberband")

    def test_upper_edge_inclusive_with_rubberband(self):
        self.assertEqual(select_stretch_engine(1.50, True), "rubberband")

    def test_just_below_lower_edge_returns_atempo(self):
        self.assertEqual(select_stretch_engine(1.149, True), "atempo")

    def test_just_above_upper_edge_returns_atempo(self):
        self.assertEqual(select_stretch_engine(1.501, True), "atempo")

    # ── Above the band ──────────────────────────────────────────────────
    def test_above_band_with_rubberband_returns_atempo(self):
        # Rubber Band itself degrades past ~1.5x; atempo behaves more
        # predictably on heavy compression.
        self.assertEqual(select_stretch_engine(1.80, True), "atempo")

    def test_severe_ratio_returns_atempo(self):
        self.assertEqual(select_stretch_engine(3.50, True), "atempo")

    # ── Custom band overrides ───────────────────────────────────────────
    def test_custom_band_is_honoured(self):
        # Caller can broaden the band experimentally without code edits.
        self.assertEqual(
            select_stretch_engine(1.70, True, rb_min=1.10, rb_max=1.80),
            "rubberband",
        )

    def test_unavailable_short_circuits_before_band_check(self):
        # Even with a custom band that would include the ratio, lack of
        # the binary still yields atempo.
        self.assertEqual(
            select_stretch_engine(1.70, False, rb_min=1.10, rb_max=1.80),
            "atempo",
        )


class BuildRubberbandCommandTests(unittest.TestCase):
    def test_first_token_is_the_binary_name(self):
        cmd = build_rubberband_command("in.wav", "out.wav", 1.30)
        self.assertEqual(cmd[0], "rubberband")

    def test_includes_formant_flag(self):
        cmd = build_rubberband_command("in.wav", "out.wav", 1.30)
        self.assertIn("--formant", cmd)

    def test_tempo_flag_uses_ratio_directly(self):
        # ratio == tempo multiplier per CLI semantics ("-T X" == "--time 1/X").
        cmd = build_rubberband_command("in.wav", "out.wav", 1.25)
        self.assertIn("-T", cmd)
        idx = cmd.index("-T")
        self.assertEqual(float(cmd[idx + 1]), 1.25)

    def test_inverse_relation_holds_for_other_ratio(self):
        # Spec sanity check: "ratio 2.0 → tempo 2.0", which means -T 2.0
        # (i.e. output duration = 1/2.0 of input). The flag value matches
        # the ratio, the inversion happens inside Rubber Band.
        cmd = build_rubberband_command("in.wav", "out.wav", 2.0)
        idx = cmd.index("-T")
        self.assertAlmostEqual(float(cmd[idx + 1]), 2.0)

    def test_input_and_output_paths_are_last_two_tokens(self):
        cmd = build_rubberband_command("/tmp/seg.wav", "/tmp/seg_sped.wav", 1.30)
        self.assertEqual(cmd[-2], "/tmp/seg.wav")
        self.assertEqual(cmd[-1], "/tmp/seg_sped.wav")

    def test_zero_ratio_raises(self):
        with self.assertRaises(ValueError):
            build_rubberband_command("in.wav", "out.wav", 0.0)

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            build_rubberband_command("in.wav", "out.wav", -1.0)

    def test_command_is_a_plain_list(self):
        # Important for subprocess.run(shell=False): no tuples, no shell
        # metacharacters, every token a str.
        cmd = build_rubberband_command("in.wav", "out.wav", 1.30)
        self.assertIsInstance(cmd, list)
        for token in cmd:
            self.assertIsInstance(token, str)


class ComputeOverlapStrategyTests(unittest.TestCase):
    """TASK 2P: pure tests for the overlap-vs-truncate decision helper."""

    # 44.1 kHz reference: 400 ms = 17_640 frames, 200 ms = 8_820 frames.
    SR = 44100
    MAX_OVERLAP = int(0.40 * SR)  # 17_640

    # ── Fit (no overshoot) ──────────────────────────────────────────────
    def test_pcm_shorter_than_slot_returns_fit(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=self.SR,           # 1 s
            slot_frames=2 * self.SR,      # 2 s
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "fit")
        self.assertEqual(target, self.SR)
        self.assertEqual(fade, 0)

    def test_pcm_equal_to_slot_returns_fit(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR,
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "fit")
        self.assertEqual(fade, 0)

    # ── Overlap clean (mild overshoot, fits within max_overlap) ─────────
    def test_mild_overshoot_uses_overlap_clean(self):
        # 200 ms overshoot, well within the 400 ms cap.
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR + int(0.20 * self.SR),
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "overlap_clean")
        # Full pcm is preserved.
        self.assertEqual(target, 2 * self.SR + int(0.20 * self.SR))
        # Fade equals min(MAX_OVERLAP/2, overshoot).
        self.assertEqual(fade, int(0.20 * self.SR))

    def test_overshoot_at_max_uses_overlap_clean(self):
        # Overshoot exactly at the boundary stays in overlap_clean.
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR + self.MAX_OVERLAP,
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "overlap_clean")
        self.assertEqual(target, 2 * self.SR + self.MAX_OVERLAP)
        # Fade capped at MAX_OVERLAP/2 = 200 ms, never the full overshoot.
        self.assertEqual(fade, self.MAX_OVERLAP // 2)

    # ── Overlap truncate (overshoot beyond budget) ──────────────────────
    def test_overshoot_beyond_budget_uses_overlap_truncate(self):
        # 1 s overshoot, far beyond the 400 ms cap.
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR + 1 * self.SR,
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "overlap_truncate")
        # Capped at slot + max_overlap.
        self.assertEqual(target, 2 * self.SR + self.MAX_OVERLAP)
        self.assertGreater(fade, 0)
        self.assertLessEqual(fade, self.MAX_OVERLAP // 2)

    # ── Last segment: never overlaps (no neighbour slot) ────────────────
    def test_last_segment_overshoot_falls_back_to_truncate(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR + int(0.20 * self.SR),
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
            is_last_segment=True,
        )
        self.assertEqual(strat, "truncate")
        # Target equals slot length (no overflow allowed past video end).
        self.assertEqual(target, 2 * self.SR)
        self.assertGreater(fade, 0)

    def test_last_segment_no_overshoot_still_returns_fit(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=self.SR,
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
            is_last_segment=True,
        )
        self.assertEqual(strat, "fit")
        self.assertEqual(fade, 0)

    # ── Opt-out: overlap disabled by CLI ────────────────────────────────
    def test_overlap_disabled_uses_legacy_truncate(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=2 * self.SR + int(0.20 * self.SR),
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
            overlap_enabled=False,
        )
        self.assertEqual(strat, "truncate")
        self.assertEqual(target, 2 * self.SR)
        self.assertGreater(fade, 0)

    # ── Defensive edge cases ────────────────────────────────────────────
    def test_zero_pcm_returns_fit(self):
        strat, target, fade = compute_overlap_strategy(
            pcm_frames=0,
            slot_frames=2 * self.SR,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "fit")
        self.assertEqual(target, 0)
        self.assertEqual(fade, 0)

    def test_zero_slot_returns_fit(self):
        # Degenerate slot: caller will skip, helper must not divide by zero.
        strat, _target, fade = compute_overlap_strategy(
            pcm_frames=1000,
            slot_frames=0,
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "fit")
        self.assertEqual(fade, 0)

    def test_fade_never_exceeds_pcm_length(self):
        # Tiny pcm with tiny overshoot — fade must shrink, not be 200 ms.
        strat, _target, fade = compute_overlap_strategy(
            pcm_frames=100,         # 100 frames of pcm
            slot_frames=80,         # 20-frame overshoot
            max_overlap_frames=self.MAX_OVERLAP,
        )
        self.assertEqual(strat, "overlap_clean")
        self.assertLessEqual(fade, 100)
        self.assertLessEqual(fade, 20)  # bounded by overshoot
        self.assertGreaterEqual(fade, 1)


if __name__ == "__main__":
    unittest.main()
