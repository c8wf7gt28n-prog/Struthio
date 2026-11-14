# Campaign run campaign_kasandra

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
| 9 | 0 | 0 | 0 | 0 | 0 | 9 |

- scenes: Pass 9

## Cases

| Case | Situation | Title | Attempt | Outcome | Checks | Seconds | Reason |
|---|---|---|---|---|---|---|---|
| P01a |  | P01, the playable scene in After Hours 07, by pointer | 1 | Pass | 54/54 | 17.3 | all declared checks met |
| P01b |  | P01, the playable scene in After Hours 07, by keys | 1 | Pass | 55/55 | 16.0 | all declared checks met |
| P01c |  | P01, the playable scene in After Hours 07, by pointer, with less motio | 1 | Pass | 56/56 | 19.5 | all declared checks met |
| P01d |  | P01, the playable scene in After Hours 07, by keys, with less motion | 1 | Pass | 57/57 | 18.4 | all declared checks met |
| P02a |  | P02, Her door on the Field, in After Hours 07, by pointer | 1 | Pass | 16/16 | 12.8 | all declared checks met |
| P02b |  | P02, Her door on the Field, in After Hours 07, by pointer, with less m | 1 | Pass | 16/16 | 15.1 | all declared checks met |
| P02c |  | P02, Her door on the Field, in After Hours 07, at Ask first, then Appr | 1 | Pass | 24/24 | 13.4 | all declared checks met |
| P03a |  | P03, You take the window back, in After Hours 07, by pointer | 1 | Pass | 26/26 | 12.2 | all declared checks met |
| P03b |  | P03, You take the window back, in After Hours 07, by pointer, with les | 1 | Pass | 26/26 | 14.5 | all declared checks met |

## Against the spec: the current code passes, a quoted spec line asks otherwise

- none

## Anchors that ran: each covers a baseline slice of its situation

- none

## Slowest attempts

- P01c attempt 1: 19.5 s (Pass)
- P01d attempt 1: 18.4 s (Pass)
- P01a attempt 1: 17.3 s (Pass)
- P01b attempt 1: 16.0 s (Pass)
- P02b attempt 1: 15.1 s (Pass)

## Spec questions (genuine questions for the owner; the case passes on current behaviour)

- none

## Not passing

- none

## Blocked (needs checked when the run started)

0 blocked: 0 for a need not met here, 0 with every need met and the steps not written yet.

- none

SUMMARY campaign_kasandra: 9 cases, Pass 9, Pass (current code; the spec asks otherwise) 0, Partial 0, Blocked 0, Fail 0, Timeout 0. Pass means every check matched the current code, not that the spec is met.
