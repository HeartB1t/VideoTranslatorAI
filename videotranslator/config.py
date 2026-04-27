"""JSON configuration helpers.

This module keeps file IO small and injectable so it can be tested without
touching the user's real config file or keyring.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_json_config(path: Path) -> dict[str, Any]:
    """Load a JSON object config; return an empty dict on absent/invalid files."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def write_json_config(path: Path, cfg: dict[str, Any]) -> None:
    """Write a full config dict atomically with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    tmp.replace(path)


def merge_json_config(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Merge ``data`` into the existing config, persist it, and return it."""
    existing = load_json_config(path)
    existing.update(data)
    write_json_config(path, existing)
    return existing

