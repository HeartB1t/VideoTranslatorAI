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


class LiveChoicesPersistenceTests(unittest.TestCase):
    """The live bar remembers mode/engine/dub/subs/delay across launches."""

    def _bar(self, kind="file"):
        return SimpleNamespace(source_kind=kind, current_settings=lambda: {
            "mode": "live", "delay": 12.5, "engine": "ollama",
            "dub": False, "subs": True})

    def test_choice_changes_schedule_a_save_even_without_a_session(self):
        for intent in ("mode", "delay", "engine", "dub", "subs"):
            app = SimpleNamespace(_live_session=None, _schedule_live_save=Mock())
            gui.App._on_live_command(app, intent, {})
            app._schedule_live_save.assert_called_once_with()

    def test_original_mute_is_not_persisted(self):
        app = SimpleNamespace(_live_session=Mock(), _schedule_live_save=Mock())
        gui.App._on_live_command(app, "original_mute", {"muted": True})
        app._schedule_live_save.assert_not_called()

    def test_save_writes_config_keys_with_delay_by_slider_range(self):
        for kind, key in (("file", "live_file_ahead_s"), ("url", "live_delay_s")):
            app = SimpleNamespace(_live_bar=self._bar(kind), _live_save_after=None)
            with mock.patch.object(gui, "save_config") as save:
                gui.App._save_live_choices(app)
            save.assert_called_once_with({
                "live_sync_mode": "live", "live_engine": "ollama",
                "live_dub_enabled": False, "live_subs_enabled": True,
                key: 12.5})

    def test_saved_choices_round_trip_through_normalize(self):
        app = SimpleNamespace(_live_bar=self._bar("file"), _live_save_after=None)
        with mock.patch.object(gui, "save_config") as save:
            gui.App._save_live_choices(app)
        settings = gui._player_settings_module.normalize_live_settings(
            save.call_args.args[0])
        self.assertEqual((settings.sync_mode, settings.engine, settings.dub_enabled,
                          settings.subs_enabled, settings.file_ahead_s),
                         ("live", "ollama", False, True, 12.5))

    def test_schedule_debounces_slider_drags(self):
        app = SimpleNamespace(_live_save_after="old", after=Mock(return_value="new"),
                              after_cancel=Mock(), _save_live_choices=Mock())
        gui.App._schedule_live_save(app)
        app.after_cancel.assert_called_once_with("old")
        self.assertEqual(app._live_save_after, "new")
        app._save_live_choices.assert_not_called()


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class ModelChoicesTests(unittest.TestCase):
    """'Models for this PC': apply, restore previous, survive a restart."""

    def setUp(self):
        self.config = {}
        self.enterContext(mock.patch.object(gui, "load_config",
                                            side_effect=lambda: dict(self.config)))
        self.enterContext(mock.patch.object(gui, "save_config",
                                            side_effect=self.config.update))
        self.app = SimpleNamespace(
            _model=_Var("small"), _translation_engine=_Var("google"),
            _ollama_model_var=_Var("qwen3:8b"), _use_xtts=_Var(False),
            _use_voicebox=_Var(False),
            _active_profile=_Var("balanced"), _live_bar=Mock(), _destroying=False,
            _on_engine_change=Mock(), _update_profile_buttons=Mock(),
            _update_start_summary=Mock(), _models_choice_restored=False)
        for name in ("_current_model_choices", "_set_model_choices"):
            setattr(self.app, name, getattr(gui.App, name).__get__(self.app))

    def test_current_choices_map_the_gui_state(self):
        self.config["live_asr_model"] = "base"
        self.assertEqual(self.app._current_model_choices(),
                         {"asr": "small", "asr_live": "base", "mt": "google", "tts": "edge"})
        self.app._translation_engine.set("llm_ollama")
        self.app._use_xtts.set(True)
        self.assertEqual(self.app._current_model_choices()["mt"], "qwen3:8b")
        self.assertEqual(self.app._current_model_choices()["tts"], "xtts")

    def test_set_choices_updates_batch_and_live_settings(self):
        gui.App._set_model_choices(self.app, {"asr": "large-v3", "asr_live": "medium",
                                              "mt": "qwen3:14b", "tts": "xtts"})
        self.assertEqual((self.app._model.get(), self.app._translation_engine.get(),
                          self.app._ollama_model_var.get(), self.app._use_xtts.get()),
                         ("large-v3", "llm_ollama", "qwen3:14b", True))
        self.assertEqual((self.config["live_asr_model"], self.config["live_engine"]),
                         ("medium", "ollama"))
        self.app._live_bar.set_config_values.assert_called_once()
        self.assertEqual(self.app._active_profile.get(), "custom")
        self.app._on_engine_change.assert_called_once_with()

    def test_voicebox_choice_turns_xtts_off(self):
        self.app._use_xtts.set(True)
        gui.App._set_model_choices(self.app, {"tts": "voicebox"})
        self.assertEqual((self.app._use_voicebox.get(), self.app._use_xtts.get()),
                         (True, False))
        self.assertEqual(self.app._current_model_choices()["tts"], "voicebox")
        gui.App._set_model_choices(self.app, {"tts": "edge"})
        self.assertFalse(self.app._use_voicebox.get())

    def test_unknown_values_are_ignored(self):
        gui.App._set_model_choices(self.app, {"asr": "huge", "mt": "bing", "tts": "robot",
                                              "asr_live": "giant"})
        self.assertEqual((self.app._model.get(), self.app._translation_engine.get(),
                          self.app._use_xtts.get()), ("small", "google", False))
        self.assertNotIn("live_asr_model", self.config)

    def test_apply_saves_previous_and_revert_swaps_back(self):
        new = {"asr": "medium", "asr_live": "small", "mt": "marian", "tts": "edge"}
        gui.App._apply_model_choices(self.app, new)
        self.assertEqual(self.config[gui._MODELS_CHOICE_KEY], new)
        self.assertEqual(self.config[gui._MODELS_PREVIOUS_KEY]["asr"], "small")
        self.assertEqual(self.app._model.get(), "medium")
        restored = gui.App._revert_model_choices(self.app)
        self.assertEqual(restored["asr"], "small")
        self.assertEqual(self.app._model.get(), "small")
        self.assertEqual(self.config[gui._MODELS_PREVIOUS_KEY]["asr"], "medium")

    def test_revert_without_previous_returns_none(self):
        self.assertIsNone(gui.App._revert_model_choices(self.app))

    def test_startup_restores_the_applied_choices(self):
        self.config[gui._MODELS_CHOICE_KEY] = {"asr": "tiny", "mt": "deepl"}
        gui.App._restore_model_choices(self.app)
        self.assertEqual((self.app._model.get(), self.app._translation_engine.get()),
                         ("tiny", "deepl"))
        self.assertTrue(self.app._models_choice_restored)

    def test_a_preset_click_forgets_the_window_choice(self):
        self.config[gui._MODELS_CHOICE_KEY] = {"asr": "tiny"}
        app = SimpleNamespace(**vars(self.app), _no_demucs=_Var(False),
                              _use_lipsync=_Var(False))
        gui.App._apply_profile(app, "fast")
        self.assertIsNone(self.config[gui._MODELS_CHOICE_KEY])
        self.assertEqual(app._model.get(), "small")


class LaunchLiveSessionConfigTests(unittest.TestCase):
    """What the window settings put into a live session's configuration."""

    def _launch(self, config, *, el_key=""):
        bar = Mock()
        bar.current_settings.return_value = {
            "mode": "delayed", "delay": 8.0, "engine": "marian", "dub": False,
            "subs": True, "original_mute": False}
        app = SimpleNamespace(
            _live_bar=bar, _lang_tgt=_Var("it"), _lang_src=_Var("en"),
            _player_controller=Mock(state=SimpleNamespace(position=0.0), paused=False),
            _live_voice_for=lambda tgt: "it-IT-X", _deepl_key_var=_Var(""),
            _ollama_url_var=_Var(""), _ollama_model_var=_Var(""),
            _voice_backend=None, _player_backend=Mock(), _player_clock=Mock(),
            _player_log=Mock(), _redirecting_thread_factory=None,
            _schedule_live_poll=Mock(), _request_voice_backend=Mock(),
            _refresh_live_bar_enabled=Mock(), _live_resolving=True)
        app._elevenlabs_settings = lambda: dict(config.get("elevenlabs") or {})
        app._live_tts_opts = gui.App._live_tts_opts.__get__(app)
        captured = {}

        def session(cfg, **kw):
            captured["cfg"] = cfg
            return Mock()
        with mock.patch.object(gui, "load_config", return_value=config), \
                mock.patch.object(gui, "load_elevenlabs_key", return_value=el_key), \
                mock.patch.object(gui._live_session_module, "LiveSession", side_effect=session):
            gui.App._launch_live_session(app, "/v.mp4", "file", title=None)
        return captured["cfg"]

    def test_file_slider_is_the_file_buffer(self):
        settings = self._launch({}).settings
        self.assertEqual((settings.file_ahead_s, settings.delay_s), (8.0, None))

    def test_live_asr_model_from_the_models_window_reaches_the_session(self):
        self.assertEqual(self._launch({"live_asr_model": "base"}).settings.asr_model, "base")
        self.assertEqual(self._launch({}).settings.asr_model, "auto")

    def test_elevenlabs_options_reach_the_session_only_when_complete(self):
        el = {"enabled": True, "voice_id": "v", "model_id": "eleven_flash_v2_5",
              "fallback": False}
        cfg = self._launch({"elevenlabs": el}, el_key="sk")
        self.assertEqual(cfg.tts_opts, {"engine": "elevenlabs", "api_key": "sk",
                                        "voice_id": "v", "model_id": "eleven_flash_v2_5",
                                        "fallback": False})
        self.assertEqual(self._launch({"elevenlabs": el}, el_key="").tts_opts, {})
        self.assertEqual(self._launch({"elevenlabs": {**el, "enabled": False}},
                                      el_key="sk").tts_opts, {})


class LanguageNameTests(unittest.TestCase):
    def test_languages_are_named_in_their_own_language(self):
        self.assertEqual(gui.LANGUAGES["de"]["name"], "🇩🇪 Deutsch")
        self.assertEqual(gui.LANGUAGES["ja"]["name"], "🇯🇵 日本語")
        self.assertEqual(set(gui.LANGUAGE_NATIVE_NAMES), set(gui.LANGUAGES))

    def test_auto_detect_label_follows_the_ui_language(self):
        for lang in ("en", "it", "de"):
            app = SimpleNamespace(_s=lambda key, lang=lang: gui.UI_STRINGS[lang][key])
            labels = gui.App._source_lang_labels(app)
            self.assertEqual(labels[0], "🔍 " + gui.UI_STRINGS[lang]["lang_auto_detect"])
            self.assertEqual(labels[1:], [gui.SOURCE_LANGS[c]
                                          for c in gui.SOURCE_LANG_CODES[1:]])
        self.assertEqual(gui.UI_STRINGS["de"]["lang_auto_detect"], "Automatisch erkennen")


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


class VoFallbackLiveOutputsTests(unittest.TestCase):
    """A VO fallback replaces the player backend and its bridge: the live session
    and the voice mpv bound to them must be retired first, never reused."""

    def _events(self):
        events = []
        live = Mock()
        live.join.side_effect = lambda *_a: events.append("live.join")
        live.request_stop.side_effect = lambda: events.append("live.request_stop")
        voice = Mock()
        voice.terminate.side_effect = lambda *_a: events.append("voice.terminate")
        built = Mock()
        built.terminate.side_effect = lambda *_a: events.append("built.terminate")
        backend = Mock()
        backend.terminate.side_effect = lambda *_a: events.append("backend.terminate")
        bridge = Mock()
        bridge.close.side_effect = lambda: events.append("bridge.close")
        return events, live, voice, built, backend, bridge

    def _fake(self, live, voice, built, bridge):
        fake = SimpleNamespace(
            _live_session=live, _live_stopping=True, _live_startup_pending=True,
            _live_poll_after=None, _voice_backend=voice, _voice_lock=threading.Lock(),
            _voice_build_token=object(), _voice_built=(bridge, object(), built),
            _live_bar=Mock(), _player_log=lambda *_a: None, _player_bridge=bridge,
            _player_guard=None, _player_init_thread=None)
        fake._refresh_live_bar_enabled = lambda: None
        fake._take_voice_build = lambda: gui.App._take_voice_build(fake)
        fake._fallback_lock = threading.Lock()
        fake._fallback_ready = None
        fake._take_fallback_ready = lambda: gui.App._take_fallback_ready(fake)
        fake._adopt_fallback_player = lambda: gui.App._adopt_fallback_player(fake)
        fake._retire_live_outputs = gui.App._retire_live_outputs
        fake._redirecting_thread_factory = (
            lambda target, name=None: SimpleNamespace(start=target))
        fake._post_if_alive = lambda fn: fn()
        return fake

    def test_detach_stops_the_session_and_takes_every_voice(self):
        events, live, voice, built, _backend, bridge = self._events()
        fake = self._fake(live, voice, built, bridge)
        got_live, voices = gui.App._detach_live_outputs(fake)
        self.assertIs(got_live, live)
        self.assertEqual(events, ["live.request_stop"])  # no blocking join on Tk
        self.assertEqual(voices, [voice, built])
        self.assertIsNone(fake._live_session)
        self.assertIsNone(fake._voice_backend)             # never reused afterwards
        self.assertIsNone(fake._voice_build_token)         # a running build is void
        fake._live_bar.set_active.assert_called_with(False)

    def test_failed_player_retires_live_outputs_before_its_backend(self):
        events, live, voice, built, backend, bridge = self._events()
        fake = self._fake(live, voice, built, bridge)
        done = []
        gui.App._terminate_failed_player(fake, backend, lambda: done.append(True),
                                         live=live, voices=[voice, built])
        self.assertEqual(events, ["live.join", "voice.terminate", "built.terminate",
                                  "backend.terminate", "bridge.close"])
        self.assertEqual(done, [True])

    def _run_replacement(self, fake, backend, events, *, post=None,
                         destroy_before_handoff=False):
        fake.__dict__.update(
            _player_backend=backend, _player_status=SimpleNamespace(vo_profiles_ok=("a",)),
            _player_vo_profile="x", _player_controller=Mock(), _player_init_running=False,
            _player_vo_retries=0, _player_guard=SimpleNamespace(
                captured=True, restore=lambda: events.append("guard.restore")),
            _player_panel=SimpleNamespace(host_wid=lambda: 1), _player_mixer=object(),
            _destroying=False)
        fake._detach_live_outputs = lambda: gui.App._detach_live_outputs(fake)
        fake._on_player_fallback_ready = lambda *a: events.append("fallback.ready")
        fake._on_player_init_failed = lambda exc: events.append(f"failed:{exc}")
        if post is not None:
            fake._post_if_alive = post
        replacement = Mock()
        replacement.terminate.side_effect = (
            lambda *_a: events.append("replacement.terminate"))

        def create(**_kw):
            if destroy_before_handoff:
                fake._destroying = True          # a close starts meanwhile
            return replacement
        with mock.patch.object(gui._player_engine, "next_vo_profile", return_value="b"), \
                mock.patch.object(gui._libmpv_runtime, "load_mpv", return_value="M"), \
                mock.patch.object(gui._player_engine, "EventBridge", return_value=Mock()), \
                mock.patch.object(gui._player_engine, "create_video_backend", create), \
                mock.patch.object(gui.sys, "platform", "linux"):
            gui.App._begin_player_vo_fallback(fake)
        return replacement

    def test_close_before_handoff_terminates_the_replacement_in_the_worker(self):
        events, live, voice, built, backend, bridge = self._events()
        fake = self._fake(live, voice, built, bridge)
        self._run_replacement(fake, backend, events, destroy_before_handoff=True)
        self.assertIn("replacement.terminate", events)
        self.assertNotIn("fallback.ready", events)
        # the guard is restored only after the replacement mpv is gone
        self.assertGreater(len(events) - events[::-1].index("guard.restore"),
                           events.index("replacement.terminate"))
        self.assertIsNone(gui.App._take_fallback_ready(fake))

    def test_close_after_handoff_can_take_the_replacement(self):
        # The Tk callback is dropped once closing: the replacement waits in the
        # slot, where the close takes it (and terminates it) instead of leaking.
        events, live, voice, built, backend, bridge = self._events()
        fake = self._fake(live, voice, built, bridge)
        replacement = self._run_replacement(fake, backend, events,
                                            post=lambda fn: None)
        taken = gui.App._take_fallback_ready(fake)
        self.assertIs(taken[0], replacement)
        self.assertNotIn("fallback.ready", events)

    def test_replacement_branch_retires_live_outputs_before_its_backend(self):
        events, live, voice, built, backend, bridge = self._events()
        fake = self._fake(live, voice, built, bridge)
        fake.__dict__.update(
            _player_backend=backend, _player_status=SimpleNamespace(vo_profiles_ok=("a",)),
            _player_vo_profile="x", _player_controller=Mock(), _player_init_running=False,
            _player_vo_retries=0, _player_guard=SimpleNamespace(captured=True,
                                                               restore=lambda: None),
            _player_panel=SimpleNamespace(host_wid=lambda: 1), _player_mixer=object(),
            _destroying=False)
        fake._detach_live_outputs = lambda: gui.App._detach_live_outputs(fake)
        fake._on_player_fallback_ready = lambda *a: events.append("fallback.ready")
        fake._on_player_init_failed = lambda exc: events.append(f"failed:{exc}")
        replacement = Mock()
        with mock.patch.object(gui._player_engine, "next_vo_profile", return_value="b"), \
                mock.patch.object(gui._libmpv_runtime, "load_mpv", return_value="M"), \
                mock.patch.object(gui._player_engine, "EventBridge", return_value=Mock()), \
                mock.patch.object(gui._player_engine, "create_video_backend",
                                  return_value=replacement), \
                mock.patch.object(gui.sys, "platform", "linux"):
            gui.App._begin_player_vo_fallback(fake)
        self.assertEqual(events, ["live.request_stop", "live.join", "voice.terminate",
                                  "built.terminate", "backend.terminate",
                                  "bridge.close", "fallback.ready"])


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


SEI_1 = ("h264: Late SEI is not implemented. Update your FFmpeg version to the newest "
         "one from Git. If the problem still occurs, it means that your file has a "
         "feature which has not been implemented.")
SEI_2 = ("h264: If you want to help, upload a sample of this file to "
         "https://streams.videolan.org/upload/ and contact the ffmpeg-devel mailing "
         "list. (ffmpeg-devel@ffmpeg.org)")
MP3 = "mp3: Estimating duration from bitrate, this may be inaccurate"


class HarmlessMpvLogTests(unittest.TestCase):
    def test_classifies_the_repetitive_harmless_notices(self):
        self.assertEqual(gui._harmless_mpv_log_kind(SEI_1), "h264_late_sei")
        self.assertEqual(gui._harmless_mpv_log_kind(SEI_2), "h264_late_sei")
        self.assertEqual(gui._harmless_mpv_log_kind(MP3), "mp3_duration")
        for line in ("Using hardware decoding (nvdec).", "VO: [gpu] 1280x720",
                     "X11 error: BadWindow (invalid Window parameter)",
                     "h264: some other decoder error", ""):
            self.assertIsNone(gui._harmless_mpv_log_kind(line), line)

    def _fake(self):
        written = []
        fake = SimpleNamespace(_mpv_x11_noise=0, _mpv_x11_noise_at=0.0,
                               _mpv_quiet_seen=set(), _player_log_lines=[],
                               _log_write=written.append, written=written)
        return fake

    def test_each_harmless_notice_is_shown_once_then_hidden(self):
        fake = self._fake()
        for line in [SEI_1, SEI_2, MP3, SEI_1, SEI_2, MP3, MP3, "VO: [gpu] 1280x720"]:
            gui.App._log_mpv_line(fake, line)
        text = "".join(fake.written)
        self.assertEqual(text.count("Late SEI"), 1)
        self.assertEqual(text.count("upload a sample"), 0)   # the companion line
        self.assertEqual(text.count("Estimating duration"), 1)
        self.assertEqual(text.count("repeats of this message are hidden"), 2)
        self.assertIn("[mpv] VO: [gpu] 1280x720\n", fake.written)
        self.assertEqual(fake._player_log_lines, ["VO: [gpu] 1280x720"])

    def test_x11_summary_behaviour_is_unchanged(self):
        fake = self._fake()
        block = ["X11 error: BadWindow (invalid Window parameter)",
                 "Type: 0, display: 0x1, resourceid: 2, serial: 3",
                 "Error code: 3, request code: f, minor code: 0"]
        for line in block * 2:
            gui.App._log_mpv_line(fake, line)
        self.assertEqual(fake.written[:3], [f"[mpv] {line}\n" for line in block])
        self.assertIn("harmless X11 window errors", fake.written[3])
        self.assertEqual(len(fake.written), 4)


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
