# -*- coding: utf-8 -*-
import re
from pathlib import Path

t = Path("_ez_iqunix.js").read_text(encoding="utf-8", errors="replace")

ids = sorted(set(re.findall(r"vendorId.:0x3869.productId.:(0x[0-9a-fA-F]+)", t)))
print("all 3869 productIds on ez.iqunix.com:", ids)

print("\n--- contexts for 0x7c18 ---")
for m in re.finditer(r".{0,80}0x7c18.{0,100}", t, flags=re.I):
    print(m.group(0))
    print("---")

print("\n--- contexts for EV63 ---")
for m in re.finditer(r".{0,40}EV63[^,]{0,20}.{0,120}", t):
    s = m.group(0)
    if "3869" in s or "productId" in s or "7c18" in s.lower() or "63e1" in s.lower():
        print(s[:200])
        print("---")
