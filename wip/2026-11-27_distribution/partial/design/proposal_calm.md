# Graphite 1.1 · "Calm": one bar, one line, your content

*One of three independent proposals; this one starts from grace. 27 November 2026. Nothing here is built, and nothing
of it has been seen on the ThinkPad.*

## 1. The idea in five sentences

1. At rest the screen holds one bar at the bottom and your content above it; the side list, Kas's sheet, the terminal and
   the menus come when called and leave when done.
2. The bar is where a Windows hand already goes (Start, a line to type in, open windows, the clock), and it carries
   Kas's presence and HALT above every app.
3. The one line (the Windows key) finds and does everything: apps, files, settings, commands, sums and questions for
   Kas; every row says what Enter will do.
4. Linux is one gesture away: F12 drops a real terminal from the top edge, and every action carries the command
   behind it.
5. Kas's rules do not move; only her furniture does: a quiet mark in the bar, a card in plain words when she needs your
   press, a sheet when you want to see her work.

## 2. The screen

| Place | Its one job | Holds |
|---|---|---|
| **Bar** (bottom, 44 px, above every app, its own process) | the session | Start · the line · open windows · Kas's mark · HALT · tray · clock |
| **Desk** (all the rest: Graphite's window) | one thing, large | Files in four views, a document or a Settings page; tabs when two are open; the split |
| **Content bar** (top of the desk, 44 px) | where you are | Back, Forward, Up · the address · Find here · view · ⋯ |
| **Side list** (left, 240 px; a rail at 1366; Ctrl+B) | where things are | Places, This computer, Workspace; in Settings, the categories |
| **Details** (right, 320 px; Alt+P) | what the chosen thing is | preview, facts, Connected |
| **Start** (rises from the bar; Win) | find and do | pinned apps, recent files, the session row; results |
| **Kas's sheet** (from the right; Win+K; can be pinned) | her work, by what needs you | Waits for you · Now · Conversation |
| **Terminal** (from the top; F12) | the shell | your own shell, DOS words |
| **Menus** (Alt or F10) | every command, with its key | File · Edit · View · Go · Tools · Kas · Help |

Nothing lives in two places. Measured on 1.0's frames, the content area grows from 1126×1043 to 1680×1112 at 1920×1200
and from about 690×610 to 1318×688 at 1366×768; the split stands side by side again.

```
1920x1200 · solid: at rest · dotted: comes only when called
+------------------------------------------------------------------------------------------------+
| <  >  ^   Home > Documents > Taxes 2026             Find here     Icons v     Board 3     ...  |
+---------------+......................................................+.........................+
| Home          :  TERMINAL (F12) drops from the top edge              :  KAS  (Win+K)       pin :
| Desktop       :  ~/Documents/Taxes 2026 $ dir        (dir is ls -l)  :  Waits for you          :
| Documents     +......................................................:   <> move files in      :
| Downloads     |                                                      :      ~/Downloads [Grant]:
| Pictures      |   bank-2026-10.pdf   council-tax.pdf   bill-10.pdf   :  Now · Tidy Downloads   :
| Bin           |                                                      :    v 1 done (verified)  :
| This computer |                                                      :   <> 2 needs your grant :
|   System /    |                                                      :  Conversation           :
|   HOLIDAY     |                                                      :  Journal Grants Findings:
| Workspace     |      ( Moved 3 files to Taxes 2026 · Undo · >_ )     :  > ask Kas              :
+.................................+                                    +.........................+
: START (Win)  pinned · recent    :                                                              |
: results as you type             :                                                              |
: Lock  Sleep  Restart  Shut down :                                                              |
+------------------------------------------------------------------------------------------------+
| #  [ find, run or ask ]  Files  Writer  Firefox      ||. Kas o Quiet   ^ HALT   : o ) =  14:02 |
+------------------------------------------------------------------------------------------------+
# Start · ||. her pulse · o Quiet · <> waits for you · ^ HALT · : o ) = vitals, network, sound, battery
```

```
1366x768 · the side list is a rail; Kas's card has risen from her mark
+--------------------------------------------------------------------+
| <  >  ^   Home > Downloads             Find here    List v    ...  |
+----+---------------------------------------------------------------+
| Ho |  Name                      Changed         Size     Kind      |
| De |  invoice-2026-001.pdf      26 Nov 17:20    933 B    PDF       |
| Do |  invoice-2026-002.pdf      26 Nov 17:20    940 B    PDF       |
| Dw |  IMG_2041.jpg              24 Nov 09:02    2 MB     Picture   |
| Pi |                                                               |
| Bi |      ( 48 chosen · Move to… · Copy to… · Delete )             |
| PC |                      +........................................+
| Ws |                      : <> Needs your grant · Tidy Downloads   :
|    |                      : Kas asks to move files in ~/Downloads, :
|    |                      : for this task.   [Grant]   [Not now]   :
+----+----------------------+........................................+
| #  [ find, run, ask ]  F W X ||. Kas <> Waits  ^ HALT  o ) = 14:02 |
+--------------------------------------------------------------------+
```

## 3. The first minute, day and week of a Windows-and-DOS person

**Minute.** The computer starts on Home as icons: Documents, Downloads, Pictures, and Drives with their free space, as
This PC shows them. They press the Windows key: Start rises with pinned apps, recent files and Lock, Sleep, Restart,
Shut down. They type `wri`; the top row reads "LibreOffice Writer · App · Enter opens"; Enter. Writer opens with − □ ✕
at its top right and stands in the bar. Alt+Tab goes back. Win+E, a double-click on Documents, F2, Delete to the Bin,
Ctrl+Z, Alt+F4. Nothing was new.

**Day.** They type `control panel`: Settings opens. A USB stick raises a quiet note at the lower right ("HOLIDAY · 16
GB · Open · Eject"); Ctrl+C and Ctrl+V copy its photos; Eject answers "Safe to remove". They type `dir`: the row reads
"dir · in Debian: ls -l · Enter runs it in the Terminal, here". F12 drops the Terminal; `dir`, `cls` and `ipconfig`
work, each saying once what Debian calls it. "What did we spend on groceries this month?" puts **Ask Kas** first; her
sheet slides in with 244.65 and its receipt. "Tidy my Downloads" brings her plan and one card, the grant in plain
words; Grant; the steps turn ✓ done (verified); "11 files sorted · Undo all".

**Week.** F8 on the budget shows the Board. They press `>_` on receipts until they type the commands themselves. They
change a key in Settings ▸ Keys and open the plain file it wrote. Kas edits a letter in LibreOffice while they watch; a
touch pauses her; once they press Win+Esc, and HALT holds her work and nothing else.

## 4. Files: an Explorer and the board, one place

Files is one place with **four views of the same selection and the same history**: Icons, List, Columns, Board.

- **As Explorer.** Places first (Home, Desktop, Documents, Downloads, Pictures, Bin), then This computer (System `/`,
  drives with free space and Eject), then Workspace (Graphite's records). The address takes a typed path. Enter or a
  double-click opens a file **in its app**, as Windows does (its saves still become revisions); Space looks at it here;
  records open here. A selection raises one pill at the foot of the content ("48 chosen · Move to… · Copy to… ·
  Delete"); the same pill carries each receipt with Undo and `>_`, then leaves (kept in Activity).
- **Details** shows the preview, the facts and **Connected**: the board's first ring as rows ("made from page 1 of
  Rail_Demo_Bench_Readings.pdf · recorded"); with nothing connected, no heading.
- **As the board** (F8, or the view button, which carries the count, "Board 7"; with no links it is disabled and says
  why): 1.0's board, unchanged in meaning, at full width. A folder's board shows what it holds, sized by recent use;
  a task's board shows what Kas read and changed, each tile with its step's mark.

The board is no longer the room you stand in; it is the view you turn to when you ask "what is this connected to?".

## 5. Apps, windows, the bar; the tray and the clock

- **Apps** (the word stays) are what is installed. Graphite's own rooms are commands found by the line.
- **The bar's middle** is the taskbar: pinned apps and open windows. Open has a short underline, active a full one and
  bold, "asks for you" a ◆. The desk itself is the pinned entry **Files**.
- **Windows** wear title bars drawn from the tokens, − □ ✕ at the right. Win+arrows snap to halves, maximise and
  restore; beside a snapped app the desk lays its content in the free half.
- **Tray**: vitals (CPU, GPU, RAM, TXT, NET behind one mark), network (● online, ⊘ offline), sound, battery, each a
  small popover with its page one press away. **Clock**: time over date; a press opens the calendar and today's notes.
  Notes from apps rise above the clock and never take the keys.

## 6. Search, the launcher and commands: Start

One line, in the bar. Empty, its panel is the Start menu: pinned apps, recent files and the session row (Lock, Sleep,
Log out, Restart, Shut down, Return to Debian). As you type, rows in this order: best match · Apps · Settings · Files
and records · Commands (every menu action, operations, kept words) · Open windows · Ask Kas · Web ("leaves this
computer"). Each row shows its kind, what Enter does, and its key. Words that read as a request put **Ask Kas**
first; Enter carries them to her sheet, where she answers: the line never answers as her. Prefixes: `>` a shell
command (Win+R), `?` Kas, `=` an exact sum, `/` an operation, `~` a path. Nothing typed runs as a command without `>`
or Ctrl+Enter. **Windows words find their Debian place**: control panel, task manager, my computer, recycle bin, cmd,
notepad, device manager; `regedit` answers honestly: "There is no registry. Settings are files: open ~/.config".

## 7. The Terminal and DOS words

F12 drops your own shell from the top edge over anything and puts it away again; it keeps running while hidden and
outlives a restart of Graphite. Its strip offers **Here** (the folder Files shows) and **Paste last action** (the
command behind your last press, at the prompt, not run).

**DOS words** are one shell file you may read and change: dir, cls, copy, move, ren, del (to the Bin, so Undo works),
md, rd, type, edit, mem, ver, cd.., ipconfig, tasklist, help. Each says once, dimly, what Debian calls it. `C:`
explains that drives are folders under /media; `format` refuses and points to Storage.

**The command behind.** Every receipt, Settings page and right-click has `>_`: "In a terminal this is: `mv -t
~/Documents/Taxes\ 2026 …`", `udisksctl unmount -b /dev/sdb1`, `nmcli device wifi connect …`. Where Graphite went
through a system service the line says "equivalent", never "what ran". Every key calls `graphite-do <verb>`, so a
script of yours can do whatever a key can; the keys, the bar's layout and the DOS words are plain files.

## 8. Settings and the system pages (a Control Panel)

Win+I. The Machine and Settings tabs become one Settings: categories in the side list, one page in the content.
**System** (Display, Sound, Network, Power, Storage, About) · **Devices** · **Personal** (Look, Bar and Start,
Notifications, Keys) · **Apps** · **Account** · **Kas** (her model, her hand, Grants, Rules) · **Update**. Every page
follows one template: the state in a word and a shape (● Connected · HomeNet); real controls (a switch, a slider, a
list); the change read back before "done"; Keep or go back for risky changes; a foot with `>_` and "Kept in:
~/.config/mimeapps.list". A page 1.1 lacks is not listed; its Windows name in Start says so and gives the command.
**Activity** (Ctrl+Shift+Esc) is the Task Manager: apps and processes with End task (asked politely first),
performance, the Log, Kas's journal.

## 9. Kas

- **Where she lives.** In the bar, always in the same spot: her **pulse** (five small bars that move only when she
  works), her name, her state as shape and word (○ Quiet, ● Working 2 of 5, ◆ Waits for you, ✓ Done, ‖ Held, ⇣ Kas:
  site while she fetches). No picture, in any look. The bar being above every app, you see her state while you work
  in LibreOffice, which 1.0's column could not show.
- **Permissions.** When a step needs your word or grant, one **card** rises from her mark: the task, the grant in plain
  words, its scope, Grant and Not now, "See the plan". It never takes the keys: no keystroke meant for a document can
  grant anything.
- **Her sheet** (Win+K, or her mark), top to bottom: Waits for you (only when something does; never folded); Now (each
  task, its plan as steps with shape and word, progress, its own Stop); Conversation with her ask line. Tabs: Journal
  (✓ done (verified), ○ prepared, → sent), Grants (uses, Revoke), Findings. Pinned, it is 1.0's column. DO, DOUBT,
  TRACE, BRIEF and CHECK ALL become words in Start and on any right-click.
- **HALT** stands beside her mark: the green triangle and the word, RESUME ▶ while held. It holds all of her work and
  nothing else. Keys: Win+Esc, and Pause where a keyboard has one; a key only ever stops, RESUME is a press. A HALT
  pressed while the desk restarts is kept and applied before anything of hers runs.

## 10. Keys

Menus, right-clicks, Start's rows and tooltips **show keys** (one switch in Settings ▸ Keys, on). Every key can be
changed there; the page writes one plain file.

| Key | Does |
|---|---|
| Win · Ctrl+Esc | Start |
| Win+E · Win+I · Win+R · Win+L | Files · Settings · Run · Lock |
| Win+D · Win+M · Win+A · Win+P | show desk · minimise all · notes and calendar · screens |
| Win+K · Win+Esc / Pause | Kas's sheet · HALT |
| Win+1…9 · Win+Tab | the bar's nth entry · open windows in Start |
| Win+←/→ · Win+↑/↓ | snap halves · maximise, restore |
| Alt+Tab · Alt+F4 · Alt+Space | next window · close · window menu |
| Ctrl+Alt+Del · Ctrl+Shift+Esc | Lock, Activity, Log out, Restart, Shut down · Activity |
| F12 · Ctrl+Alt+T · PrtSc | drop Terminal · terminal window · screenshot to Pictures |
| Enter · Space · F2 · Del · Shift+Del | open · look here · rename · to the Bin · delete for ever (asks) |
| Ctrl+C X V · Ctrl+Z Y · Ctrl+A · Ctrl+Shift+N | copy, cut, paste · undo, redo · all · new folder |
| Alt+←/→/↑ · Backspace · F5 | back, forward, up · back · refresh |
| F4 / Ctrl+L · F3 / Ctrl+F · Ctrl+K | address · find here · Start |
| Ctrl+T W Tab · Ctrl+\ · F6 | new, close, next tab · split · next pane |
| Ctrl+B · Alt+P · F8 · Ctrl+H | side list · Details · Board · hidden files |
| Alt / F10 · Shift+F10 · Alt+Enter · F1 · F11 | menus · right-click · Properties · Guide · full screen |
| In Start: Ctrl+Enter · Shift+Enter · Esc | run as a command · ask Kas · close |

## 11. Type, colour, space and motion

**Built on 1.0's tokens** (`design_tokens.py`: Inter, IBM Plex Mono, Day and Night, the 4 px grid, the radii, 28 px
controls), with fewer rules used more strictly.

- **Type.** The same scale. Mono only for what is typed or measured. Section heads are subhead in sentence case; the
  tracked capitals go. State words are sentence case, shape first ("◆ Needs your word"); only HALT and RESUME keep
  capitals.
- **Colour.** Accent for selection, focus and links; green only for "she works" and "verified"; amber only for "needs
  you"; red only for destructive and refuted.
- **Space.** New tokens: bar 44 (40 at 768), content bar 44 (40), side 240 (rail 48), Details 320, sheet 400 (340),
  Start 600×640 (480×520), card 360, content margin 24 (16), rows 28.
- **Motion** says where a thing lives: Start rises from the bar (160 ms), the sheet slides from her side (220), the
  Terminal drops from the top (180), a card rises from her mark (160). With Reduce motion, or no compositor,
  everything simply appears. Depth is hairline first; shadows are a bonus when a compositor runs.
- **Looks.** Day at launch, Night, Auto by the clock; Kasandra and Graphite become token sets on this layout.

## 12. What goes, and what I reverse

**Goes from 1.0:** the head (the fixed menu row, Apps ⊕); the foot (the five-mode chooser, the writing line, the meter
row); the three-tab left column and the Machine tab; the DELETE can; Kas's permanent column, its sixteen-bar equalizer,
NEXT STEPS and the six command buttons; the dock strip at the top; the board as the default centre; the older rooms
and the engineering rooms in the Apps list (all still found by the line).

**Earlier decisions of the owner reversed, each one switch to restore:**

1. **HALT upper left** → on the bar beside her mark. In 1.0 an app in front hid it; the bar is above every app, and
   the stop sits beside what it stops.
2. **No key printed anywhere** (13 Nov) → keys shown. Keys are how a Windows-and-DOS hand learns, and summoned menus
   cost no calm.
3. **DELETE as the bin's word** (14 Nov) → "Bin" in Day and Night; DELETE stays in the Kasandra look, where it was
   asked for. A capital verb as a place reads as a command beside a destructive act.
4. **The tree from the root** (26 Nov) → Places first; `/` is one row and one typed character away.
5. **Menus across the top** (0.5.1) and their eight names → summoned by Alt, in Windows' words.
6. **Apps upper right** ("our progman.exe") → Start at the lower left, where a Windows hand goes.
7. **Kas's column and the footer as fixed places** (26 Nov) → the sheet and the line. Kas still answers only in her
   own place; the line hands words to her, as "Ask Kasandra →" did.
8. **The equalizer of all the computer's activity** (13 Nov) → her pulse shows her work; the computer's is in Activity.
9. **Visible connecting branches in the tree** (6 Nov) → a plain list in Day and Night.

Kept: no picture of Kas; Apps, never Programs; every state a word and a shape; everything on this computer.

## 13. The build: sixteen slices

Only slice 4 edits `qt_app.py`, `arc_desktop.py`, `shell2.py` and `pane_qt.py`; every other slice hands it an
`install(host)`. No slice edits `halt_gate.py`, `grants.py`, `assignments.py` or `engineering_kernel.py`.

| # | Slice | Mostly touches | Must not collide with |
|---|---|---|---|
| 1 | Tokens and tables | `design_tokens.py`, `state_words.py`; new `windows_words.py`, `command_behind.py`, `global_keys.py` | `boss_theme.py` (16) |
| 2 | Session: generated Fluxbox files, `graphite-do`, optional compositor | `../LS_XSESSION.sh`, `session_launch.py`; new `fluxbox_conf.py`, `graphite_do.py` | `session_power.py` |
| 3 | The bar as its own process, at the bottom | new `bar_app.py`, `bar_link.py`; `system_dock_qt.py`, `windows_strip_qt.py`, `windows_x11.py` | 4 |
| 4 | The desk frame: head and foot out, content bar, tab row, summoned menus with keys | `qt_app.py`, `arc_desktop.py`, `shell2.py`, `pane_qt.py`, `desktop_header_qt.py`, `centre_one_qt.py`, `split_qt.py`, `menus2.py`, `typebar_qt.py`, `console_qt.py` | every other slice (the hub) |
| 5 | Start: the line, its panel, its sources | new `start_qt.py`; `apps_catalog.py`, `apps_qt.py`, `search_reach.py`, `foot_line.py`, `settings_registry.py` | 3 (its slot only) |
| 6 | Files as Explorer | `finder_qt.py`, `home_files_qt.py`, `bulk_files_qt.py`, `computer_tree_qt.py`, `cabinet_qt.py`, `thumbnails.py`, `trash_can_qt.py`, `context_menu.py` | 7 |
| 7 | The board as a view; Connected | `board_qt.py`, `board_model.py`, `relevance.py`, `depths_qt.py`, `living_nav_qt.py` | 6 |
| 8 | Kas in the bar: pulse, cards, HALT and its keys | new `kas_bar_qt.py`; `halt_qt.py`, `halt.py`, `waits_qt.py`, `equalizer_qt.py` | 9 |
| 9 | Kas's sheet | `her_column_qt.py`, `kasandra_column.py`, `grants_qt.py` | 8 |
| 10 | Tray, clock, notes | new `tray_qt.py`; `notify_server.py`, `notify_qt.py`, `net_meter.py`, `meter_cards.py` | 12 |
| 11 | Drop Terminal and DOS words | new `drop_terminal.py`, `dos_words.sh` | 4 (`typebar_qt.py`) |
| 12 | Settings as a Control Panel | new `settings_page_qt.py`; `settings_qt.py`, `system_settings_qt.py`, `machine_room_qt.py`, `machine_qt.py`, `brain_qt.py` | 10 |
| 13 | Windows: title bars, snap, Alt+Tab on the bar, the Keys page | `global_keys.py`, `fluxbox_conf.py` (tables only), `windows_x11.py` | 2, 3 |
| 14 | Activity and the receipt pill | new `activity_qt.py`, `receipt_qt.py`; `log_qt.py`, `machine_overview.py` | 6 (the pill's mount) |
| 15 | First run, Home, "Coming from Windows" | `empty_workspace_qt.py`, `guide_pages.py`, `launch_look.py`, `docs/` | 6 |
| 16 | Looks and the atlas: Day, Night, the two token sets, both sizes, compositor on and off | `design_tokens.py`, `boss_theme.py`, `theme2.py`, `a11y_names.py` | runs last |

Order: 1 → 2, 3, 4 together → 5 to 12 together → 13, 14, 15 → 16. `GRAPHITE_BAR_INPROCESS=1` keeps 1.0's in-window
bar as the fallback.

## 14. Risks, and what only real hardware can settle

- **No compositor under Fluxbox.** Shadows and smooth slides of Start, the cards and the sheet need one (picom). The
  design reads with hairlines alone; whether motion is smooth on the Radeon only the ThinkPad shows.
- **Keys.** The Windows key alone needs a tap binding (xcape or a release grab); a ThinkPad keyboard may have no Pause
  key, hence Win+Esc; F12 taken globally costs Firefox its tools key.
- **A second process and a link** are new ways to fail; HALT must answer while the desk is busy.
- **Fluxbox on the real screen**: the bar's strut at the bottom, halves beside it, the sheet's layer above apps, the
  Terminal's embedding and focus. Dragging a window to an edge to snap is not in 1.1.
- **Start's guess** between an app, a file and Kas will sometimes be wrong; it is safe because each row says what
  Enter does and no change runs from a guess.
- **Kas may feel absent** without her column; the pin restores it; only an evening's use says which is right.
- **Nine reversals of your own words**; each is one switch.
- **Scale**: 13 px on a 14-inch 1920×1200 panel is small; the factor is chosen on the panel.
- **The day or two**: slice 4 rewires a 5,400-line window; if it slips, slices 5 to 12 must stand in 1.0's frame.
