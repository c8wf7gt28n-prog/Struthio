# Getting started with Graphite 0.1

Graphite is the workspace and its AI under one name (before November 6, 2026: Ledger & Slate; folders, scripts and settings
keys keep the earlier names). This page is the first ten minutes. The daily guide (docs/DAILY_GUIDE.md) is the fuller
tour; the README says how to install, start, back up and check.

## Install and start

1. Install into a new folder and keep your previous program and every workspace: `python3 INSTALL_LS.py --usb . --target
   "$HOME/Applications/Graphite_0.1" --minimal-session --yes` from the release volumes, or `bash INSTALL_DEBIAN.sh --quick`
   in an extracted folder (it asks before sudo; `bash INSTALL_LEDGER.sh --quick` when the prerequisites are already there).
   Add `--math` for exact maths and the office round trip.
2. Close any earlier program and make a complete backup before opening an existing workspace (`bash LEDGER.sh backup create
   --root ~/Concern/Office --out ~/Graphite-backups/office`; restore always writes new folders).
3. Start: `bash START_MINIMAL_DEBIAN.sh` from a text login (the dedicated fullscreen session), or `bash START_OFFICE.sh`
   from an existing desktop.

## The first ten minutes

1. The window has five parts: the left column (Cabinet · Machine · Settings), the centre where the work opens, the right
   column (Operations and Graphite's face), the head (Graphite, the menu words, the CPU · GPU · RAM · TXT readings
   and the pale Graphite symbol, the System menu: Game, then Stop all jobs), and the typing strip at the bottom.
2. With nothing open the centre is the Finder: choose Today, a disk under Machine or a project folder on the left and the
   centre lists it. It looks and opens; it never changes files.
3. Drop a few files into `~/Concern/Office/Ingress` (or onto the Office) and receive them; Today counts what arrived.
4. The cat at the lower left opens the programs list (Space or Enter on it too). Documents in the list opens a page: write, select
   words and ask Stacy in the strip, `make these words bold`. Ctrl Z takes any change back.
5. On a page with quantities ask `add up the numbers on this page`: Graphite works it as an assignment you can watch, pause,
   resume and stop under its face.
6. A local model is optional. Menu → Configuration → Local model opens the Brain room; the daily guide names the small file
   to fetch.

## Working copies, Changes and continuing work

- Arrange → Changes: choose a project folder or ZIP, review the import list and accept its working copy. Edit or stage files
  or cells and freeze a proposal. Apply to the copy first; updating originals is a separate preview and owner action (close
  other programs writing those originals). Changes → Export working copy as new ZIP keeps a reviewed configuration; ZIP
  originals are never overwritten, and the copy and original have separate undo histories.
- Arrange → Continuing work: select an assignment and a profiled working copy delegated to Graphite, prepare a text read or
  draft, freeze the plan, review its calls and budgets, and authorize it once. If you include working-copy application, that
  exact application is part of the grant; publishing originals stays a separate Changes action. A finished result waits for
  review. Pause and revoke are always there; after Stop all jobs, resume global work explicitly and inspect or resume the
  affected order.
- Protected checks, parsers and model drafts stay paused until their actual worker profile qualifies
  (`bash INSTALL_DEBIAN.sh --workers`, then Continuing work → Worker protection, or `python3 -m workbench.continuing_checks
  --workers`). Unavailable isolation is a refusal, not a pass.
- Arrange → Exchange & deployment holds paired requests and results, offline release preview and inert launch files. Verify
  both full TLS-card fingerprints before pairing; returned edits are staged in Changes and reviewed. Use Offline updates
  only after confirming the real UTC clock and bootstrapping a publisher root yourself; no production publisher key is
  included. docs/STAGE6.md explains pairing, interruption, trust, clock rules and update recovery.
- Project Desk → Problem sheet keeps a durable question, explicit unknowns and the receipts of real source reads; Calculate
  there gives exact units and bounded symbolic and constraint tools (docs/INTEGRATED_I01.md and docs/INTEGRATED_I02.md).

## Checking the installation

`python3 tools/check_release.py` (with the installed Python, `.venv/bin/python`, when installed there) verifies the payload,
the seed and the live program against the recorded Graphite 0.1 registry; `--self-test` adds the focused tests one module at
a time. Exit 0 means every section passed: integrity, not readiness or acceptance. It starts no job, model, worker,
provider request or native tool. Worker qualification, real-model trials and the walkthrough on the owner's own display are
separate.
