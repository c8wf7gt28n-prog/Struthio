STRUTHIO HANDHELD
=================

You are holding everything needed to build the STRUTHIO handheld: the game
firmware, the art and the soundtrack, the case and control-board files, and
the build manual.

1. Put this folder at C:\struthio (Windows) or ~/struthio (macOS / Linux).
   No spaces in the path, and not inside OneDrive / Dropbox / iCloud.

2. Open the build manual:  manual\STRUTHIO_Build_Manual.pdf
   Follow it step by step. Every gate tells you what PASS looks like.

3. When the manual reaches the computer steps, use the menu:
     Windows:        double-click STRUTHIO.bat
                     (best from "ESP-IDF 5.5 CMD" in the Start menu)
     macOS / Linux:  ./struthio.sh
   Option 1 checks your setup and tells you what to fix.

What is where
-------------
  STRUTHIO.bat / struthio.sh       the build menu
  manual\                          the build manual (PDF and Word)
  handheld\firmware\               the program for the board (ESP-IDF 5.5)
  handheld\build\assets\           the art pack and soundtrack (do not edit)
  handheld\cad\handheld\           case STL files, sticker, control PCB, drawings
  handheld\docs\                   pin and wiring card
  handheld\core, render, audio     the game itself (portable C)
  handheld\host, golden            the desktop checks
  handheld\tools\struthio_doctor.py   the setup check the menu runs
  SHA256SUMS.txt                   fingerprints of every file (the doctor uses them)

Safety: prove everything on USB power first. The battery goes in last.
