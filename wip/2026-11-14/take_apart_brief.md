# "A computer you can take apart" — the owner's discussion document (14 Nov 2026), condensed

The owner wrote (with another assistant) a discussion piece on the Kasandra direction. "Kas" is the assistant (Kasandra).
It is ideas, "kinda just talking"; the owner asked us to keep going in that direction. Its claims and proposals:

1. Inspect the operation. Kas does something useful; you right-click the result and open the operation behind it: the
   input she picked, the method she used, where the answer went. Levels: (a) at a glance: input, what it will produce,
   whether it saves anything; (b) Open method: fields and units, the calculation or program it calls, the conditions
   under which it answers; (c) the exact staC line or registered operation, and a native program underneath if any,
   with how Graphite called it; plus what happened on THIS run. Three buttons on the card: Preview, Open method, Fork.
2. The same operation under the click and under the request to Kas: a click and her request must run the same
   registered operation so inputs/results compare directly. Claim: the Field already exposes exact read operations for
   selected work and its engineering queries run through the dispatcher (cites docs/RELEASE_NOTES_0.3.md).
3. staC words: "word waits = field.read | pick waiting | select kind,title,state" keeps a read under a word of your
   own; `waits` runs alone; `explain waits`; `waits | where kind=finding | count` carries on; the word expands before
   it runs; the full line is in the result and history; the alias belongs to the workspace and runs with the model
   unloaded; stays inside the read boundary (cites workbench/stac_words.py:1). Proposal: Kas teaches by doing — you
   open the line behind her answer, add a filter, see the list change, name your version.
4. Carry provenance through the pipe: which column, which unit, which revision supplied the values.
5. Keep the shell a shell; make the destination of the shared typing strip visible at the instant you press the key
   (cites docs/GRAPHITE_DESK.md:486).
6. Fork the rule: a clearance check with a minimum of 0.50 mm; fork to 0.70 mm; a project copy that records its parent
   revision; preview both on the same input. Fixture rows 0.49, 0.50, 0.69, 0.70 mm (rule: pass if >= minimum):
   original fails 0.49 only; fork fails 0.49, 0.50, 0.69 and passes 0.70. A row "0.028 in" converts explicitly to
   0.7112 mm and shows the conversion; a blank unit gives "Unit missing" (no arithmetic on an undefined input).
   A change to the original is shown, never silently applied to the fork. What did a result depend on (CSV, method,
   conversion table, tool version) — make-like readable account. Run again = run the method on inputs chosen now.
7. Debug together: when a run fails, Inspect shows the last step that worked, the first that stopped, and what it had
   in hand; three failure kinds (bad input, missing tool, malformed output) point to three remedies; with the model off
   the diagnostics still suffice. Subprocess errors: plain words on the card, exit status and diagnostic under a
   disclosure. Ordinary actions on the surface (Open, Run, Show result); Inspect one click away.
8. A right-click menu that grows from your work: "Keep this under Tools for SLIM4"; next week right-click a compatible
   table -> "Check enclosure clearance"; per-project tools; Kas proposes a menu entry, the owner pins; a pinned command
   runs with the model unloaded; a method change is shown as a difference before the menu moves to the new revision.
   Claims: existing docs describe reusable staC procedures carrying operations, prerequisites and checks, instantiated
   against a new assignment and working copy with its own execution grant (cites docs/STAGE5.md:60); the implementation
   plan imagines retaining adapters and helpers (cites docs/BOSS_IMPLEMENTATION_PLAN.md:176).
9. The experiment it asks for: ONE clearance method, ONE fixture, ONE project menu entry. Open the result Kas produced;
   inspect the operation; fork the method and change the threshold; compare the two outputs including the boundary and
   missing-unit cases; pin your copy; turn Kas off and run it yourself; turn her on and ask her to explain the result
   from your version.
