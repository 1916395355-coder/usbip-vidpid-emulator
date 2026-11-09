# -*- coding: utf-8 -*-
"""
Minimal USB/IP HID emulator with a custom VID/PID.

Attach with usbip-win2 to 127.0.0.1; Device Manager should show the hardware ID.

Usage:
  python emulate_hid.py
  python emulate_hid.py --vid 0x1234 --pid 0x5678 --kind mouse
  python emulate_hid.py --vid 0x1234 --pid 0x5678 --kind keyboard
"""
from __future__ import annotations

import argparse
import time

from usbip.classes.device import HID
from usbip.classes.device.hid import (
    PROTOCOL_KEYBOARD,
    PROTOCOL_MOUSE,
    SUBCLASS_BOOT,
    keyboard_report_descriptor,
    mouse_report_descriptor,
)
from usbip.device import USBDevice
from usbip.transport import USBIP


def parse_hex(s: str) -> int:
    return int(s, 0)


def main() -> None:
    ap = argparse.ArgumentParser(description="USB/IP 虚拟 HID，自定义 VID/PID")
    ap.add_argument("--vid", type=parse_hex, default=0x1234, help="如 0x1234 或 1234")
    ap.add_argument("--pid", type=parse_hex, default=0x5678, help="如 0x5678")
    ap.add_argument("--kind", choices=("mouse", "keyboard"), default="mouse")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--product", default=None)
    args = ap.parse_args()

    if args.kind == "mouse":
        hid = HID(
            mouse_report_descriptor(),
            subclass=SUBCLASS_BOOT,
            protocol=PROTOCOL_MOUSE,
            in_mps=8,
            in_interval=10,
        )
        product = args.product or "Spoof Mouse"
    else:
        hid = HID(
            keyboard_report_descriptor(),
            subclass=SUBCLASS_BOOT,
            protocol=PROTOCOL_KEYBOARD,
            in_mps=8,
            in_interval=10,
        )
        product = args.product or "Spoof Keyboard"

    vid, pid = args.vid & 0xFFFF, args.pid & 0xFFFF
    dev = USBDevice(
        vid,
        pid,
        manufacturer="VIDPID-Spoof",
        product=product,
        serial="SPOOF0001",
    )
    dev.add(hid)

    transport = USBIP(args.host, args.port)
    print(
        f"serving HID {args.kind} "
        f"VID_{vid:04X}&PID_{pid:04X} on {args.host}:{args.port}"
    )
    print("Windows: usbip-win2 里 list/attach -> 127.0.0.1 , busid 通常是 1-1")
    print("预期硬件 ID: USB\\VID_{:04X}&PID_{:04X}".format(vid, pid))
    print("Ctrl+C 结束")
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
