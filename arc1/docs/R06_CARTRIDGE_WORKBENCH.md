# ARC-1 Workbench R06 — developer specification (host evidence only)

## Interaction philosophy
- Human-facing interface: classic file manager directory and list navigation; editor follows conventional desktop app shortcuts, with orange Aqua visual styling and minimal wasted space.
- Machine-facing interface: structured JSON-lines protocol at `py -3 arc1 agent`, separate from the GUI. No arbitrary shell execution or physical flash writes.
- File management: double-click to open editable text, drag an internal file onto a project folder to copy; confirm before copying. External OS drag-and-drop needs the optional tkinterdnd2 library. Portable ZIP remains a fallback.

## Cartridge v0.1 experimental format
- ZIP `.arc1cart`, normalized paths, deterministic timestamps.
- One `arc1.game.json` manifest with schema `arc1.game-package/0.2` and only its enumerated `assets/*.sprite` entries.
- Validate SHA-256 of each asset; reject undeclared entries, traversal paths, duplicates, encrypted archives and files beyond host caps.
- Output contains **no target code**. Not flashable. No target USB runtime currently accepts it.
- This format is for early SDK asset-packaging validation and may change after real F133 USB and game-loader integration.

## Commands
```
py -3 arc1 cartridge package examples/hello_arc1 --output cartridges/hello_arc1.arc1cart
py -3 arc1 cartridge inspect cartridges/hello_arc1.arc1cart
py -3 arc1 cartridge stream cartridges/hello_arc1.arc1cart --frames 120 --bandwidth 2 --latency 10 --prefetch 12
py -3 arc1 agent
```
- To permit agents to package into the restricted cartridge shelf, start `py -3 arc1 agent --allow-writes`.
- Agent read requests include `cartridge.inspect` and `cartridge.stream`, using the `cartridges/` shelf only.

## Streaming model assumptions
- Each chunk completes after a fixed request latency plus transferred-byte duration at user-selected MiB/s.
- Asset bytes are consumed at a fixed rate per 16.67 ms synthetic frame; prefetch begins N frames before the timeline.
- A modeled stall occurs when the model's available bytes fall below the requested cumulative consumption at a frame boundary.
- No USB enumeration, actual mass storage, FAT32/exFAT, async driver, DMA, or measured bandwidth is involved. No picture/audio is rendered by this test.

## Installer
- Extract ZIP, then drag the extracted project to a user-owned location and double-click START_ARC1.cmd.
- Optional INSTALL_ARC1.cmd opens a Finder-inspired two-tile installer that copies into the current user's LOCALAPPDATA Programs and creates a Start Menu shortcut.
- The optional tkinterdnd2 dependency must be installed by the user for true external Explorer drop events; core Workbench and cartridge features run without it.
