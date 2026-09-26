"""Pure player engine primitives (spec 2.2, 3.1 and 4.13)."""

import threading
import time
import unittest
from types import SimpleNamespace

from videotranslator import player_engine as pe


class EventBridgeTests(unittest.TestCase):
    def test_latest_values_coalesce_and_drain_reports_only_changes(self):
        bridge = pe.EventBridge()
        bridge.set_latest("time-pos", 1.0, 10.0)
        bridge.set_latest("time-pos", 2.0, 11.0)
        bridge.set_latest("pause", False, 11.5)
        self.assertEqual(bridge.latest("time-pos"), (2.0, 11.0))
        first = bridge.drain()
        self.assertEqual(first.changed, {
            "time-pos": (2.0, 11.0),
            "pause": (False, 11.5),
        })
        self.assertEqual(first.events, ())
        self.assertEqual(bridge.drain().changed, {})

    def test_full_event_queue_discards_oldest_logs_first(self):
        bridge = pe.EventBridge(max_events=4)
        bridge.post("file-loaded", "first")
        bridge.post("log", "old log")
        bridge.post("playback-restart", 1)
        bridge.post("log", "new log")
        bridge.post("end-file", "eof")
        events = bridge.drain().events
        self.assertEqual([(event.kind, event.payload) for event in events], [
            ("file-loaded", "first"),
            ("playback-restart", 1),
            ("log", "new log"),
            ("end-file", "eof"),
        ])

    def test_when_no_log_exists_the_oldest_event_is_discarded(self):
        bridge = pe.EventBridge(max_events=2)
        bridge.post("file-loaded", 1)
        bridge.post("playback-restart", 2)
        bridge.post("end-file", 3)
        self.assertEqual([event.payload for event in bridge.drain().events], [2, 3])

    def test_close_drops_later_writes_but_keeps_latest_values(self):
        bridge = pe.EventBridge()
        bridge.set_latest("time-pos", 3.0, 1.0)
        bridge.post("file-loaded", 1)
        bridge.close()
        bridge.set_latest("time-pos", 4.0, 2.0)
        bridge.post("end-file", 2)
        self.assertEqual(bridge.latest("time-pos"), (3.0, 1.0))
        self.assertEqual([event.kind for event in bridge.drain().events], ["file-loaded"])

    def test_unknown_property_and_integer_event_are_ignored(self):
        bridge = pe.EventBridge()
        bridge.set_latest("not-an-mpv-property", 1, 2.0)
        bridge.post(9, "old mpv event")
        self.assertIsNone(bridge.latest("not-an-mpv-property"))
        self.assertEqual(bridge.drain().events, ())


class PlaybackClockTests(unittest.TestCase):
    def test_extrapolates_only_while_running_and_honours_speed(self):
        clock = pe.PlaybackClock()
        clock.observe(10.0, 100.0, speed=1.5, running=True, seeking=False)
        self.assertEqual(clock.now(102.0), 13.0)
        clock.observe(13.0, 102.0, speed=1.0, running=False, seeking=False)
        self.assertEqual(clock.now(110.0), 13.0)

    def test_seek_trace_ignores_clamped_values_until_restart(self):
        clock = pe.PlaybackClock()
        clock.observe(1007.52, 1.0, speed=1.0, running=True, seeking=False)
        clock.expect_restart()
        clock.observe(7.14, 1.1, speed=1.0, running=True, seeking=False)
        self.assertIsNone(clock.now(1.2))
        clock.on_playback_restart(1.3)
        self.assertEqual(clock.epoch, 1)
        clock.observe(1007.56, 1.31, speed=1.0, running=True, seeking=False)
        self.assertAlmostEqual(clock.now(1.41), 1007.66)

    def test_values_while_seeking_or_below_first_pts_are_ignored(self):
        clock = pe.PlaybackClock(first_pts=50.0)
        clock.observe(10.0, 1.0, speed=1.0, running=True, seeking=False)
        self.assertIsNone(clock.now(1.1))
        clock.observe(55.0, 2.0, speed=1.0, running=True, seeking=True)
        self.assertIsNone(clock.now(2.1))
        clock.observe(55.0, 3.0, speed=1.0, running=True, seeking=False)
        self.assertAlmostEqual(clock.now(3.5), 55.5)

    def test_none_position_invalidates_the_clock(self):
        clock = pe.PlaybackClock()
        clock.observe(4.0, 1.0, speed=1.0, running=True, seeking=False)
        clock.observe(None, 2.0, speed=1.0, running=True, seeking=False)
        self.assertFalse(clock.valid)
        self.assertIsNone(clock.now(3.0))


class CommandQueueTests(unittest.TestCase):
    def test_same_key_replaces_the_queued_command_in_place(self):
        queue = pe.CommandQueue(maxsize=3)
        calls = []
        self.assertTrue(queue.put(lambda: calls.append("seek-1"), key="seek"))
        self.assertTrue(queue.put(lambda: calls.append("pause"), key="pause"))
        self.assertTrue(queue.put(lambda: calls.append("seek-2"), key="seek"))
        queue.get(0)()
        queue.get(0)()
        self.assertEqual(calls, ["seek-2", "pause"])

    def test_full_queue_rejects_new_key_but_allows_replacement(self):
        queue = pe.CommandQueue(maxsize=2)
        self.assertTrue(queue.put(lambda: None, key="a"))
        self.assertTrue(queue.put(lambda: None, key="b"))
        self.assertFalse(queue.put(lambda: None, key="c"))
        self.assertTrue(queue.put(lambda: None, key="a"))

    def test_close_wakes_a_waiter_and_rejects_writes(self):
        queue = pe.CommandQueue()
        received = []
        waiter = threading.Thread(target=lambda: received.append(queue.get(1.0)))
        waiter.start()
        queue.close()
        waiter.join(1.0)
        self.assertFalse(waiter.is_alive())
        self.assertEqual(received, [None])
        self.assertFalse(queue.put(lambda: None))


class VolumeMixerTests(unittest.TestCase):
    def test_volume_duck_mute_and_owner_increment_versions(self):
        mixer = pe.VolumeMixer(user_volume=100)
        initial = mixer.snapshot()
        self.assertEqual((initial.version, initial.owner, initial.video_volume,
                          initial.voice_volume, initial.muted),
                         (0, "cmd", 100.0, 100.0, False))
        mixer.set_duck_gain(0.25)
        self.assertEqual(mixer.snapshot().video_volume, 25.0)
        mixer.set_user_volume(80)
        state = mixer.snapshot()
        self.assertEqual((state.video_volume, state.voice_volume), (20.0, 80.0))
        mixer.set_muted(True)
        state = mixer.snapshot()
        self.assertEqual((state.video_volume, state.voice_volume), (0.0, 0.0))
        mixer.set_owner("sched")
        self.assertEqual(mixer.snapshot().owner, "sched")
        self.assertEqual(mixer.snapshot().version, 4)

    def test_values_are_clamped_and_identical_sets_do_not_bump_version(self):
        mixer = pe.VolumeMixer(user_volume=500)
        self.assertEqual(mixer.snapshot().video_volume, 130.0)
        mixer.set_user_volume(130)
        mixer.set_duck_gain(-2)
        self.assertEqual(mixer.snapshot().video_volume, 0.0)
        version = mixer.snapshot().version
        mixer.set_duck_gain(0)
        self.assertEqual(mixer.snapshot().version, version)
        with self.assertRaises(ValueError):
            mixer.set_owner("other")


class OptionBuilderTests(unittest.TestCase):
    def test_linux_profiles_and_common_video_options(self):
        egl = pe.build_mpv_options("video", sys_platform="linux", wid=123,
                                   vo_profile="x11egl")
        self.assertEqual(egl["wid"], "123")
        self.assertEqual(egl["vo"], "gpu")
        self.assertEqual(egl["gpu_context"], "x11egl")
        self.assertNotIn("gpu_api", egl)
        self.assertEqual(egl["ytdl"], "no")
        self.assertEqual(egl["audio_buffer"], "0.2")
        vk = pe.build_mpv_options("video", sys_platform="linux", wid=1,
                                  vo_profile="x11vk")
        self.assertEqual((vk["gpu_api"], vk["gpu_context"]), ("vulkan", "x11vk"))
        sw = pe.build_mpv_options("video", sys_platform="linux", wid=1,
                                  vo_profile="x11sw")
        self.assertEqual(sw["vo"], "x11")
        self.assertNotIn("gpu_context", sw)
        self.assertNotIn("d3d11_warp", sw)
        self.assertNotIn("x11glx", pe.VO_PROFILES["linux"])

    def test_windows_wid_is_unsigned_and_d3d_options_are_scoped(self):
        options = pe.build_mpv_options("video", sys_platform="win32", wid=-1,
                                       vo_profile="d3d11-warp")
        self.assertEqual(options["wid"], str(0xFFFFFFFF))
        self.assertEqual(options["gpu_api"], "d3d11")
        self.assertEqual(options["d3d11_warp"], "yes")
        auto = pe.build_mpv_options("video", sys_platform="win32", wid=4,
                                    vo_profile="auto")
        self.assertNotIn("d3d11_warp", auto)

    def test_voice_options_have_no_window_or_network(self):
        options = pe.build_mpv_options("voice", sys_platform="linux", wid=None,
                                       vo_profile="x11egl")
        self.assertEqual(options["vid"], "no")
        self.assertEqual(options["force_window"], "no")
        self.assertEqual(options["ytdl"], "no")
        self.assertEqual(options["cache"], "no")
        self.assertNotIn("wid", options)

    def test_invalid_kind_profile_or_missing_wid_is_rejected(self):
        with self.assertRaises(ValueError):
            pe.build_mpv_options("other", sys_platform="linux", wid=1, vo_profile="x11egl")
        with self.assertRaises(ValueError):
            pe.build_mpv_options("video", sys_platform="linux", wid=1, vo_profile="bad")
        with self.assertRaises(ValueError):
            pe.build_mpv_options("video", sys_platform="linux", wid=None,
                                 vo_profile="x11egl")

    def test_profile_fallback_skips_unaccepted_entries(self):
        self.assertEqual(pe.next_vo_profile("linux", "x11egl", ("x11sw",)), "x11sw")
        self.assertIsNone(pe.next_vo_profile("linux", "x11sw", ("x11egl", "x11sw")))
        self.assertEqual(pe.next_vo_profile("win32", "missing", ("d3d11-warp",)),
                         "d3d11-warp")

    def test_vo_failure_uses_logs_or_five_second_video_timeout(self):
        self.assertTrue(pe.detect_vo_failure(
            ["vo/gpu: Failed initializing any suitable GPU context"],
            video_params_seen=False, has_video_track=True, seconds_since_loaded=0.1))
        self.assertTrue(pe.detect_vo_failure(
            ["Error opening/initializing the selected video_out (--vo) device."],
            video_params_seen=False, has_video_track=True, seconds_since_loaded=0.1))
        self.assertFalse(pe.detect_vo_failure([], video_params_seen=False,
                                              has_video_track=True,
                                              seconds_since_loaded=4.99))
        self.assertTrue(pe.detect_vo_failure([], video_params_seen=False,
                                             has_video_track=True,
                                             seconds_since_loaded=5.0))
        self.assertFalse(pe.detect_vo_failure([], video_params_seen=True,
                                              has_video_track=True,
                                              seconds_since_loaded=9.0))
        self.assertFalse(pe.detect_vo_failure([], video_params_seen=False,
                                              has_video_track=False,
                                              seconds_since_loaded=9.0))

    def test_stream_options_and_duck_helpers(self):
        self.assertEqual(pe.stream_session_options(30), {
            "rebase_start_time": "no",
            "cache": "yes",
            "force_seekable": "yes",
            "demuxer_max_bytes": str(256 * 1024 * 1024),
            "demuxer_max_back_bytes": str(32 * 1024 * 1024),
            "cache_pause": "yes",
            "cache_pause_wait": "1",
        })
        self.assertEqual(pe.duck_channel_for((0, 36)), "volume")
        self.assertEqual(pe.duck_channel_for((0, 37)), "af")
        self.assertEqual(pe.duck_channel_for(None), "volume")
        self.assertEqual(pe.af_duck_command(0.257),
                         ["af-command", "vtduck", "volume", "0.257", "volume"])


class InMemoryBackendTests(unittest.TestCase):
    def test_records_non_blocking_player_operations(self):
        backend = pe.InMemoryBackend(mpv_version=(0, 41))
        backend.load("/a.mp4", paused=True, start=2.0, options={"cache": "yes"})
        backend.set_pause(False)
        backend.seek(3.0, "relative")
        backend.add_external_audio("/a.wav", "Original")
        backend.select_audio(4)
        backend.add_subtitles("/a.srt", "Translated")
        backend.set_subtitles_visible(False)
        backend.screenshot("/shot.png")
        self.assertEqual([call[0] for call in backend.calls], [
            "load", "set_pause", "seek", "add_external_audio", "select_audio",
            "add_subtitles", "set_subtitles_visible", "screenshot",
        ])
        self.assertEqual(backend.calls[0][1], "/a.mp4")
        self.assertEqual(backend.calls[2], ("seek", 3.0, "relative"))

    def test_mix_realtime_operations_and_termination(self):
        mixer = pe.VolumeMixer(user_volume=80)
        backend = pe.InMemoryBackend(mixer=mixer)
        backend.apply_mix()
        backend.rt.set_overlay("line")
        backend.rt.set_speed(1.03)
        backend.rt.set_pause(True)
        backend.rt.set_duck(0.2)
        self.assertTrue(backend.set_af("@vtduck:lavfi=[volume=volume=1.0]"))
        self.assertTrue(backend.terminate(1.0))
        self.assertFalse(backend.terminate(1.0))
        self.assertEqual(backend.calls[-1][0], "terminate")


class _FakeX11Function:
    def __init__(self, initial):
        self.current = initial
        self.calls = []

    def __call__(self, handler):
        previous = self.current
        self.current = handler
        self.calls.append(handler)
        return previous


class X11ErrorGuardTests(unittest.TestCase):
    def test_capture_reads_and_restores_tk_handler_then_restore_sets_it(self):
        setter = _FakeX11Function(1234)
        guard = pe.X11ErrorGuard(load_libx11=lambda: SimpleNamespace(XSetErrorHandler=setter))
        guard.capture()
        self.assertTrue(guard.captured)
        self.assertEqual(setter.calls, [None, 1234])
        setter.current = None
        guard.restore()
        self.assertEqual(setter.current, 1234)

    def test_missing_library_or_null_handler_is_a_safe_noop(self):
        missing = pe.X11ErrorGuard(load_libx11=lambda: (_ for _ in ()).throw(OSError()))
        missing.capture()
        missing.restore()
        self.assertFalse(missing.captured)
        setter = _FakeX11Function(None)
        null = pe.X11ErrorGuard(load_libx11=lambda: SimpleNamespace(XSetErrorHandler=setter))
        null.capture()
        null.restore()
        self.assertFalse(null.captured)


class _FakeMpv:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.actions = []
        self.options = {}
        self.observers = {}
        self.event_callback = None
        self.bindings = {}
        self.command_events = []
        self.terminated = False
        self.terminate_gate = None
        self.mpv_version = "mpv 0.41.0"
        self._event_thread = object()

    def __getitem__(self, name):
        return self.options.get(name, f"default-{name}")

    def __setitem__(self, name, value):
        self.options[name] = value
        self.actions.append(("set", name, value))

    def command(self, *args):
        self.actions.append(("command", *args))
        event = threading.Event()
        event.set()
        self.command_events.append(event)

    def command_async(self, *args, callback=None):
        self.actions.append(("command_async", *args))
        if callback is not None:
            callback(None, None)

    def observe_property(self, name, callback):
        self.observers[name] = callback

    def register_event_callback(self, callback):
        self.event_callback = callback

    def register_key_binding(self, name, callback, mode="force"):
        self.bindings[name] = callback

    def terminate(self):
        if self.terminate_gate is not None:
            self.terminate_gate.wait()
        self.terminated = True


class _FakeMpvModule:
    class MpvEventID:
        FILE_LOADED = 8
        END_FILE = 7
        PLAYBACK_RESTART = 21

    def __init__(self):
        self.instances = []

    def MPV(self, **kwargs):
        instance = _FakeMpv(**kwargs)
        self.instances.append(instance)
        return instance


def _wait_for(predicate, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("timed out waiting for fake mpv command")


class MpvBackendTests(unittest.TestCase):
    def make_backend(self):
        module = _FakeMpvModule()
        bridge = pe.EventBridge()
        mixer = pe.VolumeMixer(user_volume=72)
        backend = pe.create_video_backend(
            wid=55, bridge=bridge, mixer=mixer, vo_profile="x11sw",
            mpv_module=module, sys_platform="linux", log=lambda *_args: None,
        )
        return backend, module.instances[0], bridge

    def test_factory_builds_player_and_registers_observers_events_and_mouse(self):
        backend, player, _bridge = self.make_backend()
        self.assertEqual(player.kwargs["wid"], "55")
        self.assertEqual(player.kwargs["vo"], "x11")
        self.assertEqual(backend.mpv_version, (0, 41))
        self.assertEqual(set(player.observers), set(pe.EventBridge.LATEST))
        self.assertIsNotNone(player.event_callback)
        self.assertEqual(set(player.bindings), {
            "MBTN_LEFT", "MBTN_LEFT_DBL", "WHEEL_UP", "WHEEL_DOWN",
        })
        self.assertTrue(backend.terminate(1.0))

    def test_load_writes_properties_before_raw_loadfile_and_restores_next_time(self):
        backend, player, _bridge = self.make_backend()
        backend.load("/one.mp4", paused=True, start=3.5,
                     options={"cache": "yes", "force_seekable": "yes"})
        _wait_for(lambda: ("command", "loadfile", "/one.mp4", "replace") in player.actions)
        load_index = player.actions.index(("command", "loadfile", "/one.mp4", "replace"))
        self.assertIn(("set", "pause", "yes"), player.actions[:load_index])
        self.assertIn(("set", "start", 3.5), player.actions[:load_index])
        self.assertIn(("set", "cache", "yes"), player.actions[:load_index])
        self.assertFalse(any(action[1] == "loadfile" and len(action) > 4
                             for action in player.actions if action[0] == "command"))

        backend.load("/two.mp4", paused=False)
        _wait_for(lambda: ("command", "loadfile", "/two.mp4", "replace") in player.actions)
        second = player.actions.index(("command", "loadfile", "/two.mp4", "replace"))
        between = player.actions[load_index + 1:second]
        self.assertIn(("set", "cache", "default-cache"), between)
        self.assertIn(("set", "force-seekable", "default-force-seekable"), between)
        self.assertIn(("set", "start", "default-start"), between)
        self.assertTrue(backend.terminate(1.0))

    def test_commands_mix_snapshot_callbacks_and_bridge_callbacks_do_not_raise(self):
        backend, player, bridge = self.make_backend()
        backend.set_pause(False)
        backend.seek(4, "relative")
        backend.apply_mix()
        backend.add_external_audio("/original.wav", "Original")
        backend.select_audio(3)
        backend.add_subtitles("/translated.srt", "Translated")
        backend.reload_subtitles()
        backend.set_subtitles_visible(False)
        backend.screenshot("/shot.png")
        _wait_for(lambda: ("command_async", "screenshot-to-file", "/shot.png", "video")
                  in player.actions)

        marker = object()
        player.observers["time-pos"]("time-pos", 9.25)
        player.observers["time-pos"](None, marker)
        player.bindings["MBTN_LEFT"]("um-", None, None, None, None)
        player.event_callback(SimpleNamespace(
            event_id=SimpleNamespace(value=_FakeMpvModule.MpvEventID.FILE_LOADED),
        ))
        player.event_callback(SimpleNamespace(
            event_id=SimpleNamespace(value=_FakeMpvModule.MpvEventID.END_FILE),
            data=SimpleNamespace(reason=4),
        ))
        player.event_callback(SimpleNamespace(
            event_id=SimpleNamespace(value=_FakeMpvModule.MpvEventID.PLAYBACK_RESTART),
        ))
        player.event_callback(SimpleNamespace(event_id=SimpleNamespace(value=999)))
        snapshot = bridge.drain()
        self.assertIs(snapshot.changed["time-pos"][0], marker)
        self.assertIn(("mouse", ("MBTN_LEFT", "um-")),
                      [(event.kind, event.payload) for event in snapshot.events])
        self.assertIn("snapshot-saved", [event.kind for event in snapshot.events])
        self.assertIn(("end-file", {"reason": "error"}),
                      [(event.kind, event.payload) for event in snapshot.events])
        self.assertTrue(backend.terminate(1.0))

    def test_terminate_is_refused_on_mpv_event_thread_and_is_idempotent(self):
        backend, player, bridge = self.make_backend()
        player._event_thread = threading.current_thread()
        self.assertFalse(backend.terminate(0.1))
        self.assertIn("terminate-refused", [event.kind for event in bridge.drain().events])
        player._event_thread = object()
        self.assertTrue(backend.terminate(1.0))
        self.assertTrue(player.terminated)
        self.assertFalse(backend.terminate(1.0))

    def test_terminate_timeout_is_a_single_total_deadline_and_can_be_rejoined(self):
        backend, player, _bridge = self.make_backend()
        player.terminate_gate = threading.Event()
        started = time.monotonic()
        self.assertFalse(backend.terminate(0.03))
        self.assertLess(time.monotonic() - started, 0.08)
        player.terminate_gate.set()
        self.assertTrue(backend.terminate(1.0))


class ExtraLatestTests(unittest.TestCase):
    def test_extra_values_are_kept_apart_from_the_latest_set(self):
        bridge = pe.EventBridge()
        bridge.set_latest("time-pos", 5.0, 10.0)
        bridge.extra_latest("voice-time-pos", 0.4, 10.0)
        bridge.extra_latest("voice-time-pos", 0.9, 11.0)
        self.assertEqual(bridge.extra("voice-time-pos"), (0.9, 11.0))
        self.assertIsNone(bridge.extra("missing"))
        # the video time-pos is untouched by the voice value
        self.assertEqual(bridge.latest("time-pos"), (5.0, 10.0))
        self.assertNotIn("voice-time-pos", bridge.drain().changed)

    def test_extra_latest_is_a_no_op_after_close(self):
        bridge = pe.EventBridge()
        bridge.close()
        bridge.extra_latest("voice-time-pos", 1.0, 1.0)
        self.assertIsNone(bridge.extra("voice-time-pos"))


class DuckAfTests(unittest.TestCase):
    def test_issues_the_af_command_and_reports_success(self):
        player = _FakeMpv()
        self.assertTrue(pe.duck_af(player, 0.3))
        self.assertEqual(player.actions[-1],
                         ("command", "af-command", "vtduck", "volume", "0.300", "volume"))

    def test_none_player_is_false(self):
        self.assertFalse(pe.duck_af(None, 0.3))

    def test_failure_is_reported_and_false(self):
        class _Boom(_FakeMpv):
            def command(self, *args):
                raise RuntimeError("no filter")
        seen = []
        self.assertFalse(pe.duck_af(_Boom(), 0.5, on_error=seen.append))
        self.assertEqual(len(seen), 1)


class MpvVoiceBackendTests(unittest.TestCase):
    def make_voice(self):
        module = _FakeMpvModule()
        bridge = pe.EventBridge()
        voice = pe.create_voice_backend(
            bridge=bridge, mpv_module=module, sys_platform="linux",
            log=lambda *_args: None,
        )
        return voice, module.instances[0], bridge

    def test_factory_builds_a_videoless_instance_with_observers(self):
        voice, player, _bridge = self.make_voice()
        self.assertEqual(player.kwargs["vid"], "no")
        self.assertEqual(player.kwargs["force_window"], "no")
        self.assertIn("time-pos", player.observers)
        self.assertIsNotNone(player.event_callback)
        self.assertEqual(voice.mpv_version, (0, 41))
        self.assertTrue(voice.terminate(1.0))

    def test_preload_then_start_command_order(self):
        voice, player, _bridge = self.make_voice()
        voice.preload("/clip.mp3", skip_s=0.2)
        load = player.actions.index(("command", "loadfile", "/clip.mp3", "replace"))
        self.assertIn(("command", "set", "pause", "yes"), player.actions[:load])
        self.assertIn(("command", "set", "start", 0.2), player.actions[:load])
        voice.start(1.1)
        speed = player.actions.index(("command", "set", "speed", 1.1))
        unpause = player.actions.index(("command", "set", "pause", "no"))
        self.assertGreater(speed, load)
        self.assertGreater(unpause, speed)

    def test_callbacks_feed_bridge_and_never_raise(self):
        voice, player, bridge = self.make_voice()
        player.observers["time-pos"]("time-pos", 0.75)
        player.event_callback(SimpleNamespace(
            event_id=SimpleNamespace(value=_FakeMpvModule.MpvEventID.END_FILE),
            data=SimpleNamespace(reason=0),
        ))
        player.event_callback(SimpleNamespace(event_id=SimpleNamespace(value=999)))
        self.assertEqual(bridge.extra("voice-time-pos")[0], 0.75)
        self.assertIn("voice-end-file", [event.kind for event in bridge.drain().events])
        self.assertTrue(voice.terminate(1.0))

    def test_transport_helpers_map_to_commands(self):
        voice, player, _bridge = self.make_voice()
        voice.set_pause(True)
        voice.set_volume(80)
        voice.set_speed(1.25)
        voice.stop()
        self.assertIn(("command", "set", "pause", "yes"), player.actions)
        self.assertIn(("command", "set", "volume", 80.0), player.actions)
        self.assertIn(("command", "set", "speed", 1.25), player.actions)
        self.assertIn(("command", "stop"), player.actions)
        self.assertTrue(voice.terminate(1.0))

    def test_terminate_refused_on_event_thread_and_idempotent(self):
        voice, player, bridge = self.make_voice()
        player._event_thread = threading.current_thread()
        self.assertFalse(voice.terminate(0.1))
        self.assertIn("voice-terminate-refused",
                      [event.kind for event in bridge.drain().events])
        player._event_thread = object()
        self.assertTrue(voice.terminate(1.0))
        self.assertTrue(player.terminated)
        self.assertFalse(voice.terminate(1.0))

    def test_ops_are_no_ops_after_terminate(self):
        voice, player, _bridge = self.make_voice()
        self.assertTrue(voice.terminate(1.0))
        before = list(player.actions)
        voice.preload("/x.mp3")
        voice.start(1.0)
        voice.set_pause(False)
        self.assertEqual(player.actions, before)


class InMemoryVoiceTests(unittest.TestCase):
    def test_records_every_operation_in_order(self):
        voice = pe.InMemoryVoice(mpv_version=(0, 41))
        voice.preload("/clip.mp3", skip_s=0.15)
        voice.start(1.2)
        voice.set_pause(True)
        voice.set_volume(90)
        voice.set_speed(1.3)
        voice.stop()
        self.assertEqual(voice.calls, [
            ("preload", "/clip.mp3", 0.15),
            ("start", 1.2),
            ("set_pause", True),
            ("set_volume", 90.0),
            ("set_speed", 1.3),
            ("stop",),
        ])
        self.assertTrue(voice.terminate(0.5))
        self.assertFalse(voice.terminate(0.5))


if __name__ == "__main__":
    unittest.main()
