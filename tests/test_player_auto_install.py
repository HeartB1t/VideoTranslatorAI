"""Auto-install del player video (self-heal senza click).

Il player sa gia' auto-installare il Vulkan Runtime e ripartire, ma a runtime
partiva solo cliccando il bottone "Installa player". Ora, come per Ollama con
``ollama_auto_install`` (default True), l'install parte da solo la prima volta
che il player manca ed e' installabile, MA solo quando l'utente mostra l'intento
di usarlo (seleziona/carica un media, avvia il live), non al refresh del badge
all'avvio (design B: niente download/pkexec non richiesti). Il bottone resta il
fallback manuale.

Copre:
  - gate di _maybe_auto_install_player (installabile/flag/one-shot/in-corso);
  - il refresh del badge (_on_player_status) NON avvia l'auto-install;
  - i punti di intento la avviano una volta: _ensure_or_show_player_status
    (selezione/load/preview/autoload/live-URL) e _start_live_session (live su file);
  - _start_live_session informa l'utente (banner) e non lancia una sessione monca;
  - _install_player(auto=True) salta askyesno/showerror (Windows e Linux);
  - il click manuale chiama sempre _install_player(auto=False).
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import video_translator_gui as gui
from videotranslator import libmpv_runtime as rt
from videotranslator import system_packages as sp


def _status(reason: str) -> rt.LibmpvStatus:
    return rt.LibmpvStatus(ok=reason == "ok", reason=reason)


class MaybeAutoInstallTests(unittest.TestCase):
    """Logica di gate di _maybe_auto_install_player (thread Tk)."""

    def _fake(self, *, tried=False, installing=False):
        return SimpleNamespace(
            _player_auto_tried=tried,
            _installing=installing,
            _player_log=lambda *a, **k: None,
            _install_player=mock.Mock())

    def _run(self, fake, status, *, auto_install=True):
        with mock.patch.object(gui, "load_config",
                               return_value={"player_auto_install": auto_install}):
            gui.App._maybe_auto_install_player(fake, status)

    # (a)
    def test_installable_and_flag_true_and_not_tried_starts_once(self):
        fake = self._fake()
        self._run(fake, _status("libmpv-missing"))
        fake._install_player.assert_called_once_with(auto=True)
        self.assertTrue(fake._player_auto_tried)

    def test_python_mpv_missing_is_also_installable(self):
        fake = self._fake()
        self._run(fake, _status("python-mpv-missing"))
        fake._install_player.assert_called_once_with(auto=True)

    # (b)
    def test_flag_false_does_not_start(self):
        fake = self._fake()
        self._run(fake, _status("libmpv-missing"), auto_install=False)
        fake._install_player.assert_not_called()
        # Non consuma il tentativo: se l'utente riabilita il flag, potra' partire.
        self.assertFalse(fake._player_auto_tried)

    # (c)
    def test_already_tried_does_not_restart(self):
        fake = self._fake(tried=True)
        self._run(fake, _status("libmpv-missing"))
        fake._install_player.assert_not_called()

    def test_install_in_progress_does_not_start(self):
        fake = self._fake(installing=True)
        self._run(fake, _status("libmpv-missing"))
        fake._install_player.assert_not_called()
        self.assertFalse(fake._player_auto_tried)

    # non installabile: es. libmpv troppo vecchia o crash -> niente auto
    def test_non_installable_status_does_not_start(self):
        for reason in ("libmpv-too-old", "probe-crashed", "libmpv-load-failed"):
            with self.subTest(reason=reason):
                fake = self._fake()
                self._run(fake, _status(reason))
                fake._install_player.assert_not_called()
                self.assertFalse(fake._player_auto_tried)


class OnPlayerStatusNoAutoTests(unittest.TestCase):
    """Il refresh del badge (_on_player_status) NON deve avviare l'auto-install:
    parte solo su intento dell'utente (design B). All'avvio niente download,
    niente pkexec."""

    def _fake(self):
        panel = SimpleNamespace(show_ready=mock.Mock(), render=mock.Mock(),
                                show_unavailable=mock.Mock(),
                                status_text=lambda: "x")
        return SimpleNamespace(
            _player_panel=panel,
            _player_controller=SimpleNamespace(state=SimpleNamespace(item=None, position=0.0)),
            _settings_win=None,
            _update_player_badge=mock.Mock(),
            _ensure_player=mock.Mock(),
            _maybe_auto_install_player=mock.Mock())

    def _call(self, fake, status, request):
        with mock.patch.object(gui, "load_config", return_value={"player_probe": None}), \
                mock.patch.object(gui._libmpv_runtime, "cache_entry", return_value=None):
            gui.App._on_player_status(fake, status, request)

    def test_ok_status_does_not_auto_install(self):
        fake = self._fake()
        self._call(fake, _status("ok"), sp.PlayerInstallRequest())
        fake._maybe_auto_install_player.assert_not_called()
        fake._player_panel.show_ready.assert_called_once()

    def test_unavailable_status_does_not_auto_install_at_refresh(self):
        fake = self._fake()
        self._call(fake, _status("libmpv-missing"),
                   sp.PlayerInstallRequest(pip_packages=("mpv",)))
        fake._player_panel.show_unavailable.assert_called_once()
        fake._maybe_auto_install_player.assert_not_called()


class IntentEnsureOrShowTests(unittest.TestCase):
    """_ensure_or_show_player_status e' il punto di intento condiviso (selezione
    input, load_item, preview editor, autoload risultato, stream live risolto):
    qui l'auto-install DEVE partire quando il player manca."""

    def _fake(self, status):
        return SimpleNamespace(
            _player_status=status,
            _player_install_request=None,
            _player_panel=SimpleNamespace(show_unavailable=mock.Mock()),
            _ensure_player=mock.Mock(),
            _maybe_auto_install_player=mock.Mock())

    def test_unavailable_triggers_auto_install(self):
        fake = self._fake(_status("libmpv-missing"))
        gui.App._ensure_or_show_player_status(fake)
        fake._player_panel.show_unavailable.assert_called_once()
        fake._maybe_auto_install_player.assert_called_once_with(fake._player_status)
        fake._ensure_player.assert_not_called()

    def test_ok_status_goes_to_ensure_player_without_auto(self):
        fake = self._fake(_status("ok"))
        gui.App._ensure_or_show_player_status(fake)
        fake._ensure_player.assert_called_once()
        fake._maybe_auto_install_player.assert_not_called()

    def test_no_status_yet_goes_to_ensure_player(self):
        fake = self._fake(None)
        gui.App._ensure_or_show_player_status(fake)
        fake._ensure_player.assert_called_once()
        fake._maybe_auto_install_player.assert_not_called()


class LiveStartIntentTests(unittest.TestCase):
    """Avvio del live su file quando il player manca: e' il caso che ha
    originato la feature. Deve avviare l'auto-install e informare l'utente,
    non lanciare una sessione monca."""

    def _fake(self, status):
        return SimpleNamespace(
            _live_session=None, _live_resolving=False, _running=False,
            _editor_open=False,
            _get_urls=lambda: [],
            _live_media_path=lambda: "/tmp/clip.mp4",
            _player_status=status,
            _installing=False,
            _player_controller=SimpleNamespace(paused=True, play_pause=mock.Mock()),
            _live_bar=SimpleNamespace(show_banner=mock.Mock()),
            _refresh_live_bar_enabled=mock.Mock(),
            _launch_live_session=mock.Mock(),
            _maybe_auto_install_player=mock.Mock())

    def test_missing_player_starts_auto_and_informs(self):
        fake = self._fake(_status("libmpv-missing"))
        # simula che l'auto-install parta (imposta _installing come fa il vero
        # _install_player).
        def start(_status):
            fake._installing = True
            return True
        fake._maybe_auto_install_player.side_effect = start
        gui.App._start_live_session(fake)
        fake._maybe_auto_install_player.assert_called_once_with(fake._player_status)
        fake._live_bar.show_banner.assert_called_once_with(
            "live_player_installing", is_error=False)
        fake._launch_live_session.assert_not_called()

    def test_missing_player_not_installable_shows_unavailable(self):
        fake = self._fake(_status("libmpv-missing"))
        # auto NON parte (flag off / gia' tentato): _installing resta False.
        fake._maybe_auto_install_player.return_value = False
        gui.App._start_live_session(fake)
        fake._live_bar.show_banner.assert_called_once_with(
            "player_unavailable_title", is_error=True)
        fake._launch_live_session.assert_not_called()

    def test_player_ok_launches_live_without_auto(self):
        fake = self._fake(_status("ok"))
        gui.App._start_live_session(fake)
        fake._maybe_auto_install_player.assert_not_called()
        fake._launch_live_session.assert_called_once()


class InstallPlayerAutoParamTests(unittest.TestCase):
    """_install_player: auto=True salta le conferme, auto=False le mantiene."""

    def _fake(self, request):
        installer = SimpleNamespace(install=mock.Mock())
        return SimpleNamespace(
            _installing=False,
            _player_install_request=request,
            _player_panel=SimpleNamespace(show_install_progress=mock.Mock()),
            _player_log=lambda *a, **k: None,
            _s=lambda k: k,
            _player_installer=lambda: installer,
            _on_player_install_done=mock.Mock(),
            _refresh_player_status=mock.Mock(),
            _installer=installer)

    def test_manual_windows_asks_confirmation(self):
        req = sp.PlayerInstallRequest(windows_dest="C:/dest", download_mb=50,
                                      pip_packages=("mpv",))
        fake = self._fake(req)
        with mock.patch.object(gui, "messagebox") as mb, \
                mock.patch.object(gui._libmpv_runtime, "install_windows"):
            mb.askyesno.return_value = False   # utente rifiuta
            gui.App._install_player(fake, auto=False)
        mb.askyesno.assert_called_once()
        fake._installer.install.assert_not_called()   # rifiuto -> niente install

    def test_auto_windows_skips_confirmation_and_installs(self):
        req = sp.PlayerInstallRequest(windows_dest="C:/dest", download_mb=50,
                                      pip_packages=("mpv",))
        fake = self._fake(req)
        with mock.patch.object(gui, "messagebox") as mb, \
                mock.patch.object(gui._libmpv_runtime, "install_windows"):
            gui.App._install_player(fake, auto=True)
        mb.askyesno.assert_not_called()               # nessuna conferma in auto
        fake._installer.install.assert_called_once()  # procede diretto

    def test_auto_linux_installs_without_confirmation(self):
        # P2: ramo auto su Linux/non-win32 (windows_dest None), con pip e
        # system_plans reali: install() parte, nessun askyesno.
        req = sp.PlayerInstallRequest(
            pip_packages=("mpv>=1.0.6,<2",),
            system_plans=((("pkexec", "apt-get", "update"),),),
            manual_command="sudo apt install libmpv2")
        fake = self._fake(req)
        with mock.patch.object(gui, "messagebox") as mb:
            gui.App._install_player(fake, auto=True)
        mb.askyesno.assert_not_called()
        mb.showerror.assert_not_called()
        fake._installer.install.assert_called_once()
        kwargs = fake._installer.install.call_args.kwargs
        self.assertEqual(kwargs["pip_packages"], ("mpv>=1.0.6,<2",))
        self.assertEqual(kwargs["system_plans"], ((("pkexec", "apt-get", "update"),),))
        self.assertIsNone(kwargs["windows_install"])

    def test_auto_concurrent_install_is_silent(self):
        fake = self._fake(sp.PlayerInstallRequest(pip_packages=("mpv",)))
        fake._installing = True
        with mock.patch.object(gui, "messagebox") as mb:
            gui.App._install_player(fake, auto=True)
        mb.showerror.assert_not_called()              # in auto niente popup errore
        fake._installer.install.assert_not_called()

    def test_manual_concurrent_install_shows_error(self):
        fake = self._fake(sp.PlayerInstallRequest(pip_packages=("mpv",)))
        fake._installing = True
        with mock.patch.object(gui, "messagebox") as mb:
            gui.App._install_player(fake, auto=False)
        mb.showerror.assert_called_once()             # percorso manuale invariato


class ManualClickRoutingTests(unittest.TestCase):
    """(e) il click sul bottone instrada sempre a _install_player(auto=False)."""

    def test_install_command_calls_with_auto_false(self):
        fake = SimpleNamespace(
            _log_event=mock.Mock(),
            _install_player=mock.Mock())
        gui.App._on_player_command(fake, "install", {})
        fake._install_player.assert_called_once_with()
        # chiamata senza argomenti -> auto assume il default False
        self.assertEqual(fake._install_player.call_args.kwargs.get("auto", False), False)


if __name__ == "__main__":
    unittest.main()
