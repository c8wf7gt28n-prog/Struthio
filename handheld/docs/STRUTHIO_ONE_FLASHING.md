# STRUTHIO ONE · Flashing the firmware

This puts the STRUTHIO game on the Waveshare ESP32-S3-Touch-LCD-3.5B. Do it **before** you build the
board into the case (build guide, "Before assembly"), with the Waveshare on its own on the bench.
Later updates work the same way through the USB-C port in the ONE's top edge.

There are two ways. **Route A** needs only Python and one command. **Route B** builds the firmware
from source with Espressif's ESP-IDF and the STRUTHIO menu. Both put the same program, art pack and
soundtrack on the board.

## 1. What you need

- A computer: Windows 10/11, macOS or Linux.
- A **USB-C data cable** (some cables only charge: if the computer never sees the board, try another cable).
- This package, unzipped so that the folder is **`C:\struthio`** (Windows) or **`~/struthio`** (macOS / Linux).
  No spaces in the path, and not inside OneDrive, Dropbox or iCloud.

## 2. Find the board's port

Plug the Waveshare into the computer.

- **Windows:** Device Manager → "Ports (COM & LPT)": a new **COMx** appears when you plug it in.
- **macOS:** in Terminal, `ls /dev/cu.usbmodem*`.
- **Linux:** `ls /dev/ttyACM*`. If you get "permission denied" later: `sudo usermod -aG dialout $USER`, then log out and in.

If nothing appears, put the board in **download mode**: hold **BOOT**, press and release **RST**, release **BOOT**.

## 3. Route A: flash the prebuilt firmware (quickest)

1. Install **Python 3** (python.org; on Windows tick "Add python.exe to PATH").
2. In a terminal: `python -m pip install "esptool>=5"` (macOS / Linux: `python3 -m pip install "esptool>=5"`).
3. Go into the `prebuilt` folder: `cd C:\struthio\prebuilt` (or `cd ~/struthio/prebuilt`).
4. Flash (replace `COM5` with your port from step 2):

       python -m esptool --chip esp32s3 -p COM5 -b 460800 write-flash @flash_args.txt

   The art pack and soundtrack take a few minutes. Every part ends with **`Hash of data verified.`**
5. Press **RST** once. The game appears with **READY** in the middle.

**Without installing anything:** Espressif's browser flasher (Chrome or Edge) at
**https://espressif.github.io/esptool-js/**. Connect, then add these five files at these addresses and
press Program:

| Address | File |
|---|---|
| `0x0` | `prebuilt/bootloader.bin` |
| `0x8000` | `prebuilt/partition-table.bin` |
| `0x10000` | `prebuilt/struthio.bin` |
| `0x410000` | `handheld/build/assets/struthio.pak` |
| `0xd10000` | `handheld/build/assets/struthio_music.ima` |

## 4. Route B: build it yourself (ESP-IDF and the menu)

1. Install **ESP-IDF v5.5** (Espressif's guide: docs.espressif.com → ESP-IDF → Get Started).
   On Windows use the ESP-IDF installer and start **"ESP-IDF 5.5 CMD"** from the Start menu.
2. Start the menu:
   - **Windows:** double-click `STRUTHIO.bat` (best from the "ESP-IDF 5.5 CMD" window: `cd C:\struthio`, then `STRUTHIO`).
   - **macOS / Linux:** `cd ~/struthio`, then `./struthio.sh`.
3. **Option 1, Check my setup.** It checks the package against `SHA256SUMS.txt`, finds ESP-IDF and the
   board. Fix anything it marks FAIL.
4. **Option 2, choose the port.**
5. **Option 5, FULL ART.** It builds, flashes the program, art pack and soundtrack, then shows the log.
   The first build takes several minutes. Leave the log with **Ctrl + ]**.
6. Other options: **4** a greybox test (flat colours on purpose), **6** a quick re-flash of the program only
   (keeps art and music), **9** erase everything.

The menu prints every command it runs, so you can type them yourself later.

## 5. What success looks like

The screen shows the game's first scene with **READY** in the middle. With Route B, the log shows lines like:

    I (290) STRUTHIO: STRUTHIO handheld boot (core: STRUTHIO ARCADE 1.8.0 port)
    I (5695) STRUTHIO: DART trial ROCKER ONLY, best 0, display ok, renderer panel (asset pack)

On the bare Waveshare there are no buttons yet, so the game waits at READY. That's
correct. The buttons are tested after assembly (build guide, step 11).

## 6. If it goes wrong

| What you see | What to do |
|---|---|
| "Failed to connect" / "No serial data received" | Download mode (step 2: hold BOOT, tap RST, release BOOT), then flash again. The port name can change in download mode |
| The port never appears | Another USB-C cable (data, not charge-only); another USB port; on Windows wait for the driver to install |
| "Permission denied" on Linux | `sudo usermod -aG dialout $USER`, log out and in |
| Flashes fine, but the screen stays black | Press RST once. Still black: flash again with Route A, all five files |
| Picture upside down after assembly | Service mode, hold RIGHT 1 s (build guide, step 12) |
| A build error (Route B) | Read the first line with `error:` in it. Check you're in ESP-IDF 5.5 and the folder path has no spaces; run option 1 |

## 7. What's in this package

| Folder / file | What it is |
|---|---|
| `prebuilt/` | The firmware ready to flash, and `flash_args.txt` (addresses and settings for esptool) |
| `STRUTHIO.bat`, `struthio.sh` | The build menu |
| `handheld/firmware/` | The firmware source (ESP-IDF 5.5 project) |
| `handheld/build/assets/` | The art pack and soundtrack (flashed to their own partitions; don't edit) |
| `handheld/core`, `render`, `audio` | The game itself (portable C) |
| `handheld/host`, `golden` | Desktop checks: the game replays the arcade's recorded runs bit for bit (menu option D) |
| `handheld/tools/struthio_doctor.py` | The setup check (menu option 1) |
| `manual/` | The whole build manual (Windows 11) and this guide, as PDFs |
| `SHA256SUMS.txt` | The fingerprint of every file |
