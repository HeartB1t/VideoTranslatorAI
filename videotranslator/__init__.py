"""Core modules for VideoTranslatorAI.

This package is introduced as a migration layer. The legacy
``video_translator_gui.py`` entry point can keep working while pure logic is
gradually moved into importable, testable modules.
"""

from .startup_env import apply_startup_env as _apply_startup_env
from .startup_env import harden_std_streams as _harden_std_streams

__version__ = "2.1.2"

# Before any ML library is imported (they read the environment at import).
_apply_startup_env()
# Before anything is printed: a redirected cp1252 stdout on Windows must not
# stop the pipeline on the first character it lacks.
_harden_std_streams()
