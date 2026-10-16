"""Pin lists for hardware-manifest links, derived from the vendored R10 interface table.

The table (hardware/sources/r10/R10_WORK/architecture/R10_interface_matrix.csv) is
the R10 handoff's generated pin plan. `arc1 hw inspect` and the SDK tests use this
module to prove that every pin list in arc1-r10.hw.json is exactly what the table
says, so a manifest edit cannot drift from its cited source.

    python3 hardware/tools/r10_links.py            # print the pin list of every selected option
"""

import csv
import sys
from pathlib import Path

TABLE = Path(__file__).resolve().parents[1] / "sources" / "r10" / "R10_WORK" / "architecture" / "R10_interface_matrix.csv"

# manifest link id -> (table "link", table "option")
SELECTED = {
    "f133_fpga12_rgmii": ("F133<->12F", "RGMII (R10 4)"),
    "d213_gpu45_rgmii": ("D213<->45F", "B: GMAC0 RGMII on PE (SELECTED, decision D1)"),
    "f133_d213_usb": ("F133<->D213", "USB 2.0 HS (R10 4, preferred)"),
    "d213_hdmi_rgb": ("D213->video", "RGB888 to ADI ADV7513 HDMI transmitter (SELECTED, decision D8)"),
    "f133_hdmi_i2s": ("F133->HDMI audio", "I2S2 stereo PCM to ADV7513 (SELECTED, decision D8)"),
}


def rows(table=TABLE):
    with open(table, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pin_line(r):
    return "%s %s %s/%s %s -> %s %s/%s %s" % (
        r["signal"], r["chip_a"], r["a_pin"], r["a_pad"], r["a_function"],
        r["chip_b"], r["b_pin"], r["b_pad"], r["b_function"])


def pins_for(link_id, table=TABLE):
    link, option = SELECTED[link_id]
    out = [pin_line(r) for r in rows(table) if r["link"] == link and r["option"] == option]
    if not out:
        raise KeyError("no rows for %s / %s in %s" % (link, option, table))
    return out


def status_for(link_id, table=TABLE):
    link, option = SELECTED[link_id]
    return sorted({r["status"] for r in rows(table) if r["link"] == link and r["option"] == option})


if __name__ == "__main__":
    for lid in SELECTED:
        print("%s  [%s]" % (lid, "; ".join(status_for(lid))))
        for line in pins_for(lid):
            print("    " + line)
    sys.exit(0)
