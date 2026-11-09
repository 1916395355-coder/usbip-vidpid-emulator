# -*- coding: utf-8 -*-
"""
3837:1018 spoof（迈从系，缺口标疑似套装，门店键鼠双报）

用法:
  python -u emulate_3837_1018.py
  python -u emulate_3837_1018.py --port 3241
然后（管理员）:
  E:\\USBip\\usbip.exe list -r 127.0.0.1:3241
  E:\\USBip\\usbip.exe attach -r 127.0.0.1:3241 -b 1-1
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

VID = 0x3837
PID = 0x1018
LOG = Path(__file__).with_name("emulate_3837_1018.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3241)
    ap.add_argument("--serial", default="SPOOF1018000001")
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
        manufacturer="MCHOSE",
        product="MCHOSE Kit (spoof 1018)",
        serial=args.serial,
    )
    dev.add(mouse)
    dev.add(keyboard)

    transport = USBIP(args.host, args.port)
    log(
        f"serving composite mouse+keyboard "
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
