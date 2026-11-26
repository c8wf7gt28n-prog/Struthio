# K4b progress (Her plan in time on a slow machine): DONE

## Built (patch b100/K4b.patch, applies to a clean ef17efb; one file: workbench/objective_plan.py, every change marked "1.0 K4b")
- PLAN turn kind v2. Message 1: the standing instructions, rewritten (the things now follow the request). Message 2: the
  tool menu only, as short numbered lines ("8 work a calculation again from its sheet: D"), only the step tools that are here
  and whose things are on the desk (USES). Message 4: the request and only the desk's things it names (named(): for each clause
  the best match among the kinds its verb takes, ties up to 3, "that one"/"the earlier one" as the desk reads them).
- Priming: plan_layout(kernel) registered in brain_briefs.DESKS['PLAN'], so after_start/open_desks primes brief+menu at Ready
  (None while HALT holds); keep_plan(i, request) before each PLAN question (brain_briefs.open_desk, keyed by the sha256 of
  messages 1-3, so a changed registry or a desk with other kinds of things primes again; its time spent from the request).
- Grammar (SHAPE): each tool admitted only with exactly the handles it takes (D among the named things of its kinds, S of an
  earlier step; a step taking S is never first). Needed: under K4's grammar the real 4B wrote "8|23|23" (no handles).
- build_from_model refuses a D handle the request did not name. offer(): no turn when nothing of the desk is named
  (NOT_ASKED_NOTHING_NAMED); words for LATE ("did not answer within its 20 s on this computer, so this is the desk's own
  plan") and CEILING_TIME; 'prompt': {'kept': KEPT|PRIMED|NOT_PRIMED} in the result; 'lead_changes' wording when a plan has no
  read (the 4B frame said "The reads go ahead" over a plan with no read).
- Caps (1200 new, 48 answer, 20 s), the 20 s foreground most and the 25 s request ceiling: unchanged.

## Checked
- stand-in: b100/K4b/smoke.py standin -> b100/K4b/standin.log (all as expected).
- real 4B (three loads under the lock: 1 crashed in my measuring code before any turn; 2 measured with K4's loose grammar:
  turns 12951 ms / 2267 ms, REFUSED "8|23|23"; 3 final, b100/K4b/live.log): tokens 492/183/309 -> 330/270/60; PLAN turn 1
  TAKEN "8 D2|23 D6 S1" in 10987 ms (cache miss: cache_n 0), turn 2 TAKEN in 3300 ms (cache_n 326).
- frames: b100/K4b/frames/k4b_live4b_day_1920x1200.png and _1366x768.png (model's plan taken, run 3; the lead sentence
  there is the one since changed to 'lead_changes').

## Not done / findings: see K4b.build.result.json.
