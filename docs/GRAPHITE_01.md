# HATCH GRAPHITE-01 · Graphite

The owner's design update of 2026-11-06 (decision D32): Graphite is the single public name for the workspace and its AI;
GRAPHITE on the startup screen; the sharpened graphite point replaces the Struthio mark; the unlabeled peeking cat
replaces the Hatch egg at the lower left and opens the existing menu. Internal identifiers, settings keys and project
paths stay as they are. The pass was delivered inside Graphite 0.1 (decision D34), which finished it; the section
"Finished in Graphite 0.1" at the end says what changed after the pass. Nothing here is owner-host acceptance.

## G-A · the mark, the startup screen and the cat

One new module, `workbench/graphite_brand.py`, paints everything with QPainter (no image files are read):

| Part | Where | What it is |
|---|---|---|
| The sharpened point | `paint_mark` | Two paper wedges converging to a point with a narrow gap between them and a short stroke past the tip, in the boot mockup's own proportions. Small sizes stay crisp: the gap keeps at least 1.25 device px at the wedges' wide end, the stroke at least 1.2 device px wide, and the stroke is left out where it would be shorter than 3 device px (only the 16 px icon); under 24 device px the tile's margin is 10%, not 15%. From 64 px, for the head's tile at device pixel ratio 2 and on the startup screen, the drawing is unchanged. |
| The head's mark | `shell2.Shell2.install` (the logo button) | The point on a 44 px graphite rounded tile on the same 54 px button as the bird; tooltip and accessible name **Graphite**. One click still opens the owner's STRUTHIO game. |
| The window icon | `qt_app.WorkbenchWindow` | The same tile painted at 16 to 256 px. |
| The startup screen | `launch.startup_screen`, called by `launch.main` | Graphite ground, the point in paper, GRAPHITE in spaced capitals. A frameless `QSplashScreen` centred on the screen, shown before `qt_app` is imported and closed by the first other window shown (the main window, or any dialog during the build, which never sits under it). No fade, so Reduce motion has nothing to stop. Any error means no startup screen, never a failed start; `--check` shows none. |
| The cat | `hatch_qt.HatchButton` + `graphite_brand.Cat` | The menu button itself: an unlabeled graphite silhouette with separately moving pupils, tail and right paw, 44 px high at 14 pt and following the interface size up to 1.4 (`typebar_qt.cat_tile`), standing on a short edge line. Tooltip and accessible name **Open menu**; the accessible description carries the service summary, the menu's choices (the words the old tooltip listed) and the F1 note. (HATCH DESK D2: pale paper on the band with graphite eyes and paws, named **Open programs**; it opens the programs list: docs/GRAPHITE_DESK.md.) |

The cat's poses (the owner's four):

- **Rest**: eyes forward, both paws on the edge, tail tucked away.
- **Hover**: a quick side-eye, the tail rises in a question-mark curl that is part of the tail (no dot), paws down.
- **Menu open**: the tail out of sight, the right paw lifted toward the menu, the eyes toward it. It wins over hover; the
  menu opens at once on click, Space or Enter, from any pose (one click from sleep).
- **Sleepy**: after 90 s with no input to the program and the menu closed, the head a little lower and the eyes closed.
  Hover wakes it into the side-eye.

When the menu closes the pointer decides: hover over the cat, rest away from it. A change moves six pose numbers in one
150 ms animation; under `reading.reduce_motion` the pose switches directly. Keyboard focus turns the edge eraser pink.

Decisions:

1. The pose logic is a pure state machine (`CatPoses`: open, then sleepy, then hover, then rest) over a table of pose
   numbers (`POSES`), tested without a window. It serves "choose the simplest implementation that fits the existing UI".
2. Input elsewhere in the program restarts the inactivity timer but never wakes a sleeping cat. Only the pointer on it,
   the menu or keyboard focus wakes it. This serves "keep the movement brief and tied to interaction". A pointer left
   resting on the cat lets it fall asleep too, and the next movement over it wakes it into the side-eye.
3. The hover wash and the eraser rule of the egg tile are gone. The cat's poses say hover and open, and the edge under
   it carries keyboard focus. The `menuOpen` property stays for the checks.
4. The menu, its rows, `LauncherKeys` and `DescriptorKeys` are unchanged. "Hatch" stays the internal name (module,
   object name, menu accessible names until the rename item).
5. The palette is graphite, paper and eraser pink only (shell2's values, repeated in `graphite_brand` so that the
   startup screen needs no window code; a test keeps them equal).

Evidence: `tests_integrated/test_graphite.py` (14 tests: the state machine, timing, Reduce motion, palette, mark
geometry, the mark crisp at 16 to 44 px, the tile arithmetic, a startup screen that cannot stop the start and closes before a failure message) and `tools/check_graphite_ui.py`
(offscreen, 11 checks, 16 captures and `graphite-brand-ui.json` in `build/graphite01_ui/brand`). `check_hatch_ui` and
`check_head_ui` now assert the cat and Open menu instead of the egg, the word Hatch and "Hatch launcher".

The wordmark beside the mark and every other public word are the rename item (G-C, below). The installers' shortcut icon
became the sharpened point in Graphite 0.1 (see the last section).

## The rename (G-C)

Graphite is the one public name of the workspace and its AI; the menu is "the menu". `version.NAME` is `Graphite`
(`SHORT` unchanged), so the window title reads Graphite, Home — Graphite or *file* — Graphite, and About, the wordmark, the
Leave dialog, the doctor's line and the launch failure say Graphite. The AI's words say Graphite and its pronoun is it: the
face, its tab and switch word, Today's card, the strip's destination word, Ask / Talk to / Message Graphite, the Work block,
"Graphite paused", "While Graphite was closed, it took …", new results "checked by Graphite", the agenda, the findings and
the model prompts ("You are Graphite…"). Program words follow: Graphite services, Exit Graphite, Graphite closed, the
Graphite service, Current Graphite host. Inventory: 673 literals read, 527 edits in 122 modules, 194 kept on purpose
(the list is in the G-C report's inventory).

Decisions:

1. Settings show Workspace and Assistant. During the pass the shipped release check compared every recorded setting
   definition byte for byte, so the definitions kept their words and a display table gave the settings page the public
   words (seven settings had Ledger, Slate or Hatch in a label, description or effect). Graphite 0.1 re-based the release
   check on its own record, so the definitions themselves now carry Graphite's words and the table is gone; the root keys
   `Ledger` and `Slate`, every settings key, default, kind and scope are unchanged, and `settings_registry.ROOT_NAMES` with
   `public(row)` still shows the two roots as Workspace and Assistant.
2. The AI switch (Operations ▸ AI admission) reads AI ON / AI OFF (tooltip and accessible name: new Graphite AI activity). "Graphite OFF" would
   read as the program going off.
3. Machine words stay and are shown in public words: the schedule reason `New Slate activity off` is shown as New Graphite
   AI activity off (`operations.PUBLIC_REASONS`); `Ledger services off` was already shown as the service summary.
4. Words already written stay readable: a condition card finds its result paragraph by block id, never by its words, so
   pages that say "checked by Slate" keep working; reasons stored before the rename ("Ledger closed") are shown as written;
   the face splits answers on both "(What Ledger knows:" and "(What Graphite knows:".
5. Kept on purpose: module, class, object and function names; operation names; settings keys and definitions; record
   actors and origins (SLATE, SLATE_MODEL, LEDGER); folder and file names on disk (Files/Slate, which Files explains as
   "Graphite's area (the Slate folder)", ~/Concern/Ledger, the Ledger menu file); signed release and manifest product
   identities ("Ledger & Slate"); the installer's file names, certificates and the application name; the knowledge seed's content and its
   model-facing label; file-format identities; the Struthio bird's history; "Hardware & Software Ledger" (a register); staC;
   the STRUTHIO game; the HATCH checkpoint name.
6. The strip's right column cap is 400 px at 14 pt (380 before; the same 1.4 ceiling): Graphite is about 30 px wider than
   Slate, and with G-B's proposed bold room for the checked destination word (applied here in `typebar_qt`) the right row
   stays whole from 14 to 20 pt. `ui_fit.PENDING` no longer lists the strip word.

Evidence: `tests_integrated/test_graphite.py` holds the rename guard tests: no
literal says "Ledger & Slate" except the listed compatibility identities; the window's modules say no Slate, Ledger or Hatch
except the listed kept words; the public name and internal identities; the settings roots shown as Workspace and Assistant;
words written before the rename stay readable; Today names the workspace; a new catalog's seed says Graphite and an older
one is shown so. `tools/check_rename_ui.py` (offscreen, 11 checks, 10 captures, `graphite-rename-ui.json` in
`build/graphite01_ui/rename`): Today with the head and strip, the menu, the face titled Graphite, the settings roots, the
cabinet with its concern, ledger and memory drawers open, Existing views and the `ledger` and `operations` dossiers, at 1920
by 1200 and 1366 by 768, over a catalog seeded before the rename. Every visible word is read, labels and the items of every
visible tree and list included (none says Slate, Ledger or Hatch, in any case, except lowercase identities such as
ledger.open), and every head, centre and strip word is whole (tools/ui_fit).

## Finished in Graphite 0.1

What the pass left open, and what changed with the release (November 6, 2026):

- **The centre at 1366 by 768 and 18 pt.** The right column's floor now gives the centre only what it lacks
  (`typebar_qt.CENTRE` 400, `centre_floor()`, `yield_to_centre()`, `TypeBar.least_width`/`least_need`): the quiet words of
  the strip yield first, so Home no longer scrolls sideways and Follow latest and Return thread · N stay whole
  (`tests_integrated/test_frame.py`, a narrow window takes the quiet words before the centre). Not yet: at 1280 by 720 and
  18 pt the centre is still about 67 px short; the left column would have to yield its quiet words too.
- **Bold room.** Cabinet, Machine and Settings (`settings_qt`), Logical cabinet and Existing views (`cabinet_qt`), Operations
  and the face row's Context and Graphite (`operations_qt`) keep room for their bold state (`keep_bold_room`), and
  `tools/ui_fit.PENDING` is empty: any clipped word anywhere in the window fails check_frame_ui, check_finder_ui and
  check_rename_ui.
- **Today's workspace name.** `TodayPage.fill` reused `name` in its Continue loop, so the greeting and THIS WORKSPACE showed
  the last recent file's name; the loop variable is now `title`.
- **Start and install words.** `START_MINIMAL_DEBIAN.sh` prints `Graphite ended with status N`. The installers show
  Graphite: `setup_arc1.APP_NAME` (the shortcuts, the Apps & Features entry, setup's messages; Windows backups keep their
  earlier folder, `BACKUP_FOLDER`), and `unix_setup`'s launcher Name, the macOS bundle's CFBundleName and display name, and
  the Fluxbox menu entry (their file names stay, so an earlier install is updated in place). The shortcut icon is the
  sharpened point: `branding/graphite/graphite.ico` (7 sizes, 16 to 256 px, written by `graphite_brand.icon_files`) and
  `graphite_icon_256.png`.
- **The catalog seed.** A new concern catalog titles its `ledger` row Graphite (the id stays) and the `operations` summary
  says Graphite maintenance; a catalog made before the rename keeps its stored words and is shown as Graphite while the
  owner has not retitled it (`concern_catalog.shown`, the one place old seed words are mapped for display).
- **Settings words.** The definitions carry Graphite's words (decision 1 above).
- **Version.** `workbench/version.py`: NAME Graphite, VERSION 0.1.0, SHORT 0.1, so the title reads Graphite 0.1.
- **Under load.** check_graphite_ui (keyboard focus back on the cat) and check_paper_ui (a colour-share measure) wait for
  their condition instead of a fixed time.
