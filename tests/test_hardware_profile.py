import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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


class DisplayAdapterTests(unittest.TestCase):
    """Display adapters of the PC, for the player's hardware decoding choice."""

    def test_pci_vendor_from_sysfs_and_windows_pnp_ids(self):
        self.assertEqual(hp.parse_pci_vendor("0x10de\n"), "10de")
        self.assertEqual(hp.parse_pci_vendor("PCI\\VEN_80EE&DEV_BEEF&SUBSYS_00000000&REV_00"),
                         "80ee")
        self.assertEqual(hp.parse_pci_vendor("PCI\\VEN_8086&DEV_46A6"), "8086")
        for other in ("", "VMBUS\\{da0a7802-e377-4aac-8e77-0558eb1073f8}",
                      "ROOT\\BasicDisplay\\0000", "ACPI\\VEN_QCOM&DEV_0D3B", "10de"):
            self.assertIsNone(hp.parse_pci_vendor(other), other)

    def test_hardware_gpu_present_ignores_emulated_adapters(self):
        self.assertIsNone(hp.hardware_gpu_present(None))
        self.assertFalse(hp.hardware_gpu_present(()))
        self.assertFalse(hp.hardware_gpu_present(("80ee",)))            # VirtualBox
        self.assertFalse(hp.hardware_gpu_present(("1414", "15ad")))     # Hyper-V, VMware
        self.assertTrue(hp.hardware_gpu_present(("10de",)))
        self.assertTrue(hp.hardware_gpu_present(("8086", "80ee")))      # Intel iGPU in a VM host

    def test_linux_vendors_come_from_drm_cards_and_nvidia_smi(self):
        with TemporaryDirectory() as tmp:
            drm = Path(tmp) / "drm"
            (drm / "card0" / "device").mkdir(parents=True)
            (drm / "card0" / "device" / "vendor").write_text("0x8086\n")
            (drm / "card0-HDMI-A-1").mkdir()              # a connector, not a card
            (drm / "card1").mkdir()                        # platform device: no PCI vendor
            (drm / "renderD128").mkdir()
            no_smi = lambda _name: None                    # noqa: E731
            with_smi = lambda name: "/usr/bin/" + name     # noqa: E731
            self.assertEqual(hp.display_adapter_vendors("linux", drm_root=drm, which=no_smi),
                             ("8086",))
            # nvidia-smi is positive evidence even when nvidia-drm is not loaded.
            self.assertEqual(hp.display_adapter_vendors("linux", drm_root=drm, which=with_smi),
                             ("8086", "10de"))
            self.assertIsNone(hp.display_adapter_vendors(
                "linux", drm_root=drm / "missing", which=no_smi))
            self.assertEqual(hp.display_adapter_vendors(
                "linux", drm_root=drm / "missing", which=with_smi), ("10de",))
            (drm / "card0" / "device" / "vendor").unlink()
            self.assertEqual(hp.display_adapter_vendors("linux", drm_root=drm, which=no_smi), ())

    def test_windows_vendors_come_from_the_display_device_ids(self):
        no_smi = lambda _name: None                        # noqa: E731
        vm = ["PCI\\VEN_80EE&DEV_BEEF&SUBSYS_040515AD&REV_00", "ROOT\\BasicDisplay\\0000"]
        self.assertEqual(hp.display_adapter_vendors("win32", device_ids=lambda: vm, which=no_smi),
                         ("80ee",))
        laptop = ["PCI\\VEN_8086&DEV_46A6&SUBSYS_0B2E1028&REV_0C",
                  "PCI\\VEN_10DE&DEV_25A2&SUBSYS_0B2E1028&REV_A1"]
        self.assertEqual(hp.display_adapter_vendors(
            "win32", device_ids=lambda: laptop, which=no_smi), ("8086", "10de"))
        self.assertEqual(hp.display_adapter_vendors(
            "win32", device_ids=lambda: ["VMBUS\\{da0a7802-e377-4aac-8e77-0558eb1073f8}"],
            which=no_smi), ())

        def broken():
            raise OSError("no user32")

        self.assertIsNone(hp.display_adapter_vendors("win32", device_ids=broken, which=no_smi))
        self.assertEqual(hp.display_adapter_vendors(
            "win32", device_ids=broken, which=lambda name: "C:\\Windows\\System32\\" + name),
            ("10de",))

    def test_other_platforms_are_unknown(self):
        self.assertIsNone(hp.display_adapter_vendors("darwin", which=lambda _name: None))


if __name__ == "__main__":
    unittest.main()
