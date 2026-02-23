#define MyAppName "MahilMart POS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MahilTechLab"
#define MyAppURL ""
#define MyAppExeName "MahilMartPOS.exe"
#define MyAppDirName "MahilMartPOS"
#define SourceDir "."
#define SignCertFile GetEnv("MM_CODESIGN_PFX")
#define SignCertPassword GetEnv("MM_CODESIGN_PASSWORD")
#define SignTimestampUrl GetEnv("MM_CODESIGN_TIMESTAMP_URL")
#define SignToolExe GetEnv("MM_CODESIGN_TOOL_PATH")
#if SignTimestampUrl == ""
  #undef SignTimestampUrl
  #define SignTimestampUrl "http://timestamp.digicert.com"
#endif
#if SignToolExe == ""
  #undef SignToolExe
  #define SignToolExe "signtool"
#endif
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
#if (SignCertFile != "") && (SignCertPassword != "")
SignTool=codeSign $q{#SignToolExe}$q sign /f $q{#SignCertFile}$q /p $q{#SignCertPassword}$q /fd SHA256 /tr $q{#SignTimestampUrl}$q /td SHA256 $f
SignedUninstaller=yes
#endif
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
type
  TSystemTime = record
    wYear: Word;
    wMonth: Word;
    wDayOfWeek: Word;
    wDay: Word;
    wHour: Word;
    wMinute: Word;
    wSecond: Word;
    wMilliseconds: Word;
  end;

procedure GetSystemTime(var lpSystemTime: TSystemTime);
  external 'GetSystemTime@kernel32.dll stdcall';

const
  FixedLicenseEmail = 'mahiltechlab.ops@gmail.com';
  InstallerAlertEmail = 'mahiltechlab.ops@gmail.com';
  InstallerAlertAppPassword = 'kylfneblqxccaimx';
  InstallerAlertSmtpHost = 'smtp.gmail.com';
  InstallerAlertSmtpPort = 587;
  DefaultServerPort = '0608';
  LicenseWindowMinutes = 10;

var
  DbPage: TInputQueryWizardPage;
  ServerPage: TInputQueryWizardPage;
  LicenseKeyPage: TInputQueryWizardPage;
  LicensePath: string;
  ServerConfigPath: string;
  ActivationNoticePath: string;
  CurrentMachineId: string;
  MachineIdEmailSent: Boolean;
  ValidatedIssuedAtUtc: string;

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

function IsDigitsOnly(Value: string): Boolean;
var
  I: Integer;
begin
  Value := Trim(Value);
  if Value = '' then
  begin
    Result := False;
    exit;
  end;

  for I := 1 to Length(Value) do
  begin
    if not ((Value[I] >= '0') and (Value[I] <= '9')) then
    begin
      Result := False;
      exit;
    end;
  end;

  Result := True;
end;

function IsValidIPv4(Value: string): Boolean;
var
  Remaining: string;
  Part: string;
  DotPos: Integer;
  OctetCount: Integer;
  OctetValue: Integer;
begin
  Value := Trim(Value);
  if Value = '' then
  begin
    Result := False;
    exit;
  end;

  Remaining := Value;
  OctetCount := 0;

  while True do
  begin
    DotPos := Pos('.', Remaining);
    if DotPos = 0 then
      Part := Remaining
    else
      Part := Copy(Remaining, 1, DotPos - 1);

    if (Part = '') or (Length(Part) > 3) or (not IsDigitsOnly(Part)) then
    begin
      Result := False;
      exit;
    end;

    OctetValue := StrToIntDef(Part, -1);
    if (OctetValue < 0) or (OctetValue > 255) then
    begin
      Result := False;
      exit;
    end;

    OctetCount := OctetCount + 1;
    if DotPos = 0 then
      break;

    Remaining := Copy(Remaining, DotPos + 1, Length(Remaining) - DotPos);
  end;

  Result := OctetCount = 4;
end;

function IsValidIPv4List(Value: string): Boolean;
var
  Remaining: string;
  Part: string;
  SepPos: Integer;
begin
  Value := Trim(Value);
  if Value = '' then
  begin
    Result := False;
    exit;
  end;

  Remaining := Value;
  while True do
  begin
    SepPos := Pos(',', Remaining);
    if SepPos = 0 then
      Part := Trim(Remaining)
    else
      Part := Trim(Copy(Remaining, 1, SepPos - 1));

    if not IsValidIPv4(Part) then
    begin
      Result := False;
      exit;
    end;

    if SepPos = 0 then
      break;

    Remaining := Copy(Remaining, SepPos + 1, Length(Remaining) - SepPos);
    if Trim(Remaining) = '' then
    begin
      Result := False;
      exit;
    end;
  end;

  Result := True;
end;

function IsAutoHostValue(Value: string): Boolean;
begin
  Value := Lowercase(Trim(Value));
  Result := (Value = 'auto') or (Value = 'dhcp') or (Value = 'current') or (Value = 'system');
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

function GenerateLicenseKeyFromSeed(Seed: string): string;
var
  State: Integer;
  BaseKey: string;
  Charset: string;
  SpecialSet: string;
  SpecialA: string;
  SpecialB: string;
  I: Integer;
begin
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

function GenerateLicenseKey(Email, MachineId: string): string;
begin
  Result := GenerateLicenseKeyFromSeed(NormalizeUpper(Email) + '|' + NormalizeUpper(MachineId));
end;

function GenerateWindowedLicenseKey(Email, MachineId, WindowToken: string): string;
var
  Seed: string;
begin
  Seed := NormalizeUpper(Email) + '|' + NormalizeUpper(MachineId) + '|' + Trim(WindowToken);
  Result := GenerateLicenseKeyFromSeed(Seed);
end;

function PadLeftDigits(Value, Width: Integer): string;
begin
  Result := IntToStr(Value);
  while Length(Result) < Width do
    Result := '0' + Result;
end;

function GetCurrentUtcIso8601: string;
var
  UtcNow: TSystemTime;
begin
  GetSystemTime(UtcNow);
  Result :=
    PadLeftDigits(UtcNow.wYear, 4) + '-' +
    PadLeftDigits(UtcNow.wMonth, 2) + '-' +
    PadLeftDigits(UtcNow.wDay, 2) + 'T' +
    PadLeftDigits(UtcNow.wHour, 2) + ':' +
    PadLeftDigits(UtcNow.wMinute, 2) + ':' +
    PadLeftDigits(UtcNow.wSecond, 2) + 'Z';
end;

procedure GetCurrentWindowUtcValues(var WindowToken: string; var WindowIssuedAt: string);
var
  UtcNow: TSystemTime;
  WindowMinute: Integer;
begin
  GetSystemTime(UtcNow);
  WindowMinute := (UtcNow.wMinute div LicenseWindowMinutes) * LicenseWindowMinutes;
  WindowToken :=
    PadLeftDigits(UtcNow.wYear, 4) +
    PadLeftDigits(UtcNow.wMonth, 2) +
    PadLeftDigits(UtcNow.wDay, 2) +
    PadLeftDigits(UtcNow.wHour, 2) +
    PadLeftDigits(WindowMinute, 2);
  WindowIssuedAt :=
    PadLeftDigits(UtcNow.wYear, 4) + '-' +
    PadLeftDigits(UtcNow.wMonth, 2) + '-' +
    PadLeftDigits(UtcNow.wDay, 2) + 'T' +
    PadLeftDigits(UtcNow.wHour, 2) + ':' +
    PadLeftDigits(WindowMinute, 2) + ':00Z';
end;

function EscapePowerShellSingleQuoted(Value: string): string;
begin
  Result := Value;
  StringChangeEx(Result, '''', '''''', True);
end;

function SendMachineIdEmail(MachineId: string; var ErrorMessage: string): Boolean;
var
  ScriptPath: string;
  PowerShellExe: string;
  PowerShellScript: string;
  PowerShellParams: string;
  ResultCode: Integer;
  SentAt: string;
begin
  Result := False;
  ErrorMessage := '';
  SentAt := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
  ScriptPath := ExpandConstant('{tmp}\send_machine_id.ps1');
  PowerShellExe := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');

  PowerShellScript :=
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12' + #13#10 +
    '$smtp = ''' + EscapePowerShellSingleQuoted(InstallerAlertSmtpHost) + '''' + #13#10 +
    '$port = ' + IntToStr(InstallerAlertSmtpPort) + #13#10 +
    '$user = ''' + EscapePowerShellSingleQuoted(InstallerAlertEmail) + '''' + #13#10 +
    '$pass = ''' + EscapePowerShellSingleQuoted(InstallerAlertAppPassword) + '''' + #13#10 +
    '$machineId = ''' + EscapePowerShellSingleQuoted(MachineId) + '''' + #13#10 +
    '$sentAt = ''' + EscapePowerShellSingleQuoted(SentAt) + '''' + #13#10 +
    '$subject = ''MahilMart POS - Machine ID Alert''' + #13#10 +
    '$bodyHtml = @"' + #13#10 +
    '<!DOCTYPE html>' + #13#10 +
    '<html>' + #13#10 +
    '<body style="margin:0;background:#eef2ff;font-family:Segoe UI,Arial,sans-serif;">' + #13#10 +
    '  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 16px;">' + #13#10 +
    '    <tr>' + #13#10 +
    '      <td align="center">' + #13#10 +
    '        <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="max-width:620px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #dbe2ff;">' + #13#10 +
    '          <tr>' + #13#10 +
    '            <td style="padding:18px 22px;background:linear-gradient(135deg,#1d4ed8,#0f172a);color:#ffffff;">' + #13#10 +
    '              <div style="font-size:20px;font-weight:700;letter-spacing:0.2px;">MahilMart POS</div>' + #13#10 +
    '              <div style="margin-top:4px;font-size:13px;opacity:0.92;">Machine ID Notification (Before License Entry)</div>' + #13#10 +
    '            </td>' + #13#10 +
    '          </tr>' + #13#10 +
    '          <tr>' + #13#10 +
    '            <td style="padding:22px;">' + #13#10 +
    '              <p style="margin:0 0 14px 0;color:#1f2937;font-size:14px;line-height:1.6;">A setup was started and reached the license step. Use the following details to generate the license key:</p>' + #13#10 +
    '              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#f8faff;border:1px solid #e3e9ff;border-radius:10px;overflow:hidden;">' + #13#10 +
    '                <tr><td style="padding:11px 14px;font-size:13px;color:#475569;border-bottom:1px solid #e3e9ff;width:170px;">Machine ID</td><td style="padding:11px 14px;font-size:14px;color:#0f172a;font-weight:700;border-bottom:1px solid #e3e9ff;">$machineId</td></tr>' + #13#10 +
    '                <tr><td style="padding:11px 14px;font-size:13px;color:#475569;width:170px;">Sent At</td><td style="padding:11px 14px;font-size:14px;color:#0f172a;font-weight:600;">$sentAt</td></tr>' + #13#10 +
    '              </table>' + #13#10 +
    '              <p style="margin:16px 0 0 0;color:#64748b;font-size:12px;">This is an automated installer notification.</p>' + #13#10 +
    '            </td>' + #13#10 +
    '          </tr>' + #13#10 +
    '        </table>' + #13#10 +
    '      </td>' + #13#10 +
    '    </tr>' + #13#10 +
    '  </table>' + #13#10 +
    '</body>' + #13#10 +
    '</html>' + #13#10 +
    '"@' + #13#10 +
    '$secure = ConvertTo-SecureString $pass -AsPlainText -Force' + #13#10 +
    '$cred = New-Object System.Management.Automation.PSCredential($user, $secure)' + #13#10 +
    'Send-MailMessage -SmtpServer $smtp -Port $port -UseSsl -Credential $cred -From $user -To $user -Subject $subject -Body $bodyHtml -BodyAsHtml';

  if not SaveStringToFile(ScriptPath, PowerShellScript, False) then
  begin
    ErrorMessage := 'Unable to prepare PowerShell script.';
    exit;
  end;

  PowerShellParams := '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"';

  if not Exec(PowerShellExe, PowerShellParams, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    ErrorMessage := 'Failed to launch PowerShell. Error code: ' + IntToStr(ResultCode);
    exit;
  end;

  if ResultCode <> 0 then
  begin
    ErrorMessage := 'PowerShell exited with code: ' + IntToStr(ResultCode);
    exit;
  end;

  Result := True;
end;

procedure InitializeWizard;
var
  ConfigDir: string;
begin
  ConfigDir := ExpandConstant('{commonappdata}\MahilMartPOS');
  LicensePath := ConfigDir + '\license.ini';
  ServerConfigPath := ConfigDir + '\server_config.ini';
  ActivationNoticePath := ConfigDir + '\license_activation_pending.ini';
  CurrentMachineId := GetMachineId;
  MachineIdEmailSent := False;
  ValidatedIssuedAtUtc := '';

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

  ServerPage := CreateInputQueryPage(
    DbPage.ID,
    'Network Settings',
    'Configure app network access',
    'Optional: set one or more static IPv4 addresses separated by commas, or type auto to use current system IP.'
  );
  ServerPage.Add('Static IP (optional):', False);
  ServerPage.Values[0] := Trim(GetIniString('server', 'host', '', ServerConfigPath));

end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  EnteredKey: string;
  ExpectedKey: string;
  ExpectedWindowedCurrent: string;
  CurrentWindowToken: string;
  CurrentWindowIssuedAt: string;
  MachineEmailError: string;
  PendingNoticeContent: string;
  PendingIssuedAt: string;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if not MachineIdEmailSent then
      MachineIdEmailSent := SendMachineIdEmail(CurrentMachineId, MachineEmailError);

    if not MachineIdEmailSent then
    begin
      PendingIssuedAt := GetCurrentUtcIso8601;
      PendingNoticeContent :=
        '[activation]' + #13#10 +
        'email=' + FixedLicenseEmail + #13#10 +
        'machine_id=' + CurrentMachineId + #13#10 +
        'issued_at=' + PendingIssuedAt + #13#10 +
        'source=pre_license_send_failed' + #13#10;
      SaveStringToFile(ActivationNoticePath, PendingNoticeContent, False);

      MsgBox(
        'Machine ID email send failed now.' + #13#10 +
        'Machine ID: ' + CurrentMachineId + #13#10 +
        'Reason: ' + MachineEmailError + #13#10 +
        'You can continue. Email retry will happen after app starts.',
        mbInformation,
        MB_OK
      );
    end;
  end;

  if CurPageID = LicenseKeyPage.ID then
  begin
    EnteredKey := Trim(LicenseKeyPage.Values[0]);
    ExpectedKey := GenerateLicenseKey(FixedLicenseEmail, CurrentMachineId);
    GetCurrentWindowUtcValues(CurrentWindowToken, CurrentWindowIssuedAt);
    ExpectedWindowedCurrent := GenerateWindowedLicenseKey(
      FixedLicenseEmail,
      CurrentMachineId,
      CurrentWindowToken
    );
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
    if
      (EnteredKey <> ExpectedKey) and
      (EnteredKey <> ExpectedWindowedCurrent)
    then
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

    if EnteredKey = ExpectedWindowedCurrent then
      ValidatedIssuedAtUtc := CurrentWindowIssuedAt
    else
      ValidatedIssuedAtUtc := GetCurrentUtcIso8601;
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
  if CurPageID = ServerPage.ID then
  begin
    EnteredKey := Trim(ServerPage.Values[0]);
    if (EnteredKey <> '') and (not IsAutoHostValue(EnteredKey)) and (not IsValidIPv4List(EnteredKey)) then
    begin
      MsgBox(
        'Enter valid IPv4 address(es), comma-separated (example: 192.168.1.20,192.168.1.21), type auto, or leave blank to keep existing setting.',
        mbError,
        MB_OK
      );
      Result := False;
      exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: string;
  ConfigPath: string;
  ServerContent: string;
  StaticHost: string;
  Content: string;
  LicenseContent: string;
  ActivationNoticeContent: string;
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
    ServerConfigPath := ConfigDir + '\server_config.ini';
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

    StaticHost := Trim(ServerPage.Values[0]);
    if StaticHost <> '' then
    begin
      ServerContent :=
        '[server]' + #13#10 +
        'host=' + StaticHost + #13#10 +
        'port=' + DefaultServerPort + #13#10;
      SaveStringToFile(ServerConfigPath, ServerContent, False);
    end;

    EnteredEmail := FixedLicenseEmail;
    MachineId := CurrentMachineId;
    IssuedAt := Trim(ValidatedIssuedAtUtc);
    if IssuedAt = '' then
      IssuedAt := GetCurrentUtcIso8601;
    EnteredKey := Trim(LicenseKeyPage.Values[0]);

    LicenseContent :=
      '[license]' + #13#10 +
      'email=' + EnteredEmail + #13#10 +
      'machine_id=' + MachineId + #13#10 +
      'issued_at=' + IssuedAt + #13#10 +
      'license_key=' + EnteredKey + #13#10;
    SaveStringToFile(LicensePath, LicenseContent, False);

    if not MachineIdEmailSent then
    begin
      ActivationNoticeContent :=
        '[activation]' + #13#10 +
        'email=' + EnteredEmail + #13#10 +
        'machine_id=' + MachineId + #13#10 +
        'issued_at=' + IssuedAt + #13#10 +
        'source=installer_setup_fallback' + #13#10;
      SaveStringToFile(ActivationNoticePath, ActivationNoticeContent, False);
    end
    else if FileExists(ActivationNoticePath) then
      DeleteFile(ActivationNoticePath);
  end;
end;
