# Graphite 1.0 · your first evening on the ThinkPad

**Built, not tested.** By your rule ("No testing") nothing in Graphite 1.0 has been through a test, a tier or a window
check, and nothing of it has run on your ThinkPad. It was built in a cloud machine with no screen, no USB port, no sound,
no Wi-Fi, no suspend and no Radeon, and seen working there offscreen and against stand-ins. **The first real proof of
1.0 is this evening.** Whatever you see that differs from this page is a result: photograph it and send it.

The evening has five parts. Each step says what to do, what you should see, and which photo to take. The photos are
numbered; name each file by its number (for example `photo-07.jpg`).

1. **Install from the kit** (about 30 minutes).
2. **Graphite as the computer, with no model**: your paper, section 2 (about 45 minutes).
3. **Her model**: the 35B with its MTP head, the model check and its tuning (60 to 90 minutes, most of it waiting).
4. **The day**: your paper, section 18, on Rail Demo, with her model ready (about 45 minutes).
5. **Leave, and what to send back** (about 15 minutes).

Two evenings are fine: parts 1 and 2, then 3 to 5.

**The machine.** ThinkPad E16 Gen 2 AMD (machine type 21M5), Ryzen 7 7735HS, Radeon 680M, Debian 13. Keep it on mains for
the whole evening (the model check waits while it runs on battery). Have your phone or a camera for the photos, and a USB
stick with a few ordinary files on it (not the kit's drive).

**Where the details are.** `docs/THINKPAD_FIRST_INSTALL.md` (the ThinkPad page: the install, the model file, the console
route if the screen stops answering) and `docs/MINIMAL_DEBIAN_INSTALL_01.md` (the dedicated session). This page points to
them rather than repeating them. In Graphite, Guide ▸ The Living Desktop and Guide ▸ Kasandra, the Ghost in the Shell say
what each part of the window is.

---

## Part 1 · Install from the kit

The kit's start page (`START_HERE.md`) says where its files go in your Graphite_Transfer folder; the 1.0 System set's own
section there says what the 136 new Debian packages are for. Then, in `App`:

```sh
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages (PREPARE_DEBIAN.sh --plan)
bash INSTALL_GRAPHITE.sh --system      # as root: install them (PREPARE_DEBIAN.sh)
```

1. The check prints nothing and ends without an error.
2. The preview should end with `3 upgraded, 133 newly installed, 0 to remove` on the ThinkPad as 0.8.x left it. apt uses
   only the files on the USB; nothing is downloaded. **Photo 1:** the last lines of the preview.
3. Install them with `--system`. **Then log out and log in again** before anything else: your login session, the sound
   services and the system's permission prompts start at login.
4. From your ordinary account, in the same `App` folder:

   ```sh
   bash INSTALL_GRAPHITE.sh               # installs Graphite 1.0 into a new folder under ~/Applications
   ```

   The installer names the folder it made (`~/Applications/Graphite-1.0`). Your 0.8.x folders and your workspace stay as
   they are.

**Before you open your own workspace in 1.0**, make a complete backup of it (restore always writes new folders):

```sh
bash "$HOME/Applications/Graphite-1.0/LEDGER.sh" backup create --root ~/Concern/Office --out ~/Graphite-backups/office-before-1.0
```

**Your 0.8.7 workspace in 1.0.** 1.0 reads a 0.8.x workspace as it is: it adds tables of its own and changes none of
0.8.7's. Here, a workspace written by 0.8.7 opened in 1.0 with every record, word, setting and the dial intact, and its
files were byte-identical afterwards. One known gap: a task Kas left running in 0.8.7 does not show in ACTIVE WORK yet.
Keep the backup above all the same.

**The cold start, and stalls.** Note how long the first start takes from the start command to the window (a photo of a
clock at each end is enough); here it was 5 to 6 seconds. To let Graphite measure itself, start it once with its stall
log:

```sh
GRAPHITE_STALL_LOG="$HOME/graphite-stalls.txt" bash "$HOME/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh"
```

Every moment the window does not answer for more than a tenth of a second is written there, with the part of Graphite
that held it. Send that file back with the rest.

## Part 2 · Graphite as the computer, with no model (your paper, section 2)

Your paper's test: start the machine without a model, open two unrelated apps, exchange material between them, connect a
USB drive, suspend and resume, then return to the console deliberately. And 1.0's own promise beside it: if Graphite's
window ends, your apps stay open and Graphite comes back.

### 2.1 Start

From the text login:

```sh
bash "$HOME/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh"
```

You should see: the window in **Day** (light, calm), with one line saying that Graphite 1.0 starts in Day and that your
earlier look is in Arrange ▸ Appearance; HALT upper left; Apps ⊕ upper right; Files on the left, starting at "This
computer /" with Home open and chosen; the board in the centre; Kasandra's column on the right with the equalizer across
its top and no picture of her; at the foot Line · Terminal · Search · Web · Log and the meters CPU GPU RAM TXT NET; and the
slim dock across the very top.

**No model.** Her column must show ○ beside her name and say that no model is loaded and what she can still do. If it
shows ● with a model ready, stop the model in the Brain room (the GPU meter's card at the foot) before you go on.

**Photo 2:** the whole screen.

### 2.2 Two apps, and material between them

1. Open **Apps** (upper right). It lists what is installed on this computer by kind, with a search line. **Photo 3.**
2. Open LibreOffice Writer, then a second app that is not LibreOffice (a text editor, Firefox, an image viewer: whatever
   Apps lists). If only LibreOffice is installed, use Writer and Calc, and say so.
3. The dock shows both windows with their titles, the active one marked. Press each in the dock: it comes forward. Press
   the dock's Graphite entry: Graphite comes back. **Photo 4:** the dock with both apps.
4. Exchange material: copy a passage from one app and paste it into the other (each app's own Edit menu); then save a
   file in one and open the saved file in the other. Say whether both ways worked.
5. In Graphite, find the saved file in Files (under Home), right-click it, Open with: the apps that take that kind of file
   are listed, the default first.

### 2.3 Graphite comes back; your apps stay

With both apps still open, choose Terminal at the foot and run:

```sh
pkill --oldest --signal KILL --full workbench.launch
```

This ends Graphite's window the hard way, as a crash would. You should see: Graphite's window gone for a few seconds, then
back, with a line saying it was started again; both apps still open, their windows untouched. **Photo 5:** Graphite back,
with the line, and the dock with both apps.

### 2.4 A USB drive

1. Plug in your USB stick. You should see it under **Drives** in Files, and in the Machine tab under **Storage**.
   **Photo 6.**
2. Open it, open a file from it in its app, and save a copy into your home from that app. Close the app.
3. Eject it safely: choose the drive under Drives (or Machine ▸ Storage), and on its page in the centre press Eject
   safely. "safe to remove" should appear only once the stick is released. **Photo 7:** "safe to remove". Then pull it out: its row goes.

### 2.5 Suspend and resume

1. From the foot of the **Work** menu: the session group reads Lock, Suspend, Log out, Restart, Shut down, Return to
   Debian. **Photo 8:** the Work menu open.
2. Choose **Lock** first: the screen locker shows; type your password into it (never into Graphite); you are back.
3. Choose **Suspend**: the screen locks first, then the computer sleeps. Wake it, type your password into the locker.
   You should see Graphite and your open apps exactly as they were. **Photo 9:** after the wake.

### 2.6 A few minutes in the Machine (if you can)

Each is optional; take a photo of whatever reads wrong.

- **Power:** the battery and the mains read correctly.
- **Network:** the Wi-Fi networks listed; NET at the foot reads ● online. With Wi-Fi as your only connection, turning it
  off makes NET read ⊘ offline.
  Joining a network asks for its password in Graphite's page, and the system's network service keeps it.
- **Sound:** the volume and mute change the real sound.
- **Screens:** with a second screen plugged in, mirror or extend; the change goes back by itself after 15 seconds unless
  you press Keep.
- **Settings ▸ This computer:** default apps, sound, screens, network, power, the session, notifications.

### 2.7 Return to the console

Choose **Return to Debian** at the foot of the Work menu with an app still open. You should see Graphite name the apps
still open and ask each to close politely (an app may ask you to save; nothing is killed). **Photo 10:** that question.
Then the text console, with `Graphite ended with status 0` and a line saying how many times Graphite was started again in
this session (one, from 2.3). **Photo 11:** the console.

## Part 3 · Her model

### 3.1 The 35B with its MTP head

The model file that carries its own multi-token prediction head, its exact name, size and checksum are on the ThinkPad
page, `docs/THINKPAD_FIRST_INSTALL.md`, section "The first evening with the model (Graphite 1.0)". Download it on a
computer with the network, check its checksum with `sha256sum` before anything else, and copy it to the ThinkPad. If you
do not have it, the 35B file you used with 0.8.7 does for everything here; the card will then say that multi-token
prediction was not tried.

Start Graphite again (2.1). In the **Brain room** (the GPU meter's card at the foot): **Add file**, choose the model, and
select it in the list. A new model file is a new model to her: her exam is sat again for it in the check below. Her
column should show ● beside her name, with the model's name. **Photo 12:** the Brain room with the model ready, its
runtime line naming llama.cpp b12359.

### 3.2 The model check and its tuning

In the Brain room: the tab **Check her model** ▸ **Check her model on this machine**. It shows its stages and their
estimated times first and asks before it starts. It runs on an invented workspace of its own, never yours, and only on
mains power. Touching the desk pauses it; leave the ThinkPad alone while it runs (about 20 to 30 minutes by the design's
estimate, then the tuning stage).

The tuning stage tries, one at a time: flash attention, the type of her prompt memory (the KV cache), reading batches,
threads, full or partial offload to the Radeon and, with the MTP file, multi-token prediction and its draft length. It
keeps a setting only when the answer is the same as without it, and says how far reading and writing are from your goal of
99 tokens a second. Its time box is 4 minutes; if the card says the box ran out before every setting was tried, run it
once more from the console with a longer box:

```sh
bash "$HOME/Applications/Graphite-1.0/MODEL_CHECK.sh" --model /path/to/the-model.gguf --tuning-seconds 900
```

At the end it shows a card, exactly what the file for sending holds, and **Use the measured settings?**: each proposal
one at a time, each with Undo. Apply what you like and write down which. **Photo 13:** the card. **Photo 14:** "Use the
measured settings?". **Show the folder** opens `for-sending/`, where the two files to send are.

If it stops early, the card says at which stage and why. Send that card too: it is a result.

**A quick model beside the 35B (optional).** Her questions are short, so a second, small model can answer some kinds
faster. If you have a small model file (a 2B to 4B), name it to the same check:

```sh
bash "$HOME/Applications/Graphite-1.0/MODEL_CHECK.sh" --model /path/to/the-35B.gguf --quick /path/to/the-small-model.gguf
```

It measures the pair, sits the small model's exam for each quick kind, and proposes the split: a kind goes to the
small model only where it passed that kind's exam and measured faster; the 35B keeps the rest. Here, a 2B passed
none of its exams, so expect it to take few kinds or none. **Photo 14b:** the Brain room's **Quick model** page, which
says which model answers which kind and why. **Put every kind back on her model** undoes it all.

## Part 4 · The day (your paper, section 18), on Rail Demo

Rail Demo is an invented desk: a 12 V rail on a bench, with bench readings (12 V, settled current 250 mA, startup current
900 mA, startup 45 ms), its limits in two revisions (Rev A, archived; Rev B, current: settled power at most 4 W, startup at
most 40 ms), the calculations made from them, four findings, a summary page and one open question. Every number in it is
made up. In this part its limits sheet (Rev B) plays the specification, and its bench readings sheet plays the
worksheet.

Her model should be ready (Part 3). Where a step says what she should answer, the words will differ; what matters is what
the answer claims.

1. **Guide ▸ Try Rail Demo**, then **Build it** on her card. It is built in a new folder of its own under
   `~/Graphite demos`, never in your workspace, and opens in a window of its own. Her card names the folder: write it down.
   **Photo 15:** Rail Demo's window.
2. **Select the project.** In the Desk drawer on the left, choose its concern, "Rail Demo (invented data)". The board
   shows its material around it, sized by relevance.
3. **Select the specification:** the sheet "Rail Demo limits Rev B CURRENT". The tree shows where it is; the board puts it
   in the middle with its neighbours around it; the Rev A sheet is smaller and marked — ARCHIVED. Click a wire: it says
   why it is there, naming the values and the revision (a dashed one says "not verified"). **Photo 16:** the board with a
   wire's basis open.
4. **Open it:** double-click it. Its working view fills the centre; Kasandra's column stays beside it.
5. **Ask her,** in her ask line at the foot of her column: *Kas, review this assembly and tell me whether the proposed
   power supply is sufficient.* What she must claim: settled power holds (3 W against the 4 W limit, supported), and
   startup is **not** cleared (45 ms against 40 ms does not hold under Rev B, or it stays an open question). She must not
   say "sufficient" without that condition. **Photo 17:** her column with the answer, its check rows and FINDINGS.
6. **Open the worksheet beside it:** press Board on the centre bar, right-click the tile "Rail Demo bench readings" and
   choose Open beside (or press Split on the centre bar and open the readings into the empty half). The specification on
   one side, the readings on the other. Press in the readings' pane: the tree's
   highlight moves to the readings, and the other pane says "Beside · another object". **Photo 18:** the split.
7. **Change a value:** in the readings, set the settled current from 250 mA to 300 mA, and Save. You should see that the
   settled-power calculation and what rests on it are marked for a recheck (it works out at 3.6 W). **Photo 19.**
8. **The summary is out of date.** Does she notice by herself that "Rail Demo summary" still says 3 W (a line in her
   column, or a NEXT STEPS button)? Write down whether she did. If she did not, ask her in her ask line: *recheck the
   settled power and update the summary page*.
9. **Her plan.** You should see a task in ACTIVE WORK with its steps, each through a registered tool; reading steps run;
   the step that changes the summary waits for you in "Waits for you" (◆ needs your word, or ◆ with a key: needs your
   grant). **Photo 20:** her column with the plan and what waits for you. Approve it.
10. **Done means verified.** The summary step should read ✓ done (verified) only after its new revision is on disk; the
    summary page on the board shows a new revision with the new value, and the old revision is kept. **Photo 21.**
11. **The startup question is still open.** Her column must show the summary update done while startup is still not
    cleared: finishing one part must not become an all-clear. **Photo 22:** FINDINGS and ACTIVE WORK together.
12. **Close the working views** (Close on the centre bar, or One pane and then Close). You should be back on the board with
    the same object in focus and its links as before. **Photo 23.**
13. **Close Rail Demo for the evening, and come back.** Close Rail Demo's window. Then choose Terminal at Graphite's foot
    and open it again on the same folder, with the folder her card named between the first quotes (the one below is an
    example):

    ```sh
    d="/home/you/Graphite demos/Rail Demo 2026-12-01 20.15.00"; cd "$HOME/Applications/Graphite-1.0" && env -u ARC_LEDGER_EDITION ARC1_WORKBENCH_CONFIG_HOME="$d/profile" ARC_LEDGER_WORKSPACE="$d/workspace" ARC_LEDGER_CONCERN="$d/Concern" setsid -f .venv/bin/python -m workbench.launch
    ```

    You should see the desk as you left it: the sources, the two revisions of the summary, the changed reading, the
    calculations, the findings, the open startup question, and her task in ACTIVE WORK with its journal (press its title):
    what was done, verified, and nothing done twice. **Photo 24:** the task's journal.

Optional, if there is time: in Rail Demo, press **HALT** while a task of hers runs. Everything of hers stops and says so;
the desktop and your apps keep running; HALT reads RESUME. Press RESUME: nothing restarts by itself. **Photo 25.**

## Part 5 · Leave, and what to send back

Choose **Return to Debian** (or Shut down) from the foot of the Work menu.

**Send back:**

1. **The photos**, by their numbers (1 to 25), and any other photo of something that read badly, with a word on what.
2. **The model check's two files** from `for-sending/`: `model-check-<date>.json` and `model-check-<date>.txt`. They are
   in the run folder under `~/.config/arc1-workbench/model-check/` (the Brain room's Show the folder opens it; the console
   run prints where). They are written only if their privacy scan is clean: no path beyond the model's file name, no host or
   user name, none of your work. Send the card of every run (3.2), and say which measured settings you applied.
3. **The session's own record**, from `~/.local/state/ledger-slate/`: `session.log` (one line for each start and end of
   Graphite and Fluxbox in each session), `last-session.json` (the last session's status and restarts) and
   `launch-error.log` if there is one. Look at them first: they hold times, statuses and process numbers, and
   `launch-error.log` can name folders in your home.
4. **Rail Demo's records and her task's journal**: the whole Rail Demo folder her card named (only invented data, though
   folder paths in it can carry your account's name). From Terminal:

   ```sh
   tar -czf ~/rail-demo-evening.tar.gz -C "$HOME/Graphite demos" "Rail Demo 2026-12-01 20.15.00"
   ```

   (with the folder's own name in place of the example's).

5. **A few lines** for each part: as written; different (what); failed (what, and the photo). The parts and steps are
   numbered above; "2.4 step 3: no 'safe to remove'" is all it needs.

**Never send** your own workspace (`~/Concern`), your profile (`~/.config/arc1-workbench` beyond the two `for-sending`
files), or a backup.

## If something goes wrong

- **Graphite's window ends by itself:** the session starts it again after 2 seconds, then 4, then 8, at most three times in
  a row; after that it returns to the text console with a plain message. Photograph the message; `session.log` has the
  rest.
- **The screen stops answering:** the console route is in `docs/THINKPAD_FIRST_INSTALL.md`, section "If the screen stops
  answering".
- **Anything else:** your 0.8.7 folder is untouched. Return to Debian and start 0.8.7 from its own folder as before.
