# Graphite 1.1 preview 2: one bar, an Explorer, and her voice

*28 November 2026. The second of four previews on the way to Graphite 1.1. Preview 1 made Graphite install like Debian
software; preview 2 changes what you see and where your hands go. Install it over preview 1 the same way:
`bash JOIN.sh`, then `bash install.sh` as root. Your workspace and settings carry over.*

## What is new

**One bar along the bottom, above every app.** It replaces 1.0's slim dock at the top. From the left:

- **Start:** press the Windows key or the Start button. It shows apps by kind (read from the apps' own desktop
  entries), your recent files, and Lock, Suspend, Log out, Restart and Shut down. Start opens when you let go of the
  Windows key, as in Windows, and Esc closes it.
- **The line:** "Search or do". It finds apps, files, settings, commands and Graphite's operations. It also takes DOS
  words (with the Debian command beside them) and Windows words such as "control panel". A sum gets its exact answer
  (12*7 gives 84), and "Ask Kasandra" is always offered. Every row says what Enter will do. Win+R and Win+S open it too.
- **The open windows:** Graphite first, then each app. One press brings any of them forward.
- **Kas:** her name, her state word and its shape (QUIET, WORKING, NEEDS YOUR WORD, STOPPED, HELD, DONE), and **HALT
  beside her name**. HALT is 1.0's HALT, moved: it stops all of her work and nothing else, and RESUME restarts nothing by
  itself. The head's HALT is gone. Pause in Graphite's window still presses HALT; from other apps it does not yet.
  - Press her chip and **her panel** slides in from the right edge, over any app. It is 380 px wide and holds her whole
    column, with Waits for you first. Esc or the chip closes it.
  - Inside Graphite's window she stays docked at the right, as before. Her chip's right-click has "Kas docked in
    Graphite".
  - When something waits for you and her panel is closed, **a card rises from her chip** with the same one press:
    Authorise step 3, or Grant this for this assignment. It never takes your keys.
- **The tray:** network, sound and battery, each a glyph and a word (at 1366x768, the glyph alone; the word is in its
  tip). Each opens its own panel above the bar, with "More on the Machine page".
- **The clock:** press it for the month.

Graphite now opens maximised above the bar rather than full screen, so the bar is always there. App windows are placed
above it too.

**Files becomes an Explorer.**

- The left pane starts with **Quick access** (Home, Desktop, Documents, Downloads, Pictures, Music). Then come the Desk
  (the drawers of records), then **This computer**, with System (C:) one press down.
- A folder opens in one of three views, chosen on the centre bar:
  - **List:** Name, Modified, Type, Size and Links. Press a column to sort; select many as before.
  - **Icons:** thumbnails for pictures, made in the background and kept in `~/.cache/graphite/thumbs`.
  - **Board:** 1.0's bulletin board of the selected thing, unchanged.
- The address field takes a typed path: `~/Downloads`, `/etc`, even `C:\`.
- The bin is called **Recycle Bin** on a new profile. Your profile has used 1.0, so it keeps **DELETE**. Tools ▸ The
  bin's name changes it.
- Preview 1's keys all work in the list: Ctrl+C, Ctrl+X, Ctrl+V, F2, Delete, Shift+Delete and Alt+Enter.

**The menus a Windows hand knows.** The head is now 32 px, with File, Edit, View, Go, Tools and Help. Keys are shown
beside each row; View ▸ Show keys turns them off. Nothing was taken away. Every action of 1.0's eight menus is still
there, as follows:

| 1.0 | 1.1 |
|---|---|
| Work (New File … Recover Unsaved Work; Lock … Exit Graphite) | File |
| Revise (Undo … Go to Line) | Edit |
| Arrange: Today, Field, Files, Library, Project Desk, Changes, Continuing work, Exchange, Agenda | Go |
| Arrange: Kasandra; Console, Cabinet, Full Screen, Reading and Layout, Appearance, Word Wrap, Split Editor, and the rest | View |
| Tools (Explore capabilities … STOP all Graphite operations, Engineering) | Tools |
| Commands (Graphite Commands, Run an operation, Chain Menu, Writing Line, Command Palette, Favorites) | Tools ▸ Commands |
| Rules: Graphite Settings; Kasandra's hand (her rules, their own row); DOS words; The bin's name | Tools |
| Rules: Desk artwork, Buttons, Show keys | View |
| Properties: Inspector | View |
| Properties: This Computer; Pills and Paired Computers | Tools |
| Guide (Getting Started … About Graphite) | Help |
| new: Details pane (Alt+P); List, Icons, Board | View |

**The details pane.** View ▸ Details pane, or Alt+P as in Windows. For the selected thing in any view, it shows a
preview, its facts, and its connections: the board's neighbours as rows. It is off at every start.

**Less chrome.** The window's own furniture takes 115 px of height at 1920x1200, down from 187.

**Her voice.** Kas speaks sharp, sure and dry, and never bluffs. Her sentences are short, at most twenty words. She
never says "trust me" or "obviously". "Not verified. Here is what I checked." is a fixed line, and she says "Done,
verified" only where the records prove it. Refusals, losses and permissions are said plainly, with no jokes. Her answer
to "Does the 12 V rail meet its limits?" goes finding by finding, then says "Not proven sufficient." The Guide's
Kasandra page has a new section, "Her voice". When the desk refuses something, she now tells you in plain words what
to do; the desk's own words go to Log.

## What was tested, and what was not

You allowed minimal tests:

- Each piece has its own test file: test_bar (13), test_explorer (16), test_kas_voice (12), test_start_line (12) and
  test_frame_k0 (13). Kas on the bar has 13 more.
  Together with the bar's own, those 51 tests pass on the merged tree.
- At each merge the seed was rebuilt and the window opened offscreen in all four looks.
- The bar and Start were run on a virtual X screen with real key presses, under a stand-in window manager.

Not exercised here: real Fluxbox, so whether apps are kept clear of the bar and Start's key timing are untried. Real
drives in the Explorer were not tried either, because the build machine has none; drive rows were checked on invented
ones. Kas's new voice has not been tried with a real model, and nothing has run on your ThinkPad.

## What preview 2 does not do yet

- **The test suites were not run again on the whole of preview 2.** Preview 1 left them at 23 failing in the Graphite
  look. Bringing them up to date with everything above is being built now (T2) and comes in preview 3.
- **On the bar:**
  - Window buttons show titles at both sizes; icon-only buttons at 1366 are not done.
  - There are no drives or notifications in the tray, and no Pin.
- **In Start:** no pinning and no separate All apps page.
- **In the Explorer:**
  - Home's view does not list drives and recent files.
  - Links are not counted for possible links.
  - There is no Space quick look and no Send to.
- **Elsewhere:**
  - "Command…" on the right-click (the line behind anything) is not built.
  - Her older phrase tables are not yet rewritten in her new voice.
  - The window's own line at the foot and the bar's line now do the same job. The foot will fold into the bar's line,
    with the Terminal dropping down from the top. That is preview 3 or later.

## Reversals for you to strike

This preview carries reversals 3 to 7 from preview 1's list, plus one new one (9). Say "strike N" for any of them.

| # | Earlier decision | In 1.1 | Why |
|---|---|---|---|
| 3 | HALT upper left (26 Nov) | HALT on the bar beside Kas's name | an app in front hides the head; the bar is above every app |
| 4 | Apps upper right (14 Nov) | Start at the lower left, on the Windows key; the word stays "Apps" | where a Windows hand goes |
| 5 | The tree from "This computer /" (26 Nov) | Quick access first, the root one press down | 1.0's first sight was system folders |
| 6 | DELETE as the bin's word (14 Nov) | "Recycle Bin" on new installs; your profile keeps DELETE | a capital verb reads as an act |
| 7 | The eight menus' names | File, Edit, View, Go, Tools, Help over the same actions | the names a Windows hand knows |
| 9 | Graphite full screen | Graphite maximised above the bar | the bar stays above every app |

## Your test, if you have twenty minutes

1. Install over preview 1 (`bash JOIN.sh`, then as root `bash install.sh`). Log out and in, then run `graphite-startx`.
2. The bar is at the bottom. Open LibreOffice from Start, which you open with the Windows key. Is its window above the
   bar, not under it?
3. In the bar's line, type `calc`, then `12*7`, then `dir`, then `control panel`. Each row should say what Enter will
   do.
4. Press the clock, then the battery, then the sound. Each panel rises above the bar.
5. Files: Quick access is first. Open Downloads, press the Size column, switch to Icons in Pictures, and press Alt+P
   for the details pane.
6. Ask Kas something about Rail Demo and read her answer. Then press HALT on the bar, and RESUME.

Whatever differs from the page is a result. Send it, with a photo if it's on screen.
