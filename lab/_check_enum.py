import hid
ds = [d for d in hid.enumerate() if d.get("vendor_id") == 0x1532 and d.get("product_id") == 0x0A4E]
print("count", len(ds))
for d in ds:
    print(
        f"iface={d.get('interface_number')} up=0x{d.get('usage_page'):04X} "
        f"u=0x{d.get('usage'):04X} product={d.get('product_string')!r}"
    )
    print(" ", d.get("path"))
