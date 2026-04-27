import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import video_translator_gui as legacy
from videotranslator import config, secrets, segments, timing


class LegacyTimingBridgeTests(unittest.TestCase):
    def test_timing_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._suggest_xtts_speed, timing.suggest_xtts_speed)
        self.assertIs(legacy._estimate_tts_duration_s, timing.estimate_tts_duration_s)
        self.assertIs(legacy._compute_segment_speed, timing.compute_segment_speed)


class LegacySegmentBridgeTests(unittest.TestCase):
    def test_segment_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._split_on_punctuation, segments.split_on_punctuation)
        self.assertIs(legacy._merge_short_segments, segments.merge_short_segments)


class LegacyConfigBridgeTests(unittest.TestCase):
    def test_config_wrappers_use_extracted_helpers_on_config_path(self):
        self.assertIs(legacy._load_json_config, config.load_json_config)
        self.assertIs(legacy._write_json_config, config.write_json_config)
        self.assertIs(legacy._merge_json_config, config.merge_json_config)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            with mock.patch.object(legacy, "CONFIG_PATH", path):
                self.assertEqual(legacy.load_config(), {})

                legacy._write_config_raw({"lang": "it", "model": "small"})
                self.assertEqual(
                    json.loads(path.read_text(encoding="utf-8")),
                    {"lang": "it", "model": "small"},
                )

                legacy.save_config({"model": "medium"})
                self.assertEqual(
                    legacy.load_config(),
                    {"lang": "it", "model": "medium"},
                )


class LegacySecretsBridgeTests(unittest.TestCase):
    def test_secret_helpers_are_extracted_module_functions(self):
        self.assertIs(legacy._import_keyring_backend, secrets.import_keyring_backend)
        self.assertIs(legacy._load_secret_token, secrets.load_secret_token)
        self.assertIs(legacy._save_secret_token, secrets.save_secret_token)


if __name__ == "__main__":
    unittest.main()
