# -*- coding: utf-8 -*-
"""Dump real BlackShark V3 Pro Xbox USB (1532:0A4E) HID/USB info."""
from __future__ import annotations

import ctypes
import json
import struct
import sys
from ctypes import wintypes
from pathlib import Path

OUT = Path(__file__).with_name("out_real_blackshark")
OUT.mkdir(exist_ok=True)

VID, PID = 0x1532, 0x0A4E

# --- hidapi enumerate ---
import hid

devs = [d for d in hid.enumerate() if d.get("vendor_id") == VID and d.get("product_id") == PID]
print(f"hidapi devices: {len(devs)}")
for i, d in enumerate(devs):
    print(
        f"[{i}] iface={d.get('interface_number')} usage_page=0x{d.get('usage_page',0):04X} "
        f"usage=0x{d.get('usage',0):04X} path={d.get('path')!r}"
    )
    print(f"     product={d.get('product_string')!r} manufacturer={d.get('manufacturer_string')!r} serial={d.get('serial_number')!r}")

(OUT / "hid_enumerate.json").write_text(
    json.dumps(
        [
            {
                k: (v.decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else v)
                for k, v in d.items()
            }
            for d in devs
        ],
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

# --- raw report descriptor via HidD / SetupAPI is hard; use IOCTL on handle ---
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
hid_dll = ctypes.WinDLL("hid", use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# IOCTL_HID_GET_REPORT_DESCRIPTOR = CTL_CODE(FILE_DEVICE_KEYBOARD, 1, METHOD_NEITHER, FILE_ANY_ACCESS)
# On modern Windows, prefer HidD_GetPreparsedData for caps; for raw RD use:
# METHOD: open device and DeviceIoControl with IOCTL_HID_GET_REPORT_DESCRIPTOR = 0x000B0001? 
# Actually: FILE_DEVICE_KEYBOARD=0x0b, Function=1, Method=0 (BUFFERED)? 
# Documented: IOCTL_HID_GET_REPORT_DESCRIPTOR = CTL_CODE(0x0000000b, 1, 0, 0) = 0x000B0004? Let's compute:
# CTL_CODE(DeviceType, Function, Method, Access) = (DeviceType<<16)|(Access<<14)|(Function<<2)|Method
# FILE_DEVICE_KEYBOARD=0x0B, HID function GET_REPORT_DESCRIPTOR=1, METHOD_NEITHER=3, FILE_ANY_ACCESS=0
# = (0x0B<<16) | (0<<14) | (1<<2) | 3 = 0x000B0007

IOCTL_HID_GET_REPORT_DESCRIPTOR = 0x000B0007


def get_report_descriptor(path_bytes: bytes) -> bytes | None:
    handle = kernel32.CreateFileW(
        path_bytes.decode("utf-8") if isinstance(path_bytes, bytes) else path_bytes,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE or handle is None or handle == -1:
        # try read-only
        handle = kernel32.CreateFileW(
            path_bytes.decode("utf-8") if isinstance(path_bytes, bytes) else path_bytes,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
    if handle == INVALID_HANDLE_VALUE or handle is None or int(handle) == -1:
        err = ctypes.get_last_error()
        print(f"  CreateFile failed err={err} path={path_bytes!r}")
        return None

    buf = (ctypes.c_ubyte * 4096)()
    returned = wintypes.DWORD()
    ok = kernel32.DeviceIoControl(
        handle,
        IOCTL_HID_GET_REPORT_DESCRIPTOR,
        None,
        0,
        buf,
        ctypes.sizeof(buf),
        ctypes.byref(returned),
        None,
    )
    kernel32.CloseHandle(handle)
    if not ok:
        print(f"  DeviceIoControl failed err={ctypes.get_last_error()}")
        return None
    return bytes(buf[: returned.value])


# Also try HidD_GetPreparsedData + caps
class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


hid_dll.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid_dll.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
hid_dll.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid_dll.HidD_FreePreparsedData.restype = wintypes.BOOLEAN
hid_dll.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid_dll.HidP_GetCaps.restype = ctypes.c_long  # NTSTATUS


def get_caps(path: str):
    handle = kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
    )
    if int(handle) in (-1, 0):
        handle = kernel32.CreateFileW(
            path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
        )
    if int(handle) in (-1, 0):
        return None
    prep = ctypes.c_void_p()
    if not hid_dll.HidD_GetPreparsedData(handle, ctypes.byref(prep)):
        kernel32.CloseHandle(handle)
        return None
    caps = HIDP_CAPS()
    status = hid_dll.HidP_GetCaps(prep, ctypes.byref(caps))
    hid_dll.HidD_FreePreparsedData(prep)
    kernel32.CloseHandle(handle)
    if status != 0x00110000:  # HIDP_STATUS_SUCCESS
        # still return caps if filled
        pass
    return {
        "Usage": caps.Usage,
        "UsagePage": caps.UsagePage,
        "InputReportByteLength": caps.InputReportByteLength,
        "OutputReportByteLength": caps.OutputReportByteLength,
        "FeatureReportByteLength": caps.FeatureReportByteLength,
        "NumberLinkCollectionNodes": caps.NumberLinkCollectionNodes,
        "status": hex(status & 0xFFFFFFFF),
    }


results = []
for i, d in enumerate(devs):
    path = d["path"]
    if isinstance(path, bytes):
        path_str = path.decode("utf-8", "surrogateescape")
    else:
        path_str = path
    print(f"\n=== dump [{i}] ===")
    caps = get_caps(path_str)
    print("caps", caps)
    rd = get_report_descriptor(path_str)
    if rd:
        print(f"report_desc len={len(rd)} hex={rd[:64].hex()}")
        (OUT / f"report_desc_{i}_iface{d.get('interface_number')}_up{d.get('usage_page'):04X}_u{d.get('usage'):04X}.bin").write_bytes(rd)
    else:
        print("report_desc: FAILED")
    results.append({"enum": {k: (v.decode('utf-8','replace') if isinstance(v,(bytes,bytearray)) else v) for k,v in d.items()}, "caps": caps, "rd_len": len(rd) if rd else 0})

(OUT / "summary.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nWrote", OUT)
