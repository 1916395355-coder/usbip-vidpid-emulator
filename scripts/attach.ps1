# Attach the USB/IP device published on 127.0.0.1:3240 (busid 1-1).
# Set USBIP_EXE if usbip.exe is not on PATH, e.g.:
#   $env:USBIP_EXE = 'C:\Tools\USBip\usbip.exe'

param(
    [string]$Remote = "127.0.0.1",
    [string]$BusId = "1-1"
)

$ErrorActionPreference = "Stop"

function Resolve-Usbip {
    if ($env:USBIP_EXE -and (Test-Path $env:USBIP_EXE)) { return $env:USBIP_EXE }
    $cmd = Get-Command usbip.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        "C:\Program Files\USBip\usbip.exe",
        "C:\Program Files (x86)\USBip\usbip.exe",
        "E:\USBip\usbip.exe"
    )) {
        if (Test-Path $p) { return $p }
    }
    throw "usbip.exe not found. Install usbip-win2 and/or set USBIP_EXE."
}

$usbip = Resolve-Usbip
& $usbip list -r $Remote
& $usbip attach -r $Remote -b $BusId
& $usbip port
