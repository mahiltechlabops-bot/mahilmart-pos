#define MyAppName "MahilMart POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MahilTechLab"
#define MyAppURL ""
#define MyAppExeName "MahilMartPOS.exe"
#define MyAppDirName "MahilMartPOS"
#define SourceDir "."

[Setup]
AppId={{7A8E2C8B-7A21-4A0E-9B58-89C2F2F8B6E0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppDirName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#SourceDir}\installer\output
OutputBaseFilename=MahilMartPOS-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: postinstall shellexec skipifsilent

[Code]
var
  DbPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  DbPage := CreateInputQueryPage(
    wpSelectDir,
    'Database Settings',
    'Configure PostgreSQL connection',
    'These settings will be saved for MahilMart POS.'
  );
  DbPage.Add('Host:', False);
  DbPage.Add('Port:', False);
  DbPage.Add('Database Name:', False);
  DbPage.Add('User:', False);
  DbPage.Add('Password:', True);

  DbPage.Values[0] := 'localhost';
  DbPage.Values[1] := '5432';
  DbPage.Values[2] := 'mmpos2';
  DbPage.Values[3] := 'postgres';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DbPage.ID then
  begin
    if Trim(DbPage.Values[2]) = '' then
    begin
      MsgBox('Database name is required.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if Trim(DbPage.Values[3]) = '' then
    begin
      MsgBox('Database user is required.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: string;
  ConfigPath: string;
  Content: string;
begin
  if CurStep = ssInstall then
  begin
    ConfigDir := ExpandConstant('{commonappdata}\MahilMartPOS');
    ForceDirectories(ConfigDir);
    ConfigPath := ConfigDir + '\db_config.ini';

    Content :=
      '[database]' + #13#10 +
      'host=' + DbPage.Values[0] + #13#10 +
      'port=' + DbPage.Values[1] + #13#10 +
      'name=' + DbPage.Values[2] + #13#10 +
      'user=' + DbPage.Values[3] + #13#10 +
      'password=' + DbPage.Values[4] + #13#10;

    SaveStringToFile(ConfigPath, Content, False);
  end;
end;
