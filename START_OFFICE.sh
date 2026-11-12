#!/usr/bin/env bash
# Graphite Office: an empty workspace in ~/Concern/Office with an Inbox,
# opened on the Office panel. Your other workspaces are not touched.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export ARC_LEDGER_EDITION=office ARC_LEDGER_OPEN="${ARC_LEDGER_OPEN:-office}"
if [[ -x .venv/bin/python ]]; then exec .venv/bin/python -m workbench.launch "$@"; fi
exec python3 -m workbench.launch "$@"
