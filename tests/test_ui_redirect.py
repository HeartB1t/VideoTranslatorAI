"""_GlobalRedirect under pythonw and the redirecting thread factory (spec R9, [CC] G2).

No display needed: the factory is bound to a stand-in object that has the
two attributes _TkStreamRedirect uses (after, _log_write).
"""

import io
import threading
import types
import unittest

import video_translator_gui as legacy


class _FakeApp:
    def __init__(self):
        self.scheduled = []
        self.written = []

    def after(self, _delay, callback, *args):
        self.scheduled.append((callback, args))

    def run_scheduled(self):
        """Play the Tk callbacks the redirect scheduled, as the Tk loop would."""
        for callback, args in self.scheduled:
            callback(*args)

    def _log_write(self, text):
        self.written.append(text)


class GlobalRedirectWithoutConsoleTests(unittest.TestCase):
    def setUp(self):
        legacy._thread_local.redirect = None

    def test_write_without_an_original_stream_drops_the_text(self):
        redirect = legacy._GlobalRedirect(None)
        self.assertEqual(redirect.write("x"), 1)
        self.assertEqual(redirect.write(""), 0)

    def test_flush_without_an_original_stream_does_not_raise(self):
        legacy._GlobalRedirect(None).flush()

    def test_fileno_without_an_original_stream_is_unsupported(self):
        with self.assertRaises(io.UnsupportedOperation):
            legacy._GlobalRedirect(None).fileno()

    def test_a_thread_local_redirect_still_wins(self):
        sink = io.StringIO()
        legacy._thread_local.redirect = sink
        try:
            legacy._GlobalRedirect(None).write("hello")
        finally:
            legacy._thread_local.redirect = None
        self.assertEqual(sink.getvalue(), "hello")

    def test_the_original_stream_is_used_when_present(self):
        original = io.StringIO()
        legacy._GlobalRedirect(original).write("abc")
        self.assertEqual(original.getvalue(), "abc")


class RedirectingThreadFactoryTests(unittest.TestCase):
    def setUp(self):
        legacy._thread_local.redirect = None
        self.app = _FakeApp()
        self.factory = types.MethodType(legacy.App._redirecting_thread_factory, self.app)

    def test_the_thread_installs_the_gui_redirect_for_its_target(self):
        seen = {}

        def target():
            seen["redirect"] = legacy._thread_local.redirect
            legacy._GlobalRedirect(None).write("from a worker")

        thread = self.factory(target, name="player-status")
        self.assertIsInstance(thread, threading.Thread)
        self.assertTrue(thread.daemon)
        self.assertEqual(thread.name, "player-status")
        thread.start()
        thread.join(5)
        self.assertIsInstance(seen["redirect"], legacy._TkStreamRedirect)
        # The text reaches the log through Tk callbacks (the throttled flush,
        # or the final flush when the dropped redirect object is closed).
        self.app.run_scheduled()
        self.assertEqual("".join(self.app.written), "from a worker")

    def test_the_redirect_is_removed_even_when_the_target_raises(self):
        def target():
            raise RuntimeError("boom")

        thread = self.factory(target, name="t")
        with self.assertRaises(RuntimeError):
            thread.run()  # runs here, so this thread's local is observable
        self.assertIsNone(legacy._thread_local.redirect)

    def test_keyword_call_like_threading_thread(self):
        thread = self.factory(target=lambda: None, name="t", daemon=False)
        self.assertFalse(thread.daemon)


if __name__ == "__main__":
    unittest.main()
