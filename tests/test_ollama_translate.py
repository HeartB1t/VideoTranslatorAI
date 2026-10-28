"""Behaviour of the Ollama translation orchestrator, with a fake daemon."""

import unittest
from unittest import mock

from videotranslator import ollama_translate as target
from videotranslator.quality_flags import (
    FLAG_LENGTH_UNFIT,
    FLAG_TRANSLATION_FALLBACK,
    compute_segment_quality_flags,
)

URL = "http://localhost:11434"


class _FakeOllama:
    """Stands in for ``requests.post``: answers by prompt kind, records payloads."""

    def __init__(self, translate, rewrite=None, verify=None):
        self.translate = translate
        self.rewrite = rewrite
        self.verify = verify
        self.payloads = []

    def __call__(self, url, json, timeout):
        self.payloads.append(json)
        prompt = json["prompt"]
        if "You are a translation verifier" in prompt:
            reply = self.verify(prompt)
        elif "too long for the audio slot" in prompt:
            reply = self.rewrite(prompt)
        else:
            reply = self.translate(prompt)
        if isinstance(reply, BaseException):
            raise reply
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": reply}
        return response

    def kinds(self):
        out = []
        for p in self.payloads:
            if "You are a translation verifier" in p["prompt"]:
                out.append("verify")
            elif "too long for the audio slot" in p["prompt"]:
                out.append("rewrite")
            else:
                out.append("translate")
        return out


def _seg(text, start=0.0, end=3.0, **extra):
    return {"start": start, "end": end, "text": text, **extra}


class TranslateWithOllamaTests(unittest.TestCase):
    def _run(self, segments, fake, *, health=(True, "", "qwen3:8b"), **kwargs):
        kwargs.setdefault("use_document_context", False)
        with mock.patch.object(target, "_ollama_health_check", return_value=health), \
                mock.patch("requests.post", fake), \
                mock.patch("builtins.print"):
            return target.translate_with_ollama(segments, "en", "it", api_url=URL, **kwargs)

    def test_translates_each_segment_with_the_shared_schema(self):
        fake = _FakeOllama(translate=lambda p: "Ciao mondo.")
        out = self._run([_seg("Hello world.", speaker="SPEAKER_01"), _seg("   ")], fake)

        self.assertEqual(out[0]["text_src"], "Hello world.")
        self.assertEqual(out[0]["text_tgt"], "Ciao mondo.")
        self.assertEqual(out[0]["speaker"], "SPEAKER_01")
        self.assertEqual((out[0]["start"], out[0]["end"]), (0.0, 3.0))
        self.assertGreater(out[0]["_target_chars"], 0)
        self.assertFalse(out[0]["_length_retry_attempted"])
        self.assertEqual(out[1]["text_tgt"], "")
        self.assertEqual(fake.kinds(), ["translate"])

    def test_daemon_down_raises_before_any_segment(self):
        fake = _FakeOllama(translate=lambda p: "x")
        with self.assertRaises(RuntimeError):
            self._run([_seg("Hello.")], fake, health=(False, "Ollama not reachable", ""))
        self.assertEqual(fake.payloads, [])

    def test_resolved_model_replaces_missing_one(self):
        fake = _FakeOllama(translate=lambda p: "Ciao.")
        self._run([_seg("Hi.")], fake, model="qwen3:14b",
                  health=(True, "using qwen3:8b", "qwen3:8b"))
        self.assertEqual(fake.payloads[0]["model"], "qwen3:8b")

    def test_qwen3_disables_thinking_and_others_do_not_send_the_flag(self):
        qwen = _FakeOllama(translate=lambda p: "Ciao.")
        self._run([_seg("Hi.")], qwen, model="qwen3:8b")
        self.assertIs(qwen.payloads[0]["think"], False)
        self.assertEqual(qwen.payloads[0]["options"]["temperature"], 0.7)

        llama = _FakeOllama(translate=lambda p: "Ciao.")
        self._run([_seg("Hi.")], llama, model="llama3:8b", health=(True, "", "llama3:8b"))
        self.assertNotIn("think", llama.payloads[0])
        self.assertEqual(llama.payloads[0]["options"]["temperature"], 0.3)

    def test_failed_segment_uses_fallback_and_is_flagged(self):
        fake = _FakeOllama(translate=lambda p: RuntimeError("boom"))
        seg = _seg("Hello.")
        out = self._run([seg], fake, fallback_fn=lambda s: "Ciao (google).")
        self.assertEqual(out[0]["text_tgt"], "Ciao (google).")
        self.assertIn(FLAG_TRANSLATION_FALLBACK, compute_segment_quality_flags(seg))

    def test_failed_segment_without_fallback_keeps_source(self):
        fake = _FakeOllama(translate=lambda p: "")
        out = self._run([_seg("Hello.")], fake)
        self.assertEqual(out[0]["text_tgt"], "Hello.")

    def test_over_budget_translation_is_rewritten_shorter(self):
        long_it = "Questa e' una traduzione davvero troppo lunga per lo slot audio breve."
        fake = _FakeOllama(translate=lambda p: long_it, rewrite=lambda p: "Troppo lunga.")
        out = self._run([_seg("Too long.", end=1.0)], fake)
        self.assertEqual(out[0]["text_tgt"], "Troppo lunga.")
        self.assertTrue(out[0]["_length_retry_attempted"])
        self.assertTrue(out[0]["_length_retry_succeeded"])
        self.assertEqual(fake.kinds(), ["translate", "rewrite"])

    def test_rewrite_that_stays_long_flags_length_unfit(self):
        long_it = "Questa e' una traduzione davvero troppo lunga per lo slot audio breve."
        fake = _FakeOllama(translate=lambda p: long_it, rewrite=lambda p: long_it)
        seg = _seg("Too long for this.", end=1.0)
        out = self._run([seg], fake)
        self.assertTrue(out[0]["_length_retry_attempted"])
        self.assertFalse(out[0]["_length_retry_succeeded"])
        self.assertIn(FLAG_LENGTH_UNFIT, out[0].get("_quality_flags", []))

    def test_commentary_outlier_is_truncated_to_first_sentence(self):
        rambling = ("Ciao. " + "Nota: questa traduzione contiene un commento lungo " * 6).strip()
        fake = _FakeOllama(translate=lambda p: rambling, rewrite=lambda p: rambling)
        out = self._run([_seg("Hi.", end=20.0)], fake)
        self.assertEqual(out[0]["text_tgt"], "Ciao.")

    def test_negation_triggers_cove_and_accepts_its_correction(self):
        fake = _FakeOllama(translate=lambda p: "Mi piace.", verify=lambda p: "Non mi piace.")
        out = self._run([_seg("I do not like it.")], fake)
        self.assertEqual(fake.kinds(), ["translate", "verify"])
        self.assertEqual(out[0]["text_tgt"], "Non mi piace.")

    def test_cove_disabled_makes_no_verification_call(self):
        fake = _FakeOllama(translate=lambda p: "Mi piace.", verify=lambda p: "Non mi piace.")
        out = self._run([_seg("I do not like it.")], fake, use_cove=False)
        self.assertEqual(fake.kinds(), ["translate"])
        self.assertEqual(out[0]["text_tgt"], "Mi piace.")

    def test_cove_http_error_keeps_first_translation(self):
        fake = _FakeOllama(translate=lambda p: "Non mi piace.",
                           verify=lambda p: RuntimeError("timeout"))
        out = self._run([_seg("I do not like it.")], fake)
        self.assertEqual(out[0]["text_tgt"], "Non mi piace.")


if __name__ == "__main__":
    unittest.main()
