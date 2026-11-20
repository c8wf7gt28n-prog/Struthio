# What we will have after this pass: Graphite 0.8.5, in about twenty minutes

*A talk for the owner, 20 November 2026. About 2,700 words, roughly twenty minutes read aloud. The numbers in the
examples are Rail Demo's invented ones, or the exact test cases of the maths design; the exact on-screen words may differ
a little from what is written here, but the answers will not.*

---

## 1. Where we are standing

Yesterday morning Graphite had twenty failing tests that everyone had learned to ignore. Last night 0.8.4 went out with
none: twelve hundred tests, both looks, every window check passing, and a release check you can run yourself. Kasandra has
one name everywhere. The start is sturdier. Her look is finished. And there is a small invented workspace, Rail Demo,
living inside the program, so every check can run anywhere without touching your own work.

That was the ground. This pass, 0.8.5, puts the first thing on it that everything else will stand on: **maths that is
never wrong without saying so.**

You chose this order yourself, and you chose it for the right reason. You said the maths "seems a root type", and it is.
When Kasandra later judges a finding, when she says "this does not hold, over by 25 to 35 milliseconds", or "I can't tell
yet, the current reading would settle it", she is not guessing and she is not asking the model. She is using this maths.
So we build it once, carefully, and everything after inherits its honesty.

## 2. What you will be able to do

After this pass you can type a line in the writing line at the bottom of the window, the same place you type everything
else, and ask four kinds of question about the numbers on your desk.

**Work it out.** `calculate`. You already had this: give it an expression and it gives you the exact answer. Twelve volts
times 280 milliamps is 3.36 watts, exactly, not 3.3599999.

**Solve for.** `solve`. This is new, and it is the one you will use most. You give it a relation and the one thing you
want to know, and it tells you every value that keeps the relation true.

Here is the example from the design, the one the tests check to the last digit. A rail at 12 volts, a continuous limit of
6 watts. You type, in effect, *solve voltage times current at most the limit, for current*. Graphite answers: **up to 500
milliamps.** Not "about half an amp": up to exactly 500 mA, including 500. If you said "strictly below the limit" instead
of "at most", and you count in whole milliamps, it says **499**, because 500 would touch the limit and you said it
mustn't.

Now the part that makes it worth having. Real voltage is not exactly 12. Say it wanders between 11.8 and 12.2 volts.
Graphite solves for the worst case across that whole range and says **up to 491 milliamps.** And it can show you why: at
492 milliamps and 12.2 volts the power comes to just over 6 watts. That is the witness, the one corner where it breaks.
You don't have to trust it. It shows you the case that fails.

**Range.** `range`. Give it an expression and ranges for its inputs, and it gives you the exact span of the answer. With
the voltage anywhere from 11.8 to 12.2 volts and the current anywhere from 270 to 290 milliamps, the power lies between
3.186 and 3.538 watts, and Graphite marks that span **exact**: those two ends really happen, at real corners, so the span
is no wider than the truth.

**Check.** `check`. Give it a relation and it gives you one of three answers: **holds**, **does not hold**, or **cannot
tell**, always with the reason.

That third answer is the heart of it. Take the same rail, but now the current might be anywhere from 270 up to 500
milliamps. Is the power under 6 watts? Most of the time, yes. At the worst corner, 12.2 volts and 500 milliamps, it is 6.1
watts. A careless tool would say "fails", because one corner fails. A hopeful tool would say "passes", because the
typical value passes. Graphite says **cannot tell**, and then, separately, **fails for some**, with that 6.1-watt case as
the witness. Those are two different questions, and it keeps them apart: *is the one real value inside the limit?* That
it can't tell, because it doesn't know where in the range the real current is. *Is every possible value inside?* That it
can tell: no, and here is one that isn't.

That distinction matters enormously in engineering, and just as much in a legal argument or a budget. "I don't know" is
an answer. "It could go wrong, and here is exactly how" is an answer. Pretending is not.

## 3. On Rail Demo, in your own terms

Rail Demo is the 12-volt rail on a bench that lives in the program: a settled current of 250 milliamps, a startup current
of 900 milliamps lasting 45 milliseconds, and two revisions of the limits. Rev A allowed 5 watts and 60 milliseconds.
Rev B, the current one, allows 4 watts and 40 milliseconds. All invented, and every page of it says so.

Here is what the maths says about it.

*How much settled current can this rail draw and stay under Rev B's 4 watts?* Up to one third of an amp: **333 milliamps**
in whole milliamps. At 334 it would be 4.008 watts: over.

*Now say the voltage is only good to a quarter of a volt either way.* You record that tolerance yourself: 12 volts, plus or
minus 0.25. Ask again, and the answer tightens to **326 milliamps**, because at the high end, 12.25 volts, 327 milliamps
would already be over 4 watts. The answer carries a note that a tolerance was applied, whose it is (yours) and which
revision of the voltage it belongs to.

*Is the settled power inside the limit?* The range is 2.94 to 3.06 watts. It **holds**, with almost a watt to spare.

*Is startup inside Rev B's 40 milliseconds?* The reading says 45. If the stopwatch is good to 3 milliseconds either way,
the startup took somewhere from 42 to 48: it **does not hold**, by 2 to 8 milliseconds, and no finer measurement can save
it. If the stopwatch were only good to 5 milliseconds, 40 to 50, then at the very best it just touches the limit. The
answer would be **cannot tell**: one value in the range is right on the line, and nothing on the desk says the real one is.

Each of those answers is a few hundredths of a second. None of them uses the model.

## 4. The receipt

Every answer comes with what the design calls its receipt, and I think this will become one of your favourite parts of
Graphite. Click it and you see:

- **What was asked**, in the words you typed.
- **Every input**, with where it came from: this cell of this sheet at this revision, or this tolerance you set on this
  date, or a value you gave in the line itself.
- **The method**, in at most eight short steps.
- **The guarantee**: *exact value*, *exact range*, *sound enclosure* (meaning the true span is inside this one, but this
  one may be a little wider), or *witness checked*.
- **Freshness**: *current*, or *review required* if something it rests on has changed since.
- A fingerprint of the maths code that produced it, so an answer from today can be told apart from an answer made by a
  later, changed version.

And it says, in so many words, **model calls: 0**. No language model touched this answer. That matters for trust, and it
matters on the ThinkPad: the maths works before you have ever loaded a model, works offline, and works in a fraction of a
second whether the 35B is loaded or not.

The receipt is also what makes the maths reusable later. When Kasandra judges a goal in the next pass, the goal's
evidence *is* this receipt. When she explains herself, she points at it. One object, used everywhere.

## 5. Your tolerances stay yours

A tolerance decides what Graphite concludes. Plus or minus a quarter volt can turn "holds" into "cannot tell". So the
design is strict about who may say it.

- A tolerance is a record of its own, with your words in it: "the bench supply is good to a quarter volt."
- Only you set one. Kasandra may propose it, but setting it is on the list of things she must always ask about, whatever
  her dial says. The words she will show are close to: *a tolerance is yours to say; it decides what I conclude.*
- When the value it belongs to changes, the tolerance does not quietly follow. If the voltage is revised and stays 12, the
  tolerance is **carried over**, and the answer says so. If the voltage changes to 12.5, the tolerance goes to **recheck**
  and is not applied until you look at it. Nothing is rewritten behind your back.
- Ranges in a solve never come from the planner either. The rule in the design is short: Kasandra's ranges come only from
  your tolerance records.

## 6. What it refuses, and how

A tool that never refuses is a tool that sometimes lies. This one refuses plainly, with the reason, and never with an
empty answer that looks like "nothing".

- Add volts to milliamps and it says **dimension mismatch**. Ask for watts from something that is not power and it says
  **incompatible output unit**.
- Divide by something whose range includes zero and it says **the denominator may be zero**, never a confident-looking
  span. For a goal later, that reads "cannot tell".
- Ask it to solve something it cannot solve exactly, two unknowns multiplied together for instance, and it says
  **unsupported**, and why.
- If a number would need more than 2,048 bits to hold exactly, it rounds *outward*, so the true value is still inside,
  and marks the answer **widened**.

It does all this in exact fractions. There is no floating point anywhere in the new code, and a test reads the code to
make sure there never is. That's why 12 times 280 milliamps is 3.36 and not 3.3599999. It also means the answers are the
same on the ThinkPad as here, to the last digit.

## 7. How we know it is right

Thirty-odd cases written before the code, each with an exact answer: the 500, the 499, the 491 and the 492, the 30,000/61
milliamps that becomes 491 in whole units, the pole, the empty domain, the zero coefficient (`x - x` is always zero, and
the maths knows it, even when the variable has a range), the repeated variable, the stale limit. Each test fails before
the code exists and passes after.

On top of those, property tests over many random exact points: every point you evaluate lies inside the range Graphite
gave; the ends of an *exact* range are really reached at some corner; a smaller box always gives a range inside the
bigger one's.

And then the part I insisted on keeping even when we agreed to cut reviews elsewhere: a second agent that did not build
it reads it, runs it, and tries to break it. Last night every review found something real. For the root of everything,
that is cheap insurance.

## 8. The rest of 0.8.5

Two small things from 0.8.4 come along.

- The setting **"Script for incidental text"** is gone from Settings. It never did anything. That one is already merged.
- The **values from your After Hours 07 workspace** that have sat in the program's shared files since 0.8.2 (some record
  ids, a file fingerprint, a reading, a spreadsheet's text) are being sorted: what came from the fictional first-run
  example that already ships stays; what is really yours is replaced with invented values. The checks will find your
  records by name when your backup is present. That one gets reviewed too, because it is about your privacy.

And, if this pass has room, **money and dates** as a second maths item on the same core: amounts in a currency kept as
exact decimals, never floating point, with rounding to the cent only when you ask and always outward-honest; and the days
between two dates, a date plus a number of days or months, done the calendar's way. That is the part that makes the maths
useful for "life and money" as you put it: what can I spend each week and stay under the month's budget; when does this
notice period actually end. If it does not fit in this pass it is the first thing in the next one.

## 9. What it will not do yet

To be plain about the edges:

- **Goals** (Kasandra judging your findings with this maths, telling you which reading would settle a question, where the
  break-even lies) come in the next pass, the united one. 0.8.5 gives the engine; 0.8.6 puts her hands on it.
- **One unknown at a time.** Solving for two things at once, or for something inside a square or a fraction in a way
  that isn't straight-line, is refused with a reason for now. It is on the list for later, and when it comes, it will be
  checked against an independent solver and marked as such.
- **No "Solve for…" in the right-click** unless the builder found it cheap and clean; otherwise you type the line, or put
  it in the writing line from the Then panel. The right-click row comes with the united pass at the latest.
- **Nothing measured on your ThinkPad yet.** As always.

## 10. Why this was the right pass to do next

Think of what comes after.

**The united pass** is the floor, the door and the hand together: the big window files split so that work is safe again,
the drills that prove an upgrade never damages your workspace, Kasandra doing what you ask on the Field with a touch to
stop her, changing things at your dial with one Undo, and judging your findings. Every one of those judgments is a call to
this maths. Without it, she would have to ask the model whether 45 milliseconds is under 40 with a 5-millisecond
tolerance, and the model would sometimes say yes.

**Then the programs.** The web first, with quarantine, so that what she reads is information and never an instruction.
Then LibreOffice, Godot, GIMP, one at a time, her taking the mouse while you watch. When she fills in a spreadsheet for
you in LibreOffice and you ask "does this budget hold for the year?", the answer comes from here, with a receipt you can
open.

And the reach of it is wider than engineering. A legal deadline is a date computation that must be exactly right. A dose
by body weight is a range that must say "cannot tell" when the weight isn't known well enough, and not round its way to
comfort. A household budget is a solve for "how much can I spend". You said you wanted her to be good at the hard things
so she would be great at the everyday ones. This is that idea in its plainest form: the same exact, honest core under both.

## 11. When, and what you will get

The core is built and is going through its wider tests and then its review as I write this. The usage limits and the
occasional restart of the machine will decide the clock more than the work will. When it is merged and the whole suite is
green in both looks, I will run the release check on the exact commit, cut the kit the same way as 0.8.4, and send it to
you with screenshots of a solve, a range and a check, in both looks.

The first thing worth trying on the ThinkPad, when you have it: type the Rail Demo solve from the Guide's page on lines,
and then open its receipt. If the receipt makes sense to you, the root is in the ground.
