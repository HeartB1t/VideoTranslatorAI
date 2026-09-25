"""What the GUI workers report to ``_on_done`` and ``_open_editor``.

The worker threads run inline (``threading.Thread`` patched) and ``after``
calls its callback at once, so these tests need no display, no Tk event
loop and no ML stack.
"""

import os
import types
import unittest
from unittest import mock

import video_translator_gui as legacy
from videotranslator.jobs import TranslationJobConfig
from videotranslator.quality_flags import FLAG_TRANSLATION_FALLBACK
from videotranslator.translation import TranslationUnavailableError

UNAVAILABLE = "msg_translation_unavailable"


class _InlineThread:
    def __init__(self, target, daemon=None):
        self._target = target

    def start(self):
        self._target()


def _result(fallback_segments, clean_segments=1):
    segments = [
        {"text_tgt": "x", "_quality_flags": [FLAG_TRANSLATION_FALLBACK]}
        for _ in range(fallback_segments)
    ]
    segments += [{"text_tgt": "y"} for _ in range(clean_segments)]
    return {"segments": segments}


def _fake_app():
    app = types.SimpleNamespace(
        _running=False,
        _btn=mock.Mock(),
        _btn_download=mock.Mock(),
        _progress=mock.Mock(),
        _log=mock.Mock(),
        _log_write=mock.Mock(),
        _edit_subs=types.SimpleNamespace(get=lambda: False),
        _snapshot_params=lambda: TranslationJobConfig(video_in=""),
        _s=lambda key: legacy.UI_STRINGS["en"][key],
        _on_done=mock.Mock(),
        _open_editor=mock.Mock(),
        _cleanup_editor_tempfile=mock.Mock(),
    )
    app.after = lambda _delay, callback, *args: callback(*args)
    return app


class _WorkerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = _fake_app()
        patcher = mock.patch.object(legacy.threading, "Thread", _InlineThread)
        patcher.start()
        self.addCleanup(patcher.stop)

    def on_done_args(self):
        self.app._on_done.assert_called_once()
        return self.app._on_done.call_args.args


class BatchWorkerTests(_WorkerTestCase):
    def run_batch(self, *outcomes):
        """One file per outcome: what ``translate_video`` returns or raises."""
        files = [f"/videos/clip{i}.mp4" for i in range(len(outcomes))]
        with mock.patch.object(legacy, "translate_video", side_effect=list(outcomes)):
            legacy.App._run_batch(self.app, files)
        return self.on_done_args()

    def test_success_sums_fallback_segments_across_files(self):
        self.assertEqual(
            self.run_batch(_result(2), _result(0), _result(3)), (True, None, 5),
        )

    def test_translation_unavailable_uses_dedicated_message(self):
        self.assertEqual(
            self.run_batch(TranslationUnavailableError("rate limited")),
            (False, UNAVAILABLE, 0),
        )

    def test_same_error_on_every_failed_file_keeps_dedicated_message(self):
        self.assertEqual(
            self.run_batch(
                TranslationUnavailableError("rate limited"),
                _result(1),
                TranslationUnavailableError("rate limited"),
            ),
            (False, UNAVAILABLE, 1),
        )

    def test_mixed_errors_use_generic_message(self):
        orders = (
            (TranslationUnavailableError("rate limited"), RuntimeError("disk full")),
            (RuntimeError("disk full"), TranslationUnavailableError("rate limited")),
        )
        for outcomes in orders:
            with self.subTest(first=type(outcomes[0]).__name__):
                self.app = _fake_app()
                self.assertEqual(self.run_batch(*outcomes), (False, None, 0))


class UrlWorkerTests(_WorkerTestCase):
    def run_urls(self, urls, translate_outcomes):
        """Download every URL (those containing "broken" raise), then feed
        ``translate_outcomes`` to ``translate_video`` in order."""
        def fake_download(url, out_dir):
            if "broken" in url:
                raise OSError("network down")
            path = os.path.join(out_dir, "video.mp4")
            with open(path, "wb") as fh:
                fh.write(b"\0")
            return path

        with mock.patch.object(legacy, "download_youtube", side_effect=fake_download), \
                mock.patch.object(legacy, "translate_video",
                                  side_effect=list(translate_outcomes)) as translate:
            legacy.App._dispatch_download(self.app, urls)
        for call in translate.call_args_list:
            self.assertFalse(os.path.exists(call.kwargs["video_in"]))
        return self.on_done_args()

    def test_success_sums_fallback_segments_across_urls(self):
        self.assertEqual(
            self.run_urls(["https://example.invalid/a", "https://example.invalid/b"],
                          [_result(1), _result(4)]),
            (True, None, 5),
        )

    def test_translation_unavailable_uses_dedicated_message(self):
        self.assertEqual(
            self.run_urls(["https://example.invalid/a"],
                          [TranslationUnavailableError("rate limited")]),
            (False, UNAVAILABLE, 0),
        )

    def test_mixed_translation_errors_use_generic_message(self):
        self.assertEqual(
            self.run_urls(["https://example.invalid/a", "https://example.invalid/b"],
                          [TranslationUnavailableError("rate limited"),
                           RuntimeError("disk full")]),
            (False, None, 0),
        )

    def test_download_failure_next_to_unavailable_translation_is_generic(self):
        self.assertEqual(
            self.run_urls(["https://example.invalid/broken", "https://example.invalid/b"],
                          [TranslationUnavailableError("rate limited")]),
            (False, None, 0),
        )


class EditorPhaseOneTests(_WorkerTestCase):
    VIDEO = "/videos/clip.mp4"
    CLEANUP = "/downloads/yt_clip.mp4"

    def run_phase1(self, outcome):
        with mock.patch.object(legacy, "translate_video", side_effect=[outcome]):
            legacy.App._start_with_editor(self.app, self.VIDEO, self.CLEANUP)

    def test_fallback_count_is_forwarded_to_the_editor(self):
        result = _result(3, clean_segments=2)
        self.run_phase1(result)
        self.app._open_editor.assert_called_once_with(
            self.VIDEO, result["segments"], self.CLEANUP, 3,
        )
        self.app._on_done.assert_not_called()

    def test_translation_unavailable_key_is_forwarded_to_on_done(self):
        self.run_phase1(TranslationUnavailableError("rate limited"))
        self.app._on_done.assert_called_once_with(False, UNAVAILABLE)
        self.app._open_editor.assert_not_called()
        self.app._cleanup_editor_tempfile.assert_called_once_with(self.CLEANUP)

    def test_other_error_uses_generic_message(self):
        self.run_phase1(RuntimeError("disk full"))
        self.app._on_done.assert_called_once_with(False, None)


if __name__ == "__main__":
    unittest.main()
