"""Güncelleme akışı: sürüm karşılaştırma, yayını okuma, indirme güvenliği, swap."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import update


REAL_057 = {
    "tag_name": "v0.5.7",
    "html_url": "https://github.com/x/y/releases/tag/v0.5.7",
    "assets": [
        {"name": "NetSonar-v0.5.7.bat", "size": 325,
         "digest": "sha256:4bd7", "browser_download_url": "https://x/bat"},
        {"name": "NetSonar-v0.5.7.exe", "size": 38321660,
         "digest": "sha256:a54a13df",
         "browser_download_url": "https://x/exe"},
    ],
}


class VersionTests(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertEqual(update.parse_version("v0.5.10"), (0, 5, 10))
        self.assertTrue(update.is_newer("v0.5.8", "0.5.7"))
        self.assertTrue(update.is_newer("0.10.0", "0.8.99"))
        self.assertFalse(update.is_newer("v0.5.7", "0.5.7"))
        self.assertFalse(update.is_newer("v0.5.6", "0.5.7"))

    def test_unparsable_version_raises(self):
        with self.assertRaises(update.UpdateError):
            update.parse_version("latest")


class ReleaseParsingTests(unittest.TestCase):
    def test_exe_asset_with_digest(self):
        info = update.parse_release(REAL_057)
        self.assertEqual(info.version, "0.5.7")
        self.assertEqual(info.asset_name, "NetSonar-v0.5.7.exe")
        self.assertEqual(info.sha256, "a54a13df")
        self.assertEqual(info.size, 38321660)

    def test_missing_exe_asset_raises(self):
        payload = dict(REAL_057, assets=[REAL_057["assets"][0]])
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload)

    def test_unknown_tag_shape_raises(self):
        with self.assertRaises(update.UpdateError):
            update.parse_release(dict(REAL_057, tag_name="latest"))


class DownloadTests(unittest.TestCase):
    def _serve(self, tmp, payload: bytes, declared: int):
        data = Path(tmp) / "payload.bin"
        data.write_bytes(payload)
        return update.UpdateInfo(
            version="9.9.9", asset_name="NetSonar-v9.9.9.exe",
            download_url=data.as_uri(), sha256=update._sha256_of(data),
            size=declared, page_url="")

    def test_download_verifies_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._serve(tmp, b"installer-bytes", 15)
            dest = Path(tmp) / "next" / "NetSonar-v9.9.9.exe"
            update.download(info, dest)
            self.assertEqual(dest.read_bytes(), b"installer-bytes")

    def test_bad_checksum_deletes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = self._serve(tmp, b"installer-bytes", 15)
            info.sha256 = "0" * 64
            dest = Path(tmp) / "bad.exe"
            with self.assertRaises(update.UpdateError):
                update.download(info, dest)
            self.assertFalse(dest.exists())

    def test_short_download_deletes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "payload.bin"
            data.write_bytes(b"short")
            info = update.UpdateInfo(
                version="9.9.9", asset_name="NetSonar-v9.9.9.exe",
                download_url=data.as_uri(), sha256="",
                size=10_000, page_url="")
            dest = Path(tmp) / "cut.exe"
            with self.assertRaises(update.UpdateError):
                update.download(info, dest)
            self.assertFalse(dest.exists())


class InstallLayoutTests(unittest.TestCase):
    def test_install_path_keeps_release_naming(self):
        dest = update.install_path(Path("C:/tools/NetSonar-v0.5.7.exe"), "0.5.8")
        self.assertEqual(dest.name, "NetSonar-v0.5.8.exe")

    def test_write_launcher_points_at_matching_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "NetSonar-v0.5.8.exe"
            exe.write_bytes(b"")
            bat = update.write_launcher(exe)
            text = bat.read_text(encoding="ascii")
            self.assertEqual(bat.name, "NetSonar-v0.5.8.bat")
            self.assertIn("NetSonar-v0.5.8.exe", text)
            self.assertNotIn("NetSonar-v0.5.7", text)

    def test_spawn_swap_writes_matching_launcher_before_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "NetSonar-v0.5.8.exe"
            exe.write_bytes(b"")
            with mock.patch("update.subprocess.Popen") as popen:
                update.spawn_swap(4242, exe)
            self.assertTrue((Path(tmp) / "NetSonar-v0.5.8.bat").exists())
            swap = (Path(tmp) / "netsonar-swap.bat").read_text(encoding="ascii")
            self.assertIn("4242", swap)
            self.assertIn("NetSonar-v0.5.8.exe", swap)
            popen.assert_called_once()


class CheckWindowTests(unittest.TestCase):
    def test_missing_or_broken_stamp_is_old(self):
        self.assertTrue(update.last_check_is_old(""))
        self.assertTrue(update.last_check_is_old("not-a-date"))

    def test_fresh_stamp_is_not_old(self):
        self.assertFalse(update.last_check_is_old(update.now_stamp()))


if __name__ == "__main__":
    unittest.main()
