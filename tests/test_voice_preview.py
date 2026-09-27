import ast
import io
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory

from videotranslator import voice_preview as vp

ROOT = Path(__file__).resolve().parents[1]


def _target_languages():
    tree = ast.parse((ROOT / "video_translator_gui.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "LANGUAGES":
            return list(ast.literal_eval(node.value))
    raise AssertionError("LANGUAGES not found")


class SentenceTests(unittest.TestCase):
    def test_every_target_language_has_a_sentence(self):
        self.assertEqual(sorted(_target_languages()), sorted(vp.PREVIEW_SENTENCES))
        for lang, text in vp.PREVIEW_SENTENCES.items():
            self.assertTrue(text.strip(), lang)

    def test_lookup_falls_back_by_base_code_then_english(self):
        self.assertEqual(vp.preview_sentence("it"), vp.PREVIEW_SENTENCES["it"])
        self.assertEqual(vp.preview_sentence("zh"), vp.PREVIEW_SENTENCES["zh-CN"])
        self.assertEqual(vp.preview_sentence("pt-BR"), vp.PREVIEW_SENTENCES["pt"])
        self.assertEqual(vp.preview_sentence("xx"), vp.PREVIEW_SENTENCES["en"])


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FetchTests(unittest.TestCase):
    def test_downloads_https_sample(self):
        seen = {}

        def opener(req, timeout):
            seen["url"], seen["timeout"] = req.full_url, timeout
            return _Resp(b"ID3audio")

        self.assertEqual(vp.fetch_sample("https://x.test/a.mp3", opener=opener), b"ID3audio")
        self.assertEqual(seen["url"], "https://x.test/a.mp3")

    def test_refuses_non_https_and_empty(self):
        for url in ("", "http://x.test/a.mp3", "file:///etc/passwd"):
            with self.assertRaises(vp.PreviewError) as ctx:
                vp.fetch_sample(url, opener=lambda *a, **k: _Resp(b"x"))
            self.assertEqual(ctx.exception.kind, "no_sample")

    def test_network_error_and_size_limit(self):
        def broken(req, timeout):
            raise urllib.error.URLError("down")

        with self.assertRaises(vp.PreviewError) as ctx:
            vp.fetch_sample("https://x.test/a.mp3", opener=broken)
        self.assertEqual(ctx.exception.kind, "network")
        with self.assertRaises(vp.PreviewError) as ctx:
            vp.fetch_sample("https://x.test/a.mp3", opener=lambda r, timeout: _Resp(b"x" * 11),
                            max_bytes=10)
        self.assertEqual(ctx.exception.kind, "failed")


class _Comm:
    def __init__(self, text, voice, rate):
        self.args = (text, voice, rate)
        _Comm.last = self

    async def stream(self):
        yield {"type": "WordBoundary"}
        yield {"type": "audio", "data": b"ab"}
        yield {"type": "audio", "data": b"cd"}


class EdgeTests(unittest.TestCase):
    def test_collects_audio_with_signed_rate(self):
        self.assertEqual(vp.synthesize_edge("ciao", "it-IT-ElsaNeural", -10,
                                            communicate=_Comm), b"abcd")
        self.assertEqual(_Comm.last.args, ("ciao", "it-IT-ElsaNeural", "-10%"))
        vp.synthesize_edge("ciao", "v", 0, communicate=_Comm)
        self.assertEqual(_Comm.last.args[2], "+0%")

    def test_failure_is_a_network_error(self):
        class Broken(_Comm):
            async def stream(self):
                raise OSError("offline")
                yield  # pragma: no cover

        with self.assertRaises(vp.PreviewError) as ctx:
            vp.synthesize_edge("ciao", "v", communicate=Broken)
        self.assertEqual(ctx.exception.kind, "network")


class FakePlayer:
    """Plays for ``duration`` seconds after play(); records calls."""

    def __init__(self, duration=0.3, starts=True):
        self.duration = duration
        self.starts = starts
        self.calls = []
        self.until = 0.0

    def play(self, path):
        self.calls.append(("play", Path(path).read_bytes()))
        self.until = time.monotonic() + self.duration if self.starts else 0.0

    def is_idle(self):
        return time.monotonic() >= self.until

    def stop(self):
        self.calls.append(("stop",))
        self.until = 0.0

    def close(self):
        self.calls.append(("close",))


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.events = []
        self.cond = threading.Condition()

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, player):
        def on_state(key, state, kind):
            with self.cond:
                self.events.append((key, state, kind))
                self.cond.notify_all()

        return vp.VoicePreview(on_state, player_factory=lambda: player,
                               temp_dir=self.tmp.name)

    def wait_for(self, event, timeout=5.0):
        with self.cond:
            ok = self.cond.wait_for(lambda: event in self.events, timeout)
        self.assertTrue(ok, f"{event} not in {self.events}")

    def test_plays_to_the_end_and_cleans_the_file(self):
        player = FakePlayer(0.2)
        preview = self.make(player)
        preview.play("a", lambda: b"mp3")
        self.wait_for(("a", "idle", None))
        self.assertEqual([e[1] for e in self.events], ["loading", "playing", "idle"])
        self.assertEqual(player.calls[0], ("play", b"mp3"))
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
        self.assertIsNone(preview.active_key())
        preview.close()
        self.assertEqual(player.calls[-1], ("close",))

    def test_toggle_same_key_stops(self):
        player = FakePlayer(30)
        preview = self.make(player)
        preview.toggle("a", lambda: b"x")
        self.wait_for(("a", "playing", None))
        self.assertEqual(preview.active_key(), "a")
        preview.toggle("a", lambda: b"x")
        self.wait_for(("a", "idle", None))
        self.assertIn(("stop",), player.calls)
        preview.close()

    def test_other_key_replaces_the_running_one(self):
        player = FakePlayer(30)
        preview = self.make(player)
        preview.toggle("a", lambda: b"one")
        self.wait_for(("a", "playing", None))
        preview.toggle("b", lambda: b"two")
        self.wait_for(("b", "playing", None))
        self.assertIn(("a", "idle", None), self.events)
        self.assertEqual([c for c in player.calls if c[0] == "play"],
                         [("play", b"one"), ("play", b"two")])
        preview.close()

    def test_loader_error_is_reported(self):
        preview = self.make(FakePlayer())

        def loader():
            raise vp.PreviewError("network")

        preview.play("a", loader)
        self.wait_for(("a", "error", "network"))
        preview.play("b", lambda: (_ for _ in ()).throw(ValueError("boom")))
        self.wait_for(("b", "error", "failed"))
        preview.close()

    def test_no_player_is_reported(self):
        def factory():
            raise vp.PreviewError("no_player")

        events = []
        done = threading.Event()
        preview = vp.VoicePreview(
            lambda k, s, kind: (events.append((k, s, kind)), s == "error" and done.set()),
            player_factory=factory, temp_dir=self.tmp.name)
        preview.play("a", lambda: b"x")
        self.assertTrue(done.wait(5))
        self.assertEqual(events[-1], ("a", "error", "no_player"))
        preview.close()

    def test_a_file_that_never_starts_is_an_error(self):
        clock = [0.0]
        player = FakePlayer(starts=False)
        events = []
        done = threading.Event()

        def tick():
            clock[0] += 1.0
            return clock[0]

        preview = vp.VoicePreview(
            lambda k, s, kind: (events.append((k, s, kind)), s == "error" and done.set()),
            player_factory=lambda: player, temp_dir=self.tmp.name, clock=tick)
        preview.play("a", lambda: b"x")
        self.assertTrue(done.wait(5))
        self.assertEqual(events[-1], ("a", "error", "failed"))
        preview.close()

    def test_close_stops_playback_and_ignores_later_requests(self):
        player = FakePlayer(30)
        preview = self.make(player)
        preview.play("a", lambda: b"x")
        self.wait_for(("a", "playing", None))
        preview.close()
        self.assertIn(("close",), player.calls)
        preview.play("b", lambda: b"y")
        preview.toggle("b", lambda: b"y")
        time.sleep(0.1)
        self.assertNotIn(("b", "loading", None), self.events)


class MakePlayerTests(unittest.TestCase):
    def test_prefers_libmpv(self):
        made = {}

        class MPV:
            def __init__(self, **options):
                made["options"] = options

        class Module:
            pass

        Module.MPV = MPV
        player = vp.make_player(sys_platform="linux", load_mpv=lambda: Module,
                                which=lambda name: None)
        self.assertIsInstance(player, vp.MpvPreviewPlayer)
        self.assertEqual(made["options"]["vid"], "no")

    def test_falls_back_to_ffplay_then_errors(self):
        def no_mpv():
            raise RuntimeError("missing")

        player = vp.make_player(sys_platform="win32", load_mpv=no_mpv,
                                which=lambda name: "/usr/bin/ffplay")
        self.assertIsInstance(player, vp.FfplayPreviewPlayer)
        with self.assertRaises(vp.PreviewError) as ctx:
            vp.make_player(sys_platform="linux", load_mpv=no_mpv, which=lambda name: None)
        self.assertEqual(ctx.exception.kind, "no_player")

    def test_ffplay_runs_hidden_and_stops(self):
        calls = []

        class Proc:
            def __init__(self):
                self.code = None

            def poll(self):
                return self.code

            def terminate(self):
                calls.append("terminate")
                self.code = 0

            def wait(self, timeout):
                return 0

        proc = Proc()

        def popen(args, **kwargs):
            calls.append((args, kwargs.get("creationflags")))
            return proc

        player = vp.FfplayPreviewPlayer("ffplay", sys_platform="win32", popen=popen)
        player.play("/tmp/a.mp3")
        self.assertFalse(player.is_idle())
        args, flags = calls[0]
        self.assertEqual(args[:5], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"])
        self.assertEqual(flags, 0x08000000)
        player.stop()
        self.assertTrue(player.is_idle())
        self.assertIn("terminate", calls)


if __name__ == "__main__":
    unittest.main()
