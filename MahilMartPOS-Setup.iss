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
  LicensePage: TInputQueryWizardPage;
  LicensePath: string;
  ActivationNoticePath: string;

function GetMachineId: string;
begin
  Result := Trim(GetEnv('COMPUTERNAME'));
  if Result = '' then
    Result := GetDateTimeString('yyyymmddhhnnss', '-', ':');
  Result := Uppercase(Result);
end;

function BuildChecksumValue(Seed: string; Multiplier, Offset: Integer): Integer;
var
  I: Integer;
begin
  Result := 0;
  for I := 1 to Length(Seed) do
  begin
    Result := (Result + (Ord(Seed[I]) + Offset) * (I + Multiplier)) mod 16777215;
  end;
end;

function ToFixedHex(Value, Width: Integer): string;
var
  HexChars: string;
  I: Integer;
  Digit: Integer;
begin
  HexChars := '0123456789ABCDEF';
  Result := '';
  for I := 1 to Width do
  begin
    Digit := Value mod 16;
    Result := Copy(HexChars, Digit + 1, 1) + Result;
    Value := Value div 16;
  end;
end;

function GenerateLicenseKey(Email, MachineId, IssuedAt: string): string;
var
  Seed: string;
  PartA: Integer;
  PartB: Integer;
  PartC: Integer;
  PartD: Integer;
begin
  Seed := Uppercase(Trim(Email)) + '|' + Uppercase(Trim(MachineId)) + '|' + Trim(IssuedAt);
  PartA := BuildChecksumValue(Seed, 3, 11);
  PartB := BuildChecksumValue(Seed, 7, 19);
  PartC := (PartA * 31 + PartB * 17 + Length(Seed) * 97) mod 16777215;
  PartD := (PartA + PartB + PartC + Length(Seed) * 13) mod 16777215;
  Result := ToFixedHex(PartA, 6) + ToFixedHex(PartB, 6) + ToFixedHex(PartC, 6) + ToFixedHex(PartD, 6);
end;

procedure InitializeWizard;
begin
  LicensePath := ExpandConstant('{commonappdata}\MahilMartPOS\license.ini');
  ActivationNoticePath := ExpandConstant('{commonappdata}\MahilMartPOS\license_activation_pending.ini');

  LicensePage := CreateInputQueryPage(
    wpSelectDir,
    'License Activation',
    'Activate your installation',
    'Enter the email address to bind this installation. A one-time license key will be generated for this machine.'
  );
  LicensePage.Add('Email:', False);
  if FileExists(LicensePath) then
    LicensePage.Values[0] := GetIniString('license', 'email', '', LicensePath);

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
  if CurPageID = LicensePage.ID then
  begin
    if Pos('@', LicensePage.Values[0]) = 0 then
    begin
      MsgBox('A valid email address is required for license activation.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;
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
  LicenseContent: string;
  ActivationNoticeContent: string;
  MachineId: string;
  IssuedAt: string;
begin
  if CurStep = ssInstall then
  begin
    ConfigDir := ExpandConstant('{commonappdata}\MahilMartPOS');
    ForceDirectories(ConfigDir);
    ConfigPath := ConfigDir + '\db_config.ini';
    LicensePath := ConfigDir + '\license.ini';
    ActivationNoticePath := ConfigDir + '\license_activation_pending.ini';

    Content :=
      '[database]' + #13#10 +
      'host=' + DbPage.Values[0] + #13#10 +
      'port=' + DbPage.Values[1] + #13#10 +
      'name=' + DbPage.Values[2] + #13#10 +
      'user=' + DbPage.Values[3] + #13#10 +
      'password=' + DbPage.Values[4] + #13#10;

    SaveStringToFile(ConfigPath, Content, False);

    if not FileExists(LicensePath) then
    begin
      MachineId := GetMachineId;
      IssuedAt := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
      LicenseContent :=
        '[license]' + #13#10 +
        'email=' + LicensePage.Values[0] + #13#10 +
        'machine_id=' + MachineId + #13#10 +
        'issued_at=' + IssuedAt + #13#10 +
        'license_key=' + GenerateLicenseKey(LicensePage.Values[0], MachineId, IssuedAt) + #13#10;
      SaveStringToFile(LicensePath, LicenseContent, False);

      ActivationNoticeContent :=
        '[activation]' + #13#10 +
        'email=' + LicensePage.Values[0] + #13#10 +
        'machine_id=' + MachineId + #13#10 +
        'issued_at=' + IssuedAt + #13#10 +
        'license_key=' + GenerateLicenseKey(LicensePage.Values[0], MachineId, IssuedAt) + #13#10;
      SaveStringToFile(ActivationNoticePath, ActivationNoticeContent, False);
    end
    else
      Log('Existing license detected; preserving current license file.');
  end;
end;
