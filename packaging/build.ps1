[CmdletBinding()]
param([string]$PythonPath, [switch]$SkipDependencyInstall)

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
$PortableExe = Join-Path $ReleaseDir "$VersionedStem.exe"
$Launcher = Join-Path $ReleaseDir "$VersionedStem.bat"

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
    $_.Name -match '^NetSonar-v\d+\.\d+\.\d+\.(exe|bat)$'
} | Remove-Item -Force

Write-Host "Tek dosyali (onefile) portable surum paketleniyor..."
$PyInstallerArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--workpath", $BuildDir, "--distpath", $AppDistDir, (Join-Path $PackagingDir "NetSonar.spec"))
& $BuildPython @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller derlemesi basarisiz oldu." }

$BuiltExe = Join-Path $AppDistDir "$VersionedStem.exe"
if (-not (Test-Path -LiteralPath $BuiltExe)) { throw "onefile EXE uretilmedi: $BuiltExe" }

$ForbiddenFiles = Get-ChildItem -LiteralPath $AppDistDir -Recurse -File | Where-Object {
    $_.Extension -in @(".py", ".db", ".log") -or $_.Name -eq "settings.json"
}
if ($ForbiddenFiles) {
    $Names = ($ForbiddenFiles.FullName -join [Environment]::NewLine)
    throw ("Paketlenmemesi gereken dosyalar bulundu:" + [Environment]::NewLine + $Names)
}

Move-Item -LiteralPath $BuiltExe -Destination $PortableExe -Force

# Eslesen BAT baslatici: update.py'deki yaz_launcher ile ayni icerik, tek kaynaktan.
# Yollar argv ile gonderilir; string'in icine gommek Windows ters bolu yuzunden bozulur.
& $BuildPython -c "import sys; sys.path.insert(0, sys.argv[1]); import update; update.write_launcher(__import__('pathlib').Path(sys.argv[2]))" $ProjectRoot $PortableExe
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Launcher)) { throw "Baslatici BAT uretilmedi." }

foreach ($temporaryPath in @($BuildDir, $AppDistDir)) {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Recurse -Force
    }
}
Write-Host "Portable surum hazir: $PortableExe"
Write-Host "Baslatici hazir: $Launcher"
