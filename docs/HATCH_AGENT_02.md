# HATCH AGENT 02

November 6, 2026 · UTC

Complete checkpoint over AGENT-01 under the Creative Implementation Commission v2.1. The owner approved the next pass, the three items named at the end of AGENT-01: work that continues while Ledger is closed, on the same record; Slate's model turn applied to a real page; and a second assignment. All three are built, checked offscreen, independently reviewed and fixed; the resident service and the small models were also run live in the build container.

## Work that continues while Ledger is closed (D29, docs/CONTINUE_01.md)

The resident Ledger service (Hatch ▸ Ledger services ▸ On) already ticks every five seconds for continuing work. That tick now also calls `agent_loop.pump`, which steps a running assignment that no desktop is driving: the same `agent_assignments` row and investigation, the same `agent.step`, recorded the same way, with `driver: service` in the step's inputs. There is no new scheduler, store or process. The desktop has priority: its step always proceeds and takes a 20-second lease, and the service steps only an assignment with no live desktop lease. The service holds the Coordinator's dispatch lock around each step and rechecks the work hold, the setting and its own closing before every one. It acts with the authority recorded on the assignment, never with approve.

Closing Ledger releases a running assignment to the service (`agent.release`) when the service is live and the setting `agent.continue_when_closed` is on (default on; Settings ▸ Slate ▸ Assignments). Otherwise closing pauses it, as AGENT-01 did. Master Stop on either side pauses every assignment. Reopening Ledger takes the work back. Today says "While Ledger was closed, Slate took N steps on …" with inspect, or resume when it is waiting or paused.

`tools/check_continue_service.py` starts the real resident service in a disposable profile, releases a numbers assignment to it, and watches the service finish it on its own ticks before shutting it down.

## The model turn applied to a real page (D30, docs/MODEL_TURN_01.md)

The owner decided in D19 that a document edit the model proposes applies at once, visibly and undoably. `workbench/model_turn.decide` checks one proposed `documents.edit` against the open page: the same document, the same revision, and a change the store accepts. When the model's place cannot hold the quoted words, the owner's selection is used and the sentence says so. The page applies the edit through the Kernel with origin `SLATE_MODEL`, which `documents.edit` alone accepts and which reads back `model_used: true`. It goes through the page's one undo stack as one step. The changed words glow pencil-yellow and fade; the glow is never saved. The face shows APPLIED ON THE PAGE with undo and the Right/Wrong marks, and the instruction matrix records the outcome against the proposal. Every other proposed operation keeps the Run/Edit words. A stale proposal is not applied, and the card says why.

The live page trial (docs/MODEL_TRIAL_02.md) ran Qwen2.5 1.5B and 0.5B through the real operations in the build container, and it found what the canned check could not. Under schema-constrained decoding both models filled every optional key of the change, so a "make it bold" proposal also replaced the words with nothing and added an empty paragraph, and the page applied it. The fix works at both ends. The model is offered one kind of change per proposal (one mark, a style, replace, append or clear, never an empty replacement). `decide` sets aside what rides along and applies one kind and one mark at a time. It replaces or deletes only the owner's own selected words, and a paragraph change applies only on the owner's paragraph; everything else waits for Run. An independent review measured the first version of the fix live and found four more holes, all closed. Page requests now also fit the owner's default 2,048-token context, which before failed every time. In the final run at that context, the 1.5B model applied bold, remove-bold and "replace lazy with sleepy" correctly, sent the heading request to Run, and changed no other word. The 0.5B model answers "bold" to almost everything, visibly and undoably. The rules still handle the common edits without any model.

## The second assignment: files about something (D31, docs/FILES_ABOUT_01.md)

With nothing open, `find files about pellets` becomes an assignment. Slate asks where Ingress is, searches Files, lists Ingress by name, reads the first lines of up to four of the best matches in Files, and writes a findings page that inspect opens. Explicit words choose this procedure, never a model, and requests about the open page go to the model instead. When a model is ready it only advises between reading more and writing. The loop now takes a profile's options after its last planned step instead of dropping them.

## Registry, settings and preservation

All 690 SERVICE-01 scopes and the 112 job-tool targets are retained. The registry reads 714: AGENT-02 adds `agent.release`. Its recorded extensions to earlier additions are `agent.step` (optional `driver`), `agent.assign` (profile `files_about`) and `documents.edit` (origin `SLATE_MODEL`). Settings read 43 with `agent.continue_when_closed`, recorded in docs/SETTINGS_INVENTORY_07.md. `tools/check_release.py` reports the registry and settings sections as ADDITIONS_RECORDED against HATCH_AGENT_02_RESULT.json. No second dispatcher, scheduler or data store was added.

## A slimmer tree (D33)

By the owner's wish for a slimmer project, the 66 regression captures of INTEGRATION-01 (17.6 MB) left the tree. Nothing pinned them: they were copies of captures earlier checkpoints ship, and they remain in the INTEGRATION-01 volumes and in git. Their JSON reports stay. The STRUTHIO · ARCADE game stays: it is the owner's Easter egg behind the logo and part of the recorded I05 baseline. The phone app's three image copies also stay, because the I05 baseline the release check verifies pins them.

## The owner's design update (D32, recorded for the next UI pass)

During this integration the owner chose Graphite as the new public name, with the sharpened graphite point as the mark and the peeking cat in place of the Hatch egg. As the owner asked, it is recorded and taken up as the next UI pass, after this checkpoint.

## Evidence

The numbers are read from build/agent02_ui/focused-tests.json, build/agent02_ui/qt-checks.json and the reports under build/agent02_ui; HATCH_AGENT_02_RESULT.json copies them. Each work item was implemented, then reviewed by an independent adversarial reviewer who reproduced every finding before it was fixed. Twelve findings were real and all were fixed; their probes are listed in the item docs.

The integration also fixed two things in the evidence itself. The AGENT-01 quiet-connections test left a parentless Related block alive. Its queued deletions crashed Qt inside the next Qt test once the new model-turn tests ran after it, so that test now closes what it opens. The Hatch check compared the Services row by its full words while the services lifecycle's one-second refresh could change them. It had passed by about a tenth of a second, and window startup is no slower in this pass (0.91 s against 0.96 s at the AGENT-01 commit). The row is now compared by its stable first word.

Numbers of this run: 379 focused tests in 26 modules passed (54 new cases over the AGENT-01 focused log; test_launcher, test_service_lifecycle, test_operations, test_explore, test_settings_registry, test_hardware_settings, test_presentation_settings, test_settings_advanced, test_memory_settings, test_model_settings, test_install_media, test_startup_scripts, test_release_check, test_readiness, test_frame, test_paper, test_machine, test_documents, test_tool_selection, test_agent_loop, test_conditions, test_related, test_browse, test_vocabulary, test_model_turn, test_profile_files); 34 checks and 11 captures in the new tools of this pass (continue 11/4, model_turn 11/3, files_about 7/4, continue_service.py 5/4), every one PASSED; 24 of 24 earlier shipped Qt tools rerun PASSED (none failed); registry 714 operations, 112 job tools, 43 settings; release check on the tree PASSED with registry ADDITIONS_RECORDED and settings ADDITIONS_RECORDED.

## What stays open

More assignments (an ARC calculation that follows a changed condition, datasheet to spreadsheet); Python helpers Slate writes himself; takeover and resume of one native artifact; model replacement with rollback; the service under the owner's systemd user unit; and everything owner-host (the ThinkPad, its display and inputs, the owner's model file). Strict HATCH acceptance 0/6; historical integrated 4/6; I05 OPEN; I06 NOT_STARTED.
