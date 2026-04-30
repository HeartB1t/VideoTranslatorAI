import os
import tempfile
import unittest
from pathlib import Path

from videotranslator.pipeline_runner import PipelineRuntime, translate_video


def _unused(*_args, **_kwargs):
    raise AssertionError("unexpected runtime call")


class PipelineRunnerTests(unittest.TestCase):
    def test_segments_override_subs_only_uses_injected_runtime(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = os.path.join(tmp_dir, "input.mp4")
            output_path = os.path.join(tmp_dir, "out.mp4")
            Path(video_path).write_bytes(b"fake")

            def extract_audio(_video_in, audio_raw):
                Path(audio_raw).write_bytes(b"audio")

            def run_ffmpeg(cmd, **_kwargs):
                Path(cmd[-1]).write_bytes(b"resampled")

            def save_subtitles(segments, output_base):
                with open(output_base + ".srt", "w", encoding="utf-8") as fh:
                    fh.write(segments[0]["text_tgt"])

            runtime = PipelineRuntime(
                languages={"it": {"voices": ["it-IT-TestNeural"]}},
                lang_expansion={"it": 1.0, "en": 1.0},
                suggest_xtts_speed=lambda *_args: (1.25, 1.0, True),
                default_videos_dir=lambda: Path(tmp_dir),
                extract_audio=extract_audio,
                separate_audio=_unused,
                run_ffmpeg=run_ffmpeg,
                transcribe=_unused,
                split_on_punctuation=_unused,
                diarize_audio=_unused,
                assign_speakers=_unused,
                merge_short_segments=_unused,
                repair_split_sentences=_unused,
                expand_tight_slots=_unused,
                add_quality_flag=_unused,
                flag_whisper_suspicious="whisper_suspicious",
                estimate_p90_ratio=_unused,
                tts_speed_factor_for=_unused,
                classify_difficulty=_unused,
                resolve_difficulty_profile=_unused,
                format_profile_log=_unused,
                translate_segments=_unused,
                save_subtitles=save_subtitles,
                generate_tts_cosyvoice=_unused,
                generate_tts_xtts=_unused,
                generate_tts=_unused,
                get_duration=_unused,
                build_dubbed_track=_unused,
                mux_video=_unused,
                has_enough_faces=_unused,
                apply_lipsync=_unused,
            )

            result = translate_video(
                video_path,
                output=output_path,
                lang_target="it",
                no_demucs=True,
                subs_only=True,
                segments_override=[
                    {"start": 0.0, "end": 1.0, "text_src": "hello", "text_tgt": "ciao"}
                ],
                difficulty_profile_enabled=False,
                runtime=runtime,
            )

            self.assertEqual(result["srt"], os.path.join(tmp_dir, "out.srt"))
            self.assertEqual(result["segments"][0]["text_tgt"], "ciao")
            self.assertTrue(os.path.exists(result["srt"]))


if __name__ == "__main__":
    unittest.main()
