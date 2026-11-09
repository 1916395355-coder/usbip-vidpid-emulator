@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PY=%LocalAppData%\Programs\Python\Python314\python.exe
if not exist "%PY%" set PY=python
set USBIP=E:\USBip\usbip.exe

echo === spoof 缺口 Top: 2F4C + 09DA 血手系 ===
echo 需要管理员权限跑 usbip attach
echo.

REM 端口 3250 起
start "spoof-2F4C-1000" /min "" "%PY%" -u emulate_vidpid.py --vid 2F4C --pid 1000 --port 3250 --manufacturer Generic --product Composite_2F4C_1000
timeout /t 1 /nobreak >nul
start "spoof-09DA-FC40" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FC40 --port 3251 --product A4Tech_FC40
timeout /t 1 /nobreak >nul
start "spoof-09DA-FA46" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FA46 --port 3252 --product A4Tech_FA46
timeout /t 1 /nobreak >nul
start "spoof-09DA-FA45" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FA45 --port 3253 --product A4Tech_FA45
timeout /t 1 /nobreak >nul
start "spoof-09DA-FAB8" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FAB8 --port 3254 --product A4Tech_FAB8
timeout /t 1 /nobreak >nul
start "spoof-09DA-FA44" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FA44 --port 3255 --product Bloody_B930_FA44
timeout /t 1 /nobreak >nul
start "spoof-09DA-FA9A" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FA9A --port 3256 --product A4Tech_FA9A
timeout /t 1 /nobreak >nul
start "spoof-09DA-FC7C" /min "" "%PY%" -u emulate_vidpid.py --vid 09DA --pid FC7C --port 3257 --product A4Tech_FC7C
timeout /t 2 /nobreak >nul

echo.
echo === attach（全局 -t 指定端口，不要写 host:port）===
for %%P in (3250 3251 3252 3253 3254 3255 3256 3257) do (
  echo --- port %%P ---
  "%USBIP%" -t %%P list -r 127.0.0.1
  "%USBIP%" -t %%P attach -r 127.0.0.1 -b 1-1
  echo.
)

"%USBIP%" port
echo.
echo 设备管理器应出现:
echo   USB\VID_2F4C^&PID_1000
echo   USB\VID_09DA^&PID_FC40 / FA46 / FA45 / FAB8 / FA44 / FA9A / FC7C
echo 再开血手驱动看是否识别。
pause
