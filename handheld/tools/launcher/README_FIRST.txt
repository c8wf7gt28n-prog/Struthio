STRUTHIO - THE SOFTWARE
=======================

This folder puts the STRUTHIO game on the screen board
(Waveshare ESP32-S3-Touch-LCD-3.5B). You do it once, before you build the board into the case.


THE ONLY THING YOU NEED TO DO
-----------------------------
  1. Unzip the whole package to C:\  (you get C:\struthio). Not inside OneDrive, no spaces in the path.
  2. Plug the screen board into the computer with a USB-C DATA cable.
  3. Double-click  FLASH_ME.bat
     (macOS / Linux: open a terminal in this folder and run  ./flash_me.sh)
  4. Wait for DONE (about 2 minutes; the first time a few more, while it installs Python and esptool).
  5. Unplug. The next time the board powers on, its screen walks you through a check of every
     button, the speaker and the battery.

If it says it cannot find the board: hold BOOT, press and release RESET, release BOOT, run it again.
If Windows says "Windows protected your PC": More info, then Run anyway (it is a plain text file:
open it in Notepad to read what it does).


WHAT IS IN THIS FOLDER
----------------------
You use the first two lines. Everything below them is there so the game can be rebuilt, checked
or changed later; you can ignore it.

  FLASH_ME.bat               START HERE (Windows): finds the board, writes the game, checks every byte
  flash_me.sh                the same for macOS and Linux

  prebuilt\                  the finished game, ready to write to the board
    bootloader.bin           the board's start-up code
    partition-table.bin      how the board's 16 MB of flash is divided
    struthio.bin             the game itself
    flash_args.txt           which file goes to which address
  handheld\build\assets\     the game's pictures (struthio.pak) and music (struthio_music.ima);
                             FLASH_ME writes these too. Do not edit them

  webflash\                  the same flasher as a web page (Chrome or Edge); it only works once the
                             page is hosted on https, so use FLASH_ME instead
  manual\                    the build manual and the flashing guide (PDF)
  SHA256SUMS.txt             a fingerprint of every file, so the setup check can tell nothing is damaged

  For building the game yourself (not needed to play):
  STRUTHIO.bat / struthio.sh the build menu (needs Espressif's ESP-IDF 5.5): build, flash, check the setup
  handheld\firmware\         the board's program (ESP-IDF project): screen, buttons, sound, power
  handheld\core\             the game rules (portable C, the same on the board and on a PC)
  handheld\render\           drawing the picture
  handheld\audio\            the sound effects and the music player
  handheld\host\, golden\    desktop checks: the game run on a PC and compared frame by frame
  handheld\tools\struthio_doctor.py   the setup check the build menu runs


BY HAND (only if FLASH_ME cannot be used)
-----------------------------------------
From the prebuilt folder, with Python and esptool installed (pip install esptool), COM5 = your port:
    python -m esptool --chip esp32s3 -p COM5 -b 460800 write-flash @flash_args.txt
