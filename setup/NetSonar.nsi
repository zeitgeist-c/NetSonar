Unicode True
!include "MUI2.nsh"

!define APP_NAME "NetSonar"
!define APP_VERSION "0.5.2"
!define APP_EXE "NetSonar.exe"

Name "${APP_NAME}"
OutFile "build\installer\NetSonar-Setup-v${APP_VERSION}-staging.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Icon "..\netsonar-v3.ico"
UninstallIcon "..\netsonar-v3.ico"
BrandingText "NetSonar"
VIProductVersion "0.5.2.0"
VIAddVersionKey /LANG=1055 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1055 "FileDescription" "NetSonar Kurulum"
VIAddVersionKey /LANG=1055 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1055 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1055 "LegalCopyright" "Copyright 2026 NetSonar"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "NetSonar'ı başlat"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Turkish"

Function .onInit
  IfFileExists "$WINDIR\System32\Npcap\wpcap.dll" npcap_second
  IfFileExists "$WINDIR\Sysnative\Npcap\wpcap.dll" npcap_second
  IfFileExists "$WINDIR\SysWOW64\Npcap\wpcap.dll" npcap_second
  Goto npcap_missing
npcap_second:
  IfFileExists "$WINDIR\System32\Npcap\Packet.dll" npcap_found
  IfFileExists "$WINDIR\Sysnative\Npcap\Packet.dll" npcap_found
  IfFileExists "$WINDIR\SysWOW64\Npcap\Packet.dll" npcap_found
npcap_missing:
  MessageBox MB_YESNO|MB_ICONEXCLAMATION \
    "NetSonar canlı ağ trafiğini izlemek için Npcap gerektirir.$\r$\n$\r$\nNpcap bulunamadı. Resmî indirme sayfası açılsın mı?$\r$\nNpcap'i kurduktan sonra bu kurulumu yeniden çalıştırın." \
    IDNO npcap_abort
  ExecShell "open" "https://npcap.com/#download"
npcap_abort:
  Abort
npcap_found:
FunctionEnd

Section "!NetSonar (gerekli)" SEC_APP
  SectionIn RO
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  File /r "dist\NetSonar\*.*"
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "NetSonar"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
SectionEnd

Section /o "Masaüstü kısayolu" SEC_DESKTOP
  SetShellVarContext all
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKLM "Software\${APP_NAME}"
  RMDir /r "$INSTDIR"
SectionEnd
