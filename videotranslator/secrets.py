"""Secret storage helpers.

The production app stores the HuggingFace token in the OS keyring when
available and falls back to legacy JSON config only when needed. The functions
here keep that behavior injectable so tests never touch the real keyring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .config import load_json_config, merge_json_config, write_json_config


KEYRING_SERVICE = "VideoTranslatorAI"
HF_TOKEN_USERNAME = "hf_token"


class KeyringLike(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None:
        ...

    def set_password(self, service_name: str, username: str, password: str) -> None:
        ...


def load_secret_token(
    *,
    keyring_backend: KeyringLike | None,
    config_path: Path,
    service_name: str = KEYRING_SERVICE,
    username: str = HF_TOKEN_USERNAME,
    config_key: str = "hf_token",
) -> str:
    """Load a token from keyring first, then migrate/fallback from JSON config."""
    if keyring_backend is not None:
        try:
            token = keyring_backend.get_password(service_name, username)
            if token:
                cfg = load_json_config(config_path)
                if config_key in cfg:
                    cfg.pop(config_key, None)
                    write_json_config(config_path, cfg)
                return token

            legacy = str(load_json_config(config_path).get(config_key, "") or "").strip()
            if legacy:
                keyring_backend.set_password(service_name, username, legacy)
                cfg = load_json_config(config_path)
                cfg.pop(config_key, None)
                write_json_config(config_path, cfg)
                return legacy
        except Exception:
            pass

    return str(load_json_config(config_path).get(config_key, "") or "").strip()


def save_secret_token(
    token: str,
    *,
    keyring_backend: KeyringLike | None,
    config_path: Path,
    service_name: str = KEYRING_SERVICE,
    username: str = HF_TOKEN_USERNAME,
    config_key: str = "hf_token",
) -> bool:
    """Save a token. Return True when stored in keyring, False for JSON fallback."""
    token = (token or "").strip()
    if not token:
        return keyring_backend is not None

    if keyring_backend is not None:
        try:
            keyring_backend.set_password(service_name, username, token)
            cfg = load_json_config(config_path)
            if config_key in cfg:
                cfg.pop(config_key, None)
                write_json_config(config_path, cfg)
            return True
        except Exception:
            pass

    merge_json_config(config_path, {config_key: token})
    return False


def import_keyring_backend() -> Any | None:
    """Return an available keyring module, or None on unavailable backends."""
    try:
        import keyring

        keyring.get_keyring()
        return keyring
    except Exception:
        return None

