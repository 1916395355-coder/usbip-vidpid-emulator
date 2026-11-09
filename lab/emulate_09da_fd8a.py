# -*- coding: utf-8 -*-
"""
09DA:FD8A spoof（缺口双报大户，疑似双飞燕/血手无线接收器）

同时挂鼠标 + 键盘两个 Boot HID，方便设备管理器/云海看到
USB\\VID_09DA&PID_FD8A 且键鼠都有。

用法:
  python -u emulate_09da_fd8a.py
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

VID = 0x09DA
PID = 0xFD8A
LOG = Path(__file__).with_name("emulate_09da_fd8a.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--serial", default="SPOOFFD8A000001")
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
        manufacturer="A4TECH",
        product="Bloody Receiver (spoof FD8A)",
        serial=args.serial,
    )
    # 先鼠后键，复合设备
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
