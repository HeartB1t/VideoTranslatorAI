"""ElevenLabs settings window. Tk tests: skip without a display, run under Xvfb."""

import gc
import tkinter as tk
import unittest

from test_ui_theme_tk import HAS_DISPLAY
from videotranslator import elevenlabs_dialog_tk as ed
from videotranslator.elevenlabs_tts import Account, ElevenLabsError, Model, Voice
from videotranslator.ui_strings_models import MODELS_UI_STRINGS
from videotranslator.ui_theme import resolve_palette


def _s(key):
    return MODELS_UI_STRINGS["en"].get(key, key)


class _Theme:
    palette = resolve_palette("graphite", "default")


def _make_button(parent, **kwargs):
    kwargs.pop("primary", None)
    wrap = tk.Frame(parent)
    button = tk.Button(wrap, **kwargs)
    button.pack()
    return wrap, button


MODELS = [Model("eleven_multilingual_v2", "Multilingual v2", ("en", "it"), True),
          Model("eleven_flash_v2_5", "Flash v2.5", ("en", "it"), True),
          Model("eleven_english", "English only", ("en",), True)]
VOICES = [Voice("v1", "Adam", "american", "male"), Voice("v2", "Bella", "", "female")]


class _Client:
    def __init__(self, key, fail=None):
        self.key, self.fail = key, fail

    def account(self):
        if self.fail:
            raise ElevenLabsError(self.fail)
        return Account(100, 10000, "starter")

    def models(self):
        return MODELS

    def voices(self):
        return VOICES


SAMPLED = [Voice("v1", "Adam", "", "male", ("it",), "https://s.test/en.mp3",
                  (("it", "https://s.test/it.mp3"),))]


class _Hub:
    def __init__(self):
        self.toggles, self.listeners, self.stopped = [], [], []

    def add_listener(self, fn):
        self.listeners.append(fn)

    def remove_listener(self, fn):
        self.listeners.remove(fn)

    def toggle(self, key, loader, label=""):
        self.toggles.append((key, loader()))
        self.labels = getattr(self, "labels", []) + [label]

    def stop_if(self, prefix):
        self.stopped.append(prefix)

    def emit(self, key, state, kind=None):
        for fn in list(self.listeners):
            fn(key, state, kind)


class CacheTests(unittest.TestCase):
    def test_catalogue_round_trip_has_no_secret(self):
        cache = ed.catalog_to_cache(VOICES, MODELS)
        self.assertEqual(ed.voices_from_cache(cache["voices"]), VOICES)
        self.assertEqual(ed.models_from_cache(cache["models"]), MODELS)
        self.assertEqual(ed.voices_from_cache([{"bad": 1}]), [])

    def test_catalogue_keeps_the_voice_samples(self):
        voices = [Voice("v1", "Adam", "", "male", ("it",), "https://s.test/en.mp3",
                        (("it", "https://s.test/it.mp3"),))]
        cache = ed.catalog_to_cache(voices, MODELS)
        self.assertEqual(ed.voices_from_cache(cache["voices"]), voices)
        self.assertEqual(ed.voices_from_cache([{"voice_id": "v", "name": "N",
                                                "previews": ["bad"]}]), [])


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class DialogTests(unittest.TestCase):
    def setUp(self):
        # Collect Tk variables here, on the main thread: collected later inside a
        # worker thread of another test, Variable.__del__ calls Tk without a
        # running main loop and blocks that thread.
        self.addCleanup(gc.collect)
        self.root = tk.Tk()
        self.root.withdraw()
        self.saved = []
        self.logged = []
        self.levels = []

    def tearDown(self):
        self.root.destroy()

    def _log_cb(self, text, level="info"):
        self.logged.append(text)
        self.levels.append(level)

    def _dialog(self, settings=None, key="sk", fail=None, lang="it", hub=None,
                client=None):
        dlg = ed.ElevenLabsDialog(
            self.root, ui_s=_s, theme=_Theme(), make_button=_make_button,
            settings=settings or {}, api_key=key, target_lang=lang,
            on_save=lambda st, k: self.saved.append((st, k)),
            client_factory=client or (lambda k: _Client(k, fail)), preview_hub=hub,
            sample_loader=lambda url: f"audio:{url}".encode(), log=self._log_cb)
        self.addCleanup(dlg.close)
        return dlg

    def _verify(self, dlg):
        dlg.verify()
        for _ in range(200):
            self.root.update()
            if not dlg._checking:
                return
            self.root.after(10)
        self.fail("verification did not finish")

    def test_verify_loads_catalogue_and_picks_a_fast_model_for_the_language(self):
        dlg = self._dialog()
        self._verify(dlg)
        self.assertEqual(dlg.selected_model().model_id, "eleven_flash_v2_5")
        self.assertEqual(dlg.selected_voice().voice_id, "v1")
        self.assertIn("100 of 10000", dlg._account.cget("text"))

    def test_results_reach_the_app_log(self):
        dlg = self._dialog()
        self._verify(dlg)
        self.assertIn(_s("el_checking"), self.logged)
        self.assertTrue(any("100 of 10000" in line and "2 voices" in line
                            for line in self.logged))
        dlg = self._dialog(fail="auth")
        self._verify(dlg)
        self.assertEqual(self.logged[-1], _s("el_err_auth"))

    def test_verify_error_logs_the_service_message(self):
        class Client(_Client):
            def account(self):
                raise ElevenLabsError("auth", "HTTP 401: Invalid API key")

        dlg = self._dialog(client=lambda k: Client(k))
        self._verify(dlg)
        self.assertEqual(dlg._status.cget("text"), _s("el_err_auth"))
        self.assertIn("ElevenLabs: auth: HTTP 401: Invalid API key", self.logged)
        self.assertEqual(self.levels[self.logged.index(_s("el_err_auth"))], "warn")

    def test_model_without_the_target_language_is_flagged(self):
        dlg = self._dialog()
        self._verify(dlg)
        dlg._model_combo.current(2)
        dlg._check_language()
        self.assertEqual(dlg._status.cget("text"),
                         _s("el_model_no_lang").format(lang="it"))

    def test_errors_are_explained(self):
        dlg = self._dialog(fail="quota")
        self._verify(dlg)
        self.assertEqual(dlg._status.cget("text"), _s("el_err_quota"))
        dlg = self._dialog(key="")
        dlg.verify()
        self.assertEqual(dlg._status.cget("text"), _s("el_err_auth"))

    def test_save_requires_key_model_and_voice_when_enabled(self):
        dlg = self._dialog(key="")
        dlg._enabled.set(True)
        self.assertFalse(dlg.save())
        self.assertEqual(self.saved, [])
        dlg = self._dialog()
        self._verify(dlg)
        dlg._enabled.set(True)
        self.assertTrue(dlg.save())
        settings, key = self.saved[-1]
        self.assertEqual((settings["enabled"], settings["voice_id"], settings["model_id"],
                          key), (True, "v1", "eleven_flash_v2_5", "sk"))
        self.assertNotIn("sk", str(settings))

    def test_cached_catalogue_and_choices_are_shown_offline(self):
        cache = ed.catalog_to_cache(VOICES, MODELS)
        dlg = self._dialog({"catalog": cache, "voice_id": "v2",
                            "model_id": "eleven_multilingual_v2", "fallback": False})
        self.assertEqual(dlg.selected_voice().voice_id, "v2")
        self.assertEqual(dlg.selected_model().model_id, "eleven_multilingual_v2")
        self.assertFalse(dlg._fallback.get())


    def test_paid_voices_are_tagged_last_and_explained_on_a_free_plan(self):
        voices = [Voice("p", "Carmelo", paid_only=True), Voice("r", "Roger")]
        cache = {**ed.catalog_to_cache(voices, MODELS), "tier": "free"}
        dlg = self._dialog({"catalog": cache, "voice_id": "p",
                            "model_id": "eleven_flash_v2_5"})
        self.assertEqual([v.voice_id for v in dlg._voices], ["r", "p"])
        self.assertTrue(dlg._voice_combo.cget("values")[1].startswith(
            f"[{_s('el_voice_paid_tag')}] Carmelo"))
        self.assertEqual(dlg._voice_tip._text_fn(), dlg._voice_combo.get())
        self.assertEqual(dlg._status.cget("text"), _s("el_err_paid_voice"))
        dlg._voice_combo.current(0)
        dlg._voice_changed()
        self.assertEqual(dlg._status.cget("text"), "")
        self.assertEqual(dlg.settings()["catalog"]["tier"], "free")
        paid = {**cache, "tier": "creator"}
        dlg = self._dialog({"catalog": paid, "voice_id": "p"})
        self.assertNotIn(_s("el_voice_paid_tag"), " ".join(dlg._voice_combo.cget("values")))

    def test_no_speaker_without_a_hub(self):
        self.assertIsNone(self._dialog().speaker)

    def test_speaker_plays_the_sample_in_the_target_language(self):
        hub = _Hub()
        dlg = self._dialog({"catalog": ed.catalog_to_cache(SAMPLED, MODELS)}, hub=hub)
        dlg.speaker.click()
        key = "el:v1:https://s.test/it.mp3"
        self.assertEqual(hub.toggles, [(key, b"audio:https://s.test/it.mp3")])
        self.assertEqual(hub.labels, ["Adam"])          # the log names the voice
        hub.emit(key, "playing")
        self.assertEqual(dlg.speaker.state, "playing")
        hub.emit("edge:x", "loading")
        self.assertEqual(dlg.speaker.state, "idle")
        hub.emit(key, "error", "network")
        self.assertEqual(dlg.speaker.state, "error")
        self.assertEqual(dlg._status.cget("text"), _s("vp_err_network"))
        dlg._voice_changed()
        dlg.close()
        self.assertEqual(hub.listeners, [])
        self.assertEqual(hub.stopped, ["el:", "el:"])

    def test_old_catalogue_is_refreshed_once_to_get_the_samples(self):
        hub = _Hub()

        class Client(_Client):
            def voices(self):
                return SAMPLED

        dlg = self._dialog({"catalog": ed.catalog_to_cache(VOICES, MODELS),
                            "voice_id": "v1"}, hub=hub, client=lambda k: Client(k))
        dlg.preview()
        for _ in range(200):
            self.root.update()
            if hub.toggles:
                break
            self.root.after(10)
        self.assertEqual(hub.toggles[0][0], "el:v1:https://s.test/it.mp3")

    def test_voice_without_sample_is_explained(self):
        hub = _Hub()
        dlg = self._dialog({"catalog": ed.catalog_to_cache(VOICES, MODELS)}, key="",
                           hub=hub)
        dlg.preview()
        self.assertEqual(hub.toggles, [])
        self.assertEqual(dlg._status.cget("text"), _s("vp_err_no_sample"))
        self.assertEqual(dlg.speaker.state, "error")


if __name__ == "__main__":
    unittest.main()
