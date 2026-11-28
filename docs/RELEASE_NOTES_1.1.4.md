# Kas 1.1.4

*28 November 2026. You said: "No more graphite. I hate that public name", and then: "it's kas. All of it. kas only
kas. The other thing if there must be something else is computer". So this release is **Kas**, along with your Night
Duo. Install it over 1.1.3: put this kit's changed files into your kit folder, delete the old `repo/` folder, run
`bash JOIN.sh`, then `bash install.sh` as root.*

## Kas, only Kas

- **Every name you see is Kas:** the window, About, Start, the menus, her words, the Guide, the docs and the kit.
  Where the desktop has to be told apart from her, it is **computer**: the bar's first button reads **Computer**, and
  "the computer's window" replaces the old name.
- **The packages are kas-computer, kas-session, kas-llama-runtime and kas-desktop.** None is a bare `kas`, because
  Debian 13 already has an unrelated package by that name, with a higher version, that apt could pick instead. Each
  takes over its old graphite* package, and four empty graphite* packages carry the upgrade, so `install.sh` moves you
  across and removes nothing.
- **The commands are kas-startx, kas-session, kas-do, kas-doctor and kas-computer.** The old graphite-* names still
  work for this one release and print the new name; they go in the next one. After installing, start with
  `kas-startx`.
- **Your choices to strike:**
  - The look once named Graphite is now **Pencil**, and the one named Kasandra is **Indigo**.
  - The Guide's page is "Kas, the Ghost in the Shell".
  - The little game keeps its title, STRUTHIO.
- **What stays inside, never shown:** internal names, such as the program folder `/usr/lib/graphite`, your settings in
  `~/.config/graphite`, module names and settings keys. Nothing of yours moves, and nothing breaks.

## Night Duo, the new default Night

Amber and green work together, with grey as the burn.

- **Green is the computer:** files, lists, the tree, the board, the terminal and the meters.
- **Amber is Kas and your word:** her panel, her words, Waits for you, HALT, the selected row, pressed buttons, the
  bar's active window and focus.
- **Grey is the past:** the burn-in, disabled things and borders.

Every word is at least 4.5 to 1 against the ground; the worst pair is 6.0 to 1.

It is a hero look:

- **Two tubes:** her panel is a second, warmer amber tube with its own bezel, and it warms up a beat after the green
  one.
- **The burn:** "kas" is burnt into the centre, an old DIR listing into the lower left, "C:\> _" into a corner, and
  "KAS> _" into her panel.
- **Full** CRT effects add a grey character-cell grid.

Night: Amber and Night: Green stay as choices. If you chose one under 1.1.3, it is kept.

## What was tested, and what was not

- **The rename:** 14 new tests, and 32 test files moved to the new words. A word sweep finds no visible old name.
- **The upgrade:** apt's own resolver moves the 1.1.3 packages to kas-* and removes nothing. A real install in a clean
  Debian chroot has **not** run, so `kas-startx` starting the session is untested. Try it first on your ThinkPad. If it
  fails, `graphite-startx` still works this release.
- **Night Duo:** 15 tests, with colour-vision checks under Duo, Amber and Green.
- **The release check** passes on the exact commit.

Not built yet from the hero ideas: the amber seven-segment clock, her words typing out, and amber peak marks on the
meters. They are first on the list for next week.
