# Graphite 1.0 · The Living Desktop and the Ghost in the Shell

This set replaces the application set in the `App` folder of your Graphite_Transfer kit (0.8.7, or anything earlier),
and **adds to the System set**: 136 Debian 13 packages for the parts of 1.0 that reach your computer (USB drives,
sound, Wi-Fi, the battery, the lock, permission prompts, Writer, accessibility). The Wheels set is unchanged.

Every ZIP in this set is smaller than 15,000,000 bytes.

## Built, not tested

You said "No testing" for 1.0. Nothing in it has been through the test suite, the tiers or the window checks, and nothing
has run on your ThinkPad. It was built in a cloud machine with no screen, USB port, sound, Wi-Fi, suspend or Radeon, and
seen working there offscreen and against stand-ins: each part's builder ran one script of the design's own examples,
and at each merge Graphite started and its window opened in all four looks. Twenty-four walkthroughs (twelve everyday,
twelve power-user) and the paper's §18 day were walked in the window, the day with a real 4B model. **The first real
proof is your evening**: `docs/ACCEPTANCE_1.0.md`, also in Graphite as Guide ▸ Your First Evening with 1.0.

Install into a new folder and keep your 0.8.x folders and a backup of your workspace (the page says how).

## What is here

- `Graphite_1.0_part_01.zip` … the numbered application parts. All of them are required.
- `Graphite_1.0_system_add_part_01.zip` … the 136 new Debian packages, under `App/debs/`, beside the 0.8.x ones.
- `Graphite_1.0_START_HERE.zip`: `App/RELEASE_PARTS.json`, `App/SHA256SUMS`, `App/INSTALL_LS.py`,
  `App/INSTALL_GRAPHITE.sh`, `App/PREPARE_DEBIAN.sh`, `App/OFFLINE_FILES.json` and `App/DEBIAN_USB.sha256` (now 540
  files: the 0.8.x ones and the new ones), `WHAT_THE_1.0_SYSTEM_SET_ADDS.md`, `SYSTEM_SET_1.0.json`, and this page.
- **Not here: the model.** You download it yourself (below).
- **Not here: any picture of Kas.** You asked for none ("No kas avatar anymore"); 1.0 shows her name, her state and her
  work, never a picture.

## Put it in place

1. In your Graphite_Transfer folder, take every earlier `Graphite_…_part_NN.zip` out of `App`.
2. Extract `Graphite_1.0_START_HERE.zip` over Graphite_Transfer so its `App` files replace the earlier ones.
3. Extract every `Graphite_1.0_system_add_part_NN.zip` over Graphite_Transfer: the new packages land in `App/debs/`
   beside the ones already there. Nothing is replaced.
4. Put the numbered `Graphite_1.0_part_NN.zip` files, intact, into `App`.
5. Check everything:

   ```sh
   cd App
   sha256sum --check --strict SHA256SUMS
   sha256sum --check --strict --quiet DEBIAN_USB.sha256
   ```

## Install

`docs/ACCEPTANCE_1.0.md`, Part 1, has every step with what you should see. In short, from `App`:

```sh
bash INSTALL_GRAPHITE.sh --plan        # as root: preview the packages; it should end "3 upgraded, 133 newly installed, 0 to remove"
bash INSTALL_GRAPHITE.sh --system      # as root: install them
# log out and log in again (your session, sound and permission prompts start at login)
bash INSTALL_GRAPHITE.sh               # as your ordinary user: install Graphite 1.0 into ~/Applications/Graphite-1.0
bash "$HOME/Applications/Graphite-1.0/START_MINIMAL_DEBIAN.sh"
```

If your ThinkPad has updated LibreOffice from the internet, the preview says it cannot resolve and why, before anything
changes; `WHAT_THE_1.0_SYSTEM_SET_ADDS.md` gives the online command for that case.

## Her model

Download on a computer with the network: unsloth's `Qwen3.6-35B-A3B-MTP-GGUF` / `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`
(22,663,387,424 bytes, sha256 `0b21525e972670ed59e1812e170b27c26355381f0656ecc4e25617ece7dac58b`; the file with its own
MTP head, for multi-token prediction). The 0.8.7 file (ggml-org's `Qwen3.6-35B-A3B-Q4_K_M.gguf`) still works, without
MTP. Check the sha256 before anything else. Then the model check, on mains: the acceptance page, Part 3.

## What is new in 1.0

- **Graphite is the session.** A supervisor keeps it alive; your apps outlive a crash of its window; the dock brings it
  back; Lock, Suspend, Log out, Restart, Shut down and Return to Debian are plain actions that close apps politely.
- **The whole computer.** Files from "This computer /" with Home open (rename, move, copy, delete to the bin and
  restore, each with Undo); Apps from what is installed; the Machine for real (USB drives, sound, screens, network and
  Wi-Fi, the battery); Settings that change real settings; notifications kept in Log.
- **The Living Desktop.** The board: what you select sits in the middle with its neighbours around it, sized by
  relevance; recorded links solid, guessed ones dashed and saying so; "Why am I shown?", Pin, Turn down. Double-click to
  work on it; Save and Return; tabs and a split; Back and Forward to exactly where you were.
- **The ghost in the shell.** Kas plans a task from the real tools, shows it in her column, asks for each permission in
  plain words, and marks a step done only when its effect is verified; a journal survives a crash or a Stop. She edits
  Writer and Calc documents through LibreOffice itself, works in your apps through accessibility while you watch (a
  touch stops her and she puts the window back), runs a utility she writes only sealed on copies, reads the web only
  as quarantined data, and reads the pages of your documents in Home. HALT stops all of her work and nothing else.
- **Her model, current.** llama.cpp v1.0.0 with multi-token prediction, flash attention and kept prompts; the model
  check measures this machine and says how far reading and writing are from 99 tokens a second; an optional quick model
  beside the 35B takes a kind of question only where it passed its exam.
- **The launch look.** Day, rebuilt on one set of design tokens with the Inter typeface, and Night, its dark twin;
  Graphite and Kasandra stay as alternatives. Her column has no picture: her name, her state and her work.
- **The floor.** Reads run beside her writes and her heavy presses run off the window's thread, so it no longer waits for
  her; the cold start is about a third faster; a 0.8.7 workspace opens in 1.0 as it is.
- **Bulk files.** Many rows at once in the tree, moved, copied or deleted in one press with one Undo for the batch.
- `docs/RELEASE_NOTES_1.0.md` (Guide ▸ What's New) has all of it, with what was measured, what was not, and what 1.0
  does not do yet.

## The licence

Graphite's own code and documents are free software under the GNU General Public License, version 2 only. `COPYING` in
the restored tree holds the owner's note and the full licence text; `RIGHTS.md` says what is kept back. Inter and IBM
Plex are under the SIL Open Font License; llama.cpp under MIT (`THIRD_PARTY_NOTICES.md`).

## What was and was not checked

Cut on 27 November 2026 in a cloud build container, offscreen, from commit `9f42ae5`:

- **The parts.** Ten application parts (`Graphite_1.0_part_01.zip` to `_10`) and four System additions
  (`Graphite_1.0_system_add_part_01.zip` to `_04`, the 136 packages, each matching `DEBIAN_USB.sha256`). Every ZIP is
  under 15,000,000 bytes. `SHA256SUMS.kit` beside them lists every ZIP's checksum.
- **Restored.** These parts restore with `INSTALL_LS.py` (`--offline --extract-only`). The restored tree matches the
  commit file for file, except the folders left out on purpose (`wip/`, the build's working notes, and
  `tools/planted_bugs/` and `tools/i05_kit/`, the build's own test material). The release check on the restored tree
  passed (1,559 files; the payload's privacy scan clean).
- **Not run:** the test suite, the tiers and the window checks (your rule); the 35B; anything on a real screen, USB, sound,
  Wi-Fi, suspend or Radeon; the Debian packages were resolved in a simulation only, never installed.
- **Seen here:** each part's builder ran one script of the design's own examples; at each merge Graphite started and its
  window opened offscreen in four looks; twenty-four walkthroughs and the paper's §18 day were walked in the window (the
  day twice with a real 4B: once by its builder, once on the merged code before the cut).
