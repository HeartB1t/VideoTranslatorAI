import json
import os
import tempfile
import unittest
from pathlib import Path

from videotranslator.config import (
    get_default_config_path,
    get_legacy_config_path,
    load_json_config,
    load_user_config,
    merge_json_config,
    migrate_legacy_config_if_needed,
    save_user_config,
    write_json_config,
)


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


class DefaultConfigPathTests(unittest.TestCase):
    """Pure path-resolution tests; no filesystem touched."""

    def test_linux_with_xdg_config_home(self):
        path = get_default_config_path(
            sys_platform="linux",
            env={"XDG_CONFIG_HOME": "/tmp/cfg"},
            home=Path("/home/exampleuser"),
        )

        self.assertEqual(path, Path("/tmp/cfg/videotranslatorai/config.json"))

    def test_linux_without_xdg_config_home_uses_dot_config(self):
        path = get_default_config_path(
            sys_platform="linux",
            env={},
            home=Path("/home/exampleuser"),
        )

        self.assertEqual(
            path,
            Path("/home/exampleuser/.config/videotranslatorai/config.json"),
        )

    def test_windows_uses_appdata(self):
        path = get_default_config_path(
            sys_platform="win32",
            env={"APPDATA": r"C:\Users\ExampleUser\AppData\Roaming"},
            home=Path(r"C:\Users\ExampleUser"),
        )

        # Compare against the platform-resolved Path so the test is portable
        # (on Linux, Path("C:\\...") becomes a PosixPath but the string still
        # matches what the caller passed in).
        self.assertEqual(
            str(path),
            str(Path(r"C:\Users\ExampleUser\AppData\Roaming")
                / "VideoTranslatorAI"
                / "config.json"),
        )

    def test_macos_uses_application_support(self):
        path = get_default_config_path(
            sys_platform="darwin",
            env={},
            home=Path("/Users/exampleuser"),
        )

        self.assertEqual(
            path,
            Path(
                "/Users/exampleuser/Library/Application Support/"
                "VideoTranslatorAI/config.json"
            ),
        )

    def test_legacy_path_under_home(self):
        legacy = get_legacy_config_path(home=Path("/home/exampleuser"))

        self.assertEqual(
            legacy, Path("/home/exampleuser/.videotranslatorai_config.json")
        )


class LoadUserConfigTests(unittest.TestCase):
    """End-to-end behavior of the platform-aware loader.

    These tests pin ``sys_platform="linux"`` because the resolution rules and
    legacy path are identical to what real users hit on Linux/Windows; the
    only thing platform-specific is the *directory*, already covered above.
    """

    def _linux_env(self, home: Path) -> dict[str, str]:
        # Force XDG_CONFIG_HOME so the test is independent of the real env.
        return {"XDG_CONFIG_HOME": str(home / ".config")}

    def test_load_with_only_new_path_returns_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            new_path = home / ".config" / "videotranslatorai" / "config.json"
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(json.dumps({"lang": "fr"}), encoding="utf-8")

            data = load_user_config(
                sys_platform="linux", env=self._linux_env(home), home=home
            )

            self.assertEqual(data, {"lang": "fr"})

    def test_load_with_only_legacy_path_returns_legacy_and_migrates(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            legacy_path = home / ".videotranslatorai_config.json"
            legacy_path.write_text(json.dumps({"lang": "de"}), encoding="utf-8")

            data = load_user_config(
                sys_platform="linux", env=self._linux_env(home), home=home
            )

            self.assertEqual(data, {"lang": "de"})

            new_path = home / ".config" / "videotranslatorai" / "config.json"
            self.assertTrue(new_path.exists(), "loader should migrate legacy → new")
            self.assertEqual(
                json.loads(new_path.read_text(encoding="utf-8")), {"lang": "de"}
            )
            # Legacy must NOT be removed by the migration.
            self.assertTrue(legacy_path.exists(), "legacy file must be kept")

    def test_load_with_both_paths_prefers_new_and_does_not_touch_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            legacy_path = home / ".videotranslatorai_config.json"
            legacy_path.write_text(json.dumps({"lang": "legacy"}), encoding="utf-8")
            legacy_mtime = legacy_path.stat().st_mtime_ns

            new_path = home / ".config" / "videotranslatorai" / "config.json"
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(json.dumps({"lang": "new"}), encoding="utf-8")

            data = load_user_config(
                sys_platform="linux", env=self._linux_env(home), home=home
            )

            self.assertEqual(data, {"lang": "new"})
            self.assertEqual(
                legacy_path.stat().st_mtime_ns,
                legacy_mtime,
                "legacy file should not be touched when new path exists",
            )

    def test_load_with_neither_path_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            data = load_user_config(
                sys_platform="linux", env=self._linux_env(home), home=home
            )

            self.assertEqual(data, {})


class SaveUserConfigTests(unittest.TestCase):
    def test_save_creates_parents_and_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {"XDG_CONFIG_HOME": str(home / ".config")}

            written = save_user_config(
                {"lang": "es"}, sys_platform="linux", env=env, home=home
            )

            expected = home / ".config" / "videotranslatorai" / "config.json"
            self.assertEqual(written, expected)
            self.assertTrue(expected.exists())
            self.assertEqual(
                json.loads(expected.read_text(encoding="utf-8")), {"lang": "es"}
            )


class MigrationIdempotencyTests(unittest.TestCase):
    def test_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {"XDG_CONFIG_HOME": str(home / ".config")}
            legacy_path = home / ".videotranslatorai_config.json"
            legacy_path.write_text(json.dumps({"lang": "it"}), encoding="utf-8")

            first = migrate_legacy_config_if_needed(
                sys_platform="linux", env=env, home=home
            )
            second = migrate_legacy_config_if_needed(
                sys_platform="linux", env=env, home=home
            )

            self.assertTrue(first, "first call must migrate")
            self.assertFalse(second, "second call must be a no-op")

    def test_migration_no_op_when_legacy_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {"XDG_CONFIG_HOME": str(home / ".config")}

            self.assertFalse(
                migrate_legacy_config_if_needed(
                    sys_platform="linux", env=env, home=home
                )
            )


if __name__ == "__main__":
    unittest.main()
