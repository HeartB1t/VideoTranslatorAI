"""Pure player engine primitives (spec 2.2, 3.1 and 4.13)."""

import threading
import unittest

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


if __name__ == "__main__":
    unittest.main()
