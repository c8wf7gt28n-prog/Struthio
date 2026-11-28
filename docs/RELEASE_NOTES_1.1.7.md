# Kas 1.1.7: Night's hero touches

*28 November 2026. The last pieces of the Night hero look you asked to be "creative awesome". Install over 1.1.6 the same
way: put this kit's changed files into your kit folder, delete the old `repo/` folder, run `bash JOIN.sh`, then
`bash install.sh` as root.*

## What is new

- **The clock in seven segments.** In Night, the bar's clock is HH:MM drawn as seven-segment digits over a faint unlit
  88:88, like an old LED desk clock, with the date small underneath. It is amber in Night Duo and Night Amber, and in
  its own phosphor in Night Green and Night Paper. Day, Pencil and Indigo keep their clock as it was.
- **Her words type out.** In Night with CRT effects on, a new line of Kas's is run out behind an amber block cursor, at
  about 600 characters a second and never longer than 0.8 seconds a line, with phosphor afterglow. A click shows the
  whole line at once. It is instant under Reduce motion or with CRT effects Off. Anything waiting for your press, such
  as her cards and Waits for you, always appears whole.
- **Peak marks.** In Night Duo the green meters carry an amber peak mark that holds for 2.5 seconds, then falls slowly.
- **Night: Paper.** A fourth Night choice under View ▸ Appearance: one paper-white phosphor, like an old white-phosphor
  terminal. Every text is at least 4.5 to 1.

## Tested

The Night tests pass (22, 7 of them new), and the release check passes on the exact commit.

Known and kept for next week: in Night Duo, her words in her answer bubbles still draw in green rather than her amber.
The typing cursor is amber.
