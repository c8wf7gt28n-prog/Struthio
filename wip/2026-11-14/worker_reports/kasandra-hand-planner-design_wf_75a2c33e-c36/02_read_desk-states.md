# The desk as states and acts: a planner's map (part: states_acts)

**Abbreviations.** A = `workbench/desk_acts.py`, D = `workbench/desk_doers.py`, H = `workbench/stacy_hand.py`, SH = `workbench/shell2.py`, FP = `workbench/field_page.py`, FQ = `workbench/field_qt.py`, SC = `workbench/desk_scene.py`, T = `tests_integrated/test_desk_acts.py`. All line numbers are at HEAD d1df337.

**Live evidence.** I ran three probes on the bench window: `build_window` (T:43) from a `git archive` copy, through `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/desk/harness.py`, offscreen, under `unshare`. No model was loaded and nothing under /home/user/Struthio was touched. Outputs are cited as:
- P1 = `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/probe.out`
- P2 = `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/probe2.out`
- P3 = `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/probe3.out`

The abstraction function is `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/probe_ab.py`. The toy planner over P01 is `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_read/states_acts/plan_p01.py` (pure Python, run with `python3 -I`).

## 1. State vocabulary

### 1a. What read.desk reports (`read_desk`, D:580-649)

| Part | Fields | Source |
|---|---|---|
| where | surface (`field`/`home`/`workspace`, read from the central stack, never the tabs), title, tab {type, text}, address, left (`files`/`machine`/`settings`), right (`talk`/`activity`/`context`), popups | D:585-600, surface D:175-181, popups D:558-577 |
| popups | any of `menu`, `panel`, `head:<M>`, `apps`, `meter`, `equalizer`, else the class name of the active popup | D:560-577 |
| field | shown, face (`work`/`apps`/`network`, mapped from the internal `programs`), selected {id, title, kind, state}, count, zoom, whole, gliding, reading (title), steps [{words, kind}], go, would, problem, pending, route {owner_title, hops, ends, animating}, revisions {a, b, a_rev, b_rev, changed} | D:601-610, FACE_WORD D:46, whole D:537-540, route D:543-548, revisions D:551-555 |
| menu | open, target, first (root keys), words, then_line, child {title, keys}, panel {line, count, preview (≤3 rows), ready} | menu_said D:506-517, panel_said D:520-521 |
| files | folder, view, names, selected; `None` unless Files is the current tab | D:612-619 |
| line | target (`her`/`terminal`/`search`/`web`/`log`), text, results (popup rows), room (`line`/`half`/`tall`), last_program | D:620-626, WHO D:41, ROOMS D:43 |
| talk | cards, last (≤300 characters), hand (dial), trail (latest entry only: words, line, undo, state) | D:627-636 |
| look | appearance (in force), next, glow, art, buttons, motion | look_now D:652-658 |
| motion | still (`None` with no Field page), calm | D:638-646 |
| last | the last act's envelope summary, `_context_last` | D:647, D:1450 |

### 1b. What the doers depend on that read.desk does not report

A planner has to know these, so they should be added to read.desk:

| Hidden state | Used by | Evidence |
|---|---|---|
| Where the keyboard is | `keyboard_on` D:285-286. Every keys form needs it (D:291, D:766, D:921, D:937, D:1105). `point.move` exists only by keys (`forms='K'` A:125, form_for D:1406). The `point.zoom` pointer falls back to keys D:857-863 | Not read |
| Whether the line's words are ours or the owner's | `unsent` D:352-355 compares against `host._desk_put`. UNSENT refusals: D:363, D:1062, D:1202 | P1:73-82: ours is overwritten, the owner's words refuse |
| A pending Kernel approval in the console | PENDING refusals D:1063, D:1203; set at console_qt.py:532-533 | Not read |
| Cards waiting for Approve | `waiting_cards` D:1290-1306 | P1:168-173: one card waits, read.desk shows only `cards` +1 |
| Whether the Field was entered from Today | `_field_from_home` FP:171, used by `back` FP:199-203 | P2:64-68: `go.back` lands on `home` |
| Whether a given sheet is in sight | `sheet_point` D:211-216 | P2:154-158: NOT_HERE at 150% |
| The Field's objects, kinds and links (read.desk gives only `count`) | `find_sheet` D:196-208, `revision_sibling` FP:694-706, `trace_route` FQ:1270-1302, `key_path` A:399-415 | |
| Row state on the current screen (enabled, asks, operation, listed) and the panel's columns and values | D:425-445, D:477-486 | |

### 1c. A finite abstraction a planner can search

The object constants are read once at the start of a turn: the sheets on each face, the folders and files, HEAD_ROWS (A:37-38), and MENU_ROWS / PANEL_ROWS (A:46-54). A panel line is the base plus at most 7 steps (`MOST_STAGES=8` at line_steps.py:23, `steps_left` line_steps.py:57-59), so every fluent below has a finite domain.

| Fluent | Domain | Read from | Unknown / N/A rule |
|---|---|---|---|
| `surface` | field, home, workspace | where.surface | — |
| `centre` | files, page, app, record, none | where.tab.type (FilesTab, OfficePanel, CabinetRecordTab… P2:49-53, P2:139-143) | — |
| `panes` | left × right (3×3) | where.left / right | — |
| `popups` | a subset of {menu, panel, head:M (8), apps, meter, equalizer} | where.popups | **Stale.** Only `menu.close` clears it (D:992-1014). `head:Tools` survived seven later acts (P1:88-142). A sheet's menu survived go.files, type.room, go.pane, go.field and head.row (P2:119-173). |
| `face` | work, apps, network | field.face | N/A until the Field page exists (D:603) |
| `sel` | Objects(face) ∪ {none} | field.selected | `go.field` selects the first sheet (P1:92, P3:6-10). A face change moves `sel` (P3:41-55). |
| `view` | whole, reading (zoom = 1), other | field.whole, zoom | `in_sight(s)` follows from whole; otherwise unknown |
| `over` | none, reading(doubt/steps/page), revisions(a,b), steps, go, would | D:1116-1117 | A new reading clears `would` and reading (FQ:165-166), so this goes unknown after any refresh |
| `route` | owner ∈ Objects ∪ {none} | field.route | **Shown only while owner = sel** (FQ:1257). read.desk reports a stale route: still owned by 07 Bench readings after the selection moved and a paint (P2:12-17). On the Apps face it reported a raw id (P3:41-45). |
| `menu` | closed, root(t), screen(t, title), panel(t, L) | menu.* | — |
| `files` | folder, view ∈ {icons, list}, has(name), selected | files.* | N/A unless Files is in front |
| `line` | target (5), text ∈ {empty, ours(L), owner's}, room (3), pending | line.* + hidden | ours vs owner's and pending are hidden today |
| `hand` | ask, show, free | talk.hand | — |
| `waiting` | 0, ≥1 | hidden | — |
| `undoable` | bool | talk.trail.state = done ∧ undo | Only the latest trail entry is shown |
| `look`, `motion` | enums, still/calm | look, motion | — |

**Rules for certainty and unknowns:**
- **Certain effects** are those the doer checks before returning ok; otherwise it raises FAILED. These are: `go.field` surface (D:710), `go.files` Files in front (D:736), `point.sheet` (D:837), `menu.open` (D:947-952), `menu.close` (D:1012-1013), `then.end` outcome (D:1070), `sheet.trace` (D:1087-1088), `sheet.compare` (D:1111-1112), `sheet.close` (D:1149), `type.to` (D:1189), `type.put` (D:1210-1213), `hand.undo` (D:1352).
- **Observed effects** are everything else, for example `go.files` folder and view (D:737-738), zoom (D:864-867), doubt, steps, go.back, go.today. They are unknown until the next read.desk.
- **read.desk is free sensing.** It writes no journal line (D:1451) and took 0.115 s (P2:169-173).
- **A refusal is not a no-op.** A `menu.choose` that failed left the "More" screen open (P3:86-90). A refused `hand.cell` still lists `field.set` in `changed` (P2:28-33). `changed` means attempted (`watching` D:126-128), not landed. Read back after every refusal.
- **The owner's own input, or a background refresh, makes every fluent unknown**, because the window is shared.

## 2. The 40 acts as operators

**Notation.** F = surface is field; sel = a sheet is selected. ✓ marks an effect the doer checks itself. "Hers" gives `desk_hers` at the Ask first / Do and show / Free hand places, run on this copy (A:299-339). N(nav) means "it moves your window, and my hand is at Ask first" (A:327). N(list) means "it is not among the things I do by myself" (H:164). Forms are A:111-171. Her door would use the default form: `by` is stripped by `offered` (A:347), and form_for gives pointer or direct (D:1409).

**Navigations.** All are mark `navigates`, exported, and Hers N(nav)/Y/Y, except `read.desk` (Y/Y/Y). This is the 30 asserted at T:382.

| Act | Pre | Add | Delete | Observe |
|---|---|---|---|---|
| `go.field {face?}` | — (pointer goes through Arrange › Field D:707-708) | surface=field ✓; face=f (D:711-720) | — | sel, zoom (1.0→0.8 at P2:114-118), whole (false at 900×640, P2:144-148); popups untouched (P1:88-92) |
| `go.today` | — | surface=home (P2:54-58) | Field in front | — |
| `go.files {folder?, view?}` | keys form only: no owner words (D:346, D:363) | workspace + Files ✓ (D:736); folder, view (D:737-738) | — | names; popups untouched (P2:124-128) |
| `go.open {sheet}` | F; sheet on this face and unique (D:196-208; P3:46-60); pointer: in sight | its page tab | surface=field → workspace (P2:49-53) | — |
| `go.open {path}` / `{tab}` | Files + file in folder (D:233-237) / 0 ≤ tab < count (D:752) | tab | Today (D:753) | surface stays field if the Field is in front (D:175-181) |
| `go.app {key}` | row present and enabled (D:783-786); `documents` needs one document to exist (MAKES, D:777-781) | app tab | — | — |
| `go.back` | F; keys form: nothing over the work (D:794-795) | surface = home or workspace (FP:197-212; P2:64-68) | field | which one (hidden) |
| `go.pane {left?, right?}` | — | panes (D:806-814) | — | left=files opened a Cabinet record tab (P2:139-143) |
| `point.sheet {title\|id}` | F; on the face, unique; pointer: in sight (P2:154-158); keys: keyboard on the Field | sel=s ✓ | steps and go (FQ:176); route as shown (FQ:1257) | revisions persist (P1:123-127, P3:21-25) |
| `point.move {way, times}` | F; keyboard on the Field (keys only, D:291) | sel = move(sel), computable (A:386-396) | — | P2:159-163 |
| `point.zoom {to}` | F; may fall back to keys and then need the keyboard (D:857-863) | whole / zoom=1 / ±0.10 (FQ:530-533; P2:149-153) | — | not checked; no-op when already whole (P1:93-97) |
| `head.open {menu}` | — | popups + head:M (keys form reads and hides it, D:881-890) | — | rows as evidence (P1:83-87) |
| `head.row {menu, row}` | row in HEAD_ROWS (D:345); keys form: no owner words | depends on the row (Today → home, P2:164-168) | — | — |
| `head.meter {which}` | — | popups + meter or equalizer (D:903-910) | — | words |
| `menu.open {on, name?}` | file: Files + file present; sheet: F, found, in sight; name needed (D:916); keys: keyboard not in a text field (D:950-951) | menu(t) ✓; replaces an open menu (P2:79-83); file selected (P1:38-42) | panel | first, then_line |
| `menu.choose {path}` | a menu is open (D:981); each segment present and enabled (D:477-483); inner rows open screens (D:485-486); last row listed and not changing (D:436-445) | then → panel(base), waits until ready (D:496-497); screen → child; row → outcome (D:500-502, D:987-988) | — | walks whatever root menu is open; the target is never checked (D:979-983) |
| `menu.close` | — | popups = ∅ ✓ | menu, panel, head menus, Apps, cards | — |
| `then.keep {column, words}` | panel (D:400-405); `step:where` offered (D:1039); the rows exist | L += `where c=v` (P1:48-52) | — | count, preview |
| `then.count` | panel; `step:count` offered | L += `count`. Not idempotent: twice gives `\| count \| count` (P2:99-108) | — | — |
| `then.back` | panel; L ≠ base (D:1049; P2:94-98) | L = back_a_step(L) (line_steps.py:80-82) | — | — |
| `then.end {how}` | panel; `line`: no owner words, nothing pending (D:1061-1063) | ending ran ✓; `line`: text = L, ours (D:1067) | menu, panel (P1:68-72) | target `her`; `show` grows room line→half (P2:109-113) |
| `sheet.trace` | F; sel (D:1083); pointer: in sight (works under a comparison, P3:26-30) | route(sel) ✓ | — | hops and ends, deducible from FQ:1270-1302; Talk +2 cards (P1:103-107) |
| `sheet.doubt` | F; sel | over = reading(Doubting …) (P2:18-22) | — | Talk +2 cards |
| `sheet.compare` | F; sel; face=work; a sibling by title (D:1103, FP:691-706; NO_SIBLING at P1:108-112) | over = revisions(older, newer) ✓; the same pair whether started from Rev A or Rev B (P1:118-122, P3:16-20) | reading (FQ:416) | changed rows |
| `sheet.close` | F | over = ∅ ✓ (D:1116-1117) | reading, revisions, steps, go, would | route kept |
| `sheet.whatif {cell, value}` | F; sel; a sheet or calculation with a number at the cell (D:1155-1161; P3:76-80) | would | — | a Talk card in the owner's voice (D:1162) |
| `sheet.steps` | F; sel; pointer: in sight | pointer: a menu on "What can be done" (P1:133-137); keys: steps page + Talk card (P1:143-147) | — | the step kinds differ by form |
| `type.to {who}` | — | target ✓ | — | — |
| `type.put {text}` | no owner words (P1:78-82); nothing pending; no unseen characters (A:274) | text, ours ✓ | — | results |
| `type.room {size}` | — | room (P2:129-133) | — | — |
| `read.desk {part}` | — | sensing only | — | everything |

**Owner-only acts.** These are never hers at any place: "only you do this", A:311, A:33.

| Act | Pre | Add |
|---|---|---|
| `type.send` | text present; target not the Web; the Terminal only for `terminal_hers` (D:1219-1220) | sent; text cleared |
| `hand.approve` | a card waits (D:1322; P3:71-75) | the latest waiting card runs (P1:174-178) |
| `hand.undo` | a done trail entry with an Undo (D:1341) | undone ✓ (P1:158-167) |
| `hand.dial` | — | hand = place (D:1358) |
| `look.set` | — | look; appearance takes effect from the next start (D:1371) |

**Changes.** These go through Stacy's hand (SH:2006-2049, run_staged SH:2051-2101).

| Act → operation (scope) | Hers ask/show/free | Pre | Effect |
|---|---|---|---|
| `hand.write` → files.write (execute) | N(list) / Y / Y | path not reserved (D:1240) | Path free and Do and show or Free hand: file written, trail done, Undo `/files.trash` with a sha256 guard (P1:28-32; H:201-212). Path taken: waits at every place (D:1243-1248). Ask first: waits (P1:168-172). |
| `hand.rename` → files.rename | N / N / N | — | Always waits (not on H:39-42) |
| `hand.trash` → files.trash | N / Y / Y | — | Done with **no Undo** (P1:179-183; `takes_back` H:193-203). The way back, files.restore, is approve scope. |
| `hand.cell` → field.set | N / Y / Y | F; sel; sheet readable (FP:496-509) | Done with Undo `/field.set` + expected_revision (H:197-200), or refused "holds words" (P2:28-33) |
| `hand.step {n}` | the step's line decides: with no line, N/N/N "the step has no line to read" (A:329-335) | F; sel; n ≤ number offered (D:1279) | A read step runs even at Ask first and puts the steps page over the work (P2:39-43). A write is staged with `asked` set (FP:324). Several changes wait together (FP:313-317). |

## 2b. Live verification sample

Bench window, Do and show, pointer form. Each row gives the envelope, then what read.desk said before → after.

| # | Act | Envelope | read.desk before → after |
|---|---|---|---|
| 1 | `sheet.trace` off the Field | ok=False, NOT_HERE, changed [], 0.096 s | no change (P1:3-7) |
| 2 | `hand.write` 07 Bench readings.csv | ok, direct, changed [files.write]; ran / hers / undo `/files.trash …` | talk 1→2 cards, trail done + undo (P1:28-32) |
| 3 | `go.files {view: list}` | ok, pointer, 0.63 s | tab none → FilesTab; files ("", list, 4 names) (P1:33-37) |
| 4 | `menu.open` file | ok | popups [] → [menu]; target set; file selected (P1:38-42) |
| 5 | `menu.choose then` | ok | panel `@files:07 Bench readings.csv \| rows` / "4 rows · 6 steps left"; popups + panel (P1:43-47) |
| 6 | `then.keep unit / is mA` | ok, 0.78 s | panel `… \| where unit=mA` / "2 rows · 5 steps left" (P1:48-52) |
| 7 | `then.count` | ok | panel `… \| count`, preview [{count: 2}] (P1:63-67) |
| 8 | `then.end line` | ok, outcome ok | menu and panel closed; line.text = L; results 0→9 (P1:68-72) |
| 9 | `go.field` with head:Tools open | ok | workspace → field; sel = Bench; whole = T; **popups still [head:Tools]** (P1:88-92) |
| 10 | `sheet.compare` from Rev A | ok, 0.78 s | over none → revisions(A \| B) (P1:118-122) |
| 11 | `sheet.close` | ok | over → none (P1:128-132) |
| 12 | `hand.undo` (owner) | ok, changed [files.trash] | trail done → undone (P1:158-162) |
| 13 | `point.sheet` by pointer at 150% | NOT_HERE "out of sight; point.zoom with to=whole…" | no change (P2:149-158) |
| 14 | `menu.choose more/copy:path` on the Field's own menu | NOT_HERE | child none → "More": a partial effect (P3:81-90) |

## 3. P01 as a plan

I wrote P01's goals as four milestones and planned each with breadth-first search over the operators in section 2. Each plan starts from wherever the previous one left the desk, which is the receding-horizon scheme.

- **G1:** the Tools menu's rows were read (evidence).
- **G2:** the line `…07 Bench readings.csv | rows | where unit=mA | count` is in the writing line.
- **G3:** the trace of 07 Bench readings is shown (route owner = sel).
- **G4:** Rev A and Rev B of 07 Limits are shown side by side.

The derived plan is 13 acts, or **12 acts** once read.desk says `whole` is true after `go.field`. P01 has 17 steps. Because revisions persist across a selection move (P3:21-25) and a trace works under the comparison (P3:26-30), G3 and G4 can even hold together at the end: go.field, point.sheet Rev A, compare, point.sheet Bench, trace.

| P01 step | Act | Derived from the goals? |
|---|---|---|
| 1 | head.open Tools | It is the goal's achiever, but the goal itself is the model's choice |
| 2 | menu.close | Not a precondition: later acts work with the head menu open (P1:88-147). It comes from a standing rule, "leave no popup over the owner's window", which is worth having because popups are sticky. |
| 3 | hand.write CSV | **The model's choice.** The file's content can't be deduced, and the seed copy already satisfies the data need; the toy planner used `seed/` and wrote nothing. It is also a data change, hers at Do and show. |
| 4 | go.files | Derived: menu.open on a file needs Files in front (D:219-237). `view=list` is a free choice. |
| 5 | menu.open | Derived: menu.choose needs an open menu (D:981) |
| 6 | menu.choose then | Derived: then.keep needs the panel (D:400-405) |
| 7–8 | then.keep, then.count | Derived only if the goal is given as the line. From words like "how many mA readings", choosing the column and value is the model's question. |
| 9 | then.end line | Derived: it is the achiever of line.text = L |
| 10 | go.field | Derived: trace and compare need F (D:184-187) |
| 11 | point.zoom whole | Derived only while whole is unknown (pointer trace needs the sheet in sight). It was a no-op on this window (P1:93-97). |
| 12 | point.sheet Bench | Not needed: go.field already selects it (P1:92) |
| 13 | sheet.trace | The achiever of G3 |
| 14 | point.sheet Rev B | Derived, with a tie: Rev A works equally well (P1:113-122) |
| 15 | sheet.compare | The achiever of G4 |
| 16 | sheet.close | Not derivable: it deletes G4. It comes from a standing tidy goal. |
| 17 | hand.undo | Owner-only, so never in a plan of hers. It undoes step 3. The scene can run it only because `run` does not enforce OWNER_ONLY for `door='script'` (D:1425-1429; look.set and hand.dial also went through that door at P3:1-5 and P3:66-70). |

**Lesson for the conditions engine.** P01's goals are *milestones that need evidence*, not a final state. The route stops being shown as soon as the selection moves (FQ:1257). "Finish requires evidence for each agreed condition" should therefore record the envelope plus the read.desk tree at the moment each condition held.

The condition language already exists: a scene step's `expect` uses a path and a matcher (SC:35-69, SC:105-109). A desk goal could be that same `{path: matcher}` without the act, plus validity rules such as "route only while owner = sel".

## 4. Where her door plugs in, and what it needs

**Today.**
- `run` refuses `door='her'` at D:1425. It is tested at T:575 and seen live at P1:18-22.
- `desk_hers` (A:299-339) is written, but nothing calls it.
- `tools()` and `plan_variants()` export 35 acts (A:353-374, T:224).
- The owner's door is the line, console_qt.py:525-528. Scenes use `door='script'` (SC:124, SC:134).

**What her branch in `run` must do:**
1. **Refuse owner-only acts inside `run` itself** for `door='her'`. Today only `desk_hers` refuses them (A:311).
2. **Refuse arguments carrying `by`.** `desk_hers('show', 'go.field', {face: apps, by: keys})` returned True on this copy, because `check` accepts `by`. Run with `by=None`.
3. **Give `hand.step` its line.** Read it from `steps_for` (FP:277), which is a read with no showing. `field_page.do` cannot be used here: it puts a page over the work (FP:288). Without the line, `desk_hers` always says N.
4. **Handle Ask first.** An act that navigates is "offered" (HAND_RULE A:206) but no code does that yet. It needs a Talk card with the act's words that runs the act at the owner's word. Add a journal state OFFERED to `record` (D:1458-1460).
5. **Record why she staged a change.** The doers hard-code `asked=True` (D:663, FP:324, FP:517). Her door needs the provenance: the owner's request becomes `word`, and her own noticing is allowed at Free hand only (H:14-15).
6. **Give her her own journal origin.** Non-owner doors default to `desk-script:script` (D:1423). Add a turn id or correlation for her acts.
7. **Make the Kernel principal a decision.** `run_staged` dispatches with `operator()` (SH:2057-2058), the owner's identity (engineering_kernel.py:299). Only the journal origin says it was her. Whether her changes need a principal of their own is open.

**Seen.**
- Use one running Talk card per turn: each act's words, done / refused / waiting, and the read-back.
- The words already print no key and never name the line language (A:20-21, T:243-247). "Apps" is kept (D:721).
- Keep navigations in a **desk trail**, separate from `stacy_trail`. That trail keeps 40 entries (H:34), and P01 alone has 17 acts, so navigations would push data Undo lines out of reach.

**Stoppable.**
- Check a stop flag before each act in `run` and inside the press loops: `key` D:262-265, `type_text` D:268-276, `walk` D:474.
- Set it from a Stop on her card, and from any **spontaneous** owner input. The doers send synthetic events through `sendEvent`/QTest (D:248-276), which Qt marks non-spontaneous. Real mouse and keys are spontaneous, so the owner's touch takes the window back mid-plan.
- Plans should end each turn with `menu.close`, because popups are sticky (P2:169-173).
- `menu.choose` should be given the expected target, since it walks any open menu (D:979-983).

**Undoable where data changes.**
- Undo lines exist only for field.set and for files she made (UNDOES H:43, H:193-203).
- `hand.trash` is hers at Do and show with no Undo (P1:179-183). Either give it a `files.restore` Undo (approve scope, run by the owner's click), or keep trash asking until it has one.
- `hand.write` over an existing file already waits (D:1243-1248). `hand.rename` always asks.
- For the window itself, snapshot the abstract state at the start of the turn. "Put my window back" is then a plan from the current state to that snapshot, using the same planner (go.*, point.sheet, sheet.close, menu.close). The writing line is cleared only if its words are still hers (D:352-355).
- Keep the scene rule: an unexpected wait is a finding (SC:142-143).

**Additions to read.desk and doer fixes:**
- **Report the hidden state from 1b:** keyboard focus, whether the line's words are ours, the pending approval, the count of waiting cards, `came_from` (Today or not), per-sheet in sight, the Field's objects and links, and the current screen's rows with their state.
- **Make `route_said` follow the view's rule:** return None when the route's owner is not the selected sheet (FQ:1257).
- **Verify data changes by a Kernel read,** not by `changed`.
- **Fix the misleading reason at Ask first.** There `why_waits` says "it is not among the things I do by myself" (H:161-164; P1:168-172), when the real reason is the dial.
- **Decide how `hand.step` behaves at Ask first.** A read step is "hers" there yet still moves the window (P2:39-43).