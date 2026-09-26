import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from videotranslator import hardware_profile as hp


def _torch(gpus, available=True):
    props = [SimpleNamespace(name=n, total_memory=int(gb * 1024 ** 3)) for n, gb in gpus]
    cuda = SimpleNamespace(is_available=lambda: available,
                           device_count=lambda: len(props),
                           get_device_properties=lambda i: props[i])
    return SimpleNamespace(cuda=cuda)


class ParseTests(unittest.TestCase):
    def test_meminfo(self):
        self.assertAlmostEqual(hp.parse_meminfo("MemTotal:  32768000 kB\nMemFree: 1 kB"),
                               32768000 * 1024 / 1024 ** 3)
        self.assertIsNone(hp.parse_meminfo("nothing here"))

    def test_nvidia_smi(self):
        gpus = hp.parse_nvidia_smi("NVIDIA GeForce RTX 3090, 24576\nbad line\n")
        self.assertEqual(gpus, [hp.GpuInfo("NVIDIA GeForce RTX 3090", 24.0, "nvidia")])


class DetectTests(unittest.TestCase):
    def test_cuda_gpu_counts_as_usable_vram(self):
        info = hp.detect_hardware(torch_module=_torch([("RTX 3090", 24.0)]),
                                  model_dir=Path("/"))
        self.assertTrue(info.cuda_usable)
        self.assertAlmostEqual(info.vram_gb, 24.0)
        self.assertEqual(info.best_gpu.name, "RTX 3090")
        self.assertIsNotNone(info.disk_free_gb)

    def test_driver_only_gpu_is_reported_but_not_usable(self):
        def run(cmd, **kw):
            return SimpleNamespace(returncode=0, stdout="GTX 1060, 6144\n")
        with mock.patch.object(hp.shutil, "which", return_value="/usr/bin/nvidia-smi"):
            info = hp.detect_hardware(torch_module=_torch([], available=False), run=run,
                                      model_dir=Path("/"))
        self.assertFalse(info.cuda_usable)
        self.assertEqual(info.best_gpu.name, "GTX 1060")
        self.assertIsNone(info.vram_gb)

    def test_cpu_only_pc_without_tools(self):
        with mock.patch.object(hp.shutil, "which", return_value=None):
            info = hp.detect_hardware(use_torch=False, model_dir=Path("/"))
        self.assertEqual(info.gpus, ())
        self.assertIsNone(info.vram_gb)
        self.assertFalse(info.cuda_usable)
        self.assertTrue(info.cpu_name)

    def test_probe_failures_never_raise(self):
        def run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd, 5)
        broken = SimpleNamespace(cuda=SimpleNamespace(
            is_available=mock.Mock(side_effect=RuntimeError("driver"))))
        with mock.patch.object(hp.shutil, "which", return_value="/x"):
            info = hp.detect_hardware(torch_module=broken, run=run,
                                      model_dir=Path("/does/not/exist/models"))
        self.assertEqual(info.gpus, ())
        self.assertIsNotNone(info.disk_free_gb)       # walks up to an existing dir

    def test_rocm_gpu_is_seen_but_not_usable_for_speech_models(self):
        torch = _torch([("Radeon RX 7900", 24.0)])
        torch.version = SimpleNamespace(hip="6.0")
        info = hp.detect_hardware(torch_module=torch, model_dir=Path("/"))
        self.assertEqual(info.best_gpu.backend, "rocm")
        self.assertFalse(info.cuda_usable)
        self.assertIsNone(info.vram_gb)

    def test_apple_silicon_is_seen_but_not_usable(self):
        torch = _torch([], available=False)
        torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True))
        with mock.patch.object(hp.shutil, "which", return_value=None):
            info = hp.detect_hardware(torch_module=torch, model_dir=Path("/"))
        self.assertEqual(info.best_gpu.backend, "mps")
        self.assertIsNone(info.vram_gb)

    def test_model_dir_follows_hf_home(self):
        with mock.patch.dict(hp.os.environ, {"HF_HOME": "/tmp/hfx"}):
            self.assertEqual(hp.default_model_dir(), Path("/tmp/hfx"))


if __name__ == "__main__":
    unittest.main()
