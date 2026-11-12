# What's new in Graphite 0.4

November 12, 2026. Guide → What's New opens this page. `docs/RELEASE_NOTES_0.3.1.md` and `docs/RELEASE_NOTES_0.3.md` describe
the Field, the shelf and Stacy.

The owner's words: "I want a do, not a chatbot." This release is the first part of that. It adds no new engine: every step
below is an operation Graphite already had. What is new is that the desk knows which ones fit, lines them up, runs what is
safe by itself, asks once for what is not, and checks afterwards.

**D: what can be done.** Select a sheet in the Field and press **D**. Graphite asks the records how that thing stands and
offers the steps that fit, numbered, in Stacy's rail and in the foot; Stacy says them in Talk. No model is asked: the steps
come from the thing's own record. A digit takes a step.

- A step that only reads runs at once. Stacy shows the exact line and what the records answered.
- A step that changes something says **asks**. It is put in Talk with what it does, what it leaves behind and its exact
  line, and waits. **G** (or Run in Talk) is your go; it runs once, through the same Kernel as everything else, and the
  Field reads the records again. A digit only ever chooses a step: it never approves one. Whether a step may run by
  itself is the Kernel's own word for that operation, not this page's.
- Every line can be put in the writing strip, changed and run again. What Graphite did is always something you can read
  and repeat.

For a calculation that fell behind its sheet: see what went into it, see its cells as they are now, bring it up to date.
For a sheet: where it came from, and the calculations it feeds that are behind. For a finding: why it stands, what comes
next, look at its sources again, run the checks that are due, accept a change or retire it. For an open question: search
the sources for its words. For a source: what depends on it, its text. For a total on a page: why it is out of date, bring
it up to date. For anything: watch it, and be told only when it changes.

**C: check the desk.** Everything is read again. Findings are compared with their sources without marking anything. Stacy
says how many things she read, which wait for you and why, with the step that would settle each, and lists the reads she
made. The same is in the Field's own menu.

**Settle what I can.** After a check, **1** puts the changes that need no decision of yours up together: each named, with
its exact line. **G** is one go for the whole list. They run in order and stop at the first that is refused; each
says how it went. Then the desk checks itself again. Finished means that check finds nothing waiting, not that something
said so. What only you can decide (an open question, a review) is left, and named.

**From the keyboard alone.** Change a number in a sheet, then: **C 1 G**. The calculations that read it are worked again.
**A** goes to what still waits; **D**, a digit, **G**.

**It notices what a change left behind.** A calculation brought up to date keeps your name for it, with the new result
where the name carried the old one ("07 Settled power · 3.36 W" becomes "07 Settled power · 3.6 W"). The page it replaces
is kept in Documents and no longer waits on the Field for ever. A finding whose words still say the old number is marked:
it says which number moved, and offers to be written again with the new one or retired. That is a match of words, said as
one, not a recorded link.

**What changed lately.** A sheet whose record changed in the last twelve hours carries a small turned corner, and the head
counts them. After a settling, the pages Graphite made for you are the ones marked. Pages, calculations and findings have
such a time in their records; sources and reviewed sheets do not yet.

**A program's full window, from the shelf.** On the shelf (**P**), **F** on a program that has a window of its own
(FreeCAD, Inkscape, Blender, Godot, mail) looks in Files for the files it opens and puts up "Open … in …" through that
program's own operation, which checks the file against what was just read; **G** is the go. **D** shows the same steps.
A room of Graphite's own says that Enter opens it. Where the program is not installed, the go is refused and says so.

**Not done, said plainly.** Nothing here has run on the ThinkPad; all of it was checked offscreen in a build container.
The steps are offered by rules written for each kind of thing, and only for what the worked case could exercise: a sheet
whose source was decided again still has to be reviewed from its page by hand, and a held source is not yet decided from
here. No native program was started: none is installed in the build container, where the go was refused with the
program's own words. The assignment loop that keeps working while Graphite is closed is not connected to this yet:
settling runs while you watch. A chain of steps cannot yet be kept under a name and run again on new material. A finding rewritten with a new number stands on nothing until its sources are cited for it again. No model takes
part in choosing a step; with a model loaded Stacy still only puts reads into words.
