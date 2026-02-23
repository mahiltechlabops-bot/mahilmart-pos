# mahilmart-pos
MahilMart POS desktop build and installer project.

## Build EXE + Installer
Run from project root:

```powershell
.\build_exe.ps1
```

Output installer:

`installer\output\MahilMartPOS-Setup.exe`

## Enable code signing (recommended)
Set environment variables before build:

```powershell
$env:MM_CODESIGN_PFX="C:\certs\mahiltechlab.pfx"
$env:MM_CODESIGN_PASSWORD="your-pfx-password"
$env:MM_CODESIGN_TIMESTAMP_URL="http://timestamp.digicert.com"
$env:MM_CODESIGN_TOOL_PATH="C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
.\build_exe.ps1
```

If `MM_CODESIGN_PFX` and `MM_CODESIGN_PASSWORD` are set, Inno Setup will sign:
- `MahilMartPOS-Setup.exe`
- installer uninstaller executable

## Optional flags
- `.\build_exe.ps1 -SkipPyInstaller` (only rebuild installer)
- `.\build_exe.ps1 -SkipInstaller` (only rebuild EXE)
