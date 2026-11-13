# What's new in Graphite 0.4.2

November 13, 2026. Guide → What's New opens this page. The 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what came
before.

The owner's whole-build specification gives each of its 35 situations a "difficult variation": the footnote that qualifies a
rating, the subtotal counted with its own rows, the check that looks at the wrong thing. Those are traps a result passes
over while looking right. This release is the first part of an answer: before Stacy makes more, she catches more.

**X: doubt it.** Select a sheet in the Field and press **X** (or Doubt it in its menu, or the Doubt step under D). Stacy puts
a fixed set of exact questions to the records and shows what she found, worst first: what does not hold, what she cannot
tell, a note worth knowing, what holds. No model is asked, nothing is changed, and each row comes from a read you can run.

- A **calculation**: does it agree with its sheet; is every input still what the source page said (an input edited on the
  working sheet says what the page said); were its inputs read under the same conditions; and what it leans on, a 1 % rise
  in each input worked exactly.
- A **reviewed sheet**: does its source stand; is every reviewed cell as it was read from the page ("B3: the page said 280,
  the sheet says 300"); rows with no unit, no condition, or an uncertain reading.
- A **finding**: how many independent sources support it; whether a check says what would show it true; whether that check
  can fail at all; and whether each number it says is on a sheet or is the result of a calculation on the desk.
- A **source** and a **total**: whether it is admitted and what rests on it; whether it still adds up.

On the worked case as it was delivered she finds two things nobody had marked: the finding "The reviewed sheet keeps the 80 ms
condition" is guarded by a check that cannot fail (it looks for the words in the whole record, which also keeps them as first
reviewed), and "Startup ran 30 ms past the Rev B limit" says a number that is on no sheet and is the result of no
calculation.

**A doubt comes with the step that removes it.** Under **D**, a finding whose check cannot fail offers "Give it a check that
can fail": three named changes put up together (watch the sheet, bind a check on the cell itself, run the checks), one **G**.
A finding with no check, whose number is a calculation's result, offers "Check it against" that calculation. Afterwards a
change to the cell is noticed: the check goes stale and the finding waits, where before it stayed current for ever.

**The desk check doubts too.** **C** now also cross-examines everything and lists, beside what waits, the things it doubts
that look right. In staC: `field.doubt {"id":"…"} | pick rows | select verdict,about,why`, and for the whole desk
`field.doubt | pick rows | where verdict=doubt | select title,about,why`.

**Stacy does not rephrase a doubt.** The rows are already plain sentences written by exact rules. With the small model
loaded, its paraphrase of one got a point backwards in rehearsal, so for doubts she shows the rows and adds no words of a
model's. A trace and a what-if are still told in her words, marked as the model's.

**Not done, said plainly.** Nothing here has run on the ThinkPad; all of it was checked offscreen in a build container.
The questions are few and fixed: they know reviewed sheets, exact calculations, findings and totals, and nothing yet about
an imported spreadsheet's formulas (the subtotal counted twice), a footnote on a page, a part with the wrong voltage, or any
of the situations that reach outside the computer. "Its numbers" is a match of a number and its unit, not a recorded link.
A check that cannot fail cannot be removed, only joined by one that can.
