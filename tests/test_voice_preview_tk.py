"""Speaker icon and preview hub. Tk tests: skip without a display, run under Xvfb."""

import gc
import tkinter as tk
import unittest

from test_ui_theme_tk import HAS_DISPLAY
from videotranslator import voice_preview_tk as vpt
from videotranslator.ui_strings_models import MODELS_UI_STRINGS
from videotranslator.ui_theme import resolve_palette


def _s(key):
    return MODELS_UI_STRINGS["en"].get(key, key)


class _Preview:
    def __init__(self, on_state):
        self.on_state = on_state
        self.calls = []
        self.active = None

    def toggle(self, key, loader):
        self.calls.append(("toggle", key))
        self.active = key

    def active_key(self):
        return self.active

    def stop(self):
        self.calls.append(("stop",))

    def close(self, timeout_s):
        self.calls.append(("close", timeout_s))


class HubTests(unittest.TestCase):
    def setUp(self):
        self.posted = []
        self.made = []

        def make(on_state):
            self.made.append(_Preview(on_state))
            return self.made[-1]

        self.hub = vpt.PreviewHub(lambda fn: (self.posted.append(fn), fn()),
                                  make_preview=make)

    def test_preview_is_created_lazily_once(self):
        self.assertEqual(self.made, [])
        self.hub.toggle("a", lambda: b"")
        self.hub.toggle("b", lambda: b"")
        self.assertEqual(len(self.made), 1)
        self.assertEqual(self.made[0].calls, [("toggle", "a"), ("toggle", "b")])

    def test_worker_events_reach_listeners_through_post(self):
        seen = []
        listener = lambda *event: seen.append(event)  # noqa: E731
        self.hub.add_listener(listener)
        self.hub.add_listener(listener)
        self.hub.toggle("a", lambda: b"")
        self.made[0].on_state("a", "playing", None)
        self.assertEqual(seen, [("a", "playing", None)])
        self.assertEqual(len(self.posted), 1)
        self.hub.remove_listener(listener)
        self.made[0].on_state("a", "idle", None)
        self.assertEqual(len(seen), 1)

    def test_dead_listener_is_dropped(self):
        def dead(*_):
            raise tk.TclError("gone")

        self.hub.add_listener(dead)
        self.hub._dispatch("a", "idle", None)
        self.assertEqual(self.hub._listeners, [])

    def test_labels_name_the_voice_for_the_log(self):
        self.hub.toggle("el:pWHq:https://x", lambda: b"", label="Carmelo La Rosa")
        self.assertEqual(self.hub.label("el:pWHq:https://x"), "Carmelo La Rosa")
        self.assertEqual(self.hub.label("unknown"), "")

    def test_stop_if_prefix_and_close(self):
        self.hub.stop_if("el:")                     # nothing created yet
        self.hub.toggle("el:v1", lambda: b"")
        self.hub.stop_if("edge:")
        self.hub.stop_if("el:")
        self.assertEqual(self.made[0].calls.count(("stop",)), 1)
        self.hub.close(1.0)
        self.assertEqual(self.made[0].calls[-1], ("close", 1.0))
        self.hub.toggle("x", lambda: b"")
        self.assertEqual(self.made[0].calls[-1], ("close", 1.0))

    def test_error_keys(self):
        self.assertEqual(vpt.error_key("network"), "vp_err_network")
        self.assertEqual(vpt.error_key(None), "vp_err_failed")
        self.assertEqual(vpt.error_key("weird"), "vp_err_failed")
        for key in vpt.ERROR_KEYS.values():
            self.assertIn(key, MODELS_UI_STRINGS["it"])


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class SpeakerButtonTests(unittest.TestCase):
    def setUp(self):
        # Collect Tk variables here, on the main thread: collected later inside a
        # worker thread of another test, Variable.__del__ calls Tk without a
        # running main loop and blocks that thread.
        self.addCleanup(gc.collect)
        self.root = tk.Tk()
        self.root.withdraw()
        self.clicks = 0
        self.palette = resolve_palette("graphite", "default")

        def click():
            self.clicks += 1

        self.button = vpt.SpeakerButton(self.root, palette=self.palette, bg_role="SURFACE",
                                        ui_s=_s, on_click=click)

    def tearDown(self):
        self.root.destroy()

    def _fills(self):
        canvas = self.button.canvas
        return {canvas.itemcget(item, "fill") for item in canvas.find_withtag("icon")}

    def test_states_change_icon_colour_and_tip(self):
        self.assertEqual(self.button.tip_text(), _s("vp_tip_play"))
        self.assertIn(self.palette.FG, self._fills())
        self.button.set_state("loading")
        self.assertEqual(self.button.tip_text(), _s("vp_loading"))
        self.button.set_state("playing")
        self.assertEqual(self._fills(), {self.palette.ACC})
        self.assertEqual(self.button.tip_text(), _s("vp_tip_stop"))
        self.button.set_state("error", "boom")
        self.assertEqual(self.button.tip_text(), "boom")
        self.assertIn(self.palette.ERR, self._fills())

    def test_click_and_keyboard_call_back_and_clear_the_error(self):
        self.button.set_state("error", "boom")
        self.button.click()
        self.assertEqual((self.clicks, self.button.state), (1, "idle"))
        self.button.canvas.pack()
        self.root.deiconify()
        self.root.update()
        self.button.canvas.focus_force()
        self.root.update()
        self.button.canvas.event_generate("<Return>")
        self.button.canvas.event_generate("<space>")
        self.assertEqual(self.clicks, 3)
        self.assertEqual(int(self.button.canvas.cget("takefocus")), 1)

    def test_theme_change_repaints(self):
        light = resolve_palette("light", "default")
        self.button.apply_palette(light, 1.25)
        self.assertEqual(self.button.canvas.cget("bg"), light.SURFACE)
        self.assertIn(light.FG, self._fills())
        self.assertEqual(int(self.button.canvas.cget("width")), 20 + 8)


if __name__ == "__main__":
    unittest.main()
