"""Kurulumcu sözleşmeleri.

NSIS betiği (packaging/NetSonar.nsi) ve build akışı, tek kanalı (kurulumcu)
ve koruma kurallarını (store'a dokunmama, sabit kurulum yolu) kodla sabitler.
Betiğin kendisi metin olarak okunur: çalıştırmadan sözleşmesi doğrulanır.
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

    def test_installer_requires_admin(self):
        self.assertIn("RequestExecutionLevel admin", self.text)

    def test_shortcuts_are_created(self):
        self.assertIn('CreateShortcut "$DESKTOP\\${APP_NAME}.lnk"', self.text)
        self.assertIn('CreateShortcut "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"',
                      self.text)

    def test_uninstaller_is_written(self):
        self.assertIn('WriteUninstaller "$INSTDIR\\Uninstall.exe"', self.text)

    def test_autostart_is_only_refreshed_when_it_was_enabled(self):
        """Tercih kapalıysa kurulum onu açmamalı."""
        self.assertIn("AutostartWasEnabled", self.text)
        self.assertIn("${If} $AutostartWasEnabled == \"1\"", self.text)

    def test_store_and_user_data_are_never_written(self):
        """Kurulumcu yalnizca program klasorune ve kayit defterine yazmali.

        Yorum satirlari LOCALAPPDATA icerebilir; bu bir komut degil. Gercek
        yazma komutlarinda kullanici verisi yolu (LOCALAPPDATA/APPDATA)
        gecmemeli.
        """
        commands = [line.strip() for line in self.text.splitlines()
                    if line.strip() and not line.strip().startswith(";")]
        body = "\n".join(commands)
        self.assertNotIn("LOCALAPPDATA", body)
        self.assertNotIn("$APPDATA", body)
        self.assertNotIn("\\store", body)
        # Program dosyalari yalnizca $INSTDIR altina yazilir.
        self.assertIn('SetOutPath "$INSTDIR"', body)
        self.assertIn('File /r "app-dist\\NetSonar\\*.*"', body)
        # Silme komutlari program klasoruyle sinirli.
        deletions = [line for line in commands if line.startswith("RMDir")]
        for line in deletions:
            self.assertTrue(
                "$INSTDIR" in line or "$PreviousInstallDir" in line
                or "$SMPROGRAMS" in line,
                f"Kaldirma hedefi program klasoru disina cikiyor: {line}")

    def test_uninstall_keeps_user_data(self):
        """Kaldirma veri klasorunu silmemeli; sadece program klasoru."""
        uninstall = self.text.split("Section \"Uninstall\"", 1)[1]
        commands = [line.strip() for line in uninstall.splitlines()
                    if line.strip() and not line.strip().startswith(";")]
        body = "\n".join(commands)
        self.assertIn('RMDir /r "$INSTDIR"', body)
        self.assertNotIn("LOCALAPPDATA", body)
        self.assertNotIn("$APPDATA", body)
        for line in [c for c in commands if c.startswith("RMDir")]:
            self.assertTrue("$INSTDIR" in line or "$SMPROGRAMS" in line,
                            f"Kaldirma hedefi program klasoru disina cikiyor: {line}")

    def test_turkish_language_is_available(self):
        self.assertIn('!insertmacro MUI_LANGUAGE "Turkish"', self.text)

    def test_registry_view_is_64_bit(self):
        """NSIS 32-bit: kayit defteri gorunumu acikca 64-bit olmali.

        Aksi halde anahtarlar WOW6432Node altina duser ve Programlar
        listesinde gorunmez. SetRegView yalnizca Section/Function icinde
        gecerli, bu yuzden .onInit icinde olmali.
        """
        init = self.text.split("Function .onInit", 1)[1].split("FunctionEnd", 1)[0]
        self.assertIn("SetRegView 64", init)
        uninstall = self.text.split('Section "Uninstall"', 1)[1]
        self.assertIn("SetRegView 64", uninstall)

    def test_desktop_shortcut_is_per_user(self):
        """OneDrive yonlendirilmis masaustunde Public Desktop gorunmez.

        Masaustu kisayolu kullaniciya ozel yazilir.
        """
        section = self.text.split('Section "NetSonar"', 1)[1]
        shortcut_line = [line.strip() for line in section.splitlines()
                         if line.strip().startswith('CreateShortcut "$DESKTOP')]
        self.assertTrue(shortcut_line)
        # "current" baglami, "all" degil.
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
        self.assertIn("$VersionedStem-Setup.exe", self.text)
        self.assertIn("makensis", self.text.lower())

    def test_build_passes_the_version_to_nsis(self):
        self.assertIn("/DAPP_VERSION=$Version", self.text)

    def test_build_cleans_only_its_own_directories(self):
        self.assertIn("Guvenli olmayan temizleme yolu", self.text)

    def test_build_refuses_to_package_user_data(self):
        self.assertIn("Paketlenmemesi gereken dosyalar bulundu", self.text)

    def test_old_release_artifacts_are_removed(self):
        self.assertIn("NetSonar-v\\d+\\.\\d+\\.\\d+(-Setup)?\\.(exe|bat)$",
                      self.text)


class SpecTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(SPEC)

    def test_package_is_a_folder_not_a_single_file(self):
        """Klasorlu paket: guncelleme program klasorunu yerinde degistirir."""
        self.assertIn("COLLECT(", self.text)
        self.assertIn('name="NetSonar"', self.text)

    def test_store_module_is_bundled(self):
        self.assertIn('"store"', self.text)

    def test_unused_qt_modules_are_excluded(self):
        self.assertIn("excludes=[", self.text)
        self.assertIn("PyQt6.QtQuick", self.text)


if __name__ == "__main__":
    unittest.main()
