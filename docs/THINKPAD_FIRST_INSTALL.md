# Graphite on the ThinkPad

This build starts from the approved Visual Pass 1 and targets a fresh Graphite installation on an existing Debian 13 x86-64 system. The first launch opens the native desk with an empty model slot. Use the ordinary Debian account for the application and its workspace.

## Observed hardware

The console photos show an AMD Ryzen 7 7735HS with eight cores and sixteen threads, Radeon 680M with the amdgpu driver loaded, a WD PC SN5000S NVMe controller, Debian 13, and kernel `6.12.113+deb13-amd64`. Debian reported 61 GiB RAM, about 60 GiB available at the console, and 48 GiB swap with 0 B used. SSD throughput and effective Vulkan allocation limits need a live check.

The starting policy uses one resident local worker, automatic Radeon discovery with CPU fallback, and the existing 2 GiB foreground memory budget. The worker admission check uses current available RAM. The hardware record is an inventory, and a later run with an actual GGUF qualifies the chosen model and offload.

## Offline USB setup

Extract the First Boot kit and copy its folder to your USB drive. The kit includes `START_HERE.md` with the short installation commands. The USB directory contains `PREPARE_DEBIAN.sh`, `DEBIAN_USB.sha256`, `INSTALL_LS.py`, `RELEASE_PARTS.json`, all numbered application parts, `OFFLINE_FILES.json`, `debs/`, and `wheels/`.

Use `lsblk -f` to identify the USB filesystem from the Debian console. Mount that partition and use the Graphite folder on the USB as the working directory for both installation phases.

At the Debian root prompt, change into that directory and preview the dependency step:

```bash
bash PREPARE_DEBIAN.sh --plan
```

Apply the verified local Debian packages:

```bash
bash PREPARE_DEBIAN.sh
```

Log into your ordinary Debian account. From the same USB directory install the app and its pinned local Python wheels:

```bash
python3 INSTALL_LS.py --usb . --target "$HOME/Applications/Graphite-0.4.4" --offline --system-ready --minimal-session --vulkan --calc
bash "$HOME/Applications/Graphite-0.4.4/START_MINIMAL_DEBIAN.sh"
```

Use a new target folder for a first install. The root script checks the whole dependency cache and can install Python on a bare Debian console. APT uses an empty repository list and the verified local Debian files. The application phase checks every release part and uses pip with its package index disabled.

## First-run workshop

The `examples/thinkpad_first_run` folder in the installation contains a fictional datasheet and stock workbook. Copy both into your work folder before editing. Open the stock workbook in Graphite, select Bracket A and Shade, and preview a shortage. The selected rows total 62 pcs.

In **References**, admit `Workshop_datasheet.pdf` and choose **Read technical PDF**. Select the table, choose **Review table**, and save the two rows as a reviewed sheet. Choose **Calculate and write report…**, use `voltage=B2` and `current=B3` as the inputs, enter `voltage * current`, and request `W`. The initial result is 3.00 W.

Change B3 to 280 mA in the working sheet and save. Recheck the report to produce a separate 3.36 W revision. Use **Source page** to inspect the original 250 mA reading. The report is a comparison exercise using fictional data.

## First work in the desk

- Press **F9** for the Field: the workshop's source, sheet, report and findings as sheets with the wires between them. Arrow keys follow a wire, **Enter** opens the real page, **Esc** comes back. **S** puts the selected sheet's staC line in the writing strip and **Shift+Enter** runs it. **N** shows this computer's network the same way and **W** returns to the work.

- From a worksheet, open **Full spreadsheet**, save in Calc, then choose **Return to sheet**.
- In a reviewed PDF sheet, select a row and choose **Open source row** to view the original passage. Pin the sheet first if you want to keep it open beside the PDF. A changed working value can be rechecked in the report.
- Find **Night Shift** in the command search. Open the saved checkpoint, inspect the grant and progress, and resume explicitly.
- In a stock sheet with Part, Required, Available, and Unit columns, select reviewed rows and use **Method Press** to retain or replay a shortage method. The method requires the reviewed unit on the new rows.
- When a local GGUF is available, open **Brain** to add the model and qualify its effective backend.
- In the Field press **P** for every program and room as a shelf; **Enter** opens one.
- In the Field press **X** on a sheet and Stacy doubts it: what does not hold, what she cannot tell, what holds.
- In the Field press **T** on a sheet to trace it back to its source, and with a calculation selected ask "what if B3 were 320?". In the writing strip `this` is the selected sheet: `this | count`, then **Ctrl+Enter**.
- In the Field press **D** on a sheet for what can be done about it, and **C** to check the whole desk. A digit chooses a step; a step that changes something waits for **G**, your go.

## The first model

The owner's choice is the Qwen family's 4.0 release at 27B, 4-bit quantised, once it exists. On 12 November 2026 it did not:
the publisher's page held no Qwen 4 weights, and files under that name elsewhere were placeholders. Read on that day from
the publisher's and the runtime's own pages, not tried on this machine:

- To rehearse until then, the same publisher's Qwen3.8-27B at Q4_K_M (about 17 GB, Apache 2.0). The bundled runtime
  (llama.cpp b11669) is newer than the builds that file was made with.
- A Qwen 4 file will probably need a newer runtime than the bundled one: check the build its publisher names against
  b11669 before the first try.
- Expect a few tokens a second from a 27B on this processor, with or without the Radeon. If loading on the Radeon fails
  with a device-lost or out-of-memory message, that is a known open fault on this graphics chip; the processor path works.
- Start small. A 2B and a 4B file of the same family answered in Graphite in 5 to 25 seconds on a slower processor than
  this one (`docs/MODEL_TRIAL_03.md`). Stacy reads the records herself and asks the model only for the words, so a small
  model is useful from the first day.
- Type `ledger.resources.observation | select kind,memory.state,memory.headroom_bytes,gpu.state,forecast.state` in the writing strip. **Ctrl+Enter** runs the local staC read. Prefix it with `explain` to preview the plan.

## Background job admission

Graphite checks current RAM headroom and the owner's foreground turn before applying a four-second forecast to new background jobs. The forecast uses a two-second half-life and can defer a job for up to eight seconds on its own. A job still needs enough current headroom after that wait. A forecast hold appears in the work list and Work trail.

## Desk artwork

After Midnight gives Stacy copper curls, green eyes, and an ink-and-screentone portrait under CRT light. The illustrated overview uses the wider workshop scene. The worksheet and journal show the still close portrait beside the work. Open **Work → Arrange → Desk artwork → Art plates** to view either image on its own. Illustrated, ASCII, and Clean modes remain available in the same menu.

## Fast-forward screensaver

Open **Work → Arrange → Desk artwork → Fast-forward screensaver → Preview now**. Amber traces, a green crossbar, and a hex window advance like a CRT recording on fast-forward. The operator appears in the workshop, with a brief *Brain on Disk* VHS cutaway about 24 seconds into each loop. The **SIMULATION** badge identifies the fictional operations. Real jobs continue through their usual Graphite controls.

Automatic start is off by default. The same menu offers five, fifteen, and thirty minutes of idle time while Graphite is active. Move the pointer, click, or press a key to return to the same desk. **Reduce optional motion** shows a still frame. For a password-protected lock, use the system's lock screen.
