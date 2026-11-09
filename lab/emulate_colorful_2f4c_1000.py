# -*- coding: utf-8 -*-
"""
七彩虹主板灯控 spoof：2F4C:1000

参考 OpenRGB / iGameMBoard：
  - VID 0x2F4C PID 0x1000
  - HID IF：UsagePage FF00（占位）+ FF01（灯控，64B In/Out）

用法：
  python -u emulate_colorful_2f4c_1000.py
  usbip.exe list -r 127.0.0.1
  usbip.exe attach -r 127.0.0.1 -b 1-1
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from usbip.classes.device import HID
from usbip.classes.device.hid import PROTOCOL_NONE, SUBCLASS_NONE
from usbip.device import USBDevice
from usbip.transport import USBIP

VID = 0x2F4C
PID = 0x1000
RAW_LEN = 64
LOG = Path(__file__).with_name("emulate_colorful_2f4c_1000.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def vendor_hid_rd(usage_page_lo: int, usage: int = 0x01) -> bytes:
    """Vendor page, Usage, In+Out RAW_LEN bytes, no Report ID."""
    return bytes(
        [
            0x06,
            usage_page_lo,
            0xFF,  # Usage Page (Vendor)
            0x09,
            usage,  # Usage
            0xA1,
            0x01,  # Collection (Application)
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
            0x02,  # Input
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
            0x02,  # Output
            0xC0,
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--usb-serial", default="SPOOF2F4C100001")
    args = ap.parse_args()

    state: dict = {"last": bytes(RAW_LEN), "led": None}

    def on_set_report(rtype, rid, payload: bytes) -> None:
        log(f"[SET_REPORT t={rtype} id={rid}] {payload[:16].hex(' ')}")
        state["last"] = (payload + bytes(RAW_LEN))[:RAW_LEN]

    def on_get_report(rtype, rid, length: int) -> bytes:
        n = length or RAW_LEN
        log(f"[GET_REPORT t={rtype} id={rid} len={n}]")
        return (state["last"] + bytes(n))[:n]

    def on_out(payload: bytes) -> None:
        log(f"[OUT] {payload[:20].hex(' ')}")
        state["last"] = (payload + bytes(RAW_LEN))[:RAW_LEN]
        hid = state.get("led")
        if hid is not None:
            try:
                hid.send_report(state["last"])
            except Exception as e:
                log(f"[IN] send_report err: {e}")

    # IF0: FF00（部分板子标 X570-USBHID-LED）
    ff00 = HID(
        vendor_hid_rd(0x00),
        subclass=SUBCLASS_NONE,
        protocol=PROTOCOL_NONE,
        in_ep=0x81,
        in_mps=RAW_LEN,
        in_interval=1,
        out_ep=0x01,
        out_mps=RAW_LEN,
        out_interval=1,
        set_report=on_set_report,
        get_report=on_get_report,
        on_output=on_out,
    )
    # IF1: FF01 灯控主接口（对应真机 interface 2 一侧的 vendor page）
    ff01 = HID(
        vendor_hid_rd(0x01),
        subclass=SUBCLASS_NONE,
        protocol=PROTOCOL_NONE,
        in_ep=0x82,
        in_mps=RAW_LEN,
        in_interval=1,
        out_ep=0x02,
        out_mps=RAW_LEN,
        out_interval=1,
        set_report=on_set_report,
        get_report=on_get_report,
        on_output=on_out,
    )
    state["led"] = ff01

    dev = USBDevice(
        VID,
        PID,
        manufacturer="COLORFUL",
        product="COLORFUL ARGB Controller",
        serial=args.usb_serial,
    )
    dev.add(ff00)
    dev.add(ff01)

    LOG.write_text("", encoding="utf-8")
    log(f"serving {VID:04X}:{PID:04X} usb_serial={args.usb_serial}")
    log(r"hardware ID expect: USB\VID_2F4C&PID_1000")
    transport = USBIP(args.host, args.port)
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
