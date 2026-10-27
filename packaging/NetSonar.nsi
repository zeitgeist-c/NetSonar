; NetSonar — Windows kurulumcusu (NSIS)
;
; Kurulum sabit yere yapar: C:\Program Files\NetSonar
; Güncelleme bu kurulumcuyu sessizce (/S) yeniden calistirir; program klasoru
; yerinde degisir, kullanici verisi ve model deposu (%LOCALAPPDATA%\NetSonar)
; ASLA dokunulmaz.
;
; Sürüm build.ps1 tarafindan -DAPP_VERSION ile verilir.
Unicode True
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!ifndef APP_VERSION
  !error "APP_VERSION build.ps1 tarafindan verilmelidir"
!endif

!define APP_NAME "NetSonar"
!define APP_EXE "NetSonar.exe"
!define APP_PUBLISHER "zeitgeist-c"
!define APP_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

Name "${APP_NAME}"
BrandingText "${APP_NAME}"
OutFile "..\dist\NetSonar-v${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
Unicode true
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1055 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1055 "FileDescription" "${APP_NAME} Kurulum"
VIAddVersionKey /LANG=1055 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1055 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1055 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1055 "LegalCopyright" "Copyright 2026 ${APP_NAME}"
VIAddVersionKey /LANG=1055 "OriginalFilename" "NetSonar-v${APP_VERSION}-Setup.exe"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "${APP_NAME}'ı başlat"
!define MUI_FINISHPAGE_RUN_CHECKBOX "Kurulumdan sonra ${APP_NAME} başlatılsın"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Turkish"

Var PreviousInstallDir
Var PreviousUninstaller
Var RunningApp
Var AutostartWasEnabled

; ─── Kurulum oncesi kontroller ──────────────────────────────────────
Function .onInit
  ; Bu kurulumcu 64-bit uygulama kurar (Program Files). NSIS 32-bit oldugu
  ; icin kayit defteri gorunumu acikca 64-bit yapilir; aksi halde anahtarlar
  ; WOW6432Node altina duser ve Programlar listesinde gorunmez.
  SetRegView 64

  ; Onceki surumun kurulum yolunu hatirla: yeni surum ayni yere yazilir.
  ReadRegStr $PreviousInstallDir HKLM "Software\${APP_NAME}" "InstallDir"
  ReadRegStr $PreviousUninstaller HKLM "${APP_UNINST_KEY}" "UninstallString"
  StrCpy $RunningApp ""

  ; Otomatik baslatma tercihi: kapaliysa kurulum onu AÇMAZ. Guncelleme
  ; sonrasi da ayni tercih korunur.
  StrCpy $AutostartWasEnabled "0"
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  ${If} $0 != ""
    StrCpy $AutostartWasEnabled "1"
  ${EndIf}

  ; Calisan NetSonar varsa kurulum dosyalari kilitli olur; kapat ve bekle.
  nsExec::ExecToStack 'cmd /c tasklist /FI "IMAGENAME eq ${APP_EXE}" /NH'
  Pop $0
  Pop $1
  ${If} $1 != ""
    DetailPrint "Çalışan NetSonar kapatılıyor..."
    nsExec::ExecToStack 'cmd /c taskkill /F /IM ${APP_EXE} /T'
    Pop $0
    Pop $1
    ; Dosya kilitlerinin release olması için kısa bekleme.
    Sleep 1500
  ${EndIf}

  ; Npcap yoksa kurulumu engelleme; uygulama açılışta uyarır.
FunctionEnd

Function .onVerifyInstDir
  ; Program Files altina yazmak icin yonetici gerekir; zaten admin istegi var.
  ${If} $INSTDIR == ""
    Abort
  ${EndIf}
FunctionEnd

; ─── Kurulum ────────────────────────────────────────────────────────
Section "NetSonar" SEC_APP
  SectionIn RO
  SetShellVarContext all
  SetOutPath "$INSTDIR"

  ; Eski surumden kalan dosyalari temizle: guncellemede "hepsi sil, yenisini
  ; yaz" davranisi. Kullanici verisi ve store bu klasorun disinda oldugu
  ; icin etkilenmez.
  ${If} $PreviousInstallDir != ""
    ${AndIf} $PreviousInstallDir != $INSTDIR
      RMDir /r "$PreviousInstallDir"
  ${EndIf}
  File /r "app-dist\NetSonar\*.*"

  ; Kisa yollar: masaustu ve Baslat menusu.
  ; Masaustu kisayolu KULLANICIYA OZEL olur (SetShellVarContext current):
  ; "all" kullanimi OneDrive yonlendirilmis masaustunde Public Desktop'e
  ; yaziyor ve kullanicinin masaustunde gorunmuyordu.
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} kaldır.lnk" "$INSTDIR\Uninstall.exe"
  SetShellVarContext current
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  SetShellVarContext all

  ; Kaldirici
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Kayit defteri: kurulum yolu ve kaldirma bilgisi
  WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoRepair" 1

  ; Otomatik baslatma kaydi varsa yeni exe'ye yonlendir. Kayit yoksa
  ; kullanici tercihi degismemeli; o yuzdu yalnizca mevcut kayit guncellenir.
  ${If} $AutostartWasEnabled == "1"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" \
      "'$INSTDIR\${APP_EXE}'"
  ${EndIf}
SectionEnd

; ─── Kaldirma ───────────────────────────────────────────────────────
Section "Uninstall"
  ; Ayni gorunum: kayit defteri anahtarlari 64-bit view'da duruyor.
  SetRegView 64
  SetShellVarContext all
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME} kaldır.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  ; Masaustu kisayolu kurulumda kullaniciya ozel yazildi; ayni yerden silinir.
  ; (Eski kurulumlar Public Desktop'e yazmisti, o da temizlenir.)
  SetShellVarContext current
  Delete "$DESKTOP\${APP_NAME}.lnk"
  SetShellVarContext all
  ; Eski kurulumlar masaustu kisayolunu "all" baglaminda yazmisti, yani
  ; Public Desktop'e; $DESKTOP bu baglamda zaten o yeri gosterir.
  Delete "$DESKTOP\${APP_NAME}.lnk"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  DeleteRegKey HKLM "${APP_UNINST_KEY}"
  DeleteRegKey HKLM "Software\${APP_NAME}"

  ; Program klasorunu sil. Kullanici verisi ve model deposu
  ; (%LOCALAPPDATA%\NetSonar) SILINMEZ: kullaninin verisi kurulumdan
  ; bagimsiz yasar.
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR\_internal"
  RMDir "$INSTDIR"
  ; Kalan dosya varsa klasor silinir; kullanici verisi etkilenmez.
  RMDir /r "$INSTDIR"
SectionEnd
