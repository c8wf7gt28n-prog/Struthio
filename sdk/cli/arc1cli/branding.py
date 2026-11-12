"""Shared official ARC-1 identity for host developer tools (not device firmware)."""

import json
from pathlib import Path

from .core import SDK_ROOT, sha256_file

IDENTITY = SDK_ROOT / "branding" / "identity.json"

def inspect_brand(result):
    try:
        obj = json.loads(IDENTITY.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        result.fail("BRAND-001", "branding identity unavailable: %s" % e)
        return
    if obj.get("schema") != "arc1.branding/0.1":
        result.fail("BRAND-002", "unknown identity schema")
        return
    result.artifact(IDENTITY)
    for key, spec in obj["asset_usage"].items():
        p = IDENTITY.parent / spec["path"]
        if not p.is_file() or sha256_file(p) != spec["sha256"]:
            result.fail("BRAND-003", "official asset missing or hash changed: %s" % key)
        else:
            result.artifact(p)
    states = obj["lcd"]["states"]
    for state, rows in states.items():
        if len(rows) != 2 or any(len(r) > 16 or not r.isascii() for r in rows):
            result.fail("BRAND-004", "invalid 16x2 LCD text for %s" % state)
    result.extra["details"] = {
        "brand": obj["display_name"],
        "expanded_name": obj["expanded_name"],
        "lcd_states": states,
        "target_firmware_verified": False,
        "hardware_lcd_verified": False,
        "windows_native_tested": False
    }

def identity():
    """Load canonical identity metadata; callers must not infer hardware status."""
    return json.loads(IDENTITY.read_text(encoding="utf-8"))
