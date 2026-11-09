# -*- coding: utf-8 -*-
import hid

VID, PID = 0x3869, 0x63E1
ds = [d for d in hid.enumerate() if d.get("vendor_id") == VID and d.get("product_id") == PID]
print("count", len(ds))
for d in ds:
    print(
        f"  iface={d.get('interface_number')} up=0x{d.get('usage_page'):04X} "
        f"u=0x{d.get('usage'):04X} product={d.get('product_string')!r}"
    )
