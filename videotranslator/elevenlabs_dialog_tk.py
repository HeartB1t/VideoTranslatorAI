"""'ElevenLabs live voice' settings window.

Lets the user turn ElevenLabs on for the live dubbed voice, check the API key
(and see the characters left on the plan), choose a model and a voice from
the account catalogue, and keep Edge-TTS as the fallback. Network calls run
on a worker thread; results reach Tk through a queue polled with ``after``.
The catalogue (no secrets) is cached in the settings so the lists are there
offline; Refresh reloads it.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .elevenlabs_tts import (ElevenLabsClient, ElevenLabsError, Model, Voice,
                             pick_live_model)
from .voice_preview import fetch_sample
from .voice_preview_tk import SpeakerButton, error_key

_ERROR_KEYS = {kind: f"el_err_{kind}" for kind in
               ("auth", "quota", "rate_limited", "unavailable", "timeout", "invalid")}


def voices_from_cache(items) -> list[Voice]:
    out = []
    for item in items or []:
        try:
            previews = tuple((str(code), str(url)) for code, url in
                             (item.get("previews") or {}).items())
            out.append(Voice(item["voice_id"], item["name"], item.get("accent", ""),
                             item.get("gender", ""), tuple(item.get("languages", ())),
                             str(item.get("preview_url") or ""), previews))
        except (KeyError, TypeError, AttributeError):
            continue
    return out


def models_from_cache(items) -> list[Model]:
    out = []
    for item in items or []:
        try:
            out.append(Model(item["model_id"], item["name"], tuple(item.get("languages", ())),
                             bool(item.get("can_tts", True))))
        except (KeyError, TypeError):
            continue
    return out


def catalog_to_cache(voices: list[Voice], models: list[Model]) -> dict:
    return {"voices": [{"voice_id": v.voice_id, "name": v.name, "accent": v.accent,
                        "gender": v.gender, "languages": list(v.languages),
                        "preview_url": v.preview_url, "previews": dict(v.previews)}
                       for v in voices],
            "models": [{"model_id": m.model_id, "name": m.name,
                        "languages": list(m.languages), "can_tts": m.can_tts}
                       for m in models]}


class ElevenLabsDialog:
    """``settings`` keys: enabled, voice_id, model_id, fallback, catalog.
    ``on_save(settings, api_key)`` persists them (the key goes to the keyring).
    ``preview_hub`` (a ``PreviewHub``) adds the speaker icon that plays the
    voice's free sample."""

    def __init__(self, parent: tk.Misc, *, ui_s: Callable[[str], str], theme: Any,
                 make_button: Callable[..., tuple[tk.Widget, tk.Button]],
                 settings: dict, api_key: str, target_lang: str,
                 on_save: Callable[[dict, str], None],
                 client_factory: Callable[[str], Any] = ElevenLabsClient,
                 preview_hub: Any = None,
                 sample_loader: Callable[[str], bytes] = fetch_sample,
                 log: Callable[[str], None] | None = None) -> None:
        self._s = ui_s
        self._log = log
        self._hub = preview_hub
        self._sample_loader = sample_loader
        self._refreshed_for_preview = False
        self._pending_preview = False
        self.speaker: SpeakerButton | None = None
        self._on_save = on_save
        self._client_factory = client_factory
        self._lang = target_lang
        self._results: queue.Queue = queue.Queue()
        self._poll_after: str | None = None
        self._closed = False
        self._checking = False
        catalog = settings.get("catalog") or {}
        self._voices = voices_from_cache(catalog.get("voices"))
        self._models = [m for m in models_from_cache(catalog.get("models")) if m.can_tts]
        pal = theme.palette

        win = tk.Toplevel(parent, bg=pal.BG)
        self.win = win
        win.title(ui_s("el_title"))
        win.transient(parent)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.close)
        body = tk.Frame(win, bg=pal.BG, padx=18, pady=14)
        body.pack(fill="both", expand=True)

        def label(parent_, key, **kw):
            return tk.Label(parent_, text=ui_s(key), bg=pal.BG, fg=kw.pop("fg", pal.FG),
                            font=kw.pop("font", "VT.Base"), anchor="w", justify="left", **kw)

        self._enabled = tk.BooleanVar(value=bool(settings.get("enabled")))
        self._fallback = tk.BooleanVar(value=bool(settings.get("fallback", True)))
        check_opts = dict(bg=pal.BG, fg=pal.FG, selectcolor=pal.SEL,
                          activebackground=pal.BG, activeforeground=pal.FG,
                          highlightbackground=pal.BG, font="VT.Base", anchor="w")
        # Key, model and voice first; the switch that turns it on comes after them.
        grid = tk.Frame(body, bg=pal.BG)
        grid.pack(fill="x", pady=(0, 4))
        label(grid, "el_key").grid(row=0, column=0, sticky="w")
        self._key_var = tk.StringVar(value=api_key)
        self._key_entry = tk.Entry(grid, textvariable=self._key_var, show="•", width=44,
                                   bg=pal.FIELD, fg=pal.FG, insertbackground=pal.FG,
                                   relief="flat")
        self._key_entry.grid(row=0, column=1, sticky="w", padx=(8, 6))
        wrap, self._verify_btn = make_button(grid, text=ui_s("el_verify"), command=self.verify)
        wrap.grid(row=0, column=2, sticky="w")
        self._account = label(grid, "el_checking", fg=pal.FG2, font="VT.Small")
        self._account.configure(text="")
        self._account.grid(row=1, column=1, columnspan=2, sticky="w", padx=(8, 0))

        label(grid, "el_model").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self._model_combo = ttk.Combobox(grid, state="readonly", width=52)
        self._model_combo.grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 0),
                               pady=(10, 0))
        self._model_combo.bind("<<ComboboxSelected>>", lambda _e: self._check_language())
        label(grid, "el_voice").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self._voice_combo = ttk.Combobox(grid, state="readonly", width=52)
        self._voice_combo.grid(row=3, column=1, columnspan=2, sticky="w", padx=(8, 0),
                               pady=(6, 0))
        self._voice_combo.bind("<<ComboboxSelected>>", lambda _e: self._voice_changed())
        if preview_hub is not None:
            self.speaker = SpeakerButton(grid, palette=pal, bg_role="BG", ui_s=ui_s,
                                         on_click=self.preview, tip_key="vp_tip_sample",
                                         scale=getattr(theme, "scale", 1.0))
            self.speaker.canvas.grid(row=3, column=3, sticky="w", padx=(6, 0), pady=(6, 0))
            preview_hub.add_listener(self._on_preview_state)
        wrap, self._refresh_btn = make_button(grid, text=ui_s("el_refresh"),
                                              command=self.verify)
        wrap.grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        tk.Checkbutton(body, text=ui_s("el_use"), variable=self._enabled,
                       **check_opts).pack(fill="x", pady=(10, 0))
        tk.Checkbutton(body, text=ui_s("el_fallback"), variable=self._fallback,
                       **check_opts).pack(fill="x", pady=(2, 0))
        label(body, "el_note", fg=pal.FG2, font="VT.Small",
              wraplength=620).pack(fill="x", pady=(8, 4))
        self._status = label(body, "el_checking", font="VT.Small", wraplength=620)
        self._set_status("")
        self._status.pack(fill="x", pady=(2, 8))

        buttons = tk.Frame(body, bg=pal.BG)
        buttons.pack(fill="x")
        wrap, self._save_btn = make_button(buttons, text=ui_s("el_save"), command=self.save,
                                           primary=True)
        wrap.pack(side="left", padx=(0, 6))
        wrap, _close = make_button(buttons, text=ui_s("el_close"), command=self.close)
        wrap.pack(side="left")

        self._fill(settings.get("model_id"), settings.get("voice_id"))
        self._schedule_poll()

    def _set_status(self, text: str) -> None:
        """Show a result under the buttons and write it to the app log."""
        self._status.configure(text=text)
        if self._log is not None and text:
            try:
                self._log(text)
            except Exception:                  # noqa: BLE001
                pass

    # -- catalogue -----------------------------------------------------------

    def _model_text(self, model: Model) -> str:
        key = "el_lang_ok" if model.supports(self._lang) else "el_lang_no"
        mark = "✓" if model.supports(self._lang) else "✗"
        return f"{mark} {model.name} · {self._s(key).format(lang=self._lang)}"

    def _voice_text(self, voice: Voice) -> str:
        return voice.label() + (f" · {', '.join(voice.languages)}"
                                if voice.languages else "")

    def _fill(self, model_id: str | None, voice_id: str | None) -> None:
        self._model_combo.configure(values=[self._model_text(m) for m in self._models])
        self._voice_combo.configure(values=[self._voice_text(v) for v in self._voices])
        ids = [m.model_id for m in self._models]
        if model_id in ids:
            self._model_combo.current(ids.index(model_id))
        else:
            best = pick_live_model(self._models, self._lang)
            if best is not None:
                self._model_combo.current(ids.index(best.model_id))
        vids = [v.voice_id for v in self._voices]
        if voice_id in vids:
            self._voice_combo.current(vids.index(voice_id))
        elif vids:
            self._voice_combo.current(0)
        self._check_language()

    def _check_language(self) -> None:
        model = self.selected_model()
        if model is not None and not model.supports(self._lang):
            self._set_status(self._s("el_model_no_lang").format(lang=self._lang))
        elif self._status.cget("text") == self._s("el_model_no_lang").format(lang=self._lang):
            self._set_status("")

    def selected_model(self) -> Model | None:
        index = self._model_combo.current()
        return self._models[index] if 0 <= index < len(self._models) else None

    def selected_voice(self) -> Voice | None:
        index = self._voice_combo.current()
        return self._voices[index] if 0 <= index < len(self._voices) else None

    # -- voice sample ---------------------------------------------------------

    def _sample_key(self, voice: Voice, url: str) -> str:
        return f"el:{voice.voice_id}:{url}"

    def preview(self) -> None:
        """Play (or stop) the free sample of the selected voice."""
        if self._hub is None:
            return
        voice = self.selected_voice()
        if voice is None:
            return
        url = voice.sample_url(self._lang)
        if not url:
            # A catalogue cached before samples were kept: reload it once.
            if (not self._refreshed_for_preview and self._key_var.get().strip()
                    and not any(v.preview_url or v.previews for v in self._voices)):
                self._refreshed_for_preview = True
                self._pending_preview = True
                self.verify()
                return
            if self.speaker is not None:
                self.speaker.set_state("error", self._s("vp_err_no_sample"))
            self._set_status(self._s("vp_err_no_sample"))
            return
        loader = self._sample_loader
        self._hub.toggle(self._sample_key(voice, url), lambda: loader(url))

    def _voice_changed(self) -> None:
        if self._hub is not None:
            self._hub.stop_if("el:")

    def _on_preview_state(self, key: str, state: str, kind: str | None) -> None:
        if self._closed or self.speaker is None:
            return
        voice = self.selected_voice()
        mine = voice is not None and key == self._sample_key(
            voice, voice.sample_url(self._lang))
        if not mine:
            if self.speaker.state != "error":
                self.speaker.set_state("idle")
            return
        if state == "error":
            text = self._s(error_key(kind))
            self.speaker.set_state("error", text)
            self._set_status(text)
        else:
            self.speaker.set_state(state)

    # -- network (worker) ---------------------------------------------------

    def verify(self) -> None:
        if self._checking:
            return
        key = self._key_var.get().strip()
        if not key:
            self._set_status(self._s("el_err_auth"))
            return
        self._checking = True
        self._verify_btn.configure(state="disabled")
        self._refresh_btn.configure(state="disabled")
        self._set_status(self._s("el_checking"))

        def work() -> None:
            try:
                client = self._client_factory(key)
                account = client.account()
                models = client.models()
                voices = client.voices()
                self._results.put(("ok", (account, models, voices)))
            except ElevenLabsError as exc:
                self._results.put(("error", exc.kind))
            except Exception:                    # noqa: BLE001
                self._results.put(("error", "unavailable"))

        threading.Thread(target=work, name="elevenlabs-check", daemon=True).start()

    def _schedule_poll(self) -> None:
        if not self._closed:
            self._poll_after = self.win.after(150, self._poll)

    def _poll(self) -> None:
        self._poll_after = None
        while True:
            try:
                kind, value = self._results.get_nowait()
            except queue.Empty:
                break
            self._handle(kind, value)
        self._schedule_poll()

    def _handle(self, kind: str, value: Any) -> None:
        self._checking = False
        self._verify_btn.configure(state="normal")
        self._refresh_btn.configure(state="normal")
        if kind == "ok":
            account, models, voices = value
            self._account.configure(text=self._s("el_account").format(
                used=account.used, limit=account.limit, tier=account.tier or "?"))
            if self._log is not None:
                self._log(self._account.cget("text") + f" · {len(voices)} voices · "
                          f"{len([m for m in models if m.can_tts])} models")
            model = self.selected_model()
            voice = self.selected_voice()
            self._models = [m for m in models if m.can_tts]
            self._voices = list(voices)
            self._set_status("")
            self._fill(model.model_id if model else None, voice.voice_id if voice else None)
            if self._pending_preview:
                self._pending_preview = False
                self.preview()
        else:
            self._pending_preview = False
            self._set_status(self._s(_ERROR_KEYS.get(value, "el_err_unavailable")))

    # -- save / close -------------------------------------------------------

    def settings(self) -> dict:
        model = self.selected_model()
        voice = self.selected_voice()
        return {"enabled": bool(self._enabled.get()),
                "model_id": model.model_id if model else "",
                "voice_id": voice.voice_id if voice else "",
                "voice_name": voice.name if voice else "",
                "fallback": bool(self._fallback.get()),
                "catalog": catalog_to_cache(self._voices, self._models)}

    def save(self) -> bool:
        current = self.settings()
        key = self._key_var.get().strip()
        if current["enabled"] and not (key and current["model_id"] and current["voice_id"]):
            self._set_status(self._s("el_missing"))
            return False
        self._on_save(current, key)
        self._set_status(self._s("el_saved"))
        return True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._hub is not None:
            self._hub.remove_listener(self._on_preview_state)
            self._hub.stop_if("el:")
        if self._poll_after is not None:
            try:
                self.win.after_cancel(self._poll_after)
            except tk.TclError:
                pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    @property
    def closed(self) -> bool:
        return self._closed
