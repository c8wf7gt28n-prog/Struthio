# Getting started with Graphite 1.0

Graphite is the whole desktop and its assistant, Kasandra (Kas), under one name (before November 6, 2026: Ledger & Slate;
folders, scripts and settings keys keep the earlier names). This page is the first ten minutes. Guide ▸ The Living Desktop
is the tour of the window, Guide ▸ Kasandra, the Ghost in the Shell is hers, and Guide ▸ Your First Evening with 1.0 is the
acceptance evening on the ThinkPad.

*Built, not tested: by the owner's rule nothing in 1.0 has been through a test, and nothing of it has run on the ThinkPad
yet. The first real proof is that evening.*

## Install and start

1. On the ThinkPad, from the kit: the Debian packages first, as root (`bash INSTALL_GRAPHITE.sh --plan` to preview, then
   `bash INSTALL_GRAPHITE.sh --system`), log out and log in again, then `bash INSTALL_GRAPHITE.sh` from your ordinary
   account. Graphite always installs into a new folder; your earlier folders and every workspace stay as they are.
   docs/THINKPAD_FIRST_INSTALL.md has the details, and docs/ACCEPTANCE_1.0.md the evening.
2. Make a complete backup before opening an existing workspace in a new version (`bash LEDGER.sh backup create --root
   ~/Concern/Office --out ~/Graphite-backups/office`; restore always writes new folders).
3. Start: `bash START_MINIMAL_DEBIAN.sh` from a text login (the dedicated session, where Graphite is the whole desktop), or
   `bash START_OFFICE.sh` from another desktop.

## The first ten minutes

1. **The window.** HALT upper left; the menus across the head (File, Edit, View, Go, Tools, Help; View ▸ Details pane, or
   Alt+P, shows the chosen thing at the right of the centre); Apps ⊕ upper right. On the left the tabs Files, Machine and Settings, with DELETE at their foot; the board in the
   centre; Kasandra's column on the right; at the foot Line · Terminal · Search · Web · Log, the writing line and the meters
   CPU GPU RAM TXT NET. In the dedicated session a slim dock across the top holds Graphite and your app windows.
2. **Files** starts at "This computer /" with Home open. Select a file and it becomes the focus of the board, with what it
   is connected to around it: solid wires are recorded, dashed ones only possible and "not verified". A double-click opens
   it in the centre; use Save and Return to come back to the same board.
3. **Apps** lists what is installed on this computer. Open one: its window appears in the dock, and one press there brings
   it forward. Right-click a file for Open with.
4. **The Machine tab** reads the computer itself: USB drives (eject safely), the battery, the network and Wi-Fi, sound and
   screens. Where a service is missing it says so, and why.
5. **Ask Kasandra in her column**: the ask line at the foot of her column, with its send arrow. With no model she answers
   what your records can answer and plans from them; words typed in Line at the foot are offered to her with Ask
   Kasandra →. Every change of hers waits for your word or a grant you gave, and is done only when it is verified.
6. **Try Rail Demo** (Guide ▸ Try Rail Demo): an invented 12 V rail, built in a new folder of its own and opened in a
   window of its own. Nothing of it reaches your workspace.
7. **Her model is optional.** The Brain room (the GPU meter's card at the foot) ▸ Add file. The ThinkPad page names the
   file and its checksum.
8. **HALT** stops all of her work at once and nothing else; it reads RESUME while held, and RESUME restarts nothing by
   itself.
9. **Leaving:** the session group at the foot of the Work menu reads Lock, Suspend, Log out, Restart, Shut down, Return to
   Debian. Before you leave, Graphite names the apps still open and asks each to close politely.

## The older rooms, still there

- Go ▸ Changes: a reviewed working copy of a project folder or ZIP; changes apply to the copy first, and updating the
  originals is a separate preview and your own action. ZIP originals are never overwritten.
- Go ▸ Continuing work: an assignment delegated to Graphite on a profiled working copy, under a plan you review and
  authorise once; pause and revoke are always there. After Stop all jobs, resume global work explicitly.
- Go ▸ Exchange & deployment: paired requests and results, offline release preview and inert launch files
  (docs/STAGE6.md explains pairing, interruption, trust, clock rules and update recovery).
- Project Desk ▸ Problem sheet: a durable question, explicit unknowns and the receipts of real source reads; Calculate
  there gives exact units and bounded symbolic and constraint tools (docs/INTEGRATED_I01.md and docs/INTEGRATED_I02.md).
- Go ▸ Field: the whole desk as sheets with what feeds what (the board's Whole desk shows it too).

## Checking the installation

`python3 tools/check_release.py` (with the installed Python, `.venv/bin/python`, when installed there) verifies the payload,
the seed and the live program against the recorded Graphite 0.1 registry; `--self-test` adds the focused tests one module at
a time. Exit 0 means every section passed: integrity, not readiness or acceptance. It starts no job, model, worker,
provider request or native tool. The model check (the Brain room, or `MODEL_CHECK.sh`) and the acceptance evening on the
owner's own display are separate.
