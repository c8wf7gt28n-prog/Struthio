# Right-click redesign: the glyphs, and what the owner has asked for

The repository was only read. No Qt, window or checks were started; the only scripts run were `python3 -I` ast walks over `glyph_set.py` and `tool_faces.py` and one small contrast calculation.

## Part 1: Icons

### 1.1 The right-click does not use Graphite's glyphs today
- **Main menus and tool buttons** use `glyph_set` through `tool_faces`.
- **The right-click menu** (`ContextMenu(DeskMenu)`, context_menu.py:1922) draws icons from two other sets:
  - `programs_qt._icon_paths` (programs_qt.py:133-247), on an 18-unit grid with round caps.
  - Its own `EXTRA` set (context_menu.py:1732-1791): passage, bold, notes, line, run, pause, compare, extract, copy, trash, view, network, packet, event, new, rename, job, chain.
  - `paint_icon` picks between the two (context_menu.py:1794-1806).
  - Each row's icon is drawn in `TEXT` cream, or `QUIET` when the row is off (context_menu.py:1909-1910). The heading uses `TEXT` (1839). Size is 16 px (`ICON = 16`, programs_qt.py:30). It is not the neon green the main menus use, has no halo, and ignores the Buttons ▸ Words | Icons choice.
- **The chain builder** (`chain_menu.Chain`, a QMenu) uses a fourth set, `chain_icons`. Its colours are fixed to the old paper palette: `GRAPHITE '#504d46'` and `PINK '#cba5a4'` (chain_icons.py:7).
  - Graphite ink on the dark grounds measures **2.3:1** on #0b0e0d and **1.98:1** on Kasandra #171b3c, so those icons are barely visible.
  - Lines 21 and 10 there colour the endings pink.
- **The same idea is drawn three different ways:**
  - copy: glyph_set.py:253-256, context_menu.py:1765-1766, chain_icons.py:80-81
  - chain: glyph_set.py:362-364, context_menu.py:1785-1786, chain_icons.py:84-85
  - agenda: glyph_set.py:355-359, programs_qt.py:174, chain_icons.py:76-77
- **Icon keys used by the right-click today** (counted with grep over context_menu.py):

  | Key | Uses | Problem |
  |---|---|---|
  | `line` | 30 | Doubt it, Trace it, What can be done, Run its line and The brief all wear the same prompt icon (1404-1425), so the icons do not tell the verbs apart |
  | `explore` | 9 | A compass rose on Look again, Check the desk and Back (1354-1361) |
  | `ask` | 4 | Drawn by neither set, so it falls back to a generic window (programs_qt.py:245-246) |
  | `leave` | 4 | The log-out door is used for Export… (programs_qt.py:237) |

- **Two bugs:**
  - The chain builder's label is `'copy the line'` (chain_menu.py:147), but `chain_icons.name_for` looks up `'copy the stac'` (chain_icons.py:102). That row gets no icon.
  - The `icon()` docstring says "amber when its line is chosen" (tool_faces.py:197), but the code uses green (207-208). The docstring is out of date.

### 1.2 Every glyph in `GLYPHS` (glyph_set.py:394-410, 64 keys) and `KIND` (413-415, 14 keys)
House rules (glyph_set.py:6-16):
- One stroke weight, `WEIGHT 1.6` units (:21), with flat caps and sharp joins (:24-26).
- Arrow heads and folded corners are small solid "facets" (:36-38).
- A hexagon is drawn wherever another program would draw a circle (`HEX`, :182).
- Each glyph is drawn in a 20×20 unit box as `draw(p, ink, accent)`. The accent only fills a facet and never carries the meaning (:9).

| Key | Line | What it depicts |
|---|---|---|
| field | 52 | Two squares (one filled with the accent) joined by an elbow wire: the Field |
| find | 59 | A lens cut as a hexagon, with a thick handle |
| smaller / larger | 65 / 69 | Minus / plus |
| undo / redo | 73 / 79 | Arrow head pointing left at the top, and the turn it came back by / the same, mirrored |
| save | 82 | Floppy disk: cut corner, accent shutter, label panel |
| previous / next | 91 / 95 | Left / right chevron (weight 2.0) |
| cite | 98 | Two solid quotation wedges |
| table | 104 | 15×11 grid with an accent header row and two column rules |
| more | 109 | Three diamonds in a row (points of the lattice) |
| note | 114 | A slip with its corner turned up (accent) and two text lines |
| report | 123 | Σ, "the sum" |
| recalc | 128 | Two half-turns of a hexagon, each ending in a solid head (go round again) |
| export | 134 | An open tray with an arrow up and out |
| cell | 140 | A pencil (accent tip) and the baseline it writes on |
| source | 147 | Three lines, the middle one ending in a right-pointing head: "this row, and where it leads" |
| document | 155 | A page with a folded corner and a plus |
| again | 162 | Two side-by-side sources (left one accent) with a double-headed arrow under them |
| pin | 169 | A push-pin: "this stays open" |
| stop | 176 | A solid square |
| page | 185 | A page with a folded corner and two lines (a source) |
| found | 192 | A hexagon with a tick (a finding) |
| asked | 198 | A question mark with a diamond dot |
| limit | 204 | "≤": a chevron over a rule ("no more than this") |
| steps | 209 | A staircase rising right, accent wedge at the top (a method) |
| running | 215 | A hexagon with a solid play triangle (a job at work) |
| folder | 221 | A folder with an accent tab |
| port | 226 | A socket with two prongs and a lead (an interface) |
| window | 231 | A window with an accent title bar and a small play mark (a running program) |
| reach | 238 | A line whose head stops against a far wall (an endpoint) |
| rooms | 244 | A 2×2 of squares, one lit (a program Graphite can open) |
| copy | 253 | An accent front sheet with an outlined sheet behind it |
| paste | 259 | A clipboard with two lines and a solid clip |
| cut | 265 | Scissors: crossed blades, diamond handles |
| select | 271 | A corner-bracket marquee around an accent square (select all) |
| full | 279 | Four L-corners (full screen) |
| home | 286 | A house with an accent door |
| sliders | 292 | Three rules with solid knobs (settings) |
| prompt | 299 | `>` and an underscore cursor (the terminal) |
| lines | 304 | Three ragged lines (a log) |
| info | 309 | A hexagon with an "i" |
| close | 315 | X |
| receive | 319 | A tray with an arrow down into it |
| chip | 325 | A chip with an accent core and pins on each side |
| book | 333 | An open book |
| key | 338 | A keycap |
| stack | 344 | Three rhombus layers, the top one accent (the library) |
| delta | 350 | A Δ outline ("what changed") |
| agenda | 355 | A checklist, first box filled (done) |
| chain | 362 | Two overlapping rectangular links |
| star | 367 | A four-pointed star, accent fill ("a favourite; what is new") |
| split | 373 | A rectangle split down the middle |
| picture | 378 | A framed landscape with an accent sun |
| bold, italic, underline, h1, h2, h3, body, code, plain | 384-409 | Letter glyphs made by `letters()`: B, *I*, U̲, H1, H2, H3, ¶, `{}` in Mono, Aa |

`KIND` (glyph_set.py:413-415):
- source→page, folder→folder, sheet→table, method→steps, calculation→report, job→running
- document→cell, finding→found, question→asked, condition→limit
- interface→port, program→window, endpoint→reach, app→rooms

Only 44 drawn glyphs are not letters or kind glyphs. `letters()` (:384-391) can make more type glyphs cheaply, such as `#` or `Σ`.

### 1.3 How `tool_faces.icon(key)` draws a glyph for a menu (tool_faces.py:196-220)
- **Lookup:** `GLYPHS.get(key) or KIND.get(key)` (:202), so kind names such as `'job'` or `'sheet'` also work as keys. An unknown key returns an empty `QIcon`.
- **Cache:** keyed by `(key, t.glow())` (:198), so the halo follows the glow dial. The appearance is not part of the key. That is safe because the appearance is fixed for the whole process (boss_theme.py:23-26, 95).
- **Sizes:** `SIDE = 20` px (:29). Each state is painted at device ratio 1 and 2 (20×20 and 40×40 px, :209-219), scaled `SIDE*ratio/20`.
- **Colours by state** (:207-208), from boss_theme.py:30-52:

  | QIcon state | Stroke (ink) | Fill (accent) | Halo strength | Graphite | Kasandra |
  |---|---|---|---|---|---|
  | Normal | `READY` | `TEAL_EDGE` | 0.10 | #c3ed74 / #789654 | #83eaff / #5a8fc4 |
  | Active and Selected | `TEAL_TEXT` | `READY` | 0.18 | #cbf08b / #c3ed74 | #b9f4ff / #83eaff |
  | Disabled | `LINE_MID` | `LINE` | none | #6b6550 / #474436 | #5969a1 / #3b4479 |

- **Halo** (:213-216): the glyph is drawn four times in `READY` at offsets of ±1 unit (1 px at ratio 1, 2 px at ratio 2), with alpha `min(0.32, lit*level/1.9)`. Glow levels are Soft 1.0, Bright 1.9 and Neon 3.0; Neon is the default (boss_theme.py:107-108). At Neon that gives about 0.16 at rest and 0.28 under the pointer.
- This is the 0.5.2 "neon green" look: green even at rest. A tool **button** is different (`paint`, :107-111): `TEXT` ink with a `FAINT` accent at rest, green only under the pointer, amber when pressed or chosen, and a full 8-direction halo (:125-130).
- `tool_faces.icon` is also used for Kasandra's column marks, `select` beside This and `running` beside Now, at 17 px × scale (shell2.py:1741-1755).

### 1.4 How `tool_faces.dress(menu)` attaches glyphs (tool_faces.py:228-254)
- **Mode:** follows the Buttons choice (`STATE['mode'] == 'icons'`). A workspace that has never chosen opens with icons (`OPENS_WITH`, :31).
- **Icon column:** dress sets the menu property `glyphs` and re-polishes the menu (:234-235). The theme's style sheet then reserves the column with `QMenu[glyphs="true"]::item {padding-left:44px}` and `::icon {left:13px}` (boss_theme.py:181-182).
- **Per line, on every open:**
  1. Hides the shortcut and cuts any `\t…` and `&` mnemonic out of the words (:240-242).
  2. Hooks each submenu so it is dressed when it opens, once (:243-245).
  3. Looks up `FOR_MENU[named(text)]`, where `named` drops `&`, everything after a tab and trailing `….` (:223-225).
  4. Keeps the line's old icon the first time (`iconBefore`, :248-249), then sets `icon(key)` and `setIconVisibleInMenu(True)` (:250-251). With Words chosen it puts the old icon back (:252-254).
- **The lookup is by exact words.** `FOR_MENU` (:176-192) has 69 entries over 45 glyphs. Examples: Open→folder, Copy→copy, Undo→undo, Export (Egress)→export, Import (Ingress)→receive, Inquiries and Assistant→asked, Run an operation→running, Chain Menu and Constructed chain→chain, Writing Line→cell, Console, Terminal and Command Palette→prompt, Inspector→info, Changes→delta, Graphite's Agenda→agenda, Favorite commands→star, Refresh Machine View and Replace→recalc.
- One glyph already stands for loosely related things: `recalc` = Replace and Refresh; `undo` = Undo, Recover Unsaved Work and Reset Window Layout (:179-187).
- Because the match is exact, right-click words like "Copy path" or "Copy the address" would not match. The right-click should look up by `Entry.key` (context_menu.py:110-118: `'copy:path'`, `'run'`, `'ask'`, `'trash'`, `'compare:with'`…) using the part before the `:`.
- `FOR_WORDS` and `BARE` (:35-47) serve the tool buttons; `wear(button, key=, tone='live')` (:163-170) is how a button names its own glyph.
- **Where dress is hooked:** the head menus (shell2.py:661-666) and Stacy's hand menu (shell2.py:2141-2145). Not the right-click (a DeskMenu that paints its own icons) and not the chain builder (`chain_icons.dress`, chain_menu.py:149-150, 482-483).

### 1.5 Why the main menus hide icons (menus2.py)
- The module docstring still says "Menus are words, with no pictures: the one mark kept is a graphite dot beside Master Stop. (paper_icon remains for any place that must show an icon…)" (menus2.py:7-8). This rule dates from before 0.5.1.
- `rebuild()` ends by calling `setIconVisibleInMenu(action is stop)` on **every** QAction in the window; only Master Stop gets `dot()` (menus2.py:281-285, `dot` :51-54).
- It then turns every button that still carries a picture into a single graphite-coloured shape, `paper_icon` (#6c675e, menus2.py:14, 39-48), unless the button has the property `paperIcon` or is the Master Stop button (:286-289).
- The glyphs come back only because `dress()` runs on `aboutToShow` and turns visibility back on for lines in `FOR_MENU` (tool_faces.py:250-251). Two mechanisms are working against each other, and the result depends on dress running after rebuild.
- Shortcut text is suppressed for every QMenu at app level (`AA_DontShowShortcutsInContextMenus`, tool_faces.py:261-263). The right-click's DeskMenu **does not use that path** (see 2.4 a).

### 1.6 Which glyph for each right-click verb

| Verb | Glyph | Why (precedent) | Fit |
|---|---|---|---|
| open | the target's own `KIND` glyph (page for a file, folder for a folder, a sheet's kind in the Field); `window` for "Open with this computer's app"; `rooms` for "Open in *its program*" | KIND glyph_set.py:413; window :231 "a program that is running"; rooms :244, FOR_MENU 'Explore capabilities' | Good. Avoid `folder` for a file even though main-menu Open→folder (tool_faces.py:177) |
| show (where it is: in its folder, in Files, in Log, the process) | `source` | "This row, and where it leads" :147; FOR_MENU Go to Line, FOR_WORDS Open source row | Good; keeps show distinct from open |
| ask | `asked` | :198; FOR_MENU Assistant and Inquiries (tool_faces.py:182, 191) | Exact. Replaces the broken `'ask'` (falls back to window) and `inquiries` |
| change (edit, rename) | `cell` | pencil on its line :140; FOR_WORDS Edit cell; FOR_MENU Writing Line | Exact |
| copy | `copy` | :253 | Exact |
| compare | `again` | :162; "Compare sources again" | Exact (`split` :373 as a second choice) |
| trace | **none that fits.** `field` (:52, two sheets and a wire) is the right idea but is already the Field's own glyph ('‹ Field', 'Field', tool_faces.py:36, 183); `source` only points one way | | **Missing** |
| keep (a line or chain as your own word, a favourite) | `star` | :367; FOR_MENU Favorite commands | Fair. `pin` (:169) for "keep open"; `note` for "Move to notes"; no bookmark exists |
| export | `export` | :134; FOR_WORDS Export…, FOR_MENU Export (Egress) | Exact. Today the right-click uses programs_qt `leave`, the log-out door |
| run | `running` | :215; FOR_MENU Run an operation; KIND job | Exact. Draw in the **line** tone (below) |
| pipe / next step | `chain` for "Chain from here" or "add a step"; `next` (:95) for the "then ›" endings | FOR_MENU Chain Menu and Constructed chain | Exact |
| filter | **partial:** `limit` (:204, ≤) fits over / under / at most, not a filter in general; `find` means search | | **Missing** a funnel (chain_icons.py:43-44 has one in the wrong style) |
| count | **none.** `report` is Σ, a sum (:123) | | **Missing**; `letters('#')` (:384) would be cheap |
| sort | **none** | | **Missing** (could be two facet heads, up and down, in undo's facet style :73-76) |
| group | **none.** `stack` is the Library; `folder` would mislead | | **Missing** |
| save as sheet | `table` | :104; KIND sheet; FOR_WORDS Review table | Good. Not `save`, which means "save this file" |
| watch | **none.** The eyes are `EXTRA 'view'` (context_menu.py:1769) and `chain_icons 'watch'` (74-75), other sets; `find` is a lens meaning Find | | **Missing** (straight-stroke lids with a diamond pupil, so it is not confused with find's hexagon) |
| add to agenda | `agenda` | :355; FOR_MENU Graphite's Agenda | Exact |
| undo | `undo` | :73 | Exact. Only `field.set` and `files.trash` have Undo lines today (stacy_hand.py:43) |
| inspect | `prompt` for "Inspect in the line" (the same picture as the right-click's current `line` icon, context_menu.py:1755); `info` for explain, about or properties | :299; FOR_MENU Console and Terminal; :309 FOR_MENU Inspector | Exact |

Other right-click verbs worth fixing at the same time:
- Have a glyph: Refresh / Look again → `recalc`; New Idea → `note`; New document → `document`; New folder or project → `folder`; Import / Receive files → `receive`; Versions / What if → `delta`; View as → `sliders`; Tool Atlas → `book`; Explore → `rooms`; Search / Investigate → `find`; Stop → `stop`; Resume → `running`; Follow this conversation → `reach`; Show the process → `window`; Cut / Paste / Select all → `cut` / `paste` / `select`; the text styles → the letter glyphs.
- **Missing:** Move to Trash (only `EXTRA 'trash'` exists, context_menu.py:1767) and Pause (`stop` is a solid square; only `EXTRA 'pause'`, :1759).

**Missing glyphs, in short:** trace, filter (`limit` is partial), count, sort, group, watch, plus trash and pause. Draw them in the house rules (glyph_set.py:6-9) and add them to `GLYPHS`.

Rendering notes for the redesign:
- **Size:** paint rows with `tool_faces.icon(key).pixmap(m.icon)`, or with the scaled draw in `field_qt._glyph` (field_qt.py:1300-1304). The right-click's icon is 16 px (programs_qt.py:30) and the glyphs were designed for 20 px (glyph_set.py:9; `SIDE`). Row height is `max(line, icon)+2·ROW_PAD` (programs_qt.py:53), so 20 px costs almost nothing. `DeskMenu` metrics are shared with Programs, though, so the change should be made only for the right-click.
- **The line tone:** rows that run or show a line (Run, Inspect in the line, the chain's "then", the chain header) should be drawn in the ROYAL tokens. In Kasandra that is ink `ROYAL_TEXT` #b9a1f6 and fill `ROYAL` #7b4fd8 (boss_theme.py:51). In Graphite the ROYAL tokens already equal `TEAL_TEXT` #cbf08b (:40), so nothing changes there. `icon()` has no tone parameter today; one is needed, and the cache key (:198) would need the tone too.
- **Words | Icons:** decide whether the right-click follows this choice. Today the right-click always shows icons, and dress takes them away under Words (tool_faces.py:252-254). The owner said "With right click icons too", and new workspaces open on Icons (:31).

## Part 2: What the owner has asked for on the right-click and menus

### 2.1 Asked for, in the owner's words, and what was promised
- **A powerful pipe menu, built for what is under the pointer** (2026-11-06):
  - "I want a quieter, symmetrical desk with a powerful Fluxbox-inspired right-click menu. Keep every useful capability reachable and put it where I would naturally look for it." (GRAPHITE_DESK.md:3-4)
  - "Make the right-click menu a defining capability of Graphite. Take the Fluxbox pipe-menu idea seriously. When I right-click, build the menu for the thing under the pointer, the current selection, and what is possible in that workspace. I want to reach an action while my attention is still on the work." (GRAPHITE_DESK.md:803-805; context_menu.py:1-3)
  - "Give these actions the same command, tool, and permission checks used elsewhere… Keep target and revision information attached to actions that change work. Show the resulting edit, tool output, or job state where it belongs." (GRAPHITE_DESK.md:805-807)
- **Cascading menus that build chains:**
  - Owner decision: "Programs entries and dropdown menu commands participate in contextual cascading actions, alongside work objects." (BOSS_IMPLEMENTATION_PLAN.md:10)
  - P03 is complete only when "Menus remain within the display and have predictable Escape, focus, and continuation behavior." (:48)
  - Recorded as built: "cascading menus that build staC chains" (RECORD_OF_DIRECTIONS.md:270).
  - The builder: "right-click builds a staC pipeline, one link per menu, Fluxbox-style… Every item says what it would give ("2 rows"): a pipeline only reads, so the menu can look before you choose." Chains are kept in an editable menu file, and every submenu can be torn off (chain_menu.py:1-19).
- **The Field sheet's menu, then cascades:**
  - 0.3: "Open, What feeds it, What it feeds, Inspect in the line, Run its staC, Ask Graphite about this, Copy its name" (RELEASE_NOTES_0.3.md:28-30).
  - 0.4.3, "The right-click menu cascades into all of it": What if ›, Doubt it ›, Trace it ›, What can be done ›, Your words ›; "Choosing in a menu never approves anything" (RELEASE_NOTES_0.4.3.md:68-81; DAILY_GUIDE.md:38-40; context_menu.py:1269).
  - "The same action should be reachable from the sheet, the right-click menu, the keyboard, a typed staC line and the assistant." (RECORD_OF_DIRECTIONS.md:109-110)
- **Mouse first, keys still work:**
  - "The mouse, keys and Stacy use the same target and operation"; someone should "sit down with a mouse and do the ordinary work by looking at the screen" (RECORD_OF_DIRECTIONS.md:57-60).
  - "now that we're using mouse as primary input" (RECORD_OF_DIRECTIONS.md:223-226).
  - The right button selects the tile and shows its menu (RELEASE_NOTES_0.4.5.md:14-15).
  - The keyboard keeps the Menu key and Shift+F10 (context_menu.py:2251-2259) and Right/Enter/Left/Escape in cascades (GRAPHITE_DESK.md:858-859).
- **One home for each action:**
  - "Really question what everything does and if it's place is justified. Every click necessary. No redoing the same thing multiple places" (RECORD_OF_DIRECTIONS.md:139-140).
  - The rule that came from it: "Its key is the second road. The right button on a thing is that thing's own road. A name is said once." (RELEASE_NOTES_0.4.9.md:14-15; RECORD_OF_DIRECTIONS.md:140-141)
  - Both the Field foot and the right button were kept for sheets (RELEASE_NOTES_0.4.9.md:111-114).
- **No white boxes:** "No ugly white boxes that stand out like a sore thumb"; controls are dark plates with quiet edges; the menu's edge was part of that cleanup (RECORD_OF_DIRECTIONS.md:144-146; RELEASE_NOTES_0.4.9.md:52-63).
- **Apple-simple at rest:**
  - "Think apple simplicity but still very powerful" (RELEASE_NOTES_0.5.0.md:10-11).
  - The rule: "At rest the window shows names and pictures, and the machinery is one move away… **Nothing is removed to make it simple: it stops being the first thing seen.**" (RECORD_OF_DIRECTIONS.md:210-213)
  - The menus moved to the head "kind of like Apple does" (RELEASE_NOTES_0.5.1.md:12-14).
- **Icons:**
  - "Or graphite themed icons can be tried as an option also" (RELEASE_NOTES_0.4.9.md:76).
  - "I love your icons. I wish we had more icons." Menu lines got glyphs (RELEASE_NOTES_0.5.1.md:43-49).
  - "the icons in the drop down menus could be neon green" (RELEASE_NOTES_0.5.2.md:27-31).
  - "maybe icons in kasandra column if they look good and kool" (RELEASE_NOTES_0.8.0.md:61-66).
- **No keys printed:** "We don't need to display keyboard shortcuts anywhere ... keep it sleek and tidy"; menus have "no column of keys… no key written into a line" (RELEASE_NOTES_0.5.2.md:10-23; RECORD_OF_DIRECTIONS.md:149-151). In 0.8.0, "Ctrl Z takes it back" after a right-click change was said to be gone (RELEASE_NOTES_0.8.0.md:158-162).
- **"A line is a line" and royal purple:**
  - The language is never named on screen (RECORD_OF_DIRECTIONS.md:34-37; RELEASE_NOTES_0.8.0.md:107-114).
  - "royal purple is the line" (RELEASE_NOTES_0.8.0.md:80-84; boss_theme.line_sheet :66-69).
- **Less scrolling:** "I know sometimes scrolling is unavoidable, but if we can really try to eliminate or reduce it as much as possible." (RELEASE_NOTES_0.8.0.md:86-88)

### 2.2 What the docs promise the right-click does today
- **Sections**, in this order: open and show · change it · its state · as a line · capabilities · the tree · edit and copy · remove (context_menu.py:51-53; GRAPHITE_DESK.md:850-851).
- **The heading** names the target: icon, name, and what it is (GRAPHITE_DESK.md:853-857).
- **Submenus** open after a 240 ms rest (context_menu.py:55).
- **Changes** carry the revision seen at the right-click and are refused if the thing moved (GRAPHITE_DESK.md:862-877).
- **Run and Inspect** never claim they ran when they did not (GRAPHITE_DESK.md:889-897, 984-985).
- **Nothing lost:** every entry of the old menus is listed in `FOLDED` (GRAPHITE_DESK.md:933-951). The test accepts keys found anywhere in the menu tree, submenus included (tests_integrated/test_context_menu.py:594-629). One check is pinned to a path, `'root/menu:edit'` (:621).
- **The daily guide** promises the sections in plain words (DAILY_GUIDE.md:119-131).

### 2.3 What works against "make it simple"
1. **Too many rows.**
   - A single file shows **24 rows in six groups**, plus four more on a working copy (GRAPHITE_DESK.md:908).
   - A passage shows 18 rows, 7 of them text edits the head menu already has (:906; context_menu.py:417-423).
   - The empty place of a folder nests the whole root menu as "Root menu ›" (GRAPHITE_DESK.md:911).
   - "Nothing removed" (RECORD_OF_DIRECTIONS.md:213) and the FOLDED test mean simplifying has to be done **by layering**, a short top level with the rest one cascade down, not by deleting. The test allows this, except for the pinned `root/menu:edit` path.
2. **Keys are still printed in the right-click**, against the 0.5.2 rule and the 0.8.0 claim.
   - `caption=` shows Ctrl B/I/U (context_menu.py:387), Ctrl 1/2/3/0/\` (393), Ctrl Z/Y/X/C/V/A (417-423), Space (750) and Ctrl Shift N (829).
   - In the Field: X, T, R, C, Esc, B, Enter, S, Shift+Enter, D (1290, 1310, 1354-1361, 1379, 1395, 1404-1425).
   - The design itself defines a caption as "a key, a status, a far address" (GRAPHITE_DESK.md:847-848; context_menu.py:110).
   - The DeskMenu paints captions itself (programs_qt.py:369-370), so the app-wide QMenu shortcut suppression (tool_faces.py:263) never reaches it.
3. **Two menus with two looks for one job.** The right-click is a DeskMenu with cream 16 px icons. The chain builder it opens is a QMenu with tear-offs and the paper-palette `chain_icons` (GRAPHITE_DESK.md:957-959; chain_menu.py:81-105).
4. **The chain builder shows the line's own keywords as menu words** instead of plain verbs: rows, headings, layers, texts, lines, facts, where, group by, take, join with, missing on, then (chain_menu.py:33; chain_icons.py:98-106). Extract › does the same with lens names (context_menu.py:549-552). This does not name the language, but it is not the "a line" plain speech of 0.8.0.
5. **Menus can run past the screen and scroll.**
   - The right-click is limited to the window's height, and anything taller **scrolls** (context_menu.py:2004, 2019; DeskMenu's scroll area, programs_qt.py:445-447).
   - The chain builder adds one cascade level per link, offers up to 8 values per column (chain_menu.py:36) and lists up to 30 files under "start from" (:472). Deep cascades step sideways across a 1366 px screen.
   - Both work against "Menus remain within the display" (BOSS_IMPLEMENTATION_PLAN.md:48) and the 0.8.0 scrolling request.
6. **Icons do not tell verbs apart.** 30 rows share `line`; the compass rose is used for Look again, Check and Back; `ask` falls back to a window (see 1.1). This works against "one idea per glyph" (glyph_set.py:9).
7. **Duplicated roads on the empty place.** The root menu on every empty place repeats Commands ▸ Chain Menu and Work ▸ New Idea / New Project / Import (GRAPHITE_DESK.md:915-916, 924). 0.4.9 allows the right button as a second road (RELEASE_NOTES_0.4.9.md:14), but the empty place's root is a third road to the same chain menu.
8. **Out-of-date names:**
   - menus2's docstring "Menus are words, with no pictures" (menus2.py:7) contradicts 0.5.1 and later.
   - context_menu's docstring still names "the System menu's process list" (context_menu.py:9-10), but the System menu has been gone since 0.7.0 (RELEASE_NOTES_0.7.0.md:6).