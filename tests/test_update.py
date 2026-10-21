"""Güncelleme akışı: sürüm karşılaştırma, yayını okuma, indirme güvenliği, swap."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import update


REAL_057 = {
    "tag_name": "v0.6.0",
    "html_url": "https://github.com/x/y/releases/tag/v0.6.0",
    "assets": [
        {"name": "NetSonar-v0.6.0-Setup.exe", "size": 38321660,
         "digest": "sha256:a54a13df",
         "browser_download_url": "https://x/setup"},
    ],
}


class VersionTests(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertEqual(update.parse_version("v0.5.10"), (0, 5, 10))
        self.assertTrue(update.is_newer("v0.5.8", "0.5.7"))
        self.assertTrue(update.is_newer("0.10.0", "0.8.99"))
        self.assertFalse(update.is_newer("v0.5.7", "0.5.7"))
        self.assertFalse(update.is_newer("0.5.6", "0.5.7"))

    def test_unparsable_version_raises(self):
        with self.assertRaises(update.UpdateError):
            update.parse_version("latest")


class ReleaseParsingTests(unittest.TestCase):
    def test_installer_asset_with_digest(self):
        info = update.parse_release(REAL_057)
        self.assertEqual(info.version, "0.6.0")
        self.assertEqual(info.asset_name, "NetSonar-v0.6.0-Setup.exe")
        self.assertEqual(info.sha256, "a54a13df")
        self.assertEqual(info.size, 38321660)

    def test_missing_installer_asset_raises(self):
        payload = dict(REAL_057, assets=[])
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload)

    def test_portable_exe_asset_is_not_accepted(self):
        """Kurulumcu kanalı: sadece -Setup.exe kabul edilir."""
        payload = dict(REAL_057, assets=[
            {"name": "NetSonar-v0.6.0.exe", "size": 10,
             "browser_download_url": "https://x/exe"},
        ])
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload)

    def test_unknown_tag_shape_raises(self):
        with self.assertRaises(update.UpdateError):
            update.parse_release(dict(REAL_057, tag_name="latest"))

    def test_asset_name_follows_delivery_rule(self):
        self.assertEqual(update.installer_asset_name("0.6.0"),
                         "NetSonar-v0.6.0-Setup.exe")


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
    def test_install_path_targets_the_update_cache(self):
        """Kurulum dosyasi Program Files'a degil, kullanici onbellegine iner."""
        dest = update.install_path(Path("C:/tools/NetSonar.exe"), "0.6.0")
        self.assertEqual(dest.name, "NetSonar-v0.6.0-Setup.exe")
        self.assertIn("updates", str(dest).lower())

    def test_install_path_is_outside_the_program_folder(self):
        dest = update.install_path(Path("C:/tools/NetSonar.exe"), "0.6.0")
        self.assertNotIn(str(update.INSTALL_DIR).lower(), str(dest).lower())

    def test_spawn_swap_is_no_longer_a_valid_flow(self):
        """Sabit kurulum yolunda kopya-degistir akisi kaldirildi."""
        with self.assertRaises(update.UpdateError):
            update.spawn_swap(4242, Path("C:/tools/NetSonar-v0.6.0.exe"))

    def test_launch_installer_requires_an_existing_file(self):
        with self.assertRaises(update.UpdateError):
            update.launch_installer(Path("C:/yok/NetSonar-v0.6.0-Setup.exe"))

    def test_launch_installer_runs_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.6.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.subprocess.Popen") as popen:
                update.launch_installer(installer)
            popen.assert_called_once()
            args = popen.call_args[0][0]
            self.assertEqual(args[0], str(installer))
            self.assertIn("/S", args)

    def test_cleanup_keeps_the_installer_in_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            keep = folder / "NetSonar-v0.6.0-Setup.exe"
            old = folder / "NetSonar-v0.5.9-Setup.exe"
            keep.write_bytes(b"")
            old.write_bytes(b"")
            with mock.patch("update.cache_dir", return_value=folder):
                removed = update.cleanup_old_installers(keep)
            self.assertEqual(removed, 1)
            self.assertTrue(keep.exists())
            self.assertFalse(old.exists())


class CheckWindowTests(unittest.TestCase):
    def test_missing_or_broken_stamp_is_old(self):
        self.assertTrue(update.last_check_is_old(""))
        self.assertTrue(update.last_check_is_old("not-a-date"))

    def test_fresh_stamp_is_not_old(self):
        self.assertFalse(update.last_check_is_old(update.now_stamp()))


if __name__ == "__main__":
    unittest.main()
