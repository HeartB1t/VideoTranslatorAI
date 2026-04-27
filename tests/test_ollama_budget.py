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

    def test_qwen3_thinking_retry_quadruples_budget(self):
        # Qwen3 thinking can produce huge chain-of-thought on dense segments;
        # the retry needs significantly more headroom than just 2x. Bumped to
        # 4x after observing seg #24 still fail at 2x in production.
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

        self.assertEqual(retry, first * 4)

    def test_non_qwen3_retry_only_doubles(self):
        # Other models do not have CoT, so doubling stays sufficient and
        # avoids burning Ollama time on a giant budget that will not be used.
        first = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=False,
            thinking=False,
        )
        retry = legacy._ollama_num_predict_for_segment(
            "A short segment.",
            is_qwen3=False,
            thinking=False,
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

