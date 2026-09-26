import unittest

from videotranslator.live_translate import (
    EN_LEGS,
    TIMEOUTS_S,
    MarianLeg,
    MarianRoute,
    marian_is_cached,
    marian_route,
)

HELS = "Helsinki-NLP/"


def _cached(*models):
    names = set(models)
    return lambda m: m in names


NONE_CACHED = lambda m: False


class MarianRouteTests(unittest.TestCase):
    def test_direct_en_to_it_single_leg(self):
        route = marian_route("en", "it", hub_has=None,
                             is_cached=_cached(HELS + "opus-mt-en-it"))
        self.assertIsNotNone(route)
        self.assertFalse(route.pivot)
        self.assertEqual([leg.model for leg in route.legs], [HELS + "opus-mt-en-it"])

    def test_direct_pair_prefers_plain_over_pivot(self):
        route = marian_route("it", "es", hub_has=None,
                             is_cached=_cached(HELS + "opus-mt-it-es"))
        self.assertFalse(route.pivot)
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-it-es")

    def test_tc_big_pair_en_to_pt(self):
        route = marian_route("en", "pt", hub_has=None,
                             is_cached=_cached(HELS + "opus-mt-tc-big-en-pt"))
        self.assertFalse(route.pivot)
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-tc-big-en-pt")

    def test_group_pair_en_to_pl_carries_target_tokens(self):
        route = marian_route("en", "pl", hub_has=None,
                             is_cached=_cached(HELS + "opus-mt-en-zlw"))
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-en-zlw")
        self.assertIn(">>pol<<", route.legs[0].target_token_candidates)

    def test_pivot_it_to_pt(self):
        route = marian_route(
            "it", "pt", hub_has=None,
            is_cached=_cached(HELS + "opus-mt-it-en", HELS + "opus-mt-tc-big-en-pt"))
        self.assertTrue(route.pivot)
        self.assertEqual([leg.model for leg in route.legs],
                         [HELS + "opus-mt-it-en", HELS + "opus-mt-tc-big-en-pt"])

    def test_norwegian_pivot_uses_group_models(self):
        route = marian_route(
            "en", "no", hub_has=None,
            is_cached=_cached(HELS + "opus-mt-tc-big-en-gmq"))
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-tc-big-en-gmq")
        self.assertIn(">>nob<<", route.legs[0].target_token_candidates)

    def test_hub_direct_when_online(self):
        route = marian_route("it", "es", hub_has=_cached(HELS + "opus-mt-it-es"),
                             is_cached=NONE_CACHED)
        self.assertFalse(route.pivot)
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-it-es")

    def test_offline_without_cache_gives_no_route(self):
        self.assertIsNone(marian_route("it", "pt", hub_has=None, is_cached=NONE_CACHED))

    def test_same_language_has_no_route(self):
        self.assertIsNone(marian_route("it", "it", hub_has=None, is_cached=NONE_CACHED))

    def test_zh_cn_normalizes_to_zh(self):
        route = marian_route("en", "zh-CN", hub_has=None,
                             is_cached=_cached(HELS + "opus-mt-en-zh"))
        self.assertEqual(route.legs[0].model, HELS + "opus-mt-en-zh")


class EnLegsTableTests(unittest.TestCase):
    def test_every_non_english_project_code_is_covered(self):
        # 26 project languages minus English, with Norwegian normalized to nb.
        expected = {
            "ar", "cs", "da", "de", "el", "es", "fi", "fr", "hi", "hu", "id",
            "it", "ja", "ko", "nl", "nb", "pl", "pt", "ro", "ru", "sv", "tr",
            "uk", "vi", "zh",
        }
        self.assertEqual(set(EN_LEGS), expected)

    def test_each_entry_has_both_directions(self):
        for code, (to_en, from_en) in EN_LEGS.items():
            self.assertIsNotNone(to_en, code)
            self.assertIsNotNone(from_en, code)


class MarianIsCachedTests(unittest.TestCase):
    def test_all_legs_cached(self):
        route = MarianRoute((MarianLeg("a"), MarianLeg("b")), True)
        self.assertTrue(marian_is_cached(route, loader=_cached("a", "b")))

    def test_missing_leg_is_not_cached(self):
        route = MarianRoute((MarianLeg("a"), MarianLeg("b")), True)
        self.assertFalse(marian_is_cached(route, loader=_cached("a")))


class TimeoutsTests(unittest.TestCase):
    def test_expected_keys(self):
        self.assertEqual(set(TIMEOUTS_S),
                         {"marian", "ollama_delayed", "ollama_live", "google", "deepl"})


if __name__ == "__main__":
    unittest.main()
