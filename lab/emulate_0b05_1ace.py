# -*- coding: utf-8 -*-
"""
0B05:1ACE spoof — ROG OMNI RECEIVER

INF 期望:
  HID\\VID_0B05&PID_1ACE&MI_00&Col01  → ROGKB
  HID\\VID_0B05&PID_1ACE&MI_01        → ROGMS

用法:
  python -u emulate_0b05_1ace.py
  python -u emulate_0b05_1ace.py --port 3240
然后（管理员）:
  E:\\USBip\\usbip.exe list -r 127.0.0.1
  E:\\USBip\\usbip.exe attach -r 127.0.0.1 -b 1-1
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

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

VID = 0x0B05
PID = 0x1ACE
LOG = Path(__file__).with_name("emulate_0b05_1ace.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--serial", default="SPOOF1ACE000001")
    args = ap.parse_args()

    # MI_00 = keyboard, MI_01 = mouse（对齐 ROGKB / ROGMS）
    keyboard = HID(
        keyboard_report_descriptor(),
        subclass=SUBCLASS_BOOT,
        protocol=PROTOCOL_KEYBOARD,
        in_mps=8,
        in_interval=10,
    )
    mouse = HID(
        mouse_report_descriptor(),
        subclass=SUBCLASS_BOOT,
        protocol=PROTOCOL_MOUSE,
        in_mps=8,
        in_interval=10,
    )

    dev = USBDevice(
        VID,
        PID,
        manufacturer="ASUSTeK Computer Inc.",
        product="ROG OMNI RECEIVER",
        serial=args.serial,
    )
    dev.add(keyboard)
    dev.add(mouse)

    transport = USBIP(args.host, args.port)
    Path(LOG).write_text("", encoding="utf-8")
    log(
        f"serving composite keyboard+mouse "
        f"VID_{VID:04X}&PID_{PID:04X} on {args.host}:{args.port}"
    )
    log(f"Windows: usbip list/attach -> 127.0.0.1:{args.port} busid 1-1")
    log(f"预期硬件 ID: USB\\VID_{VID:04X}&PID_{PID:04X}")
    log("Ctrl+C 结束")
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
