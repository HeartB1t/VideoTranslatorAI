"""Tests for videotranslator.hotwords (pure module)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from videotranslator.hotwords import (
    load_hotwords_file,
    merge_hotwords,
    parse_hotwords_string,
    to_whisper_param,
)


class ParseHotwordsStringTests(unittest.TestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(parse_hotwords_string(""), [])

    def test_none_returns_empty_list(self):
        self.assertEqual(parse_hotwords_string(None), [])

    def test_simple_comma_separated(self):
        self.assertEqual(
            parse_hotwords_string("Strix, pipx, Docker"),
            ["Strix", "pipx", "Docker"],
        )

    def test_strip_whitespace_and_dedup(self):
        # Production-like input from a careless user.
        self.assertEqual(
            parse_hotwords_string("  Strix  ,, Docker , Strix  "),
            ["Strix", "Docker"],
        )

    def test_case_preserved(self):
        # Whisper tokenizer is case-sensitive: keep both spellings if the
        # user really wants them.
        self.assertEqual(
            parse_hotwords_string("OpenAI, openai"),
            ["OpenAI", "openai"],
        )

    def test_only_separators_returns_empty(self):
        self.assertEqual(parse_hotwords_string(" , , , "), [])

    def test_unicode_terms(self):
        # Branding with accents / non-ASCII (e.g. Spanish "España" or
        # Japanese surnames) must round-trip unchanged.
        self.assertEqual(
            parse_hotwords_string("España, 東京, Pokémon"),
            ["España", "東京", "Pokémon"],
        )


class LoadHotwordsFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, payload: object) -> Path:
        path = self.tmpdir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_file_not_exists_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_hotwords_file(self.tmpdir / "missing.json")

    def test_malformed_json_raises_value_error(self):
        path = self.tmpdir / "broken.json"
        path.write_text("{ not valid json", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_hotwords_file(path)

    def test_flat_list(self):
        path = self._write("flat.json", ["Strix", "pipx", "Docker"])
        self.assertEqual(
            load_hotwords_file(path),
            ["Strix", "pipx", "Docker"],
        )

    def test_flat_list_strips_and_dedups(self):
        path = self._write(
            "flat_dirty.json",
            ["  Strix ", "Strix", "", "  ", "pipx"],
        )
        self.assertEqual(
            load_hotwords_file(path),
            ["Strix", "pipx"],
        )

    def test_per_language_dict_selects_src_lang(self):
        path = self._write(
            "by_lang.json",
            {"en": ["pipx", "Docker"], "it": ["Strix", "doppiaggio"]},
        )
        self.assertEqual(
            load_hotwords_file(path, src_lang="it"),
            ["Strix", "doppiaggio"],
        )

    def test_per_language_dict_fallback_to_en(self):
        path = self._write(
            "by_lang.json",
            {"en": ["pipx", "Docker"], "it": ["Strix"]},
        )
        # German not present -> falls back to 'en'.
        self.assertEqual(
            load_hotwords_file(path, src_lang="de"),
            ["pipx", "Docker"],
        )

    def test_per_language_dict_src_lang_none_uses_en(self):
        path = self._write("by_lang.json", {"en": ["pipx"], "it": ["Strix"]})
        self.assertEqual(load_hotwords_file(path, src_lang=None), ["pipx"])

    def test_per_language_dict_src_lang_auto_uses_en(self):
        path = self._write("by_lang.json", {"en": ["pipx"], "it": ["Strix"]})
        self.assertEqual(load_hotwords_file(path, src_lang="auto"), ["pipx"])

    def test_per_language_dict_missing_en_raises(self):
        path = self._write("by_lang.json", {"it": ["Strix"], "de": ["x"]})
        with self.assertRaises(ValueError):
            load_hotwords_file(path, src_lang="fr")

    def test_unsupported_shape_raises(self):
        path = self._write("scalar.json", "just-a-string")
        with self.assertRaises(ValueError):
            load_hotwords_file(path)

    def test_non_string_item_raises(self):
        path = self._write("mixed.json", ["Strix", 42, "pipx"])
        with self.assertRaises(ValueError):
            load_hotwords_file(path)


class MergeHotwordsTests(unittest.TestCase):
    def test_two_lists_with_overlap_dedup(self):
        cli = ["Strix", "pipx"]
        file_ = ["pipx", "Docker", "OpenAI"]
        self.assertEqual(
            merge_hotwords(cli, file_),
            ["Strix", "pipx", "Docker", "OpenAI"],
        )

    def test_order_preserved_first_occurrence(self):
        a = ["b", "a"]
        b = ["a", "c"]
        # 'a' must keep position from `a` (first occurrence wins).
        self.assertEqual(merge_hotwords(a, b), ["b", "a", "c"])

    def test_none_sources_skipped(self):
        self.assertEqual(
            merge_hotwords(None, ["x"], None, ["y"]),
            ["x", "y"],
        )

    def test_all_empty_returns_empty(self):
        self.assertEqual(merge_hotwords(None, [], None), [])


class ToWhisperParamTests(unittest.TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(to_whisper_param([]))
        self.assertIsNone(to_whisper_param(None))

    def test_single_term(self):
        self.assertEqual(to_whisper_param(["Strix"]), "Strix")

    def test_multiple_terms_space_separated(self):
        self.assertEqual(
            to_whisper_param(["Strix", "pipx", "Docker"]),
            "Strix pipx Docker",
        )

    def test_strips_dirty_entries(self):
        # If something dirty slipped through, do not crash.
        self.assertEqual(
            to_whisper_param(["  Strix  ", "", "pipx"]),
            "Strix pipx",
        )

    def test_only_blanks_returns_none(self):
        self.assertIsNone(to_whisper_param(["", "  ", "\t"]))


if __name__ == "__main__":
    unittest.main()
