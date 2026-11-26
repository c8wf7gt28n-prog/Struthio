# F2b progress (the floor, finished): DONE (17:58)

Patch: b100/F2b.patch (20 files; git apply --check on a clean copy of HEAD d4e03f8: OK). Result: b100/F2b.build.result.json.
Smoke: b100/F2b/smoke.py (F2's smoke + mode `beside` + drill10's F2b checks), runners run.sh, ab_stalls.sh, batch.sh,
looks.sh, beside.sh, drill.sh, summary.sh; what it printed: b100/F2b/smoke_summary.txt. K1's own smoke run on the F2b copy:
b100/F2b/k1smoke.log (30/30). Frames: b100/F2b/frames/ (board after the assignment: day before/after 1920 and 1366,
graphite and kasandra 1920 and 1366 (prev_* = before the kept word light); the migrated 0.8.7 window with its assignment in
ACTIVE WORK: day 1920, kasandra 1366, graphite 1366). Throwaway copies deleted.

## Built (every edit to a shared file marked "1.0 F2b")
- workbench/read_beside.py (new): WAL readers beside the one writer (query_only, one snapshot per block, kept open per
  thread; a refused write -> made again under the guard), off_thread (a timer's write on a floor worker), the Field's
  reading on a worker (desk_later, prefetch_desk, desk_kept), mark (floor.head on a kept reader). GRAPHITE_READ_BESIDE=0 off.
- workbench/older_work.py (new) + her_column_qt + floor.column_plan: a 0.8.x assignment in ACTIVE WORK, own words, own Stop.
- workbench/paint_kept.py (new) + pane_qt: the tree's word light drawn once into pictures.
- engineering_kernel (db, __init__, dispatch), host_service, instruction_matrix, office_service (Office kept per file),
  control_qt, board_qt (rebuild beside, Field reading on a worker, ring layer), qt_app (prefetch), network_qt, stac_words,
  instruments_qt, qt_master_stop, desktop_header_qt, computer_tree_qt, study_qt.

## Measured (Day, before/after interleaved, 3 each, final code)
- 1920x1200: before 210/154/193 ms (4/4/5 gaps >= 100 ms); after 129/115/109 ms (1/1/1).
- 1366x768: before 190/140/248 ms (2/4/4); after 116/107/101 ms (2/1/1).
- Graphite/Kasandra after: 113-151 ms. Remaining: the window's own work (click rebuild, NEXT STEPS drawing, rings once per
  focus, tree branches), none a wait on her writes. Beside checks 12/12; drill 16/16 + F2b 5/5; K1 smoke 30/30.

Nothing half done.
