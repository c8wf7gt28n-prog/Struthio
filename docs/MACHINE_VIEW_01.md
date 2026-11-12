# MACHINE VIEW 01 · the left column's machine and work navigator

HATCH DESKTOP-01, work item WI-4. Requirements NV01, NV02, NV03 (spec §5), the context line of HT02, the mechanical
steps of AC10. Date: November 5, 2026. Nothing in this document is owner-host acceptance: every observation quoted here
was read on the development container, and the readers describe whatever machine Ledger runs on.

## What the owner sees

The left column now carries three views behind one switch bar, `Cabinet · Machine · Settings` (three pink action words;
the current one is set in weight with a pink rule under it, so the state is not said by colour alone). Above the switch
bar, in every view, sits the **machine strip**: one line, refreshed every 2 s, reading

    <processor> · RAM <used>/<total> · <free of the workspace mount> free · net up|down

for example `AMD Ryzen 7 PRO 5850U · RAM 9.8 GiB/62.7 GiB · 412.0 GiB free · net up`. Each value that cannot be read
is the word `unavailable` in its place; nothing is animated or estimated. The strip's tooltip and accessible description
name the sources (`/proc/cpuinfo`, `/proc/meminfo`, `os.statvfs` of the workspace mount, `/sys/class/net` operstate and
carrier) and the time of the sample. The strip elides to the column; it never widens it (its minimum width is 0).

The **Machine view** is a tree with a details pane under it:

    Machine
      Processor            model · cores · threads; logical processors; load average
      Memory               RAM in use of total; swap; a cgroup ceiling when one applies
      Storage              Ledger program folder and Workspace (path, mount, free); disks; mounted filesystems
      Connections          each interface: kind (ethernet, wireless, virtual, tunnel, loopback) and link state
      Devices              USB devices; input devices; display connectors
      Installed tools      the catalogue's native families: found on PATH or not, pinned archive verified or not
    Work
      <each project>       the cabinet's own project identities (project:<id>), pink links
    Settings               switches the column to the settings hierarchy

Choosing a row writes its words into the details pane: the label, `Observed HH:MM:SS · source <path>` (or the honest
state and its reason), then the observed values as words (bytes as sizes, flags as yes/no). Choosing a Work row selects
that very identity in the cabinet and opens its record room in the centre; choosing Settings shows the settings hierarchy
in this column and the editor in the centre. `Refresh machine view` re-reads everything; the page also re-reads itself
when shown after 30 s. Trash keeps its fixed place at the foot of the column, below the stack, outside every scroll
area; Import and Export stay as the cabinet's directional words above the tree (NV03). This file touched none of them.

## Honesty rules (NV01)

- Sources are `/proc`, `/sys` and `os.statvfs` only. No subprocess, no network, no `lspci`, `lsusb`, `ip` or `df`.
- Every item carries `source` and `sampled_at`. A source that is not present or unreadable yields an `UNAVAILABLE`
  state with the path and reason in words (`not present: /sys/bus/usb/devices`), never a blank or a guess.
- A section with nothing to list is a leaf (`Devices · none detected`, `Connections · unavailable`) whose details say
  why; no empty hierarchy level is shown. A bounded list says so (`· bounded`, `PARTIAL`).
- Addresses are not read: an interface is named by kind and link state only (`addresses: NOT_READ`).
- Installed tools are presence only: `shutil.which` for the catalogue's executables, the pinned-archive hash for the
  llama.cpp runtime and the Python WASI runtime. No tool is started; versions stay unmeasured; qualification stays
  `not assessed on this host` exactly as Hatch says it.
- The result's `basis` is `CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION`. The ARC project hardware (F133, D213,
  FPGA45, FPGA12, NOR, PCB) remains in `workbench/hardware_nav.py` under Work / Project; the machine readers never
  describe it, and the Machine tree never lists it. Physical and project views are therefore distinguishable by
  construction (AC10 pass condition, mechanical part).

## Sort rule (spec §5 "alphabetize comparable siblings with a documented rule")

Comparable siblings (disks, mounts, interfaces, USB, input and display devices, tools, projects) are ordered by the
natural key of their label: digit runs compare by value, letters case-folded, ties by id (`nvme0n1p2` before
`nvme0n1p10`; `eth0`, `lo`, `wlan0`; `Icarus Verilog` before `KiBot` before `KiCad`). Descriptive lines keep their stated
order: the Processor and Memory rows (identity, count, load; RAM, swap, ceiling) and the two Ledger paths at the head of
Storage, followed by disks and then mounts, each group natural. The three roots `Machine`, `Work`, `Settings` and the six
machine sections keep the schematic's order (physical to peripheral) rather than an alphabetical one; each section's
`order` field states its rule.

## Bounds

| list | bound |
|---|---|
| mounts, interfaces, USB devices, input devices (each) | 64 |
| disks | 32 |
| display connectors | 16 |
| partitions per disk | 16 |
| any word | 160 characters |
| bytes read from one `/proc` file | 256 KiB |

A whole `ledger.machine` answer stayed under 20 KB on the development container and is asserted under 512 KiB in
`tests_integrated/test_machine.py` for a fixture host with 70 interfaces and 100 input devices.

Storage excludes `loop*`, `ram*` and `zram*` block devices (pseudo or memory-backed, not storage) and lists mounts whose
device is under `/dev/` other than loop devices, plus whichever mount holds the program folder or the workspace even
when it is not device-backed (an overlay root in a container, for instance). Those two mounts are marked
`holds the program folder` / `holds the workspace`. Mountpoints are decoded from their octal escapes (`\040`).

## The operation `ledger.machine` (the one recorded operation addition of DESKTOP-01)

- Module `workbench/machine_overview.py`, the FIELDS / SCOPES / dispatch pattern every read module uses.
- Scope `read`. Arguments: optional `section` ∈ `processor, memory, storage, connections, devices, tools`.
- Answer: `schema ledger.machine/1`, `sampled_at`, `basis`, `host` (kernel release and host name from
  `/proc/sys/kernel`), `program_folder`, `workspace`, `sections[]` (id, title, state, items[], count, sources, notes,
  partial, order, sampled_at), `sources`, `limits`, `sort_rule`, `distinct_from`, and the counters
  `model_calls = network_calls = native_invocations = subprocesses = 0`.
- Item: `id, label, kind, state (OBSERVED | PARTIAL | UNAVAILABLE), source, sampled_at, values{}, reason?`.
- Registration: `workbench/engineering_kernel.py` imports the module (one line), merges `machine_overview.SCOPES` into
  `CAPABILITIES` (one line) and routes `op in machine_overview.FIELDS` in `Kernel._dispatch` (one line);
  `workbench/engineering_cli.py` merges `MACHINE_FIELDS` into `schemas()` (two lines). The kernel keeps three explicit
  tables for an operation (scopes, schemas, dispatch), so a bare import could not register it; `stacy_foundation.
  handler_map()` finds the module through the import as `workbench/machine_overview.py · dispatch ·
  DECLARED_FIELDS_ROUTE`. Earlier `ledger.*` reads (`ledger.explore`, `ledger.operations`, `ledger.cabinet`) were
  folded into `ledger_control.py`; that file belongs to WI-3 in this pass, so the registration went through the kernel
  tables instead. No second dispatcher, scheduler or store.
- Registry readback (`workbench.doctor.inventory()`): 691 operations; the 690 SERVICE-01 rows byte-identical; the 112
  job tools identical; schema digest `3976b8bc94370a1d91b915cade233ab29afabad2e29c69950452f634ca20b786` with ledger.machine alone, `e3523d01aef045f30605085ab1e8322a2b32f0d387de6dcb6248c385c23164f0` in the WORKSHOP-01 registry of 698 operations (baseline
  `9b28255cf4cd31117ece3edada8a737b569e9de996cbb32836e3b1040f92e1a1`). `tools/check_hatch.py` will say
  `ADDITIONS_RECORDED` once `HATCH_WORKSHOP_01_RESULT.json` lists `ledger.machine` under `added_public_operations`;
  until then it says the addition is unrecorded, which is the truth.
- Privacy note for the integrator: `ledger.machine` describes the host. It should join `stacy_control.CLOUD_PRIVATE`
  (beside `ledger.explore`) so an external provider is never handed it, and `activity.OBSERVER_OPERATIONS` so the
  Machine view's reads do not fill the activity journal. Both files are outside WI-4's ownership; proposed, not done.

## The switch and the session

`settings_qt.SettingsNavigator.show_view('cabinet' | 'settings' | 'machine')` drives the stack; the existing
`show(on)` keeps its meaning (on → settings, off → cabinet) for every caller in `navigation_qt`, `control_qt` and
`cabinet_qt`. `settings_navigation.mode` now takes the third word `machine`: WI-1 widened the loader
(`session.NAVIGATION_MODES = ('cabinet', 'settings', 'machine')`), so the chosen view is saved and the Machine view
returns at start exactly as Settings does. `settings_qt.PERSIST_MACHINE_MODE` (True) is the one switch to write
`cabinet` instead should a loader without the word ever have to read the file. The Qt check writes the mode and reads
it back through `Session.load`.

The machine strip is created by the navigator and inserted above the switch bar
(`box.insertWidget(0, strip)`), so it is present in all three views and independent of them (NV01: selection and
navigation never erase machine visibility). It reads `host_observations.memory()` (the same source as the right-column
RAM monitor), `machine_overview.cpu_model()` (cached a minute), `machine_overview.space(workspace)` and
`machine_overview.network_up()`; the whole tick is a handful of small file reads and one `statvfs`.

## V-24

The Settings filter (`QLineEdit#SettingsFilter`) is now the same yellow passage as the cabinet filter (background
`#f8edc9`, no border, bottom rule on focus, selection `#ecd7d5`); the check measures the share of its pixels in that
colour.

## Decisions taken (PD04)

1. Registration through the kernel tables rather than one import line or `ledger_control.py` (above). NV01/CM02.
2. Six machine sections in the schematic's order; natural order inside them; the Ledger paths first in Storage. §5.
3. `zram` excluded with `loop` and `ram` (memory, not storage). NV01.
4. Sizes in binary units labelled GiB/MiB/TiB, so a 64 GB module reads 62.7 GiB and nothing is rounded up. NV01.
5. Empty sections are leaves with a state word, not parents of a placeholder row. §5 "no empty levels".
6. A Work row opens the record room as a click in the cabinet does, after selecting the identity there; the cabinet view
   takes the column, which is the existing follow rule for record rooms. NV02.
7. The Machine view yields to the cabinet or settings view exactly when the Settings view did before (a record room or
   settings editor becoming current); the strip is what survives navigation. NV01.
8. `settings_navigation.mode` gains `machine` through the shared `Session.load` vocabulary (WI-1's `NAVIGATION_MODES`),
   so the Machine view is remembered like the other two; a documented constant falls back to `cabinet` for an older
   loader. UI02.
9. The current switch word is said by weight and a pink rule in addition to its accessible description. VS01/AC15.
10. Tool rows reuse `capability_catalog.native` and say presence only; the llama.cpp archive is verified by hash, never
    extracted or run. HT02/HT03.

## Evidence

Tests (per module, from the program folder with the venv interpreter):

    venv/bin/python -B -m unittest -v tests_integrated.test_machine

Six tests: missing `/proc` and `/sys` give honest unavailable states; a fixture host is read with bounds and natural
order and no process may start; the tools section reuses the catalogue families passively; short model names and sizes;
`ledger.machine` is a bounded read for the owner and a read-only principal with the schema fixed; the registry adds
exactly `ledger.machine`, keeps every baseline row and the 112 tools, and matches the recorded digest.

Qt check (offscreen, disposable profile, process guards):

    QT_QPA_PLATFORM=offscreen venv/bin/python -B tools/check_machine_ui.py

Captures under `build/desktop01_ui/machine/` (or `ARC_LEDGER_MACHINE_CAPTURE_DIR`), report `machine-ui.json` with
`state`, `checks`, `captures` (sha256 and resolution), `strip_samples` and the zero-activity counters:

- `Ledger_Slate_HATCH_Desktop_01_Machine_01_Machine_View.png` (1920×1200) · the Machine view, Storage open, the
  workspace path selected, details with source and time
- `Ledger_Slate_HATCH_Desktop_01_Machine_02_Work_Link_Selects_Cabinet_Record.png` · the project chosen under Work: the
  cabinet shows the same identity selected, its room is open, the edited Preview is untouched
- `Ledger_Slate_HATCH_Desktop_01_Machine_03_Settings_With_Strip.png` · Settings from the switch under the same strip;
  the yellow settings filter
- `Ledger_Slate_HATCH_Desktop_01_Machine_04_Compact_1366.png` (1366×768) · the Machine view, one-line strip, Trash at
  the foot

AC10, mechanical part, exercised by the check: inspect machine/storage/device state (source and freshness in details);
project links select the same cabinet identity; Import and Export present; Trash pinned bottom-right outside scrolling
in all three views; the settings hierarchy reachable from the switch and from the tree; the chosen view written to the
session and read back through `Session.load`. The setting-change half of AC10
(ask Slate, read back stored/effective/pending) is the existing `ledger.settings.*` route and is not re-claimed here.
Real host and device observations for hardware claims remain the owner-host dependency the specification names.
