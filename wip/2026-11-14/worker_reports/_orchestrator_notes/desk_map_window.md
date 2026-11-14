# Map: driving the Graphite window from code (desk acts)

The window is `w`, a `WorkbenchWindow` (qt_app.py:2293). These are the handles the acts would use:

- `top = w.shell2.top` (shell2.py:3165)
- `face = w.shell2.face` (shell2.py:3174)
- `bar = w.type_bar` (typebar_qt.py:771)
- `page = w.field_page` and `v = page.view` (field_page.py:169, field_page.py:36)
- `nav = w.settings_navigator` (shell2.py:3280)
- `cm = workbench.context_menu`, whose open menu is kept in `w.context_menu` (context_menu.py:2796)

I checked the key calls by running two probes offscreen on a scratch copy of After Hours 07: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_read/probe_read.py` and `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_read/probe_scene.py`. Nothing under /home/user/Struthio was touched. Wherever a row below says "probe:", it means a result from those two runs.

Marks: **N** means navigates (changes nothing). **C** means changes. **N\*** means it keeps a window preference in the session but changes no Kernel record.

## 1. The head

| Control | Call on live `w` | Mark | Read-back | Dialog / blocking |
|---|---|---|---|---|
| The eight menus across the head | **Words:** `top.bar_menus[i]` are QToolButtons set to InstantPopup over `w.menu_groups[g]` (shell2.py:647-669). The word shown for each menu comes from `menus2.DISPLAY_TITLES` (menus2.py:17-18). **Open:** `m.popup(word.mapToGlobal(QPoint(0, word.height())))` (action_shots.py:24-25). **Submenu:** `sub.popup(m.mapToGlobal(m.actionGeometry(a).topRight()))` (action_shots.py:33-36). | N | `m.isVisible()`, `m.activeAction()`. Read a row's text with `tool_faces.named()` (tool_faces.py:239-241): until a menu is dressed, texts still carry `\tAlt+1` and similar (menus2.py:160,164,180; dressing strips them at tool_faces.py:257). `menu_groups` lists Arrange twice, under 'View' and 'Options' (menus2.py:75); probe confirmed. | **Do not call `word.click()` or `showMenu()`.** InstantPopup runs the menu's own blocking loop (Qt). `popup()` came back in 0.16 s (probe). |
| A row in a head menu | `action.trigger()` | Depends on the action (see the dialog table) | Whatever the action opens | Leave rows (Log out, Exit, Restart, Shut down) live in Work (menus2.py:209-219) and go through `session_power.leave` / `run_action` (session_power.py:262, 309). |
| Keyboard route to the head menus | None. The menu bar is hidden (qt_app.py:2881) and the menu words are not in the Tab order (typebar_qt.py:731-742). The keyboard way to reach the same QActions is the line's command search: Ctrl+K (shell2.py:3186) then `OneBox.commands` (shell2.py:1163-1175), or each action's own key (F9 Field, menus2.py:187). | N | – | – |
| Apps | `top.programs.click()` (shell2.py:597) runs `bar.hatch.open_list()` (hatch_qt.py:119-123), which shows `ProgramsList` (programs_qt.py:586-603). It is a Qt.Popup frame and does not block (programs_qt.py:438-439). | N | `hatch.programs.isVisible()`, `.words()`, `rows_by_key[k].caption` | Choosing a row (`rows_by_key[k].choose()`) triggers on a zero timer (programs_qt.py:309-314). The direct call is `hatch.choose(key)` (hatch_qt.py:203-211), which only navigates. |
| Meters CPU / GPU / RAM / TXT | `top.pulse.open_card(key)` (desktop_header_qt.py:98-102), then `meter_cards.open_card`, which sets `w._meter_card` (meter_cards.py:146-151) | N to open | `top.pulse.values[k].text()` (desktop_header_qt.py:162-168), `w._meter_card.words` (meter_cards.py:56-60) | Card buttons act on a zero timer (meter_cards.py:59). CPU "Stop all jobs" leads to Master Stop's confirm box (desktop_header_qt.py:339-343, qt_master_stop.py:172-173). GPU On/Off/Restart calls `life.request` (meter_cards.py:102-106) and is **C**. |
| Equalizer | `top.equalizer.show_card()` (equalizer_qt.py:318-325) | N | `top.equalizer.words` (equalizer_qt.py:290); probe: `{'CPU': '4 threads, 20% at work', …}`. `top.equalizer.card` is the card. | – |
| Address | `top.path.edit_location()` (shell2.py:923-927; Ctrl+L at 549), then `navigate()` (929-936) | N | `top.path.friendly()` gives (name, where) (877-893); `top.path.text()` is the address | – |

## 2. The left pane

| Control | Call | Mark | Read-back | Dialog |
|---|---|---|---|---|
| Files / Machine / Settings tabs | `nav.show_view('cabinet'\|'machine'\|'settings')` (settings_qt.py:303-310), or the tabs' own `nav.bar.buttons[i].click()` (261-262). Machine also runs `page.build()` (314-317); the Settings tab runs `w.ledger_bridge.show_settings()` (262). | N | `nav.current_view()` (312); probe: `cabinet` | – |
| Files tree (the cabinet) | Point: `w.cabinet_page.select(ident, reveal=True)` (cabinet_qt.py:240-251). Open: `w.cabinet_page.open(ident)` (263-266). Right-click: `cm.open_at(w, tree.viewport(), pt)` (268-274). | N | `tree.currentItem().data(0, Qt.UserRole)` gives `{id, label, role, target}` (cabinet_qt.py:219) | – |
| Settings tree | `nav.select(key)` (settings_qt.py:324-339); opening the row is `show_settings(key=…)` (345-347) | N | `nav.selected_key()` (341-343) | – |
| Trash | `shell2.open_destination(w, 'trash')` (shell2.py:1438-1440), the same as the can's click (trash_can_qt.py:99-102) | N | `w.trash_can.count` (90-91); `TrashTab` rows (files_qt.py:501-512) | Restore is `files.restore`, scope approve (files_qt.py:511): **C** |

## 3. The centre

| Control | Call | Mark | Read-back | Dialog |
|---|---|---|---|---|
| Today / Home | `w.a_home.trigger()` (its words are 'Today', menus2.py:290), which runs `show_start` (qt_app.py:3509-3542); or `open_destination(w, 'home')` (shell2.py:1398-1401) | N | `w._home_active`; title 'Home — Graphite' (qt_app.py:3539); `w.home_page.place` | – |
| Field | `w.a_field.trigger()` (menus2.py:187-188) runs `field_page.show_field` (field_page.py:158-181). Faces: `page.show_face('work'\|'programs'\|'network')` (104-108). Back: `field_page.back(w)` (197-212). | N | `w._field_active`; title 'Field — Graphite' (179); `page.face` | – |
| Files | `open_destination(w, 'files:'+rel)` (shell2.py:1428-1430) runs `files_qt.show` (515-521). Also `tab.go(rel)` (172-173), `tab.select_path(rel)` (316-320), `tab.toggle_view()` (244-245). | N | `tab.folder`, `tab.mode`, `tab.selected()` (134-136), `tab.listing['entries']` | Many rows open dialogs (§7) |
| Opening a file | `tab.activate(entry)` opens the viewer for a file, steps into a folder, or opens a smart folder (files_qt.py:175-181) | N | `w.tabs.currentWidget()`, `w.centre_bar._name` | – |
| Pages (sheet, document, PDF, investigation, job) | `field_page.open_object(w, obj)` picks `office_qt.open_office`, `document_qt.show`, `pdf_qt.open_pdf`, `investigations_qt.show` or `show_job` (field_page.py:651-686) | N | The current tab, `centre_bar._name` / `_said` (centre_bar.py:148-149) | – |
| Rooms | `program_rooms_qt.show(w, key)` (program_rooms_qt.py:926-928), or `open_destination(w, 'program:'+key)` (shell2.py:1404-1406) | N | The current tab | – |
| Compare room | `compare_qt.show(w, path=b, other=a)` or `version=v` (compare_qt.py:236-238) | N (`files.compare` is a read) | `tab.data`: before, after, added, removed, sheets, facts (compare_qt.py:71-79) | Inside the room: Update original asks (202-203); Save as new uses a text dialog (214) |
| Tabs | `w.tabs.setCurrentIndex(i)`; closing is `w.close_tab(i)` (qt_app.py:3470-3502) | N | `w.tabs.tabText(i)` | Closing a modified editor runs `ask_save`, which is modal (qt_app.py:3478-3486, 4080-4083) |
| Centre bar (‹ Field, Find, − +, Undo, Redo, Save) | `w.centre_bar.field / find / smaller / larger / undo / redo / save` `.click()` (centre_bar.py:52-60) | Field / Find / − + are N; Undo / Redo / Save are C (text) | Button enabled state and tooltip (`sync`, 132-172) | – |

## 4. The Field (`v = w.field_page.view`)

| Control | Call | Mark | Read-back |
|---|---|---|---|
| Select a sheet | `v.field.select(id); v._layout(); v._reveal(); v._describe(); v.update()` (the bundle at context_menu.py:1362-1363; field_model.py:216-219) | N | `v.selected()`, `v.field.selected`, `v.accessibleDescription()` (field_qt.py:175-186) |
| Keys (arrows, Home, End, A, Backspace, PgUp, PgDn) | `v.press_key(Qt.Key_…)` does exactly what the key does (field_qt.py:519-529; keys at 431-468) | N | Same as above. Arrows follow the wires (field_model.py:241-258); there is no key that jumps to a sheet by name. |
| Zoom | Z: `v.press_key(Qt.Key_Z)` runs `glide` (field_qt.py:438-440, 275-294). + / −: `set_zoom` (441-444). Ctrl+0 (445-446). Wheel (733-736). The strip's + and − (1395-1400). | N | `v.zoom`, `v._fitted`; `v._gliding is None` once the glide (190 ms, line 251) has settled. Reduced motion reads `page.view.still` (field_page.py:51-54). |
| Open (Enter / click) | `field_page.open_object(w, obj)` (field_qt.py:449-454, field_page.py:55) | N | The tab, `w._field_active` False |
| Mouse | A left click on a sheet **opens** it (field_qt.py:683-686). The right button only selects (630-631). Hot places are kept in `v._hot` (123-125, 600-608). | N | – |
| Trace (T) | `field_page.trace(w, obj)` (field_page.py:402-412) | N | A Talk card with the trace line (probe: `field.trace {...} \| pick rows \| select way,…`) |
| Doubt (X) | `field_page.doubt(w, obj)` (415-428), which puts the doubt page over the work (431-449) | N | `v.reading['title']`, Talk card |
| Check (C) | `field_page.check_desk(w)` (554-609) | N; its step 1 puts changes up | `v.reading`, `page.steps_of == '*'` |
| Brief (B) | `field_page.brief(w)` (452-493). Keeping it is staged without `asked`, so it always waits. | N; keeping it is C | `v.reading`, `v.go` |
| Do (D), then a digit | `field_page.do(w, obj)` (270-292), then `field_page.take(w, obj, n)` (295-327). A change goes to `face.stage(..., asked=True)` (324). | D is N; take is **C** | `page.steps`, `v.steps`, `v.go`, `page.pending` (72) |
| G (go) | `field_page.go(w)` (261-267) | **C** (the owner's approval) | `v.go` cleared |
| What if | `w.shell2.ask('what if B4 were 100')` (context_menu.py:1265-1272), or `field_page.show_would(...)` (525-536) | N | `v.would`, `v.would_said` |
| S line / Shift+Enter | `field_page.stac_in_line` (612-616) / `stac_run` (619-630) | N | The writing line / the console |

## 5. The right-click and the line panel

| Step | Call | Read-back / notes |
|---|---|---|
| Open with the mouse | `cm.open_at(w, widget, pt)` (context_menu.py:2805-2810). For the router's own path, send a QContextMenuEvent to the widget (2873-2882). | `w.context_menu.first_keys()` (2278), `.words()` (2267-2274), `.entries` (2166). The first level is: up to 4 usual rows from REST, then Then or Start from, then More (1951-1983). |
| Open with the keyboard | Menu key or Shift+F10 runs `cm.open_at_focus(w)` (2830-2843, 2892-2893) | In the Field the menu opens at `v.selected_point()` (2825-2826) |
| Open a › row | `menu.open_child(menu.row(key))` (2421-2449). Deeper screens replace rows in place: `child.drill(entry)` (2395-2408); go back with `child.back()` (2410-2419). | `child.screen`, `child.rows_by_key` |
| Act on a leaf | `cm.perform(w, menu.target, entry)` (2777-2787). A click instead runs `row_chosen`, which defers the act to a zero timer (2379). | `w._context_last = {key, ok, words, result}` (2786); `w._context_said` (160) |
| Then › (the line panel) | `panel = menu.open_child(menu.row('then'))`. The one read runs on a timer once the panel shows (2558-2561). **Wait for `panel.ready`** (2548, 2678). | `panel.line`, `count_words()` (2584-2589), `preview_text()` (2594-2610), `screen` keys |
| Carry a step | `panel.choose(key)` acts at once (2740-2754). Keys include `'step:where'`, then `'field:<column>'`, then the value key, e.g. `'where unit=mA'` (2699-2710); also `'step:sort'`, `'step:count'`, `'step:group'`, `'step:first'`. Back a step: `panel.step_back()` (2695-2697). | Probe: 6 rows · 6 steps left; then where unit=mA, 3 rows; then count, 1 row · 4 steps left. |
| The endings | `panel.choose('end:show'\|'end:line'\|'end:copy'\|'end:rows')` closes the menu and performs (2750-2751) | Probe for end:line: `bar.box.text() == '@files:bench readings.csv \| rows \| where unit=mA \| count'`, target `slate` |
| Close | `w.context_menu.close_menu(restore=True)` (2487-2498) | – |
| Keyboard inside the menus | Down, Up, Home, End and type-to-select letters (programs_qt.py:551-581); Right opens, Left and Esc go back (context_menu.py:2503-2513) | – |

Side effects of looking: when the menu finds its target it selects what is under the point. Files does this at context_menu.py:1504-1505 and the Field at 1695-1696, just as a person's right-click would.

Two key notes for scripts:
- The column keys `field:<column>` share a prefix with the Field's own row keys (2702 against 1406-1445). A column named "open" would read as `field:open`.
- Value keys contain spaces and `=` (probe: `'where unit=mA'`), so scripts must quote them.

## 6. The right pane (her column, hand, trail) and the typing line

| Control | Call | Mark | Read-back |
|---|---|---|---|
| Talk / Activity / Context | `w.shell2.show_slate_face()` / `show_operations_face()` / `show_context_face()` (shell2.py:3549-3558); her pane title: `title_clicked()` (3426-3433) | N | `w.console_pages.currentWidget()` |
| Words to her | `w.shell2.ask(text)` (3560-3561), into `SlateFace.ask` (2542-2560). It can **change**: `made_asked`, `set_asked` and `run_asked` (2544-2547) stage under her hand. | N, or C when the words ask for a change | The cards in `face.lines` (1801), read as `cards()` in cascade_probe.py:7. Answer cards carry `stac`, `answered`, `said` (1972). Staged cards carry `step`, `ran`, `hers`, `entry`, `run` (Approve), `back` (Undo) (2022, 2071). |
| Approve | `card.run.click()` runs `run_staged` (2028-2029, 2032-2076) | **C** | `card.ran` |
| Hand dial | Open: `face.open_hand()`, a popup that does not block (2141-2148), from `hand_menu` (461-488). Set: `stacy_hand.choose(w, key)` + `w.session.save()` + `face.show_hand()` (470-473). | N\* (the owner's) | `face.hand.text()` (2134-2139); `stacy_hand.level(w)` (stacy_hand.py:129-132) |
| Trail / Undo / what always asks | `face.say_trail()` (2150-2165), `face.undo_entry(entry)` (2167-2187), `face.say_always()` (2189-2198) | Undo is C | `stacy_hand.trail(w.session.state)` (stacy_hand.py:252-254) |
| Line's five targets | `bar.set_target('slate'\|'shell'\|'find'\|'web'\|'log', focus=False)` (typebar_qt.py:26-28, 279-302). Keys Alt+1/4/5/6 exist; **Web has no key** (menus2.py:159-161). | N | `bar.target`; probe: `{'slate': 'Stacy', 'shell': 'Terminal', 'find': 'Search', 'web': 'Web', 'log': 'Log'}` |
| Words into the line | Put: `cm.inspect_in_line(w, text, mode)` (context_menu.py:225-235). Keys: `QTest.keyClicks(bar.box, text)` (action_shots.py:59), which emits textEdited and so shows the results list (shell2.py:1004, 1065-1069). | N | `bar.box.text()`, `bar.context_kind` / `context_text` (typebar_qt.py:679-680), `bar.box.popup.list` |
| Send | The arrow: `bar.submit_line()` (423-433). Enter: `QTest.keyClick(bar.box, Qt.Key_Return)`; in Web it goes through the eventFilter (707-712), otherwise `returnPressed` reaches `popup.activate_current` (shell2.py:1293-1299). Ctrl+Enter: `bar.ctrl_enter()` (385-413). | N for a line that reads, a search or a filter. Words to her follow the "Words to her" row. Terminal runs the shell (`to_console('shell')`, shell2.py:1208-1218). Web opens the owner's browser (typebar_qt.py:361-373). | `w.console.output.toPlainText()` (console_qt.py:197), `w.console.last_program` (199, 470), `w.console.mode` |
| Expand | `w.console.set_size(0\|1\|2)` (console_qt.py:264), or `bar.expand.step()` (typebar_qt.py:177-178) | N | `w.console.size_level`, `bar.expand.level` |
| Search (Ctrl+K) | `w.shell2.search()`, which calls `bar.search()` (shell2.py:3542-3547; typebar_qt.py:310-316) | N | popup rows |

## 7. Appearance and glow

| Control | Call | Mark | Read-back | Dialog |
|---|---|---|---|---|
| Appearance | `boss_qt.choose_appearance(w, key, ask=False)` (boss_qt.py:406-421). It takes effect only at the next start, because the colours are chosen once at import (boss_theme.py:23-26, 98). Tests can choose in advance with `GRAPHITE_APPEARANCE` (84-85). | N\* | `boss_theme.APPEARANCE` is what is in force; `boss_qt.chosen_look(w)` is the next start (398-403). Probe: chosen kasandra, in force graphite, status 'Kasandra is used from the next start.' | With `ask=True` it shows a modal question (414-419) |
| Glow | `boss_qt.choose_glow(w, 'soft'\|'bright'\|'neon')` (466-475) | N\* | `w.session.state['glow']`, `boss_theme.GLOW[0]` (probe: soft → 1.0) | – |
| Desk art | `boss_qt.choose_art(w, 'illustrated'\|'ascii'\|'clean')` (477-494) | N\* | `w.session.state['desk_art']` | – |
| Words or icons on buttons | `tool_faces.choose(w, mode)` (tool_faces.py:291) | N\* | `tool_faces.mode()` (50) | – |
| Reduced motion | `reading_preferences.apply(w, {**w.reading_profile, 'reduce_motion': True}, persist=True)` (reading_preferences.py:100-133). **persist=True is needed**: `sync_profile` puts the session's profile back over a profile that was not saved (control_qt.py:293-296, 322-325). The settings key is `reading.reduce_motion` (settings_registry.py:41); setting it that way is a Kernel write (ledger.settings.set, execute scope, per the probe). | N\* | `v.still()`; probe: True, and Z went 0.8 → 1.0 at once | – |
| The Rules menu | Desk artwork, Buttons and Stacy's hand (menus2.py:227); `appearance_menu` (boss_qt.py:355-391) | – | probe: Illustrated, ASCII, Clean, Glow ›, Appearance ›, (an empty row), Fast-forward screensaver ›, Art plates › | – |

## 8. Dialogs an act must not block on, and how to pass a scripted value

| Where | Dialog | Dialog-free call that takes the scripted value |
|---|---|---|
| Rename (right-click) | `QInputDialog.getText` (context_menu.py:486-490) | `cm.act_on_files(w, t, 'files.rename', {'path', 'name'}, done)` (476-482) |
| Copy to / Move to | `QFileDialog.getExistingDirectory` (501-509; files_qt.py:360) | `tab.act(op, {'path', 'to'})` for each entry, after `cm.still_file` (context_menu.py:507-508) |
| New folder / Export / Versions | getText / getItem (files_qt.py:342, 371, 380) | `tab.act('files.mkdir', {'path', 'name'})` (343); `tab.act('files.export', {'path', 'purpose'})` (374); `tab.act('files.revert', {'path', 'version'})` (381) |
| Compare with… / with a version | File dialog / getItem (files_qt.py:384, 394) | `compare_qt.show(w, path=, other=)` / `show(w, path=, version=)` (389, 397) |
| Ask about a file / Add to the Agenda | getText / getItem (files_qt.py:403, 414) | `w.shell2.ask(q, name + ' (@files:' + path + ')')` (404); `tab.act('agenda.add', {...})` (417) |
| Import / Work on a copy / Discard / Undo update / confined runs | File dialogs and questions (files_qt.py:346, 304-310, 334, 338, 288, 282). Import copies files with `shutil.copy2` and **bypasses the Kernel** (352). | `copies.start`, `copies.discard`, `copies.undo` through the Kernel (311, 335, 339) |
| **Any refusal in Files** | `FilesTab.act` shows `QMessageBox.information` (files_qt.py:253) | A change act should dispatch through the Kernel itself and then `tab.reload()`, the way `run_staged` does (shell2.py:2039). |
| Work menu: New File, Open, Find a File, Find, Replace, Go to Line, Command Palette, Recover | qt_app.py:4108, 4086, 4093-4095, 4134, 4157-4160, 4175, 4199, 5055 | Find in a page without a dialog: `w.centre_bar.open_find()` (centre_bar.py:101-105). Others: not acts. |
| Master Stop, leave rows, switch workspace, appearance with ask | qt_master_stop.py:172-173; session_power.py:233, 262-309; shell2.py:784-796; boss_qt.py:414-419 | Owner only. Appearance takes `ask=False`. |
| Guard against any dialog not listed | The harness already patches `QMessageBox.question` (nomodel.py:28). | Patch `QInputDialog.*`, `QFileDialog.*` and `QMessageBox.information` to raise inside the act. Probe: `perform` then reports `ok False, 'Not done: modal dialog reached: QInputDialog.getText'` (context_menu.py:2784) instead of hanging. |
| Menus shown with `exec` (they block) | shell2.py:3274, finder_qt.py:548, desktop_header_qt.py:471, console_qt.py:451, and the InstantPopup head words (shell2.py:658) | Use `popup()` instead. |

## 9. Her hand and "changes" acts

- **Two routes today.**
  - Field steps and "set B3 to 300" go through `face.stage(..., asked=True)` (field_page.py:324, 513-517), which gives a card, Approve, the trail and Undo.
  - Right-click changes (rename, trash, move) bypass her: `act_on_files` → `tab.act` → `call_write` (context_menu.py:476-482, files_qt.py:251-255). They make no card, no trail entry and no Undo.
- **The proposed rule for a change act:**
  - Build `Step(words, 'write', field_do.op(operation, **args), why, CAPABILITIES[operation])` (field_do.py:26-38; engineering_kernel.py:159).
  - Call `face.stage(title, step, done, asked=True, word=<the act's words>)`.
  - `stacy_hand.hers` then decides: a read never asks; otherwise only what HERS_SHOW / HERS_FREE allow, never ALWAYS_ASKS (stacy_hand.py:150-158, 39-57). Navigation acts behave like reads (154).
  - Window-only changes have no Kernel operation: appearance, glow, art, the hand dial, leave, Master Stop, switching workspace. By the allow-list rule they ask (stacy_hand.py:17-21). Approve/G and the dial stay the owner's and are never offered to the model.
  - Probe, with the hand at Ask first: `ask('set B4 to 90')` gives `card.ran None`, `v.go='set B4 to 90 ms on “07 Limits Rev B CURRENT”'`, `page.pending` set, and an empty trail.
- **Gaps:**
  - A trail line and an Undo are written only when the card is hers (shell2.py:2061-2072). Something that waited and was Approved gets neither.
  - Undo lines exist only for `field.set` and for `files.write` / `files.mkdir` (stacy_hand.py:193-203). `files.trash` is in HERS_SHOW but has no Undo line; it comes back through Trash.
  - `files.rename`, `files.copy` and `files.move` are not in HERS_SHOW, so they would always wait.

## 10. How the offscreen probes drive the window today

| Probe | What it reaches into |
|---|---|
| nomodel.py | Environment and patches (14-17, 26-28). `WorkbenchWindow(..., restore=False)` (32). `settle()` stops the agenda and idle timers, then spins events (34-38). `align()` via `type_bar.align` (39-43). `where()` reads `central_stack`, `w._field_active`, `w._home_active`, the title and the tab (46-48). Kernel calls via `k.dispatch(op, args, operator())` (55-58). Runs the script with `exec` (67). **Fails with KeyError unless `REHEARSAL_MODEL` is set (52).** |
| rc_shots.py | Writes the CSV straight into the Files root (23-25). `files_qt.show`, `mode='list'`, `reload` (26). `cm.open_at(w, view.viewport(), at)` (31). `open_child(row('more'/'then'))` (33, 36). `panel.choose(...)` and `panel.back()` (38-42). Field: `a_field.trigger`, then `select` + `_reveal` + `_describe` (44-47). `open_at_focus` (48). Pictures composite the popups found among the top-level widgets (8-15). |
| cascade_probe.py | Talk cards via `face.lines` (6-8). `entries_for(target_at(...))`, then calls `Entry.submenu()` and `.run()` directly (13-35). `words.keep` through the Kernel (15-16). `open_child(keyboard=True)` and `child.drill` (49-51). |
| mouse2_probe.py | Builds `QMouseEvent`s and sends them to `v` (6-9). Searches `v._hot` (10-11). Pointer shape via the `greenPointer` property (12). `v._bars(v._layout())` for drag (18-21). `v.sheet_rect` (36). Watches the second click with an event filter and `v._guard` (38-49). |
| look_probe.py | `tool_faces.mode()` and `console_pages` (5). `PathBar.friendly()` / `edit_location()` (10, 20). Opens a sheet by select + `_describe` + `keyClick(Return)` (12-14). Samples the glide every 22 ms (23-27). **Reduced motion by replacing `v.still = lambda: True` (31).** |
| action_shots.py | `menu_groups['File'].aboutToShow.emit()` + `popup` (24-25). Nested Rules menus via `setActiveAction` + `sub.popup` (27-37). `top.programs.click()` (39). Meters via `QTest.mouseClick` and `w._meter_card` (41-46). `face.open_hand()` (53). `stacy_hand.choose(w, 'ask')` (55-56). `w.shell2.ask(...)` (58). `keyClicks(bar.box, …)` (59-60). `nav.bar.buttons[0].click()` (62-63). |

The private parts these lean on are what the registry should wrap: `v._reveal`, `v._describe`, `v._layout`, `v._hot`, `v._bars`, `v._guard`, `v._read_at`, `v._fitted`, the replaced `v.still`, `w._meter_card`, `w._field_active`, `w._home_active`.

## 11. The first scene, checked against the code

- **The CSV.** The demo's Files folder is empty (probe listing), so the scene's CSV is fixture setup, as in rc_shots.py:24-25. The Then path works end to end (§5 probe).
- **Trace.** By the T key: 1 card became 4. By the right-click: More › Trace it › 'The whole trace, in Talk' (rows `field:trace:all`, then the ← and → rows), performed ok, and the Field stayed in front (probe).
- **Comparison.**
  - The data that supports one is Rev A against Rev B: the sheets "07 Limits Rev A ARCHIVED" and "07 Limits Rev B CURRENT", the two Rail Limits PDFs, and the finding "Rev A allowed 120 ms. Rev B allows 80 ms." (probe object list).
  - **No window control compares two sheets.** The compare operations are only files, bom, hdl and sim (grep).
  - Files' Compare revisions does work once two revision files are in Files and both are selected. Probe: first level `compare:revisions`, CompareTab data showed 1 line added and 1 removed (context_menu.py:692-697).
  - The demo's own `07_Rail_Limits_Rev_A.pdf` / `…_Rev_B.pdf` are **not** recognised as revisions (`revisions_of_one` gives False; the REVISION pattern needs a word boundary before "rev", context_menu.py:79, 205-210). They would get "Compare these two". They also sit in Ingress, not in Files.
- **Keyboard version.** F9, the arrows, the Menu key, Down, Right and Enter, and T are enough. The head menu has no key of its own, so use Ctrl+K and the command rows (§1).
- **Reduced motion.** Use the `look.set motion=reduced` act from §12 (reading profile, persist=True) rather than replacing `v.still`.

## 12. Proposed acts (40)

The registry wraps the calls in §1-§8. An act's name is never printed on rows at rest.

### Go places

| Name | Arguments | Mark | Call |
|---|---|---|---|
| go.field | face=work\|apps\|network | N | `w.a_field.trigger()`, then `w.field_page.show_face(face)` (apps is 'programs') |
| go.today | – | N | `w.a_home.trigger()` |
| go.files | folder='' | N | `shell2.open_destination(w, 'files:'+folder)` |
| go.open | sheet \| path \| tab | N | `field_page.open_object(w, obj)` / `files_qt.show(w, parent).activate(entry)` / `w.tabs.setCurrentIndex(i)` |
| go.app | key | N | `w.type_bar.hatch.choose(key)` |
| go.compare | path, other \| version | N | `compare_qt.show(w, path=…, other=… / version=…)`. Offered only when `cm.revisions_of_one` holds or versions exist. |
| go.pane | side, view | N | `nav.show_view(...)` / `w.shell2.show_slate_face()`, `show_operations_face()`, `show_context_face()` |
| go.trash | – | N | `open_destination(w, 'trash')` |
| go.back | – | N | Field: `field_page.back(w)`; elsewhere `w.centre_bar.field.click()` |

### Point

| Name | Arguments | Mark | Call |
|---|---|---|---|
| point.sheet | title \| id, by=direct\|keys\|pointer | N | direct: the select bundle (§4); keys: arrows found by search over `Field.move`, sent with `v.press_key`; pointer: right press at `v.sheet_rect(id).center()` |
| point.move | way: left\|right\|up\|down\|first\|last\|next_waiting\|before | N | `v.press_key(Qt.Key_Left / … / Key_Home / Key_End / Key_A / Key_Backspace)` |
| point.zoom | to: whole\|reading\|larger\|smaller\|z | N | `v.press_key(Qt.Key_Z)` / `v.set_zoom(round(v.zoom*20±2)/20)`; wait until `v._gliding is None` |
| point.item | path(s) in Files \| record id | N | `tab.select_path(rel)` / `setSelected` / `w.cabinet_page.select(id, reveal=True)` |
| point.head_menu | menu, path? | N | `w.menu_groups[g].popup(...)`, then `sub.popup(...)` |
| point.head_row | menu, row | N or C by action | `action.trigger()`. Leave rows, Master Stop and New File are excluded or ask. |
| point.apps | – | N | `w.shell2.top.programs.click()` |
| point.meter | CPU\|GPU\|RAM\|TXT\|equalizer | N | `top.pulse.open_card(k)` / `top.equalizer.show_card()` |

### The right-click and the line panel

| Name | Arguments | Mark | Call |
|---|---|---|---|
| menu.open | on, by=pointer\|keys | N | pointer: `cm.open_at(w, widget, pt)` (or a QContextMenuEvent to the router); keys: `cm.open_at_focus(w)` |
| menu.choose | path, e.g. `more/field:trace/field:trace:all` | N or C by `Entry.operation` scope | `open_child` / `drill` for each ›; then `cm.perform(w, menu.target, entry)`. A C row is staged through the hand (§9). |
| menu.close | – | N | `w.context_menu.close_menu(restore=True)` |
| line.then | – | N | `menu.open_child(menu.row('then'))`; wait for `panel.ready` |
| line.step | key | N | `panel.choose(key)` |
| line.back | – | N | `panel.step_back()` |
| line.end | show\|line\|copy\|rows | N | `panel.choose('end:'+how)` |
| field.ask | trace\|doubt\|check\|brief\|whatif(cell, value)\|line | N | `field_page.trace` / `doubt` / `check_desk` / `brief` / `w.shell2.ask('what if …')` / `stac_in_line` |
| field.do | sheet, step n \| words | C | `field_page.do(w, obj)`, then `field_page.take(w, obj, n)` |
| desk.approve | – | C, owner door only | `field_page.go(w)` / `card.run.click()` |
| desk.undo | entry=latest | C | `face.undo_entry(entry)` / `card.back.click()` |

### The typing line

| Name | Arguments | Mark | Call |
|---|---|---|---|
| type.to | her\|terminal\|search\|web\|log | N | `w.type_bar.set_target(key, focus=False)` |
| type.put | text, by=put\|keys | N | `cm.inspect_in_line(w, text)` / `QTest.keyClicks(bar.box, text)` |
| type.send | by=arrow\|enter\|ctrl_enter | N for reads; C for her change words; Terminal and Web ask | `bar.submit_line()` / `keyClick(Return)` / `bar.ctrl_enter()` |
| type.room | line\|half\|tall | N | `w.console.set_size(0/1/2)` |
| type.clear | – | N | `w.type_bar.box.clear()` |

### Look

| Name | Arguments | Mark | Call |
|---|---|---|---|
| look.set | appearance \| glow \| art \| buttons \| motion | N\*; asks in the model door | `choose_appearance(ask=False)` / `choose_glow` / `choose_art` / `tool_faces.choose` / `reading_preferences.apply(..., persist=True)` |
| look.hand | ask\|show\|free | owner only | `stacy_hand.choose`, then `session.save()` and `face.show_hand()` |

### Read back

| Name | Arguments | Mark | Call |
|---|---|---|---|
| read.where | – | N | Title; `_field_active` / `_home_active`; tab type and text; `top.path.friendly()`; `centre_bar._name` / `_said`; `nav.current_view()`; `console_pages.currentWidget()`; visible popups |
| read.field | – | N | `page.face`, `v.selected()` (id, title, kind, state), `v.zoom`, `v._fitted`, `v.reading`, `v.steps`, `v.go`, `v.would_said`, `v.problem`, `page.pending` |
| read.menu | – | N | `w.context_menu` (target, `first_keys()`, `words()`, its child), panel `line` / `count_words()` / `preview_text()` / `screen`, `w._context_last` |
| read.line | – | N | `bar.target`, `box.text()`, `context_kind` / `context_text`, popup rows, `console.size_level`, `mode`, `last_program`, output tail |
| read.talk | last=n | N | Cards (`stac`, `said`, `ran`, `hers`, `entry`), `face.hand.text()`, `stacy_hand.trail(...)`, the head meters and the equalizer's words |