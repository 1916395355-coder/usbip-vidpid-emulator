@echo off
cd /d "%~dp0"
set PY=%LocalAppData%\Programs\Python\Python314\python.exe
set USBIP=E:\USBip\usbip.exe

echo [1/4] start spoof 3837:3024 on :3240 ...
start "spoof-3837-3024" /min "" "%PY%" -u emulate_3837_3024.py --port 3240
timeout /t 2 /nobreak >nul

echo [2/4] start spoof 3837:1018 on :3241 ...
start "spoof-3837-1018" /min "" "%PY%" -u emulate_3837_1018.py --port 3241
timeout /t 2 /nobreak >nul

echo [3/4] list / attach 3024 ...
"%USBIP%" list -r 127.0.0.1
"%USBIP%" attach -r 127.0.0.1 -b 1-1

echo [4/4] list / attach 1018 ...
"%USBIP%" list -r 127.0.0.1:3241
"%USBIP%" attach -r 127.0.0.1:3241 -b 1-1

"%USBIP%" port
echo.
echo Check Device Manager:
echo   USB\VID_3837^&PID_3024
echo   USB\VID_3837^&PID_1018
pause
