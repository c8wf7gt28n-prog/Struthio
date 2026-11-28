# Graphite 1.1.3: Night as a phosphor monitor, and a quieter bar

*28 November 2026. Two changes since 1.1.2, both from your words. Install over 1.1.2 the same way: put this kit's
changed files into your kit folder, delete the old `repo/` folder, run `bash JOIN.sh`, then `bash install.sh` as root.*

## Night is a phosphor monitor

You said: "night mode is to look like old computers that only had orange and black / green and black monitors....but
updated to 2026 but still old school modern". Then: "Screen burns and all the fun".

- **One phosphor on near-black:** **Amber** (the default) or **Green**, under View ▸ Appearance.
- **Hierarchy by brightness only,** never by another colour.
  - Amber uses 100%, 86% and 78% brightness: 10.8, 8.1 and 6.9 to 1 against the ground.
  - Green uses 100%, 80% and 71%: 14.8, 9.6 and 7.5 to 1.
  - Every text stays easy to read.
- **Inverse video** for the selected row, menu rows, pressed buttons, the active window on the bar, and HALT. There is
  no red.
- **IBM Plex Mono** for the chrome: the head, the bar, menus and Kas's headings.
- **The terminal** takes the phosphor's shades.
- **CRT effects** (View ▸ Appearance ▸ CRT effects), set to Off, Subtle (Night's default) or Full:
  - **burn-in:** faint, static ghosts of old screens in the empty background, such as "READY.", "C:\> _" and, in Full,
    a big GRAPHITE;
  - **phosphor afterglow** as typed text and the cursor change;
  - **a warm-up line** when Night starts;
  - **scanlines and a soft vignette;**
  - **a block cursor,** and a faint bloom on the menus.
- **Reduce motion** stops the afterglow, warm-up and blink. The burn-in, scanlines and steady cursor stay, because they
  don't move.

Day and Kasandra are unchanged.

## A quieter bar

From your idea about the tray.

- **One Quick Settings button.** Network, sound and battery are now three small glyphs in one button, with their words
  in its tip. One press opens one panel with Network, Sound and Power, each with "More on the Machine page", plus the
  meters (CPU, GPU, RAM, TXT, NET) as a fourth section.
- **More room for your windows.** At 1366×768, three app windows fit on the bar beside Start, the line, Kas, HALT,
  Quick Settings and the clock, with none folded away.
- **The head:** while the bar stands, Graphite's menus start at the left edge, and Apps leaves the head, since Start
  does that job ("Add an app to the list" sits beside Start's Apps heading).
- **Fixed:** the Power page no longer points to a System menu that has been gone since 0.7.

## What was tested, and what was not

- **Night:** 11 new tests; 65 with the colour-vision, faces and frame tests, all passing in Amber, Green and Day.
- **The bar:** 9 new tests, plus the bar's, Start's, Kas-on-the-bar and one-line tests.
- **The release check** passes on the exact commit.

Not tested:

- frames of Night at 1366;
- the afterglow beyond line edits, and the bloom beyond the menus;
- real Fluxbox;
- your ThinkPad.

## A note on the tray

You asked whether the tray could go to an upper-right bar. With Quick Settings it is now one 87-px button, and the
bottom bar has its room back. A screen-wide top bar would cost every app about 24 px of height, which is scarcer than
width at 1366×768. Say "top bar" if you want the Mac-style layout anyway, and it goes first on next week's list.
