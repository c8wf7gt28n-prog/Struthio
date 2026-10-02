# STRUTHIO ONE

The ONE is the plug-in handheld. One rigid PCB does all of the wiring, so you don't solder, crimp
or route anything. The ONE board plugs onto the back of the Waveshare board, the battery plugs into
the ONE board, and the speaker plugs into the Waveshare board.

**Design locked** (see "Design lock" at the end). Sources: case `cad/one/one_cad.py` (fit checks
`check_one.py`, 65 checks), board `pcb/one/make_one_pcb.py` (Gerbers `export_fab.sh`), face panel
`cad/one/panel/make_panel.py`, part facts `HARDWARE_FACTS.md`. Anything marked **confirm** still
needs the real part in hand; the guide says what to do if it turns out different.

## Shape

| | |
|---|---|
| Size | 136.0 × 74.0 × 23.0 mm. 65.0 mm wide above the controls (straight sides), flaring gently to 74.0 mm; the bottom edge is gently scooped |
| Screen | 3.5" Waveshare panel, visible 47.86 mm wide, behind a clear window in the face panel |
| Face | one 1.0 mm clear acrylic panel: the lens over the screen and the art round it in one piece. Its cut-outs give each key a 1 mm well |
| Wing buttons | two round 14 mm caps, a wing engraved on each. Left flaps up-left, right flaps up-right, **both together flap straight up** |
| Dart rocker | 44 × 7.2 mm under the wing buttons, a double-ended dart and reticle engraved on it. Press an end to fire the aim-assisted dart that way |
| Power | slide switch on the player's left side, by the controls. **Up (toward the screen) = ON** |
| Charging | the Waveshare's USB-C, in the top edge |

## How it fits together (front to back)

1. **Face panel**, 1.0 mm acrylic, art printed on its back, taped onto the front shell's face.
2. **Front shell.** Holds the window, the button caps in their guide collars, and four posts the ONE board rests on.
3. **Waveshare ESP32-S3-Touch-LCD-3.5B**, screen down on the front shell's inner face, located by ribs at its top and bottom edges.
4. **ONE board** (1.6 mm). A plate behind the controls with a strip up the right side. Its 2 × 16 header plugs into the
   Waveshare's J8 socket; the case sets the depth (pins 3.3 mm into the ~4 mm socket), the board rests on the posts.
5. **Battery** on the Waveshare's back, left of the strip, lead end down; a 3 mm foam pad on top of it.
6. **Speaker**, taped into a bay in the back shell, firing out through the grille.
7. **Back shell.** Hooks on at the top. Three posts with pegs drop into the Waveshare's mounting holes to locate it;
   the foam pad presses battery and board forward. Two M2 × 8 screws at the bottom go through the ONE board into the
   front posts and hold everything shut.

Why 23 mm: Waveshare 11.5 + header standoff 2.7 + header plastic 2.54 + ONE board 1.6 + header tails and the back wall.

## The ONE board

| Ref | Part | LCSC | JLC | Job |
|---|---|---|---|---|
| J1 | HCTL PZ254-2-16-Z-8.5, 2 × 16 male header | C2894977 | extended | Into the Waveshare J8. Standard mounting: plastic on the top side |
| SW1, SW2 | TS-1187A-B-A-B tact switch | C318884 | basic | Left / right wing button (GPIO17 / GPIO18) |
| SW3, SW4 | TS-1187A-B-A-B tact switch | C318884 | basic | Rocker left / right end (GPIO21 / GPIO38) |
| SW5 | G-Switch SS-12D06-G030 slide switch, 3 A | C17179519 | extended | Battery on/off: a real cut, nothing drains the cell when OFF |
| J2 | JST S2B-PH-K-S socket | C173752 | extended | The battery plugs in here (entry faces right) |
| Q1 | AO3401A P-MOSFET | C15127 | basic | Reverse-battery protection: a lead wired the wrong way round does nothing instead of damaging the Waveshare |
| Q2, C1, R1, D1 | AO3400A, 10 µF, 470 kΩ, 1N4148WS | C20917, C15850, C25790, C2128 | basic | **Power-on pulse.** On battery alone the Waveshare's power chip (AXP2101) waits for its PWR key before it connects the battery. When the slide switch turns on, this circuit holds PWR (header pin 24) for about 3–8 s, so the handheld starts by itself |

The buttons use the ESP32's internal pull-ups: each switch connects its GPIO to GND. Only diagonal pads are wired,
so a switch works whichever way round it is fitted. Header pins used: 1 BAT, 3/4/29/30 GND, 5 GPIO21, 7 GPIO38,
16 GPIO17, 18 GPIO18, 24 PWR (Waveshare's numbering, see `PINOUT_AND_WIRING.md`).

## What you buy

| Item | Exactly what |
|---|---|
| Waveshare ESP32-S3-Touch-LCD-3.5B | The bare board (not the "-C" cased version). It comes with its 6 Ω 1 W speaker. |
| LiPo cell | THOR-503450 (5 × 34 × 52 mm with its protection board), 1000 mAh. Order it with a **JST PH 2.0 mm** 2-pin plug and an **80–100 mm** lead. |
| ONE board | JLCPCB, assembled (below) |
| Face panel | Laser-cut 1.0 mm acrylic, back-printed (below) |
| Printed parts | `cad/one/stl/`: front shell, back shell, two wing buttons, rocker |
| 2 × M2 × 8 pan-head screws | Self-tapping (PA/"PT" thread) or plain machine screws; either taps the 1.7 mm pilot holes |
| 1.75 mm filament | An 11 mm piece: the rocker's axle |
| Foam pad | 3 mm soft foam (EVA or PU), about 30 × 45 mm, self-adhesive on one side |
| Double-sided tape | Thin, for the speaker and the face panel (clear adhesive transfer tape is best for the panel) |
| Paint pen, blue (optional) | To fill the engraved wings and dart |

## Printing

PLA or PETG, 0.2 mm layers, 3 walls.

| Part | Put on the bed | Supports |
|---|---|---|
| Front shell | its **face** down (the face is flat) | none needed |
| Back shell | its **back** down | none needed |
| Wing buttons, rocker | their **top face** down (the engraving prints into the first layers) | none |

## JLCPCB order

1. Upload `pcb/one/out/struthio_one_gerbers.zip`: 2 layers, 1.6 mm, any colour.
2. Turn on **PCB Assembly**, top side, **Standard** PCBA (J1, J2 and SW5 are through-hole parts).
   Upload `BOM_JLCPCB.csv` and `CPL_JLCPCB.csv`.
3. In the placement preview check:
   - **J1**: an ordinary header, plastic on the top side, its 32 pins in the 2 × 16 holes on the strip.
   - **J2**: the socket's opening faces the board's right edge.
   - **SW5**: the knob points off the board's left edge.
   - **Q1, Q2** (SOT-23): the single leg (pin 3) on the side the silkscreen shows. **D1**: its band on the pad toward the gate bus (left).
   If anything is turned, rotate it in the preview by 90° steps until it matches the silkscreen.
4. Six of the parts are JLC basic parts; J1, J2 and SW5 are extended (one set-up fee each).

## Face panel order

Any shop that laser-cuts and UV-prints acrylic can make it. Files in `cad/one/panel/`:

| File | What it is |
|---|---|
| `one_panel_cut.dxf` / `.svg` | Cut lines in mm, seen from the front: the outline and three cut-outs. Nothing is narrower than 3 mm |
| `one_panel_print_MIRRORED.png` | The art to print on the **back** (600 dpi, 1 mm bleed). The screen window is transparent: **no ink there** |
| `one_panel_white.png` | White underprint behind the colour, everywhere except the window |
| `one_panel_print.png` | The art as seen from the front, for checking |
| `one_panel_proof.png` | The art with the cut lines (magenta) and the clear window (blue) |

Ask for: **1.0 mm clear cast acrylic, cut to the DXF, reverse-printed (colour, then white) from the mirrored PNG,
window left clear.** Cheaper: a clear cut panel only, plus the art printed on clear or white sticker vinyl with the
window cut out, stuck on the panel's back.

## Before assembly: flash and test the Waveshare on its own

Flash the STRUTHIO firmware over USB-C with the Waveshare on the bench (see the software part of the manual).
The game must come up on the screen before you build it in. The firmware also sets the power chip up for the
ONE's slide switch, so flash it **before** you power the board from the battery.

## Assembly

Work on a soft cloth. Nothing needs force.

1. **Paint (optional).** Fill the engraved wings and dart with the paint pen, wipe the top face clean, let it dry.
2. **Wing buttons.** From the inside of the front shell, push each round cap into its collar with its **key** (the small
   tab on its side) in the slot on the collar's outer side. That is the only way it goes in, and it leaves the wing
   upright. The caps can't fall out of the front: their flanges are bigger than the holes.
3. **Rocker.** Push it into its collar from the inside, then push the 11 mm filament axle through the hole in the
   collar's top wall until it stops in the bottom wall. The rocker should tip freely both ways.
4. **Waveshare.** Lay it screen down in the front shell, **USB-C to the top** (it lines up with the opening), its side
   buttons (PWR, RST, BOOT) toward the pin holes on the left. It drops between the ribs at its top and bottom edges.
5. **ONE board.** Set the slide switch **down (OFF)**. Hold the board over the Waveshare with the header above the
   J8 socket, lower it straight, and press evenly until it **rests on the four posts**. It stops there by itself,
   with the pins 3.3 mm into the socket. Don't press harder or bend the header.
6. **Battery.** Look at the plug and at the **+** printed beside J2 on the board: the **red** wire must go to **+**.
   (Wrong way round does no damage, Q1 blocks it, but the handheld won't start. To fix a reversed plug, lift each
   contact's latch with a needle, pull the wires out and swap them.) Plug it into J2 from the right. Lay the cell on the
   Waveshare's back left of the ONE strip, **lead end down**, and let the lead lie flat in the gap between the cell and the
   strip, down to the plug.
7. **Foam.** Stick the 3 mm foam pad on top of the battery.
8. **Speaker.** Put a piece of double-sided tape on the speaker's back and stick it in the bay on the inside of the back
   shell, **its face toward the grille**. Plug its lead into **J9** on the Waveshare (the small 2-pin socket at the left
   edge, beside the BOOT button). Keep the back shell right beside the case while you do this; the lead is short.
9. **Close.** Put the back shell's two top hooks into the slots inside the front shell's top edge and swing it down. The power knob
   slides into its slot, the pegs drop into the Waveshare's holes. If anything stops it closing, open it and look: a
   lead is caught. Fit the two M2 × 8 screws at the bottom, **snug, not tight**.
10. **First power.** Slide the switch **up**. The screen lights within about 3–8 s (the power-on pulse) and the game
    starts. Slide it down: it goes off at once.
11. **Test every control.** Hold **both wing buttons**, slide the switch up, keep holding until the service screen
    appears. Press each wing button and each end of the rocker: each one's counter must go up by one per press, and
    none may count by itself. The BATT line shows the cell's voltage and charge (and CHARGING / USB when plugged in);
    "BATT NONE" means the cell isn't connected. Leave service mode by switching off.
12. **Screen the wrong way up?** In service mode, **hold RIGHT for 1 s**. It is saved; switch off and on to play.
13. **Charge.** Plug USB-C in **with the switch ON**. With the switch OFF the battery is disconnected: USB runs the
    handheld but doesn't charge the cell.
14. **Face panel, last.** Peel the protective film off the back, put tape on the black areas only, line the panel up
    inside the rim (the button wells over the buttons) and press it down from the middle outward. Peel the front film.

## If something is wrong

| What you see | What to do |
|---|---|
| Nothing at all when you slide the switch up | Try it **down**, in case the switch's ON end is the other way (**confirm** on the first build). Check the battery plug polarity (step 6). Plug USB-C in: if it starts on USB, charge the cell with the switch ON |
| Still nothing on battery, but it runs on USB | Slide the switch up and press the **PWR** button through its pin hole for 2 s. If that starts it, the power-on pulse isn't reaching pin 24: check that the ONE board sits fully on its posts |
| A button counts by itself in service mode | Its cap's stem is touching the switch: take the cap out and sand 0.2 mm off the stem tip |
| A button doesn't count | Check the ONE board rests on all four posts; check the cap moves freely |
| No sound | Check the speaker plug in J9, and that the speaker's face is against the grille |
| The back shell won't close | A lead or the foam is in the way; never force it. Check the knob is in its slot |

## Firmware settings that belong to the ONE

- **Dart mode ROCKER ONLY** is the default: both wing buttons together only ever flap straight up.
- **Long-press PWR does not power off:** the firmware turns that off at every boot, so the power-on pulse can't
  switch the handheld off again. The slide switch is the on/off.
- **Screen 180°:** service mode, hold RIGHT 1 s.

## Still to confirm on the first real build

| What | Designed for | If it's different |
|---|---|---|
| Waveshare J8 socket depth | ~4 mm; pins go 3.3 mm in | Pins must hold firmly; a 0.3 mm shim under the ONE board's posts changes the depth |
| Waveshare mounting hole size | ≥ 2.2 mm (pegs 1.8 mm) | Sand the pegs |
| Speaker size and lead | Bay 22 × 37 × 7.5 mm; lead ≥ 60 mm | Any box that fits the bay works with tape |
| Which way the slide switch is ON | Up (toward the screen) | Use it the other way; it changes nothing else |
| AXP2101 power-on hold time (set at the factory) | Up to 2 s; the pulse gives 3–8 s | Covered. If it ever doesn't start, see "If something is wrong" |
| USB-C height on the Waveshare edge | Generous opening, 12.8 × 7.8 mm | Widen with a file |
| Acrylic thickness | 1.0 mm (sheet is ±0.1 mm) | The panel may sit a hair proud |

## Design lock

Locked on 2026-10-02 at commit `8729dac` on branch `claude/handheld-core-port`. Changes after the lock are
fixes found on the first build, each listed here.
