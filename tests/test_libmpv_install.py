"""Windows libmpv installer (spec 8.3, Q1, Q2, Q6). Every download, 7zr run and
load check is faked: no network, no Windows, no real DLL."""

import contextlib
import hashlib
import io
import re
import subprocess
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from videotranslator import libmpv_runtime as rt
from videotranslator.libmpv_runtime import AssetSource, DownloadError, LibmpvStatus


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeHttp:
    def __init__(self, files=None, api=None, text=None, redirects=None):
        self.files = dict(files or {})
        self.api = dict(api or {})
        self.text = dict(text or {})
        self.redirects = dict(redirects or {})
        self.fetched = []

    def get_json(self, url):
        if url not in self.api:
            raise OSError(f"HTTP 403 rate limit exceeded: {url}")
        return self.api[url]

    def get_text(self, url):
        if url not in self.text:
            raise OSError(f"HTTP 404: {url}")
        return self.text[url]

    def resolve(self, url):
        if url not in self.redirects:
            raise OSError(f"HTTP 404: {url}")
        return self.redirects[url]

    def fetch(self, url, dest, *, max_bytes):
        self.fetched.append(url)
        if url not in self.files:
            raise OSError(f"HTTP 404: {url}")
        data = self.files[url]
        if len(data) > max_bytes:
            raise DownloadError(f"{url} is larger than {max_bytes} bytes")
        Path(dest).write_bytes(data)
        return _sha(data)


def fake_7zr(cmd):
    """`7zr e -y -o<dir> <archive> <member>`: a good archive is b"7z:" + the member bytes."""
    out_dir = Path(next(part[2:] for part in cmd if part.startswith("-o")))
    archive, member = Path(cmd[-2]), cmd[-1]
    data = archive.read_bytes()
    if not data.startswith(b"7z:"):
        (out_dir / member).write_bytes(b"")  # a failed real extraction can leave a 0-byte file
        return 2
    (out_dir / member).write_bytes(data[3:])
    return 0


def fake_probe(directory):
    """Load check by DLL content: MZgood loads; MZvulkan needs vulkan-fallback; else it crashes."""
    directory = Path(directory)
    data = (directory / "mpv-2.dll").read_bytes()
    loaded = LibmpvStatus(ok=True, reason="ok", api_version=(2, 5), mpv_version=(0, 41),
                          path=str(directory / "mpv-2.dll"), detail="mpv 0.41.0, client API 2.5")
    if data == b"MZgood":
        return loaded
    if data == b"MZvulkan":
        if (directory / "vulkan-fallback" / "vulkan-1.dll").is_file():
            return loaded
        return LibmpvStatus(ok=False, reason="vulkan-loader-missing", detail="WinError 126")
    return LibmpvStatus(ok=False, reason="probe-crashed", detail="exit code 3221225477")


SEVENZR_URL = "https://example.test/7zr.exe"
SEVENZR = AssetSource(kind="pinned", name="7zr-test", licence="LGPL", urls=(SEVENZR_URL,),
                      sha256=_sha(b"MZ7zr"), member="7zr.exe", max_bytes=1 << 20)
VULKAN_MEMBER = "VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll"


def _vulkan_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        bundle.writestr(VULKAN_MEMBER, b"MZvk")
    return buf.getvalue()


VULKAN_ZIP = _vulkan_zip()
VULKAN_URL = "https://example.test/vulkan.zip"
VULKAN = AssetSource(kind="pinned", name="vulkan-test", licence="MIT and Apache-2.0",
                     urls=(VULKAN_URL,), sha256=_sha(VULKAN_ZIP), member=VULKAN_MEMBER,
                     member_sha256=_sha(b"MZvk"), max_bytes=1 << 20)

REPO = "zhongfly/mpv-winbuild"
API_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=3"
GH = AssetSource(kind="github-latest", name="zhongfly-lgpl", licence="LGPL", repo=REPO,
                 asset_pattern=r"mpv-dev-lgpl-x86_64-\d{8}-git-[0-9a-f]+\.7z", max_releases=3,
                 max_bytes=1 << 20)


def _release(tag, date, commit, dll, *, digest=True):
    name = f"mpv-dev-lgpl-x86_64-{date}-git-{commit}.7z"
    archive = b"7z:" + dll
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    asset = {"name": name, "browser_download_url": url}
    if digest:
        asset["digest"] = "sha256:" + _sha(archive)
    decoys = [  # the v3 and the GPL builds of the same release must never match
        {"name": f"mpv-dev-lgpl-x86_64-v3-{date}-git-{commit}.7z",
         "browser_download_url": url + ".v3", "digest": "sha256:" + "0" * 64},
        {"name": f"mpv-dev-x86_64-{date}-git-{commit}.7z",
         "browser_download_url": url + ".gpl", "digest": "sha256:" + "1" * 64},
    ]
    return {"tag_name": tag, "assets": decoys + [asset]}, url, archive, name


def _pinned(name, urls, *, member_sha256=None):
    return AssetSource(kind="pinned", name=name, licence="GPL", urls=tuple(urls),
                       sha256=_sha(b"7z:MZgood"), member_sha256=member_sha256, max_bytes=1 << 20)


class SourceDataTests(unittest.TestCase):
    def test_q1_order_lgpl_latest_first_then_the_pinned_gpl_build(self):
        first, second = rt.WINDOWS_LIBMPV_SOURCES
        self.assertEqual((first.kind, first.name, first.licence, first.repo, first.max_releases),
                         ("github-latest", "zhongfly-lgpl", "LGPL", "zhongfly/mpv-winbuild", 3))
        pattern = re.compile(first.asset_pattern)
        self.assertTrue(pattern.fullmatch("mpv-dev-lgpl-x86_64-20260925-git-2a4eb8067c.7z"))
        self.assertIsNone(pattern.fullmatch("mpv-dev-lgpl-x86_64-v3-20260925-git-2a4eb8067c.7z"))
        self.assertIsNone(pattern.fullmatch("mpv-dev-x86_64-20260925-git-2a4eb8067c.7z"))
        self.assertEqual((second.kind, second.name, second.licence),
                         ("pinned", "shinchiro-gpl-20260920", "GPL"))
        self.assertTrue(second.urls[0].startswith("https://downloads.sourceforge.net/"))
        self.assertTrue(all(url.endswith("/mpv-dev-x86_64-20260920-git-e76a35ec95.7z")
                            for url in second.urls))
        self.assertEqual(second.sha256,
                         "60f9102db46aea8cef9bfb4345ee6a106f34fdbd1df9587e38f0660688039341")
        self.assertEqual(second.member_sha256,
                         "63e1fbb4ee890d153a9f5086410157174ee18582846bf35f6cc4e5d08d4bb662")

    def test_pinned_tools(self):
        self.assertEqual(rt.SEVENZR.urls,
                         ("https://github.com/ip7z/7zip/releases/download/26.03/7zr.exe",))
        self.assertEqual(rt.SEVENZR.sha256,
                         "ad4c82fadcbdf93c03b4fc440f300509c7d60c5c2f4d183e35d9d70d6957037d")
        self.assertEqual(rt.VULKAN_RUNTIME.member,
                         "VulkanRT-X64-1.4.357.0-Components/x64/vulkan-1.dll")
        self.assertEqual(rt.VULKAN_RUNTIME.sha256,
                         "a14672efed15aafc7f5a16572d35cd3a3416eadf670aeee3cdf50ee32d5fbf83")
        self.assertEqual(rt.VULKAN_RUNTIME.member_sha256,
                         "cd862090370454630b31b174e3d4eb474fda38ea034998d1fe1767b0c99a8696")


class InstallWindowsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self._tmp.name) / "mpv-runtime"
        self.log = []

    def tearDown(self):
        self._tmp.cleanup()

    def _install(self, sources, http, probe=fake_probe):
        return rt.install_windows(
            self.dest, sources=sources, sevenzr=SEVENZR, vulkan=VULKAN, downloader=http,
            runner=fake_7zr, probe=probe, log=self.log.append,
            now=lambda: datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc))

    def _leftovers(self):
        return sorted(p.name for p in self.dest.rglob("*")
                      if p.name.endswith(".part") or p.name in ("libmpv-2.dll", "_staging"))

    def test_the_newest_github_release_with_a_digest_is_installed(self):
        new, new_url, new_archive, new_name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood")
        old, old_url, old_archive, _ = _release("2026-09-24-bbbbbbb", "20260924", "bbbbbbb", b"MZgood")
        licence_url = "https://raw.githubusercontent.com/mpv-player/mpv/aaaaaaa/LICENSE.LGPL"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", new_url: new_archive, old_url: old_archive},
                        api={API_URL: [new, old]}, text={licence_url: "LGPL TEXT"})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, new_url])
        self.assertEqual((self.dest / "mpv-2.dll").read_bytes(), b"MZgood")
        build = rt.read_build_txt(self.dest)
        self.assertEqual(build["source"], "zhongfly-lgpl")
        self.assertEqual(build["licence"], "LGPL")
        self.assertEqual(build["release"], "2026-09-25-aaaaaaa")
        self.assertEqual(build["archive"], new_name)
        self.assertEqual(build["mpv_commit"], "aaaaaaa")
        self.assertEqual(build["mpv_version"], "0.41")
        self.assertEqual(build["dll_sha256"], _sha(b"MZgood"))
        self.assertEqual(build["vulkan_fallback"], "no")
        self.assertEqual(build["installed"], "2026-09-25T12:00:00Z")
        self.assertEqual((self.dest / "LICENSE.LGPL").read_text(encoding="utf-8"), "LGPL TEXT")
        self.assertEqual(self._leftovers(), [])

    def test_a_failed_load_check_falls_back_to_the_next_release(self):
        bad, bad_url, bad_archive, bad_name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZcrash")
        good, good_url, good_archive, _ = _release("2026-09-24-bbbbbbb", "20260924", "bbbbbbb", b"MZgood")
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", bad_url: bad_archive, good_url: good_archive},
                        api={API_URL: [bad, good]})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(rt.read_build_txt(self.dest)["release"], "2026-09-24-bbbbbbb")
        self.assertTrue(any(bad_name in line and "probe-crashed" in line for line in self.log))
        self.assertEqual(self._leftovers(), [])

    def test_api_failure_uses_the_latest_redirect_and_sha256_txt(self):
        _, url, archive, name = _release("2026-09-24-2a4eb80", "20260924", "2a4eb80", b"MZgood")
        tag_url = f"https://github.com/{REPO}/releases/tag/2026-09-24-2a4eb80"
        sums_url = f"https://github.com/{REPO}/releases/download/2026-09-24-2a4eb80/sha256.txt"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive},
                        redirects={f"https://github.com/{REPO}/releases/latest": tag_url},
                        text={sums_url: f"{'0' * 64}  mpv-dev-x86_64-20260924-git-2a4eb80.7z\n"
                                        f"{_sha(archive)}  {name}\n"})
        status = self._install([GH], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, url])

    def test_a_missing_digest_is_looked_up_in_sha256_txt(self):
        rel, url, archive, name = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood",
                                           digest=False)
        sums_url = f"https://github.com/{REPO}/releases/download/2026-09-25-aaaaaaa/sha256.txt"
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive}, api={API_URL: [rel]},
                        text={sums_url: f"{_sha(archive)} *{name}\n"})
        self.assertTrue(self._install([GH], http).ok)

    def test_an_asset_without_any_checksum_is_never_downloaded(self):
        rel, url, archive, _ = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood",
                                        digest=False)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive}, api={API_URL: [rel]})
        status = self._install([GH], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertNotIn(url, http.fetched)

    def test_malformed_api_entries_are_skipped_and_the_fallback_is_used(self):
        # Codex review: a non-dict release or asset, or a digest that is not a
        # 64-hex SHA256, must not crash the installer before the pinned
        # fallback source is tried.
        rel, url, archive, _ = _release("2026-09-25-aaaaaaa", "20260925", "aaaaaaa", b"MZgood")
        rel["assets"][-1]["digest"] = "sha256:not-a-hash"
        rel["assets"].insert(0, "not an asset")
        fallback = _pinned("shinchiro-test", ["https://mirror1.test/a.7z"])
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", url: archive,
                               "https://mirror1.test/a.7z": b"7z:MZgood"},
                        api={API_URL: ["not a release", rel]})
        status = self._install([GH, fallback], http)
        self.assertTrue(status.ok)
        self.assertNotIn(url, http.fetched)  # its digest is invalid and sha256.txt is absent
        self.assertEqual(rt.read_build_txt(self.dest)["source"], "shinchiro-test")

    def test_a_pinned_sha_mismatch_is_rejected_and_the_next_mirror_used(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z", "https://mirror2.test/a.7z"])
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZevil",
                               "https://mirror2.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertTrue(status.ok)
        self.assertEqual(http.fetched, [SEVENZR_URL, "https://mirror1.test/a.7z",
                                        "https://mirror2.test/a.7z"])
        self.assertEqual(rt.read_build_txt(self.dest)["url"], "https://mirror2.test/a.7z")
        self.assertEqual(self._leftovers(), [])

    def test_a_member_sha_mismatch_is_rejected(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z"], member_sha256="f" * 64)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("SHA256 mismatch", status.detail)
        self.assertFalse((self.dest / "mpv-2.dll").exists())

    def test_the_size_cap_is_enforced(self):
        source = AssetSource(kind="pinned", name="big", licence="GPL", urls=("https://big.test/a.7z",),
                             sha256=_sha(b"7z:MZgood"), max_bytes=4)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://big.test/a.7z": b"7z:MZgood"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("larger than 4 bytes", status.detail)
        self.assertEqual(self._leftovers(), [])

    def test_the_vulkan_loader_is_fetched_when_missing(self):
        source = AssetSource(kind="pinned", name="needs-vulkan", licence="GPL",
                             urls=("https://v.test/a.7z",), sha256=_sha(b"7z:MZvulkan"),
                             max_bytes=1 << 20)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://v.test/a.7z": b"7z:MZvulkan",
                               VULKAN_URL: VULKAN_ZIP})
        status = self._install([source], http)
        self.assertTrue(status.ok)
        self.assertIn(VULKAN_URL, http.fetched)
        self.assertEqual((self.dest / "vulkan-fallback" / "vulkan-1.dll").read_bytes(), b"MZvk")
        self.assertEqual(rt.read_build_txt(self.dest)["vulkan_fallback"], "yes")
        self.assertEqual(self._leftovers(), [])

    def test_a_second_run_skips_every_download(self):
        source = _pinned("shinchiro-test", ["https://mirror1.test/a.7z"])
        first = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://mirror1.test/a.7z": b"7z:MZgood"})
        self.assertTrue(self._install([source], first).ok)
        second = FakeHttp()
        status = self._install([source], second)
        self.assertTrue(status.ok)
        self.assertEqual(second.fetched, [])
        self.assertTrue(any("skipping the download" in line for line in self.log))

    def test_repair_of_a_current_build_restores_a_lost_vulkan_loader(self):
        # Plan review / spec 6.1 row 5: the machine lost System32\\vulkan-1.dll
        # after the install (driver change, moved to a VM without 3D). A current
        # BUILD.txt must not stop Repair from fetching the Vulkan fallback.
        source = AssetSource(kind="pinned", name="needs-vulkan", licence="GPL",
                             urls=("https://v.test/a.7z",), sha256=_sha(b"7z:MZvulkan"),
                             max_bytes=1 << 20)
        first = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://v.test/a.7z": b"7z:MZvulkan",
                                VULKAN_URL: VULKAN_ZIP})
        self.assertTrue(self._install([source], first).ok)
        (self.dest / "vulkan-fallback" / "vulkan-1.dll").unlink()
        second = FakeHttp(files={VULKAN_URL: VULKAN_ZIP})
        status = self._install([source], second)
        self.assertTrue(status.ok)
        self.assertEqual(second.fetched, [VULKAN_URL])  # no 7zr, no libmpv archive
        self.assertEqual((self.dest / "vulkan-fallback" / "vulkan-1.dll").read_bytes(), b"MZvk")
        self.assertEqual(self._leftovers(), [])

    def test_repair_of_a_current_build_reports_a_failed_vulkan_download(self):
        source = AssetSource(kind="pinned", name="needs-vulkan", licence="GPL",
                             urls=("https://v.test/a.7z",), sha256=_sha(b"7z:MZvulkan"),
                             max_bytes=1 << 20)
        first = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://v.test/a.7z": b"7z:MZvulkan",
                                VULKAN_URL: VULKAN_ZIP})
        self.assertTrue(self._install([source], first).ok)
        (self.dest / "vulkan-fallback" / "vulkan-1.dll").unlink()
        status = self._install([source], FakeHttp())  # offline
        self.assertEqual(status.reason, "vulkan-loader-missing")
        self.assertEqual(self._leftovers(), [])

    def test_repair_replaces_a_corrupt_vulkan_fallback(self):
        # Codex review: a fallback whose hash does not match is removed and
        # fetched again, even though the probe cannot tell it apart.
        source = AssetSource(kind="pinned", name="needs-vulkan", licence="GPL",
                             urls=("https://v.test/a.7z",), sha256=_sha(b"7z:MZvulkan"),
                             max_bytes=1 << 20)
        first = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://v.test/a.7z": b"7z:MZvulkan",
                                VULKAN_URL: VULKAN_ZIP})
        self.assertTrue(self._install([source], first).ok)
        (self.dest / "vulkan-fallback" / "vulkan-1.dll").write_bytes(b"MZcorrupt")
        second = FakeHttp(files={VULKAN_URL: VULKAN_ZIP})
        status = self._install([source], second)
        self.assertTrue(status.ok)
        self.assertEqual(second.fetched, [VULKAN_URL])
        self.assertEqual((self.dest / "vulkan-fallback" / "vulkan-1.dll").read_bytes(), b"MZvk")

    def test_a_build_from_a_source_no_longer_listed_is_replaced(self):
        old = _pinned("old-source", ["https://old.test/a.7z"])
        new = _pinned("new-source", ["https://new.test/a.7z"])
        self.assertTrue(self._install([old], FakeHttp(files={
            SEVENZR_URL: b"MZ7zr", "https://old.test/a.7z": b"7z:MZgood"})).ok)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://new.test/a.7z": b"7z:MZgood"})
        self.assertTrue(self._install([new], http).ok)
        self.assertIn("https://new.test/a.7z", http.fetched)
        self.assertEqual(rt.read_build_txt(self.dest)["source"], "new-source")

    def test_a_failed_extraction_leaves_no_zero_byte_dll(self):
        source = AssetSource(kind="pinned", name="broken", licence="GPL", urls=("https://b.test/a.7z",),
                             sha256=_sha(b"not an archive"), max_bytes=1 << 20)
        http = FakeHttp(files={SEVENZR_URL: b"MZ7zr", "https://b.test/a.7z": b"not an archive"})
        status = self._install([source], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("7zr could not extract", status.detail)
        self.assertEqual(self._leftovers(), [])
        self.assertFalse((self.dest / "mpv-2.dll").exists())

    def test_every_source_failing_reports_libmpv_missing(self):
        status = self._install([_pinned("a", ["https://a.test/a.7z"]),
                                _pinned("b", ["https://b.test/b.7z"])],
                               FakeHttp(files={SEVENZR_URL: b"MZ7zr"}))
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("a.7z", status.detail)
        self.assertIn("b.7z", status.detail)

    def test_a_7zr_download_failure_stops_the_install(self):
        http = FakeHttp()
        status = self._install([_pinned("a", ["https://a.test/a.7z"])], http)
        self.assertEqual(status.reason, "libmpv-missing")
        self.assertIn("7zr.exe", status.detail)
        self.assertEqual(http.fetched, [SEVENZR_URL])
        self.assertFalse((self.dest / "_staging").exists())


class _FakeResponse:
    def __init__(self, data, *, url="https://final.test/x", ctype="application/octet-stream"):
        self._buf = io.BytesIO(data)
        self._url = url
        self.headers = {"Content-Type": ctype}

    def read(self, n=-1):
        return self._buf.read(n)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class HttpClientTests(unittest.TestCase):
    def _client(self, response, seen):
        def opener(request, timeout):
            seen.append((request.full_url, request.get_header("User-agent"), timeout))
            return response

        return rt.HttpClient(opener=opener, timeout=7, chunk=4)

    def test_fetch_streams_hashes_and_sends_the_installer_agent(self):
        seen = []
        client = self._client(_FakeResponse(b"0123456789"), seen)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "f.part"
            self.assertEqual(client.fetch("https://x.test/f", target, max_bytes=100),
                             _sha(b"0123456789"))
            self.assertEqual(target.read_bytes(), b"0123456789")
        self.assertEqual(seen, [("https://x.test/f", "VideoTranslatorAI-Setup", 7)])

    def test_fetch_enforces_the_cap_and_refuses_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DownloadError):
                self._client(_FakeResponse(b"0123456789"), []).fetch(
                    "https://x.test/f", Path(tmp) / "a", max_bytes=5)
            with self.assertRaises(DownloadError):
                self._client(_FakeResponse(b"<html>", ctype="text/html; charset=utf-8"), []).fetch(
                    "https://x.test/f", Path(tmp) / "b", max_bytes=100)

    def test_json_text_and_redirect(self):
        self.assertEqual(self._client(_FakeResponse(b'[{"tag_name": "t"}]'), []).get_json(
            "https://api.test/r"), [{"tag_name": "t"}])
        self.assertEqual(self._client(_FakeResponse(b"abc"), []).get_text("https://x.test/t"), "abc")
        self.assertEqual(self._client(_FakeResponse(
            b"", url="https://github.com/r/releases/tag/v1"), []).resolve("https://x.test/latest"),
            "https://github.com/r/releases/tag/v1")


class RunHiddenTests(unittest.TestCase):
    def test_windows_tools_run_without_a_console(self):
        seen = {}

        def run(cmd, **kwargs):
            seen["cmd"], seen["kwargs"] = cmd, kwargs
            return subprocess.CompletedProcess(cmd, 0)

        self.assertEqual(rt.run_hidden(["7zr.exe", "e"], run=run, sys_platform="win32"), 0)
        self.assertEqual(seen["kwargs"]["creationflags"], 0x08000000)
        self.assertIs(seen["kwargs"]["stdin"], subprocess.DEVNULL)

    def test_a_timeout_or_a_start_failure_is_minus_one(self):
        def slow(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 1)

        def missing(cmd, **kwargs):
            raise OSError("no 7zr")

        self.assertEqual(rt.run_hidden(["7zr.exe"], run=slow), -1)
        self.assertEqual(rt.run_hidden(["7zr.exe"], run=missing), -1)


class InstallCommandTests(unittest.TestCase):
    def test_install_is_windows_only(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="linux"), 2)

    def test_install_exit_codes(self):
        cases = ((LibmpvStatus(ok=True, reason="ok", path="p"), 0),
                 (LibmpvStatus(ok=False, reason="python-mpv-missing", path="p"), 0),
                 (LibmpvStatus(ok=False, reason="libmpv-missing"), 2))
        with contextlib.redirect_stdout(io.StringIO()):
            for status, code in cases:
                with self.subTest(reason=status.reason), \
                        mock.patch.object(rt, "install_windows", return_value=status):
                    self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="win32"), code)
            with mock.patch.object(rt, "install_windows", side_effect=RuntimeError("boom")), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rt.main(["install", "--dest", "x"], sys_platform="win32"), 3)


if __name__ == "__main__":
    unittest.main()
