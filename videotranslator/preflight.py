"""Preflight diagnostics for local VideoTranslatorAI installations.

The checks here are intentionally side-effect free: no package installation,
no model download and no daemon startup. The GUI can keep its existing
auto-install flow, while CLI users get a quick way to inspect what is ready.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .platforms import platform_info


OK = "ok"
WARN = "warn"
MISSING = "missing"
INFO = "info"

GB = 1024 ** 3


@dataclass(frozen=True)
class PackageProbe:
    module: str
    pip_name: str
    required: bool = True
    description: str = ""
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class BinaryProbe:
    name: str
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    required: bool
    detail: str
    hint: str = ""

    @property
    def passes(self) -> bool:
        return self.status == OK or not self.required


@dataclass(frozen=True)
class PreflightReport:
    platform_name: str
    python_version: str
    checks: tuple[PreflightCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.passes for check in self.checks)

    @property
    def required_failures(self) -> tuple[PreflightCheck, ...]:
        return tuple(check for check in self.checks if not check.passes)


def default_required_packages(
    version_info: tuple[int, ...] | sys.version_info = sys.version_info,
) -> dict[str, str]:
    packages = {
        "faster_whisper": "faster-whisper",
        "edge_tts": "edge-tts",
        "deep_translator": "deep-translator",
        "pydub": "pydub",
        "demucs": "demucs",
        "yt_dlp": "yt-dlp",
        "torchcodec": "torchcodec",
        "requests": "requests",
    }
    if _version_tuple(version_info) >= (3, 13):
        packages["audioop"] = "audioop-lts"
    return packages


DEFAULT_OPTIONAL_PACKAGES: tuple[PackageProbe, ...] = (
    PackageProbe("sacremoses", "sacremoses", False, "MarianMT tokenizer"),
    PackageProbe("sentencepiece", "sentencepiece", False, "MarianMT tokenizer"),
    PackageProbe(
        "TTS",
        "coqui-tts transformers<5.1",
        False,
        "XTTS v2 voice cloning",
        aliases=("TTS", "coqui_tts"),
    ),
    PackageProbe(
        "pyannote",
        "pyannote.audio>=3.1,<4.0",
        False,
        "speaker diarization",
    ),
    PackageProbe("silero_vad", "silero-vad", False, "XTTS speech reference VAD"),
    PackageProbe("keyring", "keyring", False, "secure token storage"),
    PackageProbe("dlib", "dlib", False, "Wav2Lip face detector backend"),
    PackageProbe("facexlib", "facexlib", False, "Wav2Lip face helpers"),
    PackageProbe("basicsr", "new-basicsr", False, "Wav2Lip BasicSR-compatible package"),
)

DEFAULT_OPTIONAL_BINARIES: tuple[BinaryProbe, ...] = (
    BinaryProbe("git", False, "Wav2Lip first-run clone"),
    BinaryProbe("rubberband", False, "higher-quality audio stretching"),
    BinaryProbe("ollama", False, "local LLM translation"),
    BinaryProbe("nvidia-smi", False, "NVIDIA GPU diagnostics"),
)


FindSpec = Callable[[str], Any]
Which = Callable[[str], str | None]
Run = Callable[..., subprocess.CompletedProcess[str]]
DiskUsage = Callable[[str | Path], Any]


def find_missing_dependencies(
    required_packages: Mapping[str, str] | None = None,
    *,
    required_binaries: Sequence[str] = ("ffmpeg", "ffprobe"),
    find_spec: FindSpec = importlib.util.find_spec,
    which: Which = shutil.which,
) -> tuple[list[str], list[str]]:
    """Return missing pip package names and binary names.

    This preserves the legacy ``check_dependencies`` contract used by the GUI.
    """

    packages = (
        default_required_packages()
        if required_packages is None
        else required_packages
    )
    missing_pkgs = [
        pip_name
        for module, pip_name in packages.items()
        if not _module_present(module, find_spec=find_spec)
    ]
    missing_bins = [binary for binary in required_binaries if which(binary) is None]
    return missing_pkgs, missing_bins


def run_preflight(
    *,
    required_packages: Mapping[str, str] | None = None,
    optional_packages: Sequence[PackageProbe] = DEFAULT_OPTIONAL_PACKAGES,
    required_optional_modules: Sequence[str] = (),
    required_binaries: Sequence[str] = ("ffmpeg", "ffprobe"),
    optional_binaries: Sequence[BinaryProbe] = DEFAULT_OPTIONAL_BINARIES,
    min_free_gb: float = 20.0,
    disk_path: str | Path | None = None,
    sys_platform: str = sys.platform,
    version_info: tuple[int, ...] | sys.version_info = sys.version_info,
    find_spec: FindSpec = importlib.util.find_spec,
    which: Which = shutil.which,
    run: Run = subprocess.run,
    disk_usage: DiskUsage = shutil.disk_usage,
) -> PreflightReport:
    checks: list[PreflightCheck] = []
    version = _version_tuple(version_info)
    py_text = ".".join(str(part) for part in version[:3])
    info = platform_info(sys_platform)

    checks.append(_platform_check(info))
    checks.append(_python_check(version))

    packages = (
        default_required_packages(version_info)
        if required_packages is None
        else required_packages
    )
    for module, pip_name in packages.items():
        checks.append(
            _package_check(
                PackageProbe(module, pip_name, True),
                find_spec=find_spec,
            )
        )

    required_optional = set(required_optional_modules)
    for probe in optional_packages:
        effective_probe = probe
        if probe.module in required_optional:
            effective_probe = PackageProbe(
                probe.module,
                probe.pip_name,
                True,
                probe.description,
                probe.aliases,
            )
        checks.append(_package_check(effective_probe, find_spec=find_spec))

    for binary in required_binaries:
        checks.append(_binary_check(BinaryProbe(binary, True), which=which))

    for probe in optional_binaries:
        checks.append(_binary_check(probe, which=which))

    checks.append(
        _disk_space_check(
            disk_path or Path.home(),
            min_free_gb=min_free_gb,
            disk_usage=disk_usage,
        )
    )
    checks.append(_nvidia_gpu_check(which=which, run=run))

    return PreflightReport(
        platform_name=f"{info.name} ({sys_platform})",
        python_version=f"{py_text} [{platform.python_implementation()}]",
        checks=tuple(checks),
    )


def format_preflight_report(report: PreflightReport) -> str:
    """Return a compact, stable text report for CLI output."""

    labels = {
        OK: "[OK]",
        WARN: "[WARN]",
        MISSING: "[MISSING]",
        INFO: "[INFO]",
    }
    lines = [
        "VideoTranslatorAI preflight",
        f"Platform: {report.platform_name}",
        f"Python: {report.python_version}",
        "",
    ]
    for check in report.checks:
        label = labels.get(check.status, "[INFO]")
        required = "required" if check.required else "optional"
        line = f"{label} {check.name} ({required}): {check.detail}"
        if check.hint:
            line = f"{line} -- {check.hint}"
        lines.append(line)
    lines.extend(
        [
            "",
            "Result: OK" if report.ok else "Result: FAILED",
        ]
    )
    if report.required_failures:
        missing = ", ".join(check.name for check in report.required_failures)
        lines.append(f"Required failures: {missing}")
    return "\n".join(lines)


def _version_tuple(version_info: tuple[int, ...] | sys.version_info) -> tuple[int, ...]:
    return tuple(int(part) for part in version_info[:3])


def _module_present(module: str, *, find_spec: FindSpec) -> bool:
    try:
        return find_spec(module) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _package_check(probe: PackageProbe, *, find_spec: FindSpec) -> PreflightCheck:
    names = probe.aliases or (probe.module,)
    present = any(_module_present(name, find_spec=find_spec) for name in names)
    if present:
        detail = probe.description or f"module {probe.module} importable"
        return PreflightCheck(f"python:{probe.module}", OK, probe.required, detail)

    status = MISSING if probe.required else WARN
    detail = f"missing module {probe.module}"
    hint = f"install {probe.pip_name}"
    if probe.description:
        detail = f"{detail} ({probe.description})"
    return PreflightCheck(f"python:{probe.module}", status, probe.required, detail, hint)


def _binary_check(probe: BinaryProbe, *, which: Which) -> PreflightCheck:
    path = which(probe.name)
    if path:
        detail = path
        if probe.description:
            detail = f"{detail} ({probe.description})"
        return PreflightCheck(f"binary:{probe.name}", OK, probe.required, detail)

    status = MISSING if probe.required else WARN
    detail = "not found on PATH"
    if probe.description:
        detail = f"{detail} ({probe.description})"
    return PreflightCheck(f"binary:{probe.name}", status, probe.required, detail)


def _platform_check(info: Any) -> PreflightCheck:
    if info.supported:
        return PreflightCheck("platform", OK, False, info.name)
    if info.experimental:
        return PreflightCheck(
            "platform",
            WARN,
            False,
            f"{info.name} support is experimental",
        )
    return PreflightCheck("platform", WARN, False, f"{info.name} is not officially supported")


def _python_check(version: tuple[int, ...]) -> PreflightCheck:
    detail = ".".join(str(part) for part in version[:3])
    if version >= (3, 10):
        return PreflightCheck("python-version", OK, True, detail)
    return PreflightCheck(
        "python-version",
        MISSING,
        True,
        detail,
        "install Python 3.10 or newer",
    )


def _disk_space_check(
    path: str | Path,
    *,
    min_free_gb: float,
    disk_usage: DiskUsage,
) -> PreflightCheck:
    try:
        free_gb = float(disk_usage(path).free) / GB
    except (OSError, AttributeError, TypeError, ValueError) as exc:
        return PreflightCheck("disk-space", WARN, False, f"could not inspect {path}: {exc}")

    detail = f"{free_gb:.1f} GB free at {path}"
    if free_gb >= min_free_gb:
        return PreflightCheck("disk-space", OK, False, detail)
    return PreflightCheck(
        "disk-space",
        WARN,
        False,
        detail,
        f"full install is documented around {min_free_gb:.0f} GB",
    )


def _nvidia_gpu_check(*, which: Which, run: Run) -> PreflightCheck:
    if which("nvidia-smi") is None:
        return PreflightCheck(
            "gpu:nvidia",
            INFO,
            False,
            "nvidia-smi not found; CPU mode or non-NVIDIA GPU expected",
        )
    try:
        result = run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return PreflightCheck("gpu:nvidia", WARN, False, f"nvidia-smi failed: {exc}")

    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-1:]
        detail = tail[0] if tail else f"nvidia-smi exited {result.returncode}"
        return PreflightCheck("gpu:nvidia", WARN, False, detail)

    line = (result.stdout or "").strip().splitlines()
    return PreflightCheck(
        "gpu:nvidia",
        OK,
        False,
        line[0] if line else "nvidia-smi available",
    )
