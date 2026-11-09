# -*- coding: utf-8 -*-
"""对本机 1532:0A4E MI_05 发一条 Get charging status，验证 SET_REPORT/write 是否通。"""
from __future__ import annotations

import struct
import sys
import time

import hid

VID, PID = 0x1532, 0x0A4E


def pkt(cmd: int) -> bytes:
    body = bytes([cmd, 0, 0])
    hdr = bytes([0x02, 0x02, 0x60, 0x00, 0x00, 0x00]) + struct.pack("<I", len(body))
    buf = bytearray(64)
    buf[: len(hdr) + len(body)] = hdr + body
    return bytes(buf)


def main() -> None:
    devs = [d for d in hid.enumerate() if d.get("vendor_id") == VID and d.get("product_id") == PID]
    print("found", len(devs))
    for d in devs:
        print(
            f"  iface={d.get('interface_number')} up=0x{d.get('usage_page'):04X} "
            f"u=0x{d.get('usage'):04X} path={d.get('path')!r}"
        )
    if not devs:
        sys.exit(1)
    path = devs[0]["path"]
    h = hid.device()
    h.open_path(path)
    h.set_nonblocking(True)
    out = pkt(0x2A)
    print("write", out[:16].hex(" "))
    try:
        n = h.write(out)
        print("write returned", n)
    except Exception as e:
        print("write EXC", type(e), e)
        # 再试 send_feature_report / send_output_report 风格：有的封装要先带 report id 0
        try:
            n = h.send_feature_report(out)
            print("feature_report returned", n)
        except Exception as e2:
            print("feature EXC", e2)
    time.sleep(0.2)
    try:
        data = h.read(64, timeout_ms=500)
        print("read", bytes(data).hex(" ") if data else data)
    except Exception as e:
        print("read EXC", e)
    h.close()


if __name__ == "__main__":
    main()
