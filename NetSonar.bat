@echo off
:: NetSonar — Baslat (.venv kullanir)
title NetSonar - AI Ag Izleyici

:: Admin kontrolü
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo UYARI: Admin yetkisi gerekli! Yeniden baslatiliyor...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && %~nx0' -Verb RunAs"
    exit /b
)

:: .venv Python'u kullan
set PYTHON=.venv\Scripts\python.exe
if not exist %PYTHON% (
    echo HATA: .venv bulunamadi. once "python -m venv .venv" komutu calistirin.
    pause
    exit /b 1
)

:: Npcap kontrolu
if not exist "C:\Windows\System32\Npcap\wpcap.dll" (
    echo UYARI: Npcap bulunamadi. Scapy calismayabilir.
    echo Lutfen https://npcap.com adresinden Npcap yukleyin.
    echo.
)

echo NetSonar baslatiliyor...
if not exist "netsonar_data\logs" mkdir "netsonar_data\logs"
start /b .venv\Scripts\pythonw.exe main.py 2>> netsonar_data\logs\netsonar_err.log
exit
