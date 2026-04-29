import unittest

from videotranslator.jobs import PipelineProgressEvent, TranslationJobConfig
from videotranslator.pipeline import run_translation_job


class TranslationJobConfigTests(unittest.TestCase):
    def test_to_translate_video_kwargs_preserves_core_fields(self):
        cfg = TranslationJobConfig(
            video_in="input.mp4",
            output="out.mp4",
            translation_engine="llm_ollama",
            hotwords=["Strix", "Docker"],
            ollama_use_cove=False,
        )

        kwargs = cfg.to_translate_video_kwargs()

        self.assertEqual(kwargs["video_in"], "input.mp4")
        self.assertEqual(kwargs["output"], "out.mp4")
        self.assertEqual(kwargs["translation_engine"], "llm_ollama")
        self.assertEqual(kwargs["hotwords"], ["Strix", "Docker"])
        self.assertFalse(kwargs["ollama_use_cove"])


class PipelineWrapperTests(unittest.TestCase):
    def test_run_translation_job_calls_runner_with_config_kwargs(self):
        seen = {}

        def runner(**kwargs):
            seen.update(kwargs)
            return {"output": "dubbed.mp4"}

        result = run_translation_job(
            TranslationJobConfig(video_in="input.mp4", model="base"),
            runner=runner,
        )

        self.assertEqual(seen["video_in"], "input.mp4")
        self.assertEqual(seen["model"], "base")
        self.assertEqual(result.output_path, "dubbed.mp4")

    def test_run_translation_job_emits_start_and_done_events(self):
        events: list[PipelineProgressEvent] = []

        run_translation_job(
            TranslationJobConfig(video_in="input.mp4"),
            runner=lambda **_kwargs: {},
            progress_cb=events.append,
        )

        self.assertEqual([e.stage for e in events], ["start", "done"])
        self.assertEqual(events[0].message, "input.mp4")
        self.assertEqual(events[-1].current, 1)


if __name__ == "__main__":
    unittest.main()
