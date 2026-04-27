import tempfile
import unittest
from pathlib import Path

from videotranslator.config import load_json_config, write_json_config
from videotranslator.secrets import load_secret_token, save_secret_token


class FakeKeyring:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        if self.fail:
            raise RuntimeError("keyring unavailable")
        return self.values.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        if self.fail:
            raise RuntimeError("keyring unavailable")
        self.values[(service_name, username)] = password


class SecretsTests(unittest.TestCase):
    def test_load_prefers_keyring_and_clears_json_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json_config(config_path, {"hf_token": "legacy-token", "lang": "it"})
            keyring = FakeKeyring()
            keyring.set_password("VideoTranslatorAI", "hf_token", "keyring-token")

            token = load_secret_token(keyring_backend=keyring, config_path=config_path)

            self.assertEqual(token, "keyring-token")
            self.assertEqual(load_json_config(config_path), {"lang": "it"})

    def test_load_migrates_legacy_json_token_to_keyring(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json_config(config_path, {"hf_token": "legacy-token"})
            keyring = FakeKeyring()

            token = load_secret_token(keyring_backend=keyring, config_path=config_path)

            self.assertEqual(token, "legacy-token")
            self.assertEqual(
                keyring.get_password("VideoTranslatorAI", "hf_token"),
                "legacy-token",
            )
            self.assertEqual(load_json_config(config_path), {})

    def test_load_falls_back_to_json_when_keyring_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json_config(config_path, {"hf_token": "legacy-token"})

            token = load_secret_token(keyring_backend=None, config_path=config_path)

            self.assertEqual(token, "legacy-token")

    def test_save_stores_in_keyring_and_removes_json_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json_config(config_path, {"hf_token": "old-token"})
            keyring = FakeKeyring()

            stored_in_keyring = save_secret_token(
                "new-token",
                keyring_backend=keyring,
                config_path=config_path,
            )

            self.assertTrue(stored_in_keyring)
            self.assertEqual(
                keyring.get_password("VideoTranslatorAI", "hf_token"),
                "new-token",
            )
            self.assertEqual(load_json_config(config_path), {})

    def test_save_falls_back_to_json_when_keyring_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"

            stored_in_keyring = save_secret_token(
                "fallback-token",
                keyring_backend=FakeKeyring(fail=True),
                config_path=config_path,
            )

            self.assertFalse(stored_in_keyring)
            self.assertEqual(load_json_config(config_path), {"hf_token": "fallback-token"})


if __name__ == "__main__":
    unittest.main()

