# lines: fix pass after review (notes while working)

Worktree: /home/user/Struthio/.claude/worktrees/wf_023c5420-966-9 (nothing committed). lines.patch applied there (git apply, clean).
Copy for tests: work/b084/lines/copy (made by lines/fixcopy.sh; deleted at the end).

## Plan
must 1 (rounding): totals and add work out exactly on the numbers as written (fractions/decimal), no round(…,6);
  min/max give the value a row holds; too large or too small for a number is refused (total) or no value (add).
must 2 (inexact text): number() keeps text when a float cannot hold what is written (Decimal(repr(float)) != Decimal(text));
  where's literal keeps such text as text; add refuses such a literal.
should 1: where a=@b compares with field b like the other comparisons; "@b" in quotes is the text (plan key 'text').
should 2: chain_menu.word = line_steps.literal (one function); literal quotes ", \ and a leading @ too.
should 3: files_service.number keeps NaN/inf cells as text (only that; the reader's other conversions -> not_done).
should 5: a row without the field has nothing there: kept by is not / =null (as group gathers it).
should 6: words (form said once, add's help, plain()'s semicolon words).
should 7: test for the too-large total; release note says saved lines can answer differently.
should 8: add computes only the operation asked (exact arithmetic, no overflow on whole numbers).
should 4: for the owner to confirm -> decisions (no code).

## State
- [x] code edits (lines/fix_edit1.py, fix_edit2.py applied to the worktree): typed_pipeline.py, line_steps.py, chain_menu.py,
      files_service.py (NaN/inf cells stay text), test_line_rules.py (22 tests now)
- [x] tests written; test_line_rules default look: Ran 22, OK. On the builder's sources (same copy, four files swapped):
      Ran 22, failures=9, errors=1 (logs/FIX.BEFORE.test_line_rules.default.log); every new test fails there.
- [x] probe (lines/fix_probe.py): all reviewer reproductions gone; same() transitive over 54872 triples; = / is not split
      every row; 4000 random decimal texts: no two different decimals share a number; 3000 random adds = exact fractions;
      2000 rows cost 2.5 to 8 ms a line (sum 5.5, group+avg 7.9).
- [x] patch rewritten once (1254 lines, 8 files) after the first green run
- [ ] both looks: lines/fix_matrix.sh running in the background -> lines/fix.matrix.out, lines/fix.matrix.<look>.txt
- [ ] final: rewrite patch, check it applies to HEAD, append to lines.progress.md, delete lines/copy

## If cut off here
Everything is in the worktree and in lines.patch. Left to do: read lines/fix.matrix.out; the three kasandra-look failures
about the name "Stacy" (test_writing_line x2, test_context_menu x1) belong to item "name" and are expected; anything else
must be fixed. Then rewrite the patch (git add -A -N . ; git diff HEAD -- . ':(exclude)MANIFEST.json'
':(exclude)project/stacy_seed/current' ':(exclude)wip' > lines.patch), append to lines.progress.md, rm -rf lines/copy.
