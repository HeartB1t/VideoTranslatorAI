import unittest

from videotranslator.ollama_model_selector import (
    DEFAULT_PREFERRED_FAMILIES,
    select_compatible_model,
)


class SelectCompatibleModelTests(unittest.TestCase):
    def test_empty_available_returns_none(self):
        self.assertIsNone(select_compatible_model("qwen3:14b", []))

    def test_exact_match_returned_unchanged(self):
        avail = ["qwen3:14b", "qwen2.5:7b-instruct"]
        self.assertEqual(select_compatible_model("qwen3:14b", avail), "qwen3:14b")

    def test_prefix_match_quantization_tail(self):
        # User has "qwen2.5:7b-instruct-q4_K_M" installed and asks for the
        # plain "qwen2.5:7b-instruct" tag.
        avail = ["qwen2.5:7b-instruct-q4_K_M", "qwen3:14b"]
        self.assertEqual(
            select_compatible_model("qwen2.5:7b-instruct", avail),
            "qwen2.5:7b-instruct-q4_K_M",
        )

    def test_same_base_family_picks_largest(self):
        # User asks for qwen3:8b but has qwen3:14b and qwen3:4b installed
        # → 14b wins (larger).
        avail = ["qwen3:4b", "qwen3:14b"]
        self.assertEqual(
            select_compatible_model("qwen3:8b", avail),
            "qwen3:14b",
        )

    def test_real_world_mistral_nemo_missing_qwen3_available(self):
        # The 2026-04-29 production case: config wants
        # mistral-nemo:12b-instruct, daemon has qwen3:14b and qwen2.5:7b.
        # qwen3 is the first preferred family → must win.
        avail = ["qwen3:14b", "qwen2.5:7b-instruct"]
        self.assertEqual(
            select_compatible_model("mistral-nemo:12b-instruct", avail),
            "qwen3:14b",
        )

    def test_preferred_family_picks_largest_within_family(self):
        # Requested family absent. Daemon has only qwen2.5 in two sizes.
        avail = ["qwen2.5:7b-instruct", "qwen2.5:14b"]
        self.assertEqual(
            select_compatible_model("llama3:8b", avail),
            "qwen2.5:14b",
        )

    def test_preferred_family_order_is_respected(self):
        # When several preferred families are available, the earlier one
        # in the ranking wins (qwen3 before mistral, both present).
        avail = ["mistral:7b", "qwen3:8b"]
        self.assertEqual(
            select_compatible_model("does-not-exist", avail),
            "qwen3:8b",
        )

    def test_no_preferred_family_falls_back_to_largest(self):
        # All available models are unknown families. Pick the largest by
        # parameter count, ties broken alphabetically.
        avail = ["weirdmodel:3b", "weirdmodel:13b", "obscure:7b"]
        out = select_compatible_model("qwen3:14b", avail, preferred_families=())
        self.assertEqual(out, "weirdmodel:13b")

    def test_size_parsing_handles_quantization_suffix(self):
        # Tags with quantization indicators must still parse the size.
        avail = ["qwen3:8b-instruct-q4_K_M", "qwen3:14b"]
        self.assertEqual(
            select_compatible_model("qwen3:7b", avail),
            "qwen3:14b",
        )

    def test_empty_requested_goes_to_preferred_families(self):
        # No request → straight to step 4.
        avail = ["mistral:7b", "qwen3:14b"]
        self.assertEqual(
            select_compatible_model("", avail),
            "qwen3:14b",
        )

    def test_none_requested_goes_to_preferred_families(self):
        avail = ["llama3:8b", "qwen2.5:14b"]
        self.assertEqual(
            select_compatible_model(None, avail),
            "qwen2.5:14b",
        )

    def test_unparseable_size_does_not_crash(self):
        # Tag without ":Nb" pattern is allowed (size 0).
        avail = ["plain-model", "qwen3:8b"]
        self.assertEqual(
            select_compatible_model("missing", avail),
            "qwen3:8b",
        )

    def test_default_preferred_families_starts_with_qwen3(self):
        # Sanity check: qwen3 must be the first preferred family.
        self.assertEqual(DEFAULT_PREFERRED_FAMILIES[0], "qwen3")


if __name__ == "__main__":
    unittest.main()
