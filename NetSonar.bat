@echo off
setlocal
title NetSonar - AI Network Monitor

:: Always run from the current project folder this BAT file lives in.
cd /d "%~dp0" || exit /b 1

:: Packet capture and firewall operations require administrator rights.
net session >nul 2>&1
if errorlevel 1 (
    echo WARNING: Administrator rights required. Restarting elevated...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
set "ENTRYPOINT=%~dp0main.py"
set "ERROR_LOG=%~dp0netsonar_data\logs\netsonar_err.log"

if not exist "%PYTHON%" (
    echo ERROR: Project .venv was not found.
    echo Run "python -m venv .venv" first.
    pause
    exit /b 1
)
if not exist "%PYTHONW%" (
    echo ERROR: %PYTHONW% was not found.
    pause
    exit /b 1
)
if not exist "%ENTRYPOINT%" (
    echo ERROR: Current main.py was not found: %ENTRYPOINT%
    pause
    exit /b 1
)

:: Stop an older NetSonar running from this folder, so that after an update the
:: stale process and its single-instance lock cannot block the current code.
powershell -NoProfile -Command "$entry=[IO.Path]::GetFullPath('%ENTRYPOINT%'); Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and $_.CommandLine -and $_.CommandLine.Contains($entry) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

if not exist "%SystemRoot%\System32\Npcap\wpcap.dll" (
    echo WARNING: Npcap was not found. Scapy may not work.
    echo Install Npcap from https://npcap.com
    echo.
)

if not exist "%~dp0netsonar_data\logs" mkdir "%~dp0netsonar_data\logs"
echo Starting NetSonar from the current project source...
:: -B stops new .pyc cache files from being written at runtime.
start "" /b "%PYTHONW%" -B "%ENTRYPOINT%" 2>> "%ERROR_LOG%"
endlocal
exit /b 0
