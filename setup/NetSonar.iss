#define MyAppName "NetSonar"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "NetSonar"
#define MyAppExeName "NetSonar.exe"

[Setup]
AppId={{2B3AD774-4A0E-4BCA-A449-7D73B1C88B2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=build\installer
OutputBaseFilename=NetSonar-Setup-v{#MyAppVersion}-staging
SetupIconFile=..\netsonar-v3.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"; Flags: unchecked

[Files]
Source: "dist\NetSonar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\NetSonar"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\NetSonar"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "NetSonar'ı başlat"; Flags: nowait postinstall skipifsilent

[Code]
const
  NpcapDownloadUrl = 'https://npcap.com/#download';

function NpcapInstalled: Boolean;
begin
  Result :=
    (FileExists(ExpandConstant('{sys}\Npcap\wpcap.dll')) and
     FileExists(ExpandConstant('{sys}\Npcap\Packet.dll'))) or
    (FileExists(ExpandConstant('{syswow64}\Npcap\wpcap.dll')) and
     FileExists(ExpandConstant('{syswow64}\Npcap\Packet.dll')));
end;

function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  Result := NpcapInstalled;
  if Result then
    Exit;

  if MsgBox(
    'NetSonar canlı ağ trafiğini izlemek için Npcap gerektirir.' + #13#10 + #13#10 +
    'Npcap bu bilgisayarda bulunamadı. Resmî indirme sayfası açılsın mı?' + #13#10 +
    'Npcap''i kurduktan sonra bu kurulum dosyasını yeniden çalıştırın.',
    mbConfirmation, MB_YESNO) = IDYES then
  begin
    ShellExec('open', NpcapDownloadUrl, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
  end;

  MsgBox('Npcap kurulmadan NetSonar kurulumu devam edemez.', mbInformation, MB_OK);
end;
