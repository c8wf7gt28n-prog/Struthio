# Documents · the shared page (HATCH WORKSHOP-01)

November 5, 2026 · UTC. The first route of the Creative Implementation Commission v2.1's simple demonstration: the owner types a paragraph in the centre, selects words, asks Slate in the typing strip to make them bold, sees the formatting change, keeps typing; saving and reopening retain the result; undo takes Slate's change back like any other. Everything here runs with no model; the model path is unchanged and receives the document and the selection as context.

## Where it lives

- `workbench/documents.py` — the store and the rules. A document is a Project Desk record (kind `document`, schema `ledger.document/1`) in the existing `desk_records`, `desk_history` and `desk_events` tables: a title and ordered blocks, each a paragraph with a style (Normal, Heading1, Heading2, Heading3, Code) and inline marks (bold, italic, underline) over character ranges. Marks are normalised to sorted, non-overlapping runs; overlapping input runs are unioned. Limits: 5,000 blocks, 32,768 characters per block, 2,000,000 characters in all.
- `workbench/document_qt.py` — the page. `DocumentsTab` is a retained room (Hatch ▸ Work ▸ Documents, Explore, the cabinet's action shelf, `ledger.navigate` destination `documents`): a list of saved documents, a yellow title passage, a marks row of pink action words (Bold, Italic, Underline, Heading, Subheading, Minor heading, Body, Code, Plain) and the page, a `QTextEdit` in the prose font with plain paste, a visible selection while the strip has focus, and Return ending a heading. Keys: Ctrl B, Ctrl I, Ctrl U, Ctrl 1/2/3, Ctrl 0, Ctrl `, Ctrl S.
- Filing: `workbench/cabinet.py` lists documents under Documents inside their project (or Unassigned); the cabinet record view shows the page's words; `explore.suggestions` offers the page for ideas, projects and documents.

## Operations (recorded additions)

| Operation | Scope | What it does |
| --- | --- | --- |
| `documents.create` | execute | A new page (title, optional project and plain text); an unnamed page is called by its first words. |
| `documents.list`, `documents.get` | read | Summaries; one document with its events and plain text. |
| `documents.save` | execute | Whole-page save against `expected_revision`; unchanged content is not a revision. |
| `documents.edit` | execute | One bounded change on one selection (`block`, `start`, `end`, quoted `text`): bold/italic/underline on or off, `clear`, `style`, `replace`. Refuses `REVISION_CHANGED` and `SELECTION_CHANGED`; records actor, words and the request in `last_change`. |
| `documents.interpret` | read | The explicit rules over a request's words (with the selected text when there is one). |
| `documents.render` | read | Plain, Markdown or HTML text of the saved revision (the page's Export… writes one of them). |

`documents.*` is private to this computer for cloud proposals; the reads are journal observers, the writes are journalled requests. The `ledger.navigate` destination enum gains `documents` (recorded extension).

## Revision binding

The page saves itself 1.5 s after typing pauses, when focus leaves it, on Ctrl S, before export, before any Slate request and when the tab closes, always with the revision it last saw. Slate's edit names the selection and quotes the words; the store checks both against the saved revision. On refusal the page reloads the saved revision and says so; unsaved words are repeated in the status line so nothing is silently lost. Two pages over the same document cannot overwrite each other (the later save is refused and reloads).

## Slate's turn without a model

`documents.interpret` resolves formatting requests by vocabulary: every word must be a filler, a formatting word, a style word or a negation, otherwise the request is left to the model path. Recognised: bold, italic, underline (and their removal: remove, not, un-), heading / heading 2 / heading level three / title / subheading, body text, code, plain / clear the formatting, replace x with y (narrowed to the words inside the selection). `undo` and `redo` typed to Slate work the page's own undo stack. The answer names the change, the revision, that no model was needed and how to take it back. Anything else: the existing `brain.ask` path with the document and selection as the open item; with no model selected Slate says so and lists the direct edits.

## Evidence

`tests_integrated/test_documents.py` (13 cases: model, rules, store, registry boundary, cabinet filing, the Qt page round trip and a two-page stale save) and `tools/check_document_ui.py` (offscreen: Hatch route, typed paragraph, strip request, bold on the page and in the store, continued typing, close and reopen, one undo stack across Slate's italic / undo / redo / Ctrl Z, the no-model answer, 1366×768, cabinet filing, zero jobs; three captures under `build/workshop01_ui/documents/`). The live-model turn, a real display and the owner host remain open.

## What is next on this route

The model turn (a loaded GGUF proposes `documents.edit` through the plan path and the owner sees it land), Slate writing new paragraphs under an assignment, a DOCX export through the existing office profile, the same binding for spreadsheet cells and selected design objects (WS01 across artifacts), and takeover/resume with retained drafts (WS03, WS04).
