import unittest

from videotranslator.wav2lip_runtime import (
    WAV2LIP_BASE_REQUIREMENTS,
    WAV2LIP_FACE_REQUIREMENTS,
    missing_runtime_packages,
    missing_wav2lip_base_packages,
    missing_wav2lip_face_packages,
    module_present,
    wav2lip_face_stack_ready,
)


def _fake_find_spec(present: set[str]):
    def find_spec(name: str):
        if name == "raises":
            raise ModuleNotFoundError(name)
        return object() if name in present else None

    return find_spec


class Wav2LipRuntimeTests(unittest.TestCase):
    def test_module_present_handles_missing_and_import_errors(self):
        self.assertTrue(module_present("cv2", find_spec=_fake_find_spec({"cv2"})))
        self.assertFalse(module_present("missing", find_spec=_fake_find_spec(set())))
        self.assertFalse(module_present("raises", find_spec=_fake_find_spec(set())))

    def test_missing_base_packages_returns_pip_names(self):
        missing = missing_wav2lip_base_packages(
            find_spec=_fake_find_spec({"cv2", "tqdm"})
        )

        self.assertEqual(missing, ["librosa"])

    def test_missing_face_packages_maps_basicsr_to_new_basicsr(self):
        missing = missing_wav2lip_face_packages(
            find_spec=_fake_find_spec({"dlib"})
        )

        self.assertEqual(missing, ["facexlib", "new-basicsr"])

    def test_face_stack_ready_requires_all_face_modules(self):
        present = {"dlib", "facexlib", "basicsr"}

        self.assertTrue(
            wav2lip_face_stack_ready(find_spec=_fake_find_spec(present))
        )
        self.assertFalse(
            wav2lip_face_stack_ready(find_spec=_fake_find_spec({"dlib"}))
        )

    def test_requirement_sets_are_non_empty(self):
        self.assertTrue(WAV2LIP_BASE_REQUIREMENTS)
        self.assertTrue(WAV2LIP_FACE_REQUIREMENTS)
        self.assertEqual(
            missing_runtime_packages((), find_spec=_fake_find_spec(set())),
            [],
        )


if __name__ == "__main__":
    unittest.main()


class Wav2LipModelDownloadTests(unittest.TestCase):
    """torch.load unpickles the weights: only a file with the pinned hash may land."""

    class _Http:
        def __init__(self, payload: bytes):
            self.payload = payload
            self.urls = []

        def fetch(self, url, dest, *, max_bytes):
            import hashlib
            self.urls.append((url, max_bytes))
            dest.write_bytes(self.payload)
            return hashlib.sha256(self.payload).hexdigest()

    def test_a_tampered_model_is_refused_and_leaves_nothing_behind(self):
        import tempfile
        from pathlib import Path
        from videotranslator.libmpv_runtime import DownloadError
        from videotranslator.wav2lip_runtime import WAV2LIP_MODEL_URL, download_wav2lip_model
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "wav2lip_gan.pth"
            http = self._Http(b"not the real weights")
            with self.assertRaises(DownloadError):
                download_wav2lip_model(dest, http=http)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(http.urls[0][0], WAV2LIP_MODEL_URL)

    def test_the_pinned_hash_matches_the_windows_installer(self):
        import re
        from pathlib import Path
        from videotranslator.wav2lip_runtime import WAV2LIP_MODEL_SHA256
        bat = (Path(__file__).resolve().parents[1] / "setup_windows.bat").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'WAV2LIP_SHA256=([0-9a-f]{64})', bat).group(1),
                         WAV2LIP_MODEL_SHA256)
