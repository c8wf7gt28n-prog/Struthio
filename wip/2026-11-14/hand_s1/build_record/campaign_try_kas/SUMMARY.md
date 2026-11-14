# Campaign run campaign_try_kas

**What Pass means.** Pass means every declared check matched what the current code does; it is not a verdict that the spec is met. The expectations are what Graphite does today, so a Pass shows the current behaviour held, nothing more. A case whose checks record current behaviour that a quoted spec line contradicts is counted apart as "Pass (current code; the spec asks otherwise)". An anchor that passes covers a baseline slice of its situation, not the situation's whole intent; the table says so on each one.

- Build: Graphite 0.8.2, commit unknown (no  (whether it differs from a commit is unknown: no git history here)
- Python 3.13.18, PySide6 6.8.3; host Intel(R) Xeon(R) Processor @ 2.30GHz, 4 logical CPUs
- Model identity: Qwen3.6-35B-A3B-Q4_K_M.gguf (20,542,732,576 bytes); simulation uses the fixture built from its real header
- After Hours 07 seed: 703a56fc0c07746d108013e5ffda19b9b60fbcd9d8b5951f0bdca22954afc787
- Repository .ledger untouched: True
- Runner files SHA-256: 1c85a2fa65ca1dfa (part of every case revision)

## Counts (first attempts)

| Pass | Pass (current code; the spec asks otherwise) | Partial | Blocked | Fail | Timeout | Total |
|---|---|---|---|---|---|---|
| 2 | 0 | 0 | 0 | 0 | 0 | 2 |

- scenes: Pass 2

## Cases

| Case | Situation | Title | Attempt | Outcome | Checks | Seconds | Reason |
|---|---|---|---|---|---|---|---|
| P02a |  | P02, Her door on the Field, in After Hours 07, by pointer | 1 | Pass | 16/16 | 12.9 | all declared checks met |
| P03a |  | P03, You take the window back, in After Hours 07, by pointer | 1 | Pass | 26/26 | 12.3 | all declared checks met |

## Against the spec: the current code passes, a quoted spec line asks otherwise

- none

## Anchors that ran: each covers a baseline slice of its situation

- none

## Slowest attempts

- P02a attempt 1: 12.9 s (Pass)
- P03a attempt 1: 12.3 s (Pass)

## Spec questions (genuine questions for the owner; the case passes on current behaviour)

- none

## Not passing

- none

## Blocked (needs checked when the run started)

0 blocked: 0 for a need not met here, 0 with every need met and the steps not written yet.

- none

SUMMARY campaign_try_kas: 2 cases, Pass 2, Pass (current code; the spec asks otherwise) 0, Partial 0, Blocked 0, Fail 0, Timeout 0. Pass means every check matched the current code, not that the spec is met.
