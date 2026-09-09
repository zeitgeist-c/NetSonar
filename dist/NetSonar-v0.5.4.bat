@echo off
setlocal
set "PROJECT_LAUNCHER=%~dp0..\NetSonar.bat"
if not exist "%PROJECT_LAUNCHER%" (
    echo HATA: Proje baslaticisi bulunamadi: %PROJECT_LAUNCHER%
    echo Bu BAT dosyasi kurulum EXE'sini degil, kaynak projeyi calistirir.
    pause
    exit /b 1
)
call "%PROJECT_LAUNCHER%" %*
exit /b %errorlevel%
