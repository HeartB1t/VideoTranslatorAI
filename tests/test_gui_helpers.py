import threading
import unittest
from types import SimpleNamespace
from unittest import mock
from unittest.mock import Mock

import video_translator_gui as gui


class LiveTransportRoutingTests(unittest.TestCase):
    def test_original_mute_routes_to_session(self):
        gui.App._on_live_command(self.app, "original_mute", {"muted": True})
        self.session.set_original_muted.assert_called_once_with(True)

    def setUp(self):
        self.session = Mock()
        self.controller = Mock()
        self.controller.state = SimpleNamespace(position=15.0, duration=22.0)
        self.app = SimpleNamespace(
            _live_session=self.session, _player_controller=self.controller,
            _player_clock=Mock(), _stop_live_session=Mock())

    def test_live_pause_is_an_intent_not_a_second_player_writer(self):
        gui.App._on_player_command(self.app, "play_pause", {})
        self.session.toggle_user_pause.assert_called_once_with()
        self.controller.play_pause.assert_not_called()

    def test_regular_player_keeps_its_pause_behavior(self):
        self.app._live_session = None
        gui.App._on_player_command(self.app, "play_pause", {})
        self.controller.play_pause.assert_called_once_with()

    def test_live_relative_seek_uses_same_bounded_target_for_both_consumers(self):
        for name, expected in (("back_10", 5.0), ("forward_10", 22.0)):
            gui.App._on_player_command(self.app, name, {})
            self.controller.seek.assert_called_with(expected)
            self.session.notify_user_seek.assert_called_with(expected)

    def test_drag_restarts_pipeline_only_on_release(self):
        for target in (3, 9, 14):
            gui.App._on_player_command(self.app, "seek", {"seconds": target, "dragging": True})
        self.session.notify_user_seek.assert_not_called()
        self.controller.seek.assert_not_called()
        gui.App._on_player_command(self.app, "seek", {"seconds": 14})
        self.session.notify_user_seek.assert_called_once_with(14)
        self.controller.seek.assert_called_once_with(14, dragging=False)

    def test_player_stop_also_stops_live_outputs(self):
        gui.App._on_player_command(self.app, "stop", {})
        self.app._stop_live_session.assert_called_once_with()
        self.controller.stop.assert_called_once_with()


class LiveVoiceForTests(unittest.TestCase):
    def _call(self, current, tgt):
        fake = SimpleNamespace(_voice=SimpleNamespace(get=lambda: current))
        return gui.App._live_voice_for(fake, tgt)

    def test_keeps_the_user_voice_when_it_fits_the_target(self):
        voices = gui.LANGUAGES["it"]["voices"]
        self.assertEqual(self._call(voices[1], "it"), voices[1])

    def test_falls_back_to_the_first_catalog_voice(self):
        # an English voice cannot be used for an Italian dub
        self.assertEqual(self._call("en-US-JennyNeural", "it"),
                         gui.LANGUAGES["it"]["voices"][0])

    def test_unknown_target_returns_the_current_voice(self):
        self.assertEqual(self._call("whatever", "zz"), "whatever")


class _FakeVoice:
    def __init__(self):
        self.terminated = False

    def terminate(self, _timeout):
        self.terminated = True
        return True


class RequestVoiceBackendTests(unittest.TestCase):
    """The voice mpv is built on a worker and adopted on Tk only if still valid."""

    def _fake(self, *, session=None):
        threads, posted, logged, stopped = [], [], [], []
        fake = SimpleNamespace(
            _destroying=False, _player_backend=object(), _player_bridge=object(),
            _voice_backend=None, _voice_lock=threading.Lock(),
            _voice_build_token=None, _voice_built=None, _voice_init_thread=None,
            _live_session=session, _player_log=logged.append,
            threads=threads, posted=posted, logged=logged, stopped=stopped)
        fake._redirecting_thread_factory = (
            lambda target, name=None: threads.append(target) or SimpleNamespace(
                start=lambda: None, is_alive=lambda: False, join=lambda *_a: None))
        fake._post_if_alive = posted.append
        fake._on_voice_backend_ready = lambda: gui.App._on_voice_backend_ready(fake)
        fake._on_voice_backend_failed = (
            lambda exc: gui.App._on_voice_backend_failed(fake, exc))
        fake._terminate_voice_async = stopped.append
        return fake

    def _build(self, fake, create):
        # Patches stay active for the whole test: the worker runs after this
        # returns, and must never reach the real libmpv.
        self.enterContext(mock.patch.object(gui._libmpv_runtime, "load_mpv",
                                            return_value="MOD"))
        self.enterContext(mock.patch.object(gui._player_engine,
                                            "create_voice_backend", create))
        gui.App._request_voice_backend(fake)
        return list(fake.threads)

    def test_libmpv_runs_on_the_worker_not_on_tk(self):
        voice = _FakeVoice()
        calls = []
        create = lambda **kw: calls.append(kw) or voice
        fake = self._fake()
        with mock.patch.object(gui._libmpv_runtime, "load_mpv", return_value="MOD"), \
                mock.patch.object(gui._player_engine, "create_voice_backend", create):
            gui.App._request_voice_backend(fake)
            self.assertEqual(calls, [])                   # nothing built on Tk
            fake.threads[0]()                             # the worker runs it
        self.assertIs(calls[0]["bridge"], fake._player_bridge)
        for fn in fake.posted:
            fn()
        self.assertIs(fake._voice_backend, voice)

    def test_only_one_build_at_a_time(self):
        fake = self._fake()
        self._build(fake, lambda **kw: _FakeVoice())
        with mock.patch.object(gui._libmpv_runtime, "load_mpv", return_value="MOD"):
            gui.App._request_voice_backend(fake)
        self.assertEqual(len(fake.threads), 1)

    def test_ready_backend_is_attached_to_the_running_session(self):
        session = Mock()
        fake = self._fake(session=session)
        voice = _FakeVoice()
        worker, = self._build(fake, lambda **kw: voice)
        worker()
        fake.posted[0]()
        session.attach_voice.assert_called_once_with(voice)

    def test_result_for_a_replaced_bridge_is_terminated_not_adopted(self):
        fake = self._fake()
        voice = _FakeVoice()
        worker, = self._build(fake, lambda **kw: voice)
        worker()
        fake._player_bridge = object()                    # VO fallback replaced it
        fake.posted[0]()
        self.assertIsNone(fake._voice_backend)
        self.assertEqual(fake.stopped, [voice])

    def test_close_during_the_build_terminates_the_result(self):
        fake = self._fake()
        voice = _FakeVoice()
        worker, = self._build(fake, lambda **kw: voice)
        gui.App._take_voice_build(fake)                   # what close/fallback do
        worker()                                          # build ends afterwards
        self.assertTrue(voice.terminated)
        self.assertEqual(fake.posted, [])

    def test_build_failure_tells_the_session_and_logs(self):
        session = Mock()
        fake = self._fake(session=session)

        def boom(**_kw):
            raise RuntimeError("no libmpv")
        worker, = self._build(fake, boom)
        worker()
        fake.posted[0]()
        session.voice_unavailable.assert_called_once_with()
        self.assertTrue(fake.logged)
        self.assertIsNone(fake._voice_build_token)


class OnPlayerStateLiveTests(unittest.TestCase):
    def _fake(self, session):
        stopped = []
        fake = SimpleNamespace(
            _live_session=session,
            stopped=stopped,
            _stop_live_session=lambda: stopped.append(True),
            _player_clock=SimpleNamespace(expect_restart=lambda: None),
            _player_loaded_at=1.0,
            _player_video_params_seen=True,
            _player_log_lines=[1, 2],
            _player_panel=None,
            _player_backend=None,
            _refresh_live_bar_enabled=lambda: None,
        )
        return fake

    def test_loading_a_new_media_stops_a_running_session(self):
        fake = self._fake(object())
        gui.App._on_player_state(fake, SimpleNamespace(status="loading", item=None))
        self.assertEqual(fake.stopped, [True])

    def test_loading_does_nothing_without_a_session(self):
        fake = self._fake(None)
        gui.App._on_player_state(fake, SimpleNamespace(status="loading", item=None))
        self.assertEqual(fake.stopped, [])

    def test_non_loading_status_never_stops_the_session(self):
        fake = self._fake(object())
        gui.App._on_player_state(fake, SimpleNamespace(status="playing", item=None))
        self.assertEqual(fake.stopped, [])


class NoisyX11LogTests(unittest.TestCase):
    def test_matches_the_x11_badwindow_block(self):
        for line in (
            "X11 error: BadWindow (invalid Window parameter)",
            "Type: 0, display: 0x1f18ba00, resourceid: 4e4307d, serial: 1a484e",
            "Error code: 3, request code: f, minor code: 0",
        ):
            self.assertTrue(gui._is_noisy_x11_log(line), line)

    def test_keeps_normal_mpv_lines(self):
        for line in (
            "Using hardware decoding (nvdec).",
            "VO: [gpu] 1280x720 yuv420p",
            "File tags: title=...",
            "",
        ):
            self.assertFalse(gui._is_noisy_x11_log(line), line)

    def test_keeps_non_badwindow_error_headers(self):
        # a BadMatch/BadAlloc header is a real signal, not collapsed noise
        for line in (
            "X11 error: BadMatch (invalid parameter attributes)",
            "X11 error: BadAlloc (insufficient resources for operation)",
            "X11 error: BadValue (integer parameter out of range)",
        ):
            self.assertFalse(gui._is_noisy_x11_log(line), line)


if __name__ == "__main__":
    unittest.main()
