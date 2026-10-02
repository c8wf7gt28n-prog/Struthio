# STRUTHIO ONE

The ONE is the plug-in version of the handheld. One rigid PCB does all of the wiring,
so you don't solder anything, crimp anything or route any wires. The Waveshare board plugs
onto the ONE board, the battery plugs into the ONE board, and the speaker plugs into the
Waveshare board.

Sources: case `cad/one/one_cad.py` (checks: `check_one.py`), board `pcb/one/make_one_pcb.py`
(Gerbers: `export_fab.sh`), and the hardware facts in `HARDWARE_FACTS.md`.
Anything marked **confirm** has not been measured on a real part yet.

## Shape

| | |
|---|---|
| Height | 134.0 mm |
| Width | 65.0 mm above y = −30 (straight sides); 88.0 mm across the controller |
| Thickness | 23.0 mm, which is about the minimum the header stack allows (~22 mm) |
| Top | soft round corners (R 9), no crown |
| Screen | visible 47.86 mm wide, glass 48.96 mm, side margin 8.02 mm |
| Controls | two wings (left/right flap) and a rocker underneath (two buttons), symmetric about the centreline |
| Power | slide switch on the player's left side, at the controller |

## Stack-up (front to back)

1. **Front shell.** It holds the screen window, the wing and rocker caps (held in by their flanges), and the posts the ONE board rests on.
2. **Waveshare ESP32-S3-Touch-LCD-3.5B.** It lies face down, with the glass on the front skin.
3. **ONE board** (1.6 mm, green). It is a plate behind the controls with a strip up the right side. The switches are on its front face. The strip carries the 2 × 16 header, whose short pins push into the Waveshare J8 socket.
4. **Battery** (THOR-503450, 5 × 34 × 52 mm). It lies on the Waveshare board's back, beside the ONE strip.
5. **Speaker.** This is the Waveshare's own boxed speaker, about 30 × 20 × 5.6 mm (**confirm**). It sits in a frame on the back shell and fires out through the grille.
6. **Back shell.** It hooks on at the top. Its four standoffs press the Waveshare board onto the front, and its posts hold the ONE strip down. It has a pocket for the header tails.
   Six M2 × 8 screws go in from the back: four into the Waveshare's own mounting holes, and two at the bottom through the ONE board into the front bosses.

## What the ONE board carries

| Ref | Part | LCSC | Job |
|---|---|---|---|
| J1 | PZ254-2-16-Z-8.5 2 × 16 header | C2894977 | Plugs into the Waveshare J8. **Long pins go through the board**, so the 3 mm end mates. |
| SW1, SW2 | TS-1187A-B-A-B tact switch | C318884 | Left / right wing (GPIO17 / GPIO18) |
| SW3, SW4 | TS-1187A-B-A-B tact switch | C318884 | Rocker left / right end (GPIO21 / GPIO38) |
| SW5 | SS-12D06-G030 slide switch, 3 A | C17179519 | Hard battery cut: BAT_RAW → BAT (header pin 1). Which end is ON: **confirm**. |
| J2 | JST S2B-PH-K-S | C173752 | Battery plug, entry faces right |

All four switches go between their GPIO and GND, using the internal pull-ups. The pads are wired
diagonally, so a switch works however it is rotated. Header pins used are 1 BAT, 3/4/29/30 GND,
5 GPIO21, 7 GPIO38, 16 GPIO17 and 18 GPIO18, in Waveshare's physical numbering
(see `PINOUT_AND_WIRING.md`).

## What you buy

| Item | Notes |
|---|---|
| Waveshare ESP32-S3-Touch-LCD-3.5B | Comes with the 6 Ω 1 W boxed speaker on an MX1.25 lead. Plug it into J9. |
| THOR-503450 LiPo, 1000 mAh | Needs a **JST PH2.0** lead, red on pin 1 (the square pad, marked +). The lead should be about 80 mm long. |
| ONE board, assembled | JLCPCB order (below) |
| 6 × M2 × 8 screws | All from the back: 4 into the Waveshare holes, 2 at the bottom |
| 1.75 mm filament, about 50 mm | The rocker axle |
| Thin foam pad | Optional, behind the battery |
| Printed parts | `cad/one/stl/`: front, back, two wings, rocker |

## JLCPCB order checklist

1. Upload `pcb/one/out/struthio_one_gerbers.zip`. Use 2 layers, 1.6 mm thickness and any colour.
2. Turn on PCB Assembly, top side. Upload `BOM_JLCPCB.csv` and `CPL_JLCPCB.csv`.
3. In the part preview, check two things:
   - **J1**: the black plastic body sits on top. The **long** pins go down through the board and the short ends point up.
     The comment in the BOM says this too. If the preview can't show it, add an order note:
     "J1: mount reversed, long pins through the board, 3 mm end up".
   - **J2**: the plug opening faces right (+x, towards the board's right edge). The battery lead then runs to the right, towards the switch side.
4. The tact switches are JLC basic parts. The header, slide switch and JST socket are extended parts
   (one set-up fee each).

## Assembly

1. Press the wing and rocker caps into the front shell from the inside. Slide the filament axle through the rocker.
2. Lay the Waveshare board screen down in the front shell, with USB-C at the top.
3. Lower the ONE board on, so that J1 goes straight into the Waveshare J8 socket. Press it evenly until it sits on the posts.
4. Set the power switch to OFF. Plug the battery into J2 on the ONE board, then lay the battery on the Waveshare board's back. Add the foam pad if you are using it.
5. Plug the speaker into the Waveshare J9 and press it into the frame on the back shell.
6. Hook the back shell on at the top, swing it closed, and fit the six M2 × 8 screws from the back.
7. Switch on. Charge through the Waveshare USB-C.
8. If the picture is upside down, open service mode and **hold RIGHT for 1 s**. The setting is saved; power-cycle the handheld to play.

## Still to confirm on real parts

- J8 socket depth. The design assumes about 4 mm with a 3 mm pin mate.
- Speaker box size and where its port is.
- SS-12D06-G030 pin offset (assumed 3.45 mm from the body rear), and which throw is ON.
- USB-C height on the Waveshare edge.
- That the power knob sits flush with the wall.
- JLC's orientation for J1 (reversed) and J2.
