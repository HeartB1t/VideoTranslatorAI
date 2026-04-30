import subprocess
import unittest

from videotranslator.tts_reference import (
    build_speaker_reference_filter,
    extract_speaker_reference,
    safe_speaker_name,
    select_speaker_turns,
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


if __name__ == "__main__":
    unittest.main()
