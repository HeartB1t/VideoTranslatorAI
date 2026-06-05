"""Ollama runtime helpers: setup, daemon, model pull, and response cleanup."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

_RegisterHook = Callable[[Any], None]
_register_hook: _RegisterHook = lambda _proc: None
_unregister_hook: _RegisterHook = lambda _proc: None


def set_subprocess_hooks(register: _RegisterHook | None, unregister: _RegisterHook | None) -> None:
    """Set optional process registry hooks used by GUI shutdown cleanup."""
    global _register_hook, _unregister_hook
    _register_hook = register or (lambda _proc: None)
    _unregister_hook = unregister or (lambda _proc: None)


def _register_subprocess(proc: Any) -> None:
    _register_hook(proc)


def _unregister_subprocess(proc: Any) -> None:
    _unregister_hook(proc)


# ── Ollama LLM translation (v2.0) ──────────────────────────────────────────
# ISO code → human-readable language name mapping. LLM prompts are far more
# reliable when given "English"/"Italian" rather than "en"/"it". Covers the
# same set as LANGUAGES + common Whisper source codes; unknown codes fall back
# to the raw code (modern LLMs still handle it, just with slightly less
# accuracy).
_OLLAMA_LANG_NAMES: dict[str, str] = {
    "auto": "auto-detected",
    "ar": "Arabic", "cs": "Czech", "da": "Danish", "de": "German",
    "el": "Greek", "en": "English", "es": "Spanish", "fi": "Finnish",
    "fr": "French", "hi": "Hindi", "hu": "Hungarian", "id": "Indonesian",
    "it": "Italian", "ja": "Japanese", "ko": "Korean", "nl": "Dutch",
    "no": "Norwegian", "pl": "Polish", "pt": "Portuguese", "ro": "Romanian",
    "ru": "Russian", "sv": "Swedish", "tr": "Turkish", "uk": "Ukrainian",
    "vi": "Vietnamese", "zh": "Chinese", "zh-cn": "Chinese", "zh-CN": "Chinese",
}


def _ollama_lang_name(code: str) -> str:
    if not code:
        return "English"
    return _OLLAMA_LANG_NAMES.get(code, _OLLAMA_LANG_NAMES.get(code.lower(), code))


def _ollama_num_predict_for_segment(
    text: str,
    is_qwen3: bool,
    thinking: bool,
    retry: int = 0,
) -> int:
    """Token budget for one Ollama segment.

    Qwen3 thinking can spend thousands of tokens in chain-of-thought before it
    emits the final answer. If ``num_predict`` is exhausted inside ``<think>``,
    `_ollama_strip_preamble()` correctly strips the orphan reasoning block and
    returns an empty string. Keep thinking enabled, but give it a larger budget
    and one retry with doubled budget before falling back.
    """
    num_predict = max(64, len(text) * 2 // 4 * 2)
    if is_qwen3 and thinking:
        num_predict = max(4096, num_predict * 20)
    if retry > 0:
        # Qwen3 thinking on dense segments (e.g. qwen3:14b on long sentences)
        # can blow past 8192 tokens of chain-of-thought; observed in production
        # 2026-04-28 with seg #24. Quadruple the retry budget instead of just
        # doubling so the second attempt has a real chance to finish.
        if is_qwen3 and thinking:
            num_predict *= 4 ** retry
        else:
            num_predict *= 2 ** retry
    return num_predict


def _ollama_health_check(
    api_url: str, model: str, timeout: float = 5.0
) -> tuple[bool, str, str]:
    """Check that Ollama is reachable and resolve the model to use.

    Returns ``(ok, message, resolved_model)``:
    - ``ok=False, message=<human readable>, resolved_model=""`` if the daemon
      is unreachable, returns invalid JSON, or has zero models installed.
    - ``ok=True, message="", resolved_model=<requested>`` if the requested
      tag (or a quantization variant / same-family alternative) is present.
    - ``ok=True, message=<warning>, resolved_model=<auto-selected>`` if the
      requested tag is missing but ``select_compatible_model`` finds a
      sensible Ollama alternative (e.g. configured ``mistral-nemo`` is gone
      but ``qwen3:14b`` is installed). The pipeline should USE the
      ``resolved_model`` value, not the original request.

    Does not raise — the caller branches on ``ok`` and decides whether to
    surface ``message`` to the user.
    """
    import requests
    from videotranslator.ollama_model_selector import select_compatible_model

    base = api_url.rstrip("/")
    target = (model or "").strip()
    try:
        r = requests.get(f"{base}/api/tags", timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        return False, f"Ollama daemon not reachable at {base} ({e.__class__.__name__}: {e})", ""
    except Exception as e:
        return False, f"Ollama returned invalid JSON at {base} ({e.__class__.__name__}: {e})", ""

    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    if not models:
        return (
            False,
            f"No models installed in Ollama at {base}. "
            f"Install one with e.g. 'ollama pull {target or 'qwen3:14b'}'",
            "",
        )

    # Tier 1+2: exact / quantization-tail match — keep legacy behaviour
    # (silent ok, requested model used as-is).
    if target and target in models:
        return True, "", target
    for m in models:
        if target and m.startswith(target + "-"):
            return True, "", m

    # Tier 3+ (the new behaviour): use the smart selector. It always
    # returns a usable tag here because ``models`` is non-empty.
    resolved = select_compatible_model(target, models)
    if resolved == target:
        # select_compatible_model returns the same string only when it is
        # an exact match, but tier 1 above already covered that case. Guard
        # against an unexpected logic shift in the selector.
        return True, "", resolved
    available_short = ", ".join(models[:5])
    warning = (
        f"Ollama model '{target}' not installed; using '{resolved}' instead "
        f"(available: {available_short}). To use the original tag run: "
        f"'ollama pull {target}'"
    )
    return True, warning, resolved


def _ollama_strip_preamble(text: str) -> str:
    """Strip typical LLM response artifacts so XTTS does not synthesise
    preambles/disclaimers/notes as audio (which causes atempo outliers).

    Cleaning pipeline (order is critical):
      0. Qwen3 chain-of-thought: closed or orphaned <think>/<thinking>/
         <reasoning> blocks (orphaned = output truncated by num_predict).
         Must be removed FIRST — they contain LLM-specific syntax that can
         match patterns in later steps and leave dirty residues.
      1. Markdown code fences ```...``` (some models wrap their output).
      2. Bold/italic markers **x** *x* ***x***.
      3. Multi-language preambles (“Ecco la traduzione:”, “Here's the
         translation:”, “Sure!”, 好的/这是/翻译, etc.) — case-insensitive,
         multiline.
      4. Parenthetical commentary notes with keywords typical of model
         self-commentary (kept natural, fits within, ho mantenuto…).
         Legitimate parentheses in the original text are NOT touched.
      5. Square-bracket notes [note: ...], [spoken, ...].
      6. Standalone “Note: ...”, “Nota: ...”, “N.B. ...” lines.
      7. Outer quotation marks “...” '...' «...» „…” “…”.
      8. Collapse multiple whitespace/newlines → single space (avoids long
         pauses during XTTS synthesis).
    """
    if not text:
        return ""
    import re as _re
    t = text.strip()

    # 0. Qwen3 chain-of-thought: strip <think>...</think> blocks that can
    #    appear when /no_think is ignored (e.g. fine-tuned Qwen3 that bypasses
    #    the toggle, or an old Ollama version that ignores `think:false`).
    #    Captures both the standard tag and common variants (<thinking>,
    #    <reasoning>) used by Qwen3-derived models.
    THINK_BLOCK_RE = _re.compile(
        r"<\s*(think|thinking|reasoning)\s*>[\s\S]*?<\s*/\s*\1\s*>",
        flags=_re.IGNORECASE,
    )
    t = THINK_BLOCK_RE.sub("", t)
    # 0b. Unclosed opening tags (output truncated by num_predict): if a
    #     <think> has no matching </think>, strip everything up to the next
    #     double newline or end of string. Prevents handing a half-finished
    #     reasoning block to XTTS.
    ORPHAN_THINK_RE = _re.compile(
        r"<\s*(think|thinking|reasoning)\s*>[\s\S]*?(?=\n\n|$)",
        flags=_re.IGNORECASE,
    )
    t = ORPHAN_THINK_RE.sub("", t)
    t = t.strip()

    # 1. Unwrap markdown code fences ```...```, preserving the inner content.
    #    Some models wrap the translated text inside a code fence.
    t = _re.sub(r"```[a-zA-Z0-9]*\n?([\s\S]*?)```", r"\1", t)
    # 2. Strip markdown bold/italic markers (preserve the inner content)
    t = _re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", t)
    # 3. Multi-language preambles (IT, EN, FR, ES, DE, ZH). Applied in a
    #    fixed-point loop (max 6 passes) so concatenated prefixes like
    #    "Sure! Here's the translation:" or "好的这是翻译：" are consumed one
    #    by one. Each pattern ends with `\s*` / `:?\s*` to absorb trailing
    #    whitespace before the next prefix.
    PREAMBLE_PATTERNS = [
        # EN/IT "Here's the translation:" — including variants "concisa", "tradotta"
        r"^(?:here'?s?|this is|the|la|le|il)\s+(?:the\s+)?(?:concise\s+)?translation(?:\s+(?:concisa|per\s+\S+|tradotta))?\s*[:.\-]?\s*",
        # IT "Ecco la/il traduzione [concisa/per doppiaggio/tradotta]:"
        r"^ecco(?:\s+(?:la|il))?(?:\s+traduzione)?(?:\s+(?:concisa|per\s+\S+|tradotta))?\s*[:.\-]?\s*",
        # Singolo token "Traduzione:" / "Translation:" / "Übersetzung:" / "Traducción:"
        r"^(?:traduzione|translated|translation|übersetzung|traducción|traduction)\s*[:.\-]?\s*",
        # Acknowledgment: "Ok,", "Sure!", "Certainly.", "Certo!", "Bien sûr,"
        r"^(?:ok|sure|certainly|of course|certo|bien sûr)\s*[,.!]?\s*",
        # Cinese: "好的" (OK), "这是" (this is), "翻译：" (translation:)
        r"^好的\s*[，,:：]?\s*",
        r"^这是\s*[，,:：]?\s*",
        r"^翻译\s*[：:]\s*",
        # "Per favore" (acknowledgment) — NOTE: "N.B.", "Note:", "Nota bene:",
        # "Please note:" are handled at step 6 as whole lines (they consume
        # the entire disclaimer sentence, not just the prefix).
        r"^per favore\s*[,:.\-]?\s*",
    ]
    for _ in range(6):
        prev = t
        for pat in PREAMBLE_PATTERNS:
            t = _re.sub(pat, "", t, count=1, flags=_re.IGNORECASE | _re.MULTILINE)
        if t == prev:
            break
    # 4. Parenthetical notes/disclaimers with model self-commentary keywords.
    #    Deliberately conservative: avoids false positives on content
    #    parentheses (e.g. "(2020)", "(directed by Nolan)"). Non-greedy match.
    COMMENTARY_RE = _re.compile(
        r"\(\s*(?:note|n\.?\s*b\.?|nota|hint|tip|keeping|"
        r"kept|fits?\s+(?:well\s+)?within|target\s+reading|"
        r"natural|spoken|concise|shortened|translated|nota\s+bene|"
        r"ho\s+mantenuto|mantenendo|per\s+rimanere)"
        r"[^)]*?\)",
        flags=_re.IGNORECASE,
    )
    t = COMMENTARY_RE.sub("", t)
    # 5. Square-bracket notes [note:...], [spoken, natural], etc.
    BRACKET_NOTE_RE = _re.compile(
        r"\[\s*(?:note|nota|comment|spoken|dubbing)[^\]]*?\]",
        flags=_re.IGNORECASE,
    )
    t = BRACKET_NOTE_RE.sub("", t)
    # 6. Riga isolata "Note: ..." / "Nota: ..." / "Disclaimer: ..." / "N.B. ..."
    #    Also consumes the preceding newline to avoid double spaces after
    #    whitespace collapse (step 8).
    FINAL_NOTE_LINE_RE = _re.compile(
        r"(?:^|\n)[ \t]*"
        r"(?:note|nota|nota\s+bene|n\.?\s*b\.?|please\s+note|disclaimer|observation)"
        r"\s*[:\-]\s*[^\n]*",
        flags=_re.IGNORECASE,
    )
    t = FINAL_NOTE_LINE_RE.sub("", t)
    # 7. Strip outer paired quotation marks (open/close). Loop applied because
    #    there can be multiple nested layers like "\"«testo»\"".
    QUOTE_PAIRS = [
        ("\"", "\""), ("'", "'"),
        ("«", "»"), ("“", "”"), ("„", "”"), ("„", "“"),
    ]
    for _ in range(3):
        t = t.strip()
        peeled = False
        for open_q, close_q in QUOTE_PAIRS:
            if len(t) > len(open_q) + len(close_q) and t.startswith(open_q) and t.endswith(close_q):
                t = t[len(open_q):-len(close_q)]
                peeled = True
                break
        if not peeled:
            break
    # 8. Collapse multiple whitespace and newlines → single space (avoids long
    #    pauses during XTTS synthesis)
    t = _re.sub(r"\s+", " ", t)

    # 9. "Isolated" / orphaned punctuation that XTTS would pronounce literally
    #    as "dot", "comma", or emit as sharp audible clicks ("says the dot
    #    out loud at the end"). Real cases observed in Qwen3 output:
    #      ".  Buongiorno a tutti."   (stripped preamble leaves a leading ".")
    #      "Buongiorno a tutti . . ."  (Qwen repeats closing punctuation)
    #      ".\nBuongiorno"             (blank line containing only punctuation)
    #      "Buongiorno , a tutti"      (space before comma)
    #
    # Sequence: leading isolated punct → multiple consecutive marks → space
    # before punct → final tidy. Run AFTER the whitespace collapse so it
    # operates on an already single-space-normalised string.
    LEADING_PUNCT_RE   = _re.compile(r"^[\s.,;:!?\-–—…]+")
    REPEATED_PUNCT_RE  = _re.compile(r"([.,;:!?])(?:\s*\1)+")
    SPACE_BEFORE_RE    = _re.compile(r"\s+([.,;:!?])")
    DANGLING_PUNCT_RE  = _re.compile(r"\s+[.,;:!?\-–—…]+\s*$")  # tail isolato
    t = LEADING_PUNCT_RE.sub("", t)
    t = REPEATED_PUNCT_RE.sub(r"\1", t)
    t = SPACE_BEFORE_RE.sub(r"\1", t)
    t = DANGLING_PUNCT_RE.sub(".", t)  # if the tail has orphan punct, replace with a single "."

    return t.strip()


# ── Ollama auto-setup (v2.0.1) ─────────────────────────────────────────────
# Goal: zero manual setup for the end user. Same strategy already used for
# ffmpeg (on-demand download) and Git for Windows (auto-installer). The
# functions below are pure helpers — no Tk, no global state: they accept an
# optional log_cb to stream output to the GUI, and register subprocesses in
# the global registry so `_on_close` can terminate them.

def _ollama_find_binary() -> str | None:
    """Return the path to the `ollama` binary if found, otherwise None.

    Linux/macOS: uses `shutil.which`. Windows: `shutil.which` + fallback to
    the official installer's default paths (`%LOCALAPPDATA%\\Programs\\Ollama`
    and `%ProgramFiles%\\Ollama`). Necessary because on Windows, immediately
    after a silent install the current process PATH is not yet updated.
    """
    p = shutil.which("ollama")
    if p:
        return p
    if sys.platform.startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            # Official Ollama installer (per-user install)
            Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe",
            # Official Ollama installer system-wide (rare, requires admin)
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Ollama" / "ollama.exe",
            # winget install Ollama.Ollama → symlink in WinGet/Links (on Win11
            # this is in PATH by default; on Win10 often not — explicit fallback needed)
            Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ollama.exe",
        ]
        for c in candidates:
            try:
                if c.is_file():
                    return str(c)
            except OSError:
                continue
    return None


def _ollama_is_daemon_running(api_url: str, timeout: float = 2.0) -> bool:
    """Probe `/api/tags` with a short timeout. Returns True if the daemon responds 2xx."""
    import requests
    base = api_url.rstrip("/")
    try:
        r = requests.get(f"{base}/api/tags", timeout=timeout)
        return r.status_code < 400
    except Exception:
        return False


def _ollama_wait_for_daemon(api_url: str, wait_seconds: float = 12.0,
                            poll_interval: float = 1.0) -> bool:
    """Poll `_ollama_is_daemon_running` for up to `wait_seconds`. Returns True if it responds.

    Used after installing Ollama Desktop on Windows: the installer starts its
    own embedded daemon but with a 5–10 s delay after the install completes.
    Without this wait our fallback `ollama serve` would start and fail with
    port-already-in-use.
    """
    import time
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if _ollama_is_daemon_running(api_url, timeout=1.5):
            return True
        time.sleep(poll_interval)
    return False


def _ollama_start_daemon(
    binary: str,
    api_url: str = "http://localhost:11434",
    wait_seconds: float = 15.0,
    log_cb=None,
) -> tuple[bool, str]:
    """Start `ollama serve` detached and wait for `/api/tags` to respond.

    Returns (ok, message). `message` is the path to the log tempfile on
    failure, empty string on success. The subprocess is registered in
    `_active_subprocesses` so `_on_close` can terminate it.
    """
    log = log_cb or (lambda s: None)

    # Log file for debugging: on Windows there is no console, so without this
    # we lose the daemon's stderr if it starts and then crashes.
    log_file = tempfile.NamedTemporaryFile(
        prefix="ollama-serve-", suffix=".log", delete=False, mode="w",
        encoding="utf-8",
    )
    log_path = log_file.name
    log_file.close()
    fh = open(log_path, "w", encoding="utf-8")

    # start_new_session/CREATE_NEW_PROCESS_GROUP: detach from the main process
    # so closing the GUI does not kill the daemon (unless `_on_close`
    # explicitly does so via the registry).
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": fh,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform.startswith("win"):
        # CREATE_NEW_PROCESS_GROUP = 0x00000200. On Windows `start_new_session`
        # does not exist; use the creationflags equivalent instead.
        kwargs["creationflags"] = 0x00000200
    else:
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen([binary, "serve"], **kwargs)
    except Exception as e:
        fh.close()
        return False, f"Failed to spawn `ollama serve`: {e} (log: {log_path})"

    _register_subprocess(proc)

    # Polling: wait at most wait_seconds. Exit-code check: if the daemon dies
    # immediately (port already in use, broken config), stop waiting early.
    import time
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            # Daemon died before responding
            fh.close()
            _unregister_subprocess(proc)
            try:
                tail = Path(log_path).read_text(encoding="utf-8", errors="replace")[-500:]
            except Exception:
                tail = "(log unreadable)"
            log(f"     ! ollama serve exited early (rc={proc.returncode}): {tail}\n")
            return False, f"ollama serve exited (rc={proc.returncode}). Log: {log_path}"
        if _ollama_is_daemon_running(api_url, timeout=1.5):
            log(f"     [+] Ollama daemon attivo su {api_url}\n")
            # NB: fh is intentionally left open — the daemon keeps writing
            # to it for the entire session and it will be closed when proc exits.
            return True, ""
        time.sleep(0.5)

    # Timeout
    log(f"     ! Ollama daemon non ha risposto entro {wait_seconds:.0f}s (log: {log_path})\n")
    return False, f"Daemon did not become ready within {wait_seconds:.0f}s. Log: {log_path}"


def _ollama_install_linux(log_cb=None, timeout_s: int = 300) -> tuple[bool, str]:
    """Install Ollama via the official `curl -fsSL … | sh` script.

    Requires sudo to write to /usr/local/bin. If sudo is not available,
    returns an actionable message instead of failing silently.
    """
    log = log_cb or (lambda s: None)

    if not shutil.which("curl"):
        return False, (
            "curl non trovato. Installa curl (es. `sudo apt install curl`) "
            "e riprova, oppure installa Ollama manualmente da https://ollama.com/download"
        )

    # The official script requires root privileges. Try pkexec then sudo.
    prefixes: list[list[str]] = []
    if shutil.which("pkexec"):
        prefixes.append(["pkexec", "sh", "-c"])
    if shutil.which("sudo"):
        prefixes.append(["sudo", "sh", "-c"])
    prefixes.append(["sh", "-c"])  # root-less fallback (works only if already root)

    install_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
    last_err = ""
    for prefix in prefixes:
        cmd = prefix + [install_cmd]
        log(f"     Running: {' '.join(prefix)} <install.sh>\n")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError as e:
            last_err = f"{e.__class__.__name__}: {e}"
            continue

        _register_subprocess(proc)
        watchdog = threading.Timer(timeout_s, proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log(f"     {line}\n")
            proc.wait(timeout=30)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill(); proc.wait(timeout=10)
        finally:
            watchdog.cancel()
            _unregister_subprocess(proc)

        if proc.returncode == 0:
            return True, ""
        last_err = f"exit {proc.returncode} (prefix={prefix[0]})"

    return False, (
        f"Ollama install script failed ({last_err}). "
        f"Installa manualmente: curl -fsSL https://ollama.com/install.sh | sh"
    )


def _ollama_install_windows(log_cb=None, timeout_s: int = 600) -> tuple[bool, str]:
    """Download OllamaSetup.exe and launch it in fully silent mode.

    The Ollama installer is based on Inno Setup. We use the flag set
    `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL`:
      - `/VERYSILENT`: no wizard, no progress UI (`/SILENT` alone still
        shows a progress bar that may require user input);
      - `/SUPPRESSMSGBOXES`: suppresses default message boxes;
      - `/NORESTART`: do not reboot after installation;
      - `/NOCANCEL`: the user cannot abort via the cancel button.
    Without this complete flag set the subprocess can block waiting for
    user input until the timeout expires.

    Post-install, we update the current process PATH by appending the
    installer's default directory so `_ollama_find_binary` works without
    restarting the GUI.
    """
    log = log_cb or (lambda s: None)
    url = "https://ollama.com/download/OllamaSetup.exe"
    setup_path = Path(tempfile.gettempdir()) / "OllamaSetup.exe"

    log(f"     Scaricando Ollama (~1 GB) da {url}...\n")
    try:
        from urllib.request import Request, urlopen
        req = Request(url, headers={"User-Agent": "VideoTranslatorAI/2.0"})
        downloaded = 0
        last_pct = -1
        with urlopen(req, timeout=120) as r, open(setup_path, "wb") as out:
            total = int(r.headers.get("Content-Length") or 0)
            chunk = 256 * 1024
            while True:
                buf = r.read(chunk)
                if not buf:
                    break
                out.write(buf)
                downloaded += len(buf)
                if total > 0:
                    pct = min(100, downloaded * 100 // total)
                    # Log every 5% to avoid flooding the GUI
                    if pct // 5 != last_pct // 5:
                        log(f"     Download... {pct}%\n")
                        last_pct = pct
    except Exception as e:
        with contextlib.suppress(Exception):
            setup_path.unlink(missing_ok=True)
        return False, f"Download fallito: {e}"

    log("     Avvio installer silent (richiede UAC)...\n")
    # Inno Setup silent install
    try:
        proc = subprocess.Popen(
            [str(setup_path),
             "/VERYSILENT", "/SUPPRESSMSGBOXES",
             "/NORESTART", "/NOCANCEL"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
    except Exception as e:
        return False, f"Impossibile lanciare installer: {e}"

    _register_subprocess(proc)
    watchdog = threading.Timer(timeout_s, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log(f"     {line}\n")
        proc.wait(timeout=30)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill(); proc.wait(timeout=10)
    finally:
        watchdog.cancel()
        _unregister_subprocess(proc)
        with contextlib.suppress(Exception):
            setup_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        # rc=1223 = ERROR_CANCELLED on Windows (user clicked "No" on the
        # UAC prompt for the Ollama installer). The cryptic "rc=1223" message
        # is meaningless to end users — translate it into plain language.
        # rc=1602 = ERROR_INSTALL_USEREXIT (voluntary cancel without UAC).
        if proc.returncode in (1223, 1602):
            return False, (
                "Installazione annullata dall'utente (UAC negato o annullato). "
                "Riavvia la traduzione e accetta il prompt UAC, oppure scarica "
                "manualmente da https://ollama.com/download"
            )
        return False, (
            f"Installer exit rc={proc.returncode}. "
            f"Scarica e installa manualmente da https://ollama.com/download"
        )

    # Post-install: update the current process PATH with the Ollama installer's
    # default directory. This avoids having to restart the GUI.
    default_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    if default_dir.is_dir():
        cur_path = os.environ.get("PATH", "")
        if str(default_dir) not in cur_path:
            os.environ["PATH"] = cur_path + os.pathsep + str(default_dir)
    return True, ""


def _ollama_install_macos(log_cb=None, timeout_s: int = 600) -> tuple[bool, str]:
    """Try `brew install ollama` if Homebrew is available, otherwise return a
    manual install message with a link to the .dmg. We do not auto-download
    the .dmg because it requires user interaction for the drag-and-drop.
    """
    log = log_cb or (lambda s: None)
    if shutil.which("brew"):
        log("     Installazione via Homebrew: brew install ollama\n")
        try:
            proc = subprocess.Popen(
                ["brew", "install", "ollama"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
        except Exception as e:
            return False, f"brew install fallito: {e}"
        _register_subprocess(proc)
        watchdog = threading.Timer(timeout_s, proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log(f"     {line}\n")
            proc.wait(timeout=30)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill(); proc.wait(timeout=10)
        finally:
            watchdog.cancel()
            _unregister_subprocess(proc)
        if proc.returncode == 0:
            return True, ""
        return False, f"brew exit rc={proc.returncode}"

    return False, (
        "Homebrew non trovato. Installa Ollama manualmente scaricando il .dmg "
        "da https://ollama.com/download, poi riprova."
    )


def _ollama_install(log_cb=None) -> tuple[bool, str]:
    """Cross-platform dispatch for the Ollama installation."""
    if sys.platform.startswith("win"):
        return _ollama_install_windows(log_cb=log_cb)
    if sys.platform == "darwin":
        return _ollama_install_macos(log_cb=log_cb)
    # Linux + altri Unix
    return _ollama_install_linux(log_cb=log_cb)


def _ollama_pull_model(
    model: str,
    binary: str | None = None,
    log_cb=None,
    timeout_s: int = 1200,
) -> tuple[bool, str]:
    """Run `ollama pull <model>`, streaming the output to the GUI.

    `timeout_s` is generous (20 min default) because models are large
    (~4 GB) and connections can be slow. The subprocess is registered in
    the global registry for cleanup on `_on_close`.
    """
    log = log_cb or (lambda s: None)
    ollama_bin = binary or _ollama_find_binary()
    if not ollama_bin:
        return False, "ollama binary non trovato"

    log(f"     Scaricando modello {model} (può richiedere diversi minuti)...\n")
    # CREATE_NO_WINDOW (0x08000000) prevents Windows from popping a visible
    # console window for the ollama.exe child process (Go binary, console
    # subsystem). Without this the user sees a black cmd window pop up over
    # the GUI for the entire 5+ GB download. Linux/macOS ignore the flag.
    popen_kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if sys.platform.startswith("win"):
        popen_kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen([ollama_bin, "pull", model], **popen_kwargs)
    except Exception as e:
        return False, f"Failed to spawn `ollama pull`: {e}"

    _register_subprocess(proc)
    watchdog = threading.Timer(timeout_s, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    # `ollama pull` uses \r to redraw progress 10x/sec, mixes spinner chars
    # (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) for unbounded ops like sha256 verify, AND emits ANSI
    # cursor-control escape sequences. Naive line capture produced thousands
    # of duplicate log entries. We need a STABLE key per logical state
    # (e.g. "pulling a3de86cd1c13:") that ignores the changing %/bytes,
    # otherwise consecutive progress ticks always look "different".
    import re
    import time as _time
    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    _ANSI_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    _PCT_RE = re.compile(r"(\d{1,3})%")
    # Stable-key extractors: collapse all variable parts (digits, units,
    # progress bar fill, etc.) so "pulling X: 5% ... 250 MB" and
    # "pulling X: 6% ... 300 MB" map to the same key.
    _STABLE_PREFIX = re.compile(
        r'^(pulling\s+[\w.\-]+:|verifying\s+[\w.\-]+\s+[\w.\-]+|'
        r'writing\s+manifest|pulling\s+manifest|success|removing\s+\w+)',
        re.IGNORECASE,
    )

    def _stable_key(s: str) -> str:
        m = _STABLE_PREFIX.match(s)
        return m.group(1).lower() if m else s

    last_key = ""
    last_pct_seen = -1
    last_log_t = 0.0
    try:
        for line in proc.stdout:
            # Strip ANSI escape codes that Ollama emits for cursor control.
            line = _ANSI_RE.sub('', line)
            # Ollama mixes \r and \n. Split on both to recover individual frames.
            for fragment in line.replace("\r", "\n").split("\n"):
                # Strip spinner chars + whitespace
                fragment = "".join(c for c in fragment if c not in _SPINNER).strip()
                if not fragment:
                    continue
                key = _stable_key(fragment)
                now = _time.monotonic()
                if key == last_key:
                    # Same logical state — throttle progress ticks to one
                    # log entry every 5% delta OR every 2 seconds OR at 100%.
                    m = _PCT_RE.search(fragment)
                    if m:
                        pct = int(m.group(1))
                        is_complete = pct == 100 and last_pct_seen != 100
                        if pct - last_pct_seen >= 5 or now - last_log_t >= 2.0 or is_complete:
                            log(f"     {fragment}\n")
                            last_pct_seen = pct
                            last_log_t = now
                    # else: pure spinner or post-100 duplicate, drop silently.
                    continue
                # New logical state → always log.
                log(f"     {fragment}\n")
                last_key = key
                last_log_t = now
                m = _PCT_RE.search(fragment)
                last_pct_seen = int(m.group(1)) if m else -1
        proc.wait(timeout=30)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill(); proc.wait(timeout=10)
    finally:
        watchdog.cancel()
        _unregister_subprocess(proc)

    if proc.returncode != 0:
        return False, f"ollama pull {model} failed (rc={proc.returncode})"
    return True, ""


