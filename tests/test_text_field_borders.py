"""Every tk.Entry asks for its own border.

Tk on Windows draws no ring around an Entry by default, and the themes put
a FIELD entry on a background of almost the same colour: without an
explicit highlight the field is invisible there (seen on a Windows 11 VM in
the ElevenLabs key field and in the subtitle editor). Linux shows Tk's
default ring, so only a source check catches it before a Windows run.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "video_translator_gui.py", *sorted((ROOT / "videotranslator").glob("*.py"))]


def entry_calls(tree):
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "Entry" and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "tk"):
            yield node


class TextFieldBorderTests(unittest.TestCase):
    def test_every_entry_asks_for_a_one_pixel_border(self):
        found = 0
        for path in SOURCES:
            for call in entry_calls(ast.parse(path.read_text(encoding="utf-8"))):
                found += 1
                keywords = {k.arg: k.value for k in call.keywords if k.arg}
                with self.subTest(file=path.name, line=call.lineno):
                    thickness = keywords.get("highlightthickness")
                    self.assertIsInstance(thickness, ast.Constant)
                    self.assertGreaterEqual(thickness.value, 1)
                    self.assertIn("highlightbackground", keywords)
                    self.assertIn("highlightcolor", keywords)
        self.assertGreaterEqual(found, 9)


if __name__ == "__main__":
    unittest.main()
