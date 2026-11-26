# Graphite on the ThinkPad

Graphite 1.0 targets a fresh Graphite installation on an existing Debian 13 x86-64 system, where it is the whole desktop
(the dedicated session from a text login). The first launch opens in Day with no model loaded: Home on the board, and
Kasandra's column saying what she can do without one. Use the ordinary Debian account for the application and its
workspace.

**Built, not tested.** Nothing in 1.0 has run on this ThinkPad yet. The acceptance evening, `docs/ACCEPTANCE_1.0.md`
(Guide ▸ Your First Evening with 1.0), walks through the install, your paper's test, her model and the day on Rail Demo,
and says what to send back; this page holds the details it points to.

## Observed hardware

The console photos show an AMD Ryzen 7 7735HS with eight cores and sixteen threads, Radeon 680M with the amdgpu driver loaded, a WD PC SN5000S NVMe controller, Debian 13, and kernel `6.12.113+deb13-amd64`. Debian reported 61 GiB RAM, about 60 GiB available at the console, and 48 GiB swap with 0 B used. SSD throughput and effective Vulkan allocation limits need a live check.

The starting policy uses one resident local worker, automatic Radeon discovery with CPU fallback, and the existing 2 GiB foreground memory budget. The worker admission check uses current available RAM. The hardware record is an inventory, and a later run with an actual GGUF qualifies the chosen model and offload.

## Offline USB setup

Put the kit in place as its `START_HERE.md` says: the `App` folder of your Graphite_Transfer kit holds `INSTALL_GRAPHITE.sh`, `PREPARE_DEBIAN.sh`, `DEBIAN_USB.sha256`, `INSTALL_LS.py`, `RELEASE_PARTS.json`, all numbered application parts, `OFFLINE_FILES.json`, `debs/`, and `wheels/`. The 1.0 System set adds 136 Debian 13 packages (42.9 MB) to the 396 the 0.8.x set has, and removes nothing: USB drives (udisks2), the battery (upower), sound (PipeWire, WirePlumber), Wi-Fi (wpasupplicant), Lock (xsecurelock), the system's permission prompts (polkitd, lxpolkit), your login session (libpam-systemd), reading other programs (at-spi2-core, LibreOffice's GTK plugin), and LibreOffice Writer with its Python bridge (python3-uno). Their files go into the same `debs/` folder beside the 0.8.x ones.

Use `lsblk -f` to identify the USB filesystem from the Debian console. Mount that partition and use the `App` folder on the USB as the working directory for both installation phases.

At the Debian root prompt, change into that directory, check every file and preview the package step (it runs `PREPARE_DEBIAN.sh --plan`):

```bash
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan
```

On the ThinkPad as 0.8.x left it, the preview should end with `3 upgraded, 133 newly installed, 0 to remove`. Apply the verified local Debian packages (it runs `PREPARE_DEBIAN.sh`; a package already installed at the same or a newer version stays as it is):

```bash
bash INSTALL_GRAPHITE.sh --system
```

**Log out and log in again** before you start Graphite: your login session, the sound services and the system's permission prompts start at login. Then, from your ordinary Debian account and the same USB directory, install the app and its pinned local Python wheels into a new folder, and start it from a text login:

```bash
bash INSTALL_GRAPHITE.sh
bash "$HOME/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh"
```

Use a new target folder for every install; your 0.8.x folders and your workspace stay as they are. The root phase checks the whole dependency cache and can install Python on a bare Debian console. APT uses an empty repository list and the verified local Debian files; nothing is downloaded. The application phase checks every release part and uses pip with its package index disabled. If LibreOffice was updated from the network since 0.8.x, the offline set cannot add Writer to it: the preview says so before anything changes (with the network: `apt install libreoffice-writer libreoffice-gtk3 python3-uno`).

## If the screen stops answering

The dedicated session keeps a console route. If Graphite's window ends by itself, the session starts it again after 2, 4 and 8 seconds (at most 30), at most three times in a row, and then returns to the text console with a plain message; your apps stay open while it tries. If the screen itself stops answering:

- **Ctrl+Alt+F2** gives a second text console. Log in there with your ordinary account.
- `pkill --oldest --signal KILL --full workbench.launch` ends Graphite's window; the session starts it again.
- `pkill --signal TERM -x Xorg` ends the whole graphical session (unsaved work in open apps is lost); the first console then prints how Graphite ended.
- **Ctrl+Alt+F1** (the number of the console you started the session from) goes back to the session's screen.

The session's own record is in `~/.local/state/ledger-slate/`: `session.log` (each start and end), `last-session.json` (the last status and how many times Graphite was started again) and `launch-error.log` when a start failed. `docs/MINIMAL_DEBIAN_INSTALL_01.md` describes the dedicated session in full.

## First-run workshop

The `examples/thinkpad_first_run` folder in the installation contains a fictional datasheet and stock workbook. Copy both into your work folder before editing. Open the stock workbook in Graphite, select Bracket A and Shade, and preview a shortage. The selected rows total 62 pcs.

In **References**, admit `Workshop_datasheet.pdf` and choose **Read technical PDF**. Select the table, choose **Review table**, and save the two rows as a reviewed sheet. Choose **Calculate and write report…**, use `voltage=B2` and `current=B3` as the inputs, enter `voltage * current`, and request `W`. The initial result is 3.00 W.

Change B3 to 280 mA in the working sheet and save. Recheck the report to produce a separate 3.36 W revision. Use **Source page** to inspect the original 250 mA reading. The report is a comparison exercise using fictional data.

## First work in the desk

Since 1.0 the centre's home is the board: select the workshop's sheet in Files or in the Desk drawer and it stands in the middle with its source, report and findings around it; a double-click opens it, and Save and Return to the board brings you back. Kasandra is spoken to in her ask line at the foot of her column; the line at the window's foot is the computer's (Line, Terminal, Search, Web, Log). Guide ▸ The Living Desktop is the tour. The Field below is the whole desk as sheets (the board's Whole desk, or Arrange ▸ Field).

- Press **F9** for the Field: the workshop's source, sheet, report and findings as sheets with the wires between them. Arrow keys follow a wire, **Enter** opens the real page, **Esc** comes back. **S** puts the line that reads the selected sheet in Line at the foot and **Shift+Enter** runs it. **N** shows this computer's network the same way and **W** returns to the work.

- From a worksheet, open **Full spreadsheet**, save in Calc, then choose **Return to sheet**.
- In a reviewed PDF sheet, select a row and choose **Open source row** to view the original passage. Pin the sheet first if you want to keep it open beside the PDF. A changed working value can be rechecked in the report.
- Find **Night Shift** in the command search. Open the saved checkpoint, inspect the grant and progress, and resume explicitly.
- In a stock sheet with Part, Required, Available, and Unit columns, select reviewed rows and use **Method Press** to retain or replay a shortage method. The method requires the reviewed unit on the new rows.
- When a local GGUF is available, open the **Brain room** (the GPU meter's card at the foot) to add the model and qualify its effective backend.
- In the Field press **P** for every program and room as a shelf; **Enter** opens one.
- In the Field press **X** on a sheet and Kasandra doubts it: what does not hold, what she cannot tell, what holds.
- In the Field press **T** on a sheet to trace it back to its source, and with a calculation selected ask "what if B3 were 320?". In Line at the foot `this` is the selected sheet: `this | count`, then **Enter**.
- In the Field press **D** on a sheet for what can be done about it, and **C** to check the whole desk. A digit chooses a step; a step that changes something waits for **G**, your go.

## The first model

On 13 November 2026 the owner named the model Kasandra is to run: **Qwen3.6-35B-A3B at Q4_K_M, as a GGUF file**. Read from
search results that day, not from the publisher's page and not tried on this machine: the Q4_K_M file is about 21 to
22 GB depending on who made it (one maker's "UD-Q4_K_M" is 22.1 GB, another's Q4_K_M 20.75 GB), and one comparison says
it wants about 24 GB of memory at a 16k context. It is a mixture of experts: all 35B are held in memory, about 3B work
on each token, so it should answer faster than a 27B of the same size on this processor. Whether the bundled runtime
(llama.cpp v1.0.0, build b12359, since Graphite 1.0) reads the file is not known: the Brain room shows it on the ThinkPad.
The memory recorded for the ThinkPad (about 61 GiB) is room for it.

### The first evening with the model (Graphite 1.0)

- **The machine.** A ThinkPad E16 Gen 2 AMD (machine type 21M5): Ryzen 7 7735HS, Radeon 680M integrated graphics (RDNA2,
  12 compute units; its memory is the system memory) and DDR5-4800 in two slots. Writing is bound by the memory's speed:
  expect about 15 to 30 tokens a second from the 35B-A3B at Q4, more with multi-token prediction. Reading is bound by the
  680M and should be well above that.
- **The runtime.** llama.cpp v1.0.0 (build b12359, commit b1b770d90d94cad9e9ea5b993bdbc383a522fb28), both archives under
  `runtimes/llama.cpp/b12359`. Her model is sealed as before; the seal's lists come from v1.0.0's own help text.
- **The model with its MTP head.** Multi-token prediction needs the model file that carries its own MTP head:
  `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` from `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`, 22,663,387,424 bytes, sha256
  `0b21525e972670ed59e1812e170b27c26355381f0656ecc4e25617ece7dac58b` (read from the publisher's file list on 26 November
  2026; not downloaded or tried here). The same name without "MTP" (22,134,528,992 bytes) has no head. Graphite never
  loads a second, separate head file.
- **The model check.** Run it once on mains (Brain room, or `./MODEL_CHECK.sh --model <file>`). Its new tuning stage tries
  flash attention, the KV cache's type, reading batches, threads, full or partial offload and, with the MTP file, the
  draft length; it keeps a setting only when the answer is the same as without it, and says how far each speed is from
  your goal of 99 tokens a second, reading and writing. Each best setting is offered under "Use the measured settings?",
  with Undo. Nothing changes until you press it.
- **What was measured here** (26 November 2026, a busy 4-core cloud machine with no Radeon, on the processor; these
  numbers mean nothing for the ThinkPad): the sealed 4B started on v1.0.0 and every wall of the seal held. With the
  prompt cache sized for every kept prompt, PLAN's and READ's both survived the priming round, and the second PLAN turn
  on Rail Demo took 4.0 s (3.3 s on the old runtime, on a quieter machine). The tuning stage on the 4B: reads 47 a second
  plain, 67 at its best (reading batch 1,024, four threads), writing 5; on the 2B with its MTP head: reads 98 plain, 144
  at its best, writing 9 to 12. On this processor multi-token prediction gave the same answer but no speed (the model
  accepted 45 to 69 % of the drafted tokens). Flash attention off, and the half-size KV caches, changed the answer here,
  so the check did not keep them.

Before that, on 12 November, the owner's choice was the Qwen family's 4.0 release at 27B, 4-bit quantised, once it
existed. On that day it did not: the publisher's page held no Qwen 4 weights, and files under that name elsewhere were
placeholders. Read on that day from the publisher's and the runtime's own pages, not tried on this machine:

- To rehearse until then, the same publisher's Qwen3.8-27B at Q4_K_M (about 17 GB, Apache 2.0). The bundled runtime
  (llama.cpp b11669 then; v1.0.0, b12359, since Graphite 1.0) is newer than the builds that file was made with.
- A Qwen 4 file will probably need a newer runtime than the bundled one: check the build its publisher names against
  b12359 (llama.cpp v1.0.0) before the first try.
- Expect a few tokens a second from a 27B on this processor, with or without the Radeon. If loading on the Radeon fails
  with a device-lost or out-of-memory message, that is a known open fault on this graphics chip; the processor path works.
- Start small. A 2B and a 4B file of the same family answered in Graphite in 5 to 25 seconds on a slower processor than
  this one (`docs/MODEL_TRIAL_03.md`). Kasandra reads the records herself and asks the model only for the words, so a small
  model is useful from the first day.
- Type `ledger.resources.observation | select kind,memory.state,memory.headroom_bytes,gpu.state,forecast.state` in Line at the foot. **Enter** runs the local read. Prefix it with `explain` to preview the plan.

## Background job admission

Graphite checks current RAM headroom and the owner's foreground turn before applying a four-second forecast to new background jobs. The forecast uses a two-second half-life and can defer a job for up to eight seconds on its own. A job still needs enough current headroom after that wait. A forecast hold appears in the work list and Work trail.

## Desk artwork

Since 1.0 no picture of Kasandra appears anywhere, in any look (the owner, 26 November 2026: "No kas avatar anymore"): her column opens with the equalizer, her name, her model and her state word. The look itself is chosen in **Arrange → Appearance**: Day (the launch look), Night, Graphite or Kasandra. **Rules → Desk artwork** keeps the workshop's art plates (**Art plates**), the glow, and the Illustrated, ASCII and Clean modes.

## Fast-forward screensaver

Open **Rules → Desk artwork → Fast-forward screensaver → Preview now**. Amber traces, a green crossbar, and a hex window advance like a CRT recording on fast-forward. The workshop scene shows, with a brief *Brain on Disk* VHS cutaway about 24 seconds into each loop. The **SIMULATION** badge identifies the fictional operations. Real jobs continue through their usual Graphite controls.

Automatic start is off by default. The same menu offers five, fifteen, and thirty minutes of idle time while Graphite is active. Move the pointer, click, or press a key to return to the same desk. **Reduce optional motion** shows a still frame. For a password-protected lock, use the system's lock screen.
