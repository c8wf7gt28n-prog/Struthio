# STRUTHIO ONE SLIM

The ONE, 16.5 mm thick instead of 23.0. Same outline (74 × 136 mm), same face panel, same buttons and
rocker, same game. What changed is everything behind the face.

| | ONE | ONE SLIM |
|---|---|---|
| Thickness | 23.0 mm | **16.5 mm** (−28 %) |
| Battery | THOR-503450, 1000 mAh, 5.0 mm | 302535, about 250 mAh, 3.0 mm (a 303450, about 500 mAh, fits the same bay) |
| Speaker | the one that comes with the Waveshare (5–6 mm box) | Same Sky (CUI) CMS-151125-078SP, 15 × 11 × 2.5 mm |
| ONE board | 1.6 mm, on a 2 × 16 header with 2.54 mm plastic | 0.8 mm, lying on the Waveshare's socket on 8 bare pins |
| Waveshare | clamped by pegs and foam | screwed to the back shell through three of its own M2 standoffs |
| Shell joint | flat faces, two hooks | tongue and groove all round, 0.15 mm clearance each side |
| Face behind the panel | 0.8 mm | 1.6 mm (0.5 mm only where it lies on the glass) |
| Back wall | 1.8 mm | 1.5 mm |
| Screws | 2 × M2 × 8 pan head | 3 × M2 × 6 and 2 × M2 × 8, countersunk, flush with the back |

Pictures (from the 3D model): `docs/renders/slim/` — `slim_hero.png`, `slim_front.png`, `slim_back.png`,
`slim_inside.png`, `slim_exploded.png`, and `one_vs_slim_side.png` (the two side by side, same scale).

Files:

| What | Where |
|---|---|
| Case model and its checks | `cad/slim/slim_cad.py`, `cad/slim/check_slim.py` (53 checks, all pass) |
| Printed parts | `cad/slim/stl/` (front, back, two wing caps, rocker, pin jig, pin spacer) |
| Board (KiCad 7) | `pcb/slim/make_slim_pcb.py` → `pcb/slim/out/` (Gerbers zip, BOM, CPL, DRC report, pictures) |
| Firmware | the same as the ONE (`firmware/`), it works in both |

## 1. Where the 6.5 mm came from

Every number below is from the Waveshare's own 3D model (ESP32-S3-Touch-LCD-3_5B.stp, from Waveshare's wiki)
unless it says otherwise. Depths are measured into the case from the front of the face panel.

| From | To | mm | What |
|---|---|---|---|
| 0.0 | 1.0 | 1.0 | Face panel, 1.0 mm acrylic (unchanged) |
| 1.0 | 1.5 | 0.5 | Shell rim over the glass border. The ONE had 0.8 mm here |
| 1.5 | 14.1 | 12.6 | Waveshare, from the glass front to the top of its J8 socket |
| 14.1 | 14.9 | 0.8 | ONE SLIM board, lying on the socket |
| 14.9 | 15.0 | 0.1 | Clearance |
| 15.0 | 16.5 | 1.5 | Back wall |

The ONE lost its depth in three places:

- **The header.** A standard 2 × 16 header puts 2.54 mm of plastic between the two boards, and the ONE board
  sat 4.5 mm behind the socket. On the SLIM the board lies on the socket and 8 bare pins go 3.0 mm into it.
- **The battery.** The ONE's 5 mm cell sat *behind* the socket, 13.3 mm deep and more. The Waveshare's 3D model
  shows that, away from its socket, standoffs and connectors, nothing on the back of the board stands more
  than 9.5 mm behind the glass. The SLIM's 3.0 mm cell lies in that space, 0.3 mm above those parts and
  beside the ONE strip, not behind it.
- **The speaker.** A 2.5 mm speaker lies beside the cell, firing out of a grille in the back.

### What fits behind the Waveshare

| Part | Where (x, y in the case frame) | Stands behind the glass |
|---|---|---|
| J8 header socket | x 20.4 to 25.6, y −6.8 to 34.4 | 12.6 mm |
| M2 standoffs (4) | (±24.25, 49.8), (±24.25, −22.2) | 11.5 mm |
| J7 battery socket, J9 speaker socket | right top, left middle | 10.9 mm |
| USB-C | x ±4.5, y 46.2 to 53.8 | 10.75 mm |
| everything else | | 9.5 mm or less |

The battery bay (3.0 × 34 × 52 mm) and the speaker sit where only the "everything else" parts are.

## 2. Parts to buy (besides the ONE's)

| Part | Spec | Notes |
|---|---|---|
| Battery | LiPo pouch **302535**, 3.7 V, about 250 mAh, protection board, PH 2.0 lead (2 pins) | Sold as 200 to 250 mAh depending on the maker: **confirm** with your seller. 3.0 × 25 × 35 mm, about 38 mm long with its protection board. Optional: **303450**, about 500 mAh, 3.0 × 34 × 52 mm with its board (confirm the size). |
| Speaker | **Same Sky (formerly CUI Devices) CMS-151125-078SP**: 15 × 11 × 2.5 mm, 8 Ω, 0.7 W, solder pads | Mouser / DigiKey. Solder the Waveshare's speaker lead (the PH 1.25 plug) to its pads. |
| ONE SLIM board | `pcb/slim/out/struthio_one_slim_gerbers.zip`, **0.8 mm thickness**, BOM + CPL | Set "PCB thickness 0.8" on the order. J1 is not on the BOM. |
| Header pins | one standard 2.54 mm male header, 6 mm long side, 3 mm short side | You use 8 pins of it. |
| Screws | 3 × **M2 × 6 countersunk** (ISO 10642 / DIN 965), 2 × **M2 × 8 countersunk** | Into the Waveshare's standoffs, and the two lower corners. |
| Foam tape | double-sided, **1.0 mm** thick, about 20 × 30 mm | Holds the cell to the back shell. |

## 3. Measure first (2 minutes, before you order)

The case is drawn for the socket height in Waveshare's 3D model: **12.6 mm** from the front of the glass to the
top of the J8 socket. Waveshare's drawing gives the board as 11.5 mm thick, which is the height of its standoffs,
not of the socket. Check yours with calipers (depth rod on the socket, body on the glass):

- **12.6 mm:** build as drawn.
- **11.5 mm:** also print `slim_pin_spacer.stl` (1.1 mm). It lies on the socket under the ONE SLIM, and on the jig
  while you solder (so the pins stand 4.1 mm out).
- **Anything else:** tell us the number before printing.

## 4. Print

**Plastic: PETG.** It is tough rather than brittle, so screw bosses and the 0.5 mm rim do not crack, and it softens
only around 80 °C, so the toy can live in a car in summer. PLA softens around 55–60 °C and creeps under the screws:
don't. ASA is fine too (better in sunlight; it needs an enclosed printer).

Settings for a solid, not-cheap feel (0.4 mm nozzle):

| Setting | Value | Why |
|---|---|---|
| Layer | 0.2 mm (0.12 mm for the caps) | |
| Walls / perimeters | **4** | 1.6–1.8 mm: every wall in the case is then solid plastic |
| Top / bottom layers | **6 / 6** | the 1.5 mm back and 1.6 mm face are solid through |
| Infill | 40 % gyroid (it only reaches the bosses) | |
| Orientation | front shell face down, back shell back down, caps face down | no supports: the groove and tongue both point up, the countersinks are 45° |

Weight of the printed parts: about 36 cm³, **about 46 g in PETG**.

### The joint

The front shell has a 1.0 mm groove, 1.6 mm deep, in its split face; the back shell has a 0.7 mm tongue, 1.5 mm
long. That is 0.15 mm of play each side, and the tongue stops 0.1 mm short of the bottom of the groove, so the
shells close on their faces, not on the tongue. The walls are thickened to 2.75 mm round the joint by a 1 mm land
on the inside. The tongue runs round the whole case except at the power switch, USB-C and the three pin holes.
If it is tight on your printer, run a fine file along the tongue; don't open the groove.

## 5. Build

1. **Flash the board** exactly as for the ONE (Part 4 of the Windows 11 manual). Same firmware.
2. **Pins.** Cut 8 pins' worth of header (strips of 4, 1, 2 and 1). Lay the ONE SLIM *face down* on the printed
   pin jig (its 8 blind holes line up with the J1 holes marked on the back silkscreen: 1, 3, 4, 5, 7, 16, 18, 24).
   Push each strip's **long** side down through the board into the jig until it bottoms. Solder the pins on the
   back of the board, then slide the plastic carrier off over the short ends and snip the pins **flush**. Every pin
   now stands 3.0 mm out of the front.
3. **Trim** the slide switch's and battery socket's leads flush on the back (0.5 mm or less: the back shell has
   0.5 mm reliefs over them and the pins).
4. **Speaker.** Cut the stock speaker off its lead and solder the lead to the CMS-151125's two pads (either way
   round: the amplifier drives both wires). Put the speaker in its lip in the back shell, face against the grille.
5. **Battery.** Check the plug: red to the **+** next to J2. Put the foam tape on the cell's back and stick the cell
   into the bay's lower-left corner in the back shell, lead at the bottom.
6. **Front shell.** Caps and rocker (with its axle) in, as for the ONE. Lay the Waveshare face down into the glass
   pocket.
7. **ONE SLIM.** Lower it onto the Waveshare, pins into J8. It lies flat on the socket and on the front shell's
   bosses. (Spacer first, if step 3 told you so.)
8. **Close.** Speaker plug into J9, battery plug into J2, the leads in their channels (battery: down the middle to
   J2; speaker: up the left side). Back shell on, tongue into the groove. **3 × M2 × 6** into the Waveshare's
   standoffs (snug, not tight: they are small threads), **2 × M2 × 8** in the lower corners.
9. **First power.** Hold both wings and slide the switch on: the service screen. **Rocker right** sets
   CELL 250 MAH (charge 100 mA; that is the default) or 500+ MAH (200 mA). **Rocker left** sets the brightness.
   Check the BATT line. Slide off, slide on: the game.
10. **Face panel, last**, exactly as for the ONE.

## 6. Battery and run time

### What the firmware does about power (all of it in `firmware/main/main.c`, power task)

| | Before | Now |
|---|---|---|
| Backlight | 100 % | **70 %** by default; 30 / 50 / 70 / 100 % on the service screen |
| No button for 30 s | full brightness | the backlight drops to 8 % (the game over screen, mostly); any button brings it back |
| No button for 5 min | runs until the battery is flat | **switches itself off** (the AXP2101's off state, 40 µA typical) |
| Battery below 3.30 V for 5 s | runs to the protection board's cut-off | **switches itself off** (kinder to a small cell) |
| On USB | | never switches itself off |
| Charge current | 200 mA (fine for 1000 mAh) | **100 mA** by default (0.4 C for 250 mAh); 200 mA when the service screen says 500+ mAh |
| Wi-Fi, Bluetooth | never started | never started |

To wake it after it switched itself off: slide the switch off and on again.

What is left on purpose: the game runs at 60 Hz and draws 30 frames a second on both cores at 240 MHz. That is the
game; slowing the CPU would cost frames. Measure first (below), then decide.

### Estimate

Nobody publishes the Waveshare board's current, so this is an estimate from part data, with wide ranges, at the
3.3 V rail, then through the AXP2101's converter (about 90 %) to the 3.7 V cell:

| Load | mA at 3.3 V | Source |
|---|---|---|
| ESP32-S3, both cores 240 MHz, radio off | 50–70 | Espressif datasheet range |
| PSRAM and flash, busy | 10–30 | estimate |
| Panel logic (AXS15231B) and QSPI | 5–15 | estimate |
| Backlight at 70 % | 30–65 | estimate (typical 3.5 inch backlights draw 40–90 mA at full) |
| Codec, amplifier and speaker, music on | 10–40 | estimate |
| **Total** | **105–220** | from the cell: about **105–220 mA** |

| Cell | Usable (to 3.30 V) | Playing | With idle dimming in between games |
|---|---|---|---|
| 250 mAh (302535) | about 225 mAh | **1.0 – 2.1 h** | a little more |
| 500 mAh (303450) | about 450 mAh | **2.0 – 4.3 h** | |
| 1000 mAh (the ONE) | about 900 mAh | 4.1 – 8.5 h | |

Charging the 250 mAh cell from empty at 100 mA: about **3 hours** (the last 20 % are slower). Switched off by the
slide switch it draws nothing; switched off by the firmware it draws about 40 µA: a full 250 mAh cell lasts
months like that.

### Measure your own (and tighten these numbers)

- **Run-down:** charge full, unplug, play (or leave it on the game over screen, which then dims), note the time it
  switches itself off. That is your real figure.
- **USB meter:** with the battery unplugged, a USB-C power meter between charger and toy shows the whole toy's
  current at 5 V; multiply by about 1.4 for the current from a 3.7 V cell.
- The service screen's BATT line shows the cell voltage while you play.

## 7. Boot time (switch on to first picture)

| Stage | Time | Changed? |
|---|---|---|
| The ONE board holds the PWR key; the AXP2101 waits its ONLEVEL time | 0.128 – 2 s (set in the chip at the factory; the firmware's 128 ms setting does not survive the switch cutting the battery) | no: fixed in the chip |
| Power rails up, ESP32-S3 out of reset | a few ms | |
| ROM, bootloader, app image | was: whole 0.6 MB image hashed, PSRAM pattern test, bootloader logs | **image hash and PSRAM test off at power-on, bootloader quiet** (`sdkconfig.defaults`). esptool still verifies the image when it is flashed, and flash writes are read back |
| PMU, LCD reset (100 + 200 ms, Waveshare's values), panel set-up | about 0.35 s | no (vendor timing) |
| Service-mode guard | **800 ms, every time** | **only when a wing is held at power-on** |
| Sound, art pack, first frame | about 0.1 s | |
| Backlight on | was: before the first frame (a flash of noise) | **with the first frame** |

Measured in the emulator (QEMU, which runs slower than the board): the first game frame came **0.99 s sooner**.
On the board, expect the switch-to-picture time to drop from about ONLEVEL + 1.5 s to about **ONLEVEL + 0.6 s**
(estimate). The firmware logs it over USB: `first frame lit N ms after reset`.

Next step, only after measuring on a real board: Waveshare's LCD reset waits (100 ms low, 200 ms high) are
generous; the panel controller's own minimum would save up to about 0.2 s more.

## 8. Heat

Playing, the whole toy turns about **0.4–0.8 W** into heat; charging while playing adds about 0.13 W (100 mA) to
0.26 W (200 mA) in the AXP2101's linear charger.

The case's outside is about 0.025 m². Still air and radiation carry away roughly 8–10 W per m² per °C, so the
**case surface averages about 2–4 °C above the room** (up to about 5 °C charging and playing). Inside, the
ESP32-S3 and the charger run hotter locally (perhaps 10–15 °C over the room), which the board was designed for.

The cell lies on the Waveshare's back, so it will be a few degrees warmer than the room: LiPo cells charge between
0 and 45 °C and run up to 60 °C, so at room temperature there is a wide margin. **Heat is not a problem**, with two
rules: don't charge it in a hot car, and print it in PETG or ASA, not PLA.

## 9. What is drawn from data, and what to confirm

| Item | Status |
|---|---|
| Waveshare heights (socket 12.6, standoffs 11.5, parts 9.5) | Waveshare's 3D model. **Confirm the socket height** (section 3) |
| Standoffs are threaded M2 | 3D model part name SMTSO-M2X4 (an M2 × 4 SMT nut). Confirm with a screw before closing |
| 302535 capacity and size | 200–250 mAh depending on the maker: confirm with the seller |
| Speaker size and pads | Same Sky CMS-151125-078SP listing: 15 × 11 × 2.5 mm, 8 Ω, 0.7 W, solder pads |
| Run time, boot time, heat | estimates (section 6, 7, 8): measure |

## 10. Also fixed on the ONE (same evidence)

The Waveshare 3D model showed three things the ONE's case had wrong; the ONE's model and STLs are updated
(its 65 checks still pass):

- The pin holes for the three edge keys sat 1–2 mm too far back: the keys' actuators are 7.1–9.3 mm behind the
  glass. Moved.
- The USB-C opening was centred 1.2 mm too far back. Moved (the plug still fits either way, now centred).
- The back shell's pegs (1.8 mm) went into the M2 standoffs, which are threaded (about 1.6 mm inside): now 1.4 mm.
- The ONE's header goes 1.1 mm deeper into the socket than drawn if the socket is 12.6 mm tall, as in the 3D
  model: about 4.4 mm into a 5.1 mm socket. Measure it as in section 3; if yours is 12.6, snip 1 mm off the
  header's long pins before soldering it.
- **Firmware, both models:** the service screen never switched the backlight on (it only came on in the game).
  Fixed. The ONE's 1000 mAh cell now needs **CELL 500+ MAH** on the service screen to charge at 200 mA
  (otherwise it charges at a safe but slow 100 mA).
