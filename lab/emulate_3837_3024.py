# -*- coding: utf-8 -*-
"""
3837:3024 spoof（迈从 / MCHOSE HUB）

官网 connectDevice 白名单（index-CbwfU98r.js）要求：
  vendorId=14391 (0x3837) 且 productId∈{12324=0x3024, 12325=0x3025, ...}
  collections 命中：usagePage=1&usage=0  或  usagePage=65280(0xFF00)&usage=1
requestDevice filters：
  {vendorId:14391, productId:12324, usagePage:1, usage:0}
  {vendorId:14391, productId:12325, usagePage:65280, usage:1}

旧版仅 boot mouse(1/2)+keyboard(1/6)，Picker / 匹配器都认不出。

用法:
  python -u emulate_3837_3024.py
  E:\\USBip\\usbip.exe list -r 127.0.0.1
  E:\\USBip\\usbip.exe attach -r 127.0.0.1 -b 1-1
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from usbip.classes.device import HID
from usbip.classes.device.hid import (
    PROTOCOL_MOUSE,
    PROTOCOL_NONE,
    SUBCLASS_BOOT,
    SUBCLASS_NONE,
    mouse_report_descriptor,
)
from usbip.device import USBDevice
from usbip.transport import USBIP

VID = 0x3837
PID = 0x3024
RAW_LEN = 64
LOG = Path(__file__).with_name("emulate_3837_3024.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def gd_usage0_rd() -> bytes:
    """Generic Desktop / Usage 0 Application — 对齐 HUB filter usagePage:1,usage:0"""
    return bytes(
        [
            0x05,
            0x01,  # Usage Page (Generic Desktop)
            0x09,
            0x00,  # Usage (Undefined / 0)
            0xA1,
            0x01,  # Collection (Application)
            0x09,
            0x00,
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
            0x00,
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


def vendor_ff00_rd(usage: int = 0x01) -> bytes:
    """Vendor page 0xFF00 / Usage 1 — 对齐 HUB filter usagePage:65280,usage:1"""
    return bytes(
        [
            0x06,
            0x00,
            0xFF,  # Usage Page (Vendor 0xFF00)
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
    ap.add_argument("--serial", default="SPOOF3024000001")
    args = ap.parse_args()

    # IF0: GD usage 0 —— requestDevice / isSupport 主匹配
    gd0 = HID(
        gd_usage0_rd(),
        subclass=SUBCLASS_NONE,
        protocol=PROTOCOL_NONE,
        in_ep=0x81,
        in_mps=RAW_LEN,
        in_interval=1,
        out_ep=0x01,
        out_mps=RAW_LEN,
        out_interval=1,
    )
    # IF1: FF00 usage 1 —— 官方常与 3025 成对，matcher OR 条件
    vend = HID(
        vendor_ff00_rd(0x01),
        subclass=SUBCLASS_NONE,
        protocol=PROTOCOL_NONE,
        in_ep=0x82,
        in_mps=RAW_LEN,
        in_interval=1,
        out_ep=0x02,
        out_mps=RAW_LEN,
        out_interval=1,
    )
    # IF2: 普通鼠标，方便本机 PnP 仍有 Mouse 类
    mouse = HID(
        mouse_report_descriptor(),
        subclass=SUBCLASS_BOOT,
        protocol=PROTOCOL_MOUSE,
        in_ep=0x83,
        in_mps=8,
        in_interval=10,
    )

    dev = USBDevice(
        VID,
        PID,
        manufacturer="MCHOSE",
        product="MCHOSE Kit (spoof 3024)",
        serial=args.serial,
    )
    dev.add(gd0)
    dev.add(vend)
    dev.add(mouse)

    transport = USBIP(args.host, args.port)
    log(
        f"serving GD0+FF00+mouse "
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
