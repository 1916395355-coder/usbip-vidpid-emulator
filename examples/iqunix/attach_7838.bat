@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=%LocalAppData%\Programs\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"

if defined USBIP_EXE (
  set "USBIP=%USBIP_EXE%"
) else if exist "E:\USBip\usbip.exe" (
  set "USBIP=E:\USBip\usbip.exe"
) else (
  set "USBIP=usbip.exe"
)

start "spoof-3869-7838" /min "" "%PY%" -u emulate_iqunix_7838.py
timeout /t 2 /nobreak >nul
"%USBIP%" list -r 127.0.0.1
"%USBIP%" attach -r 127.0.0.1 -b 1-1
"%USBIP%" port
pause
