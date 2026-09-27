import tempfile
import unittest
from pathlib import Path

from videotranslator import resource_paths


class AssetsDirTests(unittest.TestCase):
    def test_a_checkout_uses_the_folder_next_to_the_package(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(resource_paths.assets_dir(), root / "assets")
        self.assertTrue((resource_paths.assets_dir() / "icon_256.png").is_file())

    def test_a_wheel_install_uses_the_folder_inside_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "site" / "videotranslator"
            (package / "assets").mkdir(parents=True)
            (Path(tmp) / "site" / "assets").mkdir()         # someone else's folder
            self.assertEqual(resource_paths.assets_dir(package), package / "assets")

    def test_without_either_folder_the_checkout_path_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "videotranslator"
            package.mkdir()
            self.assertEqual(resource_paths.assets_dir(package), Path(tmp) / "assets")


if __name__ == "__main__":
    unittest.main()
