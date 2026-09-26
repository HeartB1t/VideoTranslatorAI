"""Keep the complete localized READMEs aligned with the English document.

These offline checks verify structure and executable examples, not linguistic
quality. Translation wording still needs editorial review when content changes.
"""
import collections
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "docs" / "i18n"
LANGUAGES = "ar zh cs da nl fi fr de el hi hu id it ja ko no pl pt ro ru es sv tr uk vi".split()
LINK = re.compile(r"\]\(([^)]+)\)")


def structure(text):
    """Ignore prose wrapping, but retain ordered block and table structure."""
    result = []
    fenced = False
    paragraph = False
    for line in text.splitlines():
        if line.startswith("```"):
            result.append(("fence", line))
            fenced = not fenced
            paragraph = False
        elif fenced:
            command, sep, comment = line.partition("#")
            result.append(("code", command.rstrip(), bool(sep)))
        elif not line.strip():
            paragraph = False
        elif line.startswith("|"):
            cells = line.split("|")[1:-1]
            separator = bool(re.fullmatch(r"[|:\s-]+", line))
            result.append(("table", len(cells), separator))
            paragraph = False
        elif re.match(r"^#{1,6} ", line):
            result.append(("heading", len(line.split(" ", 1)[0])))
            paragraph = False
        elif re.match(r"^\s*(?:- |\d+\. )", line):
            prefix = re.match(r"^(\s*)(- |\d+\. )", line)
            result.append(("list", len(prefix[1]), prefix[2]))
            paragraph = True
        elif line.startswith(">"):
            if not paragraph:
                result.append(("quote",))
            paragraph = True
        elif not paragraph:
            result.append(("paragraph",))
            paragraph = True
    if fenced:
        raise AssertionError("Unclosed code fence")
    return result


def links(path, text):
    result = []
    for target in LINK.findall(text):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            result.append(target)
            continue
        resolved = (path.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(ROOT):
            raise AssertionError(f"Link escapes repository: {path.name}: {target}")
        if not resolved.exists():
            raise AssertionError(f"Broken link: {path.name}: {target}")
        result.append(str(resolved.relative_to(ROOT)) + "#" + parsed.fragment)
    return collections.Counter(result)


def english_fragments(text):
    """Find long copied prose, ignoring code and the native-language selector."""
    prose = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and "README.ar.md)" not in line:
            line = re.sub(r"`[^`]+`|\]\([^)]+\)|https?://\S+", " ", line)
            prose.append(line)
    words = re.findall(r"\b[a-zA-Z]{3,}\b", " ".join(prose).lower())
    return {tuple(words[i:i + 12]) for i in range(len(words) - 11)}


class ReadmeTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_path = ROOT / "README.md"
        cls.source = cls.source_path.read_text(encoding="utf-8")

    def test_all_translations_live_in_dedicated_directory(self):
        expected = {f"README.{lang}.md" for lang in LANGUAGES}
        self.assertEqual({p.name for p in I18N.glob("README.*.md")}, expected)
        self.assertFalse(list(ROOT.glob("README.*.md")))
        self.assertFalse((ROOT / "README_LANGUAGES.md").exists())

    def test_complete_structure_and_commands_match(self):
        expected = structure(self.source)
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                text = (I18N / f"README.{lang}.md").read_text(encoding="utf-8")
                self.assertEqual(structure(text), expected)
                self.assertNotRegex(text, r"ZXQ[UP]\d+QXZ")
                self.assertNotRegex(text, "[\u2013\u2014]")

    def test_inline_code_preserved_in_corresponding_sections(self):
        def sections(text):
            return [collections.Counter(re.findall(r"`([^`\n]+)`", section))
                    for section in re.split(r"^#{1,6} .*\n", text, flags=re.M)]
        expected = sections(self.source)
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                text = (I18N / f"README.{lang}.md").read_text(encoding="utf-8")
                self.assertEqual(sections(text), expected)

    def test_links_preserve_destinations(self):
        expected = links(self.source_path, self.source)
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                path = I18N / f"README.{lang}.md"
                self.assertEqual(links(path, path.read_text(encoding="utf-8")), expected)

    def test_index_links_all_26_languages(self):
        path = I18N / "README.md"
        actual = links(path, path.read_text(encoding="utf-8"))
        expected = {f"docs/i18n/README.{lang}.md#" for lang in LANGUAGES}
        expected.add("README.md#")
        self.assertEqual(set(actual), expected)

    def test_no_long_untranslated_english_passages(self):
        source = english_fragments(self.source)
        for lang in LANGUAGES:
            with self.subTest(language=lang):
                text = (I18N / f"README.{lang}.md").read_text(encoding="utf-8")
                self.assertFalse(source & english_fragments(text))


if __name__ == "__main__":
    unittest.main()
