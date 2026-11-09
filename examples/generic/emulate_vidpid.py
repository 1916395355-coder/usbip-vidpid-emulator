# -*- coding: utf-8 -*-
"""
Generic VID/PID composite (boot mouse + keyboard) for PnP / INF tests.

Usage:
  python -u emulate_vidpid.py --vid 09DA --pid FA45 --port 3250
  python -u emulate_vidpid.py --vid 046D --pid C08C --product "PnP test"
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

LOG = Path(__file__).with_name("emulate_vidpid.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_hex(s: str) -> int:
    s = s.strip().lower().replace("0x", "")
    return int(s, 16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vid", required=True, help="e.g. 09DA")
    ap.add_argument("--pid", required=True, help="e.g. FA45")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--manufacturer", default="A4TECH")
    ap.add_argument("--product", default="")
    ap.add_argument("--serial", default="")
    args = ap.parse_args()

    vid = parse_hex(args.vid)
    pid = parse_hex(args.pid)
    product = args.product or f"Spoof {vid:04X}:{pid:04X}"
    serial = args.serial or f"SP{vid:04X}{pid:04X}"

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
        vid,
        pid,
        manufacturer=args.manufacturer,
        product=product,
        serial=serial,
    )
    dev.add(mouse)
    dev.add(keyboard)

    transport = USBIP(args.host, args.port)
    log(
        f"serving composite mouse+keyboard "
        f"VID_{vid:04X}&PID_{pid:04X} on {args.host}:{args.port}"
    )
    log(f"attach: usbip -t {args.port} list -r 127.0.0.1 ; attach -b 1-1")
    log(f"预期: USB\\VID_{vid:04X}&PID_{pid:04X}")
    log("Ctrl+C 结束")
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
