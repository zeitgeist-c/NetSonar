@echo off
setlocal
cd /d "%~dp0"
rem Tek seferde tek acilis: ikinci tik ayni exe'yi bastan baslatmasin.
if "%~1"=="" tasklist /FI "IMAGENAME eq NetSonar-v0.5.8.exe" 2>nul | findstr /I "NetSonar-v0.5.8.exe" >nul && exit /b 0
start "NetSonar 0.5.8" "%~dp0NetSonar-v0.5.8.exe" %*
