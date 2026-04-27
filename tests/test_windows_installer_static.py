import unittest
from pathlib import Path


SETUP = Path(__file__).resolve().parents[1] / "setup_windows.bat"


class WindowsInstallerStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SETUP.read_text(encoding="ascii")

    def test_installer_copies_python_package(self):
        self.assertIn(r"%SCRIPT_DIR%videotranslator", self.text)
        self.assertIn(r"%INSTALL_DIR%\videotranslator", self.text)
        self.assertIn(r"videotranslator\*.py", self.text)

    def test_validate_install_imports_application(self):
        self.assertIn('pushd "%INSTALL_DIR%"', self.text)
        self.assertIn('"import video_translator_gui"', self.text)
        self.assertIn("Application importable.", self.text)


if __name__ == "__main__":
    unittest.main()
