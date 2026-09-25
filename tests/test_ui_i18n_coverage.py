import ast
import re
import unittest
from pathlib import Path

import video_translator_gui as legacy
from test_ui_theme_tk import HAS_DISPLAY, built_app

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "video_translator_gui.py"

UI_STRINGS = legacy.UI_STRINGS
UI_LANG_OPTIONS = legacy.UI_LANG_OPTIONS

# Solo placeholder con nome identificatore (es. {model}, {lang}); {}
# posizionali/vuoti non contano come placeholder nominale.
_NAMED_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-zA-Z0-9_]*)\}")
_PERCENT_PLACEHOLDER_RE = re.compile(r"%[sd]")
_S_CALL_RE = re.compile(r'(?:self\._s|ui_s|_s)\(\s*"([^"]+)"')


def _all_keys() -> set[str]:
    keys: set[str] = set()
    for bucket in UI_STRINGS.values():
        keys.update(bucket.keys())
    return keys


def _placeholders(value: str) -> set[str]:
    found = set(_NAMED_PLACEHOLDER_RE.findall(value))
    found.update(_PERCENT_PLACEHOLDER_RE.findall(value))
    return found


class UILangOptionsCoverageTests(unittest.TestCase):
    def test_lang_options_and_ui_strings_buckets_match(self):
        option_codes = {code for code, _ in UI_LANG_OPTIONS}
        bucket_codes = set(UI_STRINGS.keys())

        missing_buckets = sorted(option_codes - bucket_codes)
        orphan_buckets = sorted(bucket_codes - option_codes)

        self.assertEqual(
            missing_buckets,
            [],
            f"Lingue in UI_LANG_OPTIONS senza bucket in UI_STRINGS: {missing_buckets}",
        )
        self.assertEqual(
            orphan_buckets,
            [],
            f"Bucket UI_STRINGS orfani (assenti da UI_LANG_OPTIONS): {orphan_buckets}",
        )


class UIStringsKeyCoverageTests(unittest.TestCase):
    def test_every_key_exists_in_every_language(self):
        all_keys = _all_keys()
        missing = [
            (lang, key)
            for lang in sorted(UI_STRINGS.keys())
            for key in sorted(all_keys)
            if key not in UI_STRINGS[lang]
        ]
        if missing:
            details = "\n".join(f"  - {lang}: {key}" for lang, key in missing)
            self.fail(
                f"{len(missing)} coppie (lingua, chiave) mancanti in UI_STRINGS:\n{details}"
            )


class UIStringsValueSanityTests(unittest.TestCase):
    def test_no_empty_or_placeholder_like_values(self):
        problems = []
        for lang in sorted(UI_STRINGS.keys()):
            for key, value in UI_STRINGS[lang].items():
                if not isinstance(value, str):
                    continue
                if value.strip() == "":
                    problems.append((lang, key, "valore vuoto/solo spazi"))
                elif value.strip() == key:
                    problems.append((lang, key, "valore identico alla propria chiave"))
        if problems:
            details = "\n".join(
                f"  - {lang}.{key}: {reason}" for lang, key, reason in sorted(problems)
            )
            self.fail(f"{len(problems)} valori sospetti in UI_STRINGS:\n{details}")


class UIStringsUsedKeysTests(unittest.TestCase):
    def test_keys_called_in_source_exist_in_it_and_en(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        used_keys = sorted(set(_S_CALL_RE.findall(source)))

        self.assertTrue(
            used_keys,
            "Nessuna chiamata a self._s(...)/ui_s(...)/_s(...) trovata nel sorgente: "
            "la regex di scansione è probabilmente rotta",
        )

        missing = [
            (lang, key)
            for key in used_keys
            for lang in ("it", "en")
            if key not in UI_STRINGS[lang]
        ]
        if missing:
            details = "\n".join(f"  - {lang}: {key}" for lang, key in sorted(missing))
            self.fail(
                f"{len(missing)} chiavi usate nel codice ma assenti da it/en:\n{details}"
            )


class UIStringsPlaceholderConsistencyTests(unittest.TestCase):
    def test_format_placeholders_match_across_languages(self):
        all_keys = _all_keys()
        mismatches = []

        for key in sorted(all_keys):
            langs_with_key = [lang for lang in sorted(UI_STRINGS) if key in UI_STRINGS[lang]]
            if not langs_with_key:
                continue
            reference_lang = "it" if "it" in langs_with_key else langs_with_key[0]
            reference_value = UI_STRINGS[reference_lang][key]
            if not isinstance(reference_value, str):
                continue
            reference_placeholders = _placeholders(reference_value)

            for lang in langs_with_key:
                value = UI_STRINGS[lang][key]
                if not isinstance(value, str):
                    continue
                placeholders = _placeholders(value)
                if placeholders != reference_placeholders:
                    mismatches.append(
                        (
                            lang,
                            key,
                            sorted(placeholders),
                            sorted(reference_placeholders),
                            reference_lang,
                        )
                    )

        if mismatches:
            details = "\n".join(
                f"  - {lang}.{key}: placeholder {found} != {expected} (riferimento '{ref_lang}')"
                for lang, key, found, expected, ref_lang in sorted(mismatches)
            )
            self.fail(f"{len(mismatches)} incoerenze di placeholder tra lingue:\n{details}")


class UIStringsDynamicKeyFamiliesTests(unittest.TestCase):
    """Keys built at run time are invisible to _S_CALL_RE: assert each family."""

    _FSTRING_RE = re.compile(r'(?:self\._s|ui_s|_s)\(\s*f"([^"]+)"')
    _CB_RE = re.compile(r'\bcb\(\s*[\w.]+\s*,\s*"([^"]+)"')

    @staticmethod
    def _families() -> dict[str, list[str]]:
        return {
            "size_{k}": [f"size_{k}" for k in legacy._SCALES],
            "editor_tooltip_{f}": [
                f"editor_tooltip_{f}" for f in (
                    legacy._FLAG_TRANSLATION_FALLBACK,
                    legacy._FLAG_LENGTH_UNFIT,
                    legacy._FLAG_WHISPER_SUSPICIOUS,
                )
            ],
        }

    def test_every_fstring_family_in_source_is_known(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        found = set(self._FSTRING_RE.findall(source))
        self.assertTrue(found, "no f-string _s(...) call found: the scan regex is probably broken")
        unknown = sorted(found - set(self._families()))
        self.assertEqual(unknown, [], f"f-string key families without a test: {unknown}")

    def test_every_family_key_exists_in_every_language(self):
        missing = [
            (lang, key)
            for keys in self._families().values()
            for key in keys
            for lang in sorted(UI_STRINGS)
            if key not in UI_STRINGS[lang]
        ]
        self.assertEqual(missing, [], f"dynamic keys missing: {missing}")

    def test_checkbox_helper_keys_exist_in_every_language(self):
        source = SOURCE_PATH.read_text(encoding="utf-8")
        keys = sorted(set(self._CB_RE.findall(source)))
        self.assertGreaterEqual(len(keys), 5, "cb(...) scan found too few keys")
        missing = [(lang, key) for key in keys for lang in sorted(UI_STRINGS)
                   if key not in UI_STRINGS[lang]]
        self.assertEqual(missing, [], f"cb() keys missing: {missing}")


class PanelAndAccordionTitleSourceTests(unittest.TestCase):
    """Task 7: every card/accordion title argument must come from
    UI_STRINGS through self._s(...), never a literal string, so a future
    title cannot silently drop out of i18n."""

    @staticmethod
    def _title_calls():
        tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"), filename=str(SOURCE_PATH))
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == "_panel" and len(node.args) >= 3:
                calls.append(("_panel", node.args[2], node.lineno))
            elif node.func.attr == "_make_accordion_section" and len(node.args) >= 2:
                calls.append(("_make_accordion_section", node.args[1], node.lineno))
        return calls

    def test_title_arguments_are_translated_or_none(self):
        calls = self._title_calls()
        self.assertGreaterEqual(
            len(calls), 12,
            "too few _panel()/_make_accordion_section() calls found: "
            "the AST scan is probably broken",
        )
        bad = []
        for name, arg, lineno in calls:
            if isinstance(arg, ast.Constant) and arg.value is None:
                continue  # _panel(..., None, ...): a card with no title
            is_translated = (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Attribute)
                and arg.func.attr == "_s"
            )
            if not is_translated:
                bad.append((name, lineno))
        if bad:
            details = "\n".join(
                f"  - line {lineno}: {name}(...) title is not self._s(...) or None"
                for name, lineno in bad
            )
            self.fail(f"{len(bad)} card/accordion titles are not translated:\n{details}")


@unittest.skipUnless(HAS_DISPLAY, "needs a display (Tk)")
class PanelAndAccordionTitleI18nTests(unittest.TestCase):
    """Task 7: card and accordion section titles follow the UI language,
    and the drag order (`ui_panel_order`, keyed by panel id) never depends
    on the title text."""

    _PANEL_TITLE_KEYS = {
        "input": "panel_input",
        "translation": "panel_translation",
        "profile": "panel_profile",
        "start": "panel_start",
    }
    _SECTION_TITLE_ATTRS = {
        "_lbl_section_model": "section_model",
        "_lbl_section_engine": "section_engine",
        "_lbl_section_audio": "section_audio",
        "_lbl_section_voice_cloning": "section_voice_cloning",
        "_lbl_section_lip_sync": "section_lip_sync",
        "_lbl_section_diarization": "section_diarization",
        "_lbl_section_subtitles": "section_subtitles",
        "_lbl_section_hotwords": "section_hotwords",
    }
    # "fr" used to be the switch target, but several of these keys (e.g.
    # section_audio, "Audio" in both it and fr) share the exact same value
    # in the two languages, so a missing retext line could pass silently.
    # "ja" differs from "it" on every key above, so a dropped refresh line
    # always shows up as a real assertion failure.
    _TARGET_LANG = "ja"

    def test_panel_titles_follow_ui_language_and_ids_stay_stable(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "it"}) as (gui, app, _):
            for key in self._PANEL_TITLE_KEYS.values():
                self.assertNotEqual(
                    gui.UI_STRINGS["it"][key], gui.UI_STRINGS[self._TARGET_LANG][key],
                    f"{key!r} must differ between it and {self._TARGET_LANG!r}, "
                    "otherwise the switch below cannot prove the label was retexted",
                )
            for panel_id, key in self._PANEL_TITLE_KEYS.items():
                with self.subTest(panel=panel_id):
                    label = getattr(app, f"_lbl_panel_{panel_id}")
                    self.assertEqual(
                        label.cget("text"),
                        gui.App._title_upper(gui.UI_STRINGS["it"][key], "it"))
            panel_ids_before = sorted(app._panels.keys())
            order_before = list(app._panel_order)

            app._ui_lang.set(self._TARGET_LANG)
            app._apply_lang()

            for panel_id, key in self._PANEL_TITLE_KEYS.items():
                with self.subTest(panel=panel_id):
                    label = getattr(app, f"_lbl_panel_{panel_id}")
                    self.assertEqual(
                        label.cget("text"),
                        gui.App._title_upper(gui.UI_STRINGS[self._TARGET_LANG][key], self._TARGET_LANG))
            # The language switch retexts the labels only: panel identity
            # and the saved drag order are keyed by id, never by title text.
            self.assertEqual(sorted(app._panels.keys()), panel_ids_before)
            self.assertEqual(list(app._panel_order), order_before)

    def test_accordion_section_titles_follow_ui_language(self):
        with built_app({"ui_theme": "graphite", "ui_lang": "it"}) as (gui, app, _):
            for key in self._SECTION_TITLE_ATTRS.values():
                self.assertNotEqual(
                    gui.UI_STRINGS["it"][key], gui.UI_STRINGS[self._TARGET_LANG][key],
                    f"{key!r} must differ between it and {self._TARGET_LANG!r}, "
                    "otherwise the switch below cannot prove the label was retexted",
                )
            for attr, key in self._SECTION_TITLE_ATTRS.items():
                with self.subTest(section=attr):
                    label = getattr(app, attr)
                    self.assertEqual(label.cget("text"), gui.UI_STRINGS["it"][key])

            app._ui_lang.set(self._TARGET_LANG)
            app._apply_lang()

            for attr, key in self._SECTION_TITLE_ATTRS.items():
                with self.subTest(section=attr):
                    label = getattr(app, attr)
                    self.assertEqual(label.cget("text"), gui.UI_STRINGS[self._TARGET_LANG][key])


class TitleUpperCaseTests(unittest.TestCase):
    """_title_upper() must follow language-specific capitalization rules
    where plain str.upper() gets them wrong: Turkish dotted/dotless I, and
    Greek all-caps dropping the acute accent. A pure staticmethod, so this
    needs no Tk display."""

    def test_turkish_dotted_i_and_dotless_i(self):
        title_upper = legacy.App._title_upper
        self.assertEqual(title_upper(UI_STRINGS["tr"]["panel_input"], "tr"), "GİRİŞ")
        self.assertEqual(title_upper(UI_STRINGS["tr"]["panel_translation"], "tr"), "ÇEVİRİ")
        self.assertEqual(
            title_upper(UI_STRINGS["tr"]["panel_profile"], "tr"), "İŞ AKIŞI PROFİLİ")

    def test_greek_all_caps_drops_the_acute_accent(self):
        title_upper = legacy.App._title_upper
        self.assertEqual(title_upper(UI_STRINGS["el"]["panel_input"], "el"), "ΕΙΣΟΔΟΣ")
        self.assertEqual(title_upper(UI_STRINGS["el"]["panel_translation"], "el"), "ΜΕΤΑΦΡΑΣΗ")
        self.assertEqual(
            title_upper(UI_STRINGS["el"]["panel_profile"], "el"), "ΠΡΟΦΙΛ ΕΡΓΑΣΙΑΣ")

    def test_other_languages_still_use_plain_upper(self):
        title_upper = legacy.App._title_upper
        self.assertEqual(title_upper(UI_STRINGS["it"]["panel_input"], "it"), "INPUT")
        self.assertEqual(
            title_upper(UI_STRINGS["en"]["panel_translation"], "en"), "TRANSLATION")


if __name__ == "__main__":
    unittest.main()
