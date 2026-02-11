#define MyAppName "MahilMart POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MahilTechLab"
#define MyAppURL ""
#define MyAppExeName "MahilMartPOS.exe"
#define MyAppDirName "MahilMartPOS"
#define SourceDir "."
#ifexist "{#SourceDir}\assets\branding\app.ico"
  #define MyAppIconFile "{#SourceDir}\assets\branding\app.ico"
#endif

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
#ifdef MyAppIconFile
SetupIconFile={#MyAppIconFile}
#endif

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
const
  FixedLicenseEmail = 'mahiltechlab.ops@gmail.com';

var
  DbPage: TInputQueryWizardPage;
  LicenseKeyPage: TInputQueryWizardPage;
  LicensePath: string;
  ActivationNoticePath: string;
  CurrentMachineId: string;

function GetMachineId: string;
begin
  Result := Trim(GetEnv('COMPUTERNAME'));
  if Result = '' then
    Result := GetDateTimeString('yyyymmddhhnnss', '-', ':');
  Result := Uppercase(Result);
end;

function NormalizeUpper(Value: string): string;
begin
  Result := Uppercase(Trim(Value));
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

function IsUpperChar(C: Char): Boolean;
begin
  Result := (C >= 'A') and (C <= 'Z');
end;

function IsLowerChar(C: Char): Boolean;
begin
  Result := (C >= 'a') and (C <= 'z');
end;

function IsDigitChar(C: Char): Boolean;
begin
  Result := (C >= '0') and (C <= '9');
end;

function IsSpecialChar(C: Char): Boolean;
begin
  Result := Pos(C, '@#$%&*!?') > 0;
end;

function IsValidLicenseFormat(Value: string): Boolean;
var
  HasUpper: Boolean;
  HasLower: Boolean;
  HasDigit: Boolean;
  SpecialCount: Integer;
  I: Integer;
begin
  Value := Trim(Value);
  if Length(Value) <> 32 then
  begin
    Result := False;
    exit;
  end;

  HasUpper := False;
  HasLower := False;
  HasDigit := False;
  SpecialCount := 0;

  for I := 1 to Length(Value) do
  begin
    if IsUpperChar(Value[I]) then
      HasUpper := True
    else if IsLowerChar(Value[I]) then
      HasLower := True
    else if IsDigitChar(Value[I]) then
      HasDigit := True
    else if IsSpecialChar(Value[I]) then
      SpecialCount := SpecialCount + 1
    else
    begin
      Result := False;
      exit;
    end;
  end;

  Result := HasUpper and HasLower and HasDigit and (SpecialCount >= 2);
end;

function GenerateLicenseKey(Email, MachineId: string): string;
var
  Seed: string;
  State: Integer;
  BaseKey: string;
  Charset: string;
  SpecialSet: string;
  SpecialA: string;
  SpecialB: string;
  I: Integer;
begin
  Seed := NormalizeUpper(Email) + '|' + NormalizeUpper(MachineId);
  State := (BuildChecksumValue(Seed, 3, 11) + BuildChecksumValue(Seed, 7, 19) + Length(Seed) * 97) mod 16777215;

  BaseKey := '';
  for I := 0 to 29 do
  begin
    State := (State * 73 + 19 + I * 131) mod 16777215;
    if (I mod 3) = 0 then
      Charset := 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    else if (I mod 3) = 1 then
      Charset := 'abcdefghijkmnopqrstuvwxyz'
    else
      Charset := '23456789';

    BaseKey := BaseKey + Copy(Charset, (State mod Length(Charset)) + 1, 1);
  end;

  SpecialSet := '@#$%&*!?';
  State := (State * 73 + 17) mod 16777215;
  SpecialA := Copy(SpecialSet, (State mod Length(SpecialSet)) + 1, 1);
  State := (State * 73 + 29) mod 16777215;
  SpecialB := Copy(SpecialSet, (State mod Length(SpecialSet)) + 1, 1);

  Result := Copy(BaseKey, 1, 10) + SpecialA + Copy(BaseKey, 11, 10) + SpecialB + Copy(BaseKey, 21, 10);
end;

procedure InitializeWizard;
begin
  LicensePath := ExpandConstant('{commonappdata}\MahilMartPOS\license.ini');
  ActivationNoticePath := ExpandConstant('{commonappdata}\MahilMartPOS\license_activation_pending.ini');
  CurrentMachineId := GetMachineId;

  LicenseKeyPage := CreateInputQueryPage(
    wpSelectDir,
    'License Activation',
    'Enter license key',
    'Use the 32-character license key generated in Admin > License Manager.' + #13#10 +
    'Machine ID: ' + CurrentMachineId
  );
  LicenseKeyPage.Add('License Key:', False);
  LicenseKeyPage.Values[0] := '';

  DbPage := CreateInputQueryPage(
    LicenseKeyPage.ID,
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
var
  EnteredKey: string;
  ExpectedKey: string;
begin
  Result := True;
  if CurPageID = LicenseKeyPage.ID then
  begin
    EnteredKey := Trim(LicenseKeyPage.Values[0]);
    ExpectedKey := GenerateLicenseKey(FixedLicenseEmail, CurrentMachineId);
    if EnteredKey = '' then
    begin
      MsgBox('License key is required.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if not IsValidLicenseFormat(EnteredKey) then
    begin
      MsgBox(
        'License key format invalid.' + #13#10 +
        'Required: 32 characters with uppercase, lowercase, numbers, and at least 2 special characters.',
        mbError,
        MB_OK
      );
      Result := False;
      exit;
    end;
    if EnteredKey <> ExpectedKey then
    begin
      MsgBox(
        'Invalid license key for this machine.' + #13#10 +
        'Machine ID: ' + CurrentMachineId + #13#10 +
        'Generate key from your admin License Manager page.',
        mbError,
        MB_OK
      );
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
  MachineId: string;
  IssuedAt: string;
  EnteredKey: string;
  EnteredEmail: string;
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

    EnteredEmail := FixedLicenseEmail;
    MachineId := CurrentMachineId;
    IssuedAt := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
    EnteredKey := Trim(LicenseKeyPage.Values[0]);

    LicenseContent :=
      '[license]' + #13#10 +
      'email=' + EnteredEmail + #13#10 +
      'machine_id=' + MachineId + #13#10 +
      'issued_at=' + IssuedAt + #13#10 +
      'license_key=' + EnteredKey + #13#10;
    SaveStringToFile(LicensePath, LicenseContent, False);
    if FileExists(ActivationNoticePath) then
      DeleteFile(ActivationNoticePath);
  end;
end;
