@echo off
rem Windows: cift tiklayarak calistirin. Bu dosyanin ustune dosya/klasor da surukleyebilirsiniz.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul && (py -3 qr_paylas.py %*) || (python qr_paylas.py %*)
if errorlevel 9009 echo Python bulunamadi. https://www.python.org/downloads/ adresinden kurun ("Add python.exe to PATH" kutusunu isaretleyin).
pause
