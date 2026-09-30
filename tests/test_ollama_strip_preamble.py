import unittest

import video_translator_gui as legacy

strip = legacy._ollama_strip_preamble


class OllamaStripPreambleThinkTests(unittest.TestCase):
    """Edge cases for Qwen3 <think> blocks.

    These are the cases that, if mishandled, produce `keeping source: empty
    response` during translation. The logic lives in
    `_ollama_strip_preamble()` step 0/0b.
    """

    def test_closed_think_block_then_translation(self):
        raw = "<think>let me think about this</think>Buongiorno a tutti."
        self.assertEqual(strip(raw), "Buongiorno a tutti.")

    def test_orphan_think_only_returns_empty(self):
        # qwen3 exhausted num_predict inside <think>, no </think>,
        # no response. Must return an empty string: the caller triggers
        # the retry with num_predict doubled.
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
        # Truncated output where after the orphan think block the final
        # response is still present, separated by a double newline (rare but
        # possible).
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
        # Critical: if the orphan strip left anything behind, XTTS would
        # synthesise reasoning fragments as audio.
        raw = "<think>The user said hello, I should reply with"
        out = strip(raw)
        self.assertNotIn("<think>", out)
        self.assertNotIn("reasoning", out.lower())
        self.assertNotIn("user said", out.lower())


class OllamaStripPreambleAcknowledgmentTests(unittest.TestCase):
    """The acknowledgment preamble ("Ok,", "Sure!") must match whole words.

    Found in the 30/09 acceptance test: the IT->EN translation of "Ok, eccoci
    qui" came out as "ay, here we are" because "Ok" was cut out of "Okay".
    """

    def test_okay_is_not_cut_to_ay(self):
        self.assertEqual(strip("Okay, here we are."), "Okay, here we are.")

    def test_words_starting_with_an_acknowledgment_are_kept(self):
        for text in ("Surely not.", "Oklahoma is far.", "Certosa di Pavia.",
                     "Certainly-ish, maybe."):
            with self.subTest(text=text):
                self.assertEqual(strip(text), text)

    def test_standalone_acknowledgments_are_still_stripped(self):
        self.assertEqual(strip("Ok, eccoci qui."), "eccoci qui.")
        self.assertEqual(strip("Sure! Here's the translation: Ciao."), "Ciao.")
        self.assertEqual(strip("Certo. Buongiorno."), "Buongiorno.")


class OllamaStripPreambleContentWordTests(unittest.TestCase):
    """A preamble word followed by a content word is the sentence itself.

    Review of 30/09: the "ecco", acknowledgment and "translation" prefixes had
    OPTIONAL closing punctuation, so they also matched a sentence that merely
    starts with that word and ate its first word ("Ecco perche' lo faccio"
    became "perche' lo faccio", "Ecco il problema" even lost the article).
    A prefix is a preamble only when a structural continuation follows it
    (punctuation, or "la/il traduzione" for "ecco"); a plain space plus a
    content word means the model is speaking, not announcing.
    """

    def test_ecco_followed_by_a_content_word_is_kept(self):
        for text in ("Ecco perche' lo faccio.", "Ecco il problema.",
                     "Ecco la casa di mio padre."):
            with self.subTest(text=text):
                self.assertEqual(strip(text), text)

    def test_acknowledgment_followed_by_a_content_word_is_kept(self):
        for text in ("Certo che si'.", "Sure thing, mate.", "Ok va bene cosi'."):
            with self.subTest(text=text):
                self.assertEqual(strip(text), text)

    def test_translation_word_followed_by_a_content_word_is_kept(self):
        for text in ("Translated text: Hi.", "Traduzione simultanea in corso."):
            with self.subTest(text=text):
                self.assertEqual(strip(text), text)

    def test_real_preambles_are_still_stripped(self):
        # The structural continuations keep working after the tightening.
        self.assertEqual(strip("Ecco la traduzione: Ciao."), "Ciao.")
        self.assertEqual(strip("Ecco la traduzione concisa: Ciao."), "Ciao.")
        self.assertEqual(strip("Ecco: Ciao."), "Ciao.")
        self.assertEqual(strip("Ecco, Ciao."), "Ciao.")
        self.assertEqual(strip("Traduzione: Ciao."), "Ciao.")
        self.assertEqual(strip("Translation - Ciao."), "Ciao.")
        self.assertEqual(strip("Certo, ecco la traduzione: Ciao."), "Ciao.")

    def test_chinese_chain_is_untouched_by_the_tightening(self):
        # CJK characters are \w: the Chinese prefixes keep their own rules.
        self.assertEqual(strip("好的这是翻译：Ni hao"), "Ni hao")

    def test_label_alone_on_its_line_is_stripped(self):
        # A small model can put the label on its own line without a colon; the
        # newline is a structural continuation (it would be read aloud once the
        # newline is collapsed to a space).
        self.assertEqual(strip("Ecco\nCiao."), "Ciao.")
        self.assertEqual(strip("Traduzione\nCiao."), "Ciao.")
        self.assertEqual(strip("Ok\nCiao."), "Ciao.")
        self.assertEqual(strip("Sure\nHi."), "Hi.")

    def test_word_then_space_then_content_is_still_kept(self):
        # The line break is the signal: a plain space before a content word is
        # not, so these stay whole.
        for text in ("Ecco perche' lo faccio.", "Certo che si'.",
                     "Traduzione simultanea in corso."):
            with self.subTest(text=text):
                self.assertEqual(strip(text), text)


if __name__ == "__main__":
    unittest.main()
