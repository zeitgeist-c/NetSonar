@echo off
setlocal
title NetSonar - AI Ag Izleyici

:: Her zaman bu BAT dosyasinin bulundugu guncel proje klasorunden calis.
cd /d "%~dp0" || exit /b 1

:: Paket yakalama ve guvenlik duvari islemleri icin yonetici yetkisi gerekir.
net session >nul 2>&1
if errorlevel 1 (
    echo UYARI: Yonetici yetkisi gerekli. Yeniden baslatiliyor...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
set "ENTRYPOINT=%~dp0main.py"
set "ERROR_LOG=%~dp0netsonar_data\logs\netsonar_err.log"

if not exist "%PYTHON%" (
    echo HATA: Projeye ait .venv bulunamadi.
    echo Once python -m venv .venv komutunu calistirin.
    pause
    exit /b 1
)
if not exist "%PYTHONW%" (
    echo HATA: %PYTHONW% bulunamadi.
    pause
    exit /b 1
)
if not exist "%ENTRYPOINT%" (
    echo HATA: Guncel main.py bulunamadi: %ENTRYPOINT%
    pause
    exit /b 1
)

:: Bu klasorden calisan eski NetSonar'i kapat. Boylece guncellemeden sonra
:: eski surec ve tek-ornek kilidi guncel kodun acilmasini engellemez.
powershell -NoProfile -Command "$entry=[IO.Path]::GetFullPath('%ENTRYPOINT%'); Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -and $_.CommandLine.Contains($entry) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

if not exist "C:\Windows\System32\Npcap\wpcap.dll" (
    echo UYARI: Npcap bulunamadi. Scapy calismayabilir.
    echo Lutfen https://npcap.com adresinden Npcap yukleyin.
    echo.
)

if not exist "%~dp0netsonar_data\logs" mkdir "%~dp0netsonar_data\logs"
echo NetSonar guncel proje koduyla baslatiliyor...
:: -B calisma sirasinda yeni .pyc onbellegi yazilmasini engeller.
start "" /b "%PYTHONW%" -B "%ENTRYPOINT%" 2>> "%ERROR_LOG%"
endlocal
exit /b 0
