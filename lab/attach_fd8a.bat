@echo off
cd /d "%~dp0"
echo [1/3] start spoof 09DA:FD8A ...
start "spoof-09DA-FD8A" /min "" "%LocalAppData%\Programs\Python\Python314\python.exe" -u emulate_09da_fd8a.py
timeout /t 3 /nobreak >nul
echo [2/3] list remote ...
"E:\USBip\usbip.exe" list -r 127.0.0.1
echo [3/3] attach 1-1 ...
"E:\USBip\usbip.exe" attach -r 127.0.0.1 -b 1-1
"E:\USBip\usbip.exe" port
echo.
echo Check Device Manager for USB\VID_09DA^&PID_FD8A
pause
