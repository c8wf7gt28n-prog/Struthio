# ARC-1 Workbench R07 — Pass 7: Host Game Shelf + Workspace Presets

**Evidence:** HOST_TEST and STATIC_CHECK only. No physical ARC-1 board used. No hardware deployment, real USB mass-storage driver, or on-device launcher exists.

## Implemented
- First executable *host-only* game launch workflow. Workbench verifies a `.arc1cart` asset archive using R06 integrity checks, matches its *exact* manifest bytes to a trusted local project under `examples/`, validates a freshly compiled SDK host binary using SHA-256 and the existing SDK build stamp, and launches only that local executable. No code is loaded or executed from the cartridge archive.
- New Game Shelf window for selecting the verified `hello_arc1` cartridge and running/stopping a bounded host simulation. The display shows actual PPM frames produced by the local C11 host game and labels every result **HOST SIMULATION**. It is a precomputed frame preview, not a real-time game engine.
- Launcher state machine: `IDLE`, `STARTING`, `RUNNING`, `COMPLETED`, `STOPPED`, `FAILED`. Named rejection reasons for missing/corrupt/mismatched cartridge, stale or missing host binary, invalid path and bad arguments. Cancel uses process termination. Per-run SHA-256 evidence and trace path are returned.
- Agent API parity: `launcher.list`, `launcher.launch_sim`, `launcher.status`, `launcher.stop_sim` share the `HostLauncher` implementation with the GUI. No arbitrary executable paths are accepted and no physical flash methods are present.
- Named Code, Cartridge, Debug workspace presets; pane visibility and practical heights, last source file and editing cursor saved to a per-user, atomically written configuration file. Configuration is bounded, not evaluated.
- Quick Open (Ctrl+P) and Command Palette (Ctrl+Shift+P) support existing allowlisted file/editor/build/workspace commands. F6 opens the launcher.
- Official ARC-1 orange Aqua identity and compact 51px masthead retained without changing the R06 back-end or official logo.

## Reproducibility / acceptance
- `python tests/test_pass7_launcher.py` verifies the real host executable, frame output, SHA records, stop handling, malformed archive rejection, path restrictions, layout persistence, and agent parity.
- `xvfb-run -a -s '-screen 0 1420x900x24' python tests/workbench_r07_smoke.py` verifies the actual UI, navigation, command palette, state changes and PPM preview.
- Native Windows 11 GUI, compiler and installer tests remain outstanding. The included Linux host binary is **not** a Windows executable; rebuild it with a compatible compiler on Windows before running the launcher.

## Explicit limitations
1. `.arc1cart` R06 v0.1 still contains the game manifest and assets only, **not** a self-running game or target executable. Launching requires a matching local source project and freshly built trusted host executable.
2. The current preview is non-interactive frame playback from the actual C11 host simulator. It is not continuous player-controlled gameplay or physically measured 60 fps.
3. No USB host/storage driver, D213/45F hardware renderer, target game loader, production launcher or fully bootable firmware exists yet.
4. R10 PCB fabrication is on HOLD. Device connection and NOR flash programming remain unavailable.

## Next gate: R08
Implement a reliable source-editor/file-manager workflow: split editor, multi-file navigation, safe Save As, find/replace, backup/recovery, source search and testable keyboard paths. Prototype Qt 6 / PySide6 only as a separately benchmarked alternative; do not rewrite the working back end without evidence.
