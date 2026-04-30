import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from videotranslator.edge_tts_engine import generate_tts, tts_all, tts_segment


class FakeCommunicate:
    attempts = 0
    fail_until = 0
    calls = []

    def __init__(self, text, voice, rate="+0%"):
        self.text = text
        self.voice = voice
        self.rate = rate
        self.__class__.calls.append((text, voice, rate))

    async def save(self, out_path):
        self.__class__.attempts += 1
        if self.__class__.attempts <= self.__class__.fail_until:
            raise RuntimeError("temporary")
        Path(out_path).write_text(self.text, encoding="utf-8")


class EdgeTtsSegmentTests(unittest.TestCase):
    def setUp(self):
        FakeCommunicate.attempts = 0
        FakeCommunicate.fail_until = 0
        FakeCommunicate.calls = []

    def test_tts_segment_saves_file(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            out = os.path.join(tmp_str, "seg.mp3")

            asyncio.run(
                tts_segment(
                    "ciao",
                    "it-IT-Test",
                    out,
                    rate="+5%",
                    communicate_factory=FakeCommunicate,
                )
            )

            self.assertTrue(os.path.exists(out))
            self.assertEqual(FakeCommunicate.calls, [("ciao", "it-IT-Test", "+5%")])

    def test_tts_segment_retries_before_success(self):
        FakeCommunicate.fail_until = 2
        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        with tempfile.TemporaryDirectory() as tmp_str:
            out = os.path.join(tmp_str, "seg.mp3")

            asyncio.run(
                tts_segment(
                    "ciao",
                    "it-IT-Test",
                    out,
                    retries=3,
                    communicate_factory=FakeCommunicate,
                    sleep=fake_sleep,
                    log=lambda *args, **kwargs: None,
                )
            )

            self.assertTrue(os.path.exists(out))
            self.assertEqual(sleeps, [1, 2])


class EdgeTtsAllTests(unittest.TestCase):
    def test_tts_all_skips_empty_segments_and_returns_expected_paths(self):
        seen = []

        async def fake_runner(text, voice, out_path, rate="+0%"):
            seen.append((text, voice, Path(out_path).name, rate))
            Path(out_path).write_text(text, encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp_str:
            files = asyncio.run(
                tts_all(
                    [{"text_tgt": "uno"}, {"text_tgt": "  "}, {"text_tgt": "due"}],
                    "voice",
                    tmp_str,
                    "+0%",
                    segment_runner=fake_runner,
                    log=lambda *args, **kwargs: None,
                )
            )

            self.assertEqual([Path(p).name for p in files], ["seg_0000.mp3", "seg_0001.mp3", "seg_0002.mp3"])
            self.assertEqual(seen, [("uno", "voice", "seg_0000.mp3", "+0%"), ("due", "voice", "seg_0002.mp3", "+0%")])

    def test_generate_tts_uses_runner_and_logs(self):
        logs = []

        async def fake_all_runner(segments, voice, tmp_dir, rate):
            return [os.path.join(tmp_dir, "seg_0000.mp3")]

        files = generate_tts(
            [{"text_tgt": "uno"}],
            "voice",
            "/tmp/work",
            rate="-10%",
            all_runner=fake_all_runner,
            log=lambda *args, **kwargs: logs.append(" ".join(str(arg) for arg in args)),
        )

        self.assertEqual(files, ["/tmp/work/seg_0000.mp3"])
        self.assertTrue(any("Generating TTS" in item for item in logs))


if __name__ == "__main__":
    unittest.main()
