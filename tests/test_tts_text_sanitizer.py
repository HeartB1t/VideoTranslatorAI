import unittest

from videotranslator.tts_text_sanitizer import sanitize_for_tts


class SanitizeForTtsTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(sanitize_for_tts(""), "")
        self.assertEqual(sanitize_for_tts(None), "")

    def test_passes_through_normal_text(self):
        self.assertEqual(
            sanitize_for_tts("Buongiorno a tutti, oggi parliamo di Python."),
            "Buongiorno a tutti, oggi parliamo di Python.",
        )

    def test_colon_becomes_comma(self):
        # Production case: "americano: l'ho scritto" was pronounced
        # "americano due punti l'ho scritto".
        self.assertEqual(
            sanitize_for_tts("americano: l'ho scritto"),
            "americano, l'ho scritto",
        )

    def test_semicolon_becomes_period(self):
        self.assertEqual(
            sanitize_for_tts("frase uno; frase due"),
            "frase uno. frase due",
        )

    def test_em_dash_becomes_comma(self):
        self.assertEqual(
            sanitize_for_tts("parola — altra"),
            "parola , altra",
        )

    def test_en_dash_becomes_comma(self):
        self.assertEqual(
            sanitize_for_tts("parola – altra"),
            "parola , altra",
        )

    def test_double_hyphen_becomes_comma(self):
        self.assertEqual(
            sanitize_for_tts("parola -- altra"),
            "parola , altra",
        )

    def test_unicode_ellipsis_becomes_period(self):
        self.assertEqual(
            sanitize_for_tts("aspetto… vediamo"),
            "aspetto. vediamo",
        )

    def test_three_ascii_dots_become_period(self):
        self.assertEqual(
            sanitize_for_tts("aspetto... vediamo"),
            "aspetto. vediamo",
        )

    def test_two_ascii_dots_become_period(self):
        self.assertEqual(
            sanitize_for_tts("aspetto.. vediamo"),
            "aspetto. vediamo",
        )

    def test_idempotent(self):
        raw = "americano: l'ho scritto — è orribile..."
        once = sanitize_for_tts(raw)
        twice = sanitize_for_tts(once)
        self.assertEqual(once, twice)

    def test_combination_collapses_neighboring_punct(self):
        # Edge case: ":..." after sanitize should not produce "., . . ."
        self.assertEqual(sanitize_for_tts("X:..."), "X.")
        # Double colon collapses to single comma (acceptable prosody).
        self.assertEqual(sanitize_for_tts("X:: Y"), "X, Y")

    def test_preserves_existing_commas_and_periods(self):
        text = "Frase, virgole, sì? Punti. E altro!"
        # Sanitize should not touch ?, ! or normal commas/periods.
        self.assertEqual(sanitize_for_tts(text), text)

    def test_strip_whitespace(self):
        self.assertEqual(sanitize_for_tts("  hello  "), "hello")

    def test_collapses_multiple_spaces(self):
        self.assertEqual(
            sanitize_for_tts("parola   altra"),
            "parola altra",
        )

    def test_real_production_segment_20(self):
        # Live failure case from 2026-04-28 user test.
        raw = (
            "Potresti essere privo di sonno, ma finirai il tuo romanzo. "
            "Il mio libro non è il prossimo grande romanzo americano: "
            "l'ho scritto in un mese, è orribile."
        )
        out = sanitize_for_tts(raw)
        self.assertNotIn(":", out)
        self.assertIn("americano,", out)


if __name__ == "__main__":
    unittest.main()
