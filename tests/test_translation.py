import unittest

from videotranslator.translation import _marian_normalize_lang, translate_segments


class TranslationDispatcherTests(unittest.TestCase):
    def test_marian_normalize_lang(self):
        self.assertEqual(_marian_normalize_lang("zh-CN"), "zh")
        self.assertEqual(_marian_normalize_lang("no"), "nb")
        self.assertEqual(_marian_normalize_lang("it-IT"), "it")

    def test_ollama_engine_uses_injected_translator(self):
        seen = {}

        def fake_ollama(segments, source, target, **kwargs):
            seen["source"] = source
            seen["target"] = target
            seen["kwargs"] = kwargs
            return [{"start": 0.0, "end": 1.0, "text_src": "hello", "text_tgt": "ciao"}]

        result = translate_segments(
            [{"start": 0.0, "end": 1.0, "text": "hello"}],
            "en",
            "it",
            engine="llm_ollama",
            ollama_model="qwen3:14b",
            ollama_thinking=True,
            ollama_translator=fake_ollama,
        )

        self.assertEqual(result[0]["text_tgt"], "ciao")
        self.assertEqual(seen["source"], "en")
        self.assertEqual(seen["target"], "it")
        self.assertEqual(seen["kwargs"]["model"], "qwen3:14b")
        self.assertTrue(seen["kwargs"]["thinking"])


if __name__ == "__main__":
    unittest.main()
