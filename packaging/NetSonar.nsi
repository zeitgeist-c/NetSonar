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
OutFile "..\dist\NetSonar-${APP_VERSION}.exe"
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
VIAddVersionKey /LANG=1055 "OriginalFilename" "NetSonar-${APP_VERSION}.exe"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "$(nsRunText)"
!define MUI_FINISHPAGE_RUN_CHECKBOX "$(nsRunCheck)"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
LangString nsRunText ${LANG_ENGLISH} "Launch ${APP_NAME}"
LangString nsRunText ${LANG_TURKISH} "${APP_NAME}'ı başlat"
LangString nsRunText ${LANG_GERMAN} "${APP_NAME} starten"
LangString nsRunText ${LANG_SPANISH} "Iniciar ${APP_NAME}"
LangString nsRunText ${LANG_FRENCH} "Lancer ${APP_NAME}"
LangString nsRunText ${LANG_ITALIAN} "Avvia ${APP_NAME}"
LangString nsRunText ${LANG_PORTUGUESEBR} "Iniciar ${APP_NAME}"
LangString nsRunText ${LANG_RUSSIAN} "Запустить ${APP_NAME}"
LangString nsRunText ${LANG_POLISH} "Uruchom ${APP_NAME}"
LangString nsRunText ${LANG_DUTCH} "${APP_NAME} starten"
LangString nsRunText ${LANG_SIMPCHINESE} "启动 ${APP_NAME}"
LangString nsRunText ${LANG_JAPANESE} "${APP_NAME} を起動"
LangString nsRunText ${LANG_KOREAN} "${APP_NAME} 시작"
LangString nsRunCheck ${LANG_ENGLISH} "Run ${APP_NAME} after setup"
LangString nsRunCheck ${LANG_TURKISH} "Kurulumdan sonra ${APP_NAME} başlatılsın"
LangString nsRunCheck ${LANG_GERMAN} "${APP_NAME} nach dem Setup starten"
LangString nsRunCheck ${LANG_SPANISH} "Ejecutar ${APP_NAME} después de la instalación"
LangString nsRunCheck ${LANG_FRENCH} "Lancer ${APP_NAME} après l'installation"
LangString nsRunCheck ${LANG_ITALIAN} "Esegui ${APP_NAME} dopo il setup"
LangString nsRunCheck ${LANG_PORTUGUESEBR} "Executar ${APP_NAME} após a instalação"
LangString nsRunCheck ${LANG_RUSSIAN} "Запустить ${APP_NAME} после установки"
LangString nsRunCheck ${LANG_POLISH} "Uruchom ${APP_NAME} po instalacji"
LangString nsRunCheck ${LANG_DUTCH} "${APP_NAME} starten na de setup"
LangString nsRunCheck ${LANG_SIMPCHINESE} "安装后运行 ${APP_NAME}"
LangString nsRunCheck ${LANG_JAPANESE} "セットアップ後に ${APP_NAME} を実行"
LangString nsRunCheck ${LANG_KOREAN} "설치 후 ${APP_NAME} 실행"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "Polish"
!insertmacro MUI_LANGUAGE "Dutch"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "Korean"

Var PreviousInstallDir
Var PreviousUninstaller
Var RunningApp
Var AutostartWasEnabled

; ─── Kurulum oncesi kontroller ──────────────────────────────────────
Function .onInit
  !insertmacro MUI_LANGDLL_DISPLAY
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
    DetailPrint "Closing running NetSonar..."
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

; KURULUM DILI DEVRI: secilen dili kurulum klasorune yaz.
; Uygulama kayitli tercihi yoksa bunu okur; guncelleme tercihi ezmez.
  ${If} $LANGUAGE = 1033
  StrCpy $0 "en"
  ${ElseIf} $LANGUAGE = 1055
  StrCpy $0 "tr"
  ${ElseIf} $LANGUAGE = 1031
  StrCpy $0 "de"
  ${ElseIf} $LANGUAGE = 1034
  StrCpy $0 "es"
  ${ElseIf} $LANGUAGE = 1036
  StrCpy $0 "fr"
  ${ElseIf} $LANGUAGE = 1040
  StrCpy $0 "it"
  ${ElseIf} $LANGUAGE = 1046
  StrCpy $0 "pt-BR"
  ${ElseIf} $LANGUAGE = 1049
  StrCpy $0 "ru"
  ${ElseIf} $LANGUAGE = 1045
  StrCpy $0 "pl"
  ${ElseIf} $LANGUAGE = 1043
  StrCpy $0 "nl"
  ${ElseIf} $LANGUAGE = 2052
  StrCpy $0 "zh-CN"
  ${ElseIf} $LANGUAGE = 1041
  StrCpy $0 "ja"
  ${ElseIf} $LANGUAGE = 1042
  StrCpy $0 "ko"
  ${Else}
  StrCpy $0 "en"
  ${EndIf}
  FileOpen $1 "$INSTDIR\install-language.txt" w
  ${If} $1 != ""
  FileWrite $1 "$0"
  FileClose $1
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
