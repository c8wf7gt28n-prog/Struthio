# fixture (Rail Demo): independent review, 19 Nov

STATE: COMPLETE. Verdict: accept after fixes (2 must-fix, both small). Copy deleted. Scripts and logs kept in
b084/fixture/review/{scripts,logs} (batch1.out, batch2.out, batch3.out, probe.out).

## What I ran
- Fresh copy of the main checkout's tracked tree, `git apply fixture.patch` (clean), seed made current
  (record_registry --check: no differences).
- Default look AND GRAPHITE_APPEARANCE=kasandra, every module OK, same counts in both:
  test_rail_demo 26, test_rail_demo_campaign 18, test_desk_acts 28, test_desk_scenes 5, test_campaign 23,
  test_resource_rules 15, test_release_check 22, test_delete_words 6, test_graphite 29, test_deployment 16,
  test_workspace_backup 7, test_system_menu 31, test_kasandra_highlight 10, test_presentation_settings 16.
- The ORIGINAL cases on the owner's backup with the patch applied (temp run folder, deleted): A01 7/7, A16 28/28,
  A17 4/4, A27 7/7, P01a 54/54, P01b 55/55, P01c 56/56, P01d 57/57: all Pass. (The builder had not run P01c/P01d.)
- Owner data (scripts/cmp_owner.py, prints yes/no only): no Rail Demo title, finding, question, value-with-its-name,
  CSV line or PDF hash occurs in the backup. Shared: the four generic reading names and 12 V, both given by the task.
  No added line carries an owner number (the 280 in REQUEST was there before).
- Determinism: build 5.4 to 5.6 s; built twice under `unshare --net` with different TZ, locale and hash seed:
  the same desk picture (14 objects, 12 links). Nothing left under HOME.
- name.patch, lines.patch and faults.patch each still apply on top of this patch (git apply --check).
- No "Programs", "Stacy", "Lain", staC or shortcut in any added on-screen string; Rail Demo is not offered in the window.

## MUST FIX
1. A broken build is reported as Blocked, not Fail. tools/campaign_lib/fixture.py rail_demo_workspace turns every
   rail_demo.Unavailable into Blocked, but the need (pypdf, Poppler) was already checked before the attempt started,
   so the only things it can catch are real failures (an operation refused, a job that did not complete, a table not
   read as written, bytes changed by Files).
   Reproduce A (no source change): a folder holding executable `pdftotext` and `pdftoppm` that `exit 1`, first on PATH;
   `python tools/campaign.py run --case DA01 --out <tmp>/run --fixtures <tmp>/none` ->
   "DA01 attempt 1 Blocked ... Rail Demo could not be built: the references.pdf.page job ended Failed", SUMMARY
   "Blocked 1, Fail 0", need shown as met.
   Reproduce B (in a copy): add `+ 0.12` to `top` in rail_demo.table_region; same command ->
   "Blocked ... the table of Rail_Demo_Bench_Readings.pdf was not read as written".
   Wanted: only rail_demo.available() (what the need checks) becomes Blocked; everything else is a Fail; a test.
2. args_by_seed in run_scene has no test that fails without it. workbench/desk_scene.py run_scene works the
   arguments out twice (once for the doer, once for the row it reports); the tests read the row.
   Reproduce (in a copy): change `desk_doers.run(host, step['act'], arguments(step, seed), door='script'` to
   `step.get('args', {})` -> tests_integrated.test_rail_demo.ThePlayableSceneOnRailDemo 7/7 OK and
   tests_integrated.test_rail_demo_campaign.TheRuns 7/7 OK, although the scene then writes the After Hours 07 CSV
   text into the Rail Demo workspace. (The code is right today; nothing guards it.)
   Wanted: one `args = arguments(step, seed)` used for both, and a check that reads the file hand.write wrote
   (run_scene's after_step at step 3, or the CSV on disk) for "Settled current,250,mA".

## SHOULD FIX
- DA17: with the ARC1_WORKBENCH_CONFIG_HOME switch removed from demo_backup_restore the case still passes 8/8
  (the restored workspace read with the ORIGINAL profile gives the same desk). "restored_desk_is_the_saved_one"
  does not show that the restored profile holds the sheets.
- rail_demo._Desk.job: `del self.kernel.launch` also removes a hold the caller had put on that kernel instance
  (probe: hold gone after build). Put back what was there.
- build() can wait without bound and without a word: Kernel.run_job waits in resource_control.claim until memory is
  admitted. Probe with the host reporting 600 MiB free (reserve is 2048 MiB + 256 MiB for the job): still waiting
  after 40 s, job intake.scan Queued "Waiting for shared-memory headroom". On the ThinkPad with a large model loaded
  the D-cases would end Timeout and the two test modules would run to the hatch check's 600 s. Give it a deadline and
  say the job's reason. (Other tests that run jobs in-process share this; it predates the patch.)
- find(): documents.list is asked for 100. With 101 more pages in the workspace: "Rail Demo is not whole in this
  workspace: a record is missing." (also reached after about 95 uses of set_settled_current).
- set_settled_current cannot be carried on after a stop between the cell write and the recheck: the same value is
  refused ("B3 already says 310"). And _Desk.call says "Rail Demo could not be built: ..." for refusals in find()
  and set_settled_current too.
- The two limit revisions have no row that is the same in both (the ceiling differs only in its conditions), so
  `changed == [all three rows]` cannot tell a comparison from a list of every row. One unchanged row would.
- test_desk_acts.build_window: the bench seed now runs BEFORE the holds (no worker launch, no job submission) where
  it ran under them before. Only a seed with jobs needs to be early.
- A damaged "workspaces" entry in P01.json: `tools/campaign.py list` (any set) ends in a raw traceback at import;
  an empty name in the map silently mangles names ("Rail Demo bench readingsx"). check_scene has the words but is
  not asked.
- Small: build_window's clean-up when a seed fails has no test; report's "not recorded" line has no test (it works);
  SETTLED_POWER / STARTUP_POWER are used only by an assertion against the same literals.
- Not shown here: Poppler 24.02 only; a Poppler that lays the words out differently gives reproduction B's result.
  Run `tools/campaign.py run --set demo` and the two modules on the ThinkPad before trusting them there.

## Checked and fine
- M2: cases_scene.run_case with seed=SEED -> test_p01_is_played_on_rail_demo_in_the_graphite_look_and_in_the_kasandra_look fails. Guarded.
- Bad inputs to set_settled_current ('abc', '300 mA', '', same value) are refused with Graphite's own reason; nothing half-written.
- A build stopped in the middle: a second build says "already in this workspace", find says "not whole ... its findings are missing".
- A second workspace under the same profile builds with ids of its own; an earlier page or investigation of the same name is not mistaken for Rail Demo's.
- An old run folder (no rail_demo in MANIFEST.json) summarises with "not recorded".
- Disclosed decision, changes what a default run shows: `--set all` now also runs the four demo cases; `--set scenes` lists eight.
