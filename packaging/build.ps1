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
$InstallerDir = Join-Path $BuildDir "installer"
$Installer = Join-Path $ReleaseDir "$VersionedStem.exe"
$Launcher = Join-Path $ReleaseDir "$VersionedStem.bat"
$StagedInstaller = Join-Path $InstallerDir "$VersionedStem-staging.exe"

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

Write-Host "NetSonar uygulamasi paketleniyor..."
$PyInstallerArgs = @("-m", "PyInstaller", "--noconfirm", "--clean", "--workpath", $BuildDir, "--distpath", $AppDistDir, (Join-Path $PackagingDir "NetSonar.spec"))
& $BuildPython @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller derlemesi basarisiz oldu." }

$ForbiddenFiles = Get-ChildItem -LiteralPath $AppDistDir -Recurse -File | Where-Object {
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
& $MakeNsis /V2 "/DAPP_VERSION=$Version" (Join-Path $PackagingDir "NetSonar.nsi")
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $StagedInstaller)) { throw "NSIS derlemesi basarisiz oldu." }
Move-Item -LiteralPath $StagedInstaller -Destination $Installer -Force
$LauncherText = "@echo off`r`nsetlocal`r`nset `"PROJECT_LAUNCHER=%~dp0..\NetSonar.bat`"`r`nif not exist `"%PROJECT_LAUNCHER%`" (`r`n    echo HATA: Proje baslaticisi bulunamadi: %PROJECT_LAUNCHER%`r`n    echo Bu BAT dosyasi kurulum EXE'sini degil, kaynak projeyi calistirir.`r`n    pause`r`n    exit /b 1`r`n)`r`ncall `"%PROJECT_LAUNCHER%`" %*`r`nexit /b %errorlevel%`r`n"
[IO.File]::WriteAllText($Launcher, $LauncherText, [Text.UTF8Encoding]::new($false))
foreach ($temporaryPath in @($BuildDir, $AppDistDir)) {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Recurse -Force
    }
}
Write-Host "Kurulum paketi hazir: $Installer"
Write-Host "Kaynak proje baslaticisi hazir: $Launcher"
