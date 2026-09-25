"""player_settings: flat player_* / live_* config keys, normalised (spec 2.5)."""

import unittest

from videotranslator.player_settings import (
    LiveSettings,
    PlayerSettings,
    normalize_live_settings,
    normalize_player_settings,
    settings_to_config,
)


class PlayerSettingsTests(unittest.TestCase):
    def test_defaults_for_an_empty_config(self):
        self.assertEqual(
            normalize_player_settings({}, sys_platform="linux"),
            PlayerSettings(volume=100, muted=False, audio="dubbed", subs_visible=True,
                           autoload_result=True, vo_profile=None, keep_original_audio=True))

    def test_valid_values_are_kept(self):
        cfg = {"player_volume": 130, "player_muted": True, "player_audio": "original",
               "player_subs_visible": False, "player_autoload_result": False,
               "player_vo_profile": "x11sw", "keep_original_audio": False}
        s = normalize_player_settings(cfg, sys_platform="linux")
        self.assertEqual((s.volume, s.muted, s.audio, s.subs_visible, s.autoload_result,
                          s.vo_profile, s.keep_original_audio),
                         (130, True, "original", False, False, "x11sw", False))

    def test_malformed_values_fall_back_to_defaults(self):
        cfg = {"player_volume": 131, "player_muted": "yes", "player_audio": "both",
               "player_subs_visible": 1, "player_autoload_result": None,
               "keep_original_audio": "false"}
        s = normalize_player_settings(cfg, sys_platform="linux")
        self.assertEqual((s.volume, s.muted, s.audio, s.subs_visible, s.autoload_result,
                          s.keep_original_audio), (100, False, "dubbed", True, True, True))
        for bad in (-1, True, 55.5, "80"):
            with self.subTest(volume=bad):
                self.assertEqual(normalize_player_settings(
                    {"player_volume": bad}, sys_platform="linux").volume, 100)

    def test_vo_profile_must_belong_to_the_platform(self):
        self.assertIsNone(normalize_player_settings(
            {"player_vo_profile": "d3d11-warp"}, sys_platform="linux").vo_profile)
        self.assertIsNone(normalize_player_settings(
            {"player_vo_profile": "x11glx"}, sys_platform="linux").vo_profile)
        self.assertEqual(normalize_player_settings(
            {"player_vo_profile": "d3d11-warp"}, sys_platform="win32").vo_profile, "d3d11-warp")

    def test_round_trip_through_the_flat_keys(self):
        s = PlayerSettings(volume=45, muted=True, audio="original", subs_visible=False,
                           autoload_result=False, vo_profile="x11vk", keep_original_audio=False)
        self.assertEqual(normalize_player_settings(settings_to_config(s), sys_platform="linux"), s)

    def test_an_unset_vo_profile_is_not_written(self):
        cfg = settings_to_config(normalize_player_settings({}, sys_platform="linux"))
        self.assertNotIn("player_vo_profile", cfg)
        self.assertEqual(cfg["player_volume"], 100)


class LiveSettingsTests(unittest.TestCase):
    def test_defaults_for_an_empty_config(self):
        self.assertEqual(normalize_live_settings({}), LiveSettings(
            sync_mode="delayed", delay_s=None, file_ahead_s=None, delay_auto=True,
            engine="marian", dub_enabled=True, subs_enabled=True, duck_level=0.3,
            max_height=720, buffer_max_mb=1024))

    def test_valid_values_are_kept(self):
        cfg = {"live_sync_mode": "live", "live_delay_s": 12.5, "live_file_ahead_s": 4,
               "live_delay_auto": False, "live_engine": "ollama", "live_dub_enabled": False,
               "live_subs_enabled": False, "live_duck_level": 0.6, "live_max_height": 1080,
               "live_buffer_max_mb": 8192}
        s = normalize_live_settings(cfg)
        self.assertEqual((s.sync_mode, s.delay_s, s.file_ahead_s, s.delay_auto, s.engine,
                          s.dub_enabled, s.subs_enabled, s.duck_level, s.max_height,
                          s.buffer_max_mb),
                         ("live", 12.5, 4.0, False, "ollama", False, False, 0.6, 1080, 8192))

    def test_out_of_range_or_malformed_values_fall_back(self):
        cfg = {"live_sync_mode": "fast", "live_delay_s": 31, "live_file_ahead_s": 3.9,
               "live_delay_auto": "no", "live_engine": "xtts", "live_duck_level": 0.05,
               "live_max_height": 900, "live_buffer_max_mb": 128}
        self.assertEqual(normalize_live_settings(cfg), normalize_live_settings({}))
        self.assertIsNone(normalize_live_settings({"live_delay_s": True}).delay_s)

    def test_round_trip_and_absent_delays_stay_absent(self):
        s = normalize_live_settings({"live_engine": "deepl", "live_delay_s": 20})
        cfg = settings_to_config(s)
        self.assertEqual(normalize_live_settings(cfg), s)
        self.assertNotIn("live_file_ahead_s", cfg)
        self.assertEqual(cfg["live_delay_s"], 20.0)


if __name__ == "__main__":
    unittest.main()
