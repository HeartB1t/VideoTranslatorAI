import csv
import io
import os
import tempfile
import unittest

from videotranslator.metrics_csv import (
    CSV_FIELDS,
    dump_segment_metrics,
    normalize_row,
)


class NormalizeRowTests(unittest.TestCase):
    def test_missing_fields_default_to_empty_string(self):
        out = normalize_row({"segment_index": 0})
        self.assertEqual(out["segment_index"], 0)
        self.assertEqual(out["tts_duration_ms"], "")
        self.assertEqual(out["text_src"], "")

    def test_extra_keys_dropped_when_writing(self):
        # normalize_row returns ALL CSV_FIELDS, dropping unknown keys is
        # the writer's responsibility (extrasaction='ignore').
        out = normalize_row({"random_key": "x", "segment_index": 5})
        self.assertNotIn("random_key", out)
        self.assertEqual(out["segment_index"], 5)

    def test_all_fields_present(self):
        out = normalize_row({})
        for field in CSV_FIELDS:
            self.assertIn(field, out)


class DumpSegmentMetricsTests(unittest.TestCase):
    def _read_csv(self, path):
        with open(path, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_writes_header_only_for_empty_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            n = dump_segment_metrics([], path)
            self.assertEqual(n, 0)
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("segment_index", content)
            self.assertEqual(content.count("\n"), 1)  # only header

    def test_writes_one_row(self):
        rows = [{
            "segment_index": 0,
            "slot_s": 4.02,
            "src_chars": 113,
            "tgt_chars": 94,
            "target_chars": 66,
            "tts_duration_ms": 8118,
            "pre_stretch_ratio": 2.02,
            "stretch_engine": "atempo",
            "text_src": "Original english",
            "text_tgt": "Italiano tradotto",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            n = dump_segment_metrics(rows, path)
            self.assertEqual(n, 1)
            parsed = self._read_csv(path)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0]["segment_index"], "0")
            self.assertEqual(parsed[0]["pre_stretch_ratio"], "2.02")
            self.assertEqual(parsed[0]["text_tgt"], "Italiano tradotto")

    def test_text_with_commas_and_newlines_is_quoted(self):
        rows = [{
            "segment_index": 0,
            "text_tgt": 'Frase, con, virgole "e" virgolette\nnuova riga',
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            dump_segment_metrics(rows, path)
            parsed = self._read_csv(path)
            self.assertEqual(
                parsed[0]["text_tgt"],
                'Frase, con, virgole "e" virgolette\nnuova riga',
            )

    def test_unicode_preserved(self):
        rows = [{
            "segment_index": 0,
            "text_tgt": "ciao 你好 こんにちは 안녕하세요 — ñ",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            dump_segment_metrics(rows, path)
            parsed = self._read_csv(path)
            self.assertEqual(
                parsed[0]["text_tgt"],
                "ciao 你好 こんにちは 안녕하세요 — ñ",
            )

    def test_extra_keys_ignored_silently(self):
        rows = [{"segment_index": 0, "spurious_field": "X"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            dump_segment_metrics(rows, path)
            parsed = self._read_csv(path)
            self.assertNotIn("spurious_field", parsed[0])

    def test_returns_row_count(self):
        rows = [{"segment_index": i} for i in range(7)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            self.assertEqual(dump_segment_metrics(rows, path), 7)


if __name__ == "__main__":
    unittest.main()
