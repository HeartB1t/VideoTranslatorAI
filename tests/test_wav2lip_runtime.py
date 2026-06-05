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
