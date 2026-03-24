@echo off
:: AgTara — Baslat (.venv kullanir)
title AgTara - AI Ag Izleyici

:: .venv Python'u kullan
set PYTHON=.venv\Scripts\python.exe
if not exist %PYTHON% (
    echo HATA: .venv bulunamadi. once "python -m venv .venv" komutu calistirin.
    pause
    exit /b 1
)

:: Npcap kontrolu
if not exist "C:\Windows\System32\Npcap\pcap.dll" (
    echo UYARI: Npcap bulunamadi. Scapy calismayabilir.
    echo Lutfen https://npcap.com adresinden Npcap yukleyin.
    echo.
)

echo AgTara baslatiliyor...
%PYTHON% main.py
pause
