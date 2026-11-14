# Desk acts: Kasandra's hand, the model's tool path and the typing line (map)

## The answer in brief

- **Where the registry goes.** Put it in the window, in a new module with no Qt in it. Don't make desk acts Kernel operations. On Linux the Kernel runs in a separate host process with no window (`host_client.py:158-165`, `engineering_kernel.py:1`). The one Kernel-to-window bridge that exists, `ledger.navigate` / `ledger.open`, only queues a request that the window picks up later (`ledger_control.py:447-456`, `control_qt.py:474-485`).
- **How the hand treats acts.** An act that only navigates is never written to her trail. When the owner types it or a script runs it, her hand doesn't apply: they are the ones acting. An act that changes something names the Kernel line it runs and goes through `SlateFace.stage`, under the hand's rule as it stands today. A small set of owner-only acts is never hers and is never exported. When her own door opens later, I recommend a navigation of hers be offered, not done, while the dial is at Ask first. That needs a new function, `desk_hers`, so `hers()` keeps its tested behaviour.
- **The typed form.** Use the existing "/" line, looked up by exact name before the Kernel lookup. Watch the name: `desk.` is already taken by the Kernel operation `desk.sources.read` (`project_desk.py:42`).
- **Two problems already in the code that matter here.** The console prints key names on screen, and the model's proposals skip her hand today. Details are in section 9.

## 1. Her hand today (`workbench/stacy_hand.py`)

The module has no Qt in it (imports at `stacy_hand.py:24-28`). It decides three things: whether an act is hers to do now, why it asks, and which line takes it back. The window does the rest (`stacy_hand.py:17-22`).

| Piece | What it is | Where |
|---|---|---|
| The dial | `LEVELS` = ask "Ask first", show "Do and show", free "Free hand". Kept in `session.state['stacy_hand']`. A workspace that never chose opens on show. | `stacy_hand.py:30-35`, `129-138`; saved at `session.py:128` |
| `HERS_SHOW` / `HERS_FREE` | Allow-lists of Kernel operation names. Anything not named asks. | `stacy_hand.py:39-42`; rule in `17-20` |
| `hers(place, scope, op, args)` | A Kernel scope `read` is always hers, at every place. At show, only `execute` and on `HERS_SHOW`. At free, `execute` or `approve` and on `HERS_FREE`. Never anything `why_asks` covers. | `stacy_hand.py:150-158` |
| `why_asks` / `ALWAYS_ASKS` / `LEAVES` | Name patterns that ask on every place, with the reason in words. Any argument named address, peer, url, host or recipient also asks. | `stacy_hand.py:46-58`, `141-147` |
| `why_waits` | The words for why an act waits. | `stacy_hand.py:161-164` |
| `UNDOES` / `takes_back` / `guard` | Only `/field.set` (back to the value it had, at a revision) and `/files.trash` (for something she made new, while its guard still holds). | `stacy_hand.py:43`, `193-215` |
| `undo_allowed` / `clean` | When a saved trail is read back, any undo line not shaped like those two is dropped. | `stacy_hand.py:218-238`, `265-275`; `session.py:129-131` |
| Trail | `record` / `trail` / `taken_back`: at most 40 entries `{at, words, line, undo, word, state, guard}`, kept in `session.state['stacy_trail']`. | `stacy_hand.py:33-34`, `241-262` |
| Terminal | `terminal_hers`: one command that only reads, from `TERMINAL_READS`, with no shell characters. | `stacy_hand.py:66-126`, `283-295` |

The tests pin this down. `tests_integrated/test_stacy_hand.py:11-16` checks that a read is always hers and changes follow the dial. `:47` requires every name on her lists to exist in `docs/GRAPHITE_0.1_REGISTRY.json`. `:48-49` requires that a free hand reaches only her list. `test_stacy_hand` is in the release check's focused set (`tools/check_hatch.py:34,47`).

## 2. The window side of her hand (`shell2.SlateFace`)

| Step | What happens | Where |
|---|---|---|
| `stage(title, step, done, asked, word)` | Parses the line with `field_do.call` and works out `mine = asked and hers(level, step.scope, op, args)`. If it is hers, the Approve button is hidden and it runs at once. Otherwise it waits on an amber Approve. The card carries the line (tooltip = the line) and an "in the line" word. | `shell2.py:1991-2030` |
| `run_staged` | `engineering(root).dispatch(op, args, operator())`, then a sentence saying what was done. If it was her act: `takes_back` and `guard`, then `stacy_hand.record`, then `session.save`, then an Undo button where one is allowed. | `shell2.py:2032-2076` |
| Undo | `undo_staged` and `undo_entry` run the undo line once, through `run_line`. `changed_since` checks the guard first. | `shell2.py:2078-2132`, `2167-2187` |
| `show_hand` / `open_hand` / `hand_menu` | The two words under her name, and the menu with the three places plus "What she did…" and "What always asks…". | `shell2.py:1776-1778`, `2134-2148`, `461-488` |
| `say_trail` / `say_always` | The list of what she did, and the list of what always asks. | `shell2.py:2150-2165`, `2189-2198` |
| `say_plan` / `run_plan` | Several changes, one Approve. With `hers=True` there is no Approve, and `run_plan` does **not** re-check `hers()` for each step: the caller must (as `start_asked` does at `2221`). | `shell2.py:2387-2444` |

Who calls `stage`: the Field's `take` and `stage_set` (`field_page.py:324`, `517`), `made_asked` (`shell2.py:2289-2318`) and `started` (`2287`). `field_page._waits` (`236-244`) reuses `hers()` so a row can show "asks first".

## 3. How the model is offered operations today

`workbench/agent_operations.py` has **no** `DIRECT_OPERATIONS`. It provides `validate()` (`agent_operations.py:38-78`), which the Kernel and every gate below reuse. The lists are in `workbench/local_brain.py`. `workbench/brain_link.py` is not a tool path at all: it serves the `links.*` hardware cross-probes (`brain_link.py:1`, `12-20`, `67`).

| Path | Format given to the model | Where |
|---|---|---|
| Local plan (`brain.ask` with mode "plan") | A JSON Schema used for constrained decoding: `{text ≤240, actions: max 3, items: oneOf[{operation: const op, arguments: <schema>}]}`. The same schemas also go into the system text as "Exact available schemas: {op: schema}". Optionally a "Tools chosen…" list of `{operation, scope, why}`. | `local_brain.py:703-747`, `750-769`; `tool_selection.py:143-145` |
| Which operations | `DIRECT_OPERATIONS` (29 operations, 7,266 bytes of schema, measured in a copy of HEAD). With a request message: `CORE_OPERATIONS` plus up to 6 chosen by word match (`RELEVANT_TOOLS`). Page and Programs requests get their own small sets. The comment explains why: the full set does not fit a 2,048-token context. | `local_brain.py:591-611`, `597-599`; `tool_selection.py:94-140` |
| Deliberately not offered | `tool_selection.DENY` includes `ledger.navigate` and `ledger.open`, the existing window-moving operations. | `tool_selection.py:20`; tested at `tests_integrated/test_tool_selection.py:37` |
| Gates on the answer | `checked_plan`: each action's operation must be one that was offered, scopes limited to read and execute (approve only for Programs review actions). Then `validate_actions`: the name must be in `CAPABILITIES` and match its schema. Then `bind_actions`: the name must be in `CAPABILITIES` and the seed must be `VERIFIED_SOURCE_BINDINGS`. | `local_brain.py:772-793`, `947-985`; `stacy_control.py:272-292`; `stacy_language.py:9-36` |
| Cloud provider | One function, `ledger_command {operation enum, arguments_json}`, over every read or execute operation not in `CLOUD_PRIVATE`, within a 36 KB budget. | `stacy_control.py:167`, `295-319` |
| MCP | `tools/list` returns `{name: op with dots as underscores, description: "op · scope scope · kernel schema v1", inputSchema}` for every operation in the principal's scope. | `engineering_cli.py:344-358` |
| What happens to a proposal | It becomes a card with Run and Edit. Run calls `execute()` directly with `operator()`, so it **does not go through her hand**. Only `documents.edit` on the open page applies by itself. | `shell2.py:2668-2704` (2699), `2745-2771`, `2803-2806` |

## 4. The Kernel's registry, and the bridge that already exists

- **`CAPABILITIES`** is assembled from each module's `SCOPES` (`engineering_kernel.py:159-277`): 771 operations. By scope: 396 read, 206 approve, 157 execute, 11 candidate, 1 `repair.review`. There are 113 job tools and 49 settings. The record is `docs/GRAPHITE_0.1_REGISTRY.json`, release "Graphite 0.8.1".
- **Schemas** come from `engineering_cli.schemas()`. Every entry is `{type: object, properties, required, additionalProperties: False}` (`engineering_cli.py:276-306`).
- **`Kernel.dispatch`** rejects unknown or missing parameters, runs `validate`, checks scope, then records `activity.record REQUEST_RECEIVED`, `instruction_matrix.observe`, `audit` (`activity.append`) and `work_trail`. It returns `{ok, result, correlation_id}` or `{ok: False, error: {code, message}}` (`engineering_kernel.py:487-547`, `393-403`).
- **`tools/record_registry.py`** writes the record. The release check compares the live tree with it, and any difference is FAILED until the record is rewritten (`record_registry.py:1-16`; `check_hatch.py:234-249`; `tests_integrated/test_release_check.py:121-126`; also `test_machine.py:184-187`).
- **The seed** binds `engineering_kernel.py`, `engineering_cli.py`, `ledger_control.py`, `local_brain.py`, `shell2.py`, `typebar_qt.py` and `console_qt.py` by hash (`stacy_foundation.py:42-44`, `114`, `121`, `135`, `159`, `167`). It writes one `operation:<op>` record per operation (`stacy_foundation.py:553-557`). `stacy_hand.py` is not a seed input (checked in a copy of HEAD). If the seed is STALE, lines are refused (`stacy_language.py:9-13`) and Programs proposals expire (`shell2.py:2713-2718`). The release check reads that state as `EDITED_SOURCES_NOT_YET_PACKAGED`, and packaging rebuilds the seed (`check_hatch.py:262-270`).
- **The existing bridge.** `ledger.navigate {destination enum}` and `ledger.open {path}` are execute-scope Kernel operations (`ledger_control.py:19-22`, `42-47`). `queue_desktop` stores a "presentation intent" under `ledger.ui.<id>` as `PENDING_DESKTOP`; its own note says "queuing is not completion" (`447-456`). The window's 750 ms `tick` runs `navigation()[destination]()` or `open_document` and acknowledges the request, which writes an activity event; a request expires after 30 s (`control_qt.py:146`, `150-157`, `468-485`; `ledger_control.py:465-472`). The window also publishes `ledger.desktop_context` (surface, workspace, selection, active file) on each tick (`control_qt.py:431-466`). There is no destination for the Field.

## 5. Desk act as a Kernel operation, or as a window registry: what breaks

| | As Kernel operations | As a window registry (recommended) |
|---|---|---|
| Can it drive the window? | No. The Kernel has no Qt and is out of process. It can only queue intents that complete later, and scripts would have to poll `ledger.desktop_request` (`ledger_control.py:529-532`). Read-back is limited to `desktop_context`. | Yes. It runs on the GUI thread and answers at once. |
| Registry and release check | 771 grows, the schema digest changes, and the registry section FAILS until `record_registry.py` is rerun and its diff reviewed. | Unchanged. |
| Seed | The edited `engineering_kernel` / `cli` / `ledger_control` make the seed STALE, so it must be rebuilt. New operations also enter the seed's records and the model's seed excerpts (`local_brain.py:860-863`). | Editing `shell2`, `typebar_qt` and `console_qt` stales the seed anyway, and packaging rebuilds it. A new module is not a seed input unless it is added to `SEED_FILES`. |
| Who can reach it | MCP `tools/list` (`engineering_cli.py:344-358`), the PWA and the CLI. Word matching would pick acts unless they are added to `DENY`. `provider_plan` would offer read and execute acts to a cloud model unless the prefix goes into `CLOUD_PRIVATE` (`stacy_control.py:305`). | Only the window and scripts. Acts cannot be offered by accident: `checked_plan`, `validate_actions` and `bind_actions` all refuse any name that isn't a Kernel operation. |
| Her hand | Execute-scope acts ask until someone puts them on `HERS_*`, and `test_stacy_hand.py:46-49` applies. Read-scope acts never ask. | `hers()` needs a scope. Use `read` for navigates; for changes, use the scope of the Kernel operation the act runs. Nothing new goes on `HERS_*`, so `test_stacy_hand.py:47` holds. |
| Receipts | Automatic: `work_trail` (non-read only, `work_trail.py:72-75`), journal, audit, matrix. | None for free. Each act calls `activity.record` itself (§7). Changes still get the Kernel's own receipts because they dispatch. |
| Undo lines | — | `field_do.call` / `run_line` send any "/" line to the Kernel, which answers "Unknown operation" (`field_do.py:46-53`; `engineering_kernel.py:496-497`). `undo_allowed` and `clean` drop any undo that isn't one of the two. So a window-only change needs its own undo check; navigations have no undo. |
| Tests that count operations | `test_tool_atlas.py:28` and `test_explore.py:95` compute their counts, so they still pass. `test_tool_selection.py:37,43` need the new names in `DENY` or kept out of the direct set. | None affected. A new test file must be added to `FOCUSED_MODULES` (`check_hatch.py:34`). |

## 6. The typing line

**How a line runs:**

1. Keys: `OneBox.keyPressEvent` (`shell2.py:1042-1063`).
   - Ctrl+Enter calls `TypeBar.ctrl_enter` (`typebar_qt.py:385-413`).
   - Enter while the Log is chosen calls `log_enter`.
   - Typing `@ / ? $` into an empty line jumps to that target (`shell2.py:1048-1052`; `JUMPS` at `typebar_qt.py:37`).
2. Enter: `TypeBar.eventFilter` sends Web lines and lines that are only an address to the browser (`typebar_qt.py:707-712`). Otherwise `returnPressed` calls `ResultsPopup.activate_current`, which runs the first row of `results()` and clears the box (`shell2.py:1004`, `1293-1304`).
   - A "/" line gives a row that calls `to_console(host, 'kernel', text)` (`shell2.py:1019-1027`, `1098-1102`).
   - Plain words give a row that calls `shell2.ask`, which calls `SlateFace.ask` (`shell2.py:1107`, `3560-3561`).
   - `SlateFace.ask` tries, in order, `own_word`, `start_asked`, `made_asked`, `set_asked`, `run_asked`, then a what-if or thing question, then `direct_request`, then the model (`shell2.py:2542-2619`).
3. The arrow (`submit_line`, `typebar_qt.py:423-433`): Web or an address is opened in the browser; Log filters; with Stacy chosen and a line that reads as a line (`READS`, `46`), it runs like Ctrl+Enter; anything else acts like Enter.
4. `to_console` sets the console mode and **opens the working area** (`shell2.py:1208-1216`). An approve-scope operation waits for a second Enter and the line goes back into the box (`shell2.py:1217-1218`; `console_qt.py:502-505`). Changing the console page forgets a pending approval (`shell2.py:1213`; `console_qt.py:238`).
5. `Console.run_kernel` (`console_qt.py:479-508`):
   - Reserved first words: `help`, `ops`, `history`.
   - `parse_command` reads either `{json}` or `name=value` (`console_qt.py:67-81`).
   - An unknown name is refused with "no operation named X" plus near names.
   - The echo is `graphite › <text>`. A refusal is `refused(...)`, the word "refused" on the eraser colour (`console_qt.py:442-443`).

**The five targets.** `MODES` (`typebar_qt.py:26`): slate (shown as `named('Stacy')`, so Kasandra in her appearance, `:29`), shell = Terminal, find = Search, web = Web, log = Log. `set_target(key, focus)` chooses one and saves it in `session.state['type_target']` (`typebar_qt.py:279-302`; `session.py:208-209`). Hints name no key (`typebar_qt.py:38-45`; `shell2.py:987-991`). Putting words in the line is `context_menu.inspect_in_line` (`context_menu.py:225-235`). Changing the room's size is `ExpandButton.step` and `console.set_size` (`typebar_qt.py:177-178`).

**The cleanest place for a typed desk act:**
- **Canonical form: `/<act name> {json}` (or `name=value`), on the existing "/" door.**
  - In `run_kernel`, after `parse_command` and before the `CAPABILITIES` lookup at `console_qt.py:499`, look the name up exactly in the desk registry.
  - Echo `graphite › /…` like any operation. Refuse with `refused(...)` in the same shape.
  - Extend `help NAME` and `ops WORD` to list acts with their mark ("navigates" or "changes"), and extend Tab completion (`console_qt.py:351-354`), so the machinery is one move away.
- **Naming.** `desk.` already belongs to the Kernel (`desk.sources.read`, `project_desk.py:42,69`). "desk" also already means layout (`desk_qt`) and the Field check (`say_desk`, `shell2.py:2360`). Either choose a prefix no Kernel operation uses, or keep `desk.` with exact-name routing. Either way, add a test: no act name in `CAPABILITIES` or in the registry JSON. `capabilities` is a Kernel operation with no dot (`engineering_kernel.py:251`), so prefix checks alone aren't safe.
- **Side effects.**
  - A typed act opens the working area, through `to_console`.
  - An act that writes into the line must refuse when the line holds the owner's unsent words, or when the console has a pending approval.
  - Avoid argument names in `LEAVES` (an argument called "address" makes the act ask) unless the act really leaves the computer.
- **Word form, later.** Slot it after `run_asked` (`shell2.py:2547`), for a small fixed set of phrases. She answers in words, with "in the line" giving the act line, as `stage` and `answer_in_stac` do (`shell2.py:2021`, `1968`). It must not collide with `stacy_control.parse`'s `/open` and "open X" grammar, which serves another room (`stacy_control.py:146-162`; `control_qt.py:494`).

## 7. Receipts today, and one per desk act

| Receipt | What writes it | Where |
|---|---|---|
| Journal (`activity_journal`) | Kernel request received and completed (reads in `OBSERVER_OPERATIONS` are suppressed). GUI events: tab focus, file open, the Terminal. | `engineering_kernel.py:512-513`, `526`; `activity.py:8-33`, `99-107`; `qt_app.py:3309`, `3560`; `console_qt.py:590`, `605` |
| Audit table | `Kernel.audit`. | `engineering_kernel.py:393-403` |
| Work trail | Non-read Kernel operations, with parent nesting. | `work_trail.py:72-123` |
| Her trail | Only her own acts (`card.hers`), at most 40, in the session file. | `shell2.py:2061-2075`, `2348`, `2434`; `stacy_hand.py:241-249` |
| Presentation intent | `ledger.ui.<id>` plus an event on acknowledge. | `ledger_control.py:447-472` |
| Right-click outcome | `host._context_last`, in memory only. | `context_menu.py:2777-2787` |
| Instruction matrix | Run outcomes and Right/Wrong marks. | `shell2.py:2836-2844` |

**One record per act.**
- Write `activity.record(host.root, origin, <act name>, 'DONE' | 'REFUSED' | 'WAITING', detail)`.
  - origin is `desktop-owner` (the owner's word, as `console.shell` uses), `STACY` (as `local_brain.py:588`) or a script origin.
  - detail goes through `redact` (300 characters, local paths removed; `activity.py:39-53`).
- When the act dispatched a change, put the Kernel envelope's `correlation_id` (`engineering_kernel.py:529`) on the event, so the act joins the Kernel's own events.
- Don't journal read-backs, following the "reading is not an event" rule (`activity.py:27`).
- Her trail gets an entry only for her **changes**, through `stage`.

## 8. Recommendation

**Where the registry lives.**
- A new module with no Qt (names, marks, plain words through `named()`, argument schemas shaped exactly like `engineering_cli.schemas` entries, owner-only and asks lists, line parsing, export). Validate with `agent_operations.validate` plus the Kernel's unknown/missing check (`engineering_kernel.py:501-505`).
- Doers that take `host` and import Qt lazily, reusing `open_destination` (`shell2.py:1396`), `set_target`, `inspect_in_line`, `this_is` (`shell2.py:1811-1822`), `context_words` (`typebar_qt.py:639-657`), `choose_appearance(ask=False)` (`boss_qt.py:406-421`), and the menu's `row(key)` (`context_menu.py:2288`).
- Leave `ledger.navigate` / `ledger.open` as the external door for MCP and the PWA.

**How the three doors attach.**
1. **Her model (later): export only.**
   - `tools()` returns rows `{name, mark, words, arguments, asks}`, with a variant form shaped like `local_brain`'s oneOf but keyed `act`, not `operation`, so `checked_plan` can never take an act for an operation.
   - Add tests that no act appears in `DIRECT_OPERATIONS`, in `proposal_profile()` output, in `CAPABILITIES`, or in `tool_selection.relevant` results.
   - Keep each schema tiny (the 2,048-token budget, `local_brain.py:597-599`).
   - Write the hand's rule as data next to `stacy_hand`.
2. **The owner: the "/" line, as in §6.** The owner's typed act runs under the owner's authority, as `/field.set` does today. It is not her act and goes in the journal only.
3. **Tests and the campaign:** `run(host, name, args, by=...)`, returning the Kernel envelope shape (`engineering_kernel.py:528-544`). Read-back acts return data. Mouse-equivalent and key-equivalent paths are two doers under the same name. `by='her'` exists so tests can exercise the dial at each place.

**How her hand classifies acts.**
- **Navigates.**
  - When the owner or a script acts, the hand doesn't apply.
  - For her: hers at Do and show and at Free hand. At Ask first, I recommend it be offered, not done. Today a read is hers even at Ask first because a read is invisible (`stacy_hand.py:20`, `154`), but a navigation visibly takes the owner's window. This is the owner's call.
  - Implement it as a new `desk_hers(place, mark, name, args)` so the tested behaviour of `hers()` (`test_stacy_hand.py:11-16`) doesn't change.
  - Never written to her trail: 40 entries of navigation would push out acts that carry an Undo.
  - Refuses rather than loses anything: unsent words in the line, a pending approval, a page with unsaved edits.
- **Changes.**
  - Each carries its Kernel line. Her act goes through `stage(asked=True)` with `hers()` on that operation and its scope from `CAPABILITIES`; the card, trail entry, Undo and "always asks" follow exactly as today.
  - Owner and script acts press the same control a person would.
  - When batching, check each step before `run_plan(hers=True)`.
- **Never hers, and never exported:**
  - Approve, Run and Undo buttons
  - the hand dial
  - the appearance choice and restarting the window
  - Master Stop and quit
  - the Web target's open (leaves the computer; `typebar_qt.py:361-373`)
  - any Terminal line that isn't `terminal_hers`
  - sending words to her

  `why_asks(name, args)` also runs on every act.

**What must not change:**
- `hers()`'s behaviour, the `HERS_*` allow-list as Kernel names, `UNDOES`, and the `undo_allowed` / `clean` check of saved trails.
- `ALWAYS_ASKS` wins on every place.
- The `Kernel.dispatch` contract, and `operator()` for changes.
- The plan schema and its gates (`proposal_profile`, `DIRECT_OPERATIONS` / `CORE_OPERATIONS`, `checked_plan`, `validate_actions`, `bind_actions`), and `DENY` keeping `ledger.navigate` / `ledger.open`.
- The registry record.
- The line's behaviour: Enter goes to her, "/" runs an operation, the arrow runs a line that reads, the second Enter for approve-scope operations, and the five names.
- The owner's words: no key printed, "a line" (the language is never named), "Apps".

## 9. Problems already in the code (don't copy these strings)

- **Keys printed on screen:**
  - `console_qt.py:504`: "Press Enter again … press Esc"
  - `console_qt.py:495`: "asks for a second Enter"
  - `model_turn.py:258`: "Ctrl Z or “undo” takes it back", in her sentence
  - tooltips at `shell2.py:2020` and `2405`: "in the Field, G does the same"

  A desk-act echo that reuses `console.say` or the stage card would inherit these.
- **The model's proposals skip her hand:** Run calls `execute()` directly (`shell2.py:2699`). This is pending task #35. When the model's door opens, Kernel proposals and acts should both land through `stage`.