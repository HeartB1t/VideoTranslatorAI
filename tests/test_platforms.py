import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

from videotranslator.platforms import (
    Wav2LipPaths,
    cosyvoice_supported,
    platform_info,
    resolve_app_paths,
    resolve_wav2lip_paths,
    runtime_app_paths,
    _wav2lip_assets_present,
)


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

    # ── cosyvoice_supported policy ────────────────────────────────────────
    #
    # CosyVoice was re-enabled on Linux in 2026-04 once the upstream pip
    # package switched the text frontend default from WeTextProcessing (C++
    # build hell) to wetext. Windows still has unsolved blockers (pynini
    # MSVC + tensorrt-cu12 conda dependency) and macOS is untested; both
    # must return False so the GUI keeps the checkbox hidden.
    def test_cosyvoice_supported_on_linux(self):
        self.assertTrue(cosyvoice_supported("linux"))
        self.assertTrue(cosyvoice_supported("linux2"))

    def test_cosyvoice_unsupported_on_windows(self):
        self.assertFalse(cosyvoice_supported("win32"))

    def test_cosyvoice_unsupported_on_macos(self):
        self.assertFalse(cosyvoice_supported("darwin"))

    def test_cosyvoice_unsupported_on_unknown_platform(self):
        self.assertFalse(cosyvoice_supported("freebsd"))

    def test_cosyvoice_supported_uses_sys_platform_by_default(self):
        # Sanity: the default branch returns a plain bool tied to the host.
        result = cosyvoice_supported()
        self.assertIsInstance(result, bool)
        self.assertEqual(result, sys.platform.startswith("linux"))


def _seed_wav2lip_assets(directory: Path) -> None:
    """Create the sentinel files (repo + model) inside *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "Wav2Lip").mkdir(parents=True, exist_ok=True)
    (directory / "Wav2Lip" / "inference.py").write_text("# stub", encoding="utf-8")
    (directory / "wav2lip_gan.pth").write_bytes(b"\0" * 16)


class Wav2LipPathResolverTests(unittest.TestCase):
    """Pure tests for :func:`resolve_wav2lip_paths`.

    The resolver is exercised with synthetic ``home`` and ``env`` values so
    Windows behaviour can be verified from a Linux developer machine. Both
    the writability and the assets-present probes default to real filesystem
    operations; tests that need to fake them inject explicit predicates.
    """

    def test_linux_default_paths(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            expected_asset = home / ".local" / "share" / "wav2lip"
            paths = resolve_wav2lip_paths(
                "linux",
                {},
                home,
                assets_check=lambda _path: False,
                writable_check=lambda path: path == expected_asset,
            )

        self.assertIsInstance(paths, Wav2LipPaths)
        # No candidate has pre-existing assets; /opt is simulated as
        # non-writable so the resolver must pick the user-local data dir.
        self.assertEqual(paths.asset_dir, home / ".local" / "share" / "wav2lip")
        self.assertEqual(paths.work_dir, home / ".cache" / "wav2lip")

    def test_linux_xdg_overrides_are_respected(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            data_root = home / "custom-data"
            cache_root = home / "custom-cache"
            expected_asset = data_root / "wav2lip"
            paths = resolve_wav2lip_paths(
                "linux",
                {
                    "XDG_DATA_HOME": str(data_root),
                    "XDG_CACHE_HOME": str(cache_root),
                },
                home,
                assets_check=lambda _path: False,
                writable_check=lambda path: path == expected_asset,
            )

        self.assertEqual(paths.asset_dir, data_root / "wav2lip")
        self.assertEqual(paths.work_dir, cache_root / "wav2lip")

    def test_linux_prefers_system_assets_when_populated(self):
        with tempfile.TemporaryDirectory() as home_str, tempfile.TemporaryDirectory() as opt_str:
            home = Path(home_str)
            opt_assets = Path(opt_str)
            _seed_wav2lip_assets(opt_assets)

            # Pretend /opt/VideoTranslatorAI/wav2lip lives under our temp
            # directory: the resolver normally hard-codes /opt, so we patch
            # by passing a custom assets_check that maps /opt to opt_assets.
            def fake_assets_check(path: Path) -> bool:
                if str(path) == "/opt/VideoTranslatorAI/wav2lip":
                    return True
                return False

            def fake_writable_check(path: Path) -> bool:
                return True  # both candidates writable

            paths = resolve_wav2lip_paths(
                "linux",
                {},
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(paths.asset_dir, Path("/opt/VideoTranslatorAI/wav2lip"))

    def test_windows_prefers_program_files_when_populated_and_writable(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            program_files = r"C:\Program Files"
            asset_target = Path(program_files) / "VideoTranslatorAI" / "wav2lip"

            def fake_assets_check(path: Path) -> bool:
                return path == asset_target

            def fake_writable_check(path: Path) -> bool:
                return True

            paths = resolve_wav2lip_paths(
                "win32",
                {
                    "ProgramFiles": program_files,
                    "LOCALAPPDATA": r"C:\Users\Example\AppData\Local",
                },
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(paths.asset_dir, asset_target)
        # work_dir must always live under LOCALAPPDATA, never ProgramFiles.
        self.assertEqual(
            paths.work_dir,
            Path(r"C:\Users\Example\AppData\Local") / "VideoTranslatorAI" / "wav2lip-work",
        )

    def test_windows_program_files_present_but_not_writable_is_valid_asset_dir(self):
        """A standard user can read assets but cannot write to ProgramFiles.

        In that scenario the resolver can still use ProgramFiles as
        ``asset_dir`` because the runtime scratch directory is separated into
        ``work_dir`` under LOCALAPPDATA.
        """
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            program_files = r"C:\Program Files"
            localappdata = r"C:\Users\Example\AppData\Local"
            program_files_assets = Path(program_files) / "VideoTranslatorAI" / "wav2lip"
            localappdata_assets = Path(localappdata) / "VideoTranslatorAI" / "wav2lip"

            def fake_assets_check(path: Path) -> bool:
                return path == program_files_assets  # only system has assets

            def fake_writable_check(path: Path) -> bool:
                return path == localappdata_assets  # only user dir writable

            paths = resolve_wav2lip_paths(
                "win32",
                {"ProgramFiles": program_files, "LOCALAPPDATA": localappdata},
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(paths.asset_dir, program_files_assets)
        self.assertEqual(
            paths.work_dir,
            Path(localappdata) / "VideoTranslatorAI" / "wav2lip-work",
        )

    def test_windows_localappdata_with_assets_when_program_files_empty(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            program_files = r"C:\Program Files"
            localappdata = r"C:\Users\Example\AppData\Local"
            localappdata_assets = Path(localappdata) / "VideoTranslatorAI" / "wav2lip"

            def fake_assets_check(path: Path) -> bool:
                return path == localappdata_assets

            def fake_writable_check(path: Path) -> bool:
                return path == localappdata_assets

            paths = resolve_wav2lip_paths(
                "win32",
                {"ProgramFiles": program_files, "LOCALAPPDATA": localappdata},
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(paths.asset_dir, localappdata_assets)

    def test_windows_no_assets_anywhere_picks_first_writable(self):
        """Fresh install: no candidate has assets, the resolver picks the
        first writable candidate so the caller can clone + download there."""
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            program_files = r"C:\Program Files"
            localappdata = r"C:\Users\Example\AppData\Local"
            localappdata_assets = Path(localappdata) / "VideoTranslatorAI" / "wav2lip"

            def fake_assets_check(_path: Path) -> bool:
                return False  # nothing populated yet

            def fake_writable_check(path: Path) -> bool:
                return path == localappdata_assets  # only user dir writable

            paths = resolve_wav2lip_paths(
                "win32",
                {"ProgramFiles": program_files, "LOCALAPPDATA": localappdata},
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(paths.asset_dir, localappdata_assets)

    def test_windows_no_writable_falls_back_to_first_candidate(self):
        """Pathological case (read-only %ProgramFiles% AND read-only
        %LOCALAPPDATA%): the resolver returns the first candidate so the
        caller surfaces a clear error instead of crashing later."""
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            program_files = r"C:\Program Files"
            localappdata = r"C:\Users\Example\AppData\Local"

            def fake_assets_check(_path: Path) -> bool:
                return False

            def fake_writable_check(_path: Path) -> bool:
                return False

            paths = resolve_wav2lip_paths(
                "win32",
                {"ProgramFiles": program_files, "LOCALAPPDATA": localappdata},
                home,
                writable_check=fake_writable_check,
                assets_check=fake_assets_check,
            )

        self.assertEqual(
            paths.asset_dir,
            Path(program_files) / "VideoTranslatorAI" / "wav2lip",
        )

    def test_windows_missing_localappdata_uses_home_default(self):
        """If %LOCALAPPDATA% is missing we still get a sensible per-user path
        rooted at ``<home>\\AppData\\Local`` instead of a stray relative dir."""
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            paths = resolve_wav2lip_paths(
                "win32",
                {"ProgramFiles": r"C:\Program Files"},
                home,
                writable_check=lambda _p: False,
                assets_check=lambda _p: False,
            )

        self.assertEqual(
            paths.work_dir,
            home / "AppData" / "Local" / "VideoTranslatorAI" / "wav2lip-work",
        )

    def test_macos_paths_are_user_local(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            paths = resolve_wav2lip_paths("darwin", {}, home)

        self.assertEqual(
            paths.asset_dir,
            home / "Library" / "Application Support" / "VideoTranslatorAI" / "wav2lip",
        )
        self.assertEqual(
            paths.work_dir,
            home / "Library" / "Caches" / "VideoTranslatorAI" / "wav2lip-work",
        )

    def test_work_dir_is_created_when_resolvable(self):
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            paths = resolve_wav2lip_paths("linux", {}, home)
            self.assertTrue(paths.work_dir.is_dir(), msg=f"work_dir not created: {paths.work_dir}")

    def test_real_filesystem_detects_seeded_assets(self):
        """End-to-end smoke without mocks: seed assets in a temp XDG_DATA_HOME
        and verify the resolver picks them. Confirms the default
        ``assets_check`` and ``writable_check`` work together on POSIX."""
        with tempfile.TemporaryDirectory() as home_str:
            home = Path(home_str)
            data_root = home / "data"
            asset_target = data_root / "wav2lip"
            _seed_wav2lip_assets(asset_target)

            paths = resolve_wav2lip_paths(
                "linux",
                {"XDG_DATA_HOME": str(data_root)},
                home,
            )

        self.assertEqual(paths.asset_dir, asset_target)

    def test_assets_present_probe_treats_permission_error_as_missing(self):
        class DeniedPath:
            def is_dir(self):
                raise PermissionError("denied")

        self.assertFalse(_wav2lip_assets_present(DeniedPath()))


if __name__ == "__main__":
    unittest.main()
