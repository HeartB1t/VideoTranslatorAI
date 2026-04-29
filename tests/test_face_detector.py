import os
import tempfile
import unittest
from unittest import mock

from videotranslator.face_detector import (
    DEFAULT_MIN_FACE_RATIO,
    DEFAULT_SAMPLE_FRAMES,
    compute_face_ratio,
    count_face_frames,
    decide_has_faces,
    sample_frames_via_ffmpeg,
)


class ComputeFaceRatioTests(unittest.TestCase):
    def test_zero_total_returns_zero(self):
        self.assertEqual(compute_face_ratio(0, 0), 0.0)
        self.assertEqual(compute_face_ratio(5, 0), 0.0)

    def test_negative_face_count_returns_zero(self):
        self.assertEqual(compute_face_ratio(-1, 10), 0.0)

    def test_face_count_above_total_clamps_to_one(self):
        self.assertEqual(compute_face_ratio(20, 10), 1.0)

    def test_basic_ratio(self):
        self.assertEqual(compute_face_ratio(3, 10), 0.3)
        self.assertEqual(compute_face_ratio(0, 10), 0.0)
        self.assertEqual(compute_face_ratio(10, 10), 1.0)


class DecideHasFacesTests(unittest.TestCase):
    def test_above_threshold_true(self):
        self.assertTrue(decide_has_faces(0.30, min_face_ratio=0.20))
        self.assertTrue(decide_has_faces(0.20, min_face_ratio=0.20))

    def test_below_threshold_false(self):
        self.assertFalse(decide_has_faces(0.19, min_face_ratio=0.20))
        self.assertFalse(decide_has_faces(0.0, min_face_ratio=0.20))

    def test_zero_threshold_means_any_face(self):
        self.assertTrue(decide_has_faces(0.05, min_face_ratio=0))
        self.assertFalse(decide_has_faces(0.0, min_face_ratio=0))

    def test_default_threshold_value_is_sensible(self):
        # Voice-only video with 0% ratio must NOT pass under defaults.
        self.assertFalse(decide_has_faces(0.0, min_face_ratio=DEFAULT_MIN_FACE_RATIO))
        # Talking-head with 90% must pass.
        self.assertTrue(decide_has_faces(0.9, min_face_ratio=DEFAULT_MIN_FACE_RATIO))


class CountFaceFramesTests(unittest.TestCase):
    def test_empty_input(self):
        face, total = count_face_frames([])
        self.assertEqual(face, 0)
        self.assertEqual(total, 0)

    def test_counts_frames_with_faces(self):
        # Mock count_faces_in_frame so we don't need real images.
        with mock.patch(
            "videotranslator.face_detector.count_faces_in_frame",
            side_effect=lambda p: 1 if "yes" in p else 0,
        ):
            face, total = count_face_frames(["yes_a", "no_b", "yes_c", "no_d"])
            self.assertEqual(face, 2)
            self.assertEqual(total, 4)

    def test_multiple_faces_per_frame_still_count_once(self):
        # If a frame has 3 faces it still contributes 1 to face_frames
        # (we are gating Wav2Lip presence/absence, not headcount).
        with mock.patch(
            "videotranslator.face_detector.count_faces_in_frame",
            return_value=3,
        ):
            face, total = count_face_frames(["a", "b"])
            self.assertEqual(face, 2)
            self.assertEqual(total, 2)


class SampleFramesViaFfmpegTests(unittest.TestCase):
    def test_zero_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(sample_frames_via_ffmpeg("/nonexistent.mp4", tmp, 0), [])

    def test_missing_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                sample_frames_via_ffmpeg("/definitely_not_a_file.mp4", tmp, 5),
                [],
            )


class DefaultsAreSaneTests(unittest.TestCase):
    def test_defaults_are_positive(self):
        self.assertGreater(DEFAULT_SAMPLE_FRAMES, 0)
        self.assertGreater(DEFAULT_MIN_FACE_RATIO, 0)
        self.assertLess(DEFAULT_MIN_FACE_RATIO, 1.0)

    def test_defaults_match_documented_intent(self):
        # 15 sample frames keeps the check under a second on CPU.
        self.assertLessEqual(DEFAULT_SAMPLE_FRAMES, 30)
        # 0.20 ratio keeps the gate tolerant of hybrid videos.
        self.assertLessEqual(DEFAULT_MIN_FACE_RATIO, 0.30)


if __name__ == "__main__":
    unittest.main()
