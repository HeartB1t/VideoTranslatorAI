import unittest

import numpy as np

from videotranslator.live_segment import (
    SentenceAssembler,
    Utterance,
    UtteranceSegmenter,
)

FRAME = 512
SR = 16000
FRAME_S = FRAME / SR  # 0.032


def _samples(n):
    return np.ones(FRAME * n, dtype=np.float32)


class UtteranceSegmenterTests(unittest.TestCase):
    def test_starts_on_speech_and_ends_after_silence(self):
        seg = UtteranceSegmenter()
        probs = [0.9] * 10 + [0.0] * 13   # ~0.416 s of silence ends it
        out = seg.push(0.0, _samples(len(probs)), probs)
        self.assertEqual(len(out), 1)
        utt = out[0]
        self.assertIsInstance(utt, Utterance)
        self.assertFalse(utt.forced_cut)
        self.assertAlmostEqual(utt.start, 0.0, places=6)
        # last speech frame is index 9; keep 5 pad frames -> 15 frames total.
        self.assertEqual(len(utt.samples), 15 * FRAME)
        self.assertAlmostEqual(utt.end, 15 * FRAME_S, places=6)

    def test_leading_padding_extends_start_before_speech(self):
        seg = UtteranceSegmenter()
        probs = [0.1, 0.1, 0.9] + [0.0] * 14
        out = seg.push(0.0, _samples(len(probs)), probs)
        self.assertEqual(len(out), 1)
        # start includes the two pre-speech frames
        self.assertAlmostEqual(out[0].start, 0.0, places=6)

    def test_discontinuity_flushes_active_utterance(self):
        seg = UtteranceSegmenter()
        seg.push(0.0, _samples(5), [0.9] * 5)          # active, no end
        out = seg.push(1.0, _samples(5), [0.0] * 5)    # 0.84 s gap -> flush
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0].forced_cut)

    def test_max_length_forces_a_cut(self):
        seg = UtteranceSegmenter(max_len_s=0.3)
        out = seg.push(0.0, _samples(20), [0.9] * 20)
        self.assertTrue(any(u.forced_cut for u in out))

    def test_flush_emits_active_utterance(self):
        seg = UtteranceSegmenter()
        seg.push(0.0, _samples(5), [0.9] * 5)
        out = seg.flush()
        self.assertEqual(len(out), 1)
        self.assertFalse(out[0].forced_cut)

    def test_reset_sets_generation(self):
        seg = UtteranceSegmenter()
        seg.reset(7)
        out = seg.push(0.0, _samples(23), [0.9] * 10 + [0.0] * 13)
        self.assertEqual(out[0].gen, 7)


class SentenceAssemblerTests(unittest.TestCase):
    def test_flushes_on_end_punctuation(self):
        asm = SentenceAssembler(hold_s=1.5)
        out = asm.push([{"start": 0.0, "end": 1.0, "text": "Hello."}], gen=0)
        self.assertEqual([s.text for s in out], ["Hello."])
        self.assertEqual(out[0].seg_id, 0)
        self.assertEqual(out[0].gen, 0)

    def test_holds_then_flushes_on_edge(self):
        asm = SentenceAssembler(hold_s=1.5)
        self.assertEqual(asm.push([{"start": 0.0, "end": 1.0, "text": "no punct"}], gen=0), [])
        self.assertEqual(asm.edge(1.4), [])          # 0.4 s < hold
        out = asm.edge(2.5)                            # 1.5 s >= hold
        self.assertEqual([s.text for s in out], ["no punct"])

    def test_flushes_on_word_cap(self):
        asm = SentenceAssembler(hold_s=1.5, max_words=30)
        text = " ".join(["word"] * 30)
        out = asm.push([{"start": 0.0, "end": 5.0, "text": text}], gen=0)
        self.assertEqual(len(out), 1)

    def test_multi_sentence_split(self):
        asm = SentenceAssembler(hold_s=1.5)
        # A span long enough that both halves clear split_on_punctuation's
        # default 1 s minimum piece duration.
        out = asm.push([{"start": 0.0, "end": 4.0, "text": "Ciao mondo. Come stai?"}], gen=0)
        self.assertEqual([s.text for s in out], ["Ciao mondo.", "Come stai?"])
        self.assertLess(out[0].start, out[1].start)
        self.assertEqual([s.seg_id for s in out], [0, 1])

    def test_generation_change_resets_buffer(self):
        asm = SentenceAssembler(hold_s=1.5)
        asm.push([{"start": 0.0, "end": 1.0, "text": "partial"}], gen=0)
        out = asm.push([{"start": 5.0, "end": 6.0, "text": "fresh."}], gen=1)
        self.assertEqual([s.text for s in out], ["fresh."])
        self.assertEqual(out[0].gen, 1)


if __name__ == "__main__":
    unittest.main()
