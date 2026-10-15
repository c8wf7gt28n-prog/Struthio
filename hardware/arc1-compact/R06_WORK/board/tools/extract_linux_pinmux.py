#!/usr/bin/env python3
"""Extract the Allwinner D1/D1s/F133 pin-function table from Linux
drivers/pinctrl/sunxi/pinctrl-sun20i-d1.c (GPL-2.0; facts only are extracted).

Usage: extract_linux_pinmux.py pinctrl-sun20i-d1.c OUT.csv

Rows: pin, mux value, function name, signal comment (e.g. "CS0"). This is a
second, independent source for the F133 datasheet multiplex table. It covers
the whole D1 family; package bonding must come from the F133 pin table.
"""
import csv
import re
import sys


def main(src: str, dst: str) -> int:
    text = open(src, encoding="utf-8").read()
    blocks = re.split(r"SUNXI_PIN\(SUNXI_PINCTRL_PIN\(", text)[1:]
    rows = []
    for b in blocks:
        m = re.match(r"([A-Z]),\s*(\d+)\)", b)
        if not m:
            continue
        pin = f"P{m.group(1)}{m.group(2)}"
        for fm in re.finditer(r'SUNXI_FUNCTION\((0x[0-9a-f]+),\s*"([^"]+)"\)\s*,?\s*(?:/\*\s*([^*]*?)\s*\*/)?', b):
            rows.append({"pin": pin, "mux": int(fm.group(1), 16), "function": fm.group(2),
                         "signal": (fm.group(3) or "").strip()})
    if len(rows) < 300:
        print(f"only {len(rows)} function rows parsed; refusing", file=sys.stderr)
        return 1
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pin", "mux", "function", "signal"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} function rows to {dst}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
