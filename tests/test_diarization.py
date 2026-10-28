import sys
import types
import unittest
from unittest import mock

from videotranslator import diarization


class AssignSpeakersTests(unittest.TestCase):
    def test_picks_speaker_with_largest_overlap(self):
        segs = [{"start": 0.0, "end": 4.0}, {"start": 4.0, "end": 6.0}]
        diar = [
            {"start": 0.0, "end": 1.0, "speaker": "A"},
            {"start": 1.0, "end": 5.5, "speaker": "B"},
        ]
        out = diarization.assign_speakers(segs, diar)
        self.assertEqual([s["speaker"] for s in out], ["B", "B"])

    def test_no_overlap_leaves_segment_untouched(self):
        segs = [{"start": 10.0, "end": 11.0}]
        out = diarization.assign_speakers(segs, [{"start": 0.0, "end": 1.0, "speaker": "A"}])
        self.assertNotIn("speaker", out[0])

    def test_empty_diarization_returns_input(self):
        segs = [{"start": 0.0, "end": 1.0}]
        self.assertIs(diarization.assign_speakers(segs, []), segs)


class DiarizeAudioTests(unittest.TestCase):
    def _fake_pyannote(self, pipeline):
        audio = types.ModuleType("pyannote.audio")
        audio.Pipeline = mock.Mock()
        audio.Pipeline.from_pretrained.return_value = pipeline
        root = types.ModuleType("pyannote")
        root.audio = audio
        return {"pyannote": root, "pyannote.audio": audio}

    def test_returns_turns_from_pipeline(self):
        turn = types.SimpleNamespace(start=0.5, end=2.0)
        result = mock.Mock()
        result.itertracks.return_value = [(turn, None, "SPEAKER_00")]
        pipeline = mock.Mock(return_value=result)
        modules = self._fake_pyannote(pipeline)
        with mock.patch.dict(sys.modules, modules), mock.patch("builtins.print"):
            segs = diarization.diarize_audio("vocals.wav", "hf_x")
        self.assertEqual(segs, [{"start": 0.5, "end": 2.0, "speaker": "SPEAKER_00"}])
        modules["pyannote.audio"].Pipeline.from_pretrained.assert_called_once_with(
            diarization.DIARIZATION_MODEL, use_auth_token="hf_x"
        )
        pipeline.assert_called_once_with("vocals.wav")

    def test_from_pretrained_error_propagates(self):
        modules = self._fake_pyannote(None)
        modules["pyannote.audio"].Pipeline.from_pretrained.side_effect = RuntimeError("401")
        with mock.patch.dict(sys.modules, modules), mock.patch("builtins.print"):
            with self.assertRaises(RuntimeError):
                diarization.diarize_audio("vocals.wav", "bad")


if __name__ == "__main__":
    unittest.main()
