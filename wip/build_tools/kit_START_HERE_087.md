# Graphite 0.8.7 · the application set

This set replaces the application set in the `App` folder of your Graphite_Transfer kit (0.8.6, or anything earlier).
Everything else in that kit stays as it is: the System and Wheels sets (the offline Debian packages and Python wheels) are
the same for 0.8.7, and the Records set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Retire the old

This set is the only application set you need. You can delete every earlier one: the `Graphite_0.2a13_part` ZIPs and every
later `Graphite_…_part` ZIP up to `Graphite_0.8.6_part`, with their `START_HERE` ZIPs. Keep the System and Wheels sets;
the offline install on the ThinkPad still needs them. The Records set is history only and nothing here reads it. The
source itself is also kept at the address at the end of this page.

## What is here

- `Graphite_0.8.7_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_0.8.7_START_HERE.zip` (this file's ZIP): `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json`, `App/DEBIAN_USB.sha256`, and this page.
- **Not here: the model.** You download it yourself (below). It is about 20.5 GB.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` file out of `App`. They are no longer
   needed.
2. Extract `Graphite_0.8.7_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones of the same name.
3. Put the numbered `Graphite_0.8.7_part_NN.zip` files, intact, into `App`.
4. Check them: `cd App && sha256sum --check --strict SHA256SUMS`

## Restore the source

From the Graphite_Transfer folder:

```sh
python3 INSTALL_LS.py --usb App --target Graphite-0.8.7-Clean --offline --extract-only
```

The target must be a new folder. The installer checks every part, joins the split files and verifies every restored file.

## Install on the ThinkPad

The same steps as for 0.8.6, with 0.8.7 in the folder name. Install into the new folder; your earlier folders and your
workspace stay as they are. With `debs/` and `wheels/` already copied into `App` from the System and Wheels sets:

```sh
cd App
sha256sum --check --strict --quiet DEBIAN_USB.sha256
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the Debian packages
bash INSTALL_GRAPHITE.sh --system      # as root: install them
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 0.8.7
bash "$HOME/Applications/Graphite-0.8.7/START_MINIMAL_DEBIAN.sh"
```

## This set was not tested

You said "No tests" for 0.8.6 and 0.8.7, and "We test before 88". So nothing in 0.8.7 has been through the test suite,
the tiers or the window checks, and no part was reviewed by a second agent. Nothing has run on your ThinkPad, and the
35B has never been loaded anywhere. Install it into a new folder and keep your 0.8.5 and 0.8.6 folders: it is a
preview. The full test pass comes next, before any of 0.8.8.

## Your evening: check her model on this machine

This is what 0.8.7 is for. Your results decide the test pass and 0.8.8.

1. **Download the model** on a computer with the network: ggml-org's `Qwen3.6-35B-A3B-Q4_K_M.gguf`, 20,542,732,576
   bytes. Before anything else:

   ```sh
   sha256sum Qwen3.6-35B-A3B-Q4_K_M.gguf
   # must print f4ffe03c9139e6a905a5d346f77d9fabdd179367c3280dfd005d1e75ca5ed8c8
   ```

   If you have room, also the small fallback, unsloth's `Qwen3.5-4B-Q4_K_M.gguf` (2,740,937,888 bytes, sha256
   `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4`).
2. **Keep the ThinkPad on mains.** The check waits while it runs on battery.
3. In Graphite 0.8.7: **Brain room → Add file**, choose the model, and select it in the list.
4. **Brain room → the tab Check her model → Check her model on this machine.** It shows its stages and their estimated
   times first and asks before it starts. It runs on an invented workspace of its own, never yours. The awake part
   takes about 20 to 30 minutes by the design's estimate; touching the desk pauses it. The overnight part (the full
   exam and the I05 experiment, hours) runs only if you tick it.

   From the console instead:

   ```sh
   cd "$HOME/Applications/Graphite-0.8.7"
   ./MODEL_CHECK.sh --plan
   ./MODEL_CHECK.sh --model /path/to/Qwen3.6-35B-A3B-Q4_K_M.gguf
   ```

5. **At the end** it shows a card, exactly what the file for sending holds, and offers "Use the measured settings?"
   one at a time, each with Undo. **Show the folder** opens `for-sending/`.
6. **Send back the two files in `for-sending/`**: `model-check-<date>.json` and `model-check-<date>.txt`. They are
   written only if their privacy scan is clean (no path beyond the model's file name, no host or user name, none of
   your work). Nothing leaves your computer unless you send it.

If it stops early, the card says at which stage and why (for example, the setting to raise if her memory rule would
refuse the 35B; nothing is changed for you). Send that card too: it is a result.

## New in 0.8.7: her model, interwoven

- **It proposes; the desk checks.** Her model runs sealed (only the settings it needs, a private socket, her key, its
  agent tools refused). Every question to it is priced, capped, checked and written down. A change only the model chose
  is never done; it comes as a card.
- **"I took it as …".** When her dictionary cannot read your words, the model may, into desk verbs only, never from
  quotes or pastes. Do or Not that. What you agree to is remembered.
- **The one question.** One card per request when something is yours to settle. Leave it runs the reads it names.
- **In the window:** Ask the Library (a tab in the reference view, or "ask the library …" in the writing line), Read
  this table, cross-references beside the Act's lines, her voice floor in her column, her clock's line with Stop.
- **The exam.** A kind of question is switched off on any harm or under 12 of 20, and she says so.
- docs/RELEASE_NOTES_0.8.7.md (Guide → What's New) has all of it: what was measured (a few short 4B runs) and what was
  not, the promises that are still not true, and what is not built.

## Worth trying after the check

1. Guide → Try Rail Demo. On the Field, right-click the startup finding and choose Why: its maths line is now said in
   her voice floor's words.
2. Guide → Try Home Demo. In the writing line: `ask the library how long does the landlord have to give the deposit
   back?` The places come first, with your words lit; with a model loaded, the quote it points at is lit and marked.
3. On Home Demo, open the invented Act's page: the cross-references are drawn beside its lines.
4. With the model loaded, ask in words her dictionary does not read, and see the "I took it as" card.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in the
restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back (Stacy's artwork, the
names and the game copy).

## What was and was not checked

Built on 26 November 2026 in a cloud build container, offscreen, on the commit cut, `ddf0aed`:

- **Not run:** the test suite, the tiers and the window checks (your rule); the 35B; the overnight exam and the I05
  arms.
- **Run here, with the 4B on a busy processor, once each:** one sealed start, prompt reuse, Stop, the memory checkpoint
  (the release notes give the numbers). The exam was sat on a stand-in with no model: 114 of the 127 short questions
  can be asked at the 35B's estimated speeds.
- **Checked:** each part's builder ran one script of the design's own examples; at each merge, Graphite started and its
  window opened offscreen in both looks. These parts restore with `INSTALL_LS.py`; the restored tree matches the commit
  file for file except the folders left out on purpose (`wip/`, the build's working notes, `tools/planted_bugs/` and
  `tools/i05_kit/`), and `tools/check_release.py` PASSED on it (1,471 files).

Nothing in this set has run on the ThinkPad.

The source is public at https://github.com/c8wf7gt28n-prog/Struthio on the branch `claude/epic-galileo-c7k11y`.
