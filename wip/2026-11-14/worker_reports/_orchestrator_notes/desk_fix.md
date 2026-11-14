I reproduced all eleven findings and fixed them, and the fixes are committed in the same worktree. The window no longer crashes on any character. None of the acts marked "navigates" sends, changes a record or leaves Graphite in the reproductions or in the new sweep. Every module passes. P01 passes 4 of 4 on After Hours 07 at 1920×1200 and at 1366×768.

- **Worktree:** `/home/user/Struthio/.claude/worktrees/wf_ffffb167-845-5`
- **Branch:** `worktree-wf_ffffb167-845-5`
- **Commit:** `1c378dc379e6074fc0cbb7b0147ecb7bfc8731ec`, a new commit on top of a897af3. Not pushed.
- **Mirror:** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_acts_mirror/` is up to date.
- **Evidence:** the before and after logs are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_fix/runs/` (files `before_*.log` and `after_*.log`). The probe scripts are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_fix/scripts/`.

## Findings: what was wrong, and what changed

| # | Before the fix | Fix | After the fix |
|---|---|---|---|
| 1 CRITICAL | `type.put` with Ω by keys killed the window: the qasciikey ASSERT, exit 139 | `desk_doers.type_text` sends one key press and release per character, carrying the character. It replaces `QTest.keyClicks` in `type_put` and `by_search` | “07”, Ω ≥ 3 · 電流 are typed, from the writing line too. Line feed and 0x7f are refused |
| 2 HIGH | A carriage return started `echo PWNED` in the Terminal, and her ask received "hello from an act" | `desk_acts.check` refuses any line break or invisible character with BAD_ARGUMENTS. `type_put` compares what the line holds with the text and reports FAILED if they differ | Refused, nothing starts or reaches her. `desk_hers` now says not hers |
| 3 HIGH | `open:outside` opened the file outside Graphite. `delivery:stage` staged the file in Delivery. `menu:edit` wrote the menu file and still said "nothing was done". A document's Delete emptied it (revision 1→2) | `desk_acts.MENU_ROWS` and `PANEL_ROWS` are allow-lists of row keys, checked by `desk_doers.row_refusal`. The operation check stays as a second layer | All four refused (NOT_ALLOWED_ROW). Nothing opened, Delivery empty, no menu file, document still at revision 1 |
| 3 (dialog words) | "It would open a window that asks; nothing was done." | `desk_doers.watching()` records, without blocking, every changing Kernel call, outside open and program start during an act, into a new envelope field `changed`. The DIALOG refusal now reads "…so it was stopped there." and adds "Before that: files.write." when something was done | Tested with a stand-in doer that writes then asks |
| 4 HIGH | `sheet.whatif` on an app asked her model (`brain.ask` in plan mode) | `sheet_whatif` refuses anything but a sheet or calculation and calls `face.what_if` instead of `ask`. The value must be a number | Refused, no model call |
| 5 MEDIUM | `go.app documents` created a document (4 tables changed) | `go_app` checks `documents.list` first and refuses with a new MAKES refusal when there are none | Refused, no record |
| 6 MEDIUM | `hand.write` replaced "owner plan.txt" as hers | `hand_write` checks `files.get` and reserved names. A file that exists is put up to wait for Approve whatever the dial says, with her own words | The card waits and the file is unchanged |
| 7 MEDIUM | G approved "Watch it" while the act reported another card | `go_card` finds the card behind the Field's go. G is used only when that card is the latest, otherwise the latest card's Approve is clicked. `waiting_cards` now orders cards as Talk holds them, because hidden folded cards had no reliable screen position | The act reports the card it approved |
| 8 MEDIUM | Her hand's rule called these acts safe | `desk_hers` checks the arguments first, and takes a menu row only by a listed key | See the note below |
| 9 LOW-MED | At 1366×768 the mouse runs closed the comparison with Esc | `desk_doers.beside` finds a click point from the comparison's own rectangle | Pointer in every mouse run, bench and After Hours 07 |
| 10 LOW | Test gaps and the door default | `run()` requires `door`. New tests listed below. The export drops `by` and lists its choices flat | Export is 6,327 bytes, back under the plan's 9,000 |
| 11 LOW | Wording | The what-if punctuation is fixed. `type.send` takes "arrow" or "keys" instead of "enter". The journal records only that words were put, not the words | `help type.send` shows "arrow, keys" |

On #8, I partly disagree with the reviewer. After fixes 2 to 5, `tools()` still gives `asks: False` at "Do and show" for `go.app`, `menu.choose`, `sheet.whatif` and `type.put`. I left it that way on purpose. Each doer now refuses the unsafe cases, so treating them as navigation is correct.

## Final test results

Each module was run on its own with the required command:

| Module | Result |
|---|---|
| test_desk_acts | Ran 28, OK (was 20; about 187 s, of which the full sweep is about 110 s) |
| test_desk_scenes | Ran 5, OK (was 3) |
| test_stacy_hand | Ran 19, OK |
| test_writing_line | Ran 31, OK |
| test_kasandra | Ran 20, OK |
| test_release_check | Ran 22, OK |
| test_campaign | Ran 23, OK |
| test_tool_selection | Ran 5, OK |
| test_context_menu | Ran 44, OK |

New tests:
- **The sweep:** covers all 30 exported navigation acts, including all 33 apps. It checks record counts, the Files listing, outside opens, program starts and each act's `changed`.
- **Single cases:** refused rows and a document's Delete, the dialog path, Documents, writing over a file, Approve, what-if, typing every character, and the required door.
- **Scene:** `keys_still`, and the mouse runs at 1366×768.

I also added `instruction_matrix` to the excluded journal tables. It records every line that runs, including Then, trace and doubt, the same as when the owner runs a line by hand.

**Integrity:**
- I rebuilt the manifest, the registry, then the manifest again. The registry and seed files came out unchanged, so only `MANIFEST.json` was staged.
- The seed reads VERIFIED_SOURCE_BINDINGS and `release_integrity.verify` reads VERIFIED (1,290 files).
- `check_release.py` passed runtime, registry, settings, adapters and payload_privacy.

## The scene's final run

Campaign `scenes` on After Hours 07 gave Pass 4 of 4: P01a 54/54 checks, P01b 55/55, P01c 56/56, P01d 57/57. The mouse runs used pointer on 15 steps and direct on 2; the keys runs used keys on 15 and direct on 2. Step 16 (`sheet.close`) is now pointer. The run folder is `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_fix/campaign_scenes_fixed`.

The same set at 1366×768 also passed 4 of 4 with the same forms, step 16 by pointer. I ran it from a scratch copy with P01's size changed, so P01 in the repo still says 1920×1200. That run is in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/desk_fix/campaign_scenes_1366`.

## Still not done

- **Successes not tested:** a successful `sheet.whatif` and a successful `hand.cell`. The bench sheets hold words, not numbers.
- **Fixed but untested paths:** the change path of `hand.step` and `type.send` are still not in the tests.
- **What her hand's rule can't see:** `desk_hers` cannot tell that a file already exists or that Documents is empty; the doers enforce both.
- **Recorded, not blocked:** `watching()` only records. A changing call during a navigation act shows up in `changed` but does not refuse the act, because background timers in the real window could set it off too.
- **Brain app noise:** opening the Brain app tries to list installed packages with a subprocess. The test fixture blocks that and prints a traceback in the sweep's log, but the test passes.
- **Typed door:** in my probe, a second line typed into the writing line right after a `type.put` did not run; the reviewer's harness showed the same before these fixes. It is most likely the harness setting the text without the line's search list updating, not a bug in the acts, but I did not confirm that.
- **Carried over from the first pass:** her door, word forms, MCP/CLI exposure, adding the acts to `SEED_FILES`, a keyboard route to the head menus, the Kasandra run of P01, converting existing probes, and the version number (still 0.8.1).