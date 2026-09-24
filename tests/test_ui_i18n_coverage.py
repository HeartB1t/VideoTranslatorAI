import re
import unittest
from pathlib import Path

import video_translator_gui as legacy

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


if __name__ == "__main__":
    unittest.main()
