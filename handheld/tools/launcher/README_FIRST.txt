STRUTHIO - FIRMWARE
===================

This package puts the STRUTHIO game on the Waveshare ESP32-S3-Touch-LCD-3.5B board.

1. Unzip the whole package, for example to C:\struthio (Windows) or ~/struthio (macOS / Linux).

2. Plug the board into the computer with a USB-C DATA cable.

3. Windows: double-click  FLASH_ME.bat
   macOS / Linux: open a terminal in this folder and run  ./flash_me.sh

   It installs what it needs the first time (Python and esptool), finds the board by itself,
   writes the game, its pictures and its music, and checks every byte. About 2 minutes.

4. When it says DONE, unplug the board. The next time it powers on, its screen walks you through
   a check of every button, the speaker and the battery.

If it cannot find the board: hold BOOT, press and release RESET, release BOOT, and let it look again.

What is where
-------------
  FLASH_ME.bat / flash_me.sh       put the ready-made game on the board (start here)
  prebuilt\                        the game, ready to flash, and flash_args.txt (the addresses)
  webflash\                        the same thing as a web page (works once it is hosted on https)
  STRUTHIO.bat / struthio.sh       the build menu, to build the firmware yourself with ESP-IDF 5.5
  manual\                          the build manual and the flashing guide (PDF)
  handheld\firmware\               the firmware source (ESP-IDF 5.5)
  handheld\build\assets\           the art pack and soundtrack (do not edit)
  handheld\core, render, audio     the game itself (portable C)
  handheld\host, golden            the desktop checks
  handheld\tools\struthio_doctor.py   the setup check the menu runs
  SHA256SUMS.txt                   fingerprints of every file (the doctor uses them)

The by-hand command, if you ever want it (from the prebuilt folder):
    python -m esptool --chip esp32s3 -p COM5 -b 460800 write-flash @flash_args.txt
