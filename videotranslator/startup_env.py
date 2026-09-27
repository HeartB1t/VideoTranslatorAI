"""Environment defaults applied when the package is imported.

``huggingface_hub`` (and through it ``transformers``) reads its settings
from the environment at import time, so a default only counts when it is in
place before the first heavy import. The GUI, the CLI and the ``python -m
videotranslator...`` helper processes all import this package before any
of those libraries, which makes ``videotranslator/__init__`` the one early
hook they share. ``setdefault`` semantics: a value the user exported wins.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping

STARTUP_ENV_DEFAULTS: dict[str, str] = {
    # Windows without Developer Mode cannot create symlinks: the Hugging Face
    # cache falls back to copies and would warn about it at every start.
    "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
}


def apply_startup_env(environ: MutableMapping[str, str] | None = None) -> dict[str, str]:
    """Set the defaults missing from ``environ`` (``os.environ`` when None).

    Returns the variables this call set, so a caller can tell what changed.
    """
    target = os.environ if environ is None else environ
    applied: dict[str, str] = {}
    for name, value in STARTUP_ENV_DEFAULTS.items():
        if name not in target:
            target[name] = value
            applied[name] = value
    return applied
