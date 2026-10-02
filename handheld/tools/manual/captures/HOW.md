# How these captures were made

Every `.txt` file here is the unedited output of a command run on the release
package (`STRUTHIO_HANDHELD.zip`, unzipped to `~/struthio`), with ESP-IDF v5.5.5
and Espressif's own toolchain (xtensa-esp-elf esp-14.2.0_20260121). The manual's
screenshots (`screens.py`) only leave lines out; they never change one.

| File | Command |
|---|---|
| version.txt | `idf.py --version` |
| doctor.txt | `python3 handheld/tools/struthio_doctor.py` |
| menu_sh.txt | `./struthio.sh` (option 0) |
| desktop.txt | `make -C host test; make -C firmware/host_test run` |
| settarget.txt | `idf.py set-target esp32s3` |
| build_grey.txt | `idf.py -p /dev/ttyACM0 -D STRUTHIO_ART=greybox build` |
| flash_grey.txt | `idf.py -p socket://localhost:5555 -D STRUTHIO_ART=greybox flash` |
| reconf_full.txt | `idf.py -D STRUTHIO_ART=full reconfigure` |

Two things differ from a computer at home:

- The component registry was not reachable, so `main/idf_component.yml` pointed
  the same component versions at Espressif's git repositories (the
  "Processing 7 dependencies" lines show those paths).
- There was no board. `flash_grey.txt` flashed Espressif's ESP32-S3 emulator
  (QEMU esp_develop_9.2.2, strap 0x7 = UART download mode) over a TCP socket, so
  the port reads `socket://localhost:5555` and the MAC reads 00:00:00:00:00:00.
  Every file was read back byte for byte from the emulator's flash afterwards.

## Emulator runs (`qemu_*.txt`, `fw_*.png`)

The firmware was built for QEMU with three changes that exist only in the
emulator copy, never in the package:

1. the console on UART0 (`CONFIG_ESP_CONSOLE_UART_DEFAULT=y`) because QEMU has no
   USB Serial/JTAG; the board's own logs come over USB-C;
2. a stand-in display, because QEMU has no SPI2: `board_display_init` keeps each
   frame in PSRAM instead of sending it to the AXS15231B. `fw_*.png` are those
   frames, dumped with gdb (RGB565, panel byte order);
3. the wing inputs: QEMU has no pull-ups, so every input reads "pressed". The
   service run keeps that (both wings held = service mode, and the LEFT hold
   steps the volume); the play runs read "released", and `fw_play.png` /
   `fw_gameover.png` come from a script tapping the wings.

QEMU was started with `-m 8M` (the board's 8 MB PSRAM). There is no power chip,
I/O expander or codec in the emulator, so the log says so (`qemu_boot_*`), as a
board would if those chips did not answer. Timings in these logs are the
emulator's, not the board's.

`qemu_reboot.txt` is a cold power-on of the same flash image after a game that
set a high score of 2000: the boot line reads `best 2000`.

`cp1_*_gerber.png` are `cp1/cp1_gerbers.zip` rendered by tracespace
(@tracespace/cli), an independent Gerber viewer.
