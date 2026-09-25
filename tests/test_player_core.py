"""player_core pure helpers (spec 2.2, 2.3 reflow, 3.7 keys and mouse)."""

import unittest
from datetime import datetime
from pathlib import Path

from videotranslator import player_core as pc
from videotranslator.player_core import MediaItem


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


if __name__ == "__main__":
    unittest.main()
