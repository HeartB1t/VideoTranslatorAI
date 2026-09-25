"""player_core pure helpers (spec 2.2, 2.3 reflow, 3.7 keys and mouse)."""

import unittest
import tempfile
from datetime import datetime
from pathlib import Path

from videotranslator import player_core as pc
from videotranslator.player_engine import BridgeEvent, BridgeSnapshot, InMemoryBackend
from videotranslator.player_core import MediaItem
from videotranslator.player_settings import PlayerSettings


class ClockAndSeekMathsTests(unittest.TestCase):
    def test_format_clock(self):
        self.assertEqual(pc.format_clock(None, hours=False), "--:--")
        self.assertEqual(pc.format_clock(None, hours=True), "--:--:--")
        self.assertEqual(pc.format_clock(0, hours=False), "00:00")
        self.assertEqual(pc.format_clock(65.9, hours=False), "01:05")
        self.assertEqual(pc.format_clock(3725, hours=True), "1:02:05")
        self.assertEqual(pc.format_clock(-3, hours=False), "00:00")
        self.assertEqual(pc.format_clock(3725, hours=False), "62:05")

    def test_x_and_seconds_are_inverse_and_clamped(self):
        self.assertEqual(pc.x_to_seconds(50, 100, 0, 200), 100)
        self.assertEqual(pc.x_to_seconds(-5, 100, 10, 110), 10)
        self.assertEqual(pc.x_to_seconds(500, 100, 10, 110), 110)
        self.assertEqual(pc.x_to_seconds(10, 0, 10, 110), 10)
        self.assertEqual(pc.seconds_to_x(100, 100, 0, 200), 50)
        self.assertEqual(pc.seconds_to_x(-1, 100, 0, 200), 0)
        self.assertEqual(pc.seconds_to_x(999, 100, 0, 200), 100)
        self.assertEqual(pc.seconds_to_x(5, 100, 10, 10), 0)
        for x in (0, 17, 63, 100):
            self.assertAlmostEqual(pc.seconds_to_x(pc.x_to_seconds(x, 100, 3, 91), 100, 3, 91), x)


class AudioTrackTests(unittest.TestCase):
    def test_titles_win(self):
        tracks = [{"id": 1, "type": "audio", "title": "Original"},
                  {"id": 2, "type": "audio", "title": "Dubbed"},
                  {"id": 1, "type": "video"}]
        self.assertEqual(pc.pick_audio_track_ids(tracks), (2, 1))

    def test_external_track_is_the_original(self):
        tracks = [{"id": 1, "type": "audio"}, {"id": 2, "type": "audio", "external": True}]
        self.assertEqual(pc.pick_audio_track_ids(tracks), (1, 2))

    def test_order_when_nothing_else_tells(self):
        tracks = [{"id": 3, "type": "audio"}, {"id": 4, "type": "audio"}]
        self.assertEqual(pc.pick_audio_track_ids(tracks), (3, 4))

    def test_single_or_no_audio_track(self):
        self.assertEqual(pc.pick_audio_track_ids([{"id": 1, "type": "audio"}]), (1, None))
        self.assertEqual(pc.pick_audio_track_ids([]), (None, None))
        self.assertEqual(pc.pick_audio_track_ids(None), (None, None))


class SnapshotPathTests(unittest.TestCase):
    NOW = datetime(2026, 9, 25, 21, 30, 0)

    def test_name_and_collisions(self):
        taken = set()
        first = pc.snapshot_path(Path("/v"), "My clip.mp4", 3725.4, self.NOW,
                                 exists=lambda p: str(p) in taken)
        self.assertEqual(first, Path("/v/My clip_01-02-05.png"))
        taken.add(str(first))
        second = pc.snapshot_path(Path("/v"), "My clip.mp4", 3725.4, self.NOW,
                                  exists=lambda p: str(p) in taken)
        self.assertEqual(second, Path("/v/My clip_01-02-05_2.png"))
        taken.add(str(second))
        self.assertEqual(pc.snapshot_path(Path("/v"), "My clip.mp4", 3725.4, self.NOW,
                                          exists=lambda p: str(p) in taken),
                         Path("/v/My clip_01-02-05_3.png"))

    def test_unsafe_characters_and_missing_title(self):
        path = pc.snapshot_path(Path("/v"), 'a<b>:c"d/e\\f|g?h*.mkv', 0, self.NOW,
                                exists=lambda p: False)
        self.assertEqual(path.name, "a_b__c_d_e_f_g_h__00-00-00.png")
        self.assertEqual(pc.snapshot_path(Path("/v"), "", 12, self.NOW, exists=lambda p: False),
                         Path("/v/snapshot_20260925-213000_00-00-12.png"))


class ReflowTests(unittest.TestCase):
    ALL = frozenset({"previous", "back", "stop", "play_pause", "forward", "next", "snapshot",
                     "open_folder", "volume", "fullscreen", "audio", "subtitles", "playlist",
                     "live"})

    def test_thresholds_at_360_460_700(self):
        self.assertEqual(pc.controls_visible(700, 1.0), self.ALL)
        self.assertEqual(pc.controls_visible(460, 1.0), self.ALL)
        self.assertEqual(pc.controls_visible(439, 1.0), self.ALL - {"back", "forward"})
        self.assertEqual(pc.controls_visible(360, 1.0),
                         self.ALL - {"back", "forward", "snapshot", "open_folder"})

    def test_thresholds_follow_the_text_size(self):
        self.assertEqual(pc.controls_visible(500, 1.25), self.ALL - {"back", "forward"})


class KeyTests(unittest.TestCase):
    def test_every_action_has_a_key(self):
        self.assertEqual(pc.PLAYER_KEYS, {
            "space": "play_pause", "Left": "back_10", "Right": "forward_10",
            "Up": "volume_up", "Down": "volume_down", "m": "mute", "f": "fullscreen",
            "Escape": "exit_fullscreen", "s": "snapshot", "o": "open_folder",
            "n": "next", "p": "previous"})

    def test_interactive_widgets_keep_their_keys_outside_the_player(self):
        interactive = ("Entry", "TEntry", "Text", "Listbox", "TCombobox", "Spinbox",
                       "TSpinbox", "Treeview", "Button", "TButton", "Checkbutton",
                       "TCheckbutton", "Radiobutton", "TRadiobutton", "Scale", "TScale",
                       "Menubutton", "TMenubutton")
        for cls in interactive:
            with self.subTest(cls=cls):
                self.assertFalse(pc.handles_player_key(cls, "space", focus_in_player=False))
                self.assertTrue(pc.handles_player_key(cls, "space", focus_in_player=True))

    def test_passive_widgets_and_no_focus_reach_the_player(self):
        for cls in (None, "", "Tk", "Toplevel", "Frame", "Label", "Canvas", "TFrame", "TLabel"):
            with self.subTest(cls=cls):
                self.assertTrue(pc.handles_player_key(cls, "space", focus_in_player=False))

    def test_unmapped_keys_are_never_handled(self):
        self.assertFalse(pc.handles_player_key("Frame", "x", focus_in_player=True))


class MouseTests(unittest.TestCase):
    def _actions(self, events):
        return [a for a in (pc.mouse_action(n, s) for n, s in events) if a]

    def test_click_toggles_pause_once_on_both_versions(self):
        self.assertEqual(self._actions([("MBTN_LEFT", "dm-"), ("MBTN_LEFT", "um-")]),
                         ["toggle_pause"])
        self.assertEqual(self._actions([("MBTN_LEFT", "dm"), ("MBTN_LEFT", "um")]),
                         ["toggle_pause"])

    def test_double_click_toggles_pause_twice_then_fullscreen(self):
        trace = [("MBTN_LEFT", "dm-"), ("MBTN_LEFT", "um-"), ("MBTN_LEFT", "dm-"),
                 ("MBTN_LEFT_DBL", "p--"), ("MBTN_LEFT", "um-")]
        self.assertEqual(self._actions(trace),
                         ["toggle_pause", "toggle_fullscreen", "toggle_pause"])
        trace = [("MBTN_LEFT", "dm"), ("MBTN_LEFT", "um"), ("MBTN_LEFT", "dm"),
                 ("MBTN_LEFT_DBL", "p-"), ("MBTN_LEFT", "um")]
        self.assertEqual(self._actions(trace),
                         ["toggle_pause", "toggle_fullscreen", "toggle_pause"])

    def test_a_wheel_notch_is_one_volume_step(self):
        for trace in ([("WHEEL_UP", "dm-"), ("WHEEL_UP", "um-")],
                      [("WHEEL_UP", "dm"), ("WHEEL_UP", "um")],
                      [("WHEEL_UP", "pm-")], [("WHEEL_UP", "pm")]):
            with self.subTest(trace=trace):
                self.assertEqual(self._actions(trace), ["volume_up"])
        self.assertEqual(self._actions([("WHEEL_DOWN", "dm-"), ("WHEEL_DOWN", "um-")]),
                         ["volume_down"])

    def test_unknown_input_is_ignored(self):
        self.assertIsNone(pc.mouse_action("MBTN_RIGHT", "dm-"))
        self.assertIsNone(pc.mouse_action("MBTN_LEFT", ""))


class PlaylistGroupTests(unittest.TestCase):
    def test_results_are_disabled_while_a_job_runs(self):
        src = [MediaItem("/a.mp4", "source", "a")]
        res = [MediaItem("/a_it.mp4", "dubbed", "a_it")]
        self.assertEqual(pc.playlist_groups(src, res, job_running=False),
                         [("player_playlist_sources", src, True),
                          ("player_playlist_results", res, True)])
        self.assertEqual(pc.playlist_groups(src, res, job_running=True),
                         [("player_playlist_sources", src, True),
                          ("player_playlist_results", res, False)])


class PlayerControllerTests(unittest.TestCase):
    def setUp(self):
        self.backend = InMemoryBackend()
        self.saved = []
        self.states = []
        settings = PlayerSettings(
            volume=80,
            muted=False,
            audio="dubbed",
            subs_visible=True,
            autoload_result=True,
            vo_profile=None,
            keep_original_audio=True,
        )
        self.controller = pc.PlayerController(
            self.backend,
            settings,
            on_change=self.states.append,
            save=self.saved.append,
        )
        self.backend.calls.clear()
        self.source = MediaItem("/v/source.mp4", "source", "source.mp4")
        self.result = MediaItem("/v/result.mp4", "dubbed", "result.mp4",
                                source_path="/v/source.mp4", srt_path="/v/result.srt")

    def test_load_sets_state_and_calls_backend(self):
        self.controller.load(self.source, paused=True, start=2.5)
        self.assertEqual(self.backend.calls, [("load", self.source.path, True, 2.5, {})])
        self.assertEqual(self.controller.state.status, "loading")
        self.assertEqual(self.controller.state.item, self.source)
        self.assertEqual(self.controller.state.position, 2.5)
        self.assertTrue(self.states)

    def test_attach_backend_replays_only_the_last_pending_load(self):
        settings = PlayerSettings(100, False, "dubbed", True, True, None, True)
        states = []
        controller = pc.PlayerController(None, settings, on_change=states.append,
                                         save=lambda _cfg: None)
        controller.load(self.source, paused=True, start=0)
        controller.load(self.result, paused=False, start=3)
        backend = InMemoryBackend()
        controller.attach_backend(backend)
        load_calls = [call for call in backend.calls if call[0] == "load"]
        self.assertEqual(load_calls, [("load", self.result.path, False, 3.0, {})])
        self.assertEqual(controller.state.item, self.result)

    def test_detach_backend_queues_the_current_item_for_recreation(self):
        self.controller.load(self.source, paused=False, start=4.0)
        self.controller.detach_backend()
        replacement = InMemoryBackend()
        self.controller.attach_backend(replacement)
        self.assertIn(("load", self.source.path, False, 4.0, {}), replacement.calls)

    def test_playlist_navigation_stops_at_the_ends(self):
        third = MediaItem("/v/third.mp4", "source", "third.mp4")
        self.controller.set_playlist([self.source, self.result, third], index=1)
        self.controller.load(self.result)
        self.backend.calls.clear()
        self.controller.next()
        self.controller.next()
        self.controller.previous()
        self.assertEqual([call[1] for call in self.backend.calls if call[0] == "load"],
                         [third.path, self.result.path])

    def test_play_pause_stop_and_seek_intents(self):
        self.controller.load(self.source, paused=True)
        self.backend.calls.clear()
        self.controller.play_pause()
        self.controller.play_pause()
        self.controller.seek(12.0)
        self.controller.seek(13.0, dragging=True)
        self.controller.seek_relative(-10)
        self.controller.stop()
        self.assertEqual(self.backend.calls, [
            ("set_pause", False),
            ("set_pause", True),
            ("seek", 12.0, "exact"),
            ("seek", 13.0, "keyframes"),
            ("seek", -10.0, "relative"),
            ("stop",),
        ])
        self.assertEqual(self.controller.state.status, "idle")
        self.assertIsNone(self.controller.state.item)

    def test_volume_and_mute_update_mixer_state_and_config(self):
        self.controller.set_volume(200)
        self.controller.toggle_mute()
        self.assertEqual(self.controller.state.volume, 130)
        self.assertTrue(self.controller.state.muted)
        self.assertEqual(self.saved, [{"player_volume": 130}, {"player_muted": True}])
        mix_calls = [call for call in self.backend.calls if call[0] == "apply_mix"]
        self.assertEqual(len(mix_calls), 2)
        self.assertEqual(mix_calls[-1][1].voice_volume, 0.0)

    def test_file_loaded_adds_missing_external_audio_and_subtitles(self):
        self.controller.load(self.result)
        self.backend.calls.clear()
        snapshot = BridgeSnapshot(
            changed={
                "track-list": ([{"id": 1, "type": "audio", "title": "Dubbed"}], 1.0),
                "duration": (20.0, 1.0),
                "pause": (True, 1.0),
            },
            events=(BridgeEvent("file-loaded"),),
        )
        self.controller.apply_events(snapshot, 4.0)
        self.assertIn(("add_external_audio", self.result.source_path, "Original"),
                      self.backend.calls)
        self.assertIn(("add_subtitles", self.result.srt_path, "Translated"),
                      self.backend.calls)
        self.assertEqual(self.controller.state.duration, 20.0)
        self.assertEqual(self.controller.state.position, 4.0)
        self.assertEqual(self.controller.state.status, "paused")
        self.assertTrue(self.controller.state.subs_available)

    def test_audio_and_subtitle_selection_follow_track_events(self):
        self.controller.load(self.result)
        self.controller.apply_events(BridgeSnapshot(changed={
            "track-list": ([
                {"id": 3, "type": "audio", "title": "Dubbed"},
                {"id": 4, "type": "audio", "title": "Original"},
            ], 1.0),
        }, events=()), 0.0)
        self.backend.calls.clear()
        self.assertTrue(self.controller.select_audio("original"))
        self.assertFalse(self.controller.select_audio("missing"))
        self.controller.set_subtitles_visible(False)
        self.assertEqual(self.backend.calls, [
            ("select_audio", 4),
            ("set_subtitles_visible", False),
        ])
        self.assertEqual(self.saved, [
            {"player_audio": "original"},
            {"player_subs_visible": False},
        ])

    def test_unrelated_events_do_not_restore_an_old_audio_preference(self):
        settings = PlayerSettings(100, False, "original", True, True, None, True)
        backend = InMemoryBackend()
        controller = pc.PlayerController(backend, settings, on_change=lambda _state: None,
                                         save=lambda _cfg: None)
        controller.load(self.result)
        controller.apply_events(BridgeSnapshot(changed={
            "track-list": ([
                {"id": 3, "type": "audio", "title": "Dubbed"},
                {"id": 4, "type": "audio", "title": "Original"},
            ], 1.0),
        }, events=()), 0.0)
        self.assertEqual(controller.state.audio, "original")
        controller.select_audio("dubbed")
        backend.calls.clear()
        controller.apply_events(BridgeSnapshot(changed={"duration": (20.0, 2.0)},
                                               events=()), 1.0)
        self.assertEqual(controller.state.audio, "dubbed")
        self.assertNotIn(("select_audio", 4), backend.calls)

    def test_show_segments_rewrites_preview_and_snapshot_uses_unique_path(self):
        self.controller.load(self.result)
        self.backend.calls.clear()
        with tempfile.TemporaryDirectory() as tmp:
            srt = Path(tmp) / "preview.srt"
            self.controller.show_segments_as_subtitles(
                [{"start": 0, "end": 1, "text_tgt": "ciao"}], srt)
            self.assertIn("ciao", srt.read_text(encoding="utf-8"))
            first = Path(tmp) / "result_00-00-00.png"
            first.write_bytes(b"taken")
            shot = self.controller.snapshot(Path(tmp), datetime(2026, 9, 25, 20, 0))
        self.assertTrue(str(shot).endswith("result_00-00-00_2.png"))
        self.assertEqual(self.backend.calls, [
            ("add_subtitles", str(srt), "Translated"),
            ("reload_subtitles",),
            ("set_subtitles_visible", True),
            ("screenshot", str(shot)),
        ])

    def test_remove_and_release_rules_only_stop_held_files(self):
        self.controller.set_playlist([self.source, self.result], index=0)
        self.controller.load(self.source)
        self.backend.calls.clear()
        self.controller.remove_items([self.source.path])
        self.assertEqual(self.backend.calls, [("stop",)])
        self.assertEqual(self.controller.playlist, (self.result,))

        self.controller.load(self.result)
        self.backend.calls.clear()
        self.assertTrue(self.controller.release_for_job())
        self.assertEqual(self.backend.calls, [("stop",)])

        self.controller.load(self.result)
        self.backend.calls.clear()
        self.assertTrue(self.controller.release(self.result.source_path))
        self.assertEqual(self.backend.calls, [("stop",)])
        self.assertFalse(self.controller.release("/other.mp4"))

    def test_result_removal_does_not_stop_a_loaded_result(self):
        self.controller.set_playlist([self.result], index=0)
        self.controller.load(self.result)
        self.backend.calls.clear()
        self.controller.remove_items([self.result.path])
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(self.controller.state.item, self.result)

    def test_is_released_accepts_raw_or_stamped_latest_values(self):
        self.assertTrue(self.controller.is_released({"idle-active": True}))
        self.assertTrue(self.controller.is_released({"idle-active": (True, 2.0)}))
        self.assertFalse(self.controller.is_released({"idle-active": (False, 2.0)}))
        self.assertFalse(self.controller.is_released({}))


if __name__ == "__main__":
    unittest.main()
