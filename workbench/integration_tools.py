"""Registered local tools for the engineering register and Orange Book."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
from . import record_io as io


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("power", "vendor", "book"))
    p.add_argument("--root", type=Path, default=Path.cwd())
    a = p.parse_args(argv)
    try:
        if a.action == "power":
            from .engineering_register import analyze_power
            r = analyze_power(a.root)
            print(json.dumps({"status": "PASS", "analysis_outcome": r["outcome"], "target_status": "BLOCKED", "record_id": r["record_id"]}))
        elif a.action == "vendor":
            import vendor_kb as kb
            built = kb.build(a.root)
            k = kb.open_kb(a.root)
            try: fixtures = k.run_fixtures(kb.load_json(kb.kb_dir(a.root) / "fixtures.json"))
            finally: k.close()
            if not all(x["result"] == "PASS" for x in fixtures): raise ValueError("VENDOR_QUERY_FIXTURES_FAILED")
            r = {"status": "PASS", "created": time.time(), "built": built, "fixtures": fixtures, "target_status": "BLOCKED"}
            io.write_json(io.project_path(a.root, "build/vendor_kb/qualification.json", False), r)
            print(json.dumps(r))
        else:
            from .orange_book import export_book
            r = export_book(a.root)
            print(json.dumps({"status": "PASS" if r["pdf_state"] == "GENERATED" else "BLOCKED", "exports": r}))
            if r["pdf_state"] != "GENERATED": return 3
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": type(exc).__name__ + ": " + str(exc), "fabrication": "HOLD"}))
        return 1


if __name__ == "__main__": raise SystemExit(main())
