param(
    [switch]$Preview,
    [switch]$InstallLibreOffice
)

$ErrorActionPreference = "Stop"

$RunningOnWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
if (-not $RunningOnWindows) {
    throw "setup_windows.ps1 must be run from Windows PowerShell or PowerShell on Windows."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

function Invoke-Python {
    param([string[]]$Arguments)

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 @Arguments
        return
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source @Arguments
        return
    }

    throw "Python was not found. Install Python 3 and enable 'Add python.exe to PATH'."
}

Write-Host "Installing required img2pptx Python packages..."
Invoke-Python -Arguments @("-m", "pip", "install", "--upgrade", "python-pptx", "pillow", "numpy")

if ($Preview) {
    Write-Host "Installing Windows preview helpers..."
    Invoke-Python -Arguments @("-m", "pip", "install", "--upgrade", "pywin32", "PyMuPDF")
}

if ($InstallLibreOffice) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "winget was not found. Install LibreOffice manually from https://www.libreoffice.org/download/download/."
    }
    Write-Host "Installing LibreOffice with winget..."
    & $winget.Source install --id TheDocumentFoundation.LibreOffice --exact --accept-source-agreements --accept-package-agreements
}

Write-Host "Running img2pptx environment check..."
Invoke-Python -Arguments @("scripts/doctor.py", "--out", "scratch/doctor_report.json")
