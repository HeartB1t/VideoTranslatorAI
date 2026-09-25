import contextlib
import io
import sys
import types
import unittest
from unittest import mock

from videotranslator import translation
from videotranslator.quality_flags import FLAG_TRANSLATION_FALLBACK
from videotranslator.translation import (
    TranslationUnavailableError,
    _marian_normalize_lang,
    translate_segments,
)


class TranslationDispatcherTests(unittest.TestCase):
    def test_marian_normalize_lang(self):
        self.assertEqual(_marian_normalize_lang("zh-CN"), "zh")
        self.assertEqual(_marian_normalize_lang("no"), "nb")
        self.assertEqual(_marian_normalize_lang("it-IT"), "it")

    def test_ollama_engine_uses_injected_translator(self):
        seen = {}

        def fake_ollama(segments, source, target, **kwargs):
            seen["source"] = source
            seen["target"] = target
            seen["kwargs"] = kwargs
            return [{"start": 0.0, "end": 1.0, "text_src": "hello", "text_tgt": "ciao"}]

        result = translate_segments(
            [{"start": 0.0, "end": 1.0, "text": "hello"}],
            "en",
            "it",
            engine="llm_ollama",
            ollama_model="qwen3:14b",
            ollama_thinking=True,
            ollama_translator=fake_ollama,
        )

        self.assertEqual(result[0]["text_tgt"], "ciao")
        self.assertEqual(seen["source"], "en")
        self.assertEqual(seen["target"], "it")
        self.assertEqual(seen["kwargs"]["model"], "qwen3:14b")
        self.assertTrue(seen["kwargs"]["thinking"])


# The Google path imports deep_translator and requests lazily. CI installs
# only lightweight deps, so the tests provide stand-in modules for both.
class TooManyRequests(Exception):
    pass


class RequestError(Exception):
    pass


class TranslationNotFound(Exception):
    pass


def _fake_google_modules(translator_cls):
    dt = types.ModuleType("deep_translator")
    dt.GoogleTranslator = translator_cls
    exc = types.ModuleType("deep_translator.exceptions")
    exc.TooManyRequests = TooManyRequests
    exc.RequestError = RequestError
    exc.TranslationNotFound = TranslationNotFound
    dt.exceptions = exc
    req = types.ModuleType("requests")
    req.RequestException = type("RequestException", (Exception,), {})
    return {"deep_translator": dt, "deep_translator.exceptions": exc, "requests": req}


class _FakeClock:
    """Stand-in for the ``time`` module: sleeps advance a virtual clock."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class GoogleRateLimitTests(unittest.TestCase):
    def _run(self, side_effect, segments):
        clock = _FakeClock()
        fake_cls = mock.Mock()
        fake_cls.return_value.translate.side_effect = side_effect
        with mock.patch.dict(sys.modules, _fake_google_modules(fake_cls)), \
                mock.patch.object(translation, "time", clock), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            try:
                result = translate_segments(segments, "en", "it", engine="google")
            finally:
                self.log = out.getvalue()
                self.calls = fake_cls.return_value.translate.call_count
                self.clock = clock
        return result

    @staticmethod
    def _segs(*texts):
        return [
            {"start": float(i), "end": float(i) + 1.0, "text": t}
            for i, t in enumerate(texts)
        ]

    def test_all_rate_limited_raises_and_stops_calling_google(self):
        segs = self._segs(*[f"hello {i}" for i in range(10)])
        with self.assertRaises(TranslationUnavailableError):
            self._run(TooManyRequests(), segs)
        # 3 segments x 3 attempts, then a single probe after the cooldown.
        self.assertEqual(self.calls, 10)
        self.assertIn(translation._GOOGLE_COOLDOWN, self.clock.sleeps)

    def test_transient_rate_limit_is_retried(self):
        segs = self._segs("hello")
        result = self._run([TooManyRequests(), "ciao"], segs)
        self.assertEqual(result[0]["text_tgt"], "ciao")
        self.assertNotIn("_quality_flags", result[0])
        self.assertIn(2.0, self.clock.sleeps)

    def test_partial_failure_flags_segment_and_warns(self):
        segs = self._segs("one", "two", "three")

        def fake(text):
            if text == "two":
                raise TooManyRequests()
            return text.upper()

        result = self._run(fake, segs)
        self.assertEqual([s["text_tgt"] for s in result], ["ONE", "two", "THREE"])
        self.assertNotIn("_quality_flags", result[0])
        self.assertIn(FLAG_TRANSLATION_FALLBACK, result[1]["_quality_flags"])
        warning = (
            "Google Translate failed on 1/3 segments: they keep the source "
            "text and are flagged in the subtitle editor."
        )
        self.assertEqual(self.log.count(warning), 1)

    @staticmethod
    def _scripted(*answers):
        items = iter(answers)

        def fake(text):
            item = next(items)
            if isinstance(item, Exception):
                raise item
            return item

        return fake

    def test_block_mid_job_aborts_after_failed_probe(self):
        segs = self._segs("a", "b", "c", "d", "e", "f")
        fake = self._scripted("A", *[TooManyRequests()] * 10)
        with self.assertRaises(TranslationUnavailableError):
            self._run(fake, segs)
        # 1 success + 3 failed segments x 3 attempts + 1 probe; "f" never sent.
        self.assertEqual(self.calls, 11)

    def test_successful_probe_resumes_translation(self):
        segs = self._segs("a", "b", "c", "d", "e", "f")
        fake = self._scripted("A", *[TooManyRequests()] * 9, "E", "F")
        result = self._run(fake, segs)
        self.assertEqual(
            [s["text_tgt"] for s in result], ["A", "b", "c", "d", "E", "F"],
        )
        for seg in result[1:4]:
            self.assertIn(FLAG_TRANSLATION_FALLBACK, seg["_quality_flags"])
        for seg in (result[0], result[4], result[5]):
            self.assertNotIn("_quality_flags", seg)
        self.assertEqual(self.clock.sleeps.count(translation._GOOGLE_COOLDOWN), 1)
        self.assertIn("3/6", self.log)

    def test_probe_failing_with_captcha_page_aborts(self):
        segs = self._segs("a", "b", "c", "d", "e")
        fake = self._scripted(*[TooManyRequests()] * 9, TranslationNotFound("x"))
        with self.assertRaises(TranslationUnavailableError):
            self._run(fake, segs)
        self.assertEqual(self.calls, 10)
        self.assertEqual(self.clock.sleeps.count(translation._GOOGLE_COOLDOWN), 1)

    def test_second_block_aborts_without_another_cooldown(self):
        segs = self._segs(*"abcdefghij")
        fake = self._scripted(
            *[TooManyRequests()] * 9, "D", *[TooManyRequests()] * 9,
        )
        with self.assertRaises(TranslationUnavailableError):
            self._run(fake, segs)
        # 9 + probe + 9: the second block raises before any new request.
        self.assertEqual(self.calls, 19)
        self.assertEqual(self.clock.sleeps.count(translation._GOOGLE_COOLDOWN), 1)

    def test_block_on_last_segments_only_warns(self):
        segs = self._segs("a", "b", "c", "d")
        fake = self._scripted("A", *[TooManyRequests()] * 9)
        result = self._run(fake, segs)
        self.assertEqual(result[0]["text_tgt"], "A")
        self.assertNotIn(translation._GOOGLE_COOLDOWN, self.clock.sleeps)
        self.assertIn("3/4", self.log)

    def test_request_error_is_retried(self):
        result = self._run([RequestError(), "ciao"], self._segs("hello"))
        self.assertEqual(result[0]["text_tgt"], "ciao")
        self.assertEqual(self.calls, 2)

    def test_non_transient_errors_are_not_retried_nor_trip_the_breaker(self):
        segs = self._segs("a", "b", "c", "d", "e")
        fake = self._scripted(*[TranslationNotFound("x")] * 4, "E")
        result = self._run(fake, segs)
        self.assertEqual(self.calls, 5)
        self.assertNotIn(translation._GOOGLE_COOLDOWN, self.clock.sleeps)
        self.assertEqual(result[4]["text_tgt"], "E")
        for seg in result[:4]:
            self.assertIn(FLAG_TRANSLATION_FALLBACK, seg["_quality_flags"])

    def test_empty_segments_do_not_count_as_failures(self):
        result = self._run(TooManyRequests(), self._segs("", "  "))
        self.assertEqual([s["text_tgt"] for s in result], ["", ""])
        self.assertEqual(self.calls, 0)

    def test_requests_are_paced(self):
        self._run(lambda text: text, self._segs("a", "b", "c"))
        paced = [s for s in self.clock.sleeps if s > 0]
        self.assertEqual(len(paced), 2)


class _FakeDeepLResponse:
    def __init__(self, status_code, texts=()):
        self.status_code = status_code
        self.headers = {}
        self.text = ""
        self._texts = texts

    def raise_for_status(self):
        pass

    def json(self):
        return {"translations": [{"text": t.upper()} for t in self._texts]}


class DeepLFailedBatchTests(unittest.TestCase):
    """A batch that still fails after the retries must not go by silently."""

    def _run(self, answer_failing_batch, n_segments=51, failing_text="s50"):
        # 51 segments = two DeepL batches (50 + 1). The batch that carries
        # failing_text gets answer_failing_batch, every other one succeeds.
        segs = [
            {"start": float(i), "end": float(i) + 1.0, "text": f"s{i}"}
            for i in range(n_segments)
        ]
        modules = _fake_google_modules(mock.Mock())
        google = modules["deep_translator"].GoogleTranslator
        google.return_value.translate.side_effect = lambda text: f"google:{text}"
        requests_stub = modules["requests"]
        self.posts = 0

        def fake_post(endpoint, headers=None, data=None, timeout=None):
            self.posts += 1
            texts = [value for key, value in data if key == "text"]
            if failing_text in texts:
                return answer_failing_batch(requests_stub)
            return _FakeDeepLResponse(200, texts)

        requests_stub.post = fake_post
        self.clock = _FakeClock()
        with mock.patch.dict(sys.modules, modules), \
                mock.patch.object(translation, "time", self.clock), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            try:
                return translate_segments(
                    segs, "en", "it", engine="deepl", deepl_key="key:fx",
                )
            finally:
                self.log = out.getvalue()

    @staticmethod
    def _network_error(requests_stub):
        raise requests_stub.RequestException("connection reset")

    @staticmethod
    def _rate_limited(requests_stub):
        return _FakeDeepLResponse(429)

    def _assert_only_last_batch_flagged(self, result):
        self.assertEqual(result[0]["text_tgt"], "S0")
        self.assertEqual(result[49]["text_tgt"], "S49")
        for seg in result[:50]:
            self.assertNotIn("_quality_flags", seg)
        self.assertEqual(result[50]["text_tgt"], "s50")
        self.assertIn(FLAG_TRANSLATION_FALLBACK, result[50]["_quality_flags"])
        warning = (
            "DeepL failed on 1/51 segments: they keep the source text and "
            "are flagged in the subtitle editor."
        )
        self.assertEqual(self.log.count(warning), 1)

    def test_network_error_batch_is_flagged_and_counted(self):
        result = self._run(self._network_error)
        self._assert_only_last_batch_flagged(result)
        self.assertEqual(self.posts, 1 + 5)

    def test_rate_limited_batch_is_flagged_and_counted(self):
        result = self._run(self._rate_limited)
        self._assert_only_last_batch_flagged(result)
        self.assertEqual(self.posts, 1 + 5)

    def test_all_batches_failing_falls_back_to_google(self):
        for answer in (self._network_error, self._rate_limited):
            with self.subTest(answer=answer.__name__):
                result = self._run(answer, n_segments=3, failing_text="s0")
                self.assertEqual(
                    [s["text_tgt"] for s in result],
                    ["google:s0", "google:s1", "google:s2"],
                )
                self.assertIn("falling back to Google Translate", self.log)

    def test_success_has_no_flags_nor_warning(self):
        result = self._run(self._network_error, failing_text=None)
        self.assertEqual(result[50]["text_tgt"], "S50")
        for seg in result:
            self.assertNotIn("_quality_flags", seg)
        self.assertNotIn("failed", self.log)
        self.assertEqual(self.posts, 2)


if __name__ == "__main__":
    unittest.main()
