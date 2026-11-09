# -*- coding: utf-8 -*-
"""
雷柏 spoof：24AE:4080（缺口纯键盘）

AHUB 2.0 Game 静态清单未见 4080；描述符按网页/桌面 HUB 常见
  vendorId=0x24AE usagePage=0xFF00 usage=0x000E
先挂上让 A HUB 扫，确认认不认。
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from usbip.classes.device import HID
from usbip.classes.device.hid import (
    PROTOCOL_KEYBOARD,
    PROTOCOL_NONE,
    SUBCLASS_BOOT,
    SUBCLASS_NONE,
    keyboard_report_descriptor,
)
from usbip.device import USBDevice
from usbip.transport import USBIP

VID = 0x24AE
PID = 0x4080
RAW_LEN = 64
LOG = Path(__file__).with_name("emulate_rapoo_4080.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def vendor_ff00_000e_rd() -> bytes:
    """UsagePage FF00 / Usage 0x0E，In+Out RAW_LEN（无 Report ID）。"""
    return bytes(
        [
            0x06,
            0x00,
            0xFF,
            0x09,
            0x0E,
            0xA1,
            0x01,
            0x09,
            0x01,
            0x15,
            0x00,
            0x26,
            0xFF,
            0x00,
            0x75,
            0x08,
            0x95,
            RAW_LEN,
            0x81,
            0x02,
            0x09,
            0x02,
            0x15,
            0x00,
            0x26,
            0xFF,
            0x00,
            0x75,
            0x08,
            0x95,
            RAW_LEN,
            0x91,
            0x02,
            0xC0,
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--usb-serial", default="SPOOF4080000001")
    ap.add_argument("--no-keyboard", action="store_true")
    args = ap.parse_args()

    state = {"raw": None, "last": bytes(RAW_LEN)}

    def on_set_report(rtype, rid, payload: bytes) -> None:
        log(f"[SET_REPORT t={rtype} id={rid}] {payload[:16].hex(' ')}")
        state["last"] = (payload + bytes(RAW_LEN))[:RAW_LEN]

    def on_get_report(rtype, rid, length: int) -> bytes:
        n = length or RAW_LEN
        log(f"[GET_REPORT t={rtype} id={rid} len={n}]")
        return (state["last"] + bytes(n))[:n]

    def on_out(payload: bytes) -> None:
        log(f"[OUT] {payload[:16].hex(' ')}")
        state["last"] = (payload + bytes(RAW_LEN))[:RAW_LEN]
        hid = state["raw"]
        if hid is not None:
            try:
                hid.send_report(state["last"])
            except Exception as e:
                log(f"[IN] err: {e}")

    raw = HID(
        vendor_ff00_000e_rd(),
        subclass=SUBCLASS_NONE,
        protocol=PROTOCOL_NONE,
        in_ep=0x82,
        in_mps=RAW_LEN,
        in_interval=1,
        out_ep=0x01,
        out_mps=RAW_LEN,
        out_interval=1,
        set_report=on_set_report,
        get_report=on_get_report,
        on_output=on_out,
    )
    state["raw"] = raw

    dev = USBDevice(
        VID,
        PID,
        manufacturer="RAPOO",
        product="Rapoo Keyboard 4080",
        serial=args.usb_serial,
    )
    if not args.no_keyboard:
        kbd = HID(
            keyboard_report_descriptor(),
            subclass=SUBCLASS_BOOT,
            protocol=PROTOCOL_KEYBOARD,
            in_ep=0x81,
            in_mps=8,
            in_interval=10,
        )
        dev.add(kbd)
    dev.add(raw)

    LOG.write_text("", encoding="utf-8")
    log(f"serving {VID:04X}:{PID:04X}")
    log(r"expect USB\VID_24AE&PID_4080")
    transport = USBIP(args.host, args.port)
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
