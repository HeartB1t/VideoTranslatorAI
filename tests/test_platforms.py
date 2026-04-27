import unittest
from pathlib import Path, PureWindowsPath

from videotranslator.platforms import platform_info, resolve_app_paths


class PlatformTests(unittest.TestCase):
    def test_windows_is_supported(self):
        info = platform_info("win32")

        self.assertTrue(info.supported)
        self.assertFalse(info.experimental)
        self.assertIn("Windows", info.name)

    def test_linux_is_supported(self):
        info = platform_info("linux")

        self.assertTrue(info.supported)
        self.assertFalse(info.experimental)

    def test_macos_is_explicitly_experimental(self):
        info = platform_info("darwin")

        self.assertFalse(info.supported)
        self.assertTrue(info.experimental)

    def test_windows_paths_use_windows_locations(self):
        paths = resolve_app_paths(
            "win32",
            {
                "APPDATA": r"C:\Users\ExampleUser\AppData\Roaming",
                "LOCALAPPDATA": r"C:\Users\ExampleUser\AppData\Local",
                "PUBLIC": r"C:\Users\Public",
            },
            PureWindowsPath(r"C:\Users\ExampleUser"),
        )

        self.assertEqual(
            paths.config_dir,
            PureWindowsPath(r"C:\Users\ExampleUser\AppData\Roaming\VideoTranslatorAI"),
        )
        self.assertEqual(paths.default_videos_dir, PureWindowsPath(r"C:\Users\Public\Videos"))

    def test_linux_paths_respect_xdg(self):
        paths = resolve_app_paths(
            "linux",
            {
                "XDG_CONFIG_HOME": "/tmp/cfg",
                "XDG_DATA_HOME": "/tmp/data",
                "XDG_CACHE_HOME": "/tmp/cache",
            },
            Path("/home/exampleuser"),
        )

        self.assertEqual(paths.config_dir, Path("/tmp/cfg/videotranslatorai"))
        self.assertEqual(paths.wav2lip_dir, Path("/tmp/data/wav2lip"))


if __name__ == "__main__":
    unittest.main()
