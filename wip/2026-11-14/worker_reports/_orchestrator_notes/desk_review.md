**Desk acts (a897af3) review: five safety problems, and one act crashes Graphite**

The scene passes every run at both sizes, the release check passes, and no existing test regressed. But one act, reachable from the writing line, crashes the whole window. Five acts marked "navigates" do send, change, write or leave Graphite. I fixed nothing.

I worked in the review copy `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_review/tree`. My probes are in `.../desk_review/scripts/` and their logs in `.../desk_review/runs/`. Each probe builds the bench window from `test_desk_acts.build_window` and records `QDesktopServices.openUrl`, `QProcess.start` and Kernel dispatches.

## Findings, most severe first

### 1. CRITICAL: `type.put` by keys aborts Graphite
- **Where:** `desk_doers.py:1102` sends the text with `QTest.keyClicks(box, text)`.
- **Cause:** With the pinned PySide6 6.8.3, any character outside Latin‑1 kills the process: `ASSERT: "false" in qasciikey.cpp, line 192`, then SIGABRT (exit 134). That covers the curly quotes Graphite uses everywhere (“07”), Ω, ≥ and CJK. Line feed, 0x01 and 0x7f do the same.
- **From the writing line:** `probe3.py` typed `/type.put text=“07” by=keys` the owner's way, setText and Enter. The window died (exit 139); the log ends at that ASSERT.
- **Evidence:** `runs/probe3.log`, and `scripts/keyclicks.py`, which reproduces it in isolation.
- **Fix:**
  - Never send free text through `keyClicks`. Send one `QKeyEvent(KeyPress, 0, NoModifier, ch)` per character with `QApplication.sendEvent`.
  - Refuse control characters as BAD_ARGUMENTS.
  - Add a test that types “07”, Ω and a line feed.

### 2. HIGH: `type.put` (navigates, exported) sends, bypassing `type.send`
- **What happens:** A carriage return in the text, by keys, is a Return in the writing line.
  - Terminal: the probe recorded `QProcess.start ['-l','-c','echo PWNED > pwned.txt']`.
  - Her: her ask received `'hello from an act'`.
- **The read-back hides it:** "The writing line holds: " with `text: ""`.
- **The guard it skips:** owner-only `type.send` and its LEAVES_OR_SHELL rule.
- **Her rule agrees it is hers:** `desk_hers('show','type.put',{'text':'rm -rf x\r'})` gives `(True,'')`.
- **Evidence:** `runs/probe_safety.log` (A2, B2), `runs/probe6.log`; code at `desk_doers.py:1094-1106`, `desk_acts.py:130`.
- **Fix:** Refuse any Cc character in `check`/`type_put`. After typing, compare `box.text()` with the text and say FAILED when they differ. Add a test with a carriage return.

### 3. HIGH: `menu.choose` lets through rows that change, write or leave
The guard (`changing_row`, `desk_doers.py:357-365, 407-409`) reads only `Entry.operation`, `caption` and `asks`. Rows that name no operation pass.
- **(a) A saved document emptied.** Every step was an act: `go.app documents`, then `menu.open on=here by=keys`, `menu.choose edit:all`, `menu.open`, `menu.choose more/edit:delete`. The autosave then ran `documents.save`: revision 1→2, text "". There was no card, no trail entry and no Undo. The act said "Chose more/edit:delete." Rows at `context_menu.py:422-430`; autosave at `document_qt.py:397-408`. Evidence: `runs/probe5.log`.
- **(b) Leaves Graphite.** `more/open:outside` called `openUrl('file:///…/seed/07 Bench readings.csv')` (`context_menu.py:614`, `files_qt.py:419`). Combined with `hand.write`, which is hers at Do and show, this could open a written file with the computer's own app; I did not try it. Evidence: `runs/probe_rows.log`, `runs/probe4.log`.
- **(c) Delivery list changed.** `more/delivery:stage` left the Delivery list holding `{'seed/07 Bench readings.csv': None}`.
- **(d) A false "nothing was done".** `more/menu:edit` wrote `Concern/Ledger menu` (`chain_menu.py:498`). The act was then refused DIALOG with "It would open a window that asks; nothing was done." The probe's diff shows the new file. Evidence: `runs/probe4.log`.
- **Fix:**
  - Replace the deny-by-operation guard with an allow-list of row keys, as `HEAD_ROWS` already is for the head menus.
  - In the DIALOG path, compare state before and after the act and stop saying "nothing was done" when something was.
  - Extend test 11 with a sweep over these rows.

### 4. HIGH: `sheet.whatif` asks her model and says nothing happened
- **Where:** `desk_doers.py:1057-1062` calls `shell2.ask('what if …')`.
- **Cause:** When the selected object is not a sheet or calculation (an App, for example), `what_if` returns None. The ask then falls through to `brain.ask` in plan mode.
- **Evidence:** `runs/probe_safety.log` F3 recorded `brain.ask {"message":"what if B3 were 300\n\n(About the open item: Delivery)","mode":"plan"…}`. The act reported "Nothing would move.; nothing is changed."
- **Fix:** Refuse unless the selected kind is sheet or calculation. Call `face.what_if(text)` or `field.ripple` directly rather than `ask`, and refuse on None or a refusal.

### 5. MEDIUM: `go.app documents` creates a document
- **What happens:** When no document exists, `DocumentsTab.__init__` calls `new_document`, which runs `documents.create` (`document_qt.py:322-331`).
- **Evidence:** `runs/probe4.log` shows `desk_records 0→1`, `desk_history 0→1`, `desk_events 0→1`, `ledger_trail 9→10`.
- **Fix:** Refuse or pre-check `documents.list`, and add `go.app` to the never-changes test.

### 6. MEDIUM: `hand.write` writes over the owner's file as hers
- **What happens:** At Do and show, writing over an existing `owner plan.txt` gave `ran:true, hers:true, undo:""`; the file now reads "Replaced by an act."
- **Her own path refuses the same thing:** "There is already something called “owner plan.txt” in Files. I do not write over what is there by myself" (`shell2.py:2314`).
- **Evidence:** `runs/probe6.log`; code at `desk_doers.py:1128-1132`.
- **Fix:** Call `files.get` first; when the file exists, refuse or make the change wait.

### 7. MEDIUM: `hand.approve` by keys reports a different card than it approved
- **What happens:** Pressing G approved the Field's go ("Watch it"). The act then read `cards[-1]` (the later `hand.write` card). It returned `ok:true`, "It was refused: nothing changed.", `ran:null`, while "Watch it" left the waiting list.
- **Evidence:** `runs/probe3.log` d5–d7; code at `desk_doers.py:1181-1195`.
- **Fix:** Approve and report the card behind `page.pending`, or use G only when that card is `cards[-1]`.

### 8. MEDIUM: her hand's rule and the export call unsafe acts plain navigation
- **What it says:** `desk_hers` returns True at Do and show for `type.put` with a carriage return, for `menu.choose more/open:outside` and for `sheet.whatif`. `tools()` gives `asks: False` for `go.app`, `menu.choose`, `sheet.whatif` and `type.put`.
- **Evidence:** `runs/probe6.log`; code at `desk_acts.py:258-295`.
- **Fix:** After fixing 2–5, add per-act argument rules to `desk_hers`. Make the test sweep every exported navigation, checking record counts, process starts and `openUrl`.

### 9. LOW-MEDIUM: at 1366×768 the mouse runs press a key
- **What happens:** In both mouse runs (`mouse` and `mouse_still`), `sheet.close` (step 16) falls back to Esc (`by=keys`). This holds on the bench seed and on After Hours 07 (campaign P01a/P01c). At 1920×1200 it is `pointer`.
- **Why the tests miss it:** `test_p01_by_mouse` checks pointer-only at 1920×1200 only.
- **Code:** `desk_doers.py:1037-1051`.
- **Fix:** Derive the click point from `_rev_rect` (a body point outside it and off `_hot`), and add a 1366×768 test.

### 10. LOW: test and robustness gaps
- `run()` defaults to `door='script'` (`desk_doers.py:1274`). A future caller that forgets `door=` gets the owner-only acts. Make the door required.
- Test 11 covers 11 acts. It leaves out `go.app`, `menu.choose` rows, `type.put`, and Then, trace and doubt (each of those adds an `instruction_matrix` row).
- `test_desk_scenes` never plays `keys_still`.
- Test 20 does not check that the acts succeeded.
- `plan_variants()` is 10,940 bytes. The plan's target was 9,000 and the builder raised the test bound to 11,000. `local_brain.py`'s own notes say 6,800 characters of schemas already exceed a 2,048-token context.

### 11. LOW: words
- `sheet.whatif` prints "Nothing would move.; nothing is changed." (`desk_doers.py:1062`).
- `help type.send` prints the key name "enter" as an argument value (`desk_acts.py:131`).
- `type.put` writes the line's words into the activity journal.

## What holds
- **Her door:** `door='her'` is refused with NOT_OFFERED. No act is a Kernel name, and none is in `DIRECT_OPERATIONS`, `CORE_OPERATIONS` or any proposal schema.
- **Kernel changes:** they go through `stage(asked=True)`. What always asks still asks; `hand.rename` waits at Do and show; Undo and the trail work.
- **Rows that do declare an operation:** trash, rename, copy, move, versions, export, agenda, investigate, and pausing or stopping jobs and Agenda work are refused with CHANGES_ROW.
- **Dialogs:** the "ask" rows are refused with DIALOG and no modal window stays open.
- **Head rows:** the `HEAD_ROWS` allow-list holds, and none of those rows changed a record in the sweep.
- **The typed door:** apart from the crash, it does no more than a person can by hand. Two differences: `look.set appearance` skips the restart question (harmless), and a typed `hand.write` is recorded as hers.
- **Blocking:** in about 250 act runs nothing blocked or left a modal window open. The abort in finding 1 is the only hang-or-crash.
- **The scene, P01:** it passed all four runs (mouse, keys, mouse_still, keys_still) at 1366×768 and 1920×1200, on the bench seed (`runs/scene_*.log`) and on After Hours 07 through the campaign (`runs/campaign_scenes`, `runs/campaign_scenes_1366`). That is 16 of 16, with the CSV taken back each time. The only blemish is finding 9.
- **Words:** no act word or refusal names the line language or says Programs; `key_literals` is clean; the command search prints no key.
- **Release:**
  - `check_release.py` passed runtime, registry, settings, adapters and payload_privacy.
  - The seed reads VERIFIED_SOURCE_BINDINGS, and `release_integrity.verify` reads VERIFIED (1,290 files). The version is still 0.8.1.
  - The new files are in `MANIFEST.json`, and `FOCUSED_MODULES` lists both new test modules.
- **Existing tests:** each module run on its own matches the builder's numbers:

| Module | Result |
|---|---|
| test_desk_acts | Ran 20, OK |
| test_desk_scenes | Ran 3, OK |
| test_stacy_hand | Ran 19, OK |
| test_writing_line | Ran 31, OK |
| test_kasandra | Ran 20, OK |
| test_release_check | Ran 22, OK |
| test_campaign | Ran 23, OK |
| test_tool_selection | Ran 5, OK |
| test_context_menu | Ran 44, OK |

  `test_desk`, `test_graphite` and `test_paper` fail with the same 6, 3 and 4 failures on 1f59293 and on this pass (`runs/both.txt`).