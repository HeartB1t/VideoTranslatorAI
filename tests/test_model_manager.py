import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from videotranslator import model_manager as mm


def _info(files):
    """Fake Hub metadata: {name: (bytes, lfs)}."""
    siblings = []
    for name, (data, lfs) in files.items():
        if lfs:
            siblings.append(SimpleNamespace(rfilename=name, blob_id="x", lfs=SimpleNamespace(
                sha256=hashlib.sha256(data).hexdigest())))
        else:
            blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
            siblings.append(SimpleNamespace(rfilename=name, blob_id=blob, lfs=None))
    return SimpleNamespace(siblings=siblings)


class CacheTests(unittest.TestCase):
    def test_cached_models_follow_the_weights_lookup(self):
        def lookup(repo, name):
            return "/c/snapshots/abc/model.bin" if repo.endswith("-small") else None
        self.assertEqual(mm.cached_whisper_models(lookup=lookup), {"small"})
        self.assertEqual(mm.whisper_snapshot_dir("small", lookup=lookup),
                         Path("/c/snapshots/abc"))
        self.assertIsNone(mm.whisper_snapshot_dir("nope", lookup=lookup))

    def test_downloaded_mb_counts_partial_blobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            blobs = mm.repo_cache_dir("org/m", root=Path(tmp)) / "blobs"
            blobs.mkdir(parents=True)
            (blobs / "a").write_bytes(b"x" * 1024 * 1024)
            (blobs / "b.incomplete").write_bytes(b"x" * 512 * 1024)
            self.assertAlmostEqual(mm.downloaded_mb("org/m", root=Path(tmp)), 1.5)
            self.assertEqual(mm.downloaded_mb("org/none", root=Path(tmp)), 0.0)


# What faster-whisper downloads for Systran/faster-whisper-small.
COMPLETE = {"model.bin": (b"weights", True), "config.json": (b"{}", False),
            "tokenizer.json": (b'{"t": 1}', False), "vocabulary.txt": (b"a\nb\n", False)}


class VerifyTests(unittest.TestCase):
    def _snapshot(self, tmp, files):
        snap = Path(tmp) / "abc123"
        snap.mkdir()
        for name, (data, _lfs) in files.items():
            (snap / name).write_bytes(data)
        return snap

    def _verify(self, snap, hub_files):
        return mm.verify_snapshot("org/m", snap, model_info=lambda r, rev: _info(hub_files))

    def test_matching_files_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = self._snapshot(tmp, COMPLETE)
            seen = []
            bad = mm.verify_snapshot("org/m", snap, model_info=lambda r, rev: (
                seen.append(rev), _info(COMPLETE))[1])
            self.assertEqual(bad, [])
            self.assertEqual(seen, ["abc123"])          # checked at its own commit

    def test_large_v3_layout_passes(self):
        # vocabulary.json instead of .txt, plus the preprocessor config.
        files = {**{k: v for k, v in COMPLETE.items() if k != "vocabulary.txt"},
                 "vocabulary.json": (b'["a"]', False),
                 "preprocessor_config.json": (b'{"n_mels": 128}', False)}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify(self._snapshot(tmp, files), files), [])

    def test_files_outside_the_download_are_ignored(self):
        hub = {**COMPLETE, "README.md": (b"# m", False), ".gitattributes": (b"*", False)}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify(self._snapshot(tmp, COMPLETE), hub), [])

    def test_corrupted_files_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = self._snapshot(tmp, COMPLETE)
            (snap / "model.bin").write_bytes(b"broken")
            (snap / "config.json").write_bytes(b"{ }")
            self.assertEqual(sorted(self._verify(snap, COMPLETE)), ["config.json", "model.bin"])

    def test_missing_weights_fail(self):
        local = {k: v for k, v in COMPLETE.items() if k != "model.bin"}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify(self._snapshot(tmp, local), COMPLETE), ["model.bin"])

    def test_valid_weights_without_config_fail(self):
        local = {k: v for k, v in COMPLETE.items() if k != "config.json"}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify(self._snapshot(tmp, local), COMPLETE), ["config.json"])

    def test_empty_metadata_proves_nothing(self):
        # Weights on disk but no Hub listing: nothing was checked, so every
        # required file is reported instead of an empty "all good" list.
        with tempfile.TemporaryDirectory() as tmp:
            snap = self._snapshot(tmp, COMPLETE)
            for info in (SimpleNamespace(siblings=[]), SimpleNamespace(siblings=None),
                         SimpleNamespace()):
                with self.subTest(info=info):
                    bad = mm.verify_snapshot("org/m", snap, model_info=lambda r, rev: info)
                    self.assertEqual(bad, list(mm.REQUIRED_FILES))

    def test_metadata_missing_a_required_file_fails(self):
        hub = {k: v for k, v in COMPLETE.items() if k != "config.json"}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._verify(self._snapshot(tmp, COMPLETE), hub), ["config.json"])

    def test_a_file_without_a_hash_fails(self):
        info = _info(COMPLETE)
        for sibling in info.siblings:
            if sibling.rfilename == "tokenizer.json":
                sibling.blob_id = None
        with tempfile.TemporaryDirectory() as tmp:
            snap = self._snapshot(tmp, COMPLETE)
            self.assertEqual(mm.verify_snapshot("org/m", snap, model_info=lambda r, rev: info),
                             ["tokenizer.json"])

    def test_the_required_files_are_part_of_the_download(self):
        import fnmatch
        for required in mm.REQUIRED_FILES:
            with self.subTest(required=required):
                self.assertTrue(any(fnmatch.fnmatch(required, pattern)
                                    for pattern in mm.DOWNLOADED_FILES))


class _Proc:
    def __init__(self, rc=0, err=b"", block=None):
        self.returncode = rc
        self._err = err
        self._block = block
        self.terminated = False

    def communicate(self):
        if self._block is not None:
            self._block.wait(5)
        return b"", self._err

    def terminate(self):
        self.terminated = True
        if self._block is not None:
            self.returncode = -15
            self._block.set()


class DownloadTests(unittest.TestCase):
    def _dl(self, proc, *, bad=(), snapshot=Path("/snap/abc")):
        calls = []

        def popen(cmd, **kw):
            calls.append(cmd)
            return proc
        dl = mm.WhisperDownload("small", popen=popen, verify=lambda r, s: list(bad),
                                snapshot_dir=lambda k: snapshot, python="py")
        return dl, calls

    def test_success_is_verified(self):
        dl, calls = self._dl(_Proc())
        dl.start()
        dl.join(5)
        self.assertEqual((dl.state, dl.error), ("done", ""))
        self.assertEqual(calls[0][0], "py")
        self.assertEqual(calls[0][-1], "small")

    def test_checksum_mismatch_fails(self):
        dl, _ = self._dl(_Proc(), bad=["model.bin"])
        dl.start()
        dl.join(5)
        self.assertEqual(dl.state, "failed")
        self.assertIn("model.bin", dl.error)

    def test_process_error_fails_with_its_last_line(self):
        dl, _ = self._dl(_Proc(rc=1, err=b"Traceback\nConnectionError: offline\n"))
        dl.start()
        dl.join(5)
        self.assertEqual((dl.state, dl.error), ("failed", "ConnectionError: offline"))

    def test_cancel_terminates_the_process(self):
        proc = _Proc(block=threading.Event())
        dl, _ = self._dl(proc)
        dl.start()
        for _ in range(100):
            if dl._proc is not None:
                break
            threading.Event().wait(0.01)
        dl.cancel()
        dl.join(5)
        self.assertTrue(proc.terminated)
        self.assertEqual(dl.state, "cancelled")

    def test_missing_snapshot_after_download_fails(self):
        dl, _ = self._dl(_Proc(), snapshot=None)
        dl.start()
        dl.join(5)
        self.assertEqual(dl.state, "failed")


class _Model:
    def __init__(self, key, device, compute_type):
        self.args = (key, device, compute_type)

    def transcribe(self, audio, **kw):
        return iter([1, 2, 3]), None


class BenchmarkTests(unittest.TestCase):
    def _clock(self):
        ticks = iter(range(100))
        return lambda: float(next(ticks))

    def test_measures_load_first_segment_and_realtime_factor(self):
        import numpy as np
        res = mm.benchmark_whisper("small", "/v.mp4", seconds=10, use_gpu=False,
                                   model_cls=_Model,
                                   read_audio=lambda p, s: np.zeros(160000, np.float32),
                                   clock=self._clock())
        self.assertEqual((res.model, res.device, res.audio_s), ("small", "cpu", 10.0))
        self.assertEqual((res.load_s, res.first_segment_s), (1.0, 1.0))
        self.assertAlmostEqual(res.realtime_factor, res.total_s / 10.0)

    def test_cancel_returns_none(self):
        import numpy as np
        cancel = threading.Event()
        cancel.set()
        self.assertIsNone(mm.benchmark_whisper(
            "small", "/v.mp4", use_gpu=False, model_cls=_Model, cancel=cancel,
            read_audio=lambda p, s: np.zeros(16000, np.float32)))

    def test_empty_audio_is_an_error(self):
        import numpy as np
        with self.assertRaises(ValueError):
            mm.benchmark_whisper("small", "/v.mp4", use_gpu=False, model_cls=_Model,
                                 read_audio=lambda p, s: np.zeros(0, np.float32))


if __name__ == "__main__":
    unittest.main()
