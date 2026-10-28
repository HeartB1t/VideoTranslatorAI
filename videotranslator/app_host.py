"""Late-bound access to the GUI host module for the ``App`` mixins.

The ``app_*_tk`` mixins hold methods of ``video_translator_gui.App``. They read
the host module's globals through ``host`` (imported there as ``_g``) at call
time, so a name patched on the host module (as the tests do) is seen by every
mixin exactly as it was when the methods lived in the host file.
"""

from __future__ import annotations

from types import ModuleType


class _Host:
    __slots__ = ("_module",)

    def __init__(self) -> None:
        object.__setattr__(self, "_module", None)

    def bind(self, module: ModuleType) -> None:
        object.__setattr__(self, "_module", module)

    def __getattr__(self, name: str):
        module = object.__getattribute__(self, "_module")
        if module is None:
            raise RuntimeError("app_host is not bound: import video_translator_gui first")
        return getattr(module, name)

    def __setattr__(self, name: str, value) -> None:
        raise AttributeError("assign on the host module, not through app_host")


host = _Host()
