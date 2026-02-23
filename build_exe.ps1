param(
    [switch]$SkipPyInstaller,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

function Get-IsccPath {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidates = @(
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

if (-not $SkipPyInstaller) {
    python -m pip install --upgrade pip pyinstaller pymongo dnspython
    python -m PyInstaller --clean --noconfirm MahilMartPOS.spec
}

if ($SkipInstaller) {
    Write-Host "Installer build skipped (-SkipInstaller)."
    exit 0
}

if ($env:MM_CODESIGN_PFX -and $env:MM_CODESIGN_PASSWORD) {
    $signtoolPath = $null

    if ($env:MM_CODESIGN_TOOL_PATH) {
        if (-not (Test-Path $env:MM_CODESIGN_TOOL_PATH)) {
            throw "MM_CODESIGN_TOOL_PATH is set but file was not found: $($env:MM_CODESIGN_TOOL_PATH)"
        }
        $signtoolPath = (Resolve-Path $env:MM_CODESIGN_TOOL_PATH).Path
    }
    else {
        $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
        if (-not $signtool) {
            throw "Code signing is enabled but signtool.exe was not found in PATH. Set MM_CODESIGN_TOOL_PATH to full signtool.exe path."
        }
        $signtoolPath = $signtool.Source
    }

    $env:MM_CODESIGN_TOOL_PATH = $signtoolPath
    Write-Host "Code signing is enabled for Inno Setup output."
}
else {
    Write-Warning "Code signing is disabled. Set MM_CODESIGN_PFX and MM_CODESIGN_PASSWORD to sign the installer."
}

$isccPath = Get-IsccPath
if (-not $isccPath) {
    throw "ISCC.exe not found. Install Inno Setup 6 or add ISCC.exe to PATH."
}

& $isccPath "MahilMartPOS-Setup.iss"
Write-Host "Installer build complete: installer\\output\\MahilMartPOS-Setup.exe"
