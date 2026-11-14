# Desk acts: the build plan for one session (Graphite 0.8.2)

Everything below was checked read-only against HEAD **1f59293**. That commit came after the readers' c401f59 and moved `shell2.py` lines by about 3; every citation here is against 1f59293.

I also ran three offscreen probes on a scratch workspace. Nothing under `/home/user/Struthio` was written. They are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/design/`:

- **`seedprobe.py`** builds a bench seed through Graphite's own operations.
- **`sceneprobe.py`** drives the scene's mouse path with the calls below.
- **`keysprobe.py`** drives the keyboard path through the right-click, the line panel, F9 and the Field's menu key.

## 0. Corrections to the three maps

1. **The Field already compares two revisions.** Map 1 says no window control compares two sheets. That is out of date since bf8c12d:
   - `field_page.compare_revisions` (field_page.py:743-752) and `revision_sibling` (694-706) do it.
   - The row is `field:revisions` under More (context_menu.py:1438-1442).
   - Probe on the bench seed: Rev A against Rev B gave the changed row "Pulse duration", fields value and conditions, 120 → 80.
2. **The head menus have no keyboard route.**
   - The head words are not in the explicit Tab chain (typebar_qt.py:731-742).
   - The readers' "Tab + Space" probe actually called `tools.setFocus()` and then Space (desk_read/tests_side/probe_kb2_ts.py:55-57).
   - F10 and Alt+letter open nothing.
3. **The command search prints shortcut keys on screen.**
   - `OneBox.commands` passes `action.shortcut().toString()` as the hint (shell2.py:1177).
   - `ResultsPopup.show_results` writes it beside the row unless it is 'Enter' (shell2.py:995, 1276). So "Field      F9" is printed.
   - Undressed labels can also keep "\tAlt+1" (menus2.py:160).
   - The keyboard run of the scene goes through this list, so the pass fixes it (§7). Keys still work.
4. **Click behaviour in the Field.**
   - A left click on a sheet opens it (field_qt.py:777-781).
   - Only a right press selects without opening (field_qt.py:725-727; probe: `right_press_selects = true`).
5. **Popup 2 rows act on a zero timer.** `open_child` defers `drill` with a zero timer (context_menu.py:2430-2431), and so do `LinePanel.open_child` and `row_chosen` (2763-2770). Every act settles events after a row.
6. **`perform` swallows exceptions** (context_menu.py:2789-2791). A dialog guard therefore has to record that a dialog was reached; it cannot rely on the exception getting through.

---

## 1. Where the registry lives, and why

**In the window.** Two new modules, plus a third for scenes:

- **`workbench/desk_acts.py`** has no Qt at import. It holds:
  - the registry: name, words, mark, schema, Kernel line, owner-only flag, forms, exported flag;
  - argument checking and the refusal words;
  - `desk_hers` (her hand's rule for acts), and `tools()` / `plan_variants()` (the export);
  - `key_path` (the keys search over `field_model.Field`) and `said()`.
  - It imports only `json`, `re`, `dataclasses`, `stacy_hand`, `agent_operations.validate` and `assistant_identity.named`. None of these imports Qt: stacy_hand.py:24-28, boss_theme.py:14-16.
- **`workbench/desk_doers.py`** is the window side:
  - `run(host, name, args, door, by, origin, word)`, which runs one act;
  - one doer per act;
  - the `no_dialogs()` guard, `read_desk(host)` and the record.
  - Qt is imported inside its functions.
- **`workbench/desk_scene.py`** holds the scene format, the checker, `matches()` and `run_scene()`.

**Why not Kernel operations:**

- The Kernel has no Qt. Its only bridge to the window queues an intent that the window's tick picks up later (`ledger.navigate` / `ledger.open`; ledger_control.py:447-456, control_qt.py:468-485). An act must drive the live window and read it back at once.
- A Kernel operation would change the registry record, so the registry section of the release check would FAIL until `tools/record_registry.py` is rerun (check_hatch.py:6-9, record_sections).
- It would also be reachable by MCP, the CLI and the cloud provider's operation list unless it were denied everywhere.
- A window registry cannot be offered by accident. `checked_plan`, `validate_actions` and `bind_actions` refuse any name that is not in `CAPABILITIES` (stacy_language.py:16-36). No act is a Kernel name (test in §8).

**Consequences for the seed and the release check:**

- **No Kernel operation is added.** The registry, settings and adapters sections stay as recorded.
- **Two seed inputs are edited:** `workbench/console_qt.py` and `workbench/shell2.py` (stacy_foundation.py:114, 159). The seed reads STALE until it is rebuilt. Until then:
  - the runtime section is FAILED with `EDITED_SOURCES_NOT_YET_PACKAGED` (check_hatch.py:262-270);
  - the model's plans are refused by `_verified_seed_id` (stacy_language.py:9-13).
- **The rebuild is one command:** `python3 tools/package_graphite.py --manifest-only`. It rebuilds `project/stacy_seed/current` and rewrites `MANIFEST.json` (tools/package_graphite.py:4, 185-189). Commit 1f59293 did the same.
- **The new modules are not added to `SEED_FILES` in this pass.** `stacy_hand.py` is not there either. Putting the act registry into her seed records belongs with opening her door.

---

## 2. The act table (40 acts)

### Conventions

**Names.** Every name's first part is one of `go point head menu then sheet type hand look read`. No Kernel operation starts with any of these: the 90 Kernel heads checked include `desk`, `field` and `files` but none of these ten. So `/name` in the line can never be confused with an operation.

**Marks.**
- Every `hand.*` act and `look.set` is **changes**. Every other act is **navigates**. The mark can be read from the name.
- **owner-only** acts are never hers and never exported: `hand.approve`, `hand.undo`, `hand.dial`, `look.set` and `type.send`.

**Schema shorthand** (only what `agent_operations.validate` supports, agent_operations.py:38-80; no `pattern`, no `oneOf`):
- `S(a,b)` = `{"type":"string","minLength":a,"maxLength":b}`
- `I(a,b)` = `{"type":"integer","minimum":a,"maximum":b}`
- `E[x,y]` = `{"type":"string","enum":[…]}`
- `BY` = `E[pointer,keys]`
- Every schema is `{"type":"object","properties":{…},"required":[…],"additionalProperties":false}`, with `required` as listed.
- "one of a/b" and "at least one of" are checked by `desk_acts.check` after `validate`.
- `check` turns an int or float into a string where the schema says string, because the line's `parse_command` coerces `100` to an int (console_qt.py:59-64).

**Forms.**
- P is the pointer form, K the keys form.
- "K: —" means no keyboard route exists. The act then uses its pointer form and reports `by:"pointer"`. A scene can assert this.
- The keys forms send `QTest.keyClick` to `QApplication.focusWidget()`, or to the open menu when nothing has focus, which is where the window system delivers a key. Each act first checks that the keyboard is where it expects (otherwise it refuses with NOT_HERE). The pointer forms send real `QMouseEvent` / `QContextMenuEvent`s or `QTest.mouseClick`.
- Read-backs never name a key. They carry a count of presses, so the typed door never prints a key.

**Dialogs.**
- Every act runs inside `desk_doers.no_dialogs()`. It swaps these for raisers that record the dialog's name:
  - `QInputDialog.getText/getItem/getInt/getDouble/getMultiLineText`
  - `QFileDialog.getOpenFileName(s)/getSaveFileName/getExistingDirectory`
  - `QMessageBox.question/information/warning/critical`
  - `QMenu.exec`
- After the act and its settle, if anything was recorded, the act is refused with DIALOG.
- Patching the class attribute works because callers look it up at call time (files_qt.py:403, context_menu.py:488-490).
- Settling happens inside the guard, because deferred row timers run then.

### Go places (navigates)

| # | Act | Arguments | Call: pointer / keys | Read-back (`result`) | Dialog |
|---|---|---|---|---|---|
| 1 | `go.field` | `face:E[work,apps,network]`, `by:BY` | P: `head.row` Arrange › Field: Arrange popup, then `QTest.mouseClick` at `actionGeometry(a).center()`. K: F9 to the window (menus2.py:184-188; probe `f9 = {"field": true}`). Then the face: `w.field_page.show_face('programs' if apps)` (field_page.py:104-108); K presses the face letter from `FACES` (field_page.py:25; field_qt.py:583-584). | `{surface, face}` | none |
| 2 | `go.today` | `by:BY` | P: `head.row` Arrange › Today (menus2.py:290). K: the `a_home` shortcut read from the action (qt_app.py:2705). | `{surface:"home"}` | none |
| 3 | `go.files` | `folder:S(0,1000)`, `view:E[icons,list]`, `by:BY` | P: `head.row` Arrange › Files, then `tab.go(folder)`. K: the line's search: the Ctrl+K shortcut (shell2.py:3189), `keyClicks` "Files", Down to the COMMANDS row "Files", Return (shell2.py:1166-1178, 1296-1302). `view` uses `tab.toggle_view()` when it differs (no key). | `{surface, folder, view, names}` | none |
| 4 | `go.open` | one of `sheet:S(1,200)`, `path:S(1,1000)`, `tab:I(0,200)`; `by:BY` | sheet: P left click at `sheet_rect` centre (opens; field_qt.py:777-781), K Return on the selected sheet (field_qt.py:539-544), after `point.sheet`. path: P double click on the row, K Return on the current row (`itemActivated`, files_qt.py:67-68). tab: `w.tabs.setCurrentIndex(i)`. | `{tab:{type,text}}` | the guard (a viewer that asks is refused) |
| 5 | `go.app` | `key:S(1,120)` | P: `head.open` Apps, then click `hatch.programs.rows_by_key[key]`. Direct: `w.type_bar.hatch.choose(key)`, "navigation only" (hatch_qt.py:203-211). K: — | `{tab}` | none |
| 6 | `go.back` | `by:BY` | Field only, else NOT_HERE. P: `field_page.back(w)` (field_page.py:197-212). K: Esc to the Field, sent only when no steps, go or what-if are showing, because the first Escs close those first (field_qt.py:548-553). | `{surface}` | none |
| 7 | `go.pane` | at least one of `left:E[files,machine,settings]`, `right:E[talk,activity,context]` | left: click `w.settings_navigator.bar.buttons[i]`, each connected to its own handler (settings_qt.py:261-262). right: `w.shell2.show_slate_face()` / `show_operations_face()` / `show_context_face()` (shell2.py:3552-3562). K: — | `{left: nav.current_view(), right}` | none |

### Point (navigates)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 8 | `point.sheet` | one of `title:S(1,200)`, `id:S(1,200)`; `by:E[direct,pointer,keys]` (default direct) | Needs the Field in front. Title matching: exact, else one case-blind substring; two matches refuse and name both. **direct:** `v.field.select(id); v._layout(); v._reveal(); v._describe(); v.update()`, the bundle at context_menu.py:1364-1365. **pointer:** a RightButton press and release at `v.sheet_rect(id).center()`, which selects and opens nothing (field_qt.py:725-727). If the rect is not inside `v.body()`, refuse: "That sheet is out of sight; point.zoom with to=whole brings the whole desk in." **keys:** `desk_acts.key_path(v.field, start, goal)` is a BFS over Home, End, the arrows and A (moves as `Field.move`, `first`, `last`, `next_attention`; field_model.py:207-278). It saves and restores `field.selected` and sends the keys. | `{selected:{id,title,kind,state}, presses}` | none |
| 9 | `point.move` | `way:E[left,right,up,down,first,last,next_waiting,before]`, `times:I(1,20)` | keys only: arrows, Home, End, A, Backspace to the Field (field_qt.py:521-558) | `{selected}` | none |
| 10 | `point.zoom` | `to:E[whole,reading,larger,smaller]`, `by:BY` | Z toggles (field_qt.py:528-530), so: whole presses Z only if `abs(v.zoom - v.fit()) >= 1e-6`; reading presses Z if whole, else Ctrl+0; larger is +, smaller is −. P: the strip's + and − places in `v._hot`. Then wait until `v._gliding is None` (190 ms glide, field_qt.py:260, 284-303). | `{zoom, whole}` | none |

### The head (navigates)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 11 | `head.open` | `menu:E[Work,Revise,Tools,Arrange,Commands,Rules,Properties,Guide,Apps]`, `by:BY` | **Apps:** `w.shell2.top.programs.click()`, which runs `hatch.open_list()` (shell2.py:598; hatch_qt.py:119-123). **Others:** the word from `top.menu_words()` (shell2.py:650-674). P: `word.menu().popup(word.mapToGlobal(QPoint(0, word.height())))`. Never `word.click()` or `showMenu()`: the word is InstantPopup (shell2.py:661) and enters a nested loop. K: no keyboard route exists. The doer sets focus on the word, arms a `QTimer.singleShot(250)` that reads the popup and hides it, then sends Space. It reports `keyboard_route:false`. | `{title, rows: [tool_faces.named(a.text())], open, keyboard_route}` (probe: Tools rows include "System Check"; opened in 0.11 s) | P never blocks; K is guarded by the timer |
| 12 | `head.row` | `menu:E[the 8 words]`, `row:S(1,120)`, `by:BY` | Only rows on `HEAD_ROWS`: Arrange › Today, Field, Files, Library, Project Desk, Changes, Continuing work, Graphite's Agenda, Cabinet; Tools › Explore capabilities, Tool Atlas, Algorithm & Theory Atlas (words from desk_read/tests_side/out4.json; a test checks each against the live menus). Any other row is refused with NOT_ALLOWED_ROW. That covers leave rows, Master Stop, dialogs and Undo. P: popup, then `QTest.mouseClick` at `actionGeometry(a).center()`. K: the line's search for the row's words, Down to its COMMANDS row, Return. | `{triggered: row, surface, tab}` | refused by the allow-list, then by the guard |
| 13 | `head.meter` | `which:E[CPU,GPU,RAM,TXT,equalizer]` | `top.pulse.open_card(k)` (desktop_header_qt.py:98-102), or `top.equalizer.show_card()` (equalizer_qt.py:318). The card's own buttons are not acts. | `{which, words}` (`w._meter_card.words` / `top.equalizer.words`) | none |

### The right-click and the line panel (navigates)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 14 | `menu.open` | `on:E[file,sheet,here]`, `name:S(1,1000)` (not needed for `here`), `by:BY` | **P:** a real `QContextMenuEvent(Mouse)` to the widget at the thing's point, the router's path (context_menu.py:2880-2889). Files: `tab.table.viewport()` (or `tab.icons.viewport()`) at `visualItemRect(item).center()`. Field: `v` at `sheet_rect(id).center()`. The finder selects what is under the point, as a person's right-click does (1505-1513, 1696-1709). **K:** Files: the table gets focus, then Home and Down until the current item is the file, then `cm.open_at_focus(w)`, the Menu key's own call (2837-2850, 2901-2902). Field: the Menu key to `v` emits `menu_asked`, which goes to `open_at_focus` (field_qt.py:615-616; field_page.py:79-83). Probe: target is the selected sheet, focus is on `field:open`. | `{target, first: menu.first_keys(), words, then_line}` (probe: `["open","ask","rename","trash","then","more"]`, `"@files:07 Bench readings.csv \| rows"`) | none |
| 15 | `menu.choose` | `path:S(1,400)` (segments joined by `/`, each a row key or its words), `by:BY` | Walk from `w.context_menu`. P: `QTest.mouseClick(row)` (ContextRow.choose → row_chosen, 2132-2134, 2381-2386), then settle. K: from the focus's index in `menu.focusables()` (−1 when none), press Down or Up the difference, then Right for a › row or Return for a leaf (probe counts: 4 to `then`, 2 to `step:where`, 4 to `field:unit`, 2 to the value). A path ending at `then` waits up to 2 s for `panel.ready` (2679-2688). **A leaf is checked before it runs.** If its `Entry.operation` names any non-read operation (split on ", ") or its caption is "asks", it is refused with CHANGES_ROW and the matching `hand.*` act is named: `files.trash` → hand.trash, `files.rename` → hand.rename. Today those rows act without her hand (context_menu.py:478-482). | `{chosen, child:{title, keys}, outcome: w._context_last}` | the guard; for example 'ask' → `QInputDialog.getText` (files_qt.py:402-404) is refused |
| 16 | `menu.close` | `by:BY` | P: a press outside, sent to the top popup (ContextMenu.mousePressEvent closes all, 2534-2547; a QMenu closes on an outside press). K: Esc to the popup (programs_qt.py:552). Covers `w.context_menu`, `QApplication.activePopupWidget()`, the Apps list and the meter card. "Nothing was open" is ok. | `{closed:[kinds]}` | none |
| 17 | `then.keep` | `column:S(1,120)`, `words:S(1,200)` (the row's words, e.g. "is mA" or "at least 110"; line_steps.py:195-202), `by:BY` | Needs an open `LinePanel` (else NOT_HERE). Walks `step:where` › the column's row › the row whose `Entry.label == words`. P clicks; K as in `menu.choose`. The direct equivalent is `panel.choose` (2747-2753). This avoids the `field:<column>` key clash (2709 against 1406-1445). | `{line, count: panel.count_words(), preview: panel.preview_rows()}` | none |
| 18 | `then.count` | `by:BY` | `step:count` row (2644-2645) | same as `then.keep` | none |
| 19 | `then.back` | `by:BY` | P: the `step:back` row. K: Backspace to the panel (2772-2775). | same | none |
| 20 | `then.end` | `how:E[show,line,copy,rows]`, `by:BY` | The `end:*` row (2654-2658). `line` is refused with UNSENT if the writing line holds words that no act put there (`host._desk_put`). | `{outcome: w._context_last, line: bar.box.text()}` | none |

### The Field's sheet (navigates)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 21 | `sheet.trace` | `by:BY` | Selected sheet required. K: T to `v` (field_qt.py:570-572). P: `menu.open` on the sheet, then `menu.choose` `more/field:trace/field:trace:all` (1432-1434, 1318-1324; probe: performed ok, Talk +3 cards, Field still in front). | `route:{owner_title, hops, ends:[titles], animating}` from `v._route` and `surge_elapsed()` (field_qt.py:1283-1318) | none |
| 22 | `sheet.doubt` | `by:BY` | K: X (567-569). P: menu › More › Doubt it (1429-1431). | `{reading: v.reading['title']}` | none |
| 23 | `sheet.compare` | `by:BY` | Refused with NO_SIBLING when `revision_sibling(v, obj)` is None (field_page.py:694-706). K: the Menu key, Down to `more`, Right, Down to `field:revisions`, Return. P: menu › More › Compare with Rev X. Both perform `compare_revisions` (743-752). | `revisions:{a, b, a_rev, b_rev, changed:[parameters]}` | none |
| 24 | `sheet.close` | `by:BY` | Closes what is over the work: revisions, a reading page, steps/go/what-if. K: Esc, sent only when something is over the work, since a bare Esc leaves the Field (field_qt.py:435-440, 500-501, 548-553). P: a click beside it (699-707). | `{over: null}` | none |
| 25 | `sheet.whatif` | `cell:S(2,8)`, `value:S(1,40)` | `w.shell2.ask('what if %s were %s' % (cell, value))` with the sheet selected: a read, `field.ripple` (context_menu.py:1270-1273) | `{would: v.would_said}` | none |
| 26 | `sheet.steps` | `by:BY` | K: D (561-563). P: menu › What can be done. Both run `field_page.do` (270-292). | `{steps:[{words, kind}]}` from `page.steps` | none |

### The writing line (navigates)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 27 | `type.to` | `who:E[her,terminal,search,web,log]`, `by:BY` | Mapping: her→slate, terminal→shell, search→find, web→web, log→log (typebar_qt.py:26). P: click `bar.targets[key]`. K: the shortcut of `w.a_talk[key]`, read from the action (menus2.py:154-165). Web has none, so it falls back to P. The act does what `bar.set_target(key, focus=False)` does (279-302). | `{target}` | none |
| 28 | `type.put` | `text:S(1,4000)`, `by:E[put,keys]` | Refused with UNSENT when the box holds unsent words that no act put there, and with PENDING when `w.console.pending_approval` is set. put: `cm.inspect_in_line(w, text, bar.target)` (context_menu.py:225-237). keys: `QTest.keyClicks(bar.box, text)`. | `{text, target, results:[popup rows]}` | none |
| 29 | `type.send` *(owner-only)* | `by:E[arrow,enter]` | arrow: `bar.submit_line()` (typebar_qt.py:423-433). enter: Return to the box. Web is refused always, and Terminal unless `stacy_hand.terminal_hers(text)` (stacy_hand.py:283-295), both with LEAVES_OR_SHELL. | `{target, output_tail}` | the guard |
| 30 | `type.room` | `size:E[line,half,tall]` | `w.console.set_size(0/1/2)` (console_qt.py:264-271) | `{room}` | none |

### Her hand (changes, through `SlateFace.stage`)

All Kernel changes use one helper:

```
card = face.stage(title, Step(words, 'write', field_do.op(op, **a), why, CAPABILITIES[op]), done, asked=True, word=word)
```

(shell2.py:1994-2033; field_do.py:25-43)

- `stacy_hand.hers` decides, as today (stacy_hand.py:150-158).
- **When it is hers, it runs at once.** The card shows the result; her trail gets an entry; Undo appears where one is allowed (shell2.py:2027-2030, 2064-2078).
- **Otherwise the card waits on Approve.** The act returns `waits:true` with the words of `stacy_hand.why_waits`.
- `word` is the typed line, or "scene P01 step n".

| # | Act | Arguments | Kernel line | Read-back | Dialog |
|---|---|---|---|---|---|
| 31 | `hand.write` | `path:S(1,1000)`, `text:S(0,1000000)` | `files.write` (on HERS_SHOW). Probe: `ran true, hers true, undo '/files.trash {"path": "07 Bench readings.csv"}'` | `{ran, hers, waits, why, undo, said}` | none (never the New File dialog) |
| 32 | `hand.rename` | `path`, `name:S(1,255)` | `files.rename` (not on her lists, so it waits) | same | none (never `QInputDialog`) |
| 33 | `hand.trash` | `path` | `files.trash` (HERS_SHOW; no Undo line, the Trash gives it back) | same | none |
| 34 | `hand.cell` | `cell:S(2,8)`, `value:S(1,40)` | `field_page.stage_set(w, v.selected(), cell, value, word)`, which uses `field.set` (field_page.py:496-522) | same, plus `go: v.go` | none |
| 35 | `hand.step` | `n:I(1,9)` | `field_page.do`, then `take(w, obj, n-1)` (270-327). The step's own line decides. | same, plus `kind` (a read step reports `kind:"read"`) | none |
| 36 | `hand.approve` *(owner-only)* | `by:BY` | The latest card with `ran is None`. P: `QTest.mouseClick(card.run)`. K: G to the Field when `v.go` is set (field_qt.py:573-575; field_page.py:261-267), otherwise P. NOTHING_WAITS when there is none. | `{ran, said}` | none |
| 37 | `hand.undo` *(owner-only)* | `{}` | `face.undo_entry(stacy_hand.trail(w.session.state)[0])` (shell2.py:2170-2190), which checks `changed_since` first. NOTHING_TO_UNDO when there is none. | `{state, trashed, said}` | none |
| 38 | `hand.dial` *(owner-only)* | `place:E[ask,show,free]` | `stacy_hand.choose(w, place)`, `w.session.save()`, `face.show_hand()` (stacy_hand.py:135-138; shell2.py:2137-2142) | `{place, said: named(...)}` | none |

### Look (owner-only, changes a kept rule of the window; no Kernel line, so not through stage)

| # | Act | Arguments | Call | Read-back | Dialog |
|---|---|---|---|---|---|
| 39 | `look.set` | at least one of `appearance:E[graphite,kasandra]`, `glow:E[soft,bright,neon]`, `art:E[illustrated,ascii,clean]`, `buttons:E[words,icons]`, `motion:E[normal,reduced]` | `boss_qt.choose_appearance(w, k, ask=False)`, which only takes effect at the next start (boss_qt.py:406-421); `choose_glow` (466); `choose_art` (477); `tool_faces.choose` (tool_faces.py:291-293); `reading_preferences.apply(w, {**document_qt.profile_of(w), 'reduce_motion': on}, persist=True)` (reading_preferences.py:100-134). `persist=True` matters because `menu_catch.calm` reads the session (menu_catch.py:29-43). Probe: `still true, calm true`, and still true after `sync_profile(force=True)`. | `{before:{…}, now:{…}, in_force: boss_theme.APPEARANCE, next: chosen_look(w)}` | `ask=False` never shows the restart question |

### Read back (navigates; a read; never journaled)

| # | Act | Arguments | Call | Read-back |
|---|---|---|---|---|
| 40 | `read.desk` | `part:E[all,where,field,menu,files,line,talk,look]` | `desk_doers.read_desk(w, part)` | See below. |

`read.desk` returns these parts:

- **where:** `surface`, read from `w.central_stack.currentWidget()`. The field page gives "field", `_home_active` gives "home", anything else is "workspace". It must not use `tabs.currentWidget()`; probe: FilesTab while the Field was showing. Also `title`, `tab:{type,text}`, `address: top.path.friendly()`, `left`, `right`, and `popups:[kinds]`.
- **field:** `face`, `selected{id,title,kind,state}`, `count`, `zoom`, `whole`, `gliding`, `reading`, `steps`, `go`, `would`, `problem`, `pending`, `route`, `revisions`.
- **menu:** `open`, `target`, `first`, `words`, `then_line`, `child{title,keys}`, `panel{line,count,preview,ready}`.
- **files:** `folder`, `view`, `names`, `selected`.
- **line:** `target` (her/terminal/search/web/log), `text`, `results`, `room`, `last_program`.
- **talk:** `cards`, `last` (the last card's first label), `hand`, `trail` (latest `{words,line,undo,state}`).
- **look:** `appearance`, `next`, `glow`, `art`, `buttons`, `motion`.
- **motion:** `still`, `calm`.
- **last:** `host._desk_last`, `w._context_last`.

### Refusal codes and words

Words go through `named()`. No key is printed and the line language is never named; it is always "a line".

| Code | Words |
|---|---|
| UNKNOWN_ACT | "There is no act named “X”." plus " Acts that start the same: a, b, c." |
| BAD_ARGUMENTS | One of: "X takes a, b; it was given c." / "X needs one of a, b." / "face is one of work, apps, network." / "text is too long." |
| NOT_HERE | One of: "The Field is not in front." / "No menu is open." / "No line panel is open; choose Then first." / "Nothing is selected in the Field." / "No sheet named “X” is on this face of the Field." / "Two sheets are named like “X”: A, B." / "That sheet is out of sight; point.zoom with to=whole brings the whole desk in." / "The keyboard is not on the Field." |
| CHANGES_ROW | "That row changes something; hand.trash does it through Stacy's hand." (with the act that matches the row), or "That row changes something; it stays yours." |
| NOT_ALLOWED_ROW | "That row is not one an act may choose: it asks, leaves or stops work, and stays yours." |
| NO_SIBLING | "This sheet has no other revision on the desk." |
| DIALOG | "It would open a window that asks; nothing was done." |
| UNSENT | "The writing line holds words you have not sent; they stay." |
| PENDING | "An operation waits for your approval in the working area; it stays." |
| LEAVES_OR_SHELL | "The Web and the Terminal are yours to send to." |
| NOTHING_WAITS | "Nothing waits for your Approve." |
| NOTHING_TO_UNDO | "Nothing of Stacy's can be taken back now." |
| NOT_OFFERED | "Acts are not offered to Stacy yet." |
| FAILED | "It could not be done: …" |

---

## 3. Her hand's rule for acts, and the export (not offered)

### `desk_acts.desk_hers(place, name, args=None, line=None) -> (bool, why)`

This is pure and tested, and nothing calls it in this pass.

| Act | Ask first | Do and show | Free hand |
|---|---|---|---|
| `read.desk` | hers | hers | hers (a read never asks; stacy_hand.py:154) |
| navigates (exported) | **offered, not done**: `(False, "it moves your window, and my hand is at Ask first")` | hers | hers |
| `hand.write/rename/trash/cell/step` | `stacy_hand.hers(place, CAPABILITIES[op], op, kernel_args)`; for `hand.step` the op comes from `field_do.call(line)` | same | same |
| owner-only | never: `(False, "only you do this")` | never | never |

- `stacy_hand.why_asks(name, args)` also runs on every act. No act argument is named in `LEAVES` (stacy_hand.py:58); a test holds this, which is why `go.files` takes `folder` and not `address`.
- `ALWAYS_ASKS` therefore wins at every place. For example, with `hand.step` and `line='/trash.empty {}'` at free, the rule gives `(False, 'the Trash, once emptied, cannot be brought back')`.
- `hers()`, `HERS_*`, `UNDOES` and `undo_allowed`/`clean` are unchanged. This is the owner's call to confirm: whether a navigation by her at Ask first should be offered (my recommendation) or done.
- `desk_acts.HAND_RULE` is the same rule as data, for the export:
  ```
  {"read":"never asks","navigates":{"ask":"offered","show":"done","free":"done"},"changes":"stacy_hand.hers on its Kernel line; what always asks still asks","owner_only":"never hers"}
  ```

### Doors in this pass

- **`door='owner'`** is the typed line. **`door='script'`** is tests, the campaign and probes. For both, navigates run directly and changes go through `stage` with `asked=True`, so her dial decides exactly as for "set B3 to 300" said to her.
- **`door='her'`** is refused with NOT_OFFERED. Her trail gets entries only for her own changes (through `card.hers`). Navigations never enter it, so 40 navigations can never push out acts that carry an Undo.

### Export (for later; nothing reads it now)

- **`desk_acts.tools(place='show')`** returns `[{name, words, mark, arguments, kernel, asks}]` for the 35 exported acts. Exported means every act that is not owner-only.
- **`desk_acts.plan_variants()`** returns
  ```
  [{"type":"object","properties":{"act":{"const":name},"arguments":schema},"required":["act","arguments"],"additionalProperties":false}]
  ```
  It is keyed `act`, never `operation`, so `checked_plan` can never take an act for an operation (local_brain.py:746, 772-793).
- Each exported schema stays at or under 300 bytes in compact form, because of the 2,048-token budget (local_brain.py:597-599).

---

## 4. The typed form in the writing line

**Form:** `/go.field face=apps`, `/point.sheet title="07 Bench readings" by=keys`, or `/hand.write {"path":"a.txt","text":"x"}`. This is the existing "/" door:

1. The line's row is activated (shell2.py:1101-1105, 1296-1307).
2. `to_console(host, 'kernel', text)` runs (shell2.py:1211-1221).
3. Then `Console.enter()` and `run_kernel()` (console_qt.py:376-383, 479-508).
4. `parse_command` already takes `name=value` (shlex quoting) or `{json}` (console_qt.py:67-81).

**Change in `console_qt.run_kernel`, after `parse_command` (console_qt.py:497-498) and before `if op not in CAPABILITIES` (499):**

```python
from . import desk_acts
if desk_acts.is_act(op) or desk_acts.looks_like_act(op):
    from .desk_doers import run as run_act
    r = run_act(self.host, op, args, door='owner', word='/' + text)
    self.say(escape(desk_acts.said(r)) if r['ok'] else self.refused(desk_acts.said(r)), echo='graphite › ' + text);return
```

- **Echo:** `graphite › go.field face=apps`, the same sign as operations (console_qt.py:262).
- **Body:** the act's words, e.g. "The Field is in front, its Apps face." A change that waits says "Waits for your Approve in Talk: it is not among the things I do by myself."
- **Refusal:** the existing `refused(...)`, the word "refused" on the eraser colour (442-443), followed by the words from §2.
- `looks_like_act` is true when the first part is one of the ten act heads, so `/go.feild` gets "There is no act named “go.feild”…" and not the Kernel's "Perhaps: programs.godot…" (probe output).

**`help`, `ops` and completion, extended in the same function:**

- `help NAME` for an act shows `<b>name</b> · navigates`, or `· changes, through Stacy's hand: files.write`, or `· yours only`. Then the words, then the same argument table.
- `help acts` lists all 40 as act · mark · words.
- `ops WORD` lists the matching acts first, then the operations.
- Tab completion (`Console.complete`, console_qt.py:351-358) offers act names and their argument names from `desk_acts.schema(name)`.
- The act's name is never printed on any row at rest. It appears only in the echo and in help or ops after the owner asked.

**Change in `shell2.OneBox.results`** (shell2.py:1102): the row's word is `'Act  '` when `desk_acts.is_act(name)`, otherwise `'Operation  '`.

**Side effect:** a typed act opens the working area, as every "/" line does (`console.open`, shell2.py:1217). The act cannot lose anything that way: `type.put` and `then.end how=line` refuse over unsent words or a pending approval.

---

## 5. One record per act

`desk_doers.run` writes once, after the act, with the existing `activity.record` (activity.py:99-107), the way the window already journals `console.shell` and `files.open` (console_qt.py:590, 605; qt_app.py:3309):

```
activity.record(host.root, origin, name, state, said_words, correlation_id=card.reply.get('correlation_id') if a change dispatched)
```

| Field | Value |
|---|---|
| origin | `desktop-owner` for the typed door; `desk-script:<scene id or test>` for scripts. `STACY` is reserved for later. |
| state | `DONE`, `WAITING` (a change waiting for Approve) or `REFUSED` |
| detail | Redacted to 300 characters by `activity.redact` (39-44) |

- To make the correlation id available, `run_staged` keeps the Kernel's envelope with one added line: `card.reply = r` after the dispatch (shell2.py:2042). That is a seed input, already edited in this pass.
- **Not journaled:** `read.desk`, following "reading is not an event" (activity.py:27).
- **Also kept:**
  - `host._desk_last = {act, door, by, ok, words, result}` in memory, for read-backs;
  - the Kernel's own receipts for any change, untouched;
  - her trail, for her own changes only, through `stage`.

---

## 6. The scene format, the runner, and P01

### Format (`graphite.scene/1`, JSON)

```json
{"schema":"graphite.scene/1","id":"P01","title":"After Hours 07, the playable scene","seed":"after_hours_07",
 "given":{"size":[1920,1200],"appearance":"graphite","dial":"show"},
 "runs":[{"name":"mouse","style":"pointer"},{"name":"keys","style":"keys"},
         {"name":"mouse_still","style":"pointer","reduce_motion":true},{"name":"keys_still","style":"keys","reduce_motion":true}],
 "steps":[{"act":"head.open","args":{"menu":"Tools"},
           "expect":{"act.result.title":"Tools","act.result.rows":{"contains":"System Check"}},
           "expect_by_run":{"keys":{"act.result.keyboard_route":false}},
           "expect_by_seed":{"bench":{}}}]}
```

- **Paths** are dotted paths into `{"act": <envelope>, "desk": <read.desk all, taken after the step>}`.
- **Matchers** are `desk_scene.matches`, the same forms as campaign `core.matches`: equal, `contains`, `startswith`, `in`, `decimal`, `gte`, `lte`, `between`, `not` (tools/campaign_lib/core.py:192-215). A test holds the two to the same answers.
- **`by`** is the run's style unless the step's args name one.

### Runner: `desk_scene.run_scene(host, scene, run, *, seed, origin, after_step=None)`

1. **Check `given.appearance`.** If `boss_theme.APPEARANCE` differs, return `{"blocked": "the appearance is chosen at start"}`. The colours are read once at import (boss_qt.py:408-410).
2. **Prepare the window.** `host.resize(*size)`, `host.activateWindow()`. Run `hand.dial` with `given.dial`. If `run.reduce_motion`, run `look.set motion=reduced` (door `script`) and keep `before`.
3. **For each step:**
   - run `desk_doers.run(host, act, args, door='script', by=style, origin=origin)`;
   - take `read.desk all`;
   - score `expect` merged with `expect_by_run[run.name]` and `expect_by_seed[seed]`.
4. **Implicit failures:**
   - an act that returned `waits:true` fails unless the step expects `act.result.waits`. An ask the scene did not declare fails, so "what always asks still asks" shows;
   - a DIALOG refusal fails unless expected;
   - an exception is a failure carrying its message.
   `after_step(n, step, result)` is called for each step.
5. **Restore.** Close menus; if motion was changed, run `look.set motion=<before>`.
6. **Return** `{"run", "seed", "steps":[{"n","act","ok","by","seconds","checks":[{"path","want","got","ok"}]}], "passed"}`.

### P01 (`tools/campaign_lib/data/scenes/P01.json`)

BENCH is the text of `BENCH_CSV` from tests_integrated/test_context_menu.py:31. Its rows match After Hours 07's "07 Bench readings" sheet (reader 3, out1.json).

| n | Act and args | Expect (all runs) | By run or seed |
|---|---|---|---|
| 1 | `head.open {menu:"Tools"}` | `act.result.title`="Tools"; `act.result.rows` contains "System Check"; `act.result.rows` `{"not":{"contains":"Programs"}}` | keys runs: `act.result.keyboard_route`=false |
| 2 | `menu.close {}` | `desk.where.popups`=[] | |
| 3 | `hand.write {path:"07 Bench readings.csv", text:BENCH}` | `act.result.ran`=true; `act.result.hers`=true; `act.result.undo`=`/files.trash {"path": "07 Bench readings.csv"}`; `desk.talk.trail.line` startswith "/files.write" | |
| 4 | `go.files {view:"list"}` | `desk.where.surface`="workspace"; `desk.files.names` contains "07 Bench readings.csv" | |
| 5 | `menu.open {on:"file", name:"07 Bench readings.csv"}` | `desk.menu.first`=["open","ask","rename","trash","then","more"]; `desk.menu.then_line`="@files:07 Bench readings.csv \| rows" | still runs: `desk.motion.calm`=true |
| 6 | `menu.choose {path:"then"}` | `desk.menu.panel.count`="4 rows · 6 steps left" | |
| 7 | `then.keep {column:"unit", words:"is mA"}` | `desk.menu.panel.count`="2 rows · 5 steps left" | |
| 8 | `then.count {}` | `desk.menu.panel.line`="@files:07 Bench readings.csv \| rows \| where unit=mA \| count"; `desk.menu.panel.preview`=[{"count":2}] | |
| 9 | `then.end {how:"line"}` | `desk.line.text`= that line; `desk.line.target`="her"; `desk.menu.open`=false; `act.result.outcome.ok`=true | |
| 10 | `go.field {}` | `desk.where.surface`="field"; `desk.field.face`="work" | |
| 11 | `point.zoom {to:"whole"}` | `desk.field.whole`=true | |
| 12 | `point.sheet {title:"07 Bench readings"}` | `desk.field.selected.title`="07 Bench readings" | |
| 13 | `sheet.trace {}` | `desk.field.route.owner_title`="07 Bench readings" | after_hours_07: `hops`=2, `ends` contains "07 Settled power" and "07 Startup power"; bench: `hops`=0 (probe). Still runs: `desk.field.route.animating`=false |
| 14 | `point.sheet {title:"07 Limits Rev B CURRENT"}` | `desk.field.selected.title` as given | |
| 15 | `sheet.compare {}` | `desk.field.revisions.a`="07 Limits Rev A ARCHIVED"; `.b`="07 Limits Rev B CURRENT"; `.changed` contains "Pulse duration"; `.changed` contains "Pulse ceiling" | |
| 16 | `sheet.close {}` | `desk.field.revisions`=null; `desk.where.surface`="field" | |
| 17 | `hand.undo {}` | `act.result.state`="undone"; `act.result.trashed`="07 Bench readings.csv" | |

**How each style does it.** The mouse and keys forms each come from the act's own doer.

- **Keys:**
  - step 1: focus the word, then Space under a timer guard;
  - steps 4 and 12-14: the line's search, F9, Home and the searched arrows, T;
  - steps 5-9: the Menu key, Down, Right, Return; the probe's counts were 4, 2, 4, 2, 4, 6;
  - step 15: the Menu key › More › Compare;
  - step 16: Esc.
- **Mouse:**
  - head rows by popup and click;
  - real right-clicks;
  - row clicks;
  - a right press to select (step 12).

**Bench seed** (tests): built through Graphite's own operations. The probe proved it gives three Field sheets of kind "sheet", so `revision_sibling` finds the pair.

- Use `files.write` for `seed/07 Bench readings.csv` (BENCH), `seed/07 Limits Rev A ARCHIVED.csv` and `seed/07 Limits Rev B CURRENT.csv`.
  - Rev A: `parameter,value,unit,conditions` / `Pulse duration,120,ms,` / `Pulse ceiling,,,Up to 120 ms`
  - Rev B: the same with 80 and "Up to 80 ms".
- Then run `office.import.preview {path: <files root>/seed/<name>}`, which returns `id` and `digest`.
- Then `office.import.commit {plan: id, expected_digest: digest}`.
- The cells are read as rows when a sheet has no reviewed rows (field_page.py:709-727).

### Adapters

- **Test:** `tests_integrated/test_desk_scenes.py`, §8.
- **Campaign:** `tools/campaign_lib/cases_scene.py`.
  - Cases `P01a` (mouse), `P01b` (keys), `P01c` (mouse_still), `P01d` (keys_still).
  - Each has `set='scenes'`, `seed='after_hours_07'`, `needs=['after_hours_07']`, `budget_s=240`, `inputs={'scene':'P01','run':…}`.
  - `expect` is flattened to `"<n>:<path>"` with values for the after_hours_07 seed and the run.
  - `fn=run_case`:
    1. builds `WorkbenchWindow(ctx.kernel.root, Session(ctx.folder/'profile/session.json', ctx.kernel.root), restore=False)` behind the same holds as test_context_menu.py:56-64, plus `_guard_launch` (cases_anchor.py:61-66);
    2. stops `ledger_bridge.timer`, the lifecycle timer, `agenda_runner` and `study_idle`;
    3. runs `run_scene(..., origin='desk-script:P01')`;
    4. per step: `ctx.progress('act', n=…, act=…, ok=…)`, `ctx.observe('%d:%s' % (n, path), got)` per check, and `w.grab().save(ctx.folder/'shots'/'%02d.png' % n)`.
  - The child already runs offscreen and embedded (fixture.py:52-56).
- **Probe (optional, outside the repo):** a REHEARSAL_SCRIPT body can call `run_scene(w, …)` in place of reaching into widgets.

---

## 7. Files and functions

### Add

| File | What | Seed input? |
|---|---|---|
| `workbench/desk_acts.py` | `Act` dataclass; `ACTS` (the 40); `ACT_HEADS`; `HEAD_ROWS`; `is_act`, `looks_like_act`, `schema`, `check(name, args)` (raises `Refusal(code, words)`), `said(env)`, `desk_hers`, `HAND_RULE`, `tools`, `plan_variants`, `key_path(field, start, goal)`, `REFUSALS` | no (not added to SEED_FILES) |
| `workbench/desk_doers.py` | `run(...)` (§2, §5), `DOERS`, `no_dialogs()`, `settle(host, ms=30, n=3)`, `wait_until(pred, ms)`, `read_desk(host, part)`, the change helper `stage_change(host, words, op, args, why, word)`, `_by_search(host, words)`, `_keys_to(menu, key, last)` (the keysprobe algorithm) | no |
| `workbench/desk_scene.py` | `load(path)`, `check_scene(scene)`, `matches(want, got)`, `run_scene(...)` | no |
| `tools/campaign_lib/data/scenes/P01.json` | the scene (§6) | no; in the campaign library digest (core.py:44-56) |
| `tools/campaign_lib/cases_scene.py` | `CASES` (P01a-d), `run_case` | no |
| `tests_integrated/test_desk_acts.py` | §8 | no |
| `tests_integrated/test_desk_scenes.py` | §8 | no |

### Change

| File | Change | Seed input? |
|---|---|---|
| `workbench/console_qt.py` | `run_kernel` routes acts (§4); `help NAME`, `help acts` and `ops WORD` list acts; `complete()` offers act names and arguments | **yes** (stacy_foundation.py:114) |
| `workbench/shell2.py` | `OneBox.results`: the 'Act' word for an act line (1102). `OneBox.commands`: label `action.text().replace('&','').split('\t')[0].strip()` and hint `''`, so no key is printed (1174-1177). `run_staged`: `card.reply = r` (2042). | **yes** (159) |
| `tools/campaign_lib/runner.py` | `SETS = ('resource','anchors','selftest','real','scenes')` (39); `registry()` adds `cases_scene.CASES` (85-88); `select` error words name scenes; `select(None/'all')` unchanged | no |
| `tools/campaign.py` | the `--set` help names scenes (42) | no |
| `tools/check_hatch.py` | `FOCUSED_MODULES` gets `# 0.8.2: desk acts: the registry, her hand's rule, the typed door, the playable scene` then `'test_desk_acts','test_desk_scenes'` (34-65) | no |
| `MANIFEST.json`, `project/stacy_seed/current/*` | rewritten by `python3 tools/package_graphite.py --manifest-only`, last | (output) |

**Build order:**

1. `desk_acts.py` and the pure tests.
2. `desk_doers.py` and the live tests.
3. The console and shell2 edits.
4. `desk_scene.py`, `P01.json` and `test_desk_scenes`.
5. The campaign set.
6. `FOCUSED_MODULES`.
7. Run, each on its own: `test_desk_acts`, `test_desk_scenes`, `test_stacy_hand`, `test_context_menu`, `test_writing_line`, `test_campaign`, `test_release_check`, `test_tool_selection`. `test_desk` and `test_graphite` already fail before this pass (1f59293's message), and reader 3 saw `test_paper` fail on c401f59; leave all three as they are.
8. `--manifest-only`.
9. `python3 tools/check_release.py`. Registry, settings and adapters must be PASSED; the runtime section must be PASSED after packaging.

---

## 8. Tests (exact assertions)

Both modules use the test_context_menu fixture, copied:

- environment: `ARC_LEDGER_EMBEDDED`, `ARC_LEDGER_DISABLE_BOOK_WATCHER`, a temporary profile and Concern folder, `ARC_LEDGER_XSESSION` removed;
- holds before the build: `clip._request`, `Kernel.launch`, `Kernel.submit`, `session_power.system`, `QMessageBox.question`;
- holds after the build: `subprocess.Popen`, `os.system`, `QProcess.startDetached`;
- timers stopped as in `settle()`;
- 1920×1200; one window per module (test_context_menu.py:44-88).

The bench seed is built in `setUpModule`. `key_literals`, `KEY_TEXT` and `KEY_CAPTION` are imported from `tests_integrated.test_context_menu` (896-914, 33-36).

### `test_desk_acts`, pure (no window)

1. **`test_forty_acts_and_their_marks`.**
   - `30 <= len(ACTS) <= 40`.
   - Every mark is in {'navigates','changes'}.
   - `{n for n in ACTS if ACTS[n].mark=='changes'} == {n for n in ACTS if n.startswith(('hand.','look.'))}`.
   - Every schema has `type=='object'`, `additionalProperties is False`, and `set(required) <= set(properties)`.
   - Every act with a `kernel` op has `CAPABILITIES[kernel] != 'read'`. Every changes act has a kernel op or is owner-only.
2. **`test_no_act_is_a_kernel_name`.**
   - `not (set(ACTS) & set(CAPABILITIES))`.
   - `ACT_HEADS.isdisjoint({o.split('.')[0] for o in CAPABILITIES})`.
   - No act name is in the operations of `docs/GRAPHITE_0.1_REGISTRY.json`.
3. **`test_no_argument_leaves`.** `not ({p for a in ACTS.values() for p in a.schema['properties']} & set(stacy_hand.LEAVES))`.
4. **`test_check`.**
   - `check('go.field', {'face':'apps'}) == {'face':'apps'}`.
   - `check('sheet.whatif', {'cell':'B4','value':100}) == {'cell':'B4','value':'100'}`.
   - Bad face: `Refusal('BAD_ARGUMENTS', 'face is one of work, apps, network.')`.
   - `{'colour':'x'}`: words `'go.field takes face, by; it was given colour.'`
   - `go.open` with none of its three: `'go.open needs one of sheet, path, tab.'`
5. **`test_desk_hers`.**
   - `[desk_hers(p,'read.desk')[0] for p in ('ask','show','free')] == [True,True,True]`.
   - `go.field` gives `[False,True,True]`, and `desk_hers('ask','go.field')[1] == 'it moves your window, and my hand is at Ask first'`.
   - `hand.write {'path':'a','text':'b'}` gives `[False,True,True]`.
   - `hand.rename` gives `[False,False,False]`, with why `'it is not among the things I do by myself'` at show.
   - `desk_hers('free','hand.step',{'n':1}, line='/trash.empty {}') == (False,'the Trash, once emptied, cannot be brought back')`.
   - Each owner-only act is False at every place.
6. **`test_exported_but_not_offered`.**
   - `E = {t['name'] for t in tools()}`; `len(E) == 35`; `E.isdisjoint({'hand.approve','hand.undo','hand.dial','look.set','type.send'})`.
   - `E.isdisjoint(local_brain.DIRECT_OPERATIONS)` and `E.isdisjoint(local_brain.CORE_OPERATIONS)`.
   - For each message in ('open the field','trace the bench readings','put it in the writing line','zoom out'): the consts in `proposal_profile(m)[0]['properties']['actions']['items']['oneOf']` are disjoint from `set(ACTS)`.
   - `{'ledger.navigate','ledger.open'} <= tool_selection.DENY`.
   - Every variant in `plan_variants()` has `'act' in v['properties']` and `'operation' not in v['properties']`.
   - Every exported schema is at most 300 bytes compact, and `len(json.dumps(plan_variants(), separators=(',',':'))) <= 9000`.
7. **`test_words_print_no_key_and_never_name_the_language`.**
   - `key_literals(['workbench/desk_acts.py','workbench/desk_doers.py','workbench/desk_scene.py']) == []`.
   - Across all act words, all `REFUSALS` and `HAND_RULE`: no match for `r'(?i)\bstac\b|stacy language|\bprograms\b'`.
8. **`test_key_path`.** On a `field_model.Field` of five objects in three columns with one wire: `key_path(f, a, e)` is a shortest list. Replaying it through `Field.move/first/last` from `a` ends on `e`, and `f.selected` is unchanged after the call.
9. **`test_matches_mirror_the_campaign`.** For 14 fixed (want, got) pairs, two per form plus plain equality, `desk_scene.matches(w,g) == core.matches(w,g)`.
10. **`test_p01_is_well_formed`.**
    - `check_scene(load(P01))` returns [].
    - Every step's act is in `ACTS` and its args pass `check`.
    - The run names are `['mouse','keys','mouse_still','keys_still']`.

### `test_desk_acts`, live

11. **`test_navigation_changes_no_record`.**
    - Before and after `go.field`, `point.sheet` (all three forms), `point.zoom whole`, `go.files`, `head.open Tools`, `menu.close`, `go.today`, `go.pane left=machine right=activity` and `read.desk`: `fixture.state_digest(k)[1]['counts']` is equal after dropping `JOURNAL`. The builder sets `JOURNAL` once from a measured run of reads only (the activity tables and the audit table).
    - The Files listing `[e['path'] for e in files.list entries]` is equal.
    - `office.list` documents and versions are equal.
12. **`test_typed_act_in_the_writing_line`.**
    - `keyClicks(bar.box, '/go.field face=apps')`, then Return.
    - `w._field_active` and `w.field_page.face == 'programs'`.
    - The console output contains `'graphite › go.field face=apps'` and not `'refused'`.
    - The journal's last event: `operation=='go.field'`, `origin=='desktop-owner'`, `state=='DONE'`.
    - `'/go.feild'` gives output containing `'There is no act named “go.feild”'`.
    - `re.search(KEY_TEXT, output)` is None, and no `\bstac\b` in it.
    - The result row word for an act line starts with `'Act'`.
13. **`test_help_and_ops`.**
    - `run_kernel('help go.field')` contains `'navigates'` and `'face'`.
    - `help hand.write` contains `'files.write'`.
    - `ops sheet.` lists `sheet.trace` and `sheet.compare`.
    - `help acts` lists 40 names.
14. **`test_change_acts_follow_her_dial`.**
    - At show, `hand.write path='hand test.txt' text='x'`: `ran True`, `hers True`, `undo == '/files.trash {"path": "hand test.txt"}'`, `stacy_hand.trail(state)[0]['line'].startswith('/files.write')`. Then `hand.undo`: the trail's latest has `state == 'undone'`.
    - At ask, `hand.write path='hand test 2.txt' text='x'`: `waits True`; the journal state is `'WAITING'`; `card.ran is None`. Then `hand.approve`: `ran True`, and the trail length is unchanged (the owner's Approve is not her act).
    - At show, `hand.rename`: waits, and its why is `stacy_hand.why_waits('show','execute','files.rename')`.
15. **`test_menu_choose_refuses_change_rows_and_dialogs`.** On the CSV:
    - `menu.choose path=trash`: `error.code == 'CHANGES_ROW'`, words name `hand.trash`, and the file is still listed.
    - `menu.choose path=ask`: `error.code == 'DIALOG'` and `QApplication.activeModalWidget() is None`.
    - `menu.choose path=more/copy:path`: ok.
16. **`test_head_acts_never_block`.**
    - `head.open Tools` (pointer) returns in under 2.0 s, open, with rows containing `'System Check'`.
    - `head.open Apps`: `hatch.programs.isVisible()`.
    - `head.row menu=Work row="Log out"` gives `NOT_ALLOWED_ROW`.
    - Every `HEAD_ROWS` entry exists in the live menus by `tool_faces.named`.
    - `menu.close` leaves `read.desk where.popups == []`.
17. **`test_command_search_prints_no_key`.** After the line's search for "field", no result row text matches `r'\s(F\d{1,2}|Alt\+\d|Ctrl\+\w)\s*$'` and none contains `'\t'`.
18. **`test_read_desk_reads_the_centre`.** With a FilesTab current, `go.field`, then `read.desk`: `where.surface == 'field'`.
19. **`test_look_set_motion`.**
    - `look.set motion=reduced`: `w.field_page.view.still() is True`, `menu_catch.calm(w) is True`, `w.session.state['reading_profile']['reduce_motion'] is True`, `result.before.motion == 'normal'`.
    - `look.set appearance=kasandra`: `result.next == 'kasandra'` and `result.in_force == boss_theme.APPEARANCE`. Then restore both.
20. **`test_one_record_per_act`.** Journal rows with origin `'desk-script:test'` grow by exactly 9 over 10 acts, one of them `read.desk`.

### `test_desk_scenes` (bench seed)

21. `test_p01_by_mouse`, `test_p01_by_keys` and `test_p01_by_mouse_reduced_motion`.
    - Each runs `run_scene(w, load(P01), run, seed='bench', origin='desk-script:P01')`.
    - Each asserts `out['passed']`, with the failing checks as the message: `[(s['n'], c) for s in out['steps'] for c in s['checks'] if not c['ok']]`.
    - Each also asserts `not (files_root/'07 Bench readings.csv').exists()` afterwards.
    - `setUp` closes menus, leaves the Field, moves any leftover CSV to the Trash through the Kernel, and runs `hand.dial show`.

Both modules must pass on their own as `python -B -m unittest -v tests_integrated.<name>` within 600 s (check_hatch.py:310-320). test_context_menu's single window takes about 60 s, so the budget is ample. Once listed, `test_release_check`'s "a test module nothing runs" holds (test_release_check.py:223-229).

---

## 9. Not in this pass

- **Her door.** Nothing calls `desk_hers`, `tools()` or `plan_variants()`, and acts are not offered to any model. No word form ("open the Field" said to her) and no MCP, PWA or CLI exposure. No `ledger.navigate` destination for the Field. `door='her'` refuses.
- **Model proposals still skip her hand.** Run calls `execute()` directly (shell2.py:2699ff; task #35).
- **A person's own right-click change rows** (Rename…, Move to Trash, Copy or Move to) still act without her hand. This pass only refuses them in `menu.choose`.
- **Trail and Undo gaps stay.** A card that waited and was Approved gets no trail entry. There are no Undo lines for `files.rename` or `files.trash`.
- **A keyboard route to the head menus** (gap §0.2; the scene records `keyboard_route:false`).
- **The Kasandra run of P01.** The appearance is chosen at start (boss_theme.py:88-98); a campaign child started with `GRAPHITE_APPEARANCE` is a later case.
- **Acts for dialog-only work:** New File, Open…, Import, Export, Versions, Copy or Move to, confined runs, Master Stop, the leave rows, and the meter cards' GPU and stop buttons. The guard refuses them.
- **Converting the existing tests and offscreen probes** to acts. Nothing is removed.
- **Adding the new modules to `SEED_FILES`.**
- **Keys printed on screen elsewhere, seen and left alone:**
  - console_qt.py:495 ("asks for a second Enter") and 504 ("Press Enter again … press Esc");
  - the stage card's tooltip "in the Field, G does the same" (shell2.py:2023);
  - the Field action's tooltip "(F9)" (menus2.py:187);
  - the status line "· R looks again" (field_page.py:137).
  Act words never reuse these strings. The only key fix in this pass is the command search (§0.3), because the keys-style scene reads it.