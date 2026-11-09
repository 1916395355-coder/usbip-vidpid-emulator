# -*- coding: utf-8 -*-
"""Try to fetch USB config/HID report descriptors for 1532:0A4E."""
from __future__ import annotations

import ctypes
import re
import struct
from ctypes import wintypes
from pathlib import Path

OUT = Path(__file__).with_name("out_real_blackshark")
OUT.mkdir(exist_ok=True)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 0x10

# GUID_DEVINTERFACE_USB_DEVICE
GUID_DEVINTERFACE_USB_DEVICE = "{A5DCBF10-6530-11D2-901F-00C04FB951ED}"
# GUID_DEVINTERFACE_HID
GUID_DEVINTERFACE_HID = "{4D1E55B2-F16F-11CF-88CB-001111000030}"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


class SP_DEVICE_INTERFACE_DETAIL_DATA_W(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("DevicePath", wintypes.WCHAR * 1024)]


def parse_guid(s: str) -> GUID:
    s = s.strip("{}")
    a, b, c, d, e = s.split("-")
    g = GUID()
    g.Data1 = int(a, 16)
    g.Data2 = int(b, 16)
    g.Data3 = int(c, 16)
    rest = bytes.fromhex(d + e)
    for i, x in enumerate(rest):
        g.Data4[i] = x
    return g


SetupDiGetClassDevsW = setupapi.SetupDiGetClassDevsW
SetupDiEnumDeviceInterfaces = setupapi.SetupDiEnumDeviceInterfaces
SetupDiGetDeviceInterfaceDetailW = setupapi.SetupDiGetDeviceInterfaceDetailW
SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList


def list_interfaces(guid_str: str):
    guid = parse_guid(guid_str)
    hdev = SetupDiGetClassDevsW(ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    if hdev == ctypes.c_void_p(-1).value:
        raise OSError("SetupDiGetClassDevs failed")
    out = []
    idx = 0
    while True:
        ifdata = SP_DEVICE_INTERFACE_DATA()
        ifdata.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
        if not SetupDiEnumDeviceInterfaces(hdev, None, ctypes.byref(guid), idx, ctypes.byref(ifdata)):
            break
        detail = SP_DEVICE_INTERFACE_DETAIL_DATA_W()
        detail.cbSize = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        needed = wintypes.DWORD()
        SetupDiGetDeviceInterfaceDetailW(hdev, ctypes.byref(ifdata), ctypes.byref(detail), ctypes.sizeof(detail), ctypes.byref(needed), None)
        path = detail.DevicePath
        if "vid_1532" in path.lower() and "pid_0a4e" in path.lower():
            out.append(path)
        idx += 1
    SetupDiDestroyDeviceInfoList(hdev)
    return out


# USB IOCTLs for descriptor via hub are complex; try WinUSB-style raw control on device
# IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION needs hub.

# Alternative: use hid.dll HidD_GetManufacturerString etc already known.
# Reconstruct report descriptor from known caps — write both.

def build_mi05_report_descriptor() -> bytes:
    """
    Rebuild MI_05 RD matching observed collections:
      Col01: UP 0x000C Usage 0x0001, Input 2B
      Col02: UP 0xFF13 Usage 0x0001, In/Out 62B
      Col03: UP 0x000B Usage 0x0005, In/Out 2B
      Col04: UP 0xFF14 Usage 0x0001, In/Out 64B  (Synapse protocol)
    """
    def u8(*xs):
        return bytes(xs)

    rd = bytearray()
    # Col01 Consumer Control — 2-byte input
    rd += u8(0x05, 0x0C)  # Usage Page (Consumer)
    rd += u8(0x09, 0x01)  # Usage (Consumer Control)
    rd += u8(0xA1, 0x01)  # Collection (Application)
    rd += u8(0x15, 0x00)  # Logical Min
    rd += u8(0x25, 0x01)  # Logical Max
    rd += u8(0x75, 0x01)  # Report Size 1
    rd += u8(0x95, 0x02)  # Report Count 2  -> pad carefully for 2 bytes
    # simpler: 2 bytes array input
    rd = bytearray()
    rd += u8(0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01)
    rd += u8(0x15, 0x00, 0x26, 0xFF, 0x00)
    rd += u8(0x75, 0x08, 0x95, 0x02)
    rd += u8(0x09, 0x01, 0x81, 0x02)  # Input Data,Var,Abs
    rd += u8(0xC0)

    # Col02 vendor FF13 62B in/out
    rd += u8(0x06, 0x13, 0xFF, 0x09, 0x01, 0xA1, 0x01)
    rd += u8(0x15, 0x00, 0x26, 0xFF, 0x00)
    rd += u8(0x75, 0x08, 0x95, 0x3E)  # 62
    rd += u8(0x09, 0x01, 0x81, 0x02)  # Input
    rd += u8(0x09, 0x01, 0x91, 0x02)  # Output
    rd += u8(0xC0)

    # Col03 Telephony Headset 2B in/out
    rd += u8(0x05, 0x0B, 0x09, 0x05, 0xA1, 0x01)
    rd += u8(0x15, 0x00, 0x26, 0xFF, 0x00)
    rd += u8(0x75, 0x08, 0x95, 0x02)
    rd += u8(0x09, 0x05, 0x81, 0x02)
    rd += u8(0x09, 0x05, 0x91, 0x02)
    rd += u8(0xC0)

    # Col04 vendor FF14 64B in/out — Valkyrie
    rd += u8(0x06, 0x14, 0xFF, 0x09, 0x01, 0xA1, 0x01)
    rd += u8(0x15, 0x00, 0x26, 0xFF, 0x00)
    rd += u8(0x75, 0x08, 0x95, 0x40)  # 64
    rd += u8(0x09, 0x01, 0x81, 0x02)
    rd += u8(0x09, 0x01, 0x91, 0x02)
    rd += u8(0xC0)
    return bytes(rd)


usb_paths = list_interfaces(GUID_DEVINTERFACE_USB_DEVICE)
hid_paths = list_interfaces(GUID_DEVINTERFACE_HID)
print("USB device interfaces:")
for p in usb_paths:
    print(" ", p)
print("HID interfaces matching 0A4E:")
for p in hid_paths:
    if "0a4e" in p.lower():
        print(" ", p)

rd = build_mi05_report_descriptor()
(OUT / "mi05_report_desc_reconstructed.bin").write_bytes(rd)
(OUT / "mi05_report_desc_reconstructed.hex").write_text(rd.hex(" "), encoding="utf-8")
print(f"reconstructed MI_05 RD len={len(rd)}")

# Try open parent USB MI_05 path for raw descriptor via HID class driver
mi05 = [p for p in hid_paths if "mi_05" in p.lower() and "col" not in p.lower()]
# also USB path for composite
for label, paths in (("usb", usb_paths), ("hid_mi05_parent", [p for p in hid_paths if re.search(r"mi_05", p, re.I) and "col" not in p.lower()])):
    print(f"candidates {label}: {paths}")
