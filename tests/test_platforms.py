import sys
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

from videotranslator.platforms import platform_info, resolve_app_paths, runtime_app_paths


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

        self.assertEqual(paths.config_dir, PurePosixPath("/tmp/cfg/videotranslatorai"))
        self.assertEqual(paths.wav2lip_dir, PurePosixPath("/tmp/data/wav2lip"))

    def test_runtime_paths_are_concrete_for_current_platform(self):
        if sys.platform == "win32":
            paths = runtime_app_paths(
                sys.platform,
                {
                    "APPDATA": r"C:\Temp\AppData\Roaming",
                    "LOCALAPPDATA": r"C:\Temp\AppData\Local",
                    "PUBLIC": r"C:\Temp\Public",
                },
                Path(r"C:\Temp\ExampleUser"),
            )
        else:
            paths = runtime_app_paths(
                sys.platform,
                {
                    "XDG_CONFIG_HOME": "/tmp/vtai-cfg",
                    "XDG_DATA_HOME": "/tmp/vtai-data",
                    "XDG_CACHE_HOME": "/tmp/vtai-cache",
                },
                Path("/tmp/vtai-home"),
            )

        self.assertIs(type(paths.config_dir), type(Path()))
        self.assertIs(type(paths.data_dir), type(Path()))

    def test_runtime_paths_reject_synthetic_windows_on_non_windows(self):
        if sys.platform == "win32":
            self.skipTest("synthetic Windows matches the host on Windows")

        with self.assertRaises(ValueError):
            runtime_app_paths(
                "win32",
                {"APPDATA": r"C:\Temp\AppData\Roaming"},
                Path("/tmp/vtai-home"),
            )


if __name__ == "__main__":
    unittest.main()
