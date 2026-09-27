"""Read-only discovery of the PC hardware that matters for the AI models.

Feature "hardware-aware model selection", step 1: CPU, system RAM, GPU/backend,
usable VRAM and free disk space, detected without installing or downloading
anything. Every probe degrades gracefully: a missing tool or library leaves the
field empty (``None``) instead of raising, so a CPU-only PC, an unsupported GPU
or a restricted system still gets a usable profile.

Works on Linux, Windows and macOS with the standard library only; ``psutil``
and ``torch`` are used when they are installed, never required. Slow probes
(``torch`` import, ``nvidia-smi``) mean callers should run ``detect_hardware``
off the Tk thread.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_GIB = 1024 ** 3


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_gb: float | None          # total memory of the device
    backend: str                   # "cuda" (usable), "nvidia" (driver only),
                                   # "rocm" or "mps" (seen, but faster-whisper
                                   # and CTranslate2 cannot use them)


@dataclass(frozen=True)
class HardwareInfo:
    os_name: str
    cpu_name: str
    cpu_cores: int | None          # logical cores
    ram_gb: float | None
    gpus: tuple[GpuInfo, ...]
    cuda_usable: bool              # torch can run CUDA here
    disk_free_gb: float | None     # where the models are cached

    @property
    def best_gpu(self) -> GpuInfo | None:
        if not self.gpus:
            return None
        return max(self.gpus, key=lambda g: g.vram_gb or 0.0)

    @property
    def vram_gb(self) -> float | None:
        """VRAM usable by the models: only a GPU torch can drive counts."""
        gpu = self.best_gpu
        if gpu is None or not self.cuda_usable or gpu.backend != "cuda":
            return None
        return gpu.vram_gb


# --- individual probes (each returns None on any failure) -------------------

def _cpu_name() -> str:
    name = ""
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
                if line.lower().startswith("model name"):
                    name = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    elif sys.platform == "darwin":
        name = _run_text(["sysctl", "-n", "machdep.cpu.brand_string"]) or ""
    return name or platform.processor() or platform.machine() or "CPU"


def _run_text(cmd: list[str], *, run: Callable[..., Any] = subprocess.run,
              timeout: float = 5.0) -> str | None:
    """stdout of ``cmd`` or None (missing tool, error, timeout)."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        proc = run(cmd, capture_output=True, text=True, timeout=timeout,
                   stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if getattr(proc, "returncode", 1) != 0:
        return None
    return (proc.stdout or "").strip()


def parse_meminfo(text: str) -> float | None:
    """Total RAM in GiB from a Linux /proc/meminfo text."""
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            try:
                return int(parts[1]) * 1024 / _GIB      # value is in kB
            except (IndexError, ValueError):
                return None
    return None


def _ram_gb() -> float | None:
    try:
        import psutil  # type: ignore[import-not-found]
        return psutil.virtual_memory().total / _GIB
    except Exception:
        pass
    if sys.platform.startswith("linux"):
        try:
            return parse_meminfo(Path("/proc/meminfo").read_text())
        except OSError:
            return None
    if sys.platform == "win32":
        return _windows_ram_gb()
    if sys.platform == "darwin":
        out = _run_text(["sysctl", "-n", "hw.memsize"])
        try:
            return int(out) / _GIB if out else None
        except ValueError:
            return None
    return None


def _windows_ram_gb() -> float | None:
    try:
        import ctypes

        class _MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = _MemStatus()
        status.dwLength = ctypes.sizeof(_MemStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return status.ullTotalPhys / _GIB
    except Exception:
        return None


def parse_nvidia_smi(text: str) -> list[GpuInfo]:
    """GPUs from ``nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits``."""
    gpus: list[GpuInfo] = []
    for line in text.splitlines():
        if "," not in line:
            continue
        name, _, mem = line.rpartition(",")
        try:
            vram = float(mem.strip()) / 1024        # MiB -> GiB
        except ValueError:
            vram = None
        if name.strip():
            gpus.append(GpuInfo(name.strip(), vram, "nvidia"))
    return gpus


def _torch_gpus(torch_module: Any) -> tuple[list[GpuInfo], bool]:
    try:
        cuda = torch_module.cuda
        if cuda.is_available():
            # A ROCm build of torch answers through torch.cuda too, but the
            # speech models (CTranslate2) run on NVIDIA CUDA only.
            rocm = bool(getattr(getattr(torch_module, "version", None), "hip", None))
            backend = "rocm" if rocm else "cuda"
            gpus = []
            for index in range(cuda.device_count()):
                props = cuda.get_device_properties(index)
                gpus.append(GpuInfo(str(props.name), props.total_memory / _GIB, backend))
            return gpus, not rocm
    except Exception:
        pass
    try:
        mps = torch_module.backends.mps
        if mps.is_available():
            # Apple Silicon: memory is shared with the system (see RAM).
            return [GpuInfo("Apple GPU (Metal)", None, "mps")], False
    except Exception:
        pass
    return [], False


def _import_torch() -> Any | None:
    try:
        import torch  # noqa: PLC0415 (slow import, only when probing)
        return torch
    except Exception:
        return None


def default_model_dir() -> Path:
    """Where Hugging Face (and so faster-whisper) caches the downloaded models."""
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        return Path(hf_home)
    return Path.home() / ".cache" / "huggingface"


def _disk_free_gb(path: Path) -> float | None:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free / _GIB
    except OSError:
        return None


def detect_hardware(*, torch_module: Any | None = None, use_torch: bool = True,
                    run: Callable[..., Any] = subprocess.run,
                    model_dir: Path | None = None) -> HardwareInfo:
    """Probe the hardware once. Never raises; unknown values are None."""
    if torch_module is None and use_torch:
        torch_module = _import_torch()
    gpus: list[GpuInfo] = []
    cuda_usable = False
    if torch_module is not None:
        gpus, cuda_usable = _torch_gpus(torch_module)
    if not gpus:
        # The driver sees a GPU torch cannot use (CPU-only torch, old CUDA):
        # report it, but it does not count as usable VRAM.
        out = _run_text(["nvidia-smi", "--query-gpu=name,memory.total",
                         "--format=csv,noheader,nounits"], run=run)
        if out:
            gpus = parse_nvidia_smi(out)
    return HardwareInfo(
        os_name=f"{platform.system()} {platform.release()}".strip(),
        cpu_name=_cpu_name(),
        cpu_cores=os.cpu_count(),
        ram_gb=_ram_gb(),
        gpus=tuple(gpus),
        cuda_usable=cuda_usable,
        disk_free_gb=_disk_free_gb(model_dir or default_model_dir()),
    )


# --- display adapters (for the player's hardware decoding) -------------------
#
# Cheap and instant on purpose (sysfs, one user32 call, a PATH lookup: no
# subprocess, no torch): the player creates its mpv instance from a worker
# thread at startup and must not wait for nvidia-smi.

# PCI vendor ids of emulated or software-only display adapters. There is no
# hardware video decoder behind them, so mpv's hwdec probing can only fail
# (and log the failed CUDA / DXVA2 / D3D11VA attempts at every load).
VIRTUAL_GPU_VENDORS: frozenset[str] = frozenset({
    "80ee",   # VirtualBox
    "15ad",   # VMware SVGA
    "1234",   # QEMU / Bochs standard VGA
    "1af4",   # virtio-gpu
    "1b36",   # Red Hat QXL
    "1414",   # Microsoft (Hyper-V synthetic video, Basic Render Driver)
    "1a03",   # ASPEED (server BMC VGA)
    "102b",   # Matrox G200 (server VGA)
})
NVIDIA_VENDOR = "10de"
_PCI_VENDOR = re.compile(r"(?:^0x|\\VEN_)([0-9A-Fa-f]{4})(?![0-9A-Fa-f])")
_DRM_ROOT = Path("/sys/class/drm")


def parse_pci_vendor(text: str) -> str | None:
    """Lower-case PCI vendor id from a sysfs value (``0x10de``) or a Windows
    PnP id (``PCI\\VEN_10DE&DEV_2204&...``); None for anything else (a
    VMBUS or ROOT device, an ACPI id, garbage)."""
    match = _PCI_VENDOR.search((text or "").strip())
    return match.group(1).lower() if match else None


def _linux_display_vendors(drm_root: Path) -> tuple[str, ...] | None:
    """Vendors of the DRM cards (GPUs with a kernel driver); None without sysfs."""
    if not drm_root.is_dir():
        return None
    vendors: list[str] = []
    for card in sorted(drm_root.glob("card[0-9]*")):
        if "-" in card.name:                  # a connector (card0-HDMI-A-1), not a card
            continue
        try:
            text = (card / "device" / "vendor").read_text(encoding="ascii", errors="replace")
        except OSError:
            continue                          # platform device: no PCI vendor
        vendor = parse_pci_vendor(text)
        if vendor:
            vendors.append(vendor)
    return tuple(vendors)


def _windows_display_device_ids() -> list[str]:
    """PnP ids of the display devices (``EnumDisplayDevicesW``); raises when
    user32 is unavailable."""
    import ctypes
    from ctypes import wintypes

    class DisplayDevice(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD),
                    ("DeviceName", wintypes.WCHAR * 32),
                    ("DeviceString", wintypes.WCHAR * 128),
                    ("StateFlags", wintypes.DWORD),
                    ("DeviceID", wintypes.WCHAR * 128),
                    ("DeviceKey", wintypes.WCHAR * 128)]

    enum_devices = ctypes.windll.user32.EnumDisplayDevicesW      # type: ignore[attr-defined]
    enum_devices.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                             ctypes.POINTER(DisplayDevice), wintypes.DWORD]
    enum_devices.restype = wintypes.BOOL
    ids: list[str] = []
    for index in range(64):
        device = DisplayDevice()
        device.cb = ctypes.sizeof(DisplayDevice)
        if not enum_devices(None, index, ctypes.byref(device), 0):
            break
        ids.append(str(device.DeviceID))
    return ids


def _vendors_from_ids(ids: Iterable[str]) -> tuple[str, ...]:
    vendors: list[str] = []
    for device_id in ids:
        vendor = parse_pci_vendor(device_id)
        if vendor:
            vendors.append(vendor)
    return tuple(vendors)


def display_adapter_vendors(sys_platform: str | None = None, *,
                            drm_root: Path = _DRM_ROOT,
                            device_ids: Callable[[], Iterable[str]] | None = None,
                            which: Callable[[str], str | None] = shutil.which,
                            ) -> tuple[str, ...] | None:
    """PCI vendor ids of the PC's display adapters, in enumeration order.

    ``()`` means the probe worked and found no adapter with a PCI vendor (a
    VM without a PCI GPU, a bare framebuffer); None means this platform or
    this system cannot be probed. ``nvidia-smi`` on the PATH counts as an
    NVIDIA adapter even when the kernel/driver enumeration misses it. Never
    raises.
    """
    platform_key = sys_platform or sys.platform
    vendors: tuple[str, ...] | None = None
    try:
        if platform_key.startswith("linux"):
            vendors = _linux_display_vendors(drm_root)
        elif platform_key == "win32":
            vendors = _vendors_from_ids((device_ids or _windows_display_device_ids)())
    except Exception:                         # noqa: BLE001 - a probe must never break the player
        vendors = None
    try:
        has_smi = which("nvidia-smi") is not None
    except Exception:                         # noqa: BLE001
        has_smi = False
    if has_smi and (vendors is None or NVIDIA_VENDOR not in vendors):
        vendors = (vendors or ()) + (NVIDIA_VENDOR,)
    return vendors


def hardware_gpu_present(vendors: Sequence[str] | None) -> bool | None:
    """True when a display adapter of a real GPU vendor is present, False when
    there are none or only emulated ones, None when unknown (probe failed)."""
    if vendors is None:
        return None
    return any(vendor not in VIRTUAL_GPU_VENDORS for vendor in vendors)
