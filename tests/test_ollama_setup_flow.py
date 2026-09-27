"""Preparing Ollama when the chosen model is not downloaded.

On a Windows VM choosing qwen3:14b in the model box did nothing, and the
next translation silently used qwen3:8b: a missing model was only offered
for download when no other model was installed, in a question written in
Italian whatever the UI language. The chosen model is now offered for
download (once a session per model), in the UI language, with its size.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import video_translator_gui as gui
from videotranslator import ollama_runtime as rt

URL = "http://localhost:11434"
TEXTS = {key: gui.UI_STRINGS["en"][key] for key in (
    "ollama_install_ask", "ollama_pull_ask", "ollama_pull_size",
    "ollama_pull_else_model", "ollama_pull_else_google")}


class SizeAndQuestionTests(unittest.TestCase):
    def test_known_models_have_a_download_size(self):
        self.assertEqual(rt.ollama_model_size_gb("qwen3:14b"), 9.3)
        self.assertEqual(rt.ollama_model_size_gb("qwen3:8b"), 5.2)
        self.assertIsNone(rt.ollama_model_size_gb("somebody/custom:1b"))

    def test_the_question_names_the_model_its_size_and_what_happens_otherwise(self):
        text = gui._ollama_pull_question(TEXTS, "qwen3:14b", "qwen3:8b")
        self.assertIn("qwen3:14b", text)
        self.assertIn("9.3", text)
        self.assertIn(TEXTS["ollama_pull_else_model"].format(other="qwen3:8b"), text)
        plain = gui._ollama_pull_question(TEXTS, "somebody/custom:1b", "")
        self.assertNotIn("GB", plain)
        self.assertIn(TEXTS["ollama_pull_else_google"], plain)

    def test_every_language_has_the_questions(self):
        for lang, table in gui.UI_STRINGS.items():
            with self.subTest(lang=lang):
                texts = {key: table[key] for key in TEXTS}
                self.assertIn("qwen3:14b", gui._ollama_pull_question(texts, "qwen3:14b", "x"))


class SetupWorkerTests(unittest.TestCase):
    def setUp(self):
        self.logged, self.questions, self.answers = [], [], []
        self.app = SimpleNamespace(
            _destroying=False, _ollama_pull_declined=set(),
            _log_async=self.logged.append,
            _ask_yes_no_sync=self._ask)

    def _ask(self, title, message):
        self.questions.append(message)
        return self.answers.pop(0)

    def _run(self, model, health, *, auto_install=True, pulled=(True, "")):
        health = list(health)
        with mock.patch.object(gui, "_ollama_find_binary", return_value="/usr/bin/ollama"), \
                mock.patch.object(gui, "_ollama_is_daemon_running", return_value=True), \
                mock.patch.object(gui, "_ollama_health_check",
                                  side_effect=lambda *a, **k: health.pop(0)), \
                mock.patch.object(gui, "_ollama_pull_model", return_value=pulled) as pull:
            ok = gui.App._ollama_setup_worker(self.app, model, URL, auto_install, TEXTS)
        return ok, pull

    def test_a_chosen_model_that_is_missing_is_offered_even_with_another_installed(self):
        self.answers = [True]
        ok, pull = self._run("qwen3:14b", [(True, "using qwen3:8b", "qwen3:8b"),
                                           (True, "", "qwen3:14b")])
        self.assertTrue(ok)
        self.assertEqual(len(self.questions), 1)
        self.assertIn("qwen3:14b", self.questions[0])
        self.assertIn("qwen3:8b", self.questions[0])
        self.assertEqual(pull.call_args.args[0], "qwen3:14b")
        self.assertEqual(pull.call_args.kwargs["api_url"], URL)
        self.assertIn("qwen3:14b", self.logged[-1])

    def test_no_keeps_the_installed_model_and_is_not_asked_again_this_session(self):
        self.answers = [False]
        ok, pull = self._run("qwen3:14b", [(True, "using qwen3:8b", "qwen3:8b")])
        self.assertTrue(ok)
        pull.assert_not_called()
        self.assertIn("qwen3:8b", self.logged[-1])
        ok, pull = self._run("qwen3:14b", [(True, "using qwen3:8b", "qwen3:8b")])
        self.assertTrue(ok)
        self.assertEqual(len(self.questions), 1)                  # not asked again
        pull.assert_not_called()

    def test_no_with_nothing_installed_falls_back_to_google(self):
        self.answers = [False]
        ok, pull = self._run("qwen3:8b", [(False, "No models installed", "")])
        self.assertFalse(ok)
        pull.assert_not_called()
        self.assertIn(TEXTS["ollama_pull_else_google"], self.questions[0])

    def test_without_auto_install_nothing_is_asked(self):
        ok, pull = self._run("qwen3:14b", [(True, "using qwen3:8b", "qwen3:8b")],
                             auto_install=False)
        self.assertTrue(ok)
        self.assertEqual(self.questions, [])
        pull.assert_not_called()

    def test_a_failed_download_keeps_the_installed_model(self):
        self.answers = [True]
        ok, _pull = self._run("qwen3:14b", [(True, "using qwen3:8b", "qwen3:8b")],
                              pulled=(False, "network down"))
        self.assertTrue(ok)
        text = "".join(self.logged)
        self.assertIn("network down", text)
        self.assertIn("qwen3:8b", self.logged[-1])

    def test_an_unreachable_daemon_is_not_a_missing_model(self):
        ok, pull = self._run("qwen3:8b", [(False, "Ollama daemon not reachable at x", "")])
        self.assertFalse(ok)
        self.assertEqual(self.questions, [])
        pull.assert_not_called()



class _InlineThread:
    """threading.Thread that runs its target at start(), on the Tk thread."""

    def __init__(self, target=None, daemon=None, name=None):
        self._target = target

    def start(self):
        self._target()


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        from test_ui_theme_tk import HAS_DISPLAY
        if not HAS_DISPLAY:
            self.skipTest("needs a display (Tk)")

    def _built(self):
        from test_ui_theme_tk import built_app
        return built_app({"ui_theme": "graphite", "ui_lang": "it"})

    def test_choosing_a_model_in_the_box_prepares_it(self):
        with self._built() as (gui_module, app, _):
            seen = []
            with mock.patch.object(gui_module.threading, "Thread", _InlineThread), \
                    mock.patch.object(gui_module.App, "_ollama_setup_worker",
                                      lambda self, model, url, auto, texts:
                                      seen.append((model, texts)) or True):
                app._translation_engine.set("llm_ollama")
                app._ollama_model_var.set("qwen3:14b")
                app._ollama_model_combo.event_generate("<<ComboboxSelected>>")
                app.update()
            self.assertEqual([model for model, _ in seen], ["qwen3:14b"])
            texts = seen[0][1]
            self.assertEqual(texts["ollama_pull_ask"], gui_module.UI_STRINGS["it"]["ollama_pull_ask"])

    def test_the_box_does_nothing_for_another_engine(self):
        with self._built() as (gui_module, app, _):
            seen = []
            with mock.patch.object(gui_module.threading, "Thread", _InlineThread), \
                    mock.patch.object(gui_module.App, "_ollama_setup_worker",
                                      lambda self, *a: seen.append(a) or True):
                app._translation_engine.set("google")
                app._ollama_model_combo.event_generate("<<ComboboxSelected>>")
                app.update()
            self.assertEqual(seen, [])

    def test_one_preparation_at_a_time_and_the_next_one_uses_the_box_then(self):
        with self._built() as (gui_module, app, _):
            seen, results = [], []
            with mock.patch.object(gui_module.threading, "Thread", _InlineThread), \
                    mock.patch.object(gui_module.App, "_ollama_setup_worker",
                                      lambda self, model, *a: seen.append(model) or True):
                app._ollama_model_var.set("qwen3:8b")
                app._ensure_ollama_ready_async(on_ready=results.append)
                app._ollama_model_var.set("qwen3:14b")      # changed while the first runs
                app._ensure_ollama_ready_async(on_ready=results.append)
                self.assertEqual(seen, ["qwen3:8b"])         # the second one waits
                for _ in range(20):
                    app.update()
            self.assertEqual(seen, ["qwen3:8b", "qwen3:14b"])
            self.assertEqual(results, [True, True])
            self.assertFalse(app._ollama_setup_running)


if __name__ == "__main__":
    unittest.main()
