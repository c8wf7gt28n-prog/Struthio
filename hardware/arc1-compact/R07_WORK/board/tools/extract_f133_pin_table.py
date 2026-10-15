#!/usr/bin/env python3
"""Extract F133 Table 4-2 (pin characteristics) from `pdftotext -layout` output.

Usage: extract_f133_pin_table.py F133_datasheet.txt OUT.csv

Input: text of the Allwinner F133 Datasheet (the R05 source register URL,
cdn.semikey.com/.../4c5e315c6bb9cc2f9ecf223359e639c3.pdf, revision history up
to v1.4, 2021-12-09) produced by `pdftotext -layout`. The PDF is not
redistributed; record its SHA-256 next to the output.
Only GPIO rows (P<bank><n>) and their I/O power domain are extracted. The
result proves which GPIOs are bonded on the eLQFP128 package, nothing else.
"""
import csv
import re
import sys

ROW = re.compile(r"^\s*(\d{1,3})\s+(P[A-G]\d{1,2})\s+(I/O|I|O)\s+(\S+)\s+(\S+)\s+(\d+)\s+(VCC-[A-Z]+)\s*$")


def main(src: str, dst: str) -> int:
    rows = []
    with open(src, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = ROW.match(line)
            if m:
                rows.append({"pin_number": int(m.group(1)), "pin": m.group(2), "type": m.group(3),
                             "reset_state": m.group(4), "pull": m.group(5),
                             "default_drive_ma": int(m.group(6)), "power_domain": m.group(7)})
    seen = {}
    for r in rows:
        if r["pin"] in seen and seen[r["pin"]] != r:
            print(f"conflicting duplicate row for {r['pin']}", file=sys.stderr)
            return 1
        seen[r["pin"]] = r
    rows = sorted(seen.values(), key=lambda r: (r["pin"][1], int(r["pin"][2:])))
    if len(rows) < 60:
        print(f"only {len(rows)} GPIO rows parsed; refusing to write a partial table", file=sys.stderr)
        return 1
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} GPIO rows to {dst}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
