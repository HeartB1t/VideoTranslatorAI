import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from videotranslator.js_runtime import (
    app_bin_dir,
    app_data_dir,
    deno_asset_name,
    deno_download_url,
    ensure_js_runtime,
    find_runtime,
    install_deno,
    resolve_js_runtimes,
    runtime_binary_name,
)


class AssetNamingTests(unittest.TestCase):
    def test_linux_x86_64(self):
        self.assertEqual(
            deno_asset_name("linux", "x86_64"),
            "deno-x86_64-unknown-linux-gnu.zip",
        )

    def test_windows_amd64_alias(self):
        self.assertEqual(
            deno_asset_name("win32", "AMD64"),
            "deno-x86_64-pc-windows-msvc.zip",
        )

    def test_macos_arm64_alias(self):
        self.assertEqual(
            deno_asset_name("darwin", "arm64"),
            "deno-aarch64-apple-darwin.zip",
        )

    def test_unsupported_raises(self):
        with self.assertRaises(RuntimeError):
            deno_asset_name("win32", "arm64")  # no windows-arm deno build

    def test_download_url_uses_latest_base(self):
        url = deno_download_url("linux", "x86_64")
        self.assertTrue(url.endswith("deno-x86_64-unknown-linux-gnu.zip"))
        self.assertIn("releases/latest/download", url)


class PathTests(unittest.TestCase):
    def test_linux_data_dir_respects_xdg(self):
        d = app_data_dir(system="linux", env={"XDG_DATA_HOME": "/x"}, home="/home/u")
        self.assertEqual(d, Path("/x/VideoTranslatorAI"))

    def test_linux_data_dir_default(self):
        d = app_data_dir(system="linux", env={}, home="/home/u")
        self.assertEqual(d, Path("/home/u/.local/share/VideoTranslatorAI"))

    def test_windows_data_dir_uses_localappdata(self):
        d = app_data_dir(system="win32", env={"LOCALAPPDATA": "C:\\AppData"}, home="C:\\u")
        self.assertEqual(d, Path("C:\\AppData") / "VideoTranslatorAI")

    def test_bin_dir_is_under_data_dir(self):
        d = app_bin_dir(system="linux", env={}, home="/home/u")
        self.assertEqual(d, Path("/home/u/.local/share/VideoTranslatorAI/bin"))

    def test_runtime_binary_name_windows_suffix(self):
        self.assertEqual(runtime_binary_name("deno", "win32"), "deno.exe")
        self.assertEqual(runtime_binary_name("deno", "linux"), "deno")


class FindRuntimeTests(unittest.TestCase):
    def test_prefers_path_runtime(self):
        which = {"node": "/usr/bin/node"}.get
        found = find_runtime(which=which, bin_dir="/nope", system="linux")
        self.assertEqual(found, ("node", "/usr/bin/node"))

    def test_falls_back_to_app_local_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            deno = Path(tmp) / "deno"
            deno.write_bytes(b"x")
            found = find_runtime(
                which=lambda _name: None, bin_dir=tmp, system="linux"
            )
        self.assertEqual(found, ("deno", str(deno)))

    def test_returns_none_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                find_runtime(which=lambda _n: None, bin_dir=tmp, system="linux")
            )

    def test_resolve_js_runtimes_shapes_ytdlp_dict(self):
        which = {"deno": "/usr/local/bin/deno"}.get
        runtimes = resolve_js_runtimes(which=which, bin_dir="/nope", system="linux")
        self.assertEqual(runtimes, {"deno": {"path": "/usr/local/bin/deno"}})


def _fake_deno_zip(exe: str = "deno") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(exe, b"#!/bin/sh\necho deno\n")
    return buf.getvalue()


class InstallDenoTests(unittest.TestCase):
    def test_extracts_binary_and_sets_executable_bit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = install_deno(
                system="linux",
                machine="x86_64",
                bin_dir=tmp,
                downloader=lambda _url: _fake_deno_zip("deno"),
            )
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.access(path, os.X_OK))

    def test_missing_binary_in_archive_raises(self):
        empty = io.BytesIO()
        with zipfile.ZipFile(empty, "w") as zf:
            zf.writestr("readme.txt", b"no binary here")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                install_deno(
                    system="linux",
                    machine="x86_64",
                    bin_dir=tmp,
                    downloader=lambda _url: empty.getvalue(),
                )


class EnsureJsRuntimeTests(unittest.TestCase):
    def test_returns_existing_without_install(self):
        called = {"installer": False}

        def installer(**_kw):
            called["installer"] = True
            return "/should/not/happen"

        result = ensure_js_runtime(
            finder=lambda: {"node": {"path": "/usr/bin/node"}},
            installer=installer,
        )
        self.assertEqual(result, {"node": {"path": "/usr/bin/node"}})
        self.assertFalse(called["installer"])

    def test_installs_deno_when_missing(self):
        result = ensure_js_runtime(
            finder=lambda: None,
            installer=lambda **_kw: "/opt/app/bin/deno",
        )
        self.assertEqual(result, {"deno": {"path": "/opt/app/bin/deno"}})

    def test_install_disabled_returns_none(self):
        result = ensure_js_runtime(install=False, finder=lambda: None)
        self.assertIsNone(result)

    def test_install_failure_is_swallowed(self):
        logs: list[str] = []

        def boom(**_kw):
            raise RuntimeError("network down")

        result = ensure_js_runtime(
            finder=lambda: None, installer=boom, log_cb=logs.append
        )
        self.assertIsNone(result)
        self.assertTrue(any("fallito" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
