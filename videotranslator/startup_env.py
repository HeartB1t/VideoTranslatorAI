"""Environment defaults applied when the package is imported.

``huggingface_hub`` (and through it ``transformers``) reads its settings
from the environment at import time, so a default only counts when it is in
place before the first heavy import. The GUI, the CLI and the ``python -m
videotranslator...`` helper processes all import this package before any
of those libraries, which makes ``videotranslator/__init__`` the one early
hook they share. ``setdefault`` semantics: a value the user exported wins.
"""

from __future__ import annotations

import codecs
import os
import sys
from collections.abc import Iterable, MutableMapping

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


def harden_std_streams(streams: Iterable | None = None) -> list:
    """Never stop on printing a character the output encoding lacks.

    Windows writes a redirected stdout or stderr (a file, a pipe, a CI log)
    in the ANSI code page, cp1252 in Western Europe: the first "\u2192" the
    pipeline printed raised UnicodeEncodeError and stopped the job halfway.
    Such a stream now writes the character as an escape (``\\u2192``) and
    keeps its encoding. UTF streams, streams with an error policy already
    chosen and objects that cannot be reconfigured stay as they are.
    ``streams`` defaults to stdout and stderr; returns the streams changed.
    """
    changed = []
    for stream in (sys.stdout, sys.stderr) if streams is None else streams:
        reconfigure = getattr(stream, "reconfigure", None)
        encoding = getattr(stream, "encoding", None)
        if reconfigure is None or not encoding or getattr(stream, "errors", "strict") != "strict":
            continue
        try:
            if codecs.lookup(encoding).name.startswith("utf"):
                continue
            reconfigure(errors="backslashreplace")
        except (LookupError, ValueError, OSError):    # unknown codec, closed stream
            continue
        changed.append(stream)
    return changed
