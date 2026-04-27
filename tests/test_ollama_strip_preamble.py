import unittest

import video_translator_gui as legacy

strip = legacy._ollama_strip_preamble


class OllamaStripPreambleThinkTests(unittest.TestCase):
    """Edge case sui blocchi <think> di Qwen3.

    Questi sono i casi che, se mal gestiti, producono `keeping source: empty
    response` durante la traduzione. La logica vive in
    `_ollama_strip_preamble()` step 0/0b.
    """

    def test_closed_think_block_then_translation(self):
        raw = "<think>let me think about this</think>Buongiorno a tutti."
        self.assertEqual(strip(raw), "Buongiorno a tutti.")

    def test_orphan_think_only_returns_empty(self):
        # qwen3 ha esaurito num_predict dentro <think>, niente </think>,
        # niente risposta. Deve uscire stringa vuota: il chiamante triggera
        # il retry con num_predict raddoppiato.
        raw = "<think>I need to translate this carefully and"
        self.assertEqual(strip(raw), "")

    def test_empty_closed_think_then_translation(self):
        raw = "<think></think>Risposta concisa."
        self.assertEqual(strip(raw), "Risposta concisa.")

    def test_closed_think_only_no_translation(self):
        raw = "<think>some reasoning</think>"
        self.assertEqual(strip(raw), "")

    def test_thinking_variant_tag(self):
        raw = "<thinking>internal monologue</thinking>Ciao mondo."
        self.assertEqual(strip(raw), "Ciao mondo.")

    def test_reasoning_variant_tag(self):
        raw = "<reasoning>step by step</reasoning>Salve."
        self.assertEqual(strip(raw), "Salve.")

    def test_orphan_think_then_double_newline_then_translation(self):
        # Caso di output troncato dove dopo il think orfano c'è comunque la
        # risposta finale separata da doppio newline (rara ma possibile).
        raw = "<think>incomplete reasoning\n\nBuonasera a tutti."
        self.assertEqual(strip(raw), "Buonasera a tutti.")

    def test_plain_translation_no_think_tags(self):
        raw = "Buongiorno, oggi parliamo di Python."
        self.assertEqual(strip(raw), "Buongiorno, oggi parliamo di Python.")

    def test_empty_input_returns_empty(self):
        self.assertEqual(strip(""), "")
        self.assertEqual(strip("   "), "")

    def test_think_with_uppercase_tag(self):
        raw = "<THINK>X</THINK>Risposta"
        self.assertEqual(strip(raw), "Risposta")

    def test_idempotent(self):
        raw = "<think>x</think>Buongiorno."
        once = strip(raw)
        twice = strip(once)
        self.assertEqual(once, twice)

    def test_orphan_think_does_not_leak_partial_reasoning(self):
        # Critico: se l'orphan strip lasciasse qualcosa, XTTS sintetizzerebbe
        # frammenti di reasoning come audio.
        raw = "<think>The user said hello, I should reply with"
        out = strip(raw)
        self.assertNotIn("<think>", out)
        self.assertNotIn("reasoning", out.lower())
        self.assertNotIn("user said", out.lower())


if __name__ == "__main__":
    unittest.main()
