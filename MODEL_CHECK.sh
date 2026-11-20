#!/usr/bin/env bash
# Check her model on this machine (0.8.7): the model check kit, from the console.
#   ./MODEL_CHECK.sh --plan                         the stages and their estimated times; starts nothing
#   ./MODEL_CHECK.sh --model /path/to/model.gguf    the awake part, S0 to S5 (about 20 to 30 minutes, estimated)
#   ./MODEL_CHECK.sh --model ... --overnight        and S7: the full exam and the I05 arms (hours, on mains power)
# It writes for-sending/model-check-<date>.json and its .txt card in its run folder, and prints where.
set -euo pipefail
program_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$program_dir"
exec "${LEDGER_PYTHON:-python3}" -B -m workbench.model_check "$@"
