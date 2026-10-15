# ARC-1 Compact — Claude continuation package R0.4

Prepared 14 October 2026 after the owner selected **F133-B + T35F400C3 + BT820B + a built-in screen**, with **64 + 128 + 128 MiB** private RAM pools.

Upload this entire ZIP to Claude, or extract it for Claude Code. Paste `CLAUDE_START_PROMPT.txt` as the starting instruction.

Read in this order:

1. `CLAUDE.md` — scope, authority and continuation rules.
2. `ARC1_Compact_Claude_Handoff_R04.md` or its Word version — selected design and next work.
3. `engineering/architecture.json`, `engineering/tasks.json`, `engineering/sources.json` — machine-readable decisions, task queue and sources.
4. `COVERAGE_AND_EVIDENCE.md` — what was reviewed and what evidence is missing.
5. Historical research and unchanged originals under `reference/` as needed.

The named screen is **Newhaven NHD-7.0-1024600AF-LSXP**, a working qualification candidate. Its proposed 48 MHz / 1280 × 625 raster calculates to 60 Hz; it has not been bench-tested here. Exact RAM SKUs, storage, orientation, power/audio and final pin allocation remain to be confirmed.

This package continues **Compact**, not the separate dual-T120 Tabletop R23. Historical Tabletop `CLAUDE.md` files stay inside their original ZIPs and do not govern Compact. The earlier recommendation’s open RAM language is superseded by this owner-selected RAM target; supporting part qualification remains open.

No hardware build, firmware/RTL implementation, Efinity run or physical benchmark is supplied by this handoff. The retained test logs concern historical Project House software. All included files are listed in `SHA256SUMS`; the original attachment hashes are separately recorded in `reference/originals_manifest.json`.
