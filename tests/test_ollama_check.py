"""The Ollama Verify button: what it reports, without starting or installing anything."""
import unittest
from unittest import mock

from videotranslator import ollama_runtime as rt

URL = "http://localhost:11434"


class CheckOllamaTests(unittest.TestCase):
    def _check(self, *, running, health=(True, "", "qwen3:14b"), version="0.12.3",
               binary="/usr/bin/ollama", url=URL, model="qwen3:14b"):
        with mock.patch.object(rt, "_ollama_is_daemon_running", return_value=running), \
                mock.patch.object(rt, "_ollama_version", return_value=version), \
                mock.patch.object(rt, "_ollama_health_check", return_value=health) as health_check:
            result = rt.check_ollama(url, model, find_binary=lambda: binary)
        return result, health_check

    def test_answering_with_the_chosen_model_is_ready(self):
        result, _ = self._check(running=True)
        self.assertEqual(result, rt.OllamaCheck("ready", "0.12.3", "qwen3:14b"))

    def test_answering_without_it_names_the_model_that_will_be_used(self):
        result, _ = self._check(running=True,
                                health=(True, "qwen3:14b missing, using qwen3:8b", "qwen3:8b"))
        self.assertEqual(result, rt.OllamaCheck("fallback", "0.12.3", "qwen3:8b"))

    def test_answering_with_no_usable_model_means_a_download_at_first_use(self):
        result, _ = self._check(running=True, health=(False, "No models installed", ""))
        self.assertEqual(result, rt.OllamaCheck("missing", "0.12.3", "qwen3:14b"))

    def test_installed_but_silent_here_will_be_started(self):
        result, health_check = self._check(running=False)
        self.assertEqual(result.state, "stopped")
        health_check.assert_not_called()

    def test_not_installed_here_will_be_installed(self):
        result, _ = self._check(running=False, binary=None)
        self.assertEqual(result.state, "absent")

    def test_a_silent_remote_address_is_just_unreachable(self):
        for url in ("http://192.168.1.20:11434", "http://gpu-box.lan:11434"):
            with self.subTest(url=url):
                result, _ = self._check(running=False, url=url, binary=None)
                self.assertEqual(result.state, "unreachable")

    def test_the_local_addresses_are_recognised(self):
        for url in ("http://127.0.0.1:11434", "http://[::1]:11434", "http://LOCALHOST:11434/"):
            with self.subTest(url=url):
                result, _ = self._check(running=False, url=url, binary=None)
                self.assertEqual(result.state, "absent")

    def test_version_is_read_from_the_api_and_empty_when_it_fails(self):
        response = mock.Mock()
        response.json.return_value = {"version": "0.12.3"}
        with mock.patch("requests.get", return_value=response) as get:
            self.assertEqual(rt._ollama_version(URL), "0.12.3")
        # "localhost" goes out as 127.0.0.1 (platforms.loopback_ipv4)
        self.assertEqual(get.call_args.args[0], "http://127.0.0.1:11434/api/version")
        with mock.patch("requests.get", side_effect=OSError("down")):
            self.assertEqual(rt._ollama_version(URL), "")


if __name__ == "__main__":
    unittest.main()
