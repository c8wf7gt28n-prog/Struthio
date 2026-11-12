# The second assignment: files about something (HATCH AGENT-02 · WI-C)

November 6, 2026. AGENT-01 gave the resident loop one assignment, numbers on the page. This item adds the second, and the first that needs no page: the owner types **find files about pellets** (or *what documents do we have on the frame*, *which drawings mention the hatch door*) to Slate, with or without anything open, and Slate looks through Files and Ingress, reads the first lines of the best matches and writes a findings page in Documents. The owner's own words choose it; no model is needed for any step, and when a model is loaded it only advises at one choice. Nothing here claims acceptance; the live-model advice and the owner's display remain open.

## How to ask

A verb, a kind of thing, a link word and the topic, in that order (explicit words; `profile_files.fits(words)`; never a model):

- verb: find · look for · look up · look through · search (for / through) · show (me) · list · what · which · do we have · have we got · are there · is there
- thing: file(s) · document(s) · docs · drawing(s) · sheet(s) · spreadsheet(s) after any verb (*are there any files about the brooder*, *what documents do we have on the frame*); *anything* / *something* only after find, look for, search or list, and never with the link *for*
- link: about · on · for · mentioning · mention(s) · called · named · regarding · concerning
- topic: the rest; at least one word that is not a stop word (letters of any script count: *Müller*, *ñandú*, *鸡蛋*). Up to three words may come before the verb (“Slate,” “please”), up to four between the verb and the thing (“me all the”), and *do we have*, *are there* and the like between the thing and the link. Trailing punctuation, quotes and *please*, *for me*, *thanks* are dropped. The owner's own letters are kept for the page title.

A request that points at what is open goes to the model path (which is given the page), wherever the pointing words stand: *this / that / these / those* before page, document, sheet, spreadsheet, drawing, file or one (*search this document for pellets*, *find anything on this page about pellets*, *is there anything about pellets in this file*, *which of these documents is about chickens*), a request ending in *here*, and a search of one page, sheet or drawing (*search the document for the word pellet*, *search the sheet for totals*; *search the files for grit* is still Files). So is a topic that only points (*this page*, *the document*, *it*) or names nothing (*something*). Everyday questions (*is there anything on TV tonight*, *do we have anything for a headache*, *is there something on my calendar*, *show me something about Python decorators*) do not fit. *add up the numbers on this page* is still the numbers profile: `agent_loop.request_profile` keeps the numbers rule first and then asks each registered profile's `fits` in registry order.

## The steps

Each is one registered operation, recorded on the assignment's investigation like every AGENT-01 step.

| key | operation | what it does |
|---|---|---|
| where | `receiving.status {}` | the Ingress folder's path and how many names wait there |
| find | `files.find {text, limit: 20}` | files inside Files whose name or words carry the topic. `files.find` is a plain substring search, so the text is the topic without a leading article and with a plural's ending taken off (*the pellets* → `pellet`, *boxes* → `box`; a word of four letters or fewer stays whole: *news*, *Mars*, *eggs*); a FINDING per match: name · place · size · changed · how it matched |
| find_word | `files.find {text: word, limit: 20}` | only when a topic of several words matched nothing as a phrase: once more with its longest word (*hatch doors* → `hatch`); the findings say “matched “hatch” by name” |
| ingress | `ledger.browse {path: Ingress, limit: 500}` | only when Ingress holds something: names that carry every topic word are a FINDING each, “waiting to be received, not read”. Nothing in Ingress is opened; a file whose word is only inside it is not found there. Nothing in Files and nothing in Ingress: one QUESTION (“Is it spelt differently, or kept somewhere else?”) and the assignment is done with “Found no files about … (looked at N files)”; no page is written. The QUESTION waits for this listing, so a match only in Ingress writes the page and asks nothing; when the listing fails with nothing in Files, the QUESTION is asked with the waiting words |
| read_1, read_2 | `files.get {path}` | the first line of the two best matches (a name match first, then readable kinds, newest first; a copy in Egress last). A table says its columns and rows, a drawing its first text, anything else its kind and facts |
| (choice) | none | while matches remain unread and fewer than four were read: *Write the findings page* or *Read one more match: <name>*, both acceptable. The default is to write; with a model READY `agent_loop.choose_next` asks it, and its pick is taken. Never more than four reads, whatever it advises |
| write | `documents.create {title, text, origin: SLATE}` | the page **Files about <topic>**, its first paragraph the request and the words searched for |
| lines_k | `documents.edit {append}` | one paragraph per match, best first, then Ingress, then “Looked in Files and Ingress on <date> · N matches · read M”; each bound to the revision the previous write returned |
| done | none | “Found N files about <topic>; the findings page is in Documents” and a FINDING with the summary. The page is not opened by itself: the Document word on the Work block's inspect line opens it |

Worst case: 20 matches, 5 names in Ingress, 4 reads and the retry make 35 steps, inside the default budget of 40 (a test checks the arithmetic). A findings page that moved on while Slate wrote it (the owner typed on it) is never merged: the step is refused by the store (`REVISION_CHANGED`), the assignment waits with “Resume writes a fresh page instead of merging”, and Resume writes a new page; the owner's page keeps what Slate had written up to then and the owner's words. With a read-only budget the finding and reading run and the write is refused with the step's words.

## Where it lives

- `workbench/profile_files.py` (new): `fits`, `topic_of`, `needle_of`, `stem`, `topic_words`, the `FilesAbout` profile and `PROFILE`. `needs = ()`. `done(state)` is overridden to finish only when interpret says so (see *Loop order* below).
- `workbench/agent_profiles.py`: registers `profile_files.PROFILE` exactly as `profile_numbers` is registered (UNAVAILABLE says why when the import fails). When `profile_files` is imported before `agent_profiles` (a tool that imports it directly), `agent_profiles` runs in the middle of that import and finds no `PROFILE` yet; `profile_files` then registers itself at its end. A test simulates that import order.
- `workbench/agent_qt.py`, `assign_from_page` only: a fitting request typed with no tab open, or on any tab, becomes an assignment with context `{}` when the profile's needs do not include `document` (the page is not flushed for it); the numbers profile keeps needing a page, and an unknown profile is treated as before (a page). The function's shape, answers and the AGENT-01 test of it are unchanged.

## Decisions

- **Explicit words choose it, no model** (owner decision 6: most steps are local computation; the model only picks among options). The model's only part is the read-more-or-write choice, with the rule default (write) primary, as the AGENT-01 live trial advised for the smallest model.
- **Two reads, then the choice; never more than four.** The plan's “at most four reads” and “options after the reads” agree only when the choice comes before the fourth read; two first keeps the page quick without a model and leaves the model two real choices.
- **Plural endings off, one retry by the longest word.** Without them *find files about pellets* missed `pellet_order.md` in the first trial run; both are still `files.find` reads inside Files, recorded and said on the page (“searched Files for “hatch door”, then “hatch””). A word of four letters or fewer keeps its *s*: cut to three letters (*news* → `new`, *Mars* → `mar`) it matched “needs new felt” and “March budget” and the page said “Found 2 files about Mars”. The cost: *find files about eggs* looks for `eggs`, not `egg`; a false “found” on the page is worse than a QUESTION that invites *egg*.
- **Words of any script.** Topic and Ingress names are split into letters and digits of any script, so *Müller* is not cut to `ller` (which matched “Keller invoice.pdf”) and a topic with no Latin letters fits.
- **Pointing words anywhere in the request, not only in the topic** (reviewer finding, AGENT-02): *search this document for pellets* had become a Files-wide search that wrote a page nobody asked for while the open page went unsearched. D19 keeps the page with the model turn; this profile takes only requests that name a subject and no open thing.
- **Ingress is listed only when it holds something**, and only by name (the plan: Ingress files are listed, not read). An empty or missing Ingress is reported as looked in (receiving.status said it holds nothing).
- **Nothing found: a QUESTION and DONE, no page** (an empty page would say less than the question).
- **The page opens from inspect, not by itself**: the done words say “the findings page is in Documents” rather than “open”, so they stay true when Ledger is closed and the Ledger service finished it (WI-A).
- Commission v2.1: no second dispatcher, scheduler, store or process; reads only (`receiving.status`, `files.find`, `files.get`, `ledger.browse`) plus the two document writes; no acceptance claimed.

## Loop order

Found during this work and integrated (AGENT-02): `agent_loop.step_once` now finishes an assignment by the default rule (the cursor past the plan) only when the step offered no options, so a profile's options after its last planned step are taken, not dropped. The profile still says when it is done itself, so it works either way.

## The right column

The Work block's Found line joins every FINDING; with one per match it reads as a long block at 1920 by 1200 and is cut at 1366 by 768 (captures 02 and 04). The plan asks for a FINDING per match, so the profile keeps them (the investigation sheet and the findings page carry them); the report proposes that the Found line show the last finding and “and N more on the investigation sheet” when there are more than three.

## Registry

No operation is added or removed. `agent.assign`'s `profile` enum is every registered profile, so it gains `files_about`: `['auto', 'files_about', 'numbers_on_page', 'operation_sequence']`. That changes the schema digest; test_machine's `RECORDED_DIGEST` and the shipped counts belong to the integrator. No setting is added.

## Evidence

- `tests_integrated/test_profile_files.py`, 16 cases: fits/topic_of (eighteen fitting requests with their topics, among them *Müller*, *ñandú* and *鸡蛋*; thirty that do not, among them every pointing request and everyday question above, each also checked through `request_profile`), request_profile routing (numbers still first), plural endings and words (four-letter words whole; *Müller* not `ller`), registration whichever module is imported first, the profile in `agent.assign`'s enum and the worst case inside the budget; on a disposable workspace (Files with matches by name, by words, a table, a copy in Egress and non-matches; Ingress with a match by name, a non-match, a match only inside a file and a hidden file) through `agent.assign` + `agent.run` with `ask_model` patched: DONE, the findings page's seven paragraphs, the eight findings, the CHOICE row “no model loaded; default taken: Write the findings page”, every operation in the allowed set, every `files.get` inside Files, `ledger.browse` only on Ingress; the model advising “read one more” every time (`ask_model` / `model_answer` patched) stops at four reads with two MODEL_CHOICE rows; nothing found; a match only in Ingress (page written, nothing in needs_you); nothing in Files and the Ingress listing failing (the QUESTION held back until then, then asked); *news* searched whole (not `new`); the longest-word retry; no Ingress listing when Ingress is empty; the moved page and a fresh page on Resume; a read-only budget; `assign_from_page` with no tab, on a page (context `{}`, not flushed), *search this document for pellets* on a page (None: the model path), the numbers request with no page (None), and a request that fits nothing (None). Kernel.launch, Kernel.submit and clip._request held; zero jobs.
- `tools/check_files_about_ui.py` (offscreen; `ARC_LEDGER_FILES_ABOUT_CAPTURE_DIR`, default `build/agent02_ui/files_about/`; JSON `files-about-ui.json`): seven checks — no tab open; “find files about pellets” typed in the strip with key events becomes a files_about assignment with context `{}` and Slate says “Working on it”; after two driver steps the Work block reads running and “Listing Ingress by name (step 3 of 5)”; the driver works it to DONE between events (12 steps, one CHOICE, reads inside Files only, the Ingress listing only); the Document word on the inspect line opens the findings page (revision 7, seven paragraphs, the roof note, the receipt and the scan absent); 1366 by 768; zero jobs, launches, submissions, provider requests and processes, no model. Captures `Ledger_Slate_AGENT_02_FilesAbout_01_Running_1920.png`, `_02_Done_1920.png`, `_03_Page_1920.png`, `_04_Compact_1366.png`.
- Reruns: `tools/check_agent_ui.py` (redirected with `ARC_LEDGER_AGENT_CAPTURE_DIR`) PASSED, 13 checks, 5 captures; `tests_integrated.test_agent_loop`, `test_related` and `test_conditions` green.

## Open

- The live model's advice at the choice (the loop's model path is patched in the tests, as in AGENT-01).
- The Found line and the loop-order change proposed above.
- `files.find` reads a file's words only for text kinds up to 2 MB; PDFs and office documents are found by name only.
- Owner display, owner host, acceptance: not claimed.
