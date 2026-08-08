[CmdletBinding()]
param([string]$PythonPath, [switch]$SkipDependencyInstall)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$SetupDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $SetupDir
$BuildVenv = Join-Path $SetupDir ".build-venv"
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
$BuildDir = Join-Path $SetupDir "build"
$DistDir = Join-Path $SetupDir "dist"
$InstallerDir = Join-Path $BuildDir "installer"
$Installer = Join-Path $SetupDir "NetSonar-Setup-v0.5.0.exe"
$StagedInstaller = Join-Path $InstallerDir "NetSonar-Setup-v0.5.0-staging.exe"

if (-not $PythonPath) {
    $ProjectPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $ProjectPython) { $PythonPath = $ProjectPython }
    else { $PythonPath = (Get-Command python -ErrorAction Stop).Source }
}
if (-not (Test-Path -LiteralPath $BuildPython)) {
    Write-Host "Paketleme ortami olusturuluyor..."
    & $PythonPath -m venv $BuildVenv
}
if (-not $SkipDependencyInstall) {
    Write-Host "Sabitlenmis paketleme bagimliliklari kuruluyor..."
    & $BuildPython -m pip install --disable-pip-version-check --upgrade pip
    & $BuildPython -m pip install --disable-pip-version-check -r (Join-Path $SetupDir "requirements-build.txt")
}
foreach ($path in @($BuildDir, $DistDir)) {
    $resolvedSetup = [IO.Path]::GetFullPath($SetupDir)
    $resolvedPath = [IO.Path]::GetFullPath($path)
    if (-not $resolvedPath.StartsWith($resolvedSetup, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Guvenli olmayan temizleme yolu: $resolvedPath"
    }
    if (Test-Path -LiteralPath $resolvedPath) { Remove-Item -LiteralPath $resolvedPath -Recurse -Force }
}
if (Test-Path -LiteralPath $Installer) { Remove-Item -LiteralPath $Installer -Force }

Write-Host "NetSonar uygulamasi paketleniyor..."
$PyInstallerArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--workpath", $BuildDir, "--distpath", $DistDir, (Join-Path $SetupDir "NetSonar.spec"))
& $BuildPython @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller derlemesi basarisiz oldu." }

$ForbiddenFiles = Get-ChildItem -LiteralPath $DistDir -Recurse -File | Where-Object {
    $_.Extension -in @(".py", ".db", ".log") -or $_.Name -eq "settings.json"
}
if ($ForbiddenFiles) {
    $Names = ($ForbiddenFiles.FullName -join [Environment]::NewLine)
    throw ("Paketlenmemesi gereken dosyalar bulundu:" + [Environment]::NewLine + $Names)
}

New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
$NsisCandidates = @(
    (Join-Path ([Environment]::GetFolderPath("ProgramFilesX86")) "NSIS\makensis.exe"),
    (Join-Path ([Environment]::GetFolderPath("ProgramFiles")) "NSIS\makensis.exe")
)
$MakeNsis = Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
if (-not $MakeNsis) { $MakeNsis = $NsisCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1 }
if (-not $MakeNsis) { throw "NSIS bulunamadi. README.md icindeki onkosulu kurup yeniden deneyin." }

Write-Host "Tek dosyali Windows kurulum paketi olusturuluyor..."
& $MakeNsis /V2 (Join-Path $SetupDir "NetSonar.nsi")
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $StagedInstaller)) { throw "NSIS derlemesi basarisiz oldu." }
Move-Item -LiteralPath $StagedInstaller -Destination $Installer -Force
Write-Host "Kurulum paketi hazir: $Installer"
