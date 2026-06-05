"""Runtime dependency policy for Wav2Lip.

Wav2Lip assets (repo + model) are not enough on their own: the external
``inference.py`` script imports a small base stack and a face-detection stack.
These helpers keep that readiness check testable without invoking pip.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


FindSpec = Callable[[str], Any]


@dataclass(frozen=True)
class RuntimeRequirement:
    module: str
    pip_name: str
    description: str = ""


WAV2LIP_BASE_REQUIREMENTS: tuple[RuntimeRequirement, ...] = (
    RuntimeRequirement("cv2", "opencv-python", "OpenCV runtime"),
    RuntimeRequirement("librosa", "librosa", "audio feature extraction"),
    RuntimeRequirement("tqdm", "tqdm", "progress reporting"),
)

WAV2LIP_FACE_REQUIREMENTS: tuple[RuntimeRequirement, ...] = (
    RuntimeRequirement("dlib", "dlib", "face detector backend"),
    RuntimeRequirement("facexlib", "facexlib", "face enhancement helpers"),
    RuntimeRequirement("basicsr", "new-basicsr", "BasicSR-compatible package"),
)


def module_present(
    module: str,
    *,
    find_spec: FindSpec = importlib.util.find_spec,
) -> bool:
    try:
        return find_spec(module) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def missing_runtime_packages(
    requirements: Sequence[RuntimeRequirement],
    *,
    find_spec: FindSpec = importlib.util.find_spec,
) -> list[str]:
    missing: list[str] = []
    for requirement in requirements:
        if not module_present(requirement.module, find_spec=find_spec):
            missing.append(requirement.pip_name)
    return missing


def missing_wav2lip_base_packages(
    *,
    find_spec: FindSpec = importlib.util.find_spec,
) -> list[str]:
    return missing_runtime_packages(WAV2LIP_BASE_REQUIREMENTS, find_spec=find_spec)


def missing_wav2lip_face_packages(
    *,
    find_spec: FindSpec = importlib.util.find_spec,
) -> list[str]:
    return missing_runtime_packages(WAV2LIP_FACE_REQUIREMENTS, find_spec=find_spec)


def wav2lip_face_stack_ready(
    *,
    find_spec: FindSpec = importlib.util.find_spec,
) -> bool:
    # Readiness is platform-independent: it only asks whether the face modules
    # import. *How* they get provisioned differs per OS (Windows installer ships
    # dlib wheels; Linux compiles at first use) but that lives elsewhere.
    return not missing_wav2lip_face_packages(find_spec=find_spec)
