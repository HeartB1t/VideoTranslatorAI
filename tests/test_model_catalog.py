import unittest

from videotranslator.hardware_profile import GpuInfo, HardwareInfo
from videotranslator.model_catalog import MT, PREFERENCES, TTS, WHISPER, assess, recommend


def _hw(*, vram=None, ram=32.0, cores=16, disk=200.0, driver_only=False):
    gpus = ()
    if vram is not None:
        gpus = (GpuInfo("GPU", vram, "nvidia" if driver_only else "cuda"),)
    return HardwareInfo("Linux", "CPU", cores, ram, gpus,
                        vram is not None and not driver_only, disk)


def _keys(recs):
    return {stage: rec.option.key for stage, rec in recs.items()}


class RecommendTests(unittest.TestCase):
    def test_big_gpu(self):
        hw = _hw(vram=24.0)
        self.assertEqual(_keys(recommend(hw, "quality")),
                         {"asr": "large-v3", "asr_live": "large-v3-turbo",
                          "mt": "qwen3:14b", "tts": "xtts"})
        self.assertEqual(_keys(recommend(hw, "balanced")),
                         {"asr": "large-v3-turbo", "asr_live": "large-v3-turbo",
                          "mt": "marian", "tts": "edge"})
        self.assertEqual(_keys(recommend(hw, "speed"))["mt"], "google")
        self.assertEqual(_keys(recommend(hw, "speed"))["asr_live"], "small")

    def test_small_gpu_steps_down(self):
        recs = recommend(_hw(vram=4.0), "quality")
        self.assertEqual(recs["asr"].option.key, "large-v3-turbo")   # 4.8 GB does not fit
        self.assertEqual(recs["mt"].option.key, "marian")            # no LLM in 4 GB
        self.assertEqual(recs["tts"].option.key, "edge")
        self.assertIn("rec_reason_needs_gpu", [k for k, _ in recs["tts"].reasons])

    def test_cpu_only_prefers_light_models(self):
        recs = recommend(_hw(), "balanced")
        self.assertEqual(recs["asr"].option.key, "small")
        self.assertEqual(recs["asr_live"].option.key, "base")
        self.assertEqual(recs["asr"].reasons[0][0], "rec_reason_cpu")

    def test_weak_cpu_and_little_ram(self):
        recs = recommend(_hw(ram=4.0, cores=2), "quality")
        self.assertEqual(recs["asr"].option.key, "base")
        self.assertEqual(recs["asr_live"].option.key, "base")

    def test_driver_only_gpu_is_treated_as_cpu(self):
        recs = recommend(_hw(vram=8.0, driver_only=True), "balanced")
        self.assertEqual(recs["asr"].option.key, "small")
        self.assertEqual(recs["asr"].reasons[0][0], "rec_reason_gpu_unusable")

    def test_low_disk_skips_uncached_downloads(self):
        recs = recommend(_hw(vram=24.0, disk=3.0), "quality")
        self.assertEqual(recs["asr"].option.key, "large-v3-turbo")  # 3 GB does not fit
        self.assertIn("rec_reason_disk", [k for k, _ in recs["asr"].reasons])
        cached = recommend(_hw(vram=24.0, disk=2.0), "quality", cached={"large-v3"})
        self.assertEqual(cached["asr"].option.key, "large-v3")

    def test_every_recommendation_explains_itself(self):
        for pref in PREFERENCES:
            for vram in (None, 2.0, 6.0, 24.0):
                for rec in recommend(_hw(vram=vram), pref).values():
                    self.assertTrue(rec.reasons)
                    for key, params in rec.reasons:
                        self.assertTrue(key.startswith("rec_reason_"))
                        self.assertIsInstance(params, dict)

    def test_larger_gpu_than_a_24_gb_card_gets_a_larger_llm(self):
        self.assertEqual(recommend(_hw(vram=48.0, ram=64.0), "quality")["mt"].option.key,
                         "qwen3:32b")
        # a 24 GB card keeps room for live Whisper: the 32b model does not fit
        self.assertEqual(recommend(_hw(vram=24.0), "quality")["mt"].option.key,
                         "qwen3:14b")
        self.assertEqual(recommend(_hw(vram=12.0), "quality")["mt"].option.key,
                         "qwen3:8b")

    def test_assess_marks_every_option_for_the_manual_choice(self):
        small_gpu = _hw(vram=3.5, ram=8.0)
        self.assertEqual(assess(WHISPER["small"], small_gpu), "ok")
        self.assertEqual(assess(WHISPER["large-v3-turbo"], small_gpu), "tight")
        self.assertEqual(assess(WHISPER["large-v3"], small_gpu), "too_big")
        self.assertEqual(assess(MT["google"], small_gpu), "online")
        self.assertEqual(assess(MT["marian"], small_gpu), "ok")       # CPU model
        self.assertEqual(assess(WHISPER["large-v3"], _hw(vram=24.0, disk=1.5)), "no_disk")
        self.assertEqual(assess(WHISPER["large-v3"], _hw(vram=24.0, disk=1.5),
                                cached={"large-v3"}), "ok")
        cpu = _hw(ram=4.0)
        self.assertEqual(assess(WHISPER["medium"], cpu), "tight")
        self.assertEqual(assess(MT["qwen3:14b"], cpu), "too_big")

    def test_unknown_preference_is_balanced(self):
        self.assertEqual(_keys(recommend(_hw(vram=24.0), "turbo")),
                         _keys(recommend(_hw(vram=24.0), "balanced")))

    def test_online_services_are_not_downloads(self):
        for opt in (MT["google"], MT["deepl"], TTS["edge"]):
            self.assertFalse(opt.local)
            self.assertEqual(opt.download_mb, 0)
        self.assertTrue(MT["deepl"].needs_account)
        self.assertTrue(all(o.repo for o in WHISPER.values()))

    def test_whisper_repos_match_faster_whisper(self):
        try:
            from faster_whisper.utils import _MODELS
        except Exception:
            self.skipTest("faster-whisper not installed")
        for key, opt in WHISPER.items():
            self.assertEqual(_MODELS[key], opt.repo)


if __name__ == "__main__":
    unittest.main()


class OllamaPullFitTests(unittest.TestCase):
    """Before offering to pull an Ollama model: does it fit the disk and memory?

    A Windows VM (12.4 GB RAM, no GPU, 18 GB free) was offered qwen3:32b
    (20 GB download, about 32 GB of RAM to run) with no word about either."""

    def test_the_vm_case_has_no_room_for_qwen3_32b(self):
        from videotranslator.model_catalog import ollama_pull_fit
        fit = ollama_pull_fit("qwen3:32b", _hw(ram=12.4, disk=18.0))
        self.assertEqual(fit.verdict, "no_disk")
        self.assertAlmostEqual(fit.download_gb, 20000 / 1024, places=3)
        self.assertEqual(fit.disk_free_gb, 18.0)

    def test_with_room_it_is_still_too_big_for_the_memory(self):
        from videotranslator.model_catalog import ollama_pull_fit
        fit = ollama_pull_fit("qwen3:32b", _hw(ram=12.4, disk=100.0))
        self.assertEqual((fit.verdict, fit.need_gb, fit.have_gb, fit.gpu),
                         ("too_big", 32.0, 12.4, False))
        self.assertEqual(ollama_pull_fit("qwen3:14b", _hw(ram=12.4)).verdict, "too_big")
        self.assertEqual(ollama_pull_fit("qwen3:8b", _hw(ram=12.4)).verdict, "ok")

    def test_a_usable_gpu_is_judged_on_its_memory(self):
        from videotranslator.model_catalog import ollama_pull_fit
        fit = ollama_pull_fit("qwen3:32b", _hw(vram=24.0, ram=31.0))
        self.assertEqual((fit.verdict, fit.need_gb, fit.have_gb, fit.gpu),
                         ("ok", 22.0, 24.0, True))

    def test_models_outside_the_catalogue_are_judged_on_disk_only(self):
        from videotranslator.model_catalog import ollama_pull_fit
        self.assertEqual(ollama_pull_fit("qwen3:4b", _hw(ram=4.0), size_gb=2.5).verdict, "ok")
        self.assertEqual(ollama_pull_fit("qwen3:4b", _hw(disk=2.0), size_gb=2.5).verdict,
                         "no_disk")
        self.assertIsNone(ollama_pull_fit("somebody/custom:1b", _hw()))
