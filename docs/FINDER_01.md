# FINDER-01 · the Finder workspace (HATCH AGENT-01, UI-04)

Owner's words (November 5, 2026): "Don't forget that the empty workspace, if nothing is being worked on, is essentially
our Finder window or our Explorer of files on the computer, but mostly done in the Macintosh format. So we have always
information in the workspace. Even if nothing is being worked on, we can see the files that have been selected in the
left-hand column navigation tree."

## What the Finder is

With no document or room open, the centre of Ledger & Slate is a Finder window in the Macintosh shape. The frame does
not change: the left column, the Ledger Head, the typing strip and the right column stay where they are; the Finder
lives in the centre, where Today used to sit alone. Today is still there: it is the Finder's first place.

- **Code**: `workbench/finder_qt.py` (`FinderPage`), hosted by `workbench/empty_workspace_qt.show_home`; the listing
  operation is `ledger.browse` in `workbench/browse.py` (read scope, an observer, cloud-private).
- **`host._empty_home_page`** is the `FinderPage`; **`page.today`** is the existing `TodayPage` (greeting, capture box,
  four cards, the Waiting card's resume rows), unchanged in content. `host.finder` is the same page.
- **Toolbar** (top): back ‹ and forward › over a history of places, ↑ for the enclosing folder, the place's name, the
  view switch Icons · List · Columns, the Hidden word, the Preview word, and Places ▾.
- **Views**: one listing, three faces. *List* shows Name · Date Modified · Size · Kind, sortable by any column with
  folders always first. *Icons* shows tiles with the kind word under the name. *Columns* shows Miller columns from the
  nearest named place down to the current folder; choosing a folder opens the next column to the right; the preview is
  the last column.
- **Preview pane** (right of the listing): a drawn kind glyph or, for an image, a thumbnail read with a bounded
  `QImageReader` (longest side 512); the name; kind, size, modified and created (or "changed" with a note when the
  filesystem does not record creation); for a text under 64 KB the first forty lines, read-only. A folder's preview says
  how many items it holds and how much space its disk has.
- **Path bar** (bottom, where the Mac puts it): one word per segment, each a link to that folder. Under it the status
  line: "23 items · 118 GB available on this disk · observed from this computer". When the folder holds more than 500
  entries the line says "500 of 1,234 items shown" and a second line offers "show up to 2000".

## The places

Today · Files · Ingress · Egress · Workspace · Program · each storage mount. Files is the workspace's Files folder
(`files_service.root`); Ingress is the folder files come in through, read from `receiving.status` (`inbox`) with
`locations.ingress` as the fallback; Egress is `Files / files_service.EXPORTS`; Workspace is the window's root; Program
is the folder Ledger runs from; the mounts come from `ledger.machine`'s storage section. The names are the owner's
(Ingress and Egress: "we're going future"); the folders are resolved through those calls, never by a literal name.

## The left column is the sidebar

Nothing was added to the left column. What the owner selects there decides what the centre shows, while Home is active:

| Selected on the left | The Finder shows |
|---|---|
| the Today row | the Today place |
| a Machine ▸ Storage row (program folder, workspace, a mount) | that folder |
| the Files row, or a Library files row | the Files folder on disk |
| a cabinet project node that names a folder | its folder (no node does today; the hook is honest and idle) |
| anything else | leaves the Finder where it was |

The hooks are small: `navigation_qt.NavigationController.library_selected` (the Library's current row),
`machine_qt.MachinePage.activate` (storage rows) and `cabinet_qt.CabinetPage.clicked`. Each calls
`host.finder.show_place(...)`, which refuses while a document or room has the centre: the Finder never steals the
centre from open work. When the last tab closes, Home returns at the Finder's last place; the Today row (or
`open_destination(host, 'home')`) brings Today back, with the other places still in the history.

## What the Finder never does

- It never lists a folder itself: every listing is `Kernel.dispatch('ledger.browse', …)` with the read principal.
  `ledger.browse` reads the folder once with `os.scandir`, stats only the returned entries, never follows a symbolic
  link (a link is shown as a link, its size is its own), opens no file, writes nothing and starts no process.
- It never creates, renames, moves, copies or deletes. Those remain the Files room's own operations (Trash, versions,
  proposals). The context menu reads Open · Open in viewer · Copy path · Ask Slate about this file, with Show in Files
  and Change it in Files when the entry is inside Files; outside Files it says "Nothing changes here · Files keeps its
  own changes".
- It never keeps a second store. History lives in memory; the last place, view, preview and hidden choices are written
  to `session.state['finder']` through the existing session (a `session.py` default for the key is proposed to the
  integrator so the choice survives a restart).
- It never adds a colour: graphite words, the pencil-yellow folder glyph and selection wash, the eraser-pink underline
  of the words to act on.
- It never runs a model, a job, a worker or a provider. The check holds `Kernel.launch`, `Kernel.submit` and
  `clip._request` and counts zero of each.

## The keyboard

| Keys | Does |
|---|---|
| Enter | opens: a folder descends; a text inside the workspace opens in the editor tab; anything else opens in the viewer |
| Backspace, Alt ↑ | the enclosing folder, with the folder you left selected |
| Space | shows or hides the preview |
| Alt ←, Alt → | back and forward through the places |
| typing letters | selects by name (the views' own type-to-select) |
| double-click | opens, as Enter |
| right-click | the context menu above |

## The bound

`ledger.browse` returns at most 500 entries by default and 2000 at most; `count` is the number of entries the folder
holds after the hidden filter, so the status line can say "500 of 1,234 items shown" truthfully. A folder with more than
100,000 entries is read up to that bound and reported truncated with the count seen. Hidden entries (names beginning
with a dot) come only with the Hidden word on. The text preview reads at most 64 KB and shows forty lines; the image
preview reads a thumbnail of at most 512 pixels on the longest side.

## Decisions recorded for the register

1. **Today is the first place.** The owner's "we have always information in the workspace" is served by a Finder
   that begins at Today and keeps the greeting, the cards and the resume rows exactly as they were; the folders are
   the other places of the same window.
2. **The left column is the sidebar; nothing is added there.** "We can see the files that have been selected in the
   left-hand column navigation tree": selection on the left drives the centre, through three small hooks that act only
   while Home is active.
3. **Read-only by design.** Looking is `ledger.browse`; changing stays with the Files room's operations and their
   Trash, versions and proposals. The Finder writes nothing, not even a cache.
4. **The 500 / 2000 bound**, with a truthful count and the word that raises it, keeps a large folder quick without
   hiding that more exists.
5. **Ingress and Egress** are places named with the owner's words and resolved through `receiving.status`,
   `locations.ingress` and `files_service.EXPORTS`, never by a literal folder name.

## Narrow widths: every word whole (HATCH GRAPHITE-01, G-B, November 6, 2026)

At 1366 by 768 the AGENT-01 and AGENT-02 captures showed the toolbar clipping its words (the place name, "Colur",
"Hidc", "Prev"), the head's menu words clipping at the right ("Gui") and Today's card grid wider than the centre. Now:

- **Toolbar**: the words stay while they fit; under the bar's width the least-used fold into **⋯** in this order:
  Hidden, Places, Preview, then Icons · List · Columns. ⋯ holds the same choices as menu rows (Show hidden files, Show
  preview (Space), Places ▸, View as …), checked and enabled as their words are. The place name takes the room left and
  elides last, whole in its tooltip. A checked word keeps room for its bold face (theme2 draws a checked button at weight
  600, Qt sizes it at 400).
- **List**: Name keeps at least 150 px (at 14 pt, scaled); Kind folds first, then Date Modified, then Size. The preview
  pane shows all three. Date Modified, Size and Kind start at 120, 100 and 180 px at 14 pt and grow with the interface
  (154 px for Date Modified at 18 pt, where its title and "08 Aug 2026" need more than 120); a width the owner drags is
  kept, at every interface size.
- **Path bar**: the folders nearest the place stay whole; the leading ones fold into **…**, a menu of those folders. A
  last folder name too long for the whole foot elides in the middle (whole in its tooltip and in `path_words()`).
- **Columns**: a long name elides in the middle inside its column, whole in its tooltip; a column never scrolls sideways
  (the Columns view itself still does, by design).
- **Preview pane**: in a short window it scrolls down rather than drawing its lines over each other.
- **Today** (shell2.TodayPage, layout only): two columns of cards while two fit at their own width and 320 px each (at
  14 pt, scaled), otherwise one, sharing the width evenly, decided again after every fill; a card row never widens its
  card past its longest word (plain words wrap, a path may break after each "/", a row you open is the same words as a
  wrapping link, and the folder note beside a recent document wraps the same way, so a document five folders deep keeps
  its name a whole link).
- **The Ledger Head** (shell2.TopBar): the menu words fold into **⋯** from the right before they would clip; ⋯ opens the
  same menus. The fold is decided from the room the row can give the words when both end cells give up their slack
  (typebar.holder_widths' own rule), so it never feeds back on itself, and each heading counts at the width the layout
  draws it (its minimum width when that is larger than its size hint); at 1366 and 1280 nothing folds, at 1100 by 700
  Properties and Guide do, and from 1040 to 1400 px nothing scrolls or clips.

`tools/ui_fit.py` measures it: `whole_words(root)` lists every visible label and button whose words are wider than the room
the style gives them (less what an ancestor clips; a wrapped label needs only its longest word; a checked push button is
measured bold; a word squeezed to no width or cut off wholly sideways counts; a List's column titles are measured against
their sections), `regions(window, *parts)` splits the window's findings into the parts a check asserts and the rest, and
`side_scrolls(root, allow)` lists what scrolls sideways. `check_finder_ui` and `check_frame_ui` assert the whole window at
1920 by 1200, 1366 by 768 and 18 pt (captures and JSON in `build/graphite01_ui/fit/`); `check_frame_ui` also sweeps the
head from 1040 to 1400 px. Checked words outside the Finder keep room for the same bold face (`finder_qt.keep_bold_room`,
which applies `bold_room` again after a restyle): the left column's "Cabinet", "Machine", "Settings", "Logical cabinet" and
"Existing views", the right column's "Operations", the face row's words and the strip's selectors. `ui_fit.PENDING` (the
words allowed to fall short, by at most `PENDING_SLACK` px) is empty, so any clipped word anywhere in the window fails these
checks; the reports in `build/graphite01_ui/fit/` list none.

## Evidence

`tests_integrated/test_browse.py` (6 tests) and `tools/check_finder_ui.py` (offscreen, disposable profile, launchers
held; captures and `finder-ui.json` under `build/agent01_ui/finder`). Nothing in this document claims acceptance: the
owner's display and the real host remain open.
