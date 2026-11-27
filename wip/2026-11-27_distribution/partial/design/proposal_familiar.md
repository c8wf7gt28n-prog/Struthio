# Graphite 1.1 · proposal "Familiar"

*One of three independent proposals, starting from the owner's hands. 27 November 2026. A design: nothing here was run.*

## 1. The idea in five sentences

1. **One bar** runs along the bottom of the screen, above every app: Start, one line that searches and commands, the open windows, Kas with HALT, the tray, the clock. It replaces 1.0's dock and foot.
2. Behind the windows is **the Desktop**, Graphite's own window: an Explorer whose third view is the bulletin board, with Settings (the Control Panel) and the Task Manager as its other rooms.
3. **Kas is a colleague on the bar**, not a fifth of one window: her chip gives her state as a word and a shape, her panel slides in from the right edge over any app, and a window she works in wears her frame.
4. **Your words work** (`dir`, "control panel", `E:`), with the Linux word shown beside yours, so the bridge teaches itself away.
5. What is seen keeps to one accent, one type family and motion that means something; each thing is also **a name to type, a line in a text file, a part to replace**.

## 2. The screen

| Place | Its one job |
|---|---|
| **The bar** (bottom, 44 px; 40 at 1366) | the session, always within reach |
| **Head** (32 px) | what can be done here: File Edit View Go Tools Help |
| **Navigation pane** (left, 256 px) | where things are |
| **Centre** | the folder or the thing: one bar, tabs, List · Icons · Board, the split |
| **Details pane** (Alt+P, 320 px) | the selected thing: preview, facts, connections |
| **Kas's panel** (the screen's right edge, 380 px) | who works with you |

Start, flyouts and cards rise from the part of the bar that owns them, and nowhere else. Chrome falls from about 188 px in 1.0's frames (dock, head, centre bar, foot) to 116.

1920x1200, her panel pinned, the details pane open:

```
+----------------------------------------------------------------------------------------------------------+
| File  Edit  View  Go  Tools  Help                                                                        |
+--------------+--------------------------------------------------------+---------------+------------------+
| QUICK ACCESS | [<][>][^]  Home > Documents             [List|Icons|Board]  [Find here]| Kas  model ready |
|  Home        | [ Documents x ][ Budget 2026.ods x ][ + ]                              | o QUIET          |
|  Documents   +--------------------------------------------------------+---------------+------------------+
|  Downloads   | Name                  Modified     Type      Size Links| DETAILS       | WAITS FOR YOU    |
|  Pictures    | Taxes 2026            26 Nov 17:20 Folder              | [ preview ]   |  (only when      |
| DESK         | Budget 2026.ods       27 Nov 21:02 Sheet    41 KB 3- 2:| Budget 2026   |  something does) |
|  Sources     | Letter to council.odt 26 Nov 17:20 Text     10 KB 2-   | Sheet, 41 KB  +------------------+
|  Sheets      | Washing manual.pdf    02 Nov 09:11 PDF       3 KB      | revision 4    | the exchange     |
|  Findings    |                                                        | CONNECTIONS   | ACTIVE WORK      |
| THIS COMPUTER|                                                        | - Groceries   | NEXT STEPS       |
|  System (C:) |                                                        | - Summary     |                  |
|  HOLIDAY (E:)|                                                        | : Budget 2025 |                  |
| Recycle Bin  | 4 items, 1 selected, 41 KB                             | [Open board]  | > ask Kas...     |
+--------------+--------------------------------------------------------+---------------+------------------+
| Start | Search or command | [Graphite][Firefox][..]  | Kas o QUIET [^ HALT] | net vol bat | 21:04 27 Nov |
+----------------------------------------------------------------------------------------------------------+
```

1366x768, details pane closed, her panel slid over, a permission card risen from her chip:

```
+----------------------------------------------------------------------------+
| File  Edit  View  Go  Tools  Help                                          |
+--------------+-------------------------------------------------------------+
| QUICK ACCESS | [<][>][^] Home > Downloads       [List|Icons|Board] [Find]  |
|  Home        +------------------------------------------+------------------+
|  Documents   | Name              Modified   Type   Size | Kas    * WORKING |
|  Downloads   | invoice-001.pdf   ...                    | Tidy Downloads   |
|  Pictures    | invoice-002.pdf   ...                    |  v 1  v 2  > 3   |
| DESK         |         +--------------------------------+  <> 4 needs you  |
| THIS COMPUTER|         | <> KAS NEEDS YOUR PERMISSION   | [Stop this task] |
|  System (C:) |         | Move files inside ~/Downloads  |                  |
| Recycle Bin  |         | this task only, 11 files       | > ask Kas...     |
|              |         | [Allow for this task] [Not now]+------------------+
+--------------+---------+--------------------------------+------------------+
| Start | Search... | [G][F][W]  | Kas <> WAITS (1) [^ HALT] | n v b | 21:04 |
+----------------------------------------------------------------------------+
```

In the sketches `o` stands for ○, `*` for ●, `<>` for ◆, `^` for ▲, `v` for ✓, `-` for a recorded link and `:` for a possible one.

## 3. The first minute, the first day, the first week

**Minute.** Eyes go lower left and lower right: a Start mark, a clock. *Windows key*: Start rises, the cursor already in the line. He types `contr`; the top row reads "Settings · Control Panel in Windows"; Enter. *Win+E*: Home as a Details list. Right-click on a file: Open, Open with, Cut, Copy, Rename, Delete, Send to, Ask Kas, Properties. One card, once, above the clock: "Coming from Windows? Your keys work here. Kas, on the bar, changes nothing without your press; HALT stops her, and only her."

**Day.** A stick goes in: "HOLIDAY (E:) · Open · Safely remove". He drags photos to Pictures (across drives a drag copies, as in Windows). He types `cmd`: the Terminal; `dir` lists, and a dim line says `dir → ls -l`; `e:`, `copy`, `cls` and `ipconfig` all answer. He types "tidy my downloads" in the bar and chooses the last row, *Ask Kas*: her panel slides in with a 16-step plan; a card rises from her chip, "Move files inside ~/Downloads · this task only"; he presses **Allow for this task**; the chip counts "● WORKING 5 of 16", then "✓ DONE (verified) · Undo all".

**Week.** The dim lines have taught `ls`, `cp`, `ip`; he turns them off. He pins Writer to the bar, drops a script into `~/.config/graphite/sendto/` and finds it under Send to, adds `F5 = files.copy-to-other-pane` to `keys.conf` for his Norton hands, revokes one of Kas's permissions, and notices the Links column: the budget sheet says `3─ 2┄`; Ctrl+B shows it among what it feeds.

## 4. Files: the Explorer and the board

- **Navigation pane:** Quick access (Home, Documents, Downloads, Pictures, your pins); Desk (Graphite's records); This computer (System (C:) is `/`; each drive with letter, label and capacity bar); Recycle Bin. The root is one press down, never the first thing seen.
- **List** is Home's default view: Name, Modified, Type, Size, Links. Headers sort; typing jumps; Ctrl and Shift select; Ctrl+C/X/V, F2, Del, Ctrl+Z. Every act is a line with Undo, a batch one Undo. **Icons** shows thumbnails.
- **Open** means the default app, as in Windows. Graphite's viewer is an app among apps, the default for PDFs, pictures and text; Desk records open in their working view. Space is a quick look.
- **Board** is the third view, never an empty default. The Links column shows counts only where connections exist (`3─` recorded, `2┄` possible). Ctrl+B puts the selected thing in the middle with its neighbours: 1.0's board, unchanged. Tiles hop; the address bar follows; Back returns. Desk places open on the Board; each place remembers its view. The details pane lists the same connections as words.
- **Home** (a fresh tab) shows folders, drives and recent files: never a blank centre.
- **Properties** (Alt+Enter): General · Connections ("Why am I shown?") · Revisions · Permissions (the file's, in words; Kas's grants that touch it).
- **Send to** lists the executables in `~/.config/graphite/sendto/`. The split gains "Copy / Move to the other pane".

## 5. Apps, windows, the bar, the tray and the clock

- **Window buttons:** Graphite first, then pinned and running apps; icon and title (icon only at 1366). Running is an underline, active a filled plate, "wants you" a ◆. Right-click: Pin, Close (the app may ask; nothing is forced).
- **Windows:** title left; minimise, maximise, close at the right, in a Fluxbox style written from the tokens. Win+arrows halve; Alt+Tab draws Graphite's own switcher. Apps still start in sessions of their own.
- **Tray**, in fixed slots so nothing shifts: network, sound, battery, drives, notifications. Each opens a flyout with the real control, its state as a word (CONNECTED, MUTED, SAFE TO REMOVE) and "More in Settings →". CPU and RAM figures are an optional module.
- **Clock:** time over date; a press shows the month and the notifications kept. Toasts rise above it and never take the keyboard. The corner beyond it shows the Desktop.

## 6. Search, the launcher and commands

Start and search are one thing: the bar's line. *Win* opens Start: pinned apps, recent files, All apps ›, and the session row (Lock, Sleep, Restart, Shut down, Log out). Typing fills sections (Apps · Settings · Files · Desk · Commands), then three fixed last rows: **Run in Terminal** · **Open address** · **Ask Kas**. Enter takes the top row; a request to Kas is never taken by default, it is chosen.

- **Say it in Windows.** Synonyms answer "control panel", "device manager", "cmd", "notepad" and "regedit" ("there is no registry: settings are files; open the folder"), and show the real name beside the match.
- **Prefixes** for sure hands: `>` a command, `$` the shell, `?` Kas, `=` a sum or a Graphite line, `~` `/` `E:` a place.
- **Every command has one name** (`settings.sound`, `session.lock`): it runs from the line, from `graphite <name>` in any shell, from a key in `keys.conf`, from a script. The command may look, open, ask and halt; it can never grant, authorise or resume.

## 7. The Terminal and DOS words

Two forms of one shell. **The command line** (Win+`) is 1.0's console, rising from the bar to half the screen over any app: each command a block with its exit status and time. **The Terminal** (Ctrl+Alt+T, or `cmd`) is a full terminal window for `vim`, `top` and `ssh`.

Both read `~/.config/graphite/dos_words.sh`: `dir cls copy move ren md rd type more findstr tree ipconfig tasklist taskkill where set ver mem start explorer edit help`, and drive letters. `del` sends to the Recycle Bin. `format`, `fdisk` and `chkdsk` never run: they explain, and point to Settings ▸ Drives. After a DOS word one dim line says what ran (`copy → cp -i`), three times per word, then silence. The prompt reads `~/Documents>`. It is a text file: edit it, or delete it and the shell is plain Bash.

## 8. Settings and the system pages

One room, **Settings**, which answers to "Control Panel": categories on the left, the page on the right. System (About, Power, Drives, Session) · Display · Sound · Network · Devices · Personalisation (look, bar, Start, words) · Apps (defaults, installed, optional tools) · Time and language · Keys · **Kas** (her model, her dial, Permissions, what HALT holds) · Workspace. The Machine tab and "Settings ▸ This computer" merge here: 1.0 had two places for one thing.

Every page is real controls that take effect and read back, never 1.0's "write the value in the highlighted passage". At its foot, two quiet lines: the file (`~/.config/graphite/sound.conf`) and the command (`graphite set sound.volume 65`).

**Task Manager** (Ctrl+Shift+Esc): Processes (End task asks the app politely; Force asks you) · Performance (the equalizer's bars, as graphs) · Startup · Users (You, Kas) · **Kas**: her tasks, model, sandboxes and fetch, exactly the list HALT holds.

## 9. Kas

Her rules are untouched: the model proposes, the desk disposes; every change waits for your press or a grant in plain words; done means verified.

- **Where.** Her chip on the bar: "Kas", then one state word with its shape (○ QUIET, ● WORKING 5 of 16, ◆ WAITS FOR YOU, ✓ DONE, ‖ HELD). A press, or Win+K, opens **her panel** at the screen's right edge, over any app: pinned from 1600 px of width (apps make room), sliding over below that.
- **Plans.** A task is a card: title, state, its steps as a checklist in 1.0's one language (✓ done (verified), → sent, ○ prepared, ◆ needs your word, blocked: why), each with its one press, and the task's own Stop.
- **Permissions.** A card rises from her chip, above everything, never taking the keyboard, deaf for its first half second: what, where, for how long, in plain words. The main button is the narrowest scope ("Allow for this task"); wider ones sit under More. All grants live in Settings ▸ Kas ▸ Permissions, each with its uses and Revoke.
- **Journal.** On each task card (History); whole in Task Manager ▸ Kas.
- **Presence, no picture.** Her name and state on the bar; a thin line pulsing along her chip while she works; and **her frame**: the window she works in wears a 2 px outline with a tab, "KAS · typing in Writer · any key pauses her". After your touch, a card beside that window: "▮▮ Paused by your touch · Continue · Stop and put back". The network icon says "Kas: <site>" while she fetches.
- **HALT** stands beside her chip, green triangle and word, in the same spot at every size, above every app; beside her name it reads rightly: it stops her, never the computer. Pause, or Win+Esc, does the same from anywhere. Held, it reads ▶ RESUME; RESUME is a press, never a key, and her panel says "Nothing was restarted; each task has its own Resume."

## 10. Keys

| Key | Does |
|---|---|
| Win, Win+R | Start and search, Run: one line |
| Win+E, Win+I, Ctrl+Shift+Esc | Files, Settings, Task Manager |
| Win+D, Win+L, Win+X | the Desktop, lock, the power list |
| Alt+Tab, Alt+F4, Win+arrows | switch, close, halve or maximise |
| Win+A, Win+N, PrtSc | tray, notifications and calendar, screenshot |
| Win+`, Ctrl+Alt+T | command line, Terminal |
| Ctrl+Alt+Del | the session card |
| **Win+K; Pause or Win+Esc** | **Kas's panel and ask line; HALT** |
| Enter, Space, F2, Del, Shift+Del | open, quick look, rename, to the bin, delete for good (asks) |
| Ctrl+C/X/V/Z/A, Ctrl+Shift+N | as in Windows; new folder |
| Alt+Left/Right/Up, Backspace, F5 | back, forward, up; back; refresh |
| Ctrl+L or F4, Ctrl+F or F3 | address bar, find here |
| Ctrl+T/W/Tab, Ctrl+1/2/3, Ctrl+B | tabs; List, Icons, Board; the board of this |
| Alt+P, Alt+Enter, Shift+F10, F1 | details pane, Properties, right-click, Help |

Menus and tooltips show keys, quietly: right-aligned, mono, in the tertiary colour; Alt underlines the menu letters; buttons never carry them. One switch hides them all. The whole map is `~/.config/graphite/keys.conf`.

## 11. Type, colour, space and motion

Built on 1.0's tokens (`design_tokens.py`): extended, not replaced.

- **Type and space:** Inter and IBM Plex Mono stay, on the 4 px grid. The floor rises from 11 to 12 px; list rows 28 px; her panel's body 14/20; no target on the bar under 40 × 40.
- **Colour:** one rule added. Blue is yours (selection, focus, links); green is hers and what is verified; amber waits for you; red is danger. Each keeps its word and shape.
- **Looks:** Day launches; Night; **Auto** switches by the clock. Graphite and Kasandra become token sets too: a look is about fifteen lines in `~/.config/graphite/looks/`, so anyone can write a fifth; Settings measures its contrast and says which pairs fall short.
- **Motion and depth:** Start and flyouts rise 8 px in 160 ms; her panel slides in 220 ms; tiles ease in 240 ms. Reduce motion stills all of it. Shadows and round corners come with the optional compositor; without it, hairlines, square corners, and things appear at once.

## 12. What goes, and what is reversed

**Goes:** the top dock and the foot; the chooser Line · Terminal · Search · Web · Log; the left tabs Files / Machine / Settings; her column as part of the window; the row DO · DOUBT · TRACE · BRIEF · LINE · CHECK ALL (now right-click ▸ Ask Kas ▸, and typed words); "Full program" and "Save and Return" (Open with ▸, Ctrl+S, Ctrl+W); the long list of Graphite rooms in the open in Apps (one folder now).

**Kept:** no picture of Kas; "Apps", never Programs; Day as the launch look; the one language of states.

**Reversed**, each for the owner to strike:

1. *HALT upper left* → on the bar beside Kas. The upper left is covered whenever an app is in front, which is when her hand is at work.
2. *Apps upper right* ("our progman.exe menu") → Start, lower left, on the Windows key: where those hands go.
3. *No key printed on screen* (13 Nov) → shown in menus and tooltips. A person switching must see that his keys are honoured; one switch restores the rule.
4. *The tree from "This computer /"* → Quick access first. 1.0's first sight was mnt, nix, proc.
5. *DELETE as the bin's word* → "Recycle Bin" on new installs: a capital verb on a button reads as an act. The owner's profile and the Kasandra look keep DELETE (`words.conf`).
6. *The eight menus in the owner's words* → File Edit View Go Tools Help, over the same actions.
7. *Work happens in the centre; Apps the only way to a full program* (13 Nov) → a double-click opens the default app.
8. *The right-click's "up to four actions"* (14 Nov) → the Windows order, Properties last; Then › stays.
9. *The equalizer always in view* (13 Nov) → Task Manager; one line in `bar.conf` brings it back.
10. *Green circuit-trace tree lines* (0.5.1) → plain in Day and Night; kept in Graphite and Kasandra.

## 13. The build

Fifteen slices on `/home/user/Struthio/workbench/`. Order: 1, 2; then 3 to 9 side by side; 10, 11; 12; 13; 14, 15.

1. **Names, keys, the command.** New `command_table.py`, `global_keys.py`, `session_socket.py`, `fluxbox_files.py`, the `graphite` script; `windows_x11.py` (additions), `LS_XSESSION.sh`, `menus2.py` (keys from the table). Owns `windows_x11.py` and `LS_XSESSION.sh` until merged.
2. **The bar.** `system_dock_qt.py`, `windows_strip_qt.py`, new `bar_qt.py` with named slots; `design_tokens.py` (additions only). Later slices fill slots and never edit `bar_qt.py`.
3. **Start and the line.** `apps_qt.py` (the panel), `apps_catalog.py`, `search_reach.py`, `foot_line.py`; new `start_qt.py`, `synonyms.py`. Not `typebar_qt.py` (9).
4. **Tray, flyouts, clock.** New `tray_qt.py`, `flyouts_qt.py`; `notify_qt.py`, `net_meter.py`, `meter_cards.py`. Calls `machine_real.py`, never edits it.
5. **Explorer.** New `explorer_qt.py`; `computer_tree_qt.py`, `home_files_qt.py`, `files_qt.py`, `bulk_files_qt.py`, `cabinet_qt.py`, `trash_can_qt.py`, `thumbnails.py`. Not `board_qt.py`, not `centre_bar.py`.
6. **Settings.** `settings_qt.py`, `system_settings_qt.py`, `settings_registry.py`, `machine_room_qt.py`, `machine_qt.py`, `presentation_qt.py`, `hardware_settings_qt.py`; new `control_panel_qt.py`.
7. **Right-click, Properties, Send to.** `context_menu.py`, `object_context_qt.py`, `apps_qt.context_entries`; new `properties_qt.py`, `send_to.py`.
8. **Task Manager.** New `task_manager_qt.py`, `processes.py`; `equalizer_qt.py`, `desktop_header_qt.py` (its work list), `system_instruments.py`. Reads `assignments.py` and `halt.py`, edits neither.
9. **Terminal and DOS words.** `console_qt.py`, `console_runtime.py`, `typebar_qt.py`, `log_qt.py`; new `dos_words.py`, `terminal_app.py`.
10. **Centre bar, Board view, details pane.** `centre_bar.py`, `living_nav_qt.py`, `board_qt.py`, `split_qt.py`, `universal_viewer_qt.py`; new `details_pane_qt.py`.
11. **Kas on the bar.** `her_column_qt.py`, `waits_qt.py`, `halt_qt.py`, `grants_qt.py`, `her_hand_qt.py`, `hand_door_qt.py`; new `kas_panel_qt.py`, `kas_frame_qt.py`. Must not touch `halt.py`, `halt_gate.py`, `grants.py`, `assignments.py`, `agent_loop.py`, `hand_door.py`: her windows move, her rules do not.
12. **The Desktop's frame.** `arc_desktop.py`, `pane_qt.py`, `navigation_qt.py`, `desktop_header_qt.py`, `menus2.py`, `qt_app.py` (layout lines only), `empty_workspace_qt.py`. The only slice that edits `qt_app.py` and `arc_desktop.py`.
13. **Tokens 1.1 and looks.** `design_tokens.py`, `boss_theme.py`, `glyph_set.py`, `launch_look.py`, the Fluxbox style, the optional compositor line in `LS_XSESSION.sh`.
14. **Words and first run.** The synonyms' content, `phrases.py`, `guide_pages.py`, `handbook.py`, `a11y_names.py`, `docs/GUIDE_LIVING_DESKTOP.md` ("Coming from Windows"), `words.conf`.
15. **The walk.** X3's twelve sessions again with Windows hands, both sizes, four looks (`ux_gallery.py`, `preview_frames.py`); fixes in place, and a list proving every 1.0 action still has a home.

## 14. Risks, and what only real hardware can settle

- **Global keys by grab:** whether the ThinkPad's Windows key, Pause (often Fn+P) and Ctrl+Alt+Del arrive; apps that grab the same keys. Fallback: the same names bound in Fluxbox's keys file.
- **Two struts:** the bar below, her panel at the right. Whether Fluxbox keeps maximised and full-screen windows off them, and whether apps reflow cleanly when her panel is pinned.
- **No compositor by default:** shadows, fades and round corners need one; its cost on the Radeon and the battery is unknown.
- **Scale and lag:** title bars and the bar are drawn in pixels, so the ThinkPad panel's density decides the sizes; her frame may trail a dragged window.
- **New doors, old rules:** the bar's line, the `graphite` command and the risen cards are new ways in. X11 lets one app send presses to another; the audit must say whether a card can be pressed by anything but a hand.
- **Re-homing some two hundred actions** from eight menus to six: slice 15's list is the guard.
- **The owner may strike** reversals 3, 5 and 7 (the last also costs speed where LibreOffice starts cold); each is one line of configuration.
