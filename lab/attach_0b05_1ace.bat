@echo off
cd /d "%~dp0"
set PY=%LocalAppData%\Programs\Python\Python314\python.exe
set USBIP=E:\USBip\usbip.exe

echo [1/3] start spoof 0B05:1ACE (ROG OMNI RECEIVER) on :3240 ...
start "spoof-0b05-1ace" /min "" "%PY%" -u emulate_0b05_1ace.py --port 3240
timeout /t 2 /nobreak >nul

echo [2/3] list ...
"%USBIP%" list -r 127.0.0.1

echo [3/3] attach ...
"%USBIP%" attach -r 127.0.0.1 -b 1-1

"%USBIP%" port
echo.
echo Check Device Manager / USBip GUI:
echo   USB\VID_0B05^&PID_1ACE  ROG OMNI RECEIVER
pause
