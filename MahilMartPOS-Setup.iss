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
const
  FixedLicenseEmail = 'mahiltechlab.ops@gmail.com';

var
  DbPage: TInputQueryWizardPage;
  LicenseEmailPage: TInputQueryWizardPage;
  LicenseKeyPage: TInputQueryWizardPage;
  LicensePath: string;
  ActivationNoticePath: string;
  PendingEmail: string;
  PendingMachineId: string;
  PendingIssuedAt: string;
  PendingLicenseKey: string;
  KeyEmailSent: Boolean;

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
  FullKey: string;
begin
  Seed := NormalizeUpper(Email) + '|' + NormalizeUpper(MachineId) + '|' + Trim(IssuedAt);
  PartA := BuildChecksumValue(Seed, 3, 11);
  PartB := BuildChecksumValue(Seed, 7, 19);
  PartC := (PartA * 31 + PartB * 17 + Length(Seed) * 97) mod 16777215;
  PartD := (PartA + PartB + PartC + Length(Seed) * 13) mod 16777215;
  FullKey := ToFixedHex(PartA, 6) + ToFixedHex(PartB, 6) + ToFixedHex(PartC, 6) + ToFixedHex(PartD, 6);
  Result := Copy(FullKey, 1, 10);
end;

function EscapePSSingleQuoted(Value: string): string;
begin
  Result := Value;
  StringChangeEx(Result, '''', '''''', True);
end;

function SendLicenseKeyEmail(MachineId, IssuedAt, LicenseKey: string): Boolean;
var
  ScriptPath: string;
  ScriptContent: string;
  ResultCode: Integer;
  EmailAddress: string;
  AppPassword: string;
begin
  EmailAddress := FixedLicenseEmail;
  AppPassword := 'fbopbtqzaqvedzkg';
  ScriptPath := ExpandConstant('{tmp}\send_license_key.ps1');

  ScriptContent :=
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '$toEmail = ''' + EscapePSSingleQuoted(EmailAddress) + '''' + #13#10 +
    '$appPassword = ''' + EscapePSSingleQuoted(AppPassword) + '''' + #13#10 +
    '$machineId = ''' + EscapePSSingleQuoted(MachineId) + '''' + #13#10 +
    '$issuedAt = ''' + EscapePSSingleQuoted(IssuedAt) + '''' + #13#10 +
    '$licenseKey = ''' + EscapePSSingleQuoted(LicenseKey) + '''' + #13#10 +
    '$sec = ConvertTo-SecureString $appPassword -AsPlainText -Force' + #13#10 +
    '$cred = New-Object System.Management.Automation.PSCredential($toEmail, $sec)' + #13#10 +
    '$body = "MahilMart POS license key generated.`r`n`r`nMachine ID: $machineId`r`nIssued At: $issuedAt`r`nLicense Key: $licenseKey`r`n"' + #13#10 +
    '$msg = New-Object System.Net.Mail.MailMessage' + #13#10 +
    '$msg.From = $toEmail' + #13#10 +
    '$msg.To.Add($toEmail)' + #13#10 +
    '$msg.Subject = "MahilMart POS License Key"' + #13#10 +
    '$msg.Body = $body' + #13#10 +
    '$smtp = New-Object System.Net.Mail.SmtpClient(''smtp.gmail.com'', 587)' + #13#10 +
    '$smtp.EnableSsl = $true' + #13#10 +
    '$smtp.Credentials = $cred' + #13#10 +
    '$smtp.Timeout = 15000' + #13#10 +
    '$smtp.Send($msg)' + #13#10;

  SaveStringToFile(ScriptPath, ScriptContent, False);
  Result := Exec(
    ExpandConstant('{cmd}'),
    '/C powershell -NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) and (ResultCode = 0);
end;

procedure InitializeWizard;
begin
  LicensePath := ExpandConstant('{commonappdata}\MahilMartPOS\license.ini');
  ActivationNoticePath := ExpandConstant('{commonappdata}\MahilMartPOS\license_activation_pending.ini');
  PendingEmail := '';
  PendingMachineId := '';
  PendingIssuedAt := '';
  PendingLicenseKey := '';
  KeyEmailSent := False;

  LicenseEmailPage := CreateInputQueryPage(
    wpSelectDir,
    'License Email',
    'Send license key',
    'License email is fixed in read-only mode.' + #13#10 + 'Machine ID: ' + GetMachineId
  );
  LicenseEmailPage.Add('Email:', False);
  LicenseEmailPage.Values[0] := FixedLicenseEmail;
  LicenseEmailPage.Edits[0].ReadOnly := True;

  LicenseKeyPage := CreateInputQueryPage(
    LicenseEmailPage.ID,
    'License Validation',
    'Enter received key',
    'Enter the license key sent by email (read-only mail) for this machine.'
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
  EnteredEmail: string;
  EnteredKey: string;
  MachineId: string;
begin
  Result := True;
  if CurPageID = LicenseEmailPage.ID then
  begin
    EnteredEmail := FixedLicenseEmail;
    LicenseEmailPage.Values[0] := EnteredEmail;

    if PendingEmail <> NormalizeUpper(EnteredEmail) then
      KeyEmailSent := False;

    if not KeyEmailSent then
    begin
      PendingEmail := NormalizeUpper(EnteredEmail);
      PendingMachineId := GetMachineId;
      PendingIssuedAt := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
      PendingLicenseKey := GenerateLicenseKey(EnteredEmail, PendingMachineId, PendingIssuedAt);
      if not SendLicenseKeyEmail(PendingMachineId, PendingIssuedAt, PendingLicenseKey) then
      begin
        MsgBox('Unable to send license key email. Check internet and try again.', mbError, MB_OK);
        Result := False;
        exit;
      end;
      KeyEmailSent := True;
      MsgBox('License key sent to ' + FixedLicenseEmail + '. Enter key on next page.', mbInformation, MB_OK);
    end;
  end;
  if CurPageID = LicenseKeyPage.ID then
  begin
    EnteredKey := NormalizeUpper(LicenseKeyPage.Values[0]);
    MachineId := GetMachineId;
    if EnteredKey = '' then
    begin
      MsgBox('License key is required.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if not KeyEmailSent then
    begin
      MsgBox('License key was not sent yet. Go back and send email first.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if MachineId <> PendingMachineId then
    begin
      MsgBox('Machine changed during setup. Go back and send key email again.', mbError, MB_OK);
      Result := False;
      exit;
    end;
    if EnteredKey <> PendingLicenseKey then
    begin
      MsgBox('Invalid license key for this machine.', mbError, MB_OK);
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
    MachineId := PendingMachineId;
    if MachineId = '' then
      MachineId := GetMachineId;
    IssuedAt := PendingIssuedAt;
    if IssuedAt = '' then
      IssuedAt := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
    EnteredKey := NormalizeUpper(LicenseKeyPage.Values[0]);
    if EnteredKey = '' then
      EnteredKey := PendingLicenseKey;

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
