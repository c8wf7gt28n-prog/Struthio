# Planted bugs: how many the tests catch

A planted bug is one small wrong edit in one function: a comparison flipped, a condition negated, a return changed, a
number moved by one, a call deleted. If no test fails, the tests do not guard that behaviour. The release notes report
the share caught in the code that guards the owner (target: 75% or more, never falling after a test is retired).

Kept in the tree for each release to rerun; never shipped (`tools/package_graphite.py`, `NOT_SHIPPED`).

## Files

- `bugs.json`: the 156 planted bugs of the 14 November 2026 measure, each with its file, function, kind, old and new
  text, what the 0.8.2 suite did with it (`verdict_0_8_2`), what the 0.8.4 suite did with it (`verdict_0_8_4`, absent
  when it was not rerun), its group (`guarding` or `other`) and the test modules to run. A later release adds its own
  `verdict_` field the same way and compares.
- `plant.py`: finds a bug in the current code by its file, function, kind and text (never by line number, since code
  moves) and writes it into a copy of the tree, the file's own text first into a marker in the copy
  (`tools/planted_bugs/.planted.json`). `python3 tools/planted_bugs/plant.py --where` lists where each lands now; a bug
  the code no longer holds shows as `GONE`. `plant.py COPY --restore` puts back a bug left planted.
- `run.py`: plants each named bug in a throwaway copy, makes the seed current (so that no test fails on the seed's
  digest alone), runs the bug's modules until one fails, puts the file back, and writes one line per bug.

## Running it

Only in a throwaway copy of the tree, never in a checkout (both scripts refuse a folder with `.git`). Make the copy as
the build rules say (the tracked files without `wip/` and `.claude/`) and make its seed current first. Two copies give
two workers; never more than two test processes at once.

    python3 tools/planted_bugs/run.py --tree COPY_A --tree COPY_B --group guarding --out guarding.jsonl
    python3 tools/planted_bugs/run.py --report guarding.jsonl

`--ids M007 M008` runs named bugs; `--before gap` only the ones the 0.8.2 suite missed; `--python` names the interpreter
that has PySide6; `--plain` drops `nice` and `unshare` where `unshare` is not allowed. Without `--out` the results go
beside the first copy (`COPY_A.planted_bugs.jsonl`), never into a checkout.

## Stopping and starting again

- To stop a run, press Ctrl-C once (or send it SIGTERM). The tests running at that moment are ended, their bugs are put
  back and not written (a test cut off proves nothing), the seed is made current, and the run exits with 130.
- Start it again with the same `--out` to carry on: bugs already written are skipped; a bug written as `error` is tried
  again.
- A kill that cannot be caught (`kill -9`, a restart) can leave a bug planted. Its file's own text is in the marker, and
  every run first puts that file back and makes the seed current, so the next run measures a clean tree. The test that
  was running is ended with the run where `setpriv` is installed; elsewhere let it finish before starting again.
- A copy that cannot be made current again stops the run with exit 1 and says why: start from a fresh copy.

## Reading the result

- `caught`: a test failed with the bug in place and a current seed. This is the only verdict that counts as caught.
- `missed`: every listed module passed. The bug's `what` says what the owner would lose.
- `timeout`: a module ran out of time; reported apart.
- a row with `refresh`: packaging refused the planted tree (the seed could not be rebuilt), so its modules ran on the stale
  seed; reported apart with the tests that failed, for a person to read, not as a test's catch.
- `gone`: the code no longer holds the bug, or its file is gone (rewritten, moved or removed); drop it or plant a new one
  where the code moved.
- `error`: the bug could not be planted or run; the row says why, and the next run tries it again.

Equivalent bugs (no behaviour can tell them apart, `verdict_0_8_2: equivalent`) are left out of every rate.
When new code is written, add bugs to `bugs.json` in the same shape; keep the ids of the old ones so releases compare.
