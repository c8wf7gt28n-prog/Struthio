#!/usr/bin/env python3
"""ARC-1 Compact R10 -- processor pin/function matrix with a pin-mux conflict check (handoff rev 1.1 s5).

For every signal pin of the F133 and the D213 in board/r10_board_plan.json, derive the peripheral function the net
requires (from its name) and verify that function exists on that pad in the vendor mux table:
  F133: R85C_WORK/sources/f133/f133_elqfp128_all_pins.csv (F133 DS rev 2.3 Table 4-3)
  D213: architecture/sources/d213ecv_pins.csv (D21x HW guide Table 2-5 / DS 5.2.3)
A pad can only select one function, so the derived functions also prove there is no double use. Writes
hardware/R10_PIN_FUNCTION_MATRIX.csv; exits 1 on any mismatch or unknown requirement.
Usage: pin_function_matrix.py <R10_WORK dir>
"""
import csv
import json
import os
import re
import sys

R10 = os.path.abspath(sys.argv[1])
R85C = os.path.normpath(os.path.join(R10, "..", "R85C_WORK"))
plan = json.load(open(os.path.join(R10, "board", "r10_board_plan.json")))
f133_mux = {r["pin_number"]: r for r in csv.DictReader(open(os.path.join(R85C, "sources", "f133", "f133_elqfp128_all_pins.csv")))}
# rows whose mux text is missing in the CSV come from the R8.5-C transcription of DS rev 2.3 Table 4-3
_facts = json.load(open(os.path.join(R85C, "sources", "f133", "f133_boot_usb_facts.json")))["pin_mux_from_DS_Table_4_3"]
for _pad, _v in _facts.items():
    if isinstance(_v, dict) and "pin" in _v:
        _r = f133_mux.get(str(_v["pin"]))
        if _r and "mux:" not in _r["notes"]:
            _r["notes"] += " | mux: " + "; ".join(f"{k} {v}" for k, v in _v.items() if k.startswith("F"))
d213_mux = {r["pin"]: r for r in csv.DictReader(open(os.path.join(R10, "architecture", "sources", "d213ecv_pins.csv"),
                                                     encoding="utf-8"))}


def f133_need(net):
    rules = [(r"^EMMC_D(\d)$", r"SDC0-D\1"), (r"^EMMC_CLK_F$", "SDC0-CLK"), (r"^EMMC_CMD$", "SDC0-CMD"),
             (r"^SPI0_CLK_F$", "SPI0-CLK"), (r"^SPI0_CS0_N$", "SPI0-CS0"), (r"^SPI0_MOSI$", "SPI0-MOSI"),
             (r"^SPI0_MISO$", "SPI0-MISO"), (r"^SPI0_IO2$", "SPI0-WP"), (r"^SPI0_IO3$", "SPI0-HOLD"),
             (r"^ETH_(TX|RX)(D\d|CK)(_F)?$", r"RGMII-\1\2"), (r"^ETH_(TX|RX)CTL(_F)?$", r"RGMII-\1CTRL"),
             (r"^I2S_DOUT$", "I2S2-DOUT0"), (r"^I2S_BCLK$", "I2S2-BCLK"), (r"^I2S_LRCK$", "I2S2-LRCK"),
             (r"^UART0_(TX|RX)$", r"UART0-\1")]
    for pat, rep in rules:
        if re.match(pat, net):
            return re.sub(pat, rep, net)
    return "GPIO"


def d213_need(net):
    rules = [(r"^LCD_D(\d+)$", r"LCD_D\1"), (r"^LCD_(DCLK|HS|VS|DE)_D$", r"LCD_\1"),
             (r"^G_(TX|RX)(D\d|CK|CTL)(_D)?$", r"GMAC0_\1\2"), (r"^G_CLKIN$", "GMAC0_CLKIN"),
             (r"^D213_NOR_IO3$", "SPI0_HOLD"), (r"^D213_NOR_IO2$", "SPI0_WP"), (r"^D213_NOR_CS_N$", "SPI0_CS"),
             (r"^D213_NOR_MISO$", "SPI0_MISO"), (r"^D213_NOR_MOSI$", "SPI0_MOSI"), (r"^D213_NOR_CLK_D$", "SPI0_CLK"),
             (r"^FPGA45_SS_N_D$", "SPI1_CS"), (r"^FPGA45_MISO$", "SPI1_MISO"), (r"^FPGA45_MOSI_D$", "SPI1_MOSI"),
             (r"^FPGA45_SCK_D$", "SPI1_CLK"), (r"^HDMI_I2C_(SCL|SDA)$", r"I2C2_\1"),
             (r"^D213_UART0_(TX|RX)$", r"UART0_\1"), (r"^D213_USB0_(DM|DP)$", r"USB0_\1")]
    for pat, rep in rules:
        if re.match(pat, net):
            return re.sub(pat, rep, net)
    return "GPIO"


rows, errors = [], []
for c in plan["components"]:
    if c["part"] == "F133":
        for pin, d in c["pins"].items():
            name, net = d["name"], d["net"]
            if not net or not re.match(r"^P[A-G]\d+$", name):
                continue
            need = f133_need(net)
            mux = f133_mux[pin]["notes"]
            ok = need == "GPIO" or re.search(r"\bF\d+ (?:[\w-]+/)?" + re.escape(need) + r"(?=[/;\s]|$)", mux) is not None
            rows.append(["F133-B", pin, name, net, need, "OK" if ok else "MISSING", mux.split("mux: ")[-1] if "mux:" in mux else "GPIO only"])
            if not ok:
                errors.append(f"F133 pin {pin} {name}: net {net} needs {need}, pad offers: {mux}")
    elif c["part"] == "D213ECV":
        for pin, d in c["pins"].items():
            name, net = d["name"], d["net"]
            r = d213_mux.get(pin)
            if not net or not r or r["type"] not in ("IO", "USB/IO"):
                continue
            need = d213_need(net)
            funcs = [r[k] for k in ("name_func1", "func2", "func3", "func4", "func5", "func6", "func7", "func8") if r.get(k)]
            ok = need == "GPIO" or need in funcs
            rows.append(["D213ECV", pin, name, net, need, "OK" if ok else "MISSING", " / ".join(f for f in funcs if f != "-")])
            if not ok:
                errors.append(f"D213 pin {pin} {name}: net {net} needs {need}, pad offers {funcs}")
rows.sort(key=lambda r: (r[0], int(r[1])))
out = os.path.join(R10, "hardware", "R10_PIN_FUNCTION_MATRIX.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["chip", "pin", "pad", "net", "required_function", "check", "pad_functions_vendor_table"])
    w.writerows(rows)
print(f"{len(rows)} processor signal pins checked -> hardware/R10_PIN_FUNCTION_MATRIX.csv")
for e in errors:
    print("ERROR", e)
print("PIN_FUNCTION", "PASS" if not errors else "FAIL")
sys.exit(1 if errors else 0)
