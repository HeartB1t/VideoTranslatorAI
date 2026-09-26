import os
import time
import unittest

from videotranslator.live_translate import (
    EN_LEGS,
    TIMEOUTS_S,
    DeeplLiveTranslator,
    GoogleLiveTranslator,
    LiveTranslateError,
    OllamaLiveTranslator,
    MarianLeg,
    MarianLiveTranslator,
    MarianRoute,
    Outcome,
    make_translator,
    marian_is_cached,
    marian_route,
)

_HEAVY = os.environ.get("VTAI_RUN_HEAVY_SMOKE")
HELS_ = "Helsinki-NLP/"


class _Ret:
    def __init__(self, value):
        self.value = value

    def to(self, _device):
        return self.value


class _FakeTok:
    def __init__(self, model):
        self.model = model
        self.supported_language_codes = [">>pol<<"]

    def __call__(self, texts, **kw):
        return {"input_ids": _Ret(texts[0])}

    def batch_decode(self, gen, **kw):
        return [f"{self.model}:{gen}"]


class _FakeModel:
    def __init__(self, sleep=0.0):
        self._sleep = sleep

    def generate(self, **batch):
        if self._sleep:
            time.sleep(self._sleep)
        return batch["input_ids"]


def _cached(*models):
    names = set(models)
    return lambda m: m in names


def _marian(is_cached, *, sleep=0.0, hub_has=None):
    return MarianLiveTranslator(
        is_cached=is_cached, hub_has=hub_has,
        tokenizer_loader=lambda model: _FakeTok(model),
        model_loader=lambda model: _FakeModel(sleep))


class MarianLiveTranslatorTests(unittest.TestCase):
    def test_direct_leg_runs(self):
        tr = _marian(_cached(HELS_ + "opus-mt-en-it"))
        tr.prepare("en", "it")
        out = tr.translate("hello")
        self.assertTrue(out.ok)
        self.assertIn("opus-mt-en-it", out.text)

    def test_pivot_runs_both_legs(self):
        tr = _marian(_cached(HELS_ + "opus-mt-it-en", HELS_ + "opus-mt-tc-big-en-pt"))
        tr.prepare("it", "pt")
        out = tr.translate("ciao")
        self.assertTrue(out.ok)
        self.assertIn("opus-mt-it-en", out.text)
        self.assertIn("opus-mt-tc-big-en-pt", out.text)

    def test_group_target_token_is_prepended(self):
        tr = _marian(_cached(HELS_ + "opus-mt-en-zlw"))
        tr.prepare("en", "pl")
        self.assertIn(">>pol<<", tr.translate("hello").text)

    def test_no_route_raises(self):
        tr = _marian(lambda m: False)
        with self.assertRaises(LiveTranslateError) as ctx:
            tr.prepare("it", "pt")
        self.assertEqual(ctx.exception.key, "marian_pair")

    def test_timeout_returns_failed_outcome(self):
        tr = _marian(_cached(HELS_ + "opus-mt-en-it"), sleep=0.5)
        tr.prepare("en", "it")
        out = tr.translate("hello", timeout_s=0.05)
        self.assertFalse(out.ok)
        self.assertEqual(out.error, "timeout")

    def test_make_translator_marian(self):
        tr = make_translator("marian", is_cached=_cached(HELS_ + "opus-mt-en-it"),
                             tokenizer_loader=lambda m: _FakeTok(m),
                             model_loader=lambda m: _FakeModel())
        self.assertIsInstance(tr, MarianLiveTranslator)

    def test_make_translator_google(self):
        self.assertIsInstance(make_translator("google"), GoogleLiveTranslator)

    def test_make_translator_deepl(self):
        self.assertIsInstance(make_translator("deepl", deepl_key="k"),
                              DeeplLiveTranslator)

    def test_make_translator_ollama(self):
        self.assertIsInstance(make_translator("ollama"), OllamaLiveTranslator)

    def test_make_translator_unknown_raises(self):
        with self.assertRaises(LiveTranslateError):
            make_translator("bing")


class GoogleLiveTranslatorTests(unittest.TestCase):
    def _google(self, fn):
        class _T:
            def translate(self, text):
                return fn(text)
        return GoogleLiveTranslator(translator_factory=lambda s, t: _T(),
                                    sleep=lambda _s: None)

    def test_translates(self):
        tr = self._google(lambda _t: "ciao")
        tr.prepare("en", "it")
        out = tr.translate("hello")
        tr.close()
        self.assertTrue(out.ok)
        self.assertEqual(out.text, "ciao")

    def test_rate_limit_is_classified_and_keeps_original(self):
        def boom(_t):
            raise RuntimeError("TooManyRequests: 429")
        tr = self._google(boom)
        tr.prepare("en", "it")
        out = tr.translate("hello")
        tr.close()
        self.assertFalse(out.ok)
        self.assertEqual(out.error, "rate_limited")
        self.assertEqual(out.text, "hello")

    def test_timeout_abandons_the_call(self):
        def slow(_t):
            time.sleep(0.5)
            return "x"
        tr = self._google(slow)
        tr.prepare("en", "it")
        out = tr.translate("hello", timeout_s=0.05)
        tr.close()
        self.assertFalse(out.ok)
        self.assertEqual(out.error, "timeout")


class _FakeResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class DeeplLiveTranslatorTests(unittest.TestCase):
    def test_translates_over_free_endpoint(self):
        posts = []

        def post(url, data, headers, timeout):
            posts.append((url, dict(data), headers, timeout))
            return _FakeResp(200, {"translations": [{"text": "ciao"}]})

        tr = DeeplLiveTranslator(deepl_key="key:fx", post=post)
        tr.prepare("en", "it")
        out = tr.translate("hello")
        self.assertTrue(out.ok)
        self.assertEqual(out.text, "ciao")
        self.assertIn("api-free.deepl.com", posts[0][0])
        self.assertEqual(posts[0][3], (3, 5))

    def test_status_codes_map_to_error_kinds(self):
        for status, kind in ((429, "rate_limited"), (456, "quota"),
                             (403, "unavailable"), (500, "error")):
            tr = DeeplLiveTranslator(deepl_key="key",
                                     post=lambda *a, **k: _FakeResp(status))
            tr.prepare("en", "it")
            out = tr.translate("hi")
            self.assertFalse(out.ok)
            self.assertEqual(out.error, kind, status)
            self.assertEqual(out.text, "hi")

    def test_missing_key_raises_on_prepare(self):
        tr = DeeplLiveTranslator(deepl_key="")
        with self.assertRaises(LiveTranslateError) as ctx:
            tr.prepare("en", "it")
        self.assertEqual(ctx.exception.key, "deepl_key")

    def test_english_target_becomes_en_us_and_paid_endpoint(self):
        seen = {}

        def post(url, data, headers, timeout):
            seen["url"] = url
            seen["data"] = dict(data)
            return _FakeResp(200, {"translations": [{"text": "x"}]})

        tr = DeeplLiveTranslator(deepl_key="paidkey", post=post)
        tr.prepare("it", "en")
        tr.translate("ciao")
        self.assertEqual(seen["data"]["target_lang"], "EN-US")
        self.assertEqual(seen["data"]["source_lang"], "IT")
        self.assertIn("://api.deepl.com", seen["url"])


class OllamaLiveTranslatorTests(unittest.TestCase):
    @staticmethod
    def _ok_health(url, model):
        return (True, "", model)

    @staticmethod
    def _down_health(url, model):
        return (False, "daemon down", "")

    def test_translates(self):
        tr = OllamaLiveTranslator(
            model="qwen3:8b", health_check=self._ok_health,
            generate=lambda prompt, *, num_predict, timeout: "Ciao, come stai?")
        tr.prepare("en", "it")
        out = tr.translate("Hello, how are you?")
        tr.close()
        self.assertTrue(out.ok)
        self.assertEqual(out.text, "Ciao, come stai?")

    def test_daemon_down_raises_on_prepare(self):
        tr = OllamaLiveTranslator(health_check=self._down_health,
                                  generate=lambda *a, **k: "x")
        with self.assertRaises(LiveTranslateError) as ctx:
            tr.prepare("en", "it")
        self.assertEqual(ctx.exception.key, "ollama")

    def test_timeout_keeps_original(self):
        def boom(prompt, *, num_predict, timeout):
            raise RuntimeError("HTTPSConnectionPool: Read timed out")
        tr = OllamaLiveTranslator(health_check=self._ok_health, generate=boom)
        tr.prepare("en", "it")
        out = tr.translate("Hello")
        self.assertFalse(out.ok)
        self.assertEqual(out.error, "timeout")
        self.assertEqual(out.text, "Hello")

    def test_empty_response_is_a_failure(self):
        tr = OllamaLiveTranslator(health_check=self._ok_health,
                                  generate=lambda *a, **k: "   ")
        tr.prepare("en", "it")
        out = tr.translate("Hello")
        self.assertFalse(out.ok)
        self.assertEqual(out.error, "error")


@unittest.skipUnless(_HEAVY, "heavy smoke: set VTAI_RUN_HEAVY_SMOKE=1")
class GoogleLiveTranslatorHeavyTests(unittest.TestCase):
    def test_real_en_to_it(self):
        # The unofficial free Google endpoint often rate-limits a host (a first
        # call can already return TooManyRequests). The contract is that the real
        # call never raises and returns a well-formed Outcome: a real translation
        # when it succeeds, or the original text with a known error kind when the
        # endpoint refuses.
        tr = GoogleLiveTranslator()
        tr.prepare("en", "it")
        out = tr.translate("Hello, how are you?", timeout_s=15.0)
        tr.close()
        self.assertIsInstance(out.text, str)
        if out.ok:
            self.assertNotEqual(out.text.strip().lower(), "hello, how are you?")
        else:
            self.assertIn(out.error,
                          ("rate_limited", "quota", "timeout", "unavailable", "error"))
            self.assertEqual(out.text, "Hello, how are you?")


@unittest.skipUnless(_HEAVY, "heavy smoke: set VTAI_RUN_HEAVY_SMOKE=1")
class MarianLiveTranslatorHeavyTests(unittest.TestCase):
    def test_real_en_to_it(self):
        tr = MarianLiveTranslator(hub_has=lambda m: True, is_cached=lambda m: False)
        tr.prepare("en", "it")
        out = tr.translate("Hello, how are you today?", timeout_s=60.0)
        tr.close()
        self.assertTrue(out.ok, out.error)
        self.assertTrue(out.text.strip())
        self.assertNotEqual(out.text.strip().lower(), "hello, how are you today?")


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
