# What's new in Graphite 0.8.5

November 20, 2026. Guide → What's New opens this page. The 0.8.4 to 0.3 notes beside it describe what came before.

This release is **Maths in lines**: the root you chose to build first ("Let's just do maths ... Then we have the strongest
base to build on"). Everything Kasandra will judge later, her goals, her checks, money and deadlines, stands on it. It
asks no model anything: every answer here says *model calls: 0*, works with no model loaded, offline, in a fraction of a
second.

## Four questions you can ask in a line

Type them in the writing line at the bottom of the window. Guide → the page on lines has every form and the worked
examples below, each checked by a test.

- **Work it out.** `calculate`: 12 V times 280 mA is exactly 3.36 W, never 3.3599999.
- **Solve for.** `solve`: on Rail Demo, the settled current that keeps the rail under Rev B's 4 W is **up to 333 mA**, at
  12 V (333 mA holds at 3.996 W; 334 mA does not, at 4.008 W).
- **Range.** `range`: the exact span of an answer when its inputs have ranges. With a voltage good to half a volt either
  way, a tolerance you record yourself, Rail Demo's settled power is 2.875 to 3.125 W.
- **Check.** `check`: one of three answers, **Holds**, **Does not hold** or **Cannot tell**, always with the reason, and
  for a range also whether it fails for *some* value, with the one case that breaks it. Over that tolerance, Rail Demo's
  settled power holds for every value, with 0.875 to 1.125 W to spare.

Two answers are kept apart because they are two questions: whether the one real value is inside the limit (which may be
"cannot tell"), and whether every value in the ranges is (which may be "fails for some, here is one").

## The receipt

Every answer carries how it was reached: what was asked; every input with where it came from (a cell of a sheet at its
revision, a tolerance you set, a value given in the line); the method in a few steps; the guarantee (exact value, exact
range, or a range that contains the truth but may be wider, and then it says so: "at least 4 to spare", never more than it
knows); whether anything it rests on has changed since; and *model calls: 0*.

## Your tolerances stay yours

A tolerance decides what is concluded, so only you set one, and Kasandra must always ask about it whatever her dial
says. When the value it belongs to is revised but unchanged, the tolerance is carried over and the answer says so; when
the value changes, the tolerance goes to recheck and is not applied until you look. The ranges in her own plans can only
come from your tolerance records: any plan of hers that tries to give a range herself is refused.

## Money and dates

- **Money:** an amount is a number with its currency code, `1200 USD`, kept exact. Two currencies are never added or
  compared unless you give the rate, and then the receipt names it. Rounding happens only when you ask (`round 0.01` for
  whole cents), by one named rule, with the exact value shown once beside the rounded one. Examples in the Guide: what can
  be spent each week and stay under a month's budget with the rent between 950 and 1000 USD (up to 300.00 USD); two loans
  compared by the total repaid (the first is 410.40 EUR less).
- **Dates:** calendar days, shown with their weekday. Days between two dates; a date plus days, weeks, months or years,
  months the calendar's way (31 January plus one month is the last day of February, and the answer says it was clamped);
  business days, Monday to Friday; deadlines that say whether the last day counts ("30 days after Friday 2026-11-20 ends
  on Sunday 2026-12-20, the end day included").
- **Holidays** are counted only from a list you type in the line itself (`| holidays 2026-11-26`); with none given, the
  answer says "no holidays counted". A holiday calendar kept as a source of yours can come with the rule cards of the next
  release.
- These compute what you ask, from your numbers and the rules you state. They give no financial or legal advice.

## What it refuses, and how

Adding volts to milliamps, a denominator whose range includes zero, two unknowns multiplied together, a number too long
to hold exactly, a month that does not exist: each is refused in plain words with the reason, never with an empty answer
that looks like "nothing". There is no floating point anywhere in the new code, and a test reads the code to keep it so.

## Also in 0.8.5

- The setting "Script for incidental text" is gone from Settings: it changed nothing on screen. An old saved value loads
  without a word.
- A few values from your own After Hours 07 workspace that had been in the program's shared files since 0.8.2 (record ids,
  a file fingerprint, a reading, a spreadsheet's text) are gone; the cases that run on your backup now find your records
  by their names. Older versions in the source history keep what they held.
- A test of the start scripts that failed now and then (a race between two stand-ins, never in the program itself) is
  steady: 24 runs of 24.

## Built, checked here, not run, observed on the ThinkPad

- **Built:** everything above. Each part was built by one agent, reviewed by another that did not build it, and fixed.
  The reviews caught, among other things: a way for a plan of hers to give a range herself; a loose range worded as if it
  were exact; a documented date form that was always refused; a rounding step of 0 that crashed; the money and date tools
  crowding unrelated plans.
- **Checked here:** the whole suite in both looks before the release commit (81 modules, 1,294 tests, 0 failing in each
  look), and the release check on the exact commit of this kit (below, in the kit's page).
- **Not run:** nothing on the ThinkPad. No model was loaded (none is needed for any of this).
- **Observed on the ThinkPad:** nothing yet. Worth trying: in the writing line, the Rail Demo solve from the Guide's page
  on lines, then open its receipt; and the weekly budget with your own numbers.

## What is not done

- Kasandra judging your findings with this maths ("does not hold, over by 25 to 35 ms"), "Why", "Either way" and rule
  cards come in 0.8.6, Kas's mind without a model.
- Solving for two unknowns at once is refused with a reason for now.
- A "Solve for…" row in the right-click comes later; type the line, or put it in the writing line from Then.
