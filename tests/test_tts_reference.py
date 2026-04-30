import subprocess
import unittest

from videotranslator.tts_reference import (
    build_speaker_reference_filter,
    build_vad_reference_tiered,
    extract_speaker_reference,
    merge_vad_timestamps,
    safe_speaker_name,
    select_speaker_turns,
    select_vad_reference_ranges,
)


class TtsReferenceTests(unittest.TestCase):
    def test_safe_speaker_name(self):
        self.assertEqual(safe_speaker_name("SPEAKER 01:/x"), "SPEAKER_01__x")

    def test_select_speaker_turns_prefers_long_turns_and_caps_duration(self):
        diar = [
            {"speaker": "A", "start": 0.0, "end": 0.5},
            {"speaker": "A", "start": 2.0, "end": 7.0},
            {"speaker": "B", "start": 8.0, "end": 20.0},
            {"speaker": "A", "start": 10.0, "end": 30.0},
        ]

        self.assertEqual(
            select_speaker_turns(diar, "A", max_duration=8.0),
            [(10.0, 18.0)],
        )

    def test_build_speaker_reference_filter(self):
        filt = build_speaker_reference_filter([(1.0, 2.5), (4.0, 5.0)])

        self.assertIn("[0:a]atrim=start=1.000:end=2.500", filt)
        self.assertIn("[a0][a1]concat=n=2:v=0:a=1[out]", filt)

    def test_extract_speaker_reference_builds_ffmpeg_command(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0)

        out = extract_speaker_reference(
            "/tmp/vocals.wav",
            [{"speaker": "A/B", "start": 1.0, "end": 4.0}],
            "A/B",
            "/tmp/work",
            run=fake_run,
        )

        self.assertEqual(out, "/tmp/work/ref_A_B.wav")
        cmd = calls[0][0]
        self.assertEqual(cmd[:4], ["ffmpeg", "-y", "-i", "/tmp/vocals.wav"])
        self.assertIn("-filter_complex", cmd)
        self.assertIn("/tmp/work/ref_A_B.wav", cmd)

    def test_extract_speaker_reference_returns_none_without_turns(self):
        self.assertIsNone(extract_speaker_reference("/tmp/in.wav", [], "A", "/tmp/work"))

    def test_extract_speaker_reference_logs_ffmpeg_failure(self):
        logs = []

        def fake_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, cmd)

        self.assertIsNone(
            extract_speaker_reference(
                "/tmp/in.wav",
                [{"speaker": "A", "start": 1.0, "end": 2.5}],
                "A",
                "/tmp/work",
                run=fake_run,
                log=lambda *args, **kwargs: logs.append(" ".join(str(arg) for arg in args)),
            )
        )
        self.assertTrue(any("Could not extract reference" in item for item in logs))

    def test_merge_vad_timestamps_merges_short_gaps(self):
        merged = merge_vad_timestamps(
            [
                {"start": 0.0, "end": 1.0},
                {"start": 1.2, "end": 2.0},
                {"start": 3.0, "end": 4.0},
            ],
            max_gap_ms=300,
        )

        self.assertEqual(merged, [(0.0, 2.0), (3.0, 4.0)])

    def test_select_vad_reference_ranges_prefers_longest_or_enough_speech(self):
        self.assertEqual(
            select_vad_reference_ranges([(0.0, 20.0), (25.0, 30.0)], target_seconds=18.0),
            [(0.0, 20.0)],
        )
        self.assertEqual(
            select_vad_reference_ranges(
                [(0.0, 2.0), (5.0, 7.0), (10.0, 12.0)],
                target_seconds=5.0,
                min_seconds=3.0,
            ),
            [(0.0, 2.0), (5.0, 7.0), (10.0, 12.0)],
        )
        self.assertIsNone(
            select_vad_reference_ranges([(0.0, 1.0)], target_seconds=5.0, min_seconds=3.0)
        )

    def test_build_vad_reference_tiered_tries_descending_targets(self):
        seen = []

        def fake_builder(src_audio, out_wav, target_seconds):
            seen.append(target_seconds)
            return out_wav if target_seconds == 12.0 else None

        logs = []
        result = build_vad_reference_tiered(
            "in.wav",
            "out.wav",
            targets=(18.0, 15.0, 12.0),
            builder=fake_builder,
            log=lambda *args, **kwargs: logs.append(" ".join(str(arg) for arg in args)),
        )

        self.assertEqual(result, "out.wav")
        self.assertEqual(seen, [18.0, 15.0, 12.0])
        self.assertTrue(any("fallback target 12s" in item for item in logs))


if __name__ == "__main__":
    unittest.main()
