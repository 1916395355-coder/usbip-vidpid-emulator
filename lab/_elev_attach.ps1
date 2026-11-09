$ErrorActionPreference = "Continue"
$log = "d:\开发项目\usbip-vidpid-spoof\_elev_attach.log"
function L($m){ "$(Get-Date -Format o) $m" | Tee-Object -FilePath $log -Append }

Remove-Item $log -Force -ErrorAction SilentlyContinue
L "begin"

# detach all
& "E:\USBip\usbip.exe" detach -p 1 2>&1 | ForEach-Object { L $_ }
& "E:\USBip\usbip.exe" detach -p 2 2>&1 | ForEach-Object { L $_ }
& "E:\USBip\usbip.exe" detach -p 3 2>&1 | ForEach-Object { L $_ }

# remove stuck nodes
$ids = @(
  "USB\VID_0000&PID_0000\2&3b7c36a2&0&1",
  "USB\VID_3869&PID_7C18\SPOOF7C18000001"
)
Get-PnpDevice | Where-Object { $_.InstanceId -match "VID_3869&PID_7C18|VID_0000&PID_0000" } | ForEach-Object { $ids += $_.InstanceId }
$ids = $ids | Select-Object -Unique
foreach($id in $ids){
  L "remove $id"
  pnputil /remove-device "$id" 2>&1 | ForEach-Object { L $_ }
}

L "restart USBip HC"
pnputil /restart-device "ROOT\USB\0000" 2>&1 | ForEach-Object { L $_ }
Start-Sleep 2

# kill old spoof
Get-NetTCPConnection -LocalPort 3240 -ErrorAction SilentlyContinue | ForEach-Object {
  L "kill pid $($_.OwningProcess)"
  Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep 1

$env:USBIP_PCAPNG = "d:\开发项目\usbip-vidpid-spoof\spoof.pcapng"
$env:PYTHONUNBUFFERED = "1"
Remove-Item $env:USBIP_PCAPNG -Force -ErrorAction SilentlyContinue

$p = Start-Process -FilePath "C:\Users\lh.wang\AppData\Local\Programs\Python\Python314\python.exe" `
  -ArgumentList "-u","d:\开发项目\usbip-vidpid-spoof\emulate_iqunix_7c18.py" `
  -WorkingDirectory "d:\开发项目\usbip-vidpid-spoof" `
  -WindowStyle Hidden -PassThru
L "spoof pid $($p.Id)"
Start-Sleep 2

L "list"
& "E:\USBip\usbip.exe" list -r 127.0.0.1 2>&1 | ForEach-Object { L $_ }
L "attach"
& "E:\USBip\usbip.exe" attach -r 127.0.0.1 -b 1-1 2>&1 | ForEach-Object { L $_ }
Start-Sleep 6

L "port"
& "E:\USBip\usbip.exe" port 2>&1 | ForEach-Object { L $_ }

L "hub relations"
pnputil /enum-devices /instanceid "USB\ROOT_HUB30\1&2b53a856&0&0" /relations 2>&1 | ForEach-Object { L $_ }

L "present 3869/7C18"
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match "VID_3869|7C18" } | ForEach-Object {
  L ("PRESENT " + $_.Status + " | " + $_.FriendlyName + " | " + $_.InstanceId)
}

L "pcap size"
if (Test-Path $env:USBIP_PCAPNG) { L ((Get-Item $env:USBIP_PCAPNG).Length) } else { L "no pcap" }

L "done"
