# Graphite 1.1.2: a real terminal

*28 November 2026. One change since 1.1.1. Install it over 1.1.1: put this kit's changed files into your 1.1.1 kit
folder, delete the old `repo/` folder, run `bash JOIN.sh`, then `bash install.sh` as root. Everything in the 1.1 and
1.1.1 notes still holds.*

## What is new

**The drop-down Terminal is a real terminal now.** Press Win+` or Ctrl+Alt+T and xterm drops from the top of the
screen, embedded in Graphite's drop-down and running your own shell in your Files folder.

- Programs that draw the whole screen work: **vim, top, less, htop, nano**.
- **sudo's password prompt** should work, because this is a real terminal device. It is untested here, since the build
  machine runs as root.
- **DOS words still work.** `dir` shows "dir → ls -l" and runs `ls -l`, which goes into your history. `del` moves to
  the bin with `gio trash`, never `rm`.
- **Your own `~/.bashrc` is read first** and never edited. Graphite's DOS words are added only in this terminal.
- The same key, or `exit`, puts it away and gives the keys back to the app you were in.

xterm was already part of the Graphite session, and `libglib2.0-bin` (for `gio trash`) is added. Both were already in
the 1.1.1 kit's repository.

## What was tested, and what was not

These ran on a virtual screen with real key presses:

- a program read a key;
- top ran and q quit it;
- vim saved an edit;
- `dir` printed its Debian line and ran;
- Win+` put the terminal away and gave the keys back.

That is 13 new tests, and 24 with the drop-down's own. The release check passes on the exact commit.

Not tested: sudo's prompt, real Fluxbox, and your ThinkPad.

## Coming next (1.1.3)

- **Night as a phosphor monitor,** amber-on-black or green-on-black, old school done crisply for 2026, as you asked.
- **A quieter bar:** network, sound and battery as one Quick Settings button, with the menus at the left edge.
