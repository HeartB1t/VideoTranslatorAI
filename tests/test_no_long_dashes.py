"""No em dash (U+2014) or en dash (U+2013) in code, tests, docs or the installer (project rule)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG_DASHES = ("\u2014", "\u2013")


def _checked_files():
    files = [ROOT / name for name in ("video_translator_gui.py", "setup_windows.bat", "README.md",
                                      "pyproject.toml", ".gitignore")]
    files += sorted((ROOT / "videotranslator").glob("*.py"))
    files += sorted((ROOT / "tests").glob("*.py"))
    files += sorted(ROOT.glob("requirements*.txt"))
    return files


class NoLongDashesTests(unittest.TestCase):
    def test_no_long_dash_anywhere(self):
        offenders = []
        for path in _checked_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if any(dash in line for dash in LONG_DASHES):
                    offenders.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(offenders, [], "long dashes found:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
