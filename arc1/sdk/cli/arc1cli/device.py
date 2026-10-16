"""`arc1 device detect` and `arc1 device flash`: the console's rear USB-C path.

R10 recovers a console through the F133 boot ROM's FEL USB mode on the rear
USB-C port, driven from a PC with the third-party `xfel` tool
(hardware/sources/r10: R10_CHANGE_ORDER_1_1.md §4; R08 RECOVERY_DOSSIER.md).

Nothing here writes to hardware:
- `detect` runs only `xfel version`, a read-only query, and only when xfel is installed.
- `flash` builds and checks a complete write plan (partition, fit, digest, exact
  xfel commands, SEC-004 checklist) and always ends NOT_AVAILABLE. Flashing stays
  disabled until FEL fall-through recovery is bench-proven (change-order item
  CO-4), a board is identified and the owner approves (spec SEC-004, §13.2).
"""

import csv
import shutil
from pathlib import Path

from .core import SDK_ROOT, UsageError, display_path, run_tool, sha256_bytes, sha256_file

NOR_MAP = SDK_ROOT / "hardware" / "sources" / "r10" / "R10_WORK" / "memory" / "R10_nor_partition.csv"
NOR_BYTES = 64 * 1024 * 1024
F133_FEL_CHIP_ID = "0x00185900"  # D1/F133 chip ID that `xfel version` reports (R08 RECOVERY_DOSSIER.md step 3)
DETECT_TIMEOUT_S = 10

# Why flashing is disabled. Each entry is a gate that must close before any write.
WRITE_GATES = [
    ("board_identity", "No identified ARC-1 board: R10 is on fabrication HOLD."),
    ("recovery_verified", "FEL fall-through recovery on rear USB-C is not bench-proven (R10 change order CO-4)."),
    ("owner_approval", "No recorded owner approval for a board-affecting operation (spec SEC-004)."),
]


def partitions():
    with open(NOR_MAP, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append({"id": r["id"], "name": r["partition"], "offset": int(r["offset"], 16),
                    "size": int(r["size_bytes"]), "protection": r["protection"],
                    "written_by": r["written_by"], "contents": r["contents"], "status": r["status"],
                    "boot_rom_reads": r["boot_rom_reads"] == "yes"})
    return out


def locked(part):
    return part["protection"].startswith("locked")


def plan(partition_id, image_path):
    """Returns (plan dict, list of (code, message) problems). Never touches hardware."""
    parts = {p["id"]: p for p in partitions()}
    if partition_id not in parts:
        raise UsageError("unknown partition %r; choose one of %s" % (partition_id, ", ".join(parts)))
    part = parts[partition_id]
    problems = []
    image = Path(image_path).resolve()
    if not image.is_file():
        raise UsageError("image not found: %s" % image_path)
    size = image.stat().st_size
    digest = sha256_file(image)
    if size == 0:
        problems.append(("FLASH-FIT", "image is empty"))
    if size > part["size"]:
        problems.append(("FLASH-FIT", "image is %d bytes; partition %s holds %d" % (size, part["id"], part["size"])))
    if locked(part):
        problems.append(("SEC-004", "partition %s is %s and written by '%s' only; the SDK will not plan a write to it"
                         % (part["id"], part["protection"], part["written_by"])))
    if part["offset"] + part["size"] > NOR_BYTES:
        problems.append(("FLASH-FIT", "partition ends beyond the 64 MiB NOR"))
    name = image.name
    off = "0x%08X" % part["offset"]
    commands = [
        "xfel version                         # must report chip ID %s" % F133_FEL_CHIP_ID,
        "xfel spinor                          # must report the 64 MiB system NOR",
        "xfel spinor read %s %d before.bin   # back up the slot first" % (off, part["size"]),
        "xfel spinor write %s %s" % (off, name),
        "xfel spinor read %s %d readback.bin" % (off, size),
        "sha256sum %s readback.bin           # both must equal %s" % (name, digest),
    ]
    return {
        "operation": "write %s (%d bytes) to NOR partition %s '%s' at %s" % (name, size, part["id"], part["name"], off),
        "partition": part,
        "image": {"path": display_path(image), "bytes": size, "sha256": digest},
        "fits": size <= part["size"],
        "fill_percent": round(100.0 * size / part["size"], 1) if part["size"] else None,
        "transport": "F133 FEL over rear USB-C (xfel); command sequence UNVERIFIED on R10",
        "commands": commands,
        "risks": [
            "A failed write to a boot-path partition can leave the console unable to boot until FEL recovery works.",
            "The xfel SPI NOR sequence was written for R08 (32 MiB NOR) and is unverified on the R10 64 MiB NOR.",
        ] + (["This partition is read by the F133 boot ROM."] if part["boot_rom_reads"] else []),
        "rollback": "Not ready: rollback relies on FEL fall-through, which is bench-OPEN (CO-4).",
        "gates": [{"gate": g, "state": "OPEN", "reason": r} for g, r in WRITE_GATES],
        "write_enabled": False,
    }, problems


def flash(result, partition_id, image_path):
    result.command = "arc1 device flash --partition %s --image %s" % (partition_id, Path(image_path).name)
    p, problems = plan(partition_id, image_path)
    result.input_digest = sha256_bytes(("%s\n%s" % (partition_id, p["image"]["sha256"])).encode())
    for code, msg in problems:
        result.fail(code, msg)
    if result.verdict == "PASS":
        # The plan is valid; the write itself is not available.
        result.verdict = "NOT_AVAILABLE"
        result.failures.append({"code": "SEC-004", "message": "write disabled. " +
                                " ".join(r for _, r in WRITE_GATES)})
    result.warn("Plan only: nothing was written and no device was contacted")
    result.extra["details"] = {"plan": p}


def detect(result):
    result.command = "arc1 device detect"
    xfel = shutil.which("xfel")
    if not xfel:
        result.verdict = "NOT_AVAILABLE"
        result.failures.append({"code": "CLI-002", "message":
                                "xfel is not installed; it is the PC-side FEL tool for the rear USB-C port"})
        result.extra["details"] = {"xfel": None, "fel_device": None}
        return
    code, out = run_tool([xfel, "version"], SDK_ROOT, DETECT_TIMEOUT_S)
    text = out.strip()
    answered = code == 0 and bool(text)
    result.extra["details"] = {"xfel": xfel, "exit": code, "output": text[-500:],
                               "fel_device": answered, "f133_chip_id_seen": F133_FEL_CHIP_ID.lower() in text.lower()}
    if not answered:
        result.verdict = "NOT_AVAILABLE"
        result.failures.append({"code": "CLI-002", "message": "no FEL device answered `xfel version`"})
        return
    result.warn("A FEL device answered. This is not board identification and proves nothing about the rest of the board.")
    if F133_FEL_CHIP_ID.lower() not in text.lower():
        result.warn("Reported chip ID is not the D1/F133 ID %s" % F133_FEL_CHIP_ID)
