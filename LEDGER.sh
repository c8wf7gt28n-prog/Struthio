#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/python ]]; then exec .venv/bin/python -m workbench.baseline "$@"; fi
exec "${LEDGER_PYTHON:-python3}" -m workbench.baseline "$@"
