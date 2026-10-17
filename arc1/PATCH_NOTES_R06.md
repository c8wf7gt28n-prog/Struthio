# ARC-1 Workbench R06 / PASS 4 (host development)

## Human interface: orange Aqua, compact density
- Official branding preserved; header reduced from 93 px to 51 px. Tool strip and directory row also tightened.
- Source editor and file panes gain vertical room. The right-side boot diagnostic pane toggles with F9 or View > Toggle diagnostics.
- Standard menus, project tree, folder list, editable source, run console remain; no Win3.1 design regression.
- Within Workbench, a project file can be dragged onto an existing folder to **copy** it with confirmation. It never silently moves or overwrites.
- Optional external Windows Explorer file-drop integration is supported using `tkinterdnd2`/TkDND. Without it, the Cartridge > Import command provides the same verified cartridge-copy function. Windows shell integration has not been tested on Windows 11 yet.

## Game cartridges / SDK
- Added deterministic `.arc1cart` (ZIP format) host archive: `arc1.game.json` and manifest-listed assets, with per-asset SHA-256 checks and file path validation.
- `arc1 cartridge package`, `inspect`, and `stream` host commands. Output is explicitly not a console-executable format and requires a future target loader contract.
- USB-stream model simulates latency and bandwidth, prefetch and frame consumption, and returns a count of modeled stalls. It does not perform USB reads or verify 60 fps on a real system.
- `workbench.agent` adds cartridge.package (opt-in writes), cartridge.inspect and cartridge.stream (read only) with restricted paths.
- GUI adds Cartridge menu, a package action, an import/verification action, and a host stream test with JSON results in the build console.

## Windows deployment UX
- Added `INSTALL_ARC1.cmd` / `workbench.installer` for per-user `LOCALAPPDATA\\Programs\\ARC-1 Workbench` installation and Start Menu shortcut. No admin or registry edits.
- Installer accepts dragging the source application tile into My Apps, as well as a keyboard-accessible install button. The portable unzip-and-drag-folder workflow is always available.
- Windows installation has **not** been exercised on a Windows 11 host. Python 3.11+ with Tk is required. Real hardware flashing remains disabled.

## Tests and limitations
- Pass 4 host packaging integrity / deterministic reproduction / tamper rejection / path rejection / streaming-stall tests pass.
- R06 GUI smoke passed under Xvfb, including F9 diagnostics and staged firmware build.
- Existing firmware host test suite: 4 passed. Existing example game test suite: 4 passed. Both F133/D213 non-bootable linker smoke targets: PASS. Branding verification: PASS.
- Do not advertise `.arc1cart` as bootable, FPGA-ready, verified over physical USB, or a tested Windows 11 installer.

## Pass 5 recommended
- Versioned application/game binary container and target loader design, plus host-backed launch and visible game preview.
- Streaming stress tests with large synthetic media and varied storage latency, realistic contention, and backpressure. Reconcile with actual F133 USB host and hardware after bring-up.
- Improve Windows 11 qualification and optional Explorer drag/drop distribution (TkDND dependency or native drop adapter), and visual UI density/accessibility testing.
