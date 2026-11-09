$ErrorActionPreference = "Continue"
$root = "d:\开发项目\usbip-vidpid-spoof"
$log = Join-Path $root "_elev_attach_09da_gap.log"
$py = "$env:LocalAppData\Programs\Python\Python314\python.exe"
$usbip = "E:\USBip\usbip.exe"
function L($m) { "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }

Remove-Item $log -Force -ErrorAction SilentlyContinue
L "begin"

# detach any imported ports
1..16 | ForEach-Object {
  & $usbip detach -p $_ 2>&1 | ForEach-Object { L $_ }
}

# kill old spoof listeners on 3250-3257 (+ leftover 3240)
3250..3257 + 3240 | ForEach-Object {
  Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue | ForEach-Object {
    L "kill pid $($_.OwningProcess) port $($_.LocalPort)"
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep 1

$devs = @(
  @{vid='2F4C'; pid='1000'; port=3250; mfr='Generic'; prod='Composite 2F4C:1000'}
  @{vid='09DA'; pid='FC40'; port=3251; mfr='A4TECH';  prod='A4Tech FC40'}
  @{vid='09DA'; pid='FA46'; port=3252; mfr='A4TECH';  prod='A4Tech FA46'}
  @{vid='09DA'; pid='FA45'; port=3253; mfr='A4TECH';  prod='A4Tech FA45'}
  @{vid='09DA'; pid='FAB8'; port=3254; mfr='A4TECH';  prod='A4Tech FAB8'}
  @{vid='09DA'; pid='FA44'; port=3255; mfr='A4TECH';  prod='Bloody B930 FA44'}
  @{vid='09DA'; pid='FA9A'; port=3256; mfr='A4TECH';  prod='A4Tech FA9A'}
  @{vid='09DA'; pid='FC7C'; port=3257; mfr='A4TECH';  prod='A4Tech FC7C'}
)

$env:PYTHONUNBUFFERED = "1"
foreach ($d in $devs) {
  $p = Start-Process -FilePath $py -ArgumentList @(
    '-u', (Join-Path $root 'emulate_vidpid.py'),
    '--vid', $d.vid, '--pid', $d.pid, '--port', "$($d.port)",
    '--manufacturer', $d.mfr, '--product', $d.prod
  ) -WorkingDirectory $root -WindowStyle Minimized -PassThru
  L "spoof $($d.vid):$($d.pid) port $($d.port) pid $($p.Id)"
  Start-Sleep -Milliseconds 500
}
Start-Sleep 2

foreach ($d in $devs) {
  $port = $d.port
  L "=== list/attach $($d.vid):$($d.pid) @ $port ==="
  & $usbip -t $port list -r 127.0.0.1 2>&1 | ForEach-Object { L $_ }
  & $usbip -t $port attach -r 127.0.0.1 -b 1-1 2>&1 | ForEach-Object { L $_ }
  Start-Sleep 1
}

Start-Sleep 3
L "=== usbip port ==="
& $usbip port 2>&1 | ForEach-Object { L $_ }

L "=== present 09DA / 2F4C ==="
Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object { $_.InstanceId -match 'VID_09DA|VID_2F4C' } |
  ForEach-Object {
    L ("PRESENT " + $_.Status + " | " + $_.FriendlyName + " | " + $_.InstanceId)
  }

L "done"
