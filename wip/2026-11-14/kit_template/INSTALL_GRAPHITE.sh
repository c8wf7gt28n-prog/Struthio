#!/usr/bin/env bash
# Two explicit install phases for an existing Debian 13 amd64 system.
set -euo pipefail
kit="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
    --plan|--system)
        [[ $# == 1 ]] || { echo 'Use --plan or --system without other arguments.' >&2; exit 2; }
        if [[ $1 == --plan ]]; then exec bash "$kit/PREPARE_DEBIAN.sh" --plan; fi
        exec bash "$kit/PREPARE_DEBIAN.sh"
        ;;
    '')
        [[ $EUID != 0 ]] || { echo 'Use --system from root, then install Graphite from your ordinary account.' >&2; exit 1; }
        command -v python3 >/dev/null || { echo 'Run the Debian package phase with --system first.' >&2; exit 1; }
        exec python3 "$kit/INSTALL_LS.py" --usb "$kit" \
            --target "$HOME/Applications/Graphite-0.2a13" --offline --system-ready --minimal-session --vulkan --calc
        ;;
    *)
        echo 'Usage: bash INSTALL_GRAPHITE.sh [--plan | --system]' >&2
        exit 2
        ;;
esac
