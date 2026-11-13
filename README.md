# Graphite 0.4.8 · The desk does, doubts, looks ahead, glows, and looks like itself

Graphite is a quiet workspace for ideas, research, documents and engineering work, with its AI beside the work. It runs on
one minimal Debian computer (a phone is optional access) and keeps everything on that computer unless you turn a service
on. Graphite is the public name of the workspace; its assistant's face is Stacy, and she speaks staC; before November 6, 2026 the program was called Ledger &
Slate, and folders, scripts, settings keys and internal names keep those earlier names for compatibility.

- **Start here** · [ThinkPad first install](docs/THINKPAD_FIRST_INSTALL.md) covers USB setup, the model-free first launch and the observed hardware.
- **Buttons** · an action is a boxed button and a word that only goes somewhere is underlined, so the interface is never mistaken for the work. The sheet, the PDF and the page of writing each have one row of tools, with what is needed now and then under **More ▾**; the keys at the foot of the Field are buttons.
- **The mouse first** · above whatever is open in the centre: **‹ Field**, Find, **−** **+**, Undo, Redo, Save, **Actions ▾**, always in the same place. In the Field **Z** shows the whole desk, the bars at the edges drag, and **⋯** on the sheet under the pointer shows what can be done with it.
- **Amber** · one amber halo marks where the keys go (the selected sheet, the page being read, or the writing line); what waits for you is lit at its mark, and Approve glows until it is pressed.
- **Green** · the pointer (the mark's two facets, aimed at 11 o'clock) is drawn in the desk's green and carries a little light over the Field; whatever it is over answers in green, and what is live glows. Amber stays for what is selected and what waits for you. The Clean desk keeps the green and drops the glow.
- **The mouse** · click a tile in the Field to open it in the centre; **‹ Field** under the centre comes back to the same tile; every key the Field shows can be clicked; a change that waits has an **Approve** button. Ask Stacy "set B3 to 300" and the change waits for your Approve with what it would move marked.
- **Every key** · press **?** in the Field for a card of every key. The doubt (X), the desk check (C) and the brief (B) open on a page over the work at your reading size; the doubt and the check step aside at the next key.
- **Look ahead** · with a sheet or a calculation selected in the Field, ask "what if B4 were 100?": the cell is set without changing anything, the wires are followed, and the Field marks everything that would move with what it would say (**Esc** clears).
- **The brief** · press **B** in the Field: the whole desk written up as one page, from the records and by no model; **G** keeps it as a page that knows when the desk has moved on.
- **Right-click** · on a sheet in the Field the menu cascades: What if › a number › a value to try; Doubt it › what Stacy finds, each row opening its evidence; Trace it › every step back and on; What can be done › the steps; Your words ›.
- **Your own words** · `word waits = field.read | pick waiting | select kind,title,state`, then `waits`, `waits | count`, `words`, `forget waits`: a staC line kept under a word of yours.
- **Doubt** · press **X** on a sheet in the Field: Stacy cross-examines it for what a plausible result may hide (an edited input, mixed conditions, one source, a check that cannot fail, a number recorded nowhere) and **D** offers the step that removes the doubt.
- **staC reads the desk** · `field.read | pick waiting | select kind,title,state`; `this` is the sheet selected in the Field; **T** traces a thing to its source; ask "what if B3 were 320?" about a calculation and nothing is changed.
- **Doing** · press **D** on a sheet in the Field for the steps the records offer (a read runs; a change waits for **G**, your go); **C** checks the desk and offers to settle what needs no decision of yours.
- **The shelf** · press **P** in the Field: every program and room in six fixed columns; Enter opens one.
- **The Field** · press **F9** (or Arrange → Field, or type `field` in the writing strip): the work in this workspace as sheets with the wires that say what feeds what. Arrow keys follow the wires, Enter opens the real page, Esc comes back. Stacy's rail shows the staC line for the selected sheet: **S** puts it in the writing strip, **Shift+Enter** runs it. **N** shows this computer's network the same way; **W** returns to the work. It is the first slice of the objects and instruments desktop (master specification, sections 70 to 72), new in 0.3. Right-click a sheet (or press the Menu key) for what can be done with it. Guide → What's New has the rest.
- **Visual baseline** · [Visual Pass 1 reference review](docs/BOSS_VISUAL_PASS_01_REVISION.md) compares the five owner references with the revised worksheet, PDF evidence review and research journal.
- **Halfway release** · [P08–P10](docs/BOSS_HALFWAY_P10.md) covers resident model handling, project collections and reviewed PDF tables that become sheets and reports.
- **Evidence preparation** · [Intelligent data arrangement P07](docs/INTELLIGENT_DATA_P07.md) covers source preparation, exact calculations and follow-up passages.
- **Resource scheduling** · [Traffic cop P06](docs/TRAFFIC_COP_P06.md) covers shared-memory admission, foreground turns and readable waiting reasons.
- **Hardware route:** read [ThinkPad / Vulkan P05](docs/THINKPAD_VULKAN_P05.md): the bundled Vulkan worker, hardware profile, launch defaults, actual backend readback and CPU fallback.
- **Current desk:** read [BOSS M1](docs/BOSS_M1.md): the new native interface, path, contextual commands and constructed chains.
- **Earlier guide:** read [the daily guide](docs/DAILY_GUIDE.md) (the desk, the cat and its programs list, the System menu, the
  writing line and its four modes, Log with its Events and Network streams, the right-click menu, documents, assignments, the
  Finder, Ingress and Egress, the local model, the game behind the mark).
- **Working on it:** read [RECORD_OF_DIRECTIONS.md](RECORD_OF_DIRECTIONS.md) first: the owner's directions, where the
  knowledge is, where things stand and how to continue.

The supplied Graphite 0.1 baseline has historical mechanical and offscreen evidence from the build container, and live trials of the small Qwen models
where the docs say so. The owner's ThinkPad, its display and inputs, and the owner's model file have not been tried yet;
nothing here claims they are accepted.

The BOSS upgrade implements P01–P10 of the twenty-pass campaign. Try **References → Read technical PDF → Review table** to make a sheet from a reviewed source. Open **Project Desk → Ask Stacy → Prepare evidence** to see matching project passages and exact results before a model turn. Live model and owner-host Vulkan qualification remain pending. P11 covers full native programs.

## Install

From the release volumes (`Graphite_0.4.8_part_NN.zip`, `RELEASE_PARTS.json` and `INSTALL_LS.py` in one folder, for
example a USB stick), as your ordinary Debian user:

```
python3 INSTALL_LS.py --usb . --target "$HOME/Applications/Graphite-0.4.8" --minimal-session --vulkan --plan
python3 INSTALL_LS.py --usb . --target "$HOME/Applications/Graphite-0.4.8" --minimal-session --vulkan --yes
```

`INSTALL_LS.py` is the Graphite installer (its file name is kept: scripts, tests and earlier notes call it). It verifies
every volume, restores the program into a new folder, installs the Debian prerequisites (with `--yes`, through sudo) and
the pinned Python dependencies, checks the runtime imports, the payload and the seed, and ends with one line that says
what actually happened. `--extract-only` verifies and restores without installing anything; `--offline` uses a prepared
cache only; `--public-manifest URL --manifest-sha256 HASH` installs from a published release. Every option and refusal is
explained in [docs/MINIMAL_DEBIAN_INSTALL_01.md](docs/MINIMAL_DEBIAN_INSTALL_01.md).

From an already extracted program folder:

```
bash INSTALL_DEBIAN.sh --quick            # asks before sudo; add --vulkan for Radeon dependencies, --minimal-session for the dedicated session, or other tool options as needed
bash INSTALL_LEDGER.sh --quick            # the runtime only, on a system that already has the prerequisites
```

Keep your previous program folder and every workspace; install a new release into a new folder. A local model is
optional: the daily guide says which small GGUF file to fetch and how to register it in the Brain room. No model file is
included.

## Start

```
bash START_MINIMAL_DEBIAN.sh   # from a Debian text login: the dedicated fullscreen session; prints "Graphite ended with status N" when you leave
bash START_OFFICE.sh           # from an existing desktop: the ordinary window on the Office workspace (~/Concern/Office)
```

Leave through the System menu (the pale Graphite symbol at the upper right) → Return to Debian, or Exit Graphite on an
existing desktop. The same menu's Log out, Restart and Shut down first save or set aside your work as leaving does, ask you
to confirm, and then ask the system's own logind (never sudo); without a login session they say they are unavailable. On Windows, `START_OFFICE.cmd` starts the same program after Python
and `requirements-qt.txt` are installed.

## Operator tools

```
bash LEDGER.sh doctor                 # inspects the installation; creates no workspace, starts nothing
bash LEDGER.sh doctor --self-test     # a disposable capture, restart, backup and restore round trip
bash LEDGER.sh doctor --qt-check      # the real window and capture widget, offscreen
bash LEDGER.sh baseline --out my-baseline.json
bash LEDGER.sh inventory
```

## Complete backups

Close Graphite before taking a backup. This includes ordinary workspace files and working copies; restore always writes
NEW folders and leaves existing work untouched:

```
bash LEDGER.sh backup create --root ~/Concern/Office --out ~/Graphite-backups/office
bash LEDGER.sh backup verify ~/Graphite-backups/office
bash LEDGER.sh backup restore ~/Graphite-backups/office --to ~/Concern/Office-restored
bash LEDGER.sh open --root ~/Concern/Office-restored --profile ~/Concern/Office-restored-profile
```

External originals and external model weights are not included; model files inside the workspace are left out unless
`--include-models` is given. Complete snapshots and no-replace publication target Linux. docs/STAGE1.md explains backup and
restore in full.

## Checks

```
python3 tools/check_release.py               # payload, seed and syntax; the live program against docs/GRAPHITE_0.1_REGISTRY.json; the privacy scan
python3 tools/check_release.py --self-test   # adds the focused tests_integrated modules, one module per child process
python3 tools/check_release.py --ui          # adds the offscreen Qt checks of the UI gate
python3 -m workbench.slate_checks --runtime
python3 -m workbench.continuing_checks --workers
python3 -m workbench.deployment_checks --ui
```

`tools/check_release.py` is the one entry for the release check (it runs `tools/check_hatch.py`). The registry record
`docs/GRAPHITE_0.1_REGISTRY.json` holds every operation's scope and argument-schema digest, the job tools, every setting
definition's digest and the adapters; `tools/record_registry.py` writes it from the live tree, and any difference is listed
in words. It submits no job, starts no model or worker, makes no provider request and invokes no native tool. A passing
check is integrity, not readiness or acceptance. Tests run one module at a time:
`python3 -B -m unittest tests_integrated.test_graphite` (tests_integrated has no `__init__.py`; do not use discover).

## Paired exchange, signed releases and deployment

Arrange → Exchange & deployment holds recipient-bound request and result pills, pinned mutual TLS 1.3, replay protection,
explicit signed offline release verification and recovery, reviewable launch files and optional read-only phone progress.
A received pill stays in quarantine until explicitly accepted; returned edits become a frozen working-copy proposal, and
originals still need separate owner publication. Nothing starts merely by opening the panel. Read docs/STAGE6.md before
pairing or updating. No publisher private key or default trust root is included.

## Packaging

```
python3 tools/package_graphite.py --dry-run                                     # what would be shipped; writes nothing
python3 tools/package_graphite.py OUT
python3 tools/package_release_parts.py OUT/Graphite_0.4.8_full.zip PARTS "Graphite 0.4.8"
```

Graphite's own code and documents are free software under the GNU General Public License, version 2 only (COPYING).
Stacy's artwork, the other project art, the names and the game copy are kept back (RIGHTS.md). Licences of bundled fonts,
runtimes and dependencies are in THIRD_PARTY_NOTICES.md; the pinned dependencies are the requirements-*.txt files.
