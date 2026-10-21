[CmdletBinding()]
param([string]$PythonPath, [switch]$SkipDependencyInstall, [switch]$SkipInstaller)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$PackagingDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $PackagingDir
$ConfigText = Get-Content -LiteralPath (Join-Path $ProjectRoot "config.py") -Raw
$VersionMatch = [regex]::Match($ConfigText, '(?m)^APP_VERSION\s*=\s*"v(?<version>\d+\.\d+\.\d+)"')
if (-not $VersionMatch.Success) { throw "config.py icinde APP_VERSION bulunamadi." }
$Version = $VersionMatch.Groups["version"].Value
$VersionedStem = "NetSonar-v$Version"
$BuildVenv = Join-Path $PackagingDir ".build-venv"
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
$BuildDir = Join-Path $PackagingDir "build"
$AppDistDir = Join-Path $PackagingDir "app-dist"
$ReleaseDir = Join-Path $ProjectRoot "dist"
$Installer = Join-Path $ReleaseDir "$VersionedStem-Setup.exe"
$Makensis = "C:\Program Files (x86)\NSIS\makensis.exe"

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
    & $BuildPython -m pip install --disable-pip-version-check -r (Join-Path $PackagingDir "requirements-build.txt")
}
foreach ($path in @($BuildDir, $AppDistDir)) {
    $resolvedPackaging = [IO.Path]::GetFullPath($PackagingDir)
    $resolvedPath = [IO.Path]::GetFullPath($path)
    if (-not $resolvedPath.StartsWith($resolvedPackaging, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Guvenli olmayan temizleme yolu: $resolvedPath"
    }
    if (Test-Path -LiteralPath $resolvedPath) { Remove-Item -LiteralPath $resolvedPath -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Get-ChildItem -LiteralPath $ReleaseDir -File | Where-Object {
    $_.Name -match '^NetSonar-v\d+\.\d+\.\d+(-Setup)?\.(exe|bat)$'
} | Remove-Item -Force

Write-Host "Klasorlu (onedir) surum paketleniyor..."
$PyInstallerArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--workpath", $BuildDir, "--distpath", $AppDistDir, (Join-Path $PackagingDir "NetSonar.spec"))
& $BuildPython @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller derlemesi basarisiz oldu." }

$BuiltDir = Join-Path $AppDistDir "NetSonar"
$BuiltExe = Join-Path $BuiltDir "NetSonar.exe"
if (-not (Test-Path -LiteralPath $BuiltExe)) { throw "EXE uretilmedi: $BuiltExe" }

$ForbiddenFiles = Get-ChildItem -LiteralPath $AppDistDir -Recurse -File | Where-Object {
    $_.Extension -in @(".py", ".db", ".log") -or $_.Name -eq "settings.json"
}
if ($ForbiddenFiles) {
    $Names = ($ForbiddenFiles.FullName -join [Environment]::NewLine)
    throw ("Paketlenmemesi gereken dosyalar bulundu:" + [Environment]::NewLine + $Names)
}

if (-not $SkipInstaller) {
    if (-not (Test-Path -LiteralPath $Makensis)) {
        throw "NSIS bulunamadi: $Makensis"
    }
    Write-Host "Kurulumcu paketleniyor..."
    & $Makensis "/DAPP_VERSION=$Version" (Join-Path $PackagingDir "NetSonar.nsi")
    if ($LASTEXITCODE -ne 0) { throw "NSIS kurulumcu derlemesi basarisiz oldu." }
    if (-not (Test-Path -LiteralPath $Installer)) { throw "Kurulumcu uretilmedi: $Installer" }
    $InstallerHash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLower()
    Write-Host "Kurulumcu hazir: $Installer"
    Write-Host "SHA256: $InstallerHash"
}

foreach ($temporaryPath in @($BuildDir, $AppDistDir)) {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Recurse -Force
    }
}
Write-Host "Klasorlu surum hazir: $BuiltExe"
