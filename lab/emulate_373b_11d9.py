# -*- coding: utf-8 -*-
"""
373B:11D9 spoof（对标缺口，ATK/VGN 系，门店键鼠双报）

用法:
  python -u emulate_373b_11d9.py
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

VID = 0x373B
PID = 0x11D9
LOG = Path(__file__).with_name("emulate_373b_11d9.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--serial", default="SPOOF11D9000001")
    args = ap.parse_args()

    mouse = HID(
        mouse_report_descriptor(),
        subclass=SUBCLASS_BOOT,
        protocol=PROTOCOL_MOUSE,
        in_mps=8,
        in_interval=10,
    )
    keyboard = HID(
        keyboard_report_descriptor(),
        subclass=SUBCLASS_BOOT,
        protocol=PROTOCOL_KEYBOARD,
        in_mps=8,
        in_interval=10,
    )

    dev = USBDevice(
        VID,
        PID,
        manufacturer="ATK",
        product="ATK Receiver (spoof 11D9)",
        serial=args.serial,
    )
    dev.add(mouse)
    dev.add(keyboard)

    transport = USBIP(args.host, args.port)
    log(
        f"serving composite mouse+keyboard "
        f"VID_{VID:04X}&PID_{PID:04X} on {args.host}:{args.port}"
    )
    log("Windows: usbip list/attach -> 127.0.0.1 busid 1-1")
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
