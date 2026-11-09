#Requires -Version 5.1
<#
  ROG OMNI / 0B05:1ACE cafe collector (no Python)
  Usage: plug real Omni, then right-click bat "Run as administrator"
    powershell -NoProfile -ExecutionPolicy Bypass -File collect_omni_cafe.ps1
  Output: collect_omni_YYYYMMDD_HHMMSS\ and same-name zip
  Extra: hid_usb\ report descriptors + registry enum for 0B05:1ACE
#>
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$out = Join-Path $root ("collect_omni_{0}" -f $stamp)
New-Item -ItemType Directory -Path $out -Force | Out-Null
$log = Join-Path $out '_collector.log'

function W([string]$m) {
    $line = '{0} {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Host $line
}

function Save-Text([string]$name, [string]$text) {
    Set-Content -Path (Join-Path $out $name) -Value $text -Encoding UTF8
}

function Save-Cmd([string]$name, [scriptblock]$block) {
    try { $text = & $block 2>&1 | Out-String } catch { $text = $_ | Out-String }
    Set-Content -Path (Join-Path $out $name) -Value $text -Encoding UTF8
}

function Copy-IfExists([string]$src, [string]$destName) {
    if (Test-Path -LiteralPath $src) {
        try {
            Copy-Item -LiteralPath $src -Destination (Join-Path $out $destName) -Force
            W "copied $src"
        } catch { W "copy fail $src : $_" }
    }
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
W "out=$out admin=$admin"

Save-Cmd '00_system.txt' {
    '=== OS ==='
    Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, LastBootUpTime | Format-List
    '=== Computer ==='
    Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory | Format-List
    '=== BIOS/Board ==='
    Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, SerialNumber | Format-List
    Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, SerialNumber | Format-List
    whoami
    Get-Date
}

Save-Cmd '01_pnp_0b05_1ace.txt' {
    '=== PresentOnly VID_0B05 ==='
    Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'VID_0B05' } |
        Sort-Object InstanceId |
        Format-Table Status, Class, FriendlyName, InstanceId -AutoSize
    '=== PresentOnly PID_1ACE / OMNI ==='
    Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'PID_1ACE' -or $_.FriendlyName -match 'OMNI' } |
        Format-Table Status, Class, FriendlyName, InstanceId -AutoSize
    '=== All (incl absent) 1ACE ==='
    Get-PnpDevice -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'PID_1ACE' } |
        Format-Table Status, Class, FriendlyName, InstanceId -AutoSize
}

Save-Cmd '02_pnp_1ace_properties.txt' {
    $devs = Get-PnpDevice -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match 'VID_0B05&PID_1ACE' }
    if (-not $devs) {
        'NO 1ACE DEVICE FOUND - please plug Omni receiver first'
        return
    }
    foreach ($d in $devs) {
        '========'
        $d | Format-List Status, Class, FriendlyName, InstanceId, Problem, ProblemDescription
        Get-PnpDeviceProperty -InstanceId $d.InstanceId -ErrorAction SilentlyContinue |
            Where-Object {
                $_.KeyName -match 'Driver|Inf|Service|Problem|HardwareIds|CompatibleIds|Manufacturer|Location|Container|UpperFilters|LowerFilters|Class|Enumerator|Parent|Bus'
            } |
            Select-Object KeyName, Data |
            Format-Table -AutoSize -Wrap
    }
}

Save-Cmd '03_rogms_rogkb_service.txt' {
    foreach ($svc in @('ROGMS','ROGKB','ArmouryCrateService','ArmouryCrateDownloadTool','AsusROGLSLService','ROG Live Service')) {
        "---- sc.exe query $svc ----"
        sc.exe query $svc 2>&1
        "---- sc.exe qc $svc ----"
        sc.exe qc $svc 2>&1
        ''
    }
}

Save-Cmd '04_drivers_oem.txt' {
    '=== pnputil enum-drivers (filter lines) ==='
    $all = pnputil /enum-drivers 2>&1 | Out-String
    $all -split "`r?`n" | Where-Object { $_ -match 'rogms|rogkb|asus|Published Name|Original Name|Provider Name|Class Name|Driver Version|Driver Date|oem\d+' }

    '=== oem*.inf hits 1ACE/ROGMS/ROGKB ==='
    Get-ChildItem 'C:\Windows\INF\oem*.inf' -ErrorAction SilentlyContinue | ForEach-Object {
        $hit = Select-String -Path $_.FullName -Pattern '1ACE|ROGMS|ROGKB|OMNI RECEIVER' -ErrorAction SilentlyContinue
        if ($hit) {
            "FILE $($_.Name)"
            $hit | Select-Object -First 8 | ForEach-Object { $_.Line.Trim() }
            ''
        }
    }

    '=== DriverStore rogms/rogkb ==='
    Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository' -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^rogms\.|^rogkb\.' } |
        ForEach-Object {
            $_.FullName
            Get-ChildItem $_.FullName | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
        }
}

Save-Cmd '05_usb_wmi.txt' {
    '=== Win32_PnPEntity 0B05 ==='
    Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue |
        Where-Object { $_.PNPDeviceID -match 'VID_0B05' } |
        Select-Object Name, Status, PNPClass, Service, Manufacturer, PNPDeviceID |
        Format-List
    '=== USBControllerDevice -> 1ACE ==='
    Get-CimInstance Win32_USBControllerDevice -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Dependent -match 'VID_0B05&PID_1ACE') { $_ | Format-List }
    }
}

Save-Cmd '06_setupapi_tail_1ace.txt' {
    $sap = 'C:\Windows\INF\setupapi.dev.log'
    if (-not (Test-Path $sap)) { 'no setupapi.dev.log'; return }
    $raw = [System.IO.File]::ReadAllText($sap, [Text.Encoding]::GetEncoding(0))
    foreach ($pat in @('1ACE','ROGMS','ROGKB','OMNI','NEEDREBOOT','Reboot required','CR_REMOVE_VETOED')) {
        "===== hits: $pat (last 30) ====="
        [regex]::Matches($raw, "(?im)^.*$([regex]::Escape($pat)).*$") |
            Select-Object -Last 30 | ForEach-Object { $_.Value }
        ''
    }
    $idx = $raw.LastIndexOf('1ACE', [StringComparison]::OrdinalIgnoreCase)
    if ($idx -ge 0) {
        $start = [Math]::Max(0, $idx - 4000)
        $len = [Math]::Min(12000, $raw.Length - $start)
        '===== context around last 1ACE ====='
        $raw.Substring($start, $len)
    }
}
Copy-IfExists 'C:\Windows\INF\setupapi.dev.log' 'setupapi.dev.log.copy'

Save-Cmd '07_armoury_paths.txt' {
    foreach ($p in @(
        'C:\Program Files\ASUS',
        'C:\Program Files (x86)\ASUS',
        'C:\ProgramData\ASUS',
        "$env:LOCALAPPDATA\Packages"
    )) {
        "---- $p ----"
        if (Test-Path $p) {
            Get-ChildItem $p -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match 'Armoury|ASUS|Aura|ROG|B9EC' } |
                Select-Object FullName, LastWriteTime | Format-Table -AutoSize
        } else { 'MISSING' }
    }
    '---- ArmouryDevice exists? ----'
    "x86=$(Test-Path 'C:\Program Files (x86)\ASUS\ArmouryDevice')"
    "pf=$(Test-Path 'C:\Program Files\ASUS\ArmouryDevice')"
    Get-AppxPackage *Armoury* -ErrorAction SilentlyContinue |
        Select-Object Name, Version, PackageFullName, InstallLocation | Format-List
}

$acLocal = Join-Path $env:LOCALAPPDATA 'Packages\B9ECED6F.ArmouryCrate_qmba6cd70vzyy\LocalState'
if (Test-Path $acLocal) {
    $acLogDir = Join-Path $out 'armoury_crate_logs'
    New-Item -ItemType Directory -Path $acLogDir -Force | Out-Null
    Get-ChildItem $acLocal -Filter 'ArmouryCrate_*.log' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 3 |
        ForEach-Object { Copy-Item $_.FullName $acLogDir -Force; W "AC log $($_.Name)" }
}

$svcLogDir = Join-Path $out 'armoury_service_logs'
New-Item -ItemType Directory -Path $svcLogDir -Force | Out-Null
Get-ChildItem 'C:\ProgramData\ASUS\ALL' -Filter 'ArmouryCrate.Service*.log' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 5 |
    ForEach-Object { Copy-Item $_.FullName $svcLogDir -Force; W "svc log $($_.Name)" }

Save-Cmd '08_armoury_log_grep_1ace.txt' {
    $files = @()
    $files += Get-ChildItem (Join-Path $out 'armoury_crate_logs') -ErrorAction SilentlyContinue
    $files += Get-ChildItem (Join-Path $out 'armoury_service_logs') -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        if (-not $f) { continue }
        "======== $($f.Name) ========"
        Select-String -Path $f.FullName -Pattern '1ACE|0B05|OMNI|UNIFY|DependentApp|FirstPlugin|PlugIn|PlugOut|NEEDREBOOT|Reboot' -ErrorAction SilentlyContinue |
            Select-Object -Last 80 | ForEach-Object { $_.Line }
        ''
    }
}


# ---- 10 HID/USB descriptors (no Python; SetupAPI + hid.dll) ----
$hidDir = Join-Path $out 'hid_usb'
New-Item -ItemType Directory -Path $hidDir -Force | Out-Null
W 'dump HID/USB descriptors for 0B05:1ACE ...'

$cs = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

public static class OmniHidDump2 {
  const int DIGCF_PRESENT = 2;
  const int DIGCF_DEVICEINTERFACE = 0x10;
  const uint GENERIC_READ = 0x80000000;
  const uint GENERIC_WRITE = 0x40000000;
  const uint FILE_SHARE_READ = 1;
  const uint FILE_SHARE_WRITE = 2;
  const uint OPEN_EXISTING = 3;
  const uint FILE_ATTRIBUTE_NORMAL = 0x80;
  const uint IOCTL_HID_GET_REPORT_DESCRIPTOR = 0x000B0007;
  static readonly IntPtr INVALID = new IntPtr(-1);

  [StructLayout(LayoutKind.Sequential)]
  struct GUID { public uint Data1; public ushort Data2; public ushort Data3; public byte b0,b1,b2,b3,b4,b5,b6,b7; }

  [StructLayout(LayoutKind.Sequential)]
  struct SP_DEVICE_INTERFACE_DATA {
    public int cbSize; public GUID InterfaceClassGuid; public int Flags; public IntPtr Reserved;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct HIDD_ATTRIBUTES {
    public int Size; public ushort VendorID; public ushort ProductID; public ushort VersionNumber;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct HIDP_CAPS {
    public ushort Usage; public ushort UsagePage;
    public ushort InputReportByteLength; public ushort OutputReportByteLength; public ushort FeatureReportByteLength;
    public ushort Reserved0,Reserved1,Reserved2,Reserved3,Reserved4,Reserved5,Reserved6,Reserved7,
      Reserved8,Reserved9,Reserved10,Reserved11,Reserved12,Reserved13,Reserved14,Reserved15,Reserved16;
    public ushort NumberLinkCollectionNodes;
    public ushort NumberInputButtonCaps; public ushort NumberInputValueCaps; public ushort NumberInputDataIndices;
    public ushort NumberOutputButtonCaps; public ushort NumberOutputValueCaps; public ushort NumberOutputDataIndices;
    public ushort NumberFeatureButtonCaps; public ushort NumberFeatureValueCaps; public ushort NumberFeatureDataIndices;
  }

  [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern IntPtr SetupDiGetClassDevsW(ref GUID ClassGuid, IntPtr Enumerator, IntPtr hwndParent, int Flags);
  [DllImport("setupapi.dll", SetLastError=true)]
  static extern bool SetupDiEnumDeviceInterfaces(IntPtr DeviceInfoSet, IntPtr DeviceInfoData, ref GUID InterfaceClassGuid, uint MemberIndex, ref SP_DEVICE_INTERFACE_DATA DeviceInterfaceData);
  [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern bool SetupDiGetDeviceInterfaceDetailW(IntPtr DeviceInfoSet, ref SP_DEVICE_INTERFACE_DATA DeviceInterfaceData, IntPtr DeviceInterfaceDetailData, int DeviceInterfaceDetailDataSize, out int RequiredSize, IntPtr DeviceInfoData);
  [DllImport("setupapi.dll", SetLastError=true)]
  static extern bool SetupDiDestroyDeviceInfoList(IntPtr DeviceInfoSet);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern IntPtr CreateFileW(string lpFileName, uint dwDesiredAccess, uint dwShareMode, IntPtr lpSecurityAttributes, uint dwCreationDisposition, uint dwFlagsAndAttributes, IntPtr hTemplateFile);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool DeviceIoControl(IntPtr hDevice, uint dwIoControlCode, IntPtr lpInBuffer, int nInBufferSize, byte[] lpOutBuffer, int nOutBufferSize, out int lpBytesReturned, IntPtr lpOverlapped);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool CloseHandle(IntPtr hObject);
  [DllImport("hid.dll", SetLastError=true)]
  static extern bool HidD_GetAttributes(IntPtr HidDeviceObject, ref HIDD_ATTRIBUTES Attributes);
  [DllImport("hid.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern bool HidD_GetManufacturerString(IntPtr HidDeviceObject, StringBuilder Buffer, int BufferLength);
  [DllImport("hid.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern bool HidD_GetProductString(IntPtr HidDeviceObject, StringBuilder Buffer, int BufferLength);
  [DllImport("hid.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern bool HidD_GetSerialNumberString(IntPtr HidDeviceObject, StringBuilder Buffer, int BufferLength);
  [DllImport("hid.dll", SetLastError=true)]
  static extern bool HidD_GetPreparsedData(IntPtr HidDeviceObject, out IntPtr PreparsedData);
  [DllImport("hid.dll", SetLastError=true)]
  static extern bool HidD_FreePreparsedData(IntPtr PreparsedData);
  [DllImport("hid.dll", SetLastError=true)]
  static extern int HidP_GetCaps(IntPtr PreparsedData, out HIDP_CAPS Capabilities);

  static GUID ParseGuid(string s) {
    var g = new Guid(s);
    var bytes = g.ToByteArray();
    var r = new GUID();
    r.Data1 = BitConverter.ToUInt32(bytes, 0);
    r.Data2 = BitConverter.ToUInt16(bytes, 4);
    r.Data3 = BitConverter.ToUInt16(bytes, 6);
    r.b0=bytes[8]; r.b1=bytes[9]; r.b2=bytes[10]; r.b3=bytes[11];
    r.b4=bytes[12]; r.b5=bytes[13]; r.b6=bytes[14]; r.b7=bytes[15];
    return r;
  }

  static List<string> ListPaths(string guidStr, ushort vid, ushort pid) {
    var list = new List<string>();
    var guid = ParseGuid(guidStr);
    IntPtr h = SetupDiGetClassDevsW(ref guid, IntPtr.Zero, IntPtr.Zero, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
    if (h == INVALID) return list;
    try {
      uint idx = 0;
      while (true) {
        var ifd = new SP_DEVICE_INTERFACE_DATA();
        ifd.cbSize = Marshal.SizeOf(typeof(SP_DEVICE_INTERFACE_DATA));
        if (!SetupDiEnumDeviceInterfaces(h, IntPtr.Zero, ref guid, idx, ref ifd)) break;
        int need = 0;
        SetupDiGetDeviceInterfaceDetailW(h, ref ifd, IntPtr.Zero, 0, out need, IntPtr.Zero);
        if (need <= 0) { idx++; continue; }
        IntPtr detail = Marshal.AllocHGlobal(need);
        try {
          Marshal.WriteInt32(detail, IntPtr.Size == 8 ? 8 : 6);
          if (SetupDiGetDeviceInterfaceDetailW(h, ref ifd, detail, need, out need, IntPtr.Zero)) {
            string path = Marshal.PtrToStringUni(new IntPtr(detail.ToInt64() + 4));
            if (!string.IsNullOrEmpty(path)) {
              string low = path.ToLowerInvariant();
              string v = "vid_" + vid.ToString("x4");
              string p = "pid_" + pid.ToString("x4");
              if (low.Contains(v) && low.Contains(p)) list.Add(path);
            }
          }
        } finally { Marshal.FreeHGlobal(detail); }
        idx++;
      }
    } finally { SetupDiDestroyDeviceInfoList(h); }
    return list;
  }

  static IntPtr OpenDev(string path) {
    // HID: DesiredAccess 0 + share R/W often required for keyboard/mouse
    uint[] accessList = new uint[] { 0, GENERIC_READ, GENERIC_READ | GENERIC_WRITE };
    foreach (uint access in accessList) {
      IntPtr h = CreateFileW(path, access, FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, IntPtr.Zero);
      if (h != INVALID) return h;
      if (path.EndsWith("\\kbd", StringComparison.OrdinalIgnoreCase) || path.EndsWith("\\mouse", StringComparison.OrdinalIgnoreCase)) {
        string trimmed = path.Substring(0, path.LastIndexOf('\\'));
        h = CreateFileW(trimmed, access, FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, IntPtr.Zero);
        if (h != INVALID) return h;
      }
    }
    return INVALID;
  }

  static string SafeStr(StringBuilder sbx, bool ok) { return ok ? sbx.ToString().TrimEnd('\0') : ""; }

  public static string Run(string outDir, ushort vid, ushort pid) {
    Directory.CreateDirectory(outDir);
    var sb = new StringBuilder();
    string hidGuid = "{4D1E55B2-F16F-11CF-88CB-001111000030}";
    string usbGuid = "{A5DCBF10-6530-11D2-901F-00C04FB951ED}";
    var hidPaths = ListPaths(hidGuid, vid, pid);
    var usbPaths = ListPaths(usbGuid, vid, pid);
    sb.AppendLine("VID=0x" + vid.ToString("X4") + " PID=0x" + pid.ToString("X4"));
    sb.AppendLine("USB interfaces: " + usbPaths.Count);
    foreach (var p in usbPaths) sb.AppendLine("  USB " + p);
    sb.AppendLine("HID interfaces: " + hidPaths.Count);
    int i = 0;
    foreach (var path in hidPaths) {
      sb.AppendLine("---- HID[" + i + "] ----");
      sb.AppendLine("path=" + path);
      IntPtr h = OpenDev(path);
      if (h == INVALID) {
        sb.AppendLine("CreateFile FAILED err=" + Marshal.GetLastWin32Error());
        i++; continue;
      }
      try {
        var attr = new HIDD_ATTRIBUTES(); attr.Size = Marshal.SizeOf(typeof(HIDD_ATTRIBUTES));
        bool aok = HidD_GetAttributes(h, ref attr);
        sb.AppendLine(aok
          ? ("attr VID=0x" + attr.VendorID.ToString("X4") + " PID=0x" + attr.ProductID.ToString("X4") + " ver=0x" + attr.VersionNumber.ToString("X4"))
          : ("HidD_GetAttributes fail err=" + Marshal.GetLastWin32Error()));
        var ms = new StringBuilder(256); var ps = new StringBuilder(256); var ss = new StringBuilder(256);
        sb.AppendLine("manufacturer=" + SafeStr(ms, HidD_GetManufacturerString(h, ms, 256)));
        sb.AppendLine("product=" + SafeStr(ps, HidD_GetProductString(h, ps, 256)));
        sb.AppendLine("serial=" + SafeStr(ss, HidD_GetSerialNumberString(h, ss, 256)));

        IntPtr prep;
        if (HidD_GetPreparsedData(h, out prep)) {
          try {
            HIDP_CAPS caps;
            int st = HidP_GetCaps(prep, out caps);
            sb.AppendLine("HidP_GetCaps status=" + st
              + " UsagePage=0x" + caps.UsagePage.ToString("X4")
              + " Usage=0x" + caps.Usage.ToString("X4")
              + " InLen=" + caps.InputReportByteLength
              + " OutLen=" + caps.OutputReportByteLength
              + " FeatLen=" + caps.FeatureReportByteLength
              + " LinkNodes=" + caps.NumberLinkCollectionNodes);
          } finally { HidD_FreePreparsedData(prep); }
        } else {
          sb.AppendLine("HidD_GetPreparsedData fail err=" + Marshal.GetLastWin32Error());
        }

        byte[] buf = new byte[4096];
        int ret = 0;
        bool ok = DeviceIoControl(h, IOCTL_HID_GET_REPORT_DESCRIPTOR, IntPtr.Zero, 0, buf, buf.Length, out ret, IntPtr.Zero);
        if (ok && ret > 0) {
          string baseName = "hid_" + i.ToString("00");
          string low = path.ToLowerInvariant();
          int mi = low.IndexOf("mi_");
          if (mi >= 0 && mi + 5 <= low.Length) baseName += "_" + low.Substring(mi, 5).Replace('\\','_').Replace('#','_');
          int col = low.IndexOf("col");
          if (col >= 0 && col + 5 <= low.Length) baseName += "_" + low.Substring(col, Math.Min(5, low.Length - col)).Replace('\\','_').Replace('#','_');
          string bin = Path.Combine(outDir, baseName + "_report_desc.bin");
          string hex = Path.Combine(outDir, baseName + "_report_desc.hex");
          byte[] slice = new byte[ret];
          Buffer.BlockCopy(buf, 0, slice, 0, ret);
          File.WriteAllBytes(bin, slice);
          var hexSb = new StringBuilder(ret * 3);
          for (int k = 0; k < ret; k++) {
            if (k > 0) hexSb.Append(' ');
            hexSb.Append(slice[k].ToString("x2"));
          }
          File.WriteAllText(hex, hexSb.ToString(), Encoding.ASCII);
          sb.AppendLine("report_descriptor_len=" + ret + " file=" + Path.GetFileName(bin));
        } else {
          sb.AppendLine("IOCTL_HID_GET_REPORT_DESCRIPTOR fail ok=" + ok + " ret=" + ret + " err=" + Marshal.GetLastWin32Error());
        }
      } finally { CloseHandle(h); }
      i++;
    }
    string summaryPath = Path.Combine(outDir, "enumerate.txt");
    File.WriteAllText(summaryPath, sb.ToString(), Encoding.UTF8);
    return sb.ToString();
  }
}
'@

try {
    if (-not ([System.Management.Automation.PSTypeName]'OmniHidDump2').Type) {
        Add-Type -TypeDefinition $cs -Language CSharp -ErrorAction Stop
    }
} catch {
    if ($_.Exception.Message -notmatch 'already exists') {
        W "Add-Type OmniHidDump2 fail: $_"
    }
}

try {
    $enumText = [OmniHidDump2]::Run($hidDir, [uint16]0x0B05, [uint16]0x1ACE)
    Save-Text '10_hid_usb_descriptors.txt' $enumText
    W ("hid_usb files={0}" -f ((Get-ChildItem $hidDir -ErrorAction SilentlyContinue | Measure-Object).Count))
} catch {
    Save-Text '10_hid_usb_descriptors.txt' ("FAIL: " + $_)
    W "hid dump fail: $_"
}

# Registry enum for USB composite + children
Save-Cmd '11_registry_enum_1ace.txt' {
    $roots = @(
        'HKLM:\SYSTEM\CurrentControlSet\Enum\USB',
        'HKLM:\SYSTEM\CurrentControlSet\Enum\HID'
    )
    foreach ($r in $roots) {
        if (-not (Test-Path $r)) { continue }
        Get-ChildItem $r -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match 'VID_0B05&PID_1ACE' } | ForEach-Object {
            "==== $($_.PSPath) ===="
            Get-ChildItem $_.PSPath -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
                try {
                    $p = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
                    if ($p) {
                        $_.PSPath
                        $p | Select-Object DeviceDesc, FriendlyName, Service, ClassGUID, Driver, Mfg, HardwareID, CompatibleIDs, ParentIdPrefix, LocationInformation, UpperFilters, LowerFilters |
                            Format-List
                    }
                } catch {}
            }
        }
    }
}

Save-Cmd '09_processes_asus.txt' {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -match 'Armoury|Asus|ROG|Aura|usbip|wusbip' } |
        Select-Object Id, ProcessName, Path | Format-Table -AutoSize
    '=== PendingFileRenameOperations ==='
    $sm = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -ErrorAction SilentlyContinue
    if ($sm -and $sm.PendingFileRenameOperations) { $sm.PendingFileRenameOperations } else { 'none' }
}

$summary = New-Object System.Text.StringBuilder
[void]$summary.AppendLine("collect_omni $stamp")
[void]$summary.AppendLine("admin=$admin computer=$env:COMPUTERNAME user=$env:USERNAME")
$present = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -match 'VID_0B05&PID_1ACE' })
[void]$summary.AppendLine(("1ACE_present_count={0}" -f $present.Count))
foreach ($d in $present) {
    [void]$summary.AppendLine(("  {0} | {1} | {2}" -f $d.Status, $d.Class, $d.InstanceId))
}
[void]$summary.AppendLine('ROGMS:')
[void]$summary.AppendLine((sc.exe query ROGMS 2>&1 | Out-String))
Save-Text 'README_summary.txt' $summary.ToString()
W $summary.ToString()

$zip = Join-Path $root ("collect_omni_{0}.zip" -f $stamp)
try {
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path $out -DestinationPath $zip -Force
    W "zip=$zip"
} catch {
    W "zip fail: $_  (copy the folder instead)"
}

W 'DONE'
Write-Host ''
Write-Host 'Send back this zip:' -ForegroundColor Green
Write-Host $zip -ForegroundColor Yellow
if (-not (Test-Path $zip)) {
    Write-Host 'Or the whole folder:' -ForegroundColor Yellow
    Write-Host $out
}