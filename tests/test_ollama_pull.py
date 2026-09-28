"""Pulling an Ollama model: one advancing progress line, not hundreds.

On a Windows VM the output of `ollama pull` (a block of lines redrawn with
cursor codes) became hundreds of repeated "pulling manifest" / "verifying
sha256 digest" log lines. The pull now goes through the daemon's
`/api/pull` JSON stream; the CLI stays as the fallback when it cannot.
"""
import json
import unittest
from unittest import mock

import requests

from videotranslator import ollama_runtime as rt

URL = "http://localhost:11434"
BIG, SMALL = "sha256:a3de86cd1c13", "sha256:ae370d884f10"


class _Stream:
    def __init__(self, events, status_code=200):
        self.status_code = status_code
        self._lines = [json.dumps(e).encode() for e in events]

    def iter_lines(self):
        yield from self._lines

    def json(self):
        return json.loads(self._lines[0])

    def close(self):
        pass


def typical_pull():
    events = [{"status": "pulling manifest"}]
    for done in range(0, 5_200_000_001, 104_000_000):          # 51 ticks of the big layer
        events.append({"status": f"pulling {BIG[7:19]}", "digest": BIG,
                       "total": 5_200_000_000, "completed": done})
    events.append({"status": f"pulling {SMALL[7:19]}", "digest": SMALL,
                   "total": 1_200, "completed": 1_200})
    events += [{"status": "verifying sha256 digest"}] * 40       # repeated, as the daemon does
    events += [{"status": "writing manifest"}, {"status": "success"}]
    return events


class PullTests(unittest.TestCase):
    def setUp(self):
        self.logged = []

    def _pull(self, stream=None, post_error=None):
        post = mock.Mock(side_effect=post_error) if post_error else mock.Mock(return_value=stream)
        with mock.patch("requests.post", post), \
                mock.patch.object(rt.subprocess, "Popen",
                                  side_effect=OSError("cli not run")) as popen:
            result = rt._ollama_pull_model("qwen3:8b", binary="/usr/bin/ollama",
                                           log_cb=self.logged.append, api_url=URL)
        return result, post, popen

    def test_a_pull_is_one_progress_line_plus_each_status_once(self):
        (ok, message), post, popen = self._pull(_Stream(typical_pull()))
        self.assertEqual((ok, message), (True, ""))
        popen.assert_not_called()
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:11434/api/pull")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen3:8b")
        progress = [text for text in self.logged if "%" in text]
        self.assertTrue(all(text.startswith("\r") and not text.endswith("\n")
                            for text in progress))
        self.assertIn("100%", progress[-1])
        text = "".join(self.logged)
        for status in ("pulling manifest", "verifying sha256 digest", "writing manifest",
                       "success"):
            with self.subTest(status=status):
                self.assertEqual(text.count(status), 1)
        # Every "\r" rewrite collapses on screen: count the lines that stay.
        self.assertLessEqual(text.replace("\r", "").count("\n"), 8)

    def test_an_error_from_the_daemon_fails_with_its_message(self):
        (ok, message), _post, popen = self._pull(_Stream([
            {"status": "pulling manifest"},
            {"error": "pull model manifest: file does not exist"}]))
        self.assertFalse(ok)
        self.assertIn("file does not exist", message)
        popen.assert_not_called()

    def test_a_refused_request_fails_with_the_daemon_message(self):
        (ok, message), _post, popen = self._pull(
            _Stream([{"error": "model 'nope' not found"}], status_code=404))
        self.assertFalse(ok)
        self.assertIn("not found", message)
        popen.assert_not_called()

    def test_a_stream_that_stops_before_success_is_a_failure(self):
        events = typical_pull()[:20]
        (ok, message), _post, _popen = self._pull(_Stream(events))
        self.assertFalse(ok)
        self.assertTrue("".join(self.logged).endswith("\n"))   # the progress line is closed

    def test_without_the_api_it_falls_back_to_the_cli(self):
        (ok, message), _post, popen = self._pull(
            post_error=requests.ConnectionError("refused"))
        popen.assert_called_once()
        self.assertFalse(ok)                                     # the fake CLI cannot run
        self.assertIn("ollama pull", message)


if __name__ == "__main__":
    unittest.main()
