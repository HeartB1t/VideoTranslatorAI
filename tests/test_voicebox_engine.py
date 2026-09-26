import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path

from videotranslator import voicebox_engine as vb


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeVoicebox:
    """In-memory stand-in for the Voicebox REST API."""

    def __init__(self, *, down=False, fail_generate=False):
        self.down, self.fail_generate = down, fail_generate
        self.profiles, self.samples, self.generated, self.deleted = {}, [], [], []

    def __call__(self, req, timeout):
        if self.down:
            raise urllib.error.URLError("Connection refused")
        path = req.full_url.split("17493", 1)[1]
        method = req.get_method()
        if (method, path) == ("GET", "/health"):
            return _Resp(json.dumps({"status": "healthy", "gpu_available": True,
                                     "gpu_type": "CUDA"}).encode())
        if (method, path) == ("POST", "/profiles"):
            body = json.loads(req.data)
            pid = f"p{len(self.profiles) + 1}"
            self.profiles[pid] = body
            return _Resp(json.dumps({"id": pid}).encode())
        if method == "POST" and path.endswith("/samples"):
            self.samples.append((path.split("/")[2], req.get_header("Content-type"), req.data))
            return _Resp(b"{}")
        if (method, path) == ("POST", "/generate/stream"):
            body = json.loads(req.data)
            if self.fail_generate:
                raise urllib.error.HTTPError(req.full_url, 500, "boom", {},
                                             io.BytesIO(b'{"detail": "CUDA error"}'))
            self.generated.append(body)
            return _Resp(b"RIFF....WAVEfmt ")
        if method == "DELETE" and path.startswith("/profiles/"):
            self.deleted.append(path.split("/")[2])
            return _Resp(b"{}")
        raise AssertionError(f"unexpected {method} {path}")


def _segments():
    return [{"text_tgt": "Ciao a tutti.", "speaker": "SPEAKER_00"},
            {"text_tgt": "  ", "speaker": "SPEAKER_00"},
            {"text_tgt": "Seconda voce.", "speaker": "SPEAKER_01"}]


class ClientTests(unittest.TestCase):
    def test_only_loopback_addresses(self):
        self.assertTrue(vb.is_local_url("http://127.0.0.1:17493"))
        self.assertTrue(vb.is_local_url("http://localhost:17600"))
        self.assertFalse(vb.is_local_url("http://192.168.1.10:17493"))
        with self.assertRaises(vb.VoiceboxError):
            vb.VoiceboxClient("http://10.0.0.2:17493")

    def test_language_support(self):
        self.assertTrue(vb.supports_language("it"))
        self.assertTrue(vb.supports_language("pt-BR"))
        self.assertFalse(vb.supports_language("vi"))

    def test_sample_upload_is_multipart_with_the_reference_text(self):
        fake = _FakeVoicebox()
        client = vb.VoiceboxClient(opener=fake)
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "ref.wav"
            wav.write_bytes(b"RIFFdata")
            client.add_sample("p1", str(wav), "ciao mondo")
        pid, ctype, body = fake.samples[0]
        self.assertEqual(pid, "p1")
        self.assertTrue(ctype.startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="reference_text"\r\n\r\nciao mondo', body)
        self.assertIn(b'name="file"; filename="ref.wav"', body)
        self.assertIn(b"RIFFdata", body)

    def test_errors_are_classified(self):
        with self.assertRaises(vb.VoiceboxError) as ctx:
            vb.VoiceboxClient(opener=_FakeVoicebox(down=True)).health()
        self.assertEqual(ctx.exception.kind, "unreachable")
        with self.assertRaises(vb.VoiceboxError) as ctx:
            vb.VoiceboxClient(opener=_FakeVoicebox(fail_generate=True)).generate(
                "p", "x", "it", engine="chatterbox")
        self.assertEqual(ctx.exception.kind, "server")
        self.assertIn("CUDA error", str(ctx.exception))

    def test_describe_health(self):
        self.assertEqual(vb.describe_health({"gpu_available": True, "gpu_type": "CUDA"}),
                         "CUDA")
        self.assertEqual(vb.describe_health({"gpu_available": False}), "CPU")


class GenerateTests(unittest.TestCase):
    def _run(self, fake, *, diar=None, lang="it", transcript="testo di prova",
             reference_ok=True):
        logs = []
        with tempfile.TemporaryDirectory() as tmp:
            def build_reference(src, out, **kw):
                if not reference_ok:
                    return None
                Path(out).write_bytes(b"RIFFref")
                return out

            def speaker_reference(src, diar_segments, spk, tmp_dir):
                path = os.path.join(tmp_dir, f"ref_{spk}.wav")
                Path(path).write_bytes(b"RIFFspk")
                return path

            files = vb.generate_tts_voicebox(
                _segments(), "/vocals.wav", lang, tmp, diar_segments=diar,
                client=vb.VoiceboxClient(opener=fake), build_reference=build_reference,
                speaker_reference=speaker_reference,
                transcribe=lambda path, lang_: transcript,
                log=lambda *a, **k: logs.append(a[0]))
            existing = [os.path.exists(f) for f in files] if files else None
        return files, existing, logs

    def test_clones_generates_and_cleans_up(self):
        fake = _FakeVoicebox()
        files, existing, _ = self._run(fake)
        self.assertEqual([Path(f).name for f in files],
                         ["seg_0000.wav", "seg_0001.wav", "seg_0002.wav"])
        self.assertEqual(existing, [True, False, True])       # empty sentence skipped
        self.assertEqual(len(fake.profiles), 1)
        self.assertEqual(fake.profiles["p1"]["language"], "it")
        self.assertEqual([g["text"] for g in fake.generated],
                         ["Ciao a tutti.", "Seconda voce."])
        self.assertEqual({g["engine"] for g in fake.generated}, {"chatterbox"})
        self.assertEqual(fake.deleted, ["p1"])                  # temporary profile removed

    def test_one_profile_per_speaker_with_diarization(self):
        fake = _FakeVoicebox()
        diar = [{"speaker": "SPEAKER_00", "start": 0, "end": 5},
                {"speaker": "SPEAKER_01", "start": 5, "end": 9}]
        self._run(fake, diar=diar)
        self.assertEqual(len(fake.profiles), 3)                 # global + 2 speakers
        self.assertEqual([g["profile_id"] for g in fake.generated], ["p2", "p3"])
        self.assertEqual(sorted(fake.deleted), ["p1", "p2", "p3"])

    def test_unreachable_server_falls_back(self):
        files, _, logs = self._run(_FakeVoicebox(down=True))
        self.assertIsNone(files)
        self.assertTrue(any("not available" in line for line in logs))

    def test_generation_error_falls_back_and_still_cleans_up(self):
        fake = _FakeVoicebox(fail_generate=True)
        files, _, logs = self._run(fake)
        self.assertIsNone(files)
        self.assertEqual(fake.deleted, ["p1"])
        self.assertTrue(any("falling back to Edge-TTS" in line for line in logs))

    def test_unsupported_language_or_no_sample_falls_back(self):
        self.assertIsNone(self._run(_FakeVoicebox(), lang="vi")[0])
        self.assertIsNone(self._run(_FakeVoicebox(), reference_ok=False)[0])
        self.assertIsNone(self._run(_FakeVoicebox(), transcript="")[0])


if __name__ == "__main__":
    unittest.main()
