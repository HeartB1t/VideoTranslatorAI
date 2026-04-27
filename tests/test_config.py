import json
import os
import tempfile
import unittest
from pathlib import Path

from videotranslator.config import load_json_config, merge_json_config, write_json_config


class ConfigTests(unittest.TestCase):
    def test_missing_config_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"

            self.assertEqual(load_json_config(path), {})

    def test_invalid_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{not json", encoding="utf-8")

            self.assertEqual(load_json_config(path), {})

    def test_non_object_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("[]", encoding="utf-8")

            self.assertEqual(load_json_config(path), {})

    def test_write_json_config_creates_parent_and_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "config.json"

            write_json_config(path, {"lang": "it"})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"lang": "it"})
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_merge_json_config_preserves_existing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            write_json_config(path, {"lang": "it", "model": "small"})

            merged = merge_json_config(path, {"model": "medium"})

            self.assertEqual(merged, {"lang": "it", "model": "medium"})
            self.assertEqual(load_json_config(path), merged)


if __name__ == "__main__":
    unittest.main()

