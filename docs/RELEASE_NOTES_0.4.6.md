# What's new in Graphite 0.4.6

November 13, 2026. Guide → What's New opens this page. The 0.4.5, 0.4.4, 0.4.3, 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes
beside it describe what came before.

The owner, the same day the mouse path arrived: "I'd probably like the mouse pointer to be the systems green. We kinda
need more green glowing I think." This release is that, and one rule to keep it from becoming decoration:

**Amber is what is selected, what has the keyboard, and what waits for you. Green is what is live: readings, what is
current, staC, the pointer, and whatever the pointer is over.**

**The pointer is green.** The arrow, the hand over something you can click, the text bar in a writing place and the
closed hand while you drag the Field are drawn by Graphite in the desk's green, with a dark edge so they read over a light
page as well as over the dark desk, and a soft halo of the same green. They are drawn, not loaded from a picture, so
they are the same on every machine. The cursors Graphite does not draw stay the system's: the resize arrows on a divider
and the wait cursor.

**What the pointer is over answers in green.**

- In the Field, the tile under the pointer has a green edge and a halo, and its wires light. A key at the foot, on the key
  card or on a page turns green under the pointer, and the Approve button glows.
- **The pointer carries a little light.** On the open ground of the Field there is a faint pool of green under the pointer,
  beneath the sheets and the wires. It moves only when your hand moves it; nothing on the surface moves by itself.
- Across the desk, a button, a top menu (Work, Programs, System), a row of a list or a tree, a tab that is not the chosen
  one, a scroll handle and an underlined link word answer in green under the pointer. They answered in amber before,
  which made "the pointer is here" look like "this is selected". The chosen row of a menu or a list stays amber: that is a
  selection, and the arrow keys move it too.

**What is live glows.**

- In the Field, a sheet that is current, supported or checked has a small glow behind its mark, and a wire that is live
  carries a faint light along its length. A wire that is stale does not.
- staC is green wherever it is shown: on Stacy's rail, in the line at the foot, on a page. On a page that reports a
  doubt or a check, what holds is green.
- The live readings at the bottom right (CPU, GPU, RAM) glow a little. A reading that is not there ("—") does not.

**The Clean desk has no glow.** It keeps the green pointer and the green answers and drops every halo, the pointer's
included, as it drops every other ornament. Work → Desk art chooses.

**What was checked, and what was not.** In the build container, with the window run offscreen: the window, the writing
strip and the Field hold the green pointer and it changes shape over a tile, a key and during a drag; the Clean desk
drops the glow from the pointer, the Field and the readings and the Illustrated desk brings it back; a top menu, a link
word, a row of the cabinet tree, a row of the Activity list and a tab that is not the chosen one draw green under the
pointer (the scroll handle's green is set in the same style sheet and was not looked at); the mouse path of 0.4.5 and
the keyboard walks still pass. One thing was
measured: moving the pointer over open ground redraws only the two small squares where its light was and is, about 10 ms
in the container against about 21 ms for the whole Field.

Not seen, because it cannot be seen there: the pointer itself. An offscreen window has no pointer, so the pictures of it
are the drawn shapes, and in one picture the pointer was placed onto the picture where it stood. How the green pointer and
the glow look on the ThinkPad's own screen, and whether its X session shows a coloured pointer with a soft edge (it needs
the X Render extension, which a normal Xorg has), is for the first boot to show. If the session cannot do it, the pointer
falls back to the system's and nothing else changes. The pointer is one size; it does not grow with the reading size.
Nothing has run on the ThinkPad.

Nothing else is new here. The next journeys are the ones 0.4.5 named: an ordinary workbook as a citizen of the chain, the
centre's common frame and small toolbar, a full program through Programs with the saved revision coming back, and Stacy
working out the steps of a job.
