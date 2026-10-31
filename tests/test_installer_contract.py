"""Installer contracts.

The NSIS script (packaging/NetSonar.nsi) and the build flow pin the single
channel (installer) and the protection rules (do not touch the store, fixed
install path) in code. The script itself is read as text: its contract is
verified without executing it.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NSI = ROOT / "packaging" / "NetSonar.nsi"
BUILD = ROOT / "packaging" / "build.ps1"
SPEC = ROOT / "packaging" / "NetSonar.spec"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class InstallerScriptTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(NSI)

    def test_install_dir_is_fixed_program_files(self):
        self.assertIn('InstallDir "$PROGRAMFILES64\\${APP_NAME}"', self.text)

    def test_output_name_follows_delivery_rule(self):
        self.assertIn('OutFile "..\\dist\\NetSonar-v${APP_VERSION}-Setup.exe"',
                      self.text)

    def test_installer_remembers_the_chosen_language(self):
        self.assertIn('StrCpy $LANGUAGE $0', self.text)

    def test_installer_requires_admin(self):
        self.assertIn("RequestExecutionLevel admin", self.text)

    def test_shortcuts_are_created(self):
        self.assertIn('CreateShortcut "$DESKTOP\\${APP_NAME}.lnk"', self.text)
        self.assertIn('CreateShortcut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"',
                      self.text)

    def test_uninstaller_is_written(self):
        self.assertIn('WriteUninstaller "$INSTDIR\\Uninstall.exe"', self.text)

    def test_autostart_is_only_refreshed_when_it_was_enabled(self):
        """If the preference is off, setup must not turn it on."""
        self.assertIn("AutostartWasEnabled", self.text)
        self.assertIn("${If} $AutostartWasEnabled == \"1\"", self.text)

    def test_store_and_user_data_are_never_written(self):
        """The installer must only write to the program folder and the registry.

        Comment lines may contain LOCALAPPDATA; that is not a command. Real
        write commands must not contain the user data path
        (LOCALAPPDATA/APPDATA).
        """
        commands = [line.strip() for line in self.text.splitlines()
                    if line.strip() and not line.strip().startswith(";")]
        body = "\n".join(commands)
        self.assertNotIn("LOCALAPPDATA", body)
        self.assertNotIn("$APPDATA", body)
        self.assertNotIn("\\store", body)
        # Program files are written only under $INSTDIR.
        self.assertIn('SetOutPath "$INSTDIR"', body)
        self.assertIn('File /r "app-dist\\NetSonar\\*.*"', body)
        # Deletion commands are limited to the program folder.
        deletions = [line for line in commands if line.startswith("RMDir")]
        for line in deletions:
            self.assertTrue(
                "$INSTDIR" in line or "$PreviousInstallDir" in line
                or "$SMPROGRAMS" in line,
                f"Uninstall target escapes the program folder: {line}")

    def test_uninstall_keeps_user_data(self):
        """Uninstall must not delete the data folder; only the program folder."""
        uninstall = self.text.split("Section \"Uninstall\"", 1)[1]
        commands = [line.strip() for line in uninstall.splitlines()
                    if line.strip() and not line.strip().startswith(";")]
        body = "\n".join(commands)
        self.assertIn('RMDir /r "$INSTDIR"', body)
        self.assertNotIn("LOCALAPPDATA", body)
        self.assertNotIn("$APPDATA", body)
        for line in [c for c in commands if c.startswith("RMDir")]:
            self.assertTrue("$INSTDIR" in line or "$SMPROGRAMS" in line,
                            f"Uninstall target escapes the program folder: {line}")

    def test_turkish_language_is_available(self):
        self.assertIn('!insertmacro MUI_LANGUAGE "Turkish"', self.text)

    def test_registry_view_is_64_bit(self):
        """NSIS is 32-bit: the registry view must be explicitly 64-bit.

        Otherwise keys land under WOW6432Node and do not appear in Programs.
        SetRegView is only valid inside a Section/Function, so it must live
        in .onInit.
        """
        init = self.text.split("Function .onInit", 1)[1].split("FunctionEnd", 1)[0]
        self.assertIn("SetRegView 64", init)
        uninstall = self.text.split('Section "Uninstall"', 1)[1]
        self.assertIn("SetRegView 64", uninstall)

    def test_desktop_shortcut_is_per_user(self):
        """Public Desktop is invisible on a OneDrive-redirected desktop.

        The desktop shortcut is written per user.
        """
        section = self.text.split('Section "NetSonar"', 1)[1]
        shortcut_line = [line.strip() for line in section.splitlines()
                         if line.strip().startswith('CreateShortcut "$DESKTOP')]
        self.assertTrue(shortcut_line)
        # "current" context, not "all".
        self.assertIn('SetShellVarContext current', section)
        current_index = section.index("SetShellVarContext current")
        shortcut_index = section.index(shortcut_line[0])
        self.assertLess(current_index, shortcut_index)

    def test_version_is_injected_by_build(self):
        self.assertIn("!ifndef APP_VERSION", self.text)


class BuildScriptTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(BUILD)

    def test_build_produces_the_installer(self):
        self.assertIn("$VersionedStem.exe", self.text)
        self.assertIn("makensis", self.text.lower())

    def test_build_passes_the_version_to_nsis(self):
        self.assertIn("/DAPP_VERSION=$Version", self.text)

    def test_build_cleans_only_its_own_directories(self):
        self.assertIn("Unsafe cleanup path", self.text)

    def test_build_refuses_to_package_user_data(self):
        self.assertIn("Files that must not be packaged were found", self.text)

    def test_old_release_artifacts_are_removed(self):
        self.assertIn("NetSonar-(v\\d+\\.\\d+\\.\\d+(-Setup)?|\\d+\\.\\d+\\.\\d+)\\.(exe|bat)$",
                      self.text)


class SpecTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(SPEC)

    def test_package_is_a_folder_not_a_single_file(self):
        """Folder package: the update replaces the program folder in place."""
        self.assertIn("COLLECT(", self.text)
        self.assertIn('name="NetSonar"', self.text)

    def test_store_module_is_bundled(self):
        self.assertIn('"store"', self.text)

    def test_unused_qt_modules_are_excluded(self):
        self.assertIn("excludes=[", self.text)
        self.assertIn("PyQt6.QtQuick", self.text)


if __name__ == "__main__":
    unittest.main()
