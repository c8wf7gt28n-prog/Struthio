# Graphite Visual Pass 1 revision

Graphite 0.2a6.post1 starts from the original Visual Pass 1 archive, Graphite 0.2a6. The five owner images guide this revision. The visual direction is Lain, 2600 and an after-hours hacker's workbench. The portrait belongs to the desk, the command chain reads like a circuit and the evidence stays legible while you work.

## The five references

The original images ship in `docs/BOSS_visual_references`. The program captures ship in `docs/BOSS_worksheet_captures`. `Graphite_Workshop_Cascade.png` and `Graphite_Workshop_Compact.png` show the earlier Pass 1 for comparison.

| Reference | What changed from Pass 1 | Where the running program follows its own data |
| --- | --- | --- |
| Workshop Stock, portrait composition (`workshop-stock-portrait.jpeg`) | Wider result rail. Large inked operator under the bordered result. Bigger ASCII bracket below the files. A real dashed amber route leaves the selected rows, bends to the open cascade and joins the outlined chain. | The header shows the actual editable path. The cascade shows the commands that apply to the current rows. Run chain produces a CSV and source receipt. |
| Workshop Stock, panoramic banner (`workshop-stock.jpeg`) | Explicit steps in the left rail, a sharper grid, heavier active rules and a green confirmed total. The selected cells carry both a mark and a visible color change. | Steps follow the worksheet's open, select, preview and save states. The existing Keep as a method action lives in the chain menu. |
| Workshop Stock, task progress (`workshop-stock-task-progress.jpeg`) | The containing folder has the active sheet, related files and a task ladder. Save stays visible beside the four stages. Source identity and output sit in separate parts of the preview rail. | A prepared result and a saved result use different labels. The original workbook is used as an input. An external change clears the old preview and prompts a reload. |
| Material Comparison (`material-comparison.jpeg`) | PDF review now puts the selected PDF crop beside the editable candidate rows. The amber line begins at the original words and ends on the selected candidate. The current unit and condition read out above the grid. | The link comes from the actual page coordinates, including the chosen text layer. Save uses the reviewed candidates and binds the result to that page. This appears in the review dialog. |
| Overnight Investigation (`overnight-investigation.jpeg`) | A halftone masthead, an outlined index and three numbered sections give the journal a hierarchy. Continue sits directly below the next action. | The sections read the investigation's actual findings, open questions and next step. The inspector reflects the recorded state and counts. Checks and attempts remain in the journal. |

## Look and mechanics

| Surface | Earlier Pass 1 | Revised Pass 1 |
| --- | --- | --- |
| Desk frame | Similar side widths and softer boundaries. | Fine cream vertical rules, amber top and bottom seams and a worksheet-specific wider evidence rail. |
| Type | Mono accents mixed into the existing desk. | IBM Plex Mono carries worksheet headings, quantities, context menus, source states, file marks, and journal numbering. Reading views continue to use their reading settings. |
| Color | More subdued amber and green. | Near-black graphite under warm cream. Amber shows the current path, selection and next action. Green is reserved for confirmed values, evidence and live readings. Symbols and state words accompany the colors. |
| Workbook | Even columns and compact result. | Part has more room. Quantities align consistently. The example makes 40 pcs for Bracket A and 22 pcs for Shade, with a combined 62 pcs. A total requires compatible unit labels. |
| Command menu | A source-to-chain trace and a functional cascade. | Native menus with title bars, fine frames and compact spacing. The trace tracks the menu's actual position and rejoins the tray. Selection, preview and commit are separately visible. |
| Left rail | Full cabinet with a small folder strip. | Working folder and task state take the foreground on a worksheet. Cabinet reopens the full tree. Trash remains at the foot and keeps its existing actions. |
| Right rail | A small preview and a smaller portrait. | The result gets a framed card. The portrait fills the space below it, with the source state nearby. Preview, Activity and Sources remain reachable. |
| Writing line | Flat shared line. | Bordered line with an amber submit control for the current mode. Assistant, Terminal and Log stay in one strip. CPU and RAM come from the session. GPU and TXT display readings when available. |

## Artwork shipped in the project

- `branding/boss/preview-operator.webp` is the original Pass 1 halftone portrait. It fills the worksheet rail in Illustrated mode.
- `branding/boss/journal-operator.webp` is the project’s earlier Night Operator artwork, bundled for the journal masthead. `branding/boss/roof-antenna.txt` is a character-cell drawing from the project’s Character Cell Kit and appears in the journal's ASCII mode.
- The worksheet's bracket is drawn from character cells. Invented file marks such as `[=]`, `[#]`, `[@]` and `[*]` identify the workbook, tabular files, text and notes. There are spoken names and complete filenames in the file tree.
- Work → Arrange → Desk artwork switches between Illustrated, ASCII and Clean. The presentation changes while task states, source bindings and command actions remain available.

I chose the large portrait composition for the worksheet and used a strip of artwork in the journal. That gives each view a different silhouette while keeping the same ink, borders, and typography. The running desk uses actual sample records for the captures. The mockups' paths, workstation readings and example revision numbers are illustrative.

## A twenty-minute review of the desk

**Minutes 0–4 · Arrive and find the work.** Start at screenshots 2 through 7. The strong bits are the full path, the native menus and the artwork choices in Work. The initial cabinet still gives the general Concern tree most of the left edge. I'd make opening a project shift the desk into its own small working set, with a quick return to the global cabinet. I'd keep the monospace file marks close to filenames so people can distinguish file types before opening them. The portrait and bracket should tell you which kind of work is in front of you, like illustrated dividers in a physical binder.

**Minutes 4–9 · See and run the chain.** Look at screenshots 1 and 8 through 11, then the compact capture. The amber route ties a row to the work you're about to do. Keeping the preview visible through the cascade lets you judge what a command will do before you commit. I'd give the chain itself a keyboard walk-through, with one key to move through steps and a plain-language explanation under the focused step. I'd also make the saved output open from the receipt with one action. On the compact capture I would keep an eye on the third menu's overlap when the user makes the side panes wider. The final Run control needs to stay discoverable while you're still considering a choice.

**Minutes 9–13 · Trace a number.** Use screenshots 12 and 13. The amber elbow is the best part of the Material Comparison image because it explains where to look when a number needs scrutiny. The running PDF review has that relation and keeps the source on screen while candidates are editable. I'd carry the same interaction into the saved sheet next. Selecting a value there could open the exact passage with the source, page, condition and saved revision alongside. The PDF and comparison could then stay docked during ordinary editing. A question like whether a figure applies at startup should stay visible with its relevant rows.

**Minutes 13–17 · Leave and return to work.** Screenshot 14 shows the simplest journal sequence. What did I learn? What's open? What can I do now? The artwork gives the journal a distinct place to return to. I'd show the source's human-readable filename next to its snapshot address and group past attempts under the question they served. I'd also bring a small real checkpoint summary into the right pane when one is available, with date, record identity and what a resume can actually do. The current investigation has one recorded source and a waiting state. The app can show those records clearly without borrowing the mockup's running-worker indicators.

**Minutes 17–20 · Read the machine and choose the next improvement.** Compare the System screenshot, the worksheet preview and the journal context. I'd carry their state vocabulary across the app. A ready preview, a saved artifact, a worker waiting for input and a stale source each need a distinct label and a clear next action. I would start with the saved-sheet source link. It completes a job that crosses three screens, from seeing a figure in a PDF to defending the value in a sheet. Then I'd extend the project-specific left rail to the journal and report views so moving between those screens feels like staying in the same workshop.

## Observed on this build

Native Qt was captured at 1536 × 960 and 1366 × 768 using a disposable Office. The check selected two ODS rows, opened the real cascade, previewed the 62-piece result, saved a two-row CSV and a JSON receipt, changed and reloaded the source, and switched artwork modes. A real sample PDF fed the candidate review and an editable sheet. The journal used a recorded source, one supported finding and one open question. Physical ThinkPad, live model and Vulkan qualification remain pending.
