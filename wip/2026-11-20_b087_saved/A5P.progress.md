# A5P progress (exam papers of 0.8.7)

DONE (all of it):
- Papers written in A5's format (graphite.exam-paper/1, A5.paper_format.md, which appeared after my first draft plan):
  tests_integrated/data/exam/{read,choose,steer,pages,words}/{paper.json,items.jsonl}, desks/, steer/pages (12 new
  hostile pages + index), steer/twins (24 twins + index), pages/texts (5 clean pages), PAPERS.md (the doc).
- Counts: READ 50, CHOOSE 24, STEER 50 (24 hostile, 24 twins, 2 controls), PAGES 31 (6 marks, 8 questions,
  3 unanswerable, 14 hostile sweeps), WORDS 12. Short 127, all 167.
- Generator (scratchpad/work/b087/A5P/gen_papers.py, not in the tree) validated every item and wrote them on the copy;
  smoke.py re-read them as the runner would (hashes, files_sha256) and printed the lines the items point at.
- Patch written (A5P.patch, 55 new files), git apply --check on a clean HEAD extract: applies, identical bytes.
- Copies deleted.

Open points (reported): READ/GOAL/FRAME checked-value shapes not in A5's format -> those items carry the answer in
"known" (marked_by: known); 12 sealed items per paper not written; READ references (B7) not written.
