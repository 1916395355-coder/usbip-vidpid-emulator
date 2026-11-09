$log = "d:\????\usbip-vidpid-spoof\_elev_clean.log"
"start $(Get-Date)" | Out-File $log
& "E:\USBip\usbip.exe" detach -p 1 2>&1 | Tee-Object -FilePath $log -Append
& "E:\USBip\usbip.exe" detach -p 2 2>&1 | Tee-Object -FilePath $log -Append
pnputil /remove-device "USB\VID_0000&PID_0000\2&3b7c36a2&0&1" 2>&1 | Tee-Object -FilePath $log -Append
Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_3869&PID_7C18|VID_0000&PID_0000' } | ForEach-Object {
  "removing $($_.InstanceId) status=$($_.Status)" | Tee-Object -FilePath $log -Append
  pnputil /remove-device $_.InstanceId 2>&1 | Tee-Object -FilePath $log -Append
}
"done $(Get-Date)" | Tee-Object -FilePath $log -Append
