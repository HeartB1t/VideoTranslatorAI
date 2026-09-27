"""What the sdist and the wheel carry: the bundled icons, fonts and licences.

A wheel is installed outside the checkout, so the assets travel inside the
package (``videotranslator/assets``); the sdist keeps the repository layout.
Both are built for real with setuptools from a copy of the tracked files, as
pip would build them, without network access (no build isolation).
"""
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICONS = ("icon.ico", "icon.png", "icon_256.png")
FONTS = ("fonts/PixelifySans.ttf", "fonts/VT323-Regular.ttf",
         "fonts/OFL-PixelifySans.txt", "fonts/OFL-VT323.txt")

# One hook per process, as pypa/build does: two builds in the same process
# reuse setuptools state and the wheel lands in the sdist's folder.
_BUILD = (
    "import sys\n"
    "import setuptools.build_meta as backend\n"
    "print('BUILT:' + getattr(backend, sys.argv[1])(sys.argv[2]))\n"
)

_INSTALLED = (
    "import sys\n"
    "from pathlib import Path\n"
    "from videotranslator import resource_paths, ui_fonts\n"
    "print(resource_paths.assets_dir())\n"
    "print(ui_fonts.FONTS_DIR)\n"
    "print(','.join(ui_fonts.register_bundled_fonts(sys_platform='linux',"
    " home=Path(sys.argv[1]))))\n"
)


def _tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                             capture_output=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return [name for name in out.decode("utf-8").split("\0") if name]


def _can_build():
    try:
        import setuptools
    except ImportError:
        return "setuptools is not installed"
    major, minor = (int(part) for part in setuptools.__version__.split(".")[:2])
    if (major, minor) < (69, 0):
        return f"setuptools {setuptools.__version__} is older than the build requirement"
    if (major, minor) < (70, 1):
        try:
            import wheel  # noqa: F401 (bdist_wheel before setuptools 70.1)
        except ImportError:
            return "wheel is not installed"
    return ""


class PackageListTests(unittest.TestCase):
    def test_every_python_package_is_listed(self):
        # The package list is explicit (the assets need a package-dir entry),
        # so a new subpackage must be added by hand.
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        listed = set(config["tool"]["setuptools"]["packages"])
        for init in (ROOT / "videotranslator").rglob("__init__.py"):
            name = ".".join(init.parent.relative_to(ROOT).parts)
            with self.subTest(package=name):
                self.assertIn(name, listed)
        self.assertIn("videotranslator.assets", listed)


class DistributionContentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reason = _can_build()
        files = _tracked_files()
        if reason or files is None:
            raise unittest.SkipTest(reason or "git is not available")
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        source = cls.tmp / "source"
        for name in files:
            path = ROOT / name
            if path.is_file():
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, source / name)
        dist = cls.tmp / "dist"
        dist.mkdir()
        cls.sdist = dist / cls._build("build_sdist", source, dist)
        cls.wheel = dist / cls._build("build_wheel", source, dist)

    @classmethod
    def _build(cls, hook, source, dist):
        run = subprocess.run([sys.executable, "-c", _BUILD, hook, str(dist)], cwd=source,
                             capture_output=True, text=True, timeout=600)
        if run.returncode != 0:
            cls._tmp.cleanup()
            raise AssertionError(f"{hook} failed:\n" + run.stdout[-2000:] + run.stderr[-4000:])
        # setuptools logs to stdout too: the file name is the marked line.
        return [line[len("BUILT:"):] for line in run.stdout.splitlines()
                if line.startswith("BUILT:")][-1]

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_wheel_carries_icons_fonts_and_licences_inside_the_package(self):
        names = set(zipfile.ZipFile(self.wheel).namelist())
        for name in ICONS + FONTS:
            with self.subTest(name=name):
                self.assertTrue(f"videotranslator/assets/{name}" in names, "missing from the wheel")
        # Nothing at the top of site-packages, and no documentation image.
        self.assertFalse([name for name in names if name.startswith("assets/")])
        self.assertFalse([name for name in names if name.endswith("screenshot.png")])

    def test_the_sdist_keeps_the_repository_layout(self):
        with tarfile.open(self.sdist) as archive:
            names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        for name in ICONS + FONTS:
            with self.subTest(name=name):
                self.assertTrue(f"assets/{name}" in names, "missing from the sdist")

    def test_an_installed_wheel_finds_its_assets_outside_the_checkout(self):
        site = self.tmp / "site"
        with zipfile.ZipFile(self.wheel) as archive:
            archive.extractall(site)             # a pure wheel installs as unpacked
        home = self.tmp / "home"
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        env["PYTHONPATH"] = str(site)
        run = subprocess.run([sys.executable, "-s", "-c", _INSTALLED, str(home)],
                             cwd=self.tmp, env=env, capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(run.returncode, 0, run.stderr)
        assets, fonts, registered = run.stdout.strip().splitlines()[-3:]
        # samefile: Windows may spell the temp folder with 8.3 names (RUNNER~1).
        self.assertTrue(os.path.samefile(assets, site / "videotranslator" / "assets"), assets)
        self.assertTrue(os.path.samefile(fonts, site / "videotranslator" / "assets" / "fonts"), fonts)
        self.assertEqual(registered.split(","), ["PixelifySans.ttf", "VT323-Regular.ttf"])
        copied = home / ".local" / "share" / "fonts" / "VideoTranslatorAI" / "VT323-Regular.ttf"
        self.assertEqual(copied.read_bytes(), (ROOT / "assets" / "fonts" / "VT323-Regular.ttf").read_bytes())


if __name__ == "__main__":
    unittest.main()
