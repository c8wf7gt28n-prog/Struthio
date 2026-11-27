# Graphite 1.1 · "Plain Sight" · the power-first proposal

*27 November 2026. One of three independent designs. Starting point: freedom. Read only; nothing in the tree was changed.*

## 1. The idea in five sentences

Graphite 1.1 has one grammar: **things** (files, apps, windows, settings, drives, Kas's tasks), **verbs** (the kernel's named operations) and **lines** that join them, and every button, menu row, panel and page on screen is a view of one of those. Anything visible answers one question, **Command…**, with the exact line it is or runs, and from there one press keeps it as a word, pins it, binds a key, schedules it or gives it to Kas. The shape is Windows': a bar along the bottom with Start, a Run line, the open windows, a tray and a clock; Files is an Explorer; a Control Panel holds every system page; the mouse alone reaches all of it. The finish is Apple's: one bar, one seat for Kas, one command bar per window, and command text folded away until asked for, so the power lies under the surface and never across it. Kas is the second user of the same grammar: she types the commands you could type, through the same kernel, you read her plan as a script before your press, and HALT stands beside her name over every app.

## 2. The screen

| Place | Its one job | Holds |
|---|---|---|
| **The bar** (bottom, 44 px, 40 at 1366; a dock window of its own, above every app) | the computer, always | Start · the Run line · pinned and open windows · workspaces (shown once a second one exists) · Kas's chip and HALT · tray: NET, VOL, BAT, drives, notices · clock |
| **Kas's seat** (right edge, 360 px, 320 at 1366; a panel of its own, beside any app) | who works with you | her name and cursor, Waits for you, the plan, her ask line; Journal and Grants as folds |
| **The Graphite window** (an ordinary window: it snaps, tiles and closes to the bar) | where things are, and working on them | Places on the left · tabs · one command bar · the view (Details, Icons, Board, a working view, a Control Panel page) · a status strip |
| **App windows** | your apps | Fluxbox frames in a style written from the look's tokens; close, maximise, minimise at the right |
| **The receipt** (one line above the bar's left end, 8 s, then kept in History) | what just happened | the words, Undo, and the command that ran |

The rule that replaces "nothing lives in two places": **a place for the hand, a name for the keyboard.** Each thing has one home on screen and one name the Run line knows.

```
1920 x 1200 · Kas's seat pinned
+--------------------------------------------------------------------------------+----------------------+
| Home | Taxes 2026 x | Budget 2026.ods x | +                              _ [] x | Kasandra ▮  ● WORKING|
| <  >  ^   Home > Documents > Taxes 2026      New v  Sort v  View v  Split   ... | tidying ~/Downloads  |
+-------------+----------------------------------------------+-------------------+ |----------------------|
| FAVOURITES  | Name                   Modified      Type Size| PREVIEW           | | WAITS FOR YOU · 1    |
|  Desktop    | bank-statement-10.pdf  27 Nov 14:02  PDF  81 K| [first page]      | | ◆ Allow Kas to move  |
|  Documents  |>council-tax-2026.pdf   26 Nov 09:10  PDF  40 K| council-tax-2026  | |   files inside       |
|  Downloads  | electricity-10.pdf     25 Nov 18:31  PDF  55 K| PDF · 40 KB       | |   ~/Downloads, for   |
|  Pictures   |                                               | Opens with Okular | |   this task only.    |
| DRIVES      |                                               |                   | | [Allow] [Commands]   |
|  HOLIDAY E: |                                               | CONNECTED · 3     | |----------------------|
| THIS        |                                               | ■ Budget 2026.ods | | PLAN · 16 steps      |
|  COMPUTER / |                                               | - - possible: 2   | | ✓ 1 make folder PDFs |
| DESK        |                                               | [Open board]      | | → 5 move invoice-01  |
| DELETE      |                                               |                   | | ○ 6 move invoice-02  |
+-------------+----------------------------------------------+-------------------+ | Journal · Grants     |
| 3 items · 1 selected · 40 KB       @files:~/Documents/Taxes 2026 | sort name   | | > ask Kas...         |
+--------------------------------------------------------------------------------+----------------------+
| Renamed council-tax-2026.pdf · Undo · ren council-tax-2026-27.pdf council-tax-2026.pdf                |
| [Start] [Run or find anything     ] | Files  Writer  Firefox | 1 2 | Kas ● WORKING  ▲ HALT | NET VOL BAT  14:32 |
+-------------------------------------------------------------------------------------------------------+

1366 x 768 · seat closed (her chip opens it over the right edge) · preview off
+------------------------------------------------------------------------------+
| Home | Taxes 2026 x | +                                               _ [] x |
| <  >  ^   Home > Documents > Taxes 2026           New v  Sort v  View v  ... |
+------------+-----------------------------------------------------------------+
| FAVOURITES | Name                      Modified       Type    Size           |
|  Documents |>council-tax-2026.pdf      26 Nov 09:10   PDF     40 KB          |
|  Downloads | electricity-10.pdf        25 Nov 18:31   PDF     55 KB          |
| DRIVES     |                                                                 |
| THIS COMP. |                                                                 |
| DESK       |                                                                 |
| DELETE     | 3 items · 1 selected          @files:~/Documents/Taxes 2026     |
+------------+-----------------------------------------------------------------+
| [Start] [Run or find...  ] | Files  Writer | Kas ◆ 1 WAITS  ▲ HALT | NET VOL  14:32 |
+------------------------------------------------------------------------------+
```

## 3. The first minute, day and week of a Windows-and-DOS person

**Minute.** The session opens on a quiet Day wallpaper, the bar, and the Graphite window at **Home**: four panels (Start here, Recent, Drives, Desktop). They press the Windows key: Start rises from the lower left with the cursor already in the Run line. They type `wri`; LibreOffice Writer is the first row; Enter. Writer appears on the bar. Windows+E brings Files at Home in Details view. F2 renames; Delete sends to DELETE; the receipt says "Deleted letter.odt · Undo" with `del letter.odt` under it. They type `dir` in the Run line: the first row reads "Run: dir, as ls -l"; Enter shows the listing.

**Day.** Wi-Fi from the tray's NET (a list, a password, CONNECTED). A stick goes in: a notice, "HOLIDAY (E:) connected · Open · Eject". Photos copied with Ctrl+C, Ctrl+V. Right-click a PDF ▸ Open with ▸ Always. At dusk the look turns to Night by itself (a schedule line they can read). They type "tidy my downloads": the last row is **Ask Kas →**; her seat opens with a 16-step plan; **Commands** shows it as sixteen `md` and `move` lines; **Allow all 16**; each step ticks ✓; one Undo puts everything back.

**Week.** In Downloads they filter by "invoice", press Command…, and see `@files:~/Downloads | where name has invoice | sort date`; **Keep as a word** `invoices`; **Pin to Start**; **Key…** Ctrl+Alt+I. They schedule `backup` for Fridays at 17:00: on Friday the tray says "Backup is ready: 12 files · Run". They open `keys.conf` from Control Panel ▸ Keys ▸ Open the file, change a line, save: "Keys reloaded · 1 change". Workspace 2 gets tiling for terminal work. By Friday the Terminal has shown `ls -l` under `dir` often enough that they type `ls`.

## 4. Files: an Explorer that can become the board

Files is an Explorer first. **Places**: Favourites (Desktop, Documents, Downloads, Pictures, Music, Videos; drag a folder in), Drives (label and letter), This computer / (the root, one press), Desk (the workspace's records), DELETE. **Views**: Details (sortable columns, the default), Icons (real thumbnails), Board. Windows selection (Ctrl, Shift, rubber band), drag and drop, cut, copy, paste, one Undo per batch, Properties (Alt+Enter), an address bar that takes a typed path, tabs, and a two-pane split.

The **board is a view, not a room.** The preview pane carries the board in small: "Connected · 3", each neighbour with its state shape, solid for recorded, dashed for possible. Ctrl+B (or View ▸ Board) grows it to the full board in the same tab, with the same focus; Escape returns to the list at the same row. A Desk record opens on its board by default, because there the links are the point; a household PDF opens in Details, and never shows a lonely tile. A board is also a line (`this | links | board`), so it can be a Home panel.

The status strip ends with the view's own line in mono; clicking it opens the command card. The filter box, the sort and the columns all rewrite that line, so the owner learns the grammar by watching the mouse write it.

## 5. Apps, windows, the bar, the tray and the clock

**Start** is the launcher: pinned tiles (apps, folders, words), All apps by category (Graphite's own tools folded under one heading; engineering tools only when a project is attached), and the power group (Lock, Sleep, Log out, Restart, Shut down). The bar's middle is a taskbar: pinned apps and open windows, the active one underlined, a window Kas works in marked `⌐ Kas`; middle-click closes, right-click gives Close, Move to workspace, Pin, Command…. Windows snap by drag to an edge or Windows+arrows; Alt+Tab shows a row of windows. **Workspaces** stay out of sight until Ctrl+Windows+D makes a second. **Tiling** is a per-workspace switch for people who want it: new windows take a tile (main and stack). The **tray**: NET (networks), VOL (slider, output), BAT (percent, time left), drives (Eject), notices; each icon carries its word in a tooltip and opens its Control Panel page. The **clock** opens a month calendar with the kept notifications and the schedule under it. The meters live in **Task Manager** (Ctrl+Shift+Esc): processes, End task, CPU, GPU, RAM, disk.

## 6. Search, the launcher and commands: one line

Start, Run and Search are one surface. Typing ranks across Apps, Files (names in Home and the Desk), Settings, Commands (every verb, in plain words), Words (your own tools), open Windows, and exact maths (`= 12.50 * 3` gives 37.50 with its receipt); the last row is always **Ask Kas →**. Enter takes the first row; Right-arrow opens a row's actions (Open, Open with, Show in folder, Pin, Key…, Command…). Prefixes are optional shortcuts for the same thing: `>` shell, `/` a verb by name, `@` a thing by address, `=` maths.

The **command card** is the signature: on anything, right-click ▸ Command… (Ctrl+.) shows its line in mono with what it does in words, and five presses: Copy · Keep as a word · Pin · Key… · Schedule… · Give to Kas…. Words take slots (`word invoices <folder> = @files:<folder> | where name has invoice`). The clock, like Kas, proposes: a scheduled read runs; a scheduled change is prepared at its time and waits for one press, unless a grant in plain words lets it go ahead.

## 7. The Terminal and DOS words

Terminal (Windows+T) is a real terminal (xterm dressed from the look's tokens, IBM Plex Mono) running the owner's bash with a generated file of **DOS words**: `dir copy move del ren md rd type cls more find tree attrib ipconfig tasklist taskkill ver help`, backslashes accepted, `C:` for /, `E:` for a drive. Each prints one quiet line before its output, `ran: ls -l --group-directories-first`, so the Debian command is taught every time. `del` sends to DELETE (it says so); `format` refuses and opens Storage. The table is `dos.words`, a readable file; `dos off` turns the words off. The Run line reads the same table. Graphite's own doors answer in the Terminal too: `graphite do files.move a b`, `graphite line '…'`.

## 8. Settings and the system pages: Control Panel

One Control Panel, opened from Start, Windows+I, or by typing "control panel". A grid of categories with a search line: **System** (About, Updates, Storage, Power, Date and time, Language and keyboard, Users), **Devices** (Screens, Sound, Printers, Bluetooth, Mouse and touchpad), **Network**, **Look** (look, wallpaper, bar, text size, density), **Apps** (installed, default apps, startup), **Files** (DELETE, hidden files), **Keys**, **Kasandra** (her model, her hand, Grants, Journal), **Privacy** (what left this computer: nothing, and the network log). Every page has one anatomy: the state in words, the controls, and a quiet foot row, **Command · File**, giving the equivalent line (`set sound.volume 65`), the Debian command ("same as: wpctl set-volume …") and the file that holds it. Machine and Settings merge here.

Everything configurable is text in `~/.config/graphite/`: `keys.conf`, `bar.conf`, `menus.conf`, `places.conf`, `dos.words`, `schedule`, `looks/*.look`, `panels/*.line`, `words/*.line`. Files are watched; a bad line is refused in words and the last good file kept. Grants and the journal are readable as text but written only by the desk.

## 9. Kas

**Where.** Her seat on the right edge of the screen, beside whatever is in front (Windows+K, or her chip on the bar). At 1366 it opens over the edge instead of taking room.

**Presence without a picture.** Her name with a cursor, `Kasandra ▮`: steady when quiet, blinking while her model writes, with one line of what she is doing now; her state word and shape; and **her mark**, `⌐ Kas`, on whatever she touches: the window she works in, the file rows she moves, the bar entry. She is seen where she acts.

**Plans.** A plan card: numbered steps in plain words with the state shapes of 1.0; **Commands** unfolds each step into the line it will run. A finished plan can be kept as a word; a word can be given to her as a tool.

**Permissions.** A sentence first, its formal line second: "Allow Kas to move files inside ~/Downloads, for this task only." `grant kas files.move in ~/Downloads for task 12`. Allow · Not now. Waits for you never folds; her chip counts it (◆ 1 WAITS) over any app.

**Journal.** A fold in her seat, a page in History (filter: you, Kas, the clock), and a text mirror, `~/.local/state/graphite/kas/journal.log`, that `type` or `tail -f` can follow.

**HALT** stands on the bar at her chip's right: the green triangle and the word, RESUME ▶ while held, the Pause key anywhere. It stops her work and nothing else. Her rules do not move.

## 10. Keys

Global (written into Fluxbox's keys file from `keys.conf`, so they work over any app): Windows or Ctrl+Esc Start · Windows+R Run · Windows+E Files · Windows+D show the desktop · Windows+L lock · Windows+I Control Panel · Windows+T Terminal · Windows+K Kas's seat · Pause or Windows+Esc HALT · Alt+Tab switch · Alt+F4 close · Windows+arrows snap · Windows+1…9 bar entries · Ctrl+Windows+Left/Right workspace · Ctrl+Windows+D new workspace · Windows+Shift+T tiling · Ctrl+Shift+Esc Task Manager · PrtSc screenshot · Windows+/ the keys sheet.

In Files: Enter open · F2 rename · Delete · Shift+Delete (asks) · Ctrl+C/X/V/Z/A · Ctrl+T, Ctrl+W tabs · Ctrl+Shift+N new folder · Alt+Left/Right/Up · F5 refresh · Ctrl+L address · Ctrl+F find here · Alt+Enter Properties · Alt+P preview · Ctrl+B board · Ctrl+\ split · F6 other pane · Ctrl+. Command… · Alt or F10 the menu bar. With `commander = on`, F5 F6 F7 F8 copy, move, make and delete across the split.

No key ever allows a step for Kas: Allow is pressed with the focus on it. **Menus, Run rows and tooltips show keys**, right-aligned in quiet mono, read from `keys.conf`; one switch hides them.

## 11. Type, colour, space and motion

**Built on 1.0's tokens** (`design_tokens.py`): Inter and IBM Plex Mono, the Day and Night colours, the 4 px grid, radii and elevations stay. Added: a `command` role (Plex Mono 12/16 on the raised plate), bar and seat sizes, two densities (rows 28 or 24), her mark, a wallpaper. Tokens are exported as `.look` files; the Fluxbox style, xterm's resources and the GTK light or dark choice are written from the same file, so app windows match. Graphite and Kasandra become `.look` files (palette, faces); Auto follows the clock. Motion: 120 ms for Start, 160 for press, 220 for panels, a 100 ms outline before a snap; nothing loops; Reduce motion stills all. Command text appears in four places only: the status strip, the receipt, the command card and her unfolded plan.

## 12. What goes, and what is reversed

**Gone from 1.0:** the head; the top dock; the foot and its five-mode chooser (Log becomes History); the meter row; the left tabs; the equalizer; the six-command row (they are verbs on the right-click and in Run); NEXT STEPS and FINDINGS as fixed sections (the plan card; a `findings` panel); the older rooms under Arrange; ⊕; "Save and Return", "Full program" (Save and close; Open in Okular); engineering verbs on household files.

**Owner's decisions reversed:**
1. *HALT upper left* → on the bar beside Kas. Upper left is inside one window and vanishes under any app; here it is over all of them, next to what it stops.
2. *No key printed* → keys shown. Keys are now the owner's to edit; a binding that is not shown cannot be learned or checked.
3. *The tree from "This computer /"* → Favourites and Home first, the root one row below. The first start showed /sbin before Documents.
4. *Apps, upper right* → inside Start, lower left; still Apps, never Programs.
5. *The eight menu names* → File Edit View Go Tools Help behind Alt; `menus.conf` restores the old names in one line.
6. *The board as the centre's home* → a view, the default only for Desk records.
7. *Line · Terminal · Search · Web · Log* → one Run line.
8. *`prompt` as the empty hint* → "Run or find anything".
9. *The looks' painted character* (trace tree, glow) → options inside a `.look`.

Kept: DELETE, no picture of Kas, every state's word and shape, all of her rules.

## 13. The build: sixteen slices, in order

1. **Grammar index.** New `command_index.py`, `graphite_cli.py`; reads `engineering_kernel.py`, `tools_registry.py`, `settings_registry.py`, `apps_catalog.py`, `capability_catalog.py`; slots in `stac_words.py`. Changes no dispatch.
2. **Config files.** New `config_files.py`; `session_settings.py`, `workspaces.py`. Owns `~/.config/graphite/`.
3. **Session and X11.** `LS_XSESSION.sh`, `START_OFFICE.sh`, new `fluxbox_files.py`, `windows_x11.py` (move, size, state, desktops). Owns all X atoms; others call it.
4. **The Graphite window's frame.** `qt_app.py`, `shell2.py`, `arc_desktop.py`, `desktop_header_qt.py`, `centre_bar.py`, `menus2.py`. Lands alone; later slices enter these files by one hook each.
5. **The bar.** `system_dock_qt.py`, `windows_strip_qt.py`, new `bar_qt.py`, `tray_qt.py`; `meter_cards.py`, `net_meter.py`, `notify_qt.py`, `halt_qt.py` (placement only).
6. **Start and Run.** New `run_qt.py`; folds `apps_qt.py`, `foot_line.py`, `search_reach.py`, `typebar_qt.py`. Not `shell2.py`.
7. **Files as Explorer.** `finder_qt.py`, `computer_tree_qt.py`, `navigation_qt.py`, `places.py`, `home_files_qt.py`, `bulk_files_qt.py`, `thumbnails.py`, `trash_can_qt.py`, `context_menu.py` (owner of that file).
8. **Board as a view, preview pane.** `board_qt.py`, `living_nav_qt.py`, `depths_qt.py`, `split_qt.py`, `universal_viewer_qt.py`.
9. **Command card and receipts.** New `command_card_qt.py`, `receipt_qt.py`; `agenda.py`, `chain_menu.py`; one provider row in the context menu, through slice 7's hook.
10. **Terminal and DOS words.** New `dos_words.py`; `console_qt.py`.
11. **Control Panel.** `settings_qt.py`, `system_settings_qt.py`, `machine_room_qt.py`, `machine_qt.py`, `system_instruments.py`; reads `machine_real.py`; new pages as the audit names them.
12. **Kas's seat.** New `seat_qt.py`; `her_column_qt.py`, `waits_qt.py`, `grants_qt.py`, `objective_plan_qt.py`, `hand_door_qt.py`. Never `assignments.py`, `grants.py`, `halt.py`, `halt_gate.py`.
13. **Looks as files.** `design_tokens.py`, `boss_theme.py`, `qt_theme.py`, `theme2.py`, `launch_look.py`.
14. **Workspaces, snap, tiling, switcher.** New `tiling.py`, `switcher_qt.py`; through slice 3's calls.
15. **Home panels and first run.** New `panels_qt.py`; `home_qt.py`, `empty_workspace_qt.py`, `guide_pages.py`.
16. **Sweep.** `a11y_names.py`, `state_words.py`; words, frames in every look at both sizes.

Slices 1 to 4 run first (1 to 3 in parallel); 5 to 13 in parallel after 4; 14 to 16 last.

## 14. Risks, and what only real hardware can settle

- **Slice 4 is the dangerous one**: `qt_app.py` and `shell2.py` are 9,400 lines, untested by rule. If it slips, the bar and the seat still stand over the 1.0 window.
- **The cockpit.** Command text will try to creep onto every surface; the four-places rule must be held in review.
- **Honesty of "ran:".** Many system verbs go through D-Bus, not a command; those say "same as:", never "ran:".
- **A bad `keys.conf` must never lock the owner out**: Start, HALT and Control Panel cannot be unbound.
- **The clock and Kas share the Grants page**; the wording must keep whose permission is whose.
- **Only the ThinkPad can settle:** whether Fluxbox honours a bottom and a right strut together and reloads keys cleanly; a lone tap of the Windows key (Ctrl+Esc is the sure fallback); Pause on a keyboard without one (Fn+P); the seat taking the keyboard beside a focused app, and "a touch stops her" there; two screens; suspend and lock with dock windows up; GTK apps matching the look; xterm's type at the panel's density; real Wi-Fi, sound, battery and drives in the tray; the 35B's speed deciding whether her cursor reads as alive.
