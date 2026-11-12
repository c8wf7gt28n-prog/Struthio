#!/usr/bin/env bash
set -euo pipefail
program_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${LEDGER_PYTHON:-python3}" -B "$program_dir/tools/hatch_check.py" "$@"
