"""Security: the release tag and version string must not hijack the download path.

`parse_version` only extracts numbers from the tag; if the raw tag reaches the
file name, a value like `1.2.3/../../evil` redirects the download outside the
cache folder. `clean_version` reduces the version to the strict X.Y.Z form.
"""

import unittest
from pathlib import Path
from unittest import mock

import update


HOSTILE = "v1.2.3/../../../../Users/Public/evil"


def payload(tag, asset_name="NetSonar-v1.2.3-Setup.exe"):
    return {
        "tag_name": tag,
        "html_url": "https://github.com/x/y/releases/tag/x",
        "assets": [{
            "name": asset_name,
            "size": 10,
            "digest": "sha256:" + "0" * 64,
            "browser_download_url": "https://x/setup",
        }],
    }


class HostileVersionTests(unittest.TestCase):
    def test_traversal_tag_is_rejected(self):
        with self.assertRaises(update.UpdateError):
            update.parse_release(payload(HOSTILE))

    def test_traversal_in_asset_builder_is_rejected(self):
        for hostile in ("1.2.3/../../evil", "1.2.3\\..\\..\\evil", "../1.2.3",
                        "1.2.3:stream", "1.2", ""):
            with self.subTest(version=hostile):
                with self.assertRaises(update.UpdateError):
                    update.installer_asset_name(hostile)

    def test_surrounding_whitespace_is_normalized_not_rejected(self):
        """Trimming is safe: ' 1.2.3 ' -> '1.2.3' (produces no path separator)."""
        self.assertEqual(update.clean_version(" 1.2.3 "), "1.2.3")

    def test_install_path_stays_inside_the_cache(self):
        with mock.patch("update.cache_dir", return_value=Path("C:/cache/updates")):
            dest = update.install_path(Path("C:/tools/NetSonar.exe"), "0.6.0")
        self.assertEqual(dest.parent, Path("C:/cache/updates").resolve())
        self.assertEqual(dest.name, "NetSonar-v0.6.0-Setup.exe")

    def test_install_path_refuses_traversal(self):
        with mock.patch("update.cache_dir", return_value=Path("C:/cache/updates")):
            with self.assertRaises(update.UpdateError):
                update.install_path(Path("C:/tools/NetSonar.exe"), "1.2.3/../../evil")

    def test_plain_versions_still_work(self):
        self.assertEqual(update.clean_version("v0.6.0"), "0.6.0")
        self.assertEqual(update.clean_version("0.6.0"), "0.6.0")
        self.assertEqual(update.installer_asset_name("v0.6.1"),
                         "NetSonar-v0.6.1-Setup.exe")

    def test_compare_still_accepts_a_prefixed_tag(self):
        """parse_version stays lenient: version comparison must not break."""
        self.assertTrue(update.is_newer("v0.6.3", "0.6.2"))


if __name__ == "__main__":
    unittest.main()
