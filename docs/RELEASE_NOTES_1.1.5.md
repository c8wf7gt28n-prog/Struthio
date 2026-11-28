# Kas 1.1.5: more screen burns

*28 November 2026. You said: "We need more screen burns, and can probably add some burnt gray". Install over 1.1.4 the
same way: put this kit's changed files into your kit folder, delete the old `repo/` folder, run `bash JOIN.sh`, then
`bash install.sh` as root.*

## What is new

**More burnt grey.** The burn-in is stronger: about 5% of the phosphor in Subtle and 8% in Full, up from 3% and 5%.
Every word is still at least 4.5 to 1 against it, and a test keeps it that way.

**More burns, each one the machine's own past, burnt where it sat for years:**

- **1.0's old dock:** a grey band along the top.
- **The old foot's five names** ("Line Terminal Search Web Log") along the bottom, burnt deeper than the rest because
  they sat there longest.
- **An old boxed MAIN MENU:** 1. FILES, 2. MAIL, 3. LEDGER, 4. GAMES, SELECT >.
- **A VCR's 12:00** in seven-segment digits at the top right.
- **A function-key strip:** F1 HELP, F2 SAVE, F3 LOAD, F5 RUN, F10 QUIT.
- **A tape's** LOAD "*",8,1 / SEARCHING FOR * / LOADING / READY.
- **In Kas's amber tube:** lines of an old session above her KAS> prompt.

They join the burns from 1.1.4: kas in the middle, the old DIR listing, C:\> and READY. All of it is grey, static and
under everything, and it shows in Night with CRT effects on (Subtle or Full).

## Tested

The Night tests (15) and the name sweep (14) pass, and the release check passes on the exact commit. Not tried yet on
your screen.
