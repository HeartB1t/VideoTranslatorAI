import io
import json
import queue
import tempfile
import threading
import time
import unittest
import urllib.error
from types import SimpleNamespace

from videotranslator import elevenlabs_tts as el
from videotranslator.live_tts import LiveTtsUnavailable


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code, detail=None):
    body = json.dumps({"detail": detail or {}}).encode()
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))


class _Opener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, req, timeout):
        self.requests.append((req, timeout))
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _Resp(item if isinstance(item, bytes) else json.dumps(item).encode())


class _Breaker:
    def __init__(self):
        self.failures, self.successes, self.open = [], 0, False

    def allow(self):
        return not self.open

    def record_failure(self, *, kind):
        self.failures.append(kind)

    def record_success(self):
        self.successes += 1


class ClassifyTests(unittest.TestCase):
    def test_http_errors(self):
        quota = json.dumps({"detail": {"status": "quota_exceeded"}}).encode()
        self.assertEqual(el.classify_http(401, quota), "quota")
        self.assertEqual(el.classify_http(401, b"{}"), "auth")
        self.assertEqual(el.classify_http(402, b""), "quota")
        self.assertEqual(el.classify_http(429, b"{}"), "rate_limited")
        self.assertEqual(el.classify_http(422, b"{}"), "invalid")
        self.assertEqual(el.classify_http(503, b"<html>"), "unavailable")

    def test_rate_to_speed_is_clamped(self):
        self.assertEqual(el.rate_to_speed(0), 1.0)
        self.assertEqual(el.rate_to_speed(15), 1.15)
        self.assertEqual(el.rate_to_speed(60), 1.2)
        self.assertEqual(el.rate_to_speed(-50), 0.7)


class ClientTests(unittest.TestCase):
    def test_key_travels_only_in_the_header(self):
        opener = _Opener([_http_error(401)])
        client = el.ElevenLabsClient("sk_secret", opener=opener)
        with self.assertRaises(el.ElevenLabsError) as ctx:
            client.account()
        self.assertEqual(ctx.exception.kind, "auth")
        self.assertNotIn("sk_secret", str(ctx.exception))
        req = opener.requests[0][0]
        self.assertEqual(req.get_header("Xi-api-key"), "sk_secret")
        self.assertNotIn("sk_secret", req.full_url)

    def test_no_key_is_an_auth_error_without_a_request(self):
        opener = _Opener([])
        with self.assertRaises(el.ElevenLabsError) as ctx:
            el.ElevenLabsClient("  ", opener=opener).voices()
        self.assertEqual(ctx.exception.kind, "auth")
        self.assertEqual(opener.requests, [])

    def test_account_voices_models(self):
        opener = _Opener([
            {"character_count": 1200, "character_limit": 10000, "tier": "free"},
            {"voices": [{"voice_id": "v2", "name": "Zoe", "labels": {"accent": "british"}},
                        {"voice_id": "v1", "name": "Adam", "labels": {"gender": "male"},
                         "verified_languages": [{"language": "it"}, {"language": "en"}]}]},
            [{"model_id": "eleven_multilingual_v2", "name": "Multilingual v2",
              "can_do_text_to_speech": True,
              "languages": [{"language_id": "it"}, {"language_id": "en"}]},
             {"model_id": "eleven_flash_v2_5", "name": "Flash v2.5",
              "can_do_text_to_speech": True, "languages": [{"language_id": "it"}]},
             {"model_id": "sts", "name": "STS", "can_do_text_to_speech": False,
              "languages": [{"language_id": "it"}]}],
        ])
        client = el.ElevenLabsClient("k", opener=opener)
        self.assertEqual(client.account(), el.Account(1200, 10000, "free"))
        voices = client.voices()
        self.assertEqual([v.name for v in voices], ["Adam", "Zoe"])
        self.assertEqual(voices[0].languages, ("en", "it"))
        self.assertEqual(voices[1].label(), "Zoe (british)")
        models = client.models()
        self.assertEqual(el.pick_live_model(models, "it").model_id, "eleven_flash_v2_5")
        self.assertEqual(el.pick_live_model(models, "en").model_id, "eleven_multilingual_v2")
        self.assertIsNone(el.pick_live_model(models, "ja"))

    def test_synthesize_sends_language_only_to_models_that_accept_it(self):
        opener = _Opener([b"mp3", b"mp3"])
        client = el.ElevenLabsClient("k", opener=opener)
        client.synthesize("ciao", "v1", "eleven_flash_v2_5", language="it-IT", speed=1.1)
        client.synthesize("ciao", "v1", "eleven_multilingual_v2", language="it")
        first = json.loads(opener.requests[0][0].data)
        second = json.loads(opener.requests[1][0].data)
        self.assertEqual(first["language_code"], "it")
        self.assertEqual(first["voice_settings"], {"speed": 1.1})
        self.assertNotIn("language_code", second)
        self.assertIn("output_format=mp3_44100_64", opener.requests[0][0].full_url)

    def test_network_errors(self):
        for exc, kind in ((urllib.error.URLError("no route"), "unavailable"),
                          (TimeoutError(), "timeout"),
                          (_http_error(429), "rate_limited")):
            with self.assertRaises(el.ElevenLabsError) as ctx:
                el.ElevenLabsClient("k", opener=_Opener([exc])).synthesize("x", "v", "m")
            self.assertEqual(ctx.exception.kind, kind)


class _FakeClient:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def synthesize(self, text, voice_id, model_id, *, language=None, speed=1.0,
                   timeout=None):
        self.calls.append((text, voice_id, model_id, language, speed))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _wait_result(results, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            return results.get_nowait()
        except queue.Empty:
            time.sleep(0.01)
    raise AssertionError("no result")


class SynthTests(unittest.TestCase):
    def _synth(self, tmp, outcome, **kw):
        breaker = _Breaker()
        synth = el.ElevenLabsClipSynth("k", "v1", "eleven_flash_v2_5", tmp, breaker=breaker,
                                       language="it", client=_FakeClient(outcome),
                                       sanitize=lambda t: t.strip(), **kw)
        synth.start()
        self.addCleanup(synth.stop, 2.0)
        return synth, breaker

    def test_clip_is_written_measured_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth, breaker = self._synth(tmp, b"x" * 16000)
            self.assertTrue(synth.submit(3, 1, " ciao ", 10, time.monotonic() + 10))
            seg, gen, clip, reason = _wait_result(synth.results)
            self.assertEqual((seg, gen, reason), (3, 1, None))
            self.assertAlmostEqual(clip.duration, 2.0)
            self.assertEqual(clip.rate, "+10%")
            self.assertTrue(clip.path.endswith("clip_1_3.mp3"))
            self.assertEqual(breaker.successes, 1)
            self.assertEqual(synth._client.calls[0], ("ciao", "v1", "eleven_flash_v2_5",
                                                      "it", 1.1))

    def test_quota_is_fatal_and_refuses_further_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth, breaker = self._synth(tmp, el.ElevenLabsError("quota"))
            synth.submit(1, 0, "a", 0, time.monotonic() + 10)
            _, _, clip, reason = _wait_result(synth.results)
            self.assertIsNone(clip)
            self.assertEqual(reason, "elevenlabs_quota")
            self.assertEqual(synth.fatal, "quota")
            self.assertEqual(breaker.failures, ["quota"])
            self.assertFalse(synth.submit(2, 0, "b", 0, time.monotonic() + 10))

    def test_transient_error_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth, breaker = self._synth(tmp, el.ElevenLabsError("rate_limited"))
            synth.submit(1, 0, "a", 0, time.monotonic() + 10)
            self.assertEqual(_wait_result(synth.results)[3], "elevenlabs_rate_limited")
            self.assertIsNone(synth.fatal)
            self.assertEqual(breaker.failures, ["tts"])

    def test_late_and_empty_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth, _ = self._synth(tmp, b"x")
            self.assertFalse(synth.submit(1, 0, "a", 0, time.monotonic() - 1))
            synth.submit(2, 0, "   ", 0, time.monotonic() + 10)
            self.assertEqual(_wait_result(synth.results)[3], "empty")

    def test_missing_configuration_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            synth = el.ElevenLabsClipSynth("", "v", "m", tmp, breaker=_Breaker())
            with self.assertRaises(LiveTtsUnavailable):
                synth.start()


class _FakeFallback:
    name = "edge-tts"

    def __init__(self):
        self.results = queue.Queue()
        self.started = False
        self.submitted = []

    def start(self):
        self.started = True

    def submit(self, seg_id, gen, text, rate_pct, deadline):
        self.submitted.append((seg_id, gen, text))
        self.results.put((seg_id, gen, SimpleNamespace(path="edge.mp3"), None))
        return True

    def stop(self, timeout_s):
        return True


class FallbackTests(unittest.TestCase):
    def test_fatal_error_switches_and_resends_the_sentence(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary = el.ElevenLabsClipSynth(
                "k", "v", "m", tmp, breaker=_Breaker(),
                client=_FakeClient(el.ElevenLabsError("auth")), sanitize=str.strip)
            fallback = _FakeFallback()
            switched = []
            synth = el.FallbackClipSynth(primary, lambda: fallback, on_switch=switched.append)
            synth.start()
            self.addCleanup(synth.stop, 2.0)
            self.assertTrue(synth.submit(1, 0, "ciao", 0, time.monotonic() + 10))
            result = _wait_result(synth.results)
            self.assertEqual(result[0], 1)
            self.assertEqual(result[2].path, "edge.mp3")        # voiced by the fallback
            self.assertEqual(switched, ["auth"])
            self.assertTrue(fallback.started)
            self.assertEqual(synth.name, "edge-tts")
            synth.submit(2, 0, "dopo", 0, time.monotonic() + 10)
            self.assertEqual(fallback.submitted[-1], (2, 0, "dopo"))

    def test_no_fallback_keeps_the_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary = el.ElevenLabsClipSynth(
                "k", "v", "m", tmp, breaker=_Breaker(),
                client=_FakeClient(el.ElevenLabsError("quota")), sanitize=str.strip)
            synth = el.FallbackClipSynth(primary, lambda: None)
            synth.start()
            self.addCleanup(synth.stop, 2.0)
            synth.submit(1, 0, "ciao", 0, time.monotonic() + 10)
            self.assertEqual(_wait_result(synth.results)[3], "elevenlabs_quota")


if __name__ == "__main__":
    unittest.main()
