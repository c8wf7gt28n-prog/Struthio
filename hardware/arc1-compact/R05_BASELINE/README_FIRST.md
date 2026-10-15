# ARC-1 Compact — development and Claude handoff R05

Prepared 14 October 2026. This package continues the owner-selected **F133-B +
T35F400C3 + BT820B**, with a built-in LVDS display and **64 + 128 + 128 MiB** of
private RAM. It now includes working host code, a transform RTL simulation and
executable engineering checks.

Upload the entire ZIP to Claude, or extract it for Claude Code. Paste
`CLAUDE_START_PROMPT.txt` as the starting instruction.

Read in this order:

1. `CLAUDE.md` and `OWNER_SELECTION.md` — current scope and authority.
2. `ARC1_Compact_Claude_Handoff_R05.md` or its Word version — results and next work.
3. `engineering/architecture.json`, `tasks.json`, `sources.json` — current decisions and task queue.
4. `VERIFY.md` and `verification/last_run/summary.json` — reproduction and actual results.
5. The component contracts and source under `protocol/`, `compute/`, `integration/`, `display/`, `memory/`, `system/`.

**R05 corrects R04's display porch interpretation.** Use
`display/compact_display.json`; R04's porch values are retained only as an invalid
regression fixture. The proposed 48 MHz / 1280 × 625 raster still calculates to
nominal 60 Hz. This is not a measured display result.

The host integration scene transforms/culls bounds; it does not draw pixels or
run the game. There is no complete SPI/BT820 driver, bootable F133 image, Efinity
project, Compact CAD or measured hardware performance. These are the next work.

The five supplied original attachments remain unchanged under
`reference/originals/`. Previous handoffs, research and Tabletop software logs
are historical evidence; the root R05 instructions govern Compact. Other chats
were not accessible from the supplied chat ID.

`SHA256SUMS` lists packaged files; `PACKAGE_CHECKS.md` explains archive checks.
Build outputs, proprietary EDA tools and downloaded third-party tool binaries
are excluded. Rebuild source using `VERIFY.md`.
