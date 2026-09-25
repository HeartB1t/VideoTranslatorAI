# Backlog hardening (2026-09-25)

Follow-ups of the Google rate-limit fix (commits 1f3c48e, cadcf66) and of the
final review of the UI themes plan. No spec: the requirements come from the
review findings listed in `_dev/CHANGELOG.md` (entries `[fix-google-ratelimit]`
and `[ui-themes]`) and from the operator's rules in the project CLAUDE.md.

## Global Constraints

- Work directly on `main`, local commits only. Never push.
- Commit messages: conventional commits (`fix`, `feat`, `ui`, `test`, `docs`,
  `refactor`, `chore`), imperative, explaining what and why. NEVER add a
  `Co-Authored-By` trailer.
- Never use the em dash (U+2014) or en dash (U+2013) anywhere: code, comments,
  docstrings, strings, docs, commit messages. Use `-`, a comma, a colon or
  parentheses.
- Every user-visible string goes in `UI_STRINGS` (`video_translator_gui.py`)
  in ALL 26 languages (it, en, ar, zh, cs, da, nl, fi, fr, de, el, hi, hu, id,
  ja, ko, no, pl, pt, ro, ru, es, sv, tr, uk, vi) with correct accents and
  spelling; `tests/test_ui_i18n_coverage.py` must stay green.
- Everything must work on Windows and Linux.
- Tests use `unittest`. Run them with `python3 -m unittest discover -s tests`
  (never `pytest` from the repo root). CI installs only `requirements-dev.txt`:
  no deep_translator, requests, torch, transformers. Tests must be hermetic
  (stand-in modules / mocks, no network, no real config or keyring). Tk tests
  must skip cleanly without a display (follow `tests/test_ui_theme_tk.py`).
- Before each commit: `python3 -m py_compile video_translator_gui.py
  videotranslator/*.py`, the full suite green, zero em/en dash in touched files.
- Do not touch `_backup_ui_redesign_20260617/`, `_demo_styles.py`, `_dev/`.
- One logical change per commit. No features beyond the task.

## Task 1: DeepL failed batches are no longer silent

In `videotranslator/translation.py` (DeepL branch of `translate_segments`),
a batch that still fails after `MAX_RETRIES` keeps the source text with no
flag and no warning. Required behaviour:
- every segment of a failed batch gets the `translation_fallback` quality
  flag (`add_quality_flag`, same as the Google path);
- at the end, when some segments failed, print one warning line with the
  count (`N/M`), like the Google path;
- when every non-empty segment failed, do not return a source-language
  result: raise inside the DeepL `try` so the existing
  `except Exception -> falling back to Google Translate` path takes over.
Tests in `tests/test_translation.py` with a stand-in `requests` module
(CI has no requests): partial failure flags only the failed batch and warns;
total failure falls back to Google (patch the Google path with the existing
stand-in modules helper).

## Task 2: per-request timeout on Google Translate

deep-translator calls `requests.get` without a timeout, so a hung connection
blocks the job forever. In the Google branch, run each
`translator.translate(text)` call with a timeout of 30 s (module constant
`_GOOGLE_REQUEST_TIMEOUT = 30.0`), e.g. through a single reusable
`concurrent.futures.ThreadPoolExecutor(max_workers=1)` shut down with
`wait=False` at the end of the branch (also on exceptions). A timeout counts
as a transient (throttling-class) error: it is retried with the same backoff
and counts toward the breaker. The hung worker thread is abandoned (daemon
behaviour acceptable; document it in a comment). If a timed-out call leaves
the single worker busy, later calls must not queue behind it forever: create
a fresh executor after a timeout. Tests: a stand-in translator that blocks on
an Event for the first call proves the timeout path (patch the constant to a
small value), then succeeds on retry; no real sleeps longer than ~1 s.

## Task 3: Ollama failing on every segment falls back to Google

When Ollama answers the health check but every per-segment call fails,
`translate_with_ollama` returns a result where every non-empty entry carries
`translation_fallback` and keeps the source text; the job then dubs the source
language with only a warning. In `translate_segments` (Ollama branch), after
the injected `ollama_translator` returns: if there is at least one non-empty
segment and every non-empty entry is flagged `translation_fallback` AND its
`text_tgt` equals its `text_src`, print a log line and fall through to the
Google path (engine-level fallback, same as when Ollama is unreachable).
Partial failures keep today's behaviour. Tests with a fake `ollama_translator`.

## Task 4: GUI worker error reporting

In `video_translator_gui.py`:
- In the batch worker (`_run_batch` -> `run_all`) and the URL worker
  (`_dispatch_download` -> `run`), the specific error dialog key
  (`_error_key_for`) must be used only when EVERY failed file had that same
  key; with mixed failures show the generic `msg_error`.
- Add Tk-free tests that drive `run_all` and the URL `run` synchronously
  (fake `self` via `types.SimpleNamespace` or a minimal stub, `threading.Thread`
  patched to run the target inline, `self.after` calling the function
  immediately, `translate_video` / `download_youtube` patched) and assert the
  arguments `_on_done` receives: success with fallback count summed across
  files; single TranslationUnavailableError -> `msg_translation_unavailable`;
  mixed errors -> generic. Also cover phase 1 of the editor flow
  (`_start_with_editor`): fallback count forwarded to `_open_editor`, error key
  forwarded to `_on_done`.

## Task 5: keyboard access to the settings gear and the accent dots

The header settings gear (`self._btn_settings`, a `tk.Label` with the gear
glyph, built in the header method near "settings gear") and the accent dots in
the settings window (`self._accent_dots`, `tk.Label` widgets built in
`_open_settings`) are mouse-only. Make them reachable and operable from the
keyboard: `takefocus=1`, activation with Return, KP_Enter and space, a visible
focus indication consistent with the theme (e.g. highlightthickness with the
palette accent / focus colour, recoloured correctly by the live recolour
logic), and a sensible Tab order. No new user-visible text. Tk tests (skip
without display) that focus each widget and generate the key event.

## Task 6: system theme detection off the Tk main thread

`videotranslator/ui_theme_tk.py` (`ThemeManager`, around the call to
`detect_system_dark()`) runs the detection on the main thread; the probes
(xfconf-query, gsettings, defaults, winreg) can take up to ~6 s in the worst
case. Required: the first paint must not wait on the detection. Start the
detection in a background thread; until it answers, use the last known value
cached in the UI config if available, otherwise dark; when the result arrives,
hand it back to the Tk thread with `after` and re-apply the theme only if the
"auto" theme is active and the value changed. No Tk calls from the worker
thread. Keep `detect_system_dark` itself unchanged unless needed. Tests: pure
tests for the caching/decision logic, a Tk test (skip without display) that the
apply path does not call the detector synchronously.

## Task 7: translate the hard-coded card and accordion titles

Card titles and accordion section titles in the main window (e.g. INPUT,
WORKFLOW PROFILE, TRADUZIONE and the accordion headers) include hard-coded
strings that do not follow the UI language. Move every such title to
`UI_STRINGS` keys in all 26 languages and make them update on UI language
change like the other labels (follow the existing refresh mechanism). The
drag-and-drop card order (`ui_panel_order`) must keep working: it must not rely
on the translated text. Extend the i18n coverage test so the titles are
covered.
