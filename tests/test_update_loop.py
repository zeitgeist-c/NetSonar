"""Update loop and audit visibility regression tests.

This file is the regression protection for the "I said update and it keeps
updating itself" bug and the "the update side looks like it was never
installed" complaint.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import update


class SameVersionLoopTests(unittest.TestCase):
    """Installing the same version over and over must be prevented."""

    def test_same_version_is_not_newer(self):
        self.assertFalse(update.is_newer("0.6.0", "0.6.0"))
        self.assertFalse(update.is_newer("0.6.0", "0.6.0"))
        self.assertFalse(update.is_newer("0.5.9", "0.6.0"))
        self.assertTrue(update.is_newer("0.6.1", "0.6.0"))

    def test_check_for_update_returns_none_for_current_version(self):
        with mock.patch("update.fetch_latest") as fetch:
            fetch.return_value = update.UpdateInfo(
                version="0.6.0", asset_name="NetSonar-v0.6.0-Setup.exe",
                download_url="https://x/setup", sha256="abc", size=10, page_url="")
            self.assertIsNone(update.check_for_update("0.6.0"))
            self.assertIsNone(update.check_for_update("0.6.0"))

    def test_check_for_update_returns_info_only_when_newer(self):
        with mock.patch("update.fetch_latest") as fetch:
            fetch.return_value = update.UpdateInfo(
                version="0.7.0", asset_name="NetSonar-v0.7.0-Setup.exe",
                download_url="https://x/setup", sha256="abc", size=10, page_url="")
            info = update.check_for_update("0.6.0")
            self.assertIsNotNone(info)
            self.assertEqual(info.version, "0.7.0")


class InstallBatonTests(unittest.TestCase):
    """Install order: the installer must not run before the program exits."""

    def test_baton_waits_for_the_process_then_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            script = update.write_install_baton(installer, 4242)
            text = script.read_text(encoding="ascii")
            # The PID is awaited first, then the installer runs.
            self.assertIn("4242", text)
            self.assertLess(text.index("4242"), text.index("Setup.exe"))
            self.assertIn("/S", text)

    def test_baton_uses_powershell_for_the_pid_check(self):
        """The tasklist /FI filter is not honored on some Windows versions.

        The reliable method is PowerShell Get-Process -Id.
        """
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            text = update.write_install_baton(installer, 4242).read_text(
                encoding="ascii")
            self.assertIn("Get-Process -Id 4242", text)
            self.assertNotIn("tasklist", text)

    def test_baton_uses_the_absolute_windows_timeout(self):
        """In Git-Bash/MSYS 'timeout' resolves to the GNU tool and the loop
        never ends.

        The Windows timeout command must be called via an absolute path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            text = update.write_install_baton(installer, 4242).read_text(
                encoding="ascii")
            self.assertIn("timeout.exe", text)
            self.assertIn(str(update.WINDOWS_TIMEOUT), text)
            # There must be no relative call ("timeout /t").
            self.assertNotIn("(timeout /t", text)

    def test_baton_restarts_the_app_only_when_packaged(self):
        """In packaged mode the program is restarted; in source mode it is not."""
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.sys.frozen", True, create=True), \
                 mock.patch("update.sys.executable", "C:/Program Files/NetSonar/NetSonar.exe"):
                script = update.write_install_baton(installer, 4242)
            text = script.read_text(encoding="ascii")
            self.assertIn("NetSonar.exe", text)
            # The restart comes AFTER the install.
            self.assertLess(text.index("Setup.exe"), text.index("NetSonar.exe"))

    def test_baton_in_source_mode_does_not_restart_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.sys.frozen", False, create=True):
                script = update.write_install_baton(installer, 4242)
            text = script.read_text(encoding="ascii")
            self.assertNotIn("python", text.lower())

    def test_spawn_baton_arms_the_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.subprocess.Popen") as popen:
                update.spawn_install_baton(installer, 4242)
            popen.assert_called_once()
            args = popen.call_args[0][0]
            # call: cmd.exe /c call <baton>
            self.assertIn("call", args)
            script = Path(args[-1])
            self.assertTrue(script.exists())
            self.assertEqual(script.name, "netsonar-install.bat")

    def test_baton_survives_a_non_ascii_user_profile_path(self):
        """A Turkish user name must not stop the update.

        The installer lands under %LOCALAPPDATA%; if the user name contains
        non-ASCII characters (C:\\Users\\<non-ascii>\\...) the fixed ASCII
        encoding raised UnicodeEncodeError and the baton was never created.
        """
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "C_Users_Şükrü_Ğ" / "updates"
            folder.mkdir(parents=True)
            installer = folder / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            script = update.write_install_baton(installer, 4242)
            text = script.read_text(encoding=update._oem_encoding())
            self.assertIn("4242", text)
            self.assertIn("/S", text)
            self.assertIn("Setup.exe", text)

    def test_spawn_baton_does_not_combine_incompatible_creation_flags(self):
        """DETACHED_PROCESS + CREATE_NEW_CONSOLE together yields WinError 87."""
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.subprocess.Popen") as popen:
                update.spawn_install_baton(installer, 4242)
            flags = popen.call_args[1]["creationflags"]
            detached = getattr(__import__("subprocess"), "DETACHED_PROCESS", 0)
            new_console = getattr(__import__("subprocess"), "CREATE_NEW_CONSOLE", 0)
            self.assertEqual(flags & new_console, 0)
            self.assertTrue(flags & detached or detached == 0)


class InstallOutcomeTests(unittest.TestCase):
    """Post-install verification: did the version actually go up?"""

    def test_outcome_detects_a_successful_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.run_installer_and_wait", return_value=0), \
                 mock.patch("update.installed_version", return_value="0.7.0"):
                result = update.install_outcome(installer, "0.6.0")
            self.assertTrue(result["succeeded"])
            self.assertTrue(result["changed"])
            self.assertEqual(result["installed_version"], "0.7.0")

    def test_outcome_detects_a_failed_update(self):
        """The install did not run: the version stayed the same and must not
        be counted as success."""
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.run_installer_and_wait", return_value=0), \
                 mock.patch("update.installed_version", return_value="0.6.0"):
                result = update.install_outcome(installer, "0.6.0")
            self.assertFalse(result["succeeded"])
            self.assertFalse(result["changed"])

    def test_outcome_treats_nonzero_exit_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            installer = Path(tmp) / "NetSonar-v0.7.0-Setup.exe"
            installer.write_bytes(b"")
            with mock.patch("update.run_installer_and_wait", return_value=1), \
                 mock.patch("update.installed_version", return_value="0.7.0"):
                result = update.install_outcome(installer, "0.6.0")
            self.assertFalse(result["succeeded"])

    def test_installed_version_reads_the_app_version_in_source_mode(self):
        """In unpackaged mode the version is read from config."""
        from config import get_app_version
        self.assertEqual(update.installed_version(),
                         get_app_version().lstrip("v"))


class UpdateStateTests(unittest.TestCase):
    """The audit result must be recorded and the card must always be populated."""

    def test_settings_carry_the_update_state(self):
        from config import _default_settings
        from settings_service import validate_settings
        defaults = _default_settings()
        self.assertIn("UPDATE_LAST_SEEN_VERSION", defaults)
        self.assertIn("UPDATE_AVAILABLE", defaults)
        validated = validate_settings({}, defaults)
        self.assertEqual(validated["UPDATE_LAST_SEEN_VERSION"], "")
        self.assertFalse(validated["UPDATE_AVAILABLE"])
        # Corrupt input is normalized.
        dirty = validate_settings({"UPDATE_AVAILABLE": "yes",
                                   "UPDATE_LAST_SEEN_VERSION": 5}, defaults)
        self.assertIsInstance(dirty["UPDATE_AVAILABLE"], bool)
        self.assertEqual(dirty["UPDATE_LAST_SEEN_VERSION"], "5")


if __name__ == "__main__":
    unittest.main()
