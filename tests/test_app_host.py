import ast
import types
import unittest
from pathlib import Path
from unittest import mock

from videotranslator.app_host import _Host

ROOT = Path(__file__).resolve().parents[1]


class HostProxyTests(unittest.TestCase):
    def test_unbound_host_raises_a_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "not bound"):
            _Host().anything

    def test_reads_follow_the_bound_module_at_call_time(self):
        module = types.ModuleType("fake_gui")
        module.VALUE = 1
        host = _Host()
        host.bind(module)
        self.assertEqual(host.VALUE, 1)
        module.VALUE = 2
        self.assertEqual(host.VALUE, 2)

    def test_assignments_through_the_host_are_refused(self):
        host = _Host()
        host.bind(types.ModuleType("fake_gui"))
        with self.assertRaises(AttributeError):
            host.VALUE = 3


class AppMixinTests(unittest.TestCase):
    def test_a_name_patched_on_the_gui_module_reaches_a_mixin_method(self):
        import video_translator_gui as gui
        from videotranslator.app_engines_tk import EnginesMixin

        self.assertIn(EnginesMixin, gui.App.__mro__)
        self.assertNotIn("_ollama_check_text", gui.App.__dict__)
        with mock.patch.object(gui, "_ollama_model_size_gb", return_value=7.5):
            self.assertEqual(gui._ollama_model_size_gb("x"), 7.5)
            from videotranslator.app_host import host
            self.assertEqual(host._ollama_model_size_gb("x"), 7.5)

    def test_mixins_import_nothing_but_the_host(self):
        for path in sorted((ROOT / "videotranslator").glob("app_*_tk.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
            with self.subTest(module=path.name):
                self.assertEqual(imports, ["from .app_host import host as _g"])


if __name__ == "__main__":
    unittest.main()
