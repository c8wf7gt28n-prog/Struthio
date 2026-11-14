# Progressive right-click: four things, then the line

Designer 3 of 3. The angle is progressive disclosure and teaching. I only read the repository and nothing in it was edited. I did not start Qt, the window, any check or any probe.

One scratch script checks both worked examples against the real line parser, using `typed_pipeline.py` and `addresses.py` loaded by file path, and the copy of After Hours 07's records already in scratch, read-only: `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/rightclick/progressive/worked.py`. Every row count in section 2 is that script's output. Every pixel height is an estimate from the size constants in `programs_qt.py:30-38`, not a measurement.

**Abbreviations used in citations:**
- cm = `workbench/context_menu.py`
- chm = `workbench/chain_menu.py`
- cc = `workbench/command_context.py`
- pq = `workbench/programs_qt.py`
- tf = `workbench/tool_faces.py`
- gs = `workbench/glyph_set.py`
- bt = `workbench/boss_theme.py`
- sh = `workbench/stacy_hand.py`
- s2 = `workbench/shell2.py`
- tp = `sdk/cli/arc1cli/typed_pipeline.py`
- sl = `workbench/stacy_language.py`
- cw = `workbench/chain_workbench_qt.py`

---

## 0. In one screen

- **At rest, every menu has the same shape and is short.** The heading names the thing. Below it are its **4 usual actions**, plus at most **1 learned action** and at most **2 chains you kept for this kind of thing**. Then come **And then…** (the line) and **More ›**. A fresh workspace shows **6 rows** for a file (today: 25, cm:596-664), at about 271 px against about 725 px today.
- **More ›** opens everything else, grouped by verb, one level down. At last the group words appear: `SECTION_WORDS` exists (cm:52-53) but is never read.
- **The foot teaches the line.** Under the rows, the menu's foot shows the line the row under the pointer or keyboard would run. In Kasandra it sits on the royal slab (`bt.line_sheet()`, bt:66-69); in Graphite it is shown in green letters, as `bt.line_sheet()` gives. Under the line, one quiet sentence says what the hand will do:
  - "reads only · nothing changes"
  - "Undo takes it back"
  - "asks first: what it stops cannot be put back"

  With nothing pointed at, the foot shows the line that reads the thing itself. That is how people learn the line: by using the menu.
- **And then… builds the chain in one panel, in place.** You don't open 8 popups side by side. Each choice appends a step, and the panel redraws with:
  - the longer line,
  - a 3-row preview,
  - an exact count on every offer,
  - how many steps are left,
  - and the endings.

  Each step costs **one** Kernel read. Today a single numeric "where" costs up to 32 synchronous reads (chm:208-216).
- **Every row wears one of Graphite's own glyphs** (gs:394-410), drawn by `tool_faces` in the theme's colours. Rows that run or show a line use the royal tone. 8 new glyphs are needed.
- **No row prints a key.** That removes 31 captions at 24 call sites (cm:388-423, 750, 829, 1290, 1310, 1354-1425), the "Shortcut:" line (cc:125) and the key words in tooltips.
- **Every change goes through the hand.** It runs through `SlateFace.stage(…, asked=True)` (s2:1991-2030) and gets a card, a trail line and an Undo where there is one. Stop on a job or Agenda work (cm:974, cm:1045) and the shell endings (chm:299) stop being one click and always ask (sh:52, sh:56).

---

## 1. The design

### 1.1 One shape for every menu

```
┌──────────────────────────────────────────────────────────┐
│ [table] 07 Bench readings              reviewed sheet ·… │  heading: the thing, named before you act (kept)
├──────────────────────────────────────────────────────────┤
│ [undo]  Undo: saved “mA count”                           │  only for 10 min after a change made from a menu
├──────────────────────────────────────────────────────────┤
│ [table] Open                                             │  ┐
│ [steps] What can be done                               › │  │ the 4 usual (fixed per kind)
│ [found] Doubt it                                       › │  │
│ [asked] Ask Stacy about this                             │  ┘
│ [sort]  Sort by value (yours)                            │  1 learned (only when earned)
├──────────────────────────────────────────────────────────┤
│ [pin]   ma count                                         │  ≤ 2 chains kept for this kind, in this project
├──────────────────────────────────────────────────────────┤
│ [chain] And then…                                      › │  royal tone: the line
│ [more]  More                                           › │
├──────────────────────────────────────────────────────────┤
│ ▌@office:owner:db5f66… | pick origin.reviewed_rows | se… │  the foot: the line (slab), 2 lines at most
│  reads only · nothing changes                            │  what the hand does with it
└──────────────────────────────────────────────────────────┘
```

**Rules:**

1. **The heading stays** (cm:1809-1876). It loses "revision N" in its noun (cm:306, 309). The revision is in the line, in the foot, when it matters.
2. **The 4 usual actions come from a fixed preference list per kind.** The first 4 keys present for this target are shown. If a key is absent (a folder has no Ask) or can never apply here (a caret has nothing to Cut), the next preference fills its slot. Of a twin pair (Pause/Resume), only the one the Kernel would take is shown.
3. **One learned slot.** It holds the More key chosen most often on this kind of thing in this project, once it has been chosen **3 times or more** (ties: the most recent). It is added as row 5 and never replaces or reorders the four. It changes only between openings.
4. **Kept chains:** up to 2, the most used first, below a hairline. The rest are in More › "Kept for <kind> ›".
5. **And then…** appears when the thing has a line that reads it. On an empty place the same row reads **Start from ›**. Several selected files have none: a line reads one source. In that case the foot says "A line reads one thing at a time: right-click one of them to start one."
6. **More ›** is the rest, grouped by verb (§1.6). It has no More row when nothing is left (a Library file, a Programs row).
7. **The undo row** shows only while a change made from a right-click still has a valid Undo, for 10 minutes. It uses the trail entry and its guard (sh:241-249, s2:2111-2129).
8. **What is no longer printed:**
   - The word "unavailable" (cm:1883). A greyed row shows its reason in the foot and as its tooltip.
   - Tooltip lines "Through Kernel.dispatch: <op>" (cm:123). The foot shows the line instead.
   - Every key caption.
   - Captions that remain are statuses only: "asks", a count, a process name, an address.

### 1.2 How the first level is chosen

- **Defaults are a table**, `menu_rest.REST[kind]`, listed per target in §1.6.
- **Use is counted per project and per kind.** In `perform` (cm:2143), every chosen key adds `[n, last]` to `session.state['menu_use'][kind][key]`.
  - The session is per project: a different project starts clean (`session.py:105-106`). So "learned in this project" comes for free.
  - It needs one validated field in `Session.load`, the way `stacy_trail` is cleaned (`session.py:122-124`). Caps: 40 kinds × 60 keys.
- **Kept chains are words** in the workspace's Kernel (the `stac_words` table, `stac_words.py:43`), so they are per project too. They gain one column, `for_kind`, and a new lead word, `these` (§2.4).
- **One reset:** More › "This menu › Back to the usual lines" clears `menu_use[kind]`. It only shows when the learned slot is filled.

### 1.3 The foot: the line under every action

- **The widget.** `LineFoot` replaces the script caption "what you can do right here" (cm:54, 1943). It is a `QLabel` styled with `bt.line_sheet()`, as s2:2017 already does, plus one quiet `QLabel` underneath.
  - Its height is fixed (2 mono lines plus 1 quiet line, about 73 px with its rule), so the menu never jumps.
  - Long record numbers are cut with `bt.eye()` (bt:72-74). The whole line is in its tooltip and accessible name.
- **What it shows:**
  - **At rest:** the line And then… would start from (§2), or for a thing with no line, the quiet words "Point at a row to see what it runs".
  - **On hover or keyboard focus of a row:** `entry.line`.
    - A read shows its read line.
    - A change shows the operation line, e.g. `/files.rename {"path": "notes.csv", "name": "…"}`, where "…" marks what you will be asked for.
    - A navigation row has no slab, only words: "Opens its page in the Office · nothing runs".
  - **The quiet sentence** comes from `stacy_hand`: `why_asks` (sh:141-147), `hers` (sh:150-158), `takes_back` (sh:193-203). See §1.5.
- **Explaining a row.** Right-clicking a row of the right-click menu, or pressing F1 on it (pq:559), **pins** the foot to that row. Today a second right-click rebuilds a meta-menu and closes the one you were in (cc:53-57, cm:2158-2161).

### 1.4 Glyphs

- **Drawing.** Rows are painted, not QActions (pq:265), so a row paints its glyph itself through a new `tool_faces.paint_glyph(p, rect, key, state, tone)`. It shares `tf.icon`'s cache, extended with `tone` (tf:198).
  - Because rows never call `setIcon`, `menus2.rebuild`'s `setIconVisibleInMenu` / `paper_icon` pass (menus2.py:281-289) cannot reach them. Rows also set `paperIcon` as a belt.
- **Colours,** the same as the head menus so the two menus match (tf:207-208):
  - at rest `READY` ink with `TEAL_EDGE` accent;
  - under the pointer `TEAL_TEXT` with a halo;
  - unavailable `LINE_MID`.
- **Line tone** (`tone='line'`): ink `ROYAL_TEXT`, accent `ROYAL`.
  - In Kasandra that is #b9a1f6 on #7b4fd8 (bt:51).
  - In Graphite the ROYAL tokens already equal `TEAL_TEXT` (bt:40), so nothing changes there.
  - Used by: And then…, Start from, kept chains, Run its line, In the line, Copy the line, and the step panel's heading.
- **Size:** 20 px, the size the glyphs were drawn for (gs:9, tf:29). Only the right-click gets this metric; the Programs list keeps 16 (pq:31). At 14 pt the row stays 24 px, because `max(line≈20, 20)+4` = 24 (pq:45-56).
- **What is retired:** cm's `EXTRA`/`_extra_paths`/`paint_icon` (cm:1732-1806) and, with the old builder, `chain_icons`. The latter has fixed #504d46/#cba5a4 colours (chain_icons.py:7) and the dead lookup "copy the stac" (chain_icons.py:102).
- **Words | Icons.** The right-click always shows glyphs. It has always had an icon column (cm:1910), and the owner asked "with right click icons too". This is open decision D3.

**Verb → glyph** (all in `GLYPHS`/`KIND`, gs:394-415, except the 8 marked *new*):

| Verb | Glyph |
|---|---|
| Open | the thing's own kind glyph (`table`, `page`, `folder`, `cell`, `running`…; `KIND`, gs:413) |
| Open with this computer's app | `window` |
| Open in a program | `rooms` |
| Show (in its folder, in Files, in Jobs, the original) | `source` |
| Ask | `asked` |
| Rename / change | `cell` |
| Copy (clipboard), Copy to… | `copy` |
| Move to… | `reach` |
| Versions, What if | `delta` |
| Compare | `again` |
| Export | `export` |
| Import / Receive / Keep a copy | `receive` |
| Stage in Delivery | `stack` |
| Add to the Agenda | `agenda` |
| Explain, What it does | `info` |
| Search / Investigate / New smart folder | `find` |
| Atlases | `book` |
| Explore | `rooms` |
| New idea / Move to notes / The brief | `note` |
| New folder / New project | `folder` |
| New document | `document` |
| View as / settings / toggles | `sliders` |
| Refresh / Look again / Again | `recalc` |
| Expand / Collapse | `larger` / `smaller` |
| Bold, Italic, Underline, Plain, styles | the letter glyphs (gs:405-409) |
| Undo, Redo, Cut, Paste, Select all, Delete | `undo`, `redo`, `cut`, `paste`, `select`, `close` |
| Run its line / Resume / Its job | `running` (line tone for Run) |
| In the line | `prompt` (line tone) |
| And then… / Start from | `chain` (line tone) |
| More | `more` |
| Kept chain / Keep for… / Your words | `pin` |
| What can be done | `steps` |
| Doubt it, Check the desk, provider checks | `found` |
| What feeds it / What it feeds / Back | `previous` / `next` / `previous` |
| Show the network / Join with | `port` |
| Follow this conversation | `reach` |
| Show the process | `window` |
| Show its output / Show the rows / Show in Log | `lines` |
| Save as a sheet | `table` |
| First N | `limit` |
| Add a column | `larger` |
| Keep columns | `select` |
| Stop | `stop` |
| Move to Trash / Discard this draft | *new* `trash` |
| Pause | *new* `pause` |
| Only rows where | *new* `filter` |
| Sort by | *new* `sort` |
| Count | *new* `count` (`letters('#')`, gs:384) |
| Count by / Total by | *new* `group` |
| Watch it | *new* `watch` |
| Trace it | *new* `trace` |

**The 8 new glyphs, drawn to the house rules** (gs:6-16: 20-unit box, weight 1.6, flat caps, mitre joins, solid facets, a hexagon instead of a circle):

| Glyph | Drawing |
|---|---|
| `trash` | A lid rule with an accent handle facet, and a tapered can with two inner rules. |
| `pause` | Two solid upright facets. `stop` stays one square. |
| `filter` | A funnel outline with an accent facet across its mouth. |
| `sort` | Two stems, an up-head facet on the left and a down-head facet on the right, in `undo`'s facet style (gs:73). |
| `count` | `letters('#')`. |
| `group` | Three short rules gathered by a bracket into one head facet. |
| `watch` | A straight-stroke lens (a rhombus) with a diamond pupil facet. It must not read as `find`'s hexagon. |
| `trace` | Three small nodes on an elbow wire ending in a head facet. It must not read as `field`'s two squares (gs:52). |

### 1.5 What changes, and the hand

**The rule for every row that changes something** is "follows the hand rules, Undo where possible, nothing silently applied, what cannot be undone always asks". The row calls `cm.change(host, target, words, line, scope)`. That builds a `field_do.Step(words, 'write', line, scope=…)` (field_do.py:25-33) and goes through `SlateFace.stage(title, step, asked=True)` (s2:1991-2030).

- At **Do and show** (the default, sh:32), an operation on `HERS_SHOW` is done at once.
  - A card in her pane shows the line on the slab.
  - The trail records it with an Undo where `takes_back` has one (s2:2032-2087).
  - The status line says it.
  - The undo row (§1.1, rule 7) appears in the next right-click.
- Anything else waits for Approve with `why_waits` (sh:161-164).
- Anything `ALWAYS_ASKS` covers waits with `why_asks` (sh:46-57).
- Before you choose, the row carries the status caption "asks" when it will wait, as the Field's steps already do (cm:1279). The foot says why.

| Class | Rows | Path today | Path in the new design |
|---|---|---|---|
| **Reads and navigation** | Open, Show…, Ask…, Copy…, every And then… step, Show the rows, Copy the line | direct | direct. Foot: "reads only · nothing changes" or "opens … · nothing runs" |
| **Changes with an exact Undo** | Move to Trash (`files.trash`, sh:39), New folder… (`files.mkdir`), Save as a sheet (new `chains.save`), Keep for… (`words.keep`, new name only); Rename…, Copy to…, Move to… after D1 | Trash, Rename, Copy and Move are direct with no record (cm:479-503) | stage(asked=True). Done at once at Do and show, with Undo. Waits at Ask first |
| **Changes with no exact Undo** | Watch it, Add to the Agenda (`agenda.add`), Export…, Stage in Delivery | direct (s2:2831-2834, 2887-2889) | stage(asked=True). The card says "There is no exact Undo for this: what it made is kept beside what was there." (s2:2074) |
| **Edits on the page under your eyes** | Bold, Italic, Underline, Plain, Paragraph style, the page half of Move to notes | `documents.edit` with `expected_revision`; the page's own Undo (cm:322-354) | unchanged (decision D2). The change lands where you are looking and the page's Undo takes it back. The foot shows the `documents.edit` line and "the page's Undo takes it back". Move to notes says honestly "Undo puts the words back; the note stays" (today's gap, cm:357-378) |
| **Cannot be undone: always asks** | Stop… on a job (`jobs.cancel`) or on Agenda work (`agenda.cancel`), Discard this draft… (`copies.discard`), Forget it (`words.forget`), Send to your command (`shell.*`) | Stop is one click (cm:974→910-921; cm:1045→1025-1030); a kept shell line runs on one click (chm:299, 311-323) | always a waiting card with `why_asks`, e.g. "what it stops or settles cannot be put back" (sh:52). The row reads "Stop…" with caption "asks" |

### 1.6 Every kind of thing: the first level and one level down

**How to read these lines:**
- At rest: `[glyph] Words`, in order.
- `+then` means And then… / Start from › is present; `+more` means More ›.
- More lists its verb groups in this order: *Open and show · Look into it · Change it · Compare · Ask and find out · Make and arrange · Send and keep · As a line · Copy · This working copy · Remove*. A group with nothing in it is not drawn.

**File in Files** (cm:596-664; e.g. `notes.csv`, heading glyph `table`)
- At rest: [table] Open · [asked] Ask Stacy about this · [cell] Rename… · [trash] Move to Trash · +then · +more
- More, 17-18 rows:
  - *Open and show:* [window] Open with this computer's app; [rooms] Open in Calculator (one per adapter, cm:71-77); [source] Show in its folder (only when the file came from a search, never as a grey placeholder)
  - *Change it:* [copy] Copy to…; [reach] Move to…; [delta] Versions…
  - *Compare:* [again] Compare with…; [again] Compare with a kept version › (its list is read when More opens, not at every right-click as today, cm:627)
  - *Ask and find out:* [info] Explain this file; [find] Investigate…; [book] Find tools in the Tool Atlas; [rooms] Explore capabilities…
  - *Send and keep:* [export] Export…; [stack] Stage in Delivery; [agenda] Add to the Agenda…
  - *Copy:* [copy] Copy path; [copy] Copy the address
  - *This working copy* (only on one, +4): [asked] Ask Stacy to work on this…; [again] Review changes to the original…; [source] Show the original; [trash] Discard this draft… (asks)
- And then starts from `@files:<path> | <lens by suffix>`, as `staC_for_file` does (cm:210-213). **The space guard goes** (cm:619-634): only a *joined* name must be one word (tp:10). A pill reads "Open pill…".

**Folder** (and smart folder)
- At rest: [folder] Open · [cell] Rename… · [copy] Copy path · [trash] Move to Trash · +then (its listing: `files.list {"path":"…"} | pick entries | select name,kind,size,modified`; the `entries` key is at `files_service.py:452`) · +more
- More: *Change it* — Copy to…, Move to…. *Send and keep* — Export…. *Copy* — Copy the address. *This working copy* (folder copies) — [find] Look inside, confined…; [prompt] Run a command here, confined… (asks); [export] Return as a pill…; [again] Review changes / Review the changes…; [source] Show the original; [trash] Discard this draft… (asks).

**Several files** (cm:674-694)
- At rest: [again] Compare these two / Compare revisions (when 2) · [copy] Copy to… · [reach] Move to… · [trash] Move to Trash · +more
- More: [stack] Stage selected files in Delivery; [copy] Copy paths.
- No And then; the foot explains why.

**Empty place in Files** (cm:697-710)
- At rest: [folder] New folder… · [receive] Import… · [sliders] View as › (Thumbnails / List, current one marked) · [recalc] Refresh · Start from › · +more
- More: *Make and arrange* — [find] New smart folder…; [copy] Work on a copy of a file…; [sliders] Show all files / Hide machine files. Then [home] **On any empty place ›**: Inquiries…, Algorithm & Theory Atlas…, Tool Atlas…, Writing line ›, Edit the Graphite menu…. This is today's nested "Root menu ›" (cm:1214-1218).
- Start from ›:
  - This folder as a list (the folder line above)
  - Its tables, the 8 most recent
  - Kept for this place
  - Your chains ›: the menu file, `kept_chain_entries`, cm:1149-1174

**Finder entry** (cm:713-739)
- Inside Files: [page/table] Open · [source] Show in Files · [asked] Ask Stacy about this file · [copy] Copy path · +then (new: today a Finder file has no chain, cm:730-734) · +more (Open in viewer; Open in <program>)
- Outside Files: [kind] Open · [page] Open in viewer · [asked] Ask… · [copy] Copy path · +more (Open in <program>). No line. The heading noun says "file · read only here".

**Empty place in the Finder** (cm:742-753)
- At rest: [sliders] View as › · [sliders] Show hidden files · [picture] Show the preview (its "Space" caption goes, cm:750) · [recalc] Refresh · Start from › · +more ([copy] Copy path; [home] On any empty place ›)

**Library** (cm:756-772)
- A received file: [page] Open · [receive] Keep a copy in Files · [asked] Ask Stacy about this file · [copy] Copy the name. No line, no More: 4 rows.
- The empty place: [receive] Receive files… · [recalc] Refresh · +more (On any empty place ›)

**Passage in a document** (cm:381-427)
- At rest: [bold] Bold / Not bold · [italic] Italic / Not italic · [note] Move to notes · [asked] Ask Stacy about this · +then (the page's paragraphs: `documents.get {"id":…} | pick document.blocks | select text`, the form at field_source.py:216) · +more
- More, 14 rows:
  - *Change it:* [underline] Underline; [plain] Plain (only when the words carry marks); [h1] Paragraph style › (Heading h1, Subheading h2, Minor heading h3, Body body, Code code; the current one marked)
  - *Ask and find out:* [find] Search for these words
  - *Make and arrange:* [document] New document
  - *Send and keep:* [export] Export…
  - *Copy:* [undo] Undo; [redo] Redo; [cut] Cut; [copy] Copy; [paste] Paste; [close] Delete; [select] Select all
  - *As a line:* [prompt] Put the Bold change in the writing line (today's Inspect in the line, cm:403-406; the foot shows the same line on hover of Bold)

**Page in a document** (caret only)
- At rest: [body] Paragraph style › · [paste] Paste · [select] Select all · [document] New document · +then · +more (Undo, Redo, Export…)
- Cut, Copy and Delete are not offered on a caret: they never apply there.

**Sheet on the Field** (cm:1392-1431; work face)
- At rest: [kind glyph] Open · [steps] What can be done › · [found] Doubt it › · [asked] Ask Stacy about this · +then (the sheet's **rows line**, §2) · +more
- More: *Look into it* — [trace] Trace it ›; [previous] What feeds it ›; [next] What it feeds ›; [delta] What if ›. *As a line* — [running] Run its line (the sheet's own `obj.stac`, which on a reviewed sheet reads its state, not its rows); [pin] Your words ›. *Copy* — Copy its name.
- Programs face: Open (its room) · What can be done › · Doubt it · Ask…
- Network face: [lines] Show in Log · What can be done › · Doubt it · [trace] Trace it (no Ask there, as today)
- "The brief of the desk" (cm:1425) moves to the empty desk, where it belongs.

**Empty place of the Field** (cm:1352-1391)
- Work face: [recalc] Look again · [found] Check the desk · [note] The brief · [rooms] Show the programs · Start from › (This face as lines: the 8 lines at cm:1371-1378, plus your words) · +more ([port] Show the network; [previous] Back; [pin] Your words › — Run it / In the line / Forget it… (asks) / Keep a new word…)
- The R, C, P/N, Esc and B captions all go.

**Today, the workspace's empty place, and pages with no finder** (cm:1197-1225)
- At rest: [note] New Idea… · [folder] New Project… · [receive] Import (Ingress)… · [asked] Inquiries… · Start from › (Your chains ›; the 8 most recent tables, today 30, cm:1182; Another file… opens Files) · +more ([book] Algorithm & Theory Atlas…; [book] Tool Atlas…; [prompt] Writing line › — Assignment [asked], Terminal [prompt], Search [find], Log [lines]; [cell] Edit the Graphite menu…)
- "Ctrl Shift N" goes (cm:829).

**PDF page, Office grid, image and viewer pages**
- New finder `find_viewer`. Today these land on "Technical PDF · an empty place" (pdf_qt.py:15, 360; cm:1690-1698).
- At rest: [source] Show enclosing folder · [asked] Ask about this file · [copy] Copy full path · +then (inside Files; merges "Build a chain from this file" and "Read and transform", cc:183-185) · +more (On any empty place ›)
- These rows exist today but are reachable only through "For <file> ›" (cc:25-32, 157-161).

**Log and Activity** (cm:1101-1138)
- An event in the Log: [asked] Ask Stacy about this · [running] Its job › (when it has one) · [copy] Copy · +then (`activity | where operation=<its operation> | select …`). The event payload carries `operation`, `state`, `detail` (activity.py:167); field names are to be confirmed against a real journal. "Show in Log" is not offered inside the Log itself.
- An event in Activity: [lines] Open · Ask… · [lines] Show in Log · Copy · +more (Its job ›)
- A connection or packet: [asked] Ask… · [reach] Follow this conversation · [window] Show the process (caption: the process name) · [copy] Copy address (caption: the address) · +then (`network.observe | pick connections | where remote=<ip> | select process,remote,rport,state`, the form at field_source.py:395)

**Jobs and Agenda work** (cm:957-979, 1033-1058)
- A job: [lines] Show its output · [pause] Pause **or** [running] Resume (whichever `no_pause`/state allows, cm:942-954; the other is not shown) · [stop] Stop… (asks) · [source] Show in Jobs · +then (`@evidence:<id>` when kept, else `@job:<id>`, cm:962-964) · +more (Copy the job id). In the Jobs list, Copy the job id takes the place of Show in Jobs.
- Agenda work: [pause] Pause or [running] Resume · [stop] Stop… (asks) · [running] Its job › · [agenda] Open Agenda · +then (its program)

**Cabinet, Activity selection, Machine, Settings** (cm:777-893)
- A cabinet record:
  - At rest: [folder] Open · [note] Write an idea here… · [rooms] Open <first workspace> · [copy] Copy the identity · +then (`@<canonical>` when addressable, cm:802-808) · +more
  - More: *Open and show* — [page] Read saved details; the other Open <workspace> rows. *Ask and find out* — the N provider checks [found]; **one** [rooms] Explore (merges cm:585-style `cabinet:explore` with Activity's second "Explore", cm:1438). *Make and arrange* — New Idea…, New Project…, Import (Ingress)…, Refresh, View as ›. *Send and keep* — Export (Egress)….
- The empty cabinet tree: New Idea… · New Project… · Import (Ingress)… · View as › · +more (Refresh; Export (Egress)…)
- Machine, a project: [folder] Open · [export] Export (Egress)… · [note] New Idea… · [recalc] Refresh · +then · +more (New Project…)
- Machine, the Work root: New Idea… · New Project… · Import… · Refresh
- Machine, a computer row: [source] Show in the Finder · [sliders] Open Settings · [copy] Copy what it says · [recalc] Refresh
- A setting: [sliders] Open this setting · [find] Search settings… · [copy] Copy the key · [larger] Expand all · +more (Collapse all)
- A settings group: Expand all · Collapse all · Search settings…

**Programs rows and head-menu rows** (cc:134-167)
- A Programs row: [info] What it does · [rooms] Open capability · [kind] For <current work> › · [book] Explore supported operations
- A head-menu row: [info] What it does · [running] Run this command, or [more] Choose an operation › · [kind] For <work> ›
- "What it does" loses the "Shortcut:" line (cc:125).
- Right-clicking a row of the right-click menu no longer makes a meta-menu. It pins the foot (§1.3).

**The console's output** (console_qt.py:445-451; new target `answer`)
- The output widget gets the `graphiteContext` property, the escape `owns_menu` reads (cm:1709) and nothing sets yet. A finder `find_console` then catches it.
- At rest: [copy] Copy · [select] Select all · [table] Save as a sheet · [recalc] Again · +then (from the rows the console already holds; nothing is run when the menu opens, unlike chm:133) · +more (Copy Link Location; [watch] Watch it; [agenda] Add to the Agenda; [copy] Copy the line)

**First-level rows, fresh workspace** (actions + then + more):

| Target | Rows | Target | Rows |
|---|---|---|---|
| File | 6 | Field sheet (any face) | 6 |
| Folder | 6 | Field empty desk | 6 |
| Several files | 5 | Today / workspace | 6 |
| Files empty place | 6 | Viewer / PDF page | 5 |
| Finder entry / outside Files | 6 / 5 | Log event / Activity event | 4-5 / 6 |
| Finder empty place | 6 | Connection, packet | 5 |
| Library file / empty | 4 / 3 | Job / Jobs-list job | 6 / 5 |
| Passage | 6 | Agenda work | 5 |
| Page | 6 | Cabinet record / tree | 6 / 5 |
| Setting / group | 5 / 3 | Machine project / root / row | 6 / 4 / 4 |
| Programs row / menu row | 4 / 3 | Console answer | 6 |

The most any menu can have is 4 + 1 learned + 2 kept + then + more + the undo row = **10**.

### 1.7 Fit (estimated from pq:30-38: row 24, rule 9, margins 12, heading 24, foot ≈73)

| Menu | Height | Fits in 1366×768? |
|---|---|---|
| Today's file menu, for comparison | ≈725 (it scrolls in a 768 window, cm:2004, 2016) | no |
| Fresh first level (4 + then + more) | ≈271 | yes |
| Fullest first level (5 + 2 kept + undo) | ≈385 | yes |
| More, file / working copy / passage / Field sheet | ≈504 / ≈618 / ≈456 / ≈210 | yes |
| The step panel (§2.1) | ≈425 | yes |
| Field list ≤12 / value list ≤8 | ≈300 / ≈204 | yes |
| Columns side by side at most: panel + fields + values | ≈820 px wide | yes |

**Guarantees:**
- **The rows never scroll.** If More would be taller than the window (`bounds()`, cm:1992-1996) less two insets, `fit_more` turns its groups into submenu rows, the largest group first, until it fits. It never scrolls.
- **The menu is placed inside the screen, not only inside the window.** The screen's available geometry is preferred when the window is smaller, so a short window doesn't force a fold the screen has room for.

### 1.8 Mouse first; the keyboard still works

- **Mouse:** right-click opens; click chooses; hover opens a submenu after 240 ms (cm:55); a row's own right-click explains it in the foot.
- **Keyboard:**
  - The Menu key and Shift+F10 still open the menu for the focus (cm:2251-2261), its first row focused.
  - Up/Down, Home/End, type-to-select and F1 work as today (pq:545-580).
  - Right or Enter goes into a submenu or into And then…. Left or Esc comes back one level.
  - In the step panel, choosing a value returns focus to its first verb.
- **None of these keys is printed anywhere.** The Field's key card stays the one place that lists them (RELEASE_NOTES_0.8.0.md:158-162).

---

## 2. Chaining: And then…

### 2.1 The step panel

Choosing **And then…** (click, Right or Enter) turns the menu, **in place** (same top-left, same width), into the step panel. It does not cascade a QMenu builder beside it (cm:2036-2042, chm:99-109). The first menu is gone, so at most three columns ever stand side by side.

```
[chain] ‹ 07 Bench readings · and then                 4 rows · 5 steps left
▌@office:owner:db5f66… | pick origin.reviewed_rows | select parameter,value,unit,conditions
 parameter         value  unit  conditions
 Rail voltage      12     V     During both observations
 Settled current   280    mA    After settling
 Startup current   650    mA    During startup pulse
 … and 1 more
[filter] Only rows where                              ›
[sort]   Sort by                                      ›
[count]  Count                                        4
[group]  Count by                                     ›
[more]   More steps                                   ›   Total by · Keep columns · Add a column · Join with · First
──────────────────────────
[lines]  Show the rows
[table]  Save as a sheet
[pin]    Keep for sheets…
[more]   More endings                                 ›   Watch it · Add to the Agenda · Copy the line · In the line ·
                                                          Lay it out below · Keep in your Graphite menu… · Send to your command
[undo]   Take back “only rows where unit is mA”           (once a step is added)
```

**The panel's parts:**
- **The heading** is the chain so far, with its count and the steps left. A line holds one source and at most 7 steps (tp:25).
- **The slab** is the exact line. A **preview** shows 3 rows and "… and N more", in mono, quiet.
- **Step verbs** use plain words, never the line's keywords: today the menu shows `where`, `group by`, `take`, `join with` and lens names (chm:33-36, 171-196; cm:549-552). The first panel for a thing that is not yet rows offers **Read it as ›** first: the sheet <name>, rows, headings, drawing layers, text on the drawing, lines, facts. This merges Extract › and Chain from here, which list the same readings today (cm:537-555, chm:153-166).
- **Counts.**
  - Every value offer carries the exact number of rows it would keep, and **Count** carries its answer.
  - **One Kernel read per step:** a new read-only `language.peek` returns the count, up to 200 sample rows, and per-column type, distinct values, the 8 commonest, and numeric picks. It is computed in one pass on the Kernel side under the 2000-row source budget (tp:219).
  - Every offer's count is then computed from that data with `typed_pipeline.apply` itself, the same code `language.run` uses (sl:116-127). So **no hover runs anything**.
- **Steps left** shrinks with each step. At 0 the verbs are greyed, with the reason "A line holds seven steps: save or keep it, then go on from what you saved".
- **Esc or a click away** closes the panel. The unfinished chain is remembered for 10 minutes, and And then… on the same thing then offers "Go on from: … (2 steps)" as its first row.
- **Endings** are listed in §2.4 and §1.5. Save as a sheet and the tray's Save sheet become **one** ending with a receipt (cw:306-335). The tray stays as the "Lay it out below" ending for long work (cw:165-201).

### 2.2 Worked example: After Hours 07, the sheet "07 Bench readings"

The record is office `owner:db5f669f863d4c71b89fa7ba348957da`, reviewed from `07_Bench_Readings.pdf` page 1. Its 4 reviewed rows are:

| parameter | value | unit |
|---|---|---|
| Rail voltage | 12 | V |
| Settled current | 280 | mA |
| Startup current | 650 | mA |
| Startup duration | 110 | ms |

That is `origin.reviewed_rows`, the field_doubt.py:211 form.

**The problem with the sheet's line today.** Its own line, `office.get {"id":…} | select source_state.state,origin.pdf.page_index` (field_source.py:180), returns **one** row: `CURRENT_PDF_SOURCE, 0` (script output). You cannot filter readings from it, and `this | …` keeps only that line's first step (field_page.py:399). So the design gives each kind a **rows line**. For a reviewed sheet it is:

```
@office:owner:db5f669f863d4c71b89fa7ba348957da | pick origin.reviewed_rows | select parameter,value,unit,conditions
```

**Step 0. Right-click the sheet on the Field.**
- `find_field` selects it, as today (cm:1674-1687). Nothing is read: the menu shows no counts at rest, unlike today, where a file's right-click dispatches `files.versions` (cm:627).
- The menu: [table] Open · [steps] What can be done › · [found] Doubt it › · [asked] Ask Stacy about this · [chain] And then… · [more] More.
- The foot shows the rows line above (cut to `owner:db5f66…` by `bt.eye`) and "reads only · nothing changes".
- Hovering *Doubt it* shows `field.doubt {"id":"…"} | pick rows | select verdict,about,why` · reads only.
- Hovering *Open* shows "Opens its page in the Office · nothing runs".

**Step 1. Choose And then….** The menu becomes the panel: **1 read** (`language.peek`). It shows "4 rows · 5 steps left", the 3-row preview, and Count caption **4**.

**Step 2. Filter.**
- Hover **Only rows where ›**. The field list is drawn from the peek, with no read:
  - parameter — text · 4 different
  - value — numbers 12 to 650
  - unit — text · 3 different
  - conditions — text · 4 different
- Hover **unit ›**: is mA **2** · is V **1** · is ms **1** · is not mA **2** · has… (puts the line so far in the writing line, to finish).
- The foot on "is mA" shows `… | where unit=mA` and "2 rows · reads only".
- Click **is mA**. The cascades close and the panel redraws with **1 read**: "2 rows · 4 steps left". The preview shows Settled current 280 mA and Startup current 650 mA. A new row appears: [undo] Take back "only rows where unit is mA".

**Step 3. Count.** Click **Count**, whose caption was already **2**. The panel shows "1 row · 3 steps left" and the preview `count 2`. Line:

```
@office:owner:db5f66… | pick origin.reviewed_rows | select parameter,value,unit,conditions | where unit=mA | count
```

**Step 4. Save as a sheet.**
- `cm.change` stages the step **Save as a sheet** with the line `/chains.save {"line":"…| where unit=mA | count","name":"07 Bench readings · mA count"}`.
- At Do and show (with D1, which adds `chains.save` to `HERS_SHOW`), it is done at once:
  - Her card: "For “07 Bench readings”: save as a sheet." The line is on the royal slab, followed by "Done: “Slate/Chains/07 Bench readings · mA count/rows.csv” is in Files." and an **Undo** button.
  - The trail's Undo is `/files.trash {"path":"Slate/Chains/07 Bench readings · mA count"}`, guarded by `items: 2` (the CSV and its receipt). The existing folder guard in `changed_since` already checks that (s2:2128).
  - The next right-click anywhere starts with [undo] "Undo: saved “mA count”".
- At Ask first, the card waits with Approve and nothing is written.

**Other step 2 choices, all checked by the script:**

| Choice | Rows | Row values |
|---|---|---|
| value › over 100 | 3 | 280, 650, 110 (text values compare as numbers here, tp:183-187) |
| Count by › unit | 3 | V 1 · mA 2 · ms 1 |
| Sort by › value | — | sorts as **text** (tp:196-210), see §2.5 |

### 2.3 Worked example: a CSV in Files ("parts list.csv", made up for the check)

The table has 6 rows: Ref, Part, Qty, Stock.

**Step 0. Right-click it.**
- The menu: [table] Open · [asked] Ask Stacy about this · [cell] Rename… · [trash] Move to Trash · And then… · More.
- The foot shows `@files:parts list.csv | rows`.
- Today every line row is greyed for this name: "An address is one word: this name has a space…" (cm:619-634). In the design it is enabled, because the parser takes it as the main source.

**Step 1. And then….** One read: "6 rows · 6 steps left".

**Step 2. Add a column.**
- **More steps › Add a column ›** offers presets from the first numeric pairs: "Qty − Stock", "Stock − Qty", "Qty + Stock", and **Your own…**. The last is prefilled `Short = Qty - Stock`, as chm:263 does.
- After OK the chain **continues**. Today "add a column…" ends straight in the console (chm:260-264).
- The panel shows "6 rows · 5 steps left" and the preview gains a Short column (−28, 2, 4, −8, 1, −2).

**Step 3. Filter.** Only rows where › Short (numbers −28 to 4) › **over 0 · 3**. 0 is added as a pick because the range crosses 0; picks are otherwise spread over the values, as at chm:209-211. The panel shows "3 rows · 4 steps left".

**Step 4. Sort.** Sort by › Short › **largest first**. The panel shows C1 4 · R2 2 · U1 1.

**Step 5. End.**
- **Save as a sheet:** as in §2.2.
- **Watch it:** `agenda.add` is on `HERS_SHOW` (sh:39), so it is done and shown. The card says there is no exact Undo, because taking it out is `agenda.cancel`, which always asks (sh:52).

The line, 4 steps and 3 rows:

```
@files:parts list.csv | rows | add Short = Qty - Stock | where Short over 0 | sort -Short
```

**Join with ›** lists only tables with one-word names. The parser refuses `join @files:stock count.csv rows on Ref` with "join requires: @address [rows|…] on FIELD" (script output; tp:10, 98-104). The list's quiet foot says "a table whose name has a space can't be joined".

### 2.4 Keeping a chain for a kind of thing (it appears at rest)

**Keep for sheets…** (the kind's plural word) opens a small dialog. It shows the line on the slab and a name field prefilled from the steps ("ma-count"; a word is 2-24 small letters, digits or hyphens, `stac_words.py`). Its button is **Keep**. It stages:

```
/words.keep {"name":"ma-count","line":"these | where unit=mA | count","for":"field:sheet"}
```

- **What `these` means.** It is a new lead word: the selected thing's **rows line**, written out before it runs, the same way `this` is written out by `field_page.expand_this` (field_page.py:388-399).
  - **Why not change `this`:** it means the first step of the sheet's own line, and the owner may already have kept words built on `this | pick …`.
  - `these` joins `RESERVED` (`stac_words.py:34`) and is kept without the parse check, as `this` is (`stac_words.py:82`).
- **Where it is stored.** `words.keep` gains an optional `for`, saved in a new nullable column `for_kind`. Words live in the workspace's own Kernel, so a kept chain is **per project**.
- **Where it appears.** Right-clicking any reviewed sheet in this project, for example "07 Limits Rev B CURRENT", shows [pin] **ma count** at rest.
  - Choosing it opens the panel already at `… | where unit=mA | count`. On Rev B that honestly shows `count 0`.
  - Typing `ma-count` in the writing line, with the sheet selected, does the same. The kept chain is a word.
- **The hand.** `words.keep` is not on `HERS_SHOW`. Under D1 its Undo is `/words.forget`, guarded by "the word still holds exactly this line" and offered only for a **new** name. Without D1 the card waits for Approve.
- **The menu file still works.** It is shown under Start from › Your chains, as today (cm:1149-1174), and its new keeps store **the chosen ending**; today it always writes `then console` (chm:347). New keeps go to words. Nothing is migrated.

### 2.5 Limits the panel handles honestly

- **More than 200 rows.** A line answers at most 200 rows (tp:272; sl:112). `language.peek` still counts beyond that, e.g. "1,240 rows: a line shows at most 200; filter first".
  - Show the rows and Save as a sheet are greyed with that reason. Today's tray already refuses at 200 (cw:308).
  - **First › 200** is offered as one step.
  - Today a lens over 200 rows is silently dropped (chm:164) and the builder only says "does not run" (chm:133-135).
- **Steps left** are always shown. Sort, group, select and take are no longer offered blind at the limit; today they fail only when opened.
- **Numbers kept as text.** Reviewed values are strings ("280"). `where … over N` converts them (tp:183-187), but `sort` orders text as text (tp:196-210). Here that happens to give 650, 280 (script), yet "12" would sort above "110".
  - Sort by › value therefore reads "largest first (as numbers)". That adds `add value_n = value` first, which converts the text to numbers (tp:142-147), at the cost of one step.
  - The other fix, making sort read numeric text as numbers, changes the line's meaning everywhere. That is decision D4.
- **Joins:** one word, one level (sl:79-80), as above.
- **No line for the thing.** And then… is not shown, and the foot says why. That covers several files, a Finder entry outside Files, a setting, and a Library file.

---

## 3. Nothing lost

Notation for the "now" column:
- **rest** = first level
- **then** = And then… panel; **then/read** = its "Read it as ›" first panel; **then/end:…** = an ending
- **from** = Start from ›
- **foot** = shown in the foot
- **more/<group>** = More ›, with the group named
- **merged → x** = the same call as x
- **dropped** = with the reason given

Every key of `FOLDED` (cm:2267-2307) gets the new path in its fourth column: `more/<key>`, `then/<key>`, `more/root/<key>`.

**File in Files** (25-30 rows)

| Today | Now |
|---|---|
| open | rest |
| open:outside | more/open |
| show:folder | more/open, only when it applies; never a grey placeholder |
| rename | rest |
| copy:to, move:to, versions | more/change |
| export | more/send |
| inspect | foot + then/end:line + more/line |
| run | then/end:show ("Show the rows") |
| chain | then |
| compare:with, compare:version › | more/compare |
| extract › | merged → then/read |
| adapter:* | more/open |
| atlas, explore, explain, investigate | more/ask |
| delivery:stage, agenda | more/send |
| ask | rest |
| copy:path, copy:address | more/copy |
| trash | rest |
| copy:slate, copy:review, copy:original, copy:discard | more/draft |

**Folder:** open, rename, copy:path, trash → rest. copy:to, move:to → more/change. export → more/send. copy:address → more/copy. copy:look, copy:run, copy:pill, copy:review, copy:original, copy:discard → more/draft.

**Several files:** compare:two/revisions, copy:to, move:to, trash → rest. delivery:stage → more/send. copy:paths → more/copy.

**Files empty place:**
- new:folder, import, view › (view:icons, view:list), refresh → rest
- new:smart, work:copy, view:all → more/make
- root › → more/root, with inquiries, algorithms, atlas, line › (line:*) and menu:edit
- root/chains and root/start → from

**Finder:**
- An entry: open, show:files, ask, copy:path → rest. change:files → merged → show:files (the same call, cm:724, 729). open:viewer, adapter:* → more/open. inspect → foot + then. run → then/end:show. extract → then/read. change:none → the heading noun "read only here" (dropped as a row; it never did anything, cm:736).
- The empty place: view ›, hidden, preview, refresh → rest. copy:path → more/copy. root → more/root.

**Library:** open, keep, ask, copy:name → rest. On the empty place: import, refresh → rest; root → more/root.

**Passage:**
- mark:bold, mark:italic, notes, ask → rest
- mark:underline, mark:clear, style › (style:*) → more/change
- search → more/ask
- doc:new → more/make
- doc:export → more/send
- edit:undo, redo, cut, copy, paste, delete, all → more/copy
- inspect → foot (on hover of Bold) + more/line

**Page:** style, edit:paste, edit:all, doc:new → rest. edit:undo, edit:redo → more/copy. doc:export → more/send. edit:cut, copy and delete are always greyed on a caret: dropped there, still on a passage.

**Field sheet:**
- field:open, field:do ›, field:doubt ›, field:ask → rest
- field:trace ›, field:fed ›, field:feeds ›, field:whatif › → more/look
- field:run, field:words › → more/line
- field:inspect → foot + then/end:line
- field:copy → more/copy
- field:brief → moved to the empty desk (field:brief there)
- Inner rows are kept: doubt:all, trace:all, do:* (status caption "asks"), whatif:*, go:*. They lose the captions X and T, the ← and → captions (cm:1401-1402) and the key words in tips (cm:1259, 1261, 1280, 1414, 1417, 1420).

**Field empty desk:** field:again, field:check, field:brief and the first other face → rest. The second face and field:back → more/open. field:stac › (field:stac:*) → from. field:words › (words:*) → more/line.

**Today / workspace:** new:idea, new:project, import, inquiries → rest. chains, start → from. algorithms, atlas → more/ask. line ›, menu:edit → more/line.

**Viewer:** viewer:folder, viewer:ask, viewer:path → rest. viewer:chain, viewer:continue → merged → then.

**Log, Activity, network:**
- An event: ask, job ›, copy → rest. open, show:log → rest in Activity; show:log is not offered inside the Log.
- A connection or packet: ask, follow, process, copy:address → rest.

**Jobs and Agenda:**
- A job: job:output, job:pause|job:resume, job:stop, job:show → rest. inspect → foot + then. copy:id → more/copy.
- Agenda work: queued:pause|resume, queued:stop, job ›, agenda → rest. inspect → foot + then.

**Cabinet:**
- open, cabinet:write, the first cabinet:workspace:*, copy:id → rest
- cabinet:record and the other workspaces → more/open
- cabinet:check:* → more/ask
- cabinet:explore + activity:explore → merged → more/ask "Explore"
- inspect, run → foot + then
- export → more/send
- refresh, view ›, new:*, import → more/make
- actions:none → the heading noun

**Machine and Settings:** every row stays, at rest or in more/make (§1.6).

**Command context:** command:inspect, invoke, choices, work and atlas → rest. On a right-click row, the meta-menu → dropped, replaced by the foot pin. "Continue this chain" (cc:153) → dropped: chaining happens in the menu.

**The chain builder** (its words carry the same meanings):
- header line → the slab
- "Build on the desk…" → then/end:tray
- lenses → then/read
- where › F › word › V → filter › F › value. "at least" and "at most" sit in "at least or at most ›". "has" is typed.
- sort › F › smallest/largest → sort › F
- group by › F › count → Count by › F
- group by › F › sum/avg/min/max N → Total by › F › N
- select › only F / choose columns… → Keep columns ›; the dialog now continues the chain
- add a column… → Add a column ›; continues the chain
- join with › T › join/missing on F → Join with › T › "matching on F" / "missing from it on F"
- take › → First ›
- count → Count
- then › console / sheet / watch / agenda / keep / copy / shell › → the endings; shell always asks
- root_menu → the empty places (rest, from, more)

**Dropped outright, with reasons:**
- The "unavailable" caption (the greyed ink and the foot say it).
- Placeholder rows that never act.
- "Through Kernel.dispatch: …" tooltips (the foot shows the line).
- "revision N" in headings (it is in the line).
- Every printed key, and "Shortcut:" (owner rule, RELEASE_NOTES_0.5.2.md:10-23).
- Tear-off strips (chm:104, 141, 171…): "Lay it out below" keeps a chain in view.
- The run when the menu opens: on a file (cm:627) it moves to More; in the console (chm:133) the menu uses the rows already held.

**Left as their own menus in this design** (named honestly as phase 4):
- worksheet rows (sheet_workbench_qt.py:566-640)
- program room results (program_rooms_qt.py:195-209)
- Master Stop, Lab paths, Adaptive, the meters, the companion
- text fields (Qt's own menu)

---

## 4. Build plan

### 4.1 Reused as is

- **Target / Entry** (cm:88-130), the providers and `entries_for` (cm:1442-1461), and every revision check (cm:322-354, 454-460, 901-907, 1015-1022, cc:65-89).
- **The single dispatch door** (cm:143-147); `perform` with its refusals (cm:2143-2153).
- **DeskMenu:** keyboard, type-to-select, F1, Rule, Margin (pq:431-580); the heading (cm:1809-1876).
- **The finders and `target_at`** (cm:1466-1727).
- **`tool_faces.icon`** (tf:196-220), **`GLYPHS`/`KIND`** (gs:394-415), **`bt.line_sheet`** and **`bt.eye`** (bt:66-74).
- **The hand:** `stacy_hand.hers`/`why_asks`/`takes_back`/`guard`/`record` (sh:141-249); `SlateFace.stage`/`run_staged`/`undo_staged`/`changed_since` (s2:1991-2129); `field_do.Step`/`call` (field_do.py:25-50).
- **From the chain menu:** `chain_menu.parse_menu`/`menu_path`/`stock_methods`/`edit_menu_file` (chm:331-499); the tray as an ending (cw).
- **`explain.explain` suggestions** (explain.py:15-55) to order the first verbs; `stac_words.keep`/`expand`/`known_to`.

### 4.2 New and changed, file by file

**`workbench/menu_rest.py` (new, no Qt)**
- `REST`: kind → ordered preference keys (§1.6).
- `VERBS` (group order and words) and `SECTION_VERB` (maps today's sections to verbs, so providers keep their `section`).
- `VERB_OF` overrides by key prefix (`compare:`→compare, `adapter:`→open, `export`→send…).
- `GLYPH_OF` by key or prefix, with fallback from the old icon keys.
- `kind_of(target)`: e.g. `'file:table'`, `'field:sheet'`, `'empty:files'`, `'job'`.
- `at_rest(kind, present, use, kept) -> (rest, yours)`; `note_use(state, kind, key, now)`; `clean_use(value)`; `fit_more(entries, budget_px, m)`.

**`workbench/menu_steps.py` (new, no Qt)**
- `rows_line(host, target)`: one function for every kind's read line. It replaces scattered pieces: `staC_for_file`/`LENS` (cm:68, 210), the cabinet (cm:806), the job (cm:962), the Field face lines (cm:1363-1378).
- `plain(transform)`: the words for a step.
- `offers(peek)` → verbs and values with counts, via `typed_pipeline.apply`.
- `steps_left(line)`; `ENDINGS`; `expand_these(host, text)`.

**`workbench/stacy_language.py`**
- `language.peek` added to `FIELDS`/`SCOPES` (read) and `dispatch`.
- It runs `_execute_plan` with limit 2000 and returns a summary: count, ≤200 rows, columns, tallies, readings for a non-rows object. `model_calls: 0`.
- `language.run` is untouched.

**`workbench/context_menu.py`**
- `Entry` gains `line` (str or callable), `verb`, `tone` and `glyph`. `tooltip()` loses the dispatch line.
- `ContextMenu.__init__` lays out undo / rest / yours / then / more / foot instead of sorting all rows by section (cm:1926-1945).
- New `StepPanel` (drill-in, refills rows in place, deferring with `QTimer.singleShot(0)` as cm:1895 does) and `LineFoot`.
- `ContextRow.paintEvent` uses `tool_faces.paint_glyph` (cm:1905-1919); `EXTRA`/`_extra_paths`/`paint_icon` are removed.
- Every key caption is removed (listed in §0).
- `job_action`/`queued_action` stop dispatching `*.cancel` directly and go through `change()`.
- `rename_file`/`place_files`/`trash_files` call `change()` (cm:479-503).
- New finders `find_viewer` and `find_console`.
- The Router: a right-press on a `ContextRow` pins the foot (cm:2233-2238).
- `FOLDED` gets the new paths.

**`workbench/glyph_set.py`:** the 8 glyphs of §1.4, added to `GLYPHS`.

**`workbench/tool_faces.py`:** `icon(key, tone=None)`, cache key `(key, glow, tone)`; `paint_glyph(...)`; fix the out-of-date "amber" docstring (tf:197).

**`workbench/stacy_hand.py`:**
- `takes_back`/`guard`/`undo_allowed` learn: `chains.save` (trash the folder, items guard), `files.rename` (rename back, guarded by sha256), `files.copy` (trash the copy, sha guard), `files.move` (move back, guarded), `words.keep` new name (forget, line guard), `files.restore` for Trash.
- `UNDOES` grows to match.
- `HERS_SHOW` additions are **decision D1**.

**`workbench/shell2.py`:**
- `save_rows` / `watch` / `keep_in_agenda` (s2:2822-2889) route through `stage`.
- The new `chains.save` operation (CSV + receipt in one folder, merging cw:306-335) is registered where the files operations are.
- The preview note "Ctrl+Enter keeps this word" goes (s2:1230).

**`workbench/stac_words.py`:** a `for_kind` column (ALTER guarded by `pragma table_info`), a `for` argument on `words.keep`, `these` in `RESERVED`, and the parse skip for `these`.

**`workbench/field_page.py`:** the error "(F9)" loses the key (field_page.py:397). `these` is written out next to `this`.

**`workbench/session.py`:** `menu_use` is loaded through `menu_rest.clean_use`.

**`workbench/command_context.py`:** "Shortcut:" goes (cc:125); "Continue this chain" goes (cc:152-153).

**`workbench/console_qt.py`:** `output_menu` (console_qt.py:445-451) defers to cm; the console keeps `last_rows`.

**`workbench/chain_menu.py`:**
- `open_here` (chm:502-509; Tools ▸ Chain Menu, menus2.py:272) opens the step panel, or Start from ›.
- `Chain`/`fill`/`shape`/`where_values`/`join_tables` and `chain_icons.py` are retired after phase 3.
- `then`/`keep`/`to_shell` go through the hand.

**Docs:** the GRAPHITE_DESK.md right-click section (GRAPHITE_DESK.md:803-959), DAILY_GUIDE.md:119-131, menus2's out-of-date docstring (menus2.py:7-8).

### 4.3 Phases (each one can ship on its own)

1. **The face.** Glyphs, the foot, rest/More/fit, no printed keys, Stop and the shell endings asking. And then… opens today's builder (`Entry.qmenu`) for one release.
2. **The line.** `rows_line`, `language.peek`, `StepPanel`, endings through the hand, `chains.save`.
3. **Keeping and the remaining surfaces.** `these`, words `for_kind`, kept chains at rest, the learned slot, `find_viewer`/`find_console`/Agenda rows; retire the QMenu builder and `chain_icons`.
4. **The surfaces that keep their own menus** (§3).

### 4.4 Tests that prove it

**`tests_integrated/test_menu_rest.py` (new, pure, no Qt):**

1. `at_rest(k, present=set(REST[k]), use={}, kept=[])[0] == REST[k][:4]` for every `k` in `REST`. And `at_rest('file:table', present={'open','rename','trash','copy:path'}, …)[0] == ('open','rename','trash','copy:path')`: an absent key yields to the next preference.
2. The learned slot:
   - `use={'file:table': {'compare:with': [3, t]}}` → `yours == ('compare:with',)`
   - with `[2, t]` → `yours == ()`
   - `rest` is identical in both cases.
3. Kept chains: `kept=['ma-count','x','y']` → `yours[:2] == ('kept:ma-count','kept:x')` and `len(rest) == 4`.
4. On the 4 Bench rows (literals in the test):
   - `offers(peek(rows))['filter']['unit']` lists `('is mA','where unit=mA',2)`, `('is V',…,1)`, `('is ms',…,1)`, `('is not mA','where unit is not mA',2)`.
   - For **every** offer of every verb: `offer.count == len(tp.apply(rows, tp.parse('x | ' + offer.step)['transforms']))`. Counts are always what the line would give.
5. `steps_left(rows_line(bench_sheet)) == 5`; after `| where unit=mA`, `4`.
6. `tp.parse(sl.source(rows_line(t))[0])` succeeds for a fixture of every kind that has a line.
7. Glyphs: `{'trash','pause','filter','sort','count','group','watch','trace'} <= set(GLYPHS)`, and every value of `GLYPH_OF` is in `GLYPHS` or `KIND`.
8. No printed keys (AST walk of `context_menu.py`, `command_context.py`, `menu_rest.py`, `menu_steps.py`):
   - No `caption=` string constant matches `KEY = re.compile(r'(?<![\w-])(?:Ctrl|Shift|Alt|Meta|Cmd|Esc|Escape|Enter|Return|Space|Backspace|F(?:[1-9]|1[0-2]))(?![\w-])')`.
   - None is fullmatched by `r'\(?[A-Z0-9←→]\)?'`.
9. Words: no label in `menu_steps`/`ENDINGS`/`VERBS` contains `staC`, `stac`, `pipeline`, `language`, or starts with `where `, `pick `, `select `, `join `, `take `, `group `.

**`tests_integrated/test_context_menu.py` (Qt, run later, not now):**

10. **First level.** For every target fixture (the kinds of §1.6) on a fresh session:
    - `menu.keys()[:4]` equals the first four present keys of `REST[kind]`
    - `len(menu.keys()) <= 7`
    - `menu.keys()[-1] == 'more'` when More has rows
    - `'then' in menu.keys()` exactly when `rows_line(target)` is non-empty
    - every row's `entry.glyph in GLYPHS or in KIND`
11. **Nothing scrolls.** At `w.resize(1366, 768)` and `(1920, 1200)`, for the menu, More, the step panel, a field list and a value list: `menu.scroll.verticalScrollBar().maximum() == 0` and `menu.bounds().contains(menu.geometry())`.
12. **No row prints a key.** Walk `menu_tree` (cm test helper, test_context_menu.py:708-718) through More and `then/*`, plus `menu.foot.words.text()`. `KEY.search` finds nothing in any label, caption, tip, reason or foot, and no caption is a lone letter. The "Shortcut:" word is absent from `cc.describe` output.
13. **The foot.** For each row given focus:
    - if `entry.line`: `menu.foot.slab.text() == bt.eye(entry.line_text())` and `menu.foot.slab.styleSheet() == bt.line_sheet()`
    - else the slab is hidden and the words end with "nothing runs"
    - at rest it shows `rows_line(target)`
14. **One read per step.** Patch `cm.dispatch` to count. Opening And then… → `language.peek == 1`, `language.run == 0`. Hovering Only rows where › unit › values → still 1. Choosing "is mA" → 2.
15. **The hand.**
    - Dial `show`: Save as a sheet → `card.ran is True`, `card.entry['undo'].startswith('/files.trash')`, the folder exists. `undo_staged(card)` → the folder is gone.
    - Dial `ask`: `card.ran is None` and no folder.
    - Stop… on a Running job → `jobs.cancel` is never dispatched before Approve, and the card text contains `sh.why_asks('jobs.cancel')`.
16. **Nothing lost.** The `FOLDED` loop (test_context_menu.py:594-629) matches by leaf: `key in {p.rsplit('/',1)[-1] for p in found[kind]}`, with depth ≤ 2 (≤ 3 under `more/root`). `'menu:edit'` is in `found['empty:files']`'s leaves, replacing the pinned `'root/menu:edit'` (test_context_menu.py:621). A new `FOLDED_CHAIN` maps every word of the old builder to a `then/*` key, walked the same way.
17. **Kept for a kind.** Keep "ma-count" for `field:sheet` → on another sheet `'kept:ma-count' in menu.keys()` at the first level; on a calculation it is not.
18. **Metrics.** Replaces test_context_menu.py:679-689: `menu.m.icon == scaled(20)`, `menu.m.row == programs_qt.metrics(w).row` at 14 pt, one icon column, inside the window.
19. **Glyph drawing.** Patch `tool_faces.paint_glyph` to record keys and grab the menu: the recorded set equals the entries' glyphs. `programs_qt.paint_icon` is never called by a `ContextRow`.

---

## 5. Risks, and what is honestly hard

1. **Learned menus can move things under the hand.**
   - Research on adaptive menus is mixed. That is why only one slot learns, the four never move, changes happen between openings, and there is a reset.
   - The menu still differs between projects (per-project session state). Some may read that as "my menu changed".
2. **The hand adds friction unless the owner widens it (D1).**
   - Rename, Copy to, Move to and Keep for are not on `HERS_SHOW` (sh:39). Under stage(asked=True) they wait for Approve after their own dialog: two confirmations.
   - Adding them, with exact Undo lines, also lets **Stacy** do them by herself at Do and show. That is a policy change for the owner to make, not for me.
   - Trash's Undo needs `files.restore`, an approve-scope operation (`files_service.py:71-72`), in `UNDOES`.
3. **Page edits stay on the page's own Undo (D2).** They don't go through the hand, because sending Bold to a waiting card would be absurd. Move to notes keeps its known gap: Undo leaves the note (cm:357-378). The foot says so.
4. **Performance is not measured.**
   - `language.peek` is still synchronous on the window's thread. One read per step beats up to 32 (chm:208-216), but a 2000-row spreadsheet may still pause the menu noticeably.
   - Moving it off the thread depends on the Kernel's SQLite use across threads, which I have not checked.
5. **The rows line is missing for ordinary Office sheets.**
   - Reviewed sheets have `origin.reviewed_rows`. A sheet not made from a PDF has only cells: `office.get` returns cells, and no lens turns cells into rows (tp:12).
   - It needs a header-row view in `office.get`'s result (e.g. `data.rows`, so the existing `rows` lens works). That changes a read other code fingerprints (cw:42-60).
6. **`these` is new surface in the line language.** It is never named on screen, and lines are always written out on the slab, but it is one more word to keep consistent across the writing line, words and the menu. Changing `this` instead would break kept words.
7. **Numbers stored as text** (§2.5). Either the menu spends a step, or the line's sort changes meaning (D4).
8. **Drill-in departs from strict Fluxbox cascading.** The owner asked for "Fluxbox-inspired" (GRAPHITE_DESK.md:803-805). Values still cascade; only the chain's own panel replaces the menu, to avoid 8 popups. Rebuilding rows under the pointer during their own click must be deferred, or Qt deletes a widget inside its handler.
9. **Test churn.** `FOLDED` paths, the pinned `root/menu:edit`, the metrics test and the keys of the Field's menus all move. The `FOLDED` tests are rewritten, not merely loosened: leaf plus depth limit.
10. **The fit rule depends on window height.** `fit_more` may fold groups on a short window, so a rare action can be one level deeper at 1366×768 than at 1920×1200. The paths are stable for a given size.
11. **Some surfaces keep their own menu** (§3): worksheet rows, program rooms and others remain a separate look until phase 4.
12. **Unverified:** the event read line's field names (activity.py:167 suggests `operation`), every pixel height, and anything that needs the running window.

**Decisions for the owner:**
- **D1:** Put `files.rename`, `files.copy`, `files.move`, `words.keep` (new names only) and `chains.save` on `HERS_SHOW`, with exact Undo lines and `files.restore` as Trash's Undo. If not, those rows wait for Approve.
- **D2:** Page edits keep the page's Undo (recommended).
- **D3:** The right-click always wears glyphs, even with Words chosen (recommended, per "with right click icons too"). If not, it follows Buttons ▸ Words | Icons like the head menus (tf:228-254).
- **D4:** Make `sort` read numeric text as numbers. This changes existing lines; if declined, the menu adds a step.