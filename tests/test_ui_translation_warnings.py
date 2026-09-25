"""GUI surfacing of translation failures (Google rate limit)."""

import types
import unittest
from unittest import mock

import video_translator_gui as legacy
from videotranslator.quality_flags import FLAG_TRANSLATION_FALLBACK
from videotranslator.translation import TranslationUnavailableError


def _fake_app():
    return types.SimpleNamespace(
        _destroying=False,
        _running=True,
        _progress=mock.Mock(),
        _btn=mock.Mock(),
        _btn_download=mock.Mock(),
        _log_write=mock.Mock(),
        _s=lambda key: legacy.UI_STRINGS["en"][key],
    )


class CountFallbackSegmentsTests(unittest.TestCase):
    def test_counts_only_fallback_flagged_segments(self):
        result = {"segments": [
            {"text_tgt": "a", "_quality_flags": [FLAG_TRANSLATION_FALLBACK]},
            {"text_tgt": "b", "_quality_flags": ["whisper_suspicious"]},
            {"text_tgt": "c"},
            {"text_tgt": "d", "_quality_flags": ["length_unfit", FLAG_TRANSLATION_FALLBACK]},
        ]}
        self.assertEqual(legacy._count_fallback_segments(result), 2)

    def test_tolerates_missing_result(self):
        self.assertEqual(legacy._count_fallback_segments(None), 0)
        self.assertEqual(legacy._count_fallback_segments({}), 0)


class ErrorKeyTests(unittest.TestCase):
    def test_translation_unavailable_has_dedicated_message(self):
        self.assertEqual(
            legacy._error_key_for(TranslationUnavailableError("x")),
            "msg_translation_unavailable",
        )
        self.assertIsNone(legacy._error_key_for(RuntimeError("x")))


class OnDoneDialogTests(unittest.TestCase):
    def _on_done(self, *args):
        app = _fake_app()
        with mock.patch.object(legacy, "messagebox") as box:
            legacy.App._on_done(app, *args)
        return box

    def test_success_without_fallback_shows_info(self):
        box = self._on_done(True)
        box.showinfo.assert_called_once()
        box.showwarning.assert_not_called()

    def test_success_with_fallback_shows_warning_with_count(self):
        box = self._on_done(True, None, 4)
        box.showinfo.assert_not_called()
        box.showwarning.assert_called_once()
        self.assertIn(": 4.", box.showwarning.call_args.args[1])

    def test_failure_uses_specific_message(self):
        box = self._on_done(False, "msg_translation_unavailable")
        self.assertEqual(
            box.showerror.call_args.args[1],
            legacy.UI_STRINGS["en"]["msg_translation_unavailable"],
        )

    def test_failure_without_key_uses_generic_message(self):
        box = self._on_done(False)
        self.assertEqual(
            box.showerror.call_args.args[1], legacy.UI_STRINGS["en"]["msg_error"],
        )


if __name__ == "__main__":
    unittest.main()
