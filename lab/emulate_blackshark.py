# -*- coding: utf-8 -*-
"""
BlackShark V3 Pro Xbox USB spoof (1532:0A4E)

关键：真机 MI_05 无 Interrupt OUT，Synapse write 走 SET_REPORT。
此前我们加了 OUT 端点，Windows 能枚举，但 node-hid write 走中断 OUT，
在 usbip-win2 路径上 send failed。改回「仅 IN + RD 含 Output」，对齐真机。
"""
from __future__ import annotations

import argparse
import struct
import time
from pathlib import Path

from usbip.classes.device import HID
from usbip.device import USBDevice
from usbip.function import Interface
from usbip.transport import USBIP

VID = 0x1532
PID = 0x0A4E
COL04_LEN = 64
DEFAULT_SERIAL = b"HN2545D37700222"
LOG = Path(__file__).with_name("emulate_blackshark.log")


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def mi05_rd_col04() -> bytes:
    """UsagePage FF14 / Usage1 / In+Out 64B，无 Report ID。"""
    return bytes(
        [
            0x06,
            0x14,
            0xFF,
            0x09,
            0x01,
            0xA1,
            0x01,
            0x15,
            0x00,
            0x26,
            0xFF,
            0x00,
            0x75,
            0x08,
            0x95,
            0x40,
            0x09,
            0x01,
            0x81,
            0x02,  # Input
            0x09,
            0x01,
            0x91,
            0x02,  # Output（无 OUT EP → SET_REPORT）
            0xC0,
        ]
    )


class VendorStub(Interface):
    bInterfaceClass = 0xFF
    bInterfaceSubClass = 0x00
    bInterfaceProtocol = 0x00


def build_response(cmd: int, data: bytes, status: int = 1, flag: int = 1) -> bytes:
    body = bytes([cmd & 0xFF, status & 0xFF, flag & 0xFF]) + data
    hdr = bytes([0x02, 0x02, 0x60, 0x00, 0x00, 0x00]) + struct.pack("<I", len(body))
    pkt = bytearray(COL04_LEN)
    blob = hdr + body
    pkt[: len(blob)] = blob
    pkt[COL04_LEN - 2] = sum(blob) & 0xFF
    return bytes(pkt)


def handle_command(cmd: int, serial: bytes) -> bytes:
    if cmd == 0x2A:
        return build_response(0x2A, bytes([1]))
    if cmd == 0x21:
        return build_response(0x21, bytes([100]))
    if cmd == 0x00:
        return build_response(0x00, serial, status=1, flag=len(serial))
    if cmd == 0x01:
        return build_response(0x01, bytes([0]))
    log(f"[valkyrie] unknown cmd=0x{cmd:02X}")
    return build_response(cmd, bytes([0]))


def parse_cmd(payload: bytes, rid: int | None = None) -> int | None:
    """解析 AudioValkyrie。SET_REPORT 常剥掉首字节 report id，且第二字节可为 0x00/0x02。"""
    if not payload:
        return None
    buf = bytes(payload)
    # 若库把 report id 单独传出且 payload 已剥头，有时 rid 仍有用；这里优先按内容判断
    if rid and buf[0] != 0x02 and len(buf) >= 9 and buf[0] == 0x60:
        buf = bytes([rid & 0xFF]) + buf

    def _cmd_at_valkyrie(b: bytes, hdr0_at: int) -> int | None:
        # b[hdr0_at]=flags, b[hdr0_at+1]=0x60, size@+5, cmd@+9
        if len(b) < hdr0_at + 10:
            return None
        if b[hdr0_at + 1] != 0x60:
            return None
        return b[hdr0_at + 9]

    # 完整（含 report id 0x02）：02 XX 60 ...
    if len(buf) >= 12 and buf[0] == 0x02 and buf[2] == 0x60:
        return buf[10]
    # SET_REPORT 剥掉 0x02 后：XX 60 ...（Synapse 常用 XX=0x00）
    c = _cmd_at_valkyrie(buf, 0)
    if c is not None:
        return c
    # 短命令 [cmd,0,0,...]
    if len(buf) >= 3 and buf[1] == 0 and buf[2] == 0:
        return buf[0]
    return None


def build_out_probe(cmd: int) -> bytes:
    """构造与日志一致的主机→设备包，便于本机自测。"""
    body = bytes([cmd & 0xFF, 0x00, 0x00])
    hdr = bytes([0x02, 0x02, 0x60, 0x00, 0x00, 0x00]) + struct.pack("<I", len(body))
    pkt = bytearray(COL04_LEN)
    pkt[: len(hdr) + len(body)] = hdr + body
    return bytes(pkt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=3240)
    ap.add_argument("--serial", default=DEFAULT_SERIAL.decode())
    ap.add_argument("--usb-serial", default="SPOOF0A4E000003")
    args = ap.parse_args()
    serial = args.serial.encode("ascii", errors="replace")[:15]

    state = {"hid": None, "last": handle_command(0x21, serial)}

    def handle_host_out(payload: bytes, src: str, rid: int | None = None) -> None:
        log(f"[{src}] len={len(payload)} {payload[:20].hex(' ')}")
        cmd = parse_cmd(payload, rid=rid)
        if cmd is None:
            log(f"[{src}] parse fail")
            return
        resp = handle_command(cmd, serial)
        state["last"] = resp
        log(f"[IN] cmd=0x{cmd:02X} {resp[:20].hex(' ')}")
        hid = state["hid"]
        if hid is None:
            return
        try:
            hid.send_report(resp)
        except Exception as e:
            log(f"[IN] send_report err: {e}")

    def on_set_report(rtype, rid, payload: bytes) -> None:
        handle_host_out(payload, f"SET_REPORT t={rtype} id={rid}", rid=rid)

    def on_get_report(rtype, rid, length: int) -> bytes:
        resp = state["last"]
        n = length or COL04_LEN
        log(f"[GET_REPORT] t={rtype} id={rid} len={n}")
        return (resp + bytes(max(0, n - len(resp))))[:n]

    stubs = [VendorStub() for _ in range(5)]
    # 对齐真机：仅 Interrupt IN 0x84；Output 走 SET_REPORT
    control = HID(
        mi05_rd_col04(),
        in_ep=0x84,
        in_mps=64,
        in_interval=1,
        out_ep=None,
        set_report=on_set_report,
        get_report=on_get_report,
    )
    state["hid"] = control

    dev = USBDevice(
        VID,
        PID,
        manufacturer="Razer Inc",
        product="BlackShark V3 Pro Xbox USB",
        serial=args.usb_serial,
    )
    for s in stubs:
        dev.add(s)
    dev.add(control)

    LOG.write_text("", encoding="utf-8")
    log(f"serving {VID:04X}:{PID:04X} usb_serial={args.usb_serial}")
    log("MI_05: IN-only 0x84, Output via SET_REPORT (match real device)")
    transport = USBIP(args.host, args.port)
    dev.plug(via=transport)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
