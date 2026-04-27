import unittest

import video_translator_gui as legacy


class OllamaBudgetTests(unittest.TestCase):
    def test_qwen3_thinking_uses_large_initial_budget(self):
        budget = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=True,
            thinking=True,
        )

        self.assertEqual(budget, 4096)

    def test_qwen3_thinking_retry_doubles_budget(self):
        first = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=True,
            thinking=True,
        )
        retry = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=True,
            thinking=True,
            retry=1,
        )

        self.assertEqual(retry, first * 2)

    def test_non_thinking_keeps_small_budget(self):
        budget = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=True,
            thinking=False,
        )

        self.assertEqual(budget, 64)


if __name__ == "__main__":
    unittest.main()

