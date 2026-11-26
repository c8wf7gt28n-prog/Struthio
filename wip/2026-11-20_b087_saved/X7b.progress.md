# X7b progress (0.8.7: the exam's six blockers)
DONE. Patch b087/X7b.patch (48,067 bytes, 6 files) is against HEAD 24313c2, and `git apply --check` passes on a clean export of HEAD.
The result file b087/X7b.build.result.json is written.
- (5) brief.vocabulary keeps only the tokens and merges arrays. The 4B file now reads (248,320 tokens, about 0.5 s).
- (2)(3) model_exam.score: a MARKS item is right on a subset (no false mark, at least one found), with precision and recall per
  item and per paper. wrong_used and _acted count only TAKEN or TRIMMED answers (asking is not harm). The READ.asks marker now
  reads an option's title as its handle on the exam desk. The card adds "found: x of y". The docstring is updated.
- (1) brain_briefs: prime(port, kind, held), open_desk keyed by the sha256 of messages 1 to 3, open_desks at after_start through
  DESKS. understand: keep_desk (called in ask), desk_layout (DESKS['READ']), exam_ask. READ's caps are unchanged (250).
- (4) judgment.exam_ask goes through ask_next and marks the final outcome, recording the first and second picks. model_exam.sit uses
  the kind module's exam_ask.
- (6) tests_integrated/data/exam/DISAGREEMENTS.md is written. The papers are unchanged.
Smoke: b087/X7b/smoke.py printed 41 of 41 ok (b087/X7b/smoke.out, details in smoke.detail.txt). The registry was regenerated
in the copy and is unchanged. The copy is deleted.
