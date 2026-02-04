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
