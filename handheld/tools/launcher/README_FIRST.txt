STRUTHIO ONE - FIRMWARE
=======================

This package puts the STRUTHIO game on the Waveshare ESP32-S3-Touch-LCD-3.5B.

1. Put this folder at C:\struthio (Windows) or ~/struthio (macOS / Linux).
   No spaces in the path, and not inside OneDrive / Dropbox / iCloud.

2. Open the guide:  manual\STRUTHIO_ONE_Flashing_Guide.pdf

3. Quickest way (Route A in the guide): install Python 3, then
       python -m pip install esptool
       cd C:\struthio\prebuilt          (or: cd ~/struthio/prebuilt)
       python -m esptool --chip esp32s3 -p COM5 -b 460800 write_flash @flash_args.txt
   (COM5 = your board's port; the guide shows how to find it.)

   Or build it yourself with ESP-IDF 5.5 (Route B) using the menu:
       Windows:        double-click STRUTHIO.bat
       macOS / Linux:  ./struthio.sh

What is where
-------------
  prebuilt\                        the firmware ready to flash, and flash_args.txt
  STRUTHIO.bat / struthio.sh       the build menu
  manual\                          the flashing guide (PDF)
  handheld\firmware\               the firmware source (ESP-IDF 5.5)
  handheld\build\assets\           the art pack and soundtrack (do not edit)
  handheld\core, render, audio     the game itself (portable C)
  handheld\host, golden            the desktop checks
  handheld\tools\struthio_doctor.py   the setup check the menu runs
  SHA256SUMS.txt                   fingerprints of every file (the doctor uses them)

Flash the board on its own, over USB, before you build it into the case.
