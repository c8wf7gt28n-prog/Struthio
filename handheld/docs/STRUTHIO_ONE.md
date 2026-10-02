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
| Width | 65.0 mm above y = −30 (straight sides), then a gentle flare to 74.0 mm across the controls |
| Thickness | 23.0 mm, which is about the minimum the header stack allows (~22 mm) |
| Top | soft round corners (R 9), no crown |
| Screen | visible 47.86 mm wide, glass 48.96 mm, side margin 8.02 mm |
| Face | one 1.0 mm clear acrylic panel: the lens over the screen and the front art in one piece. Its cut-outs make a 1 mm well round each key |
| Controls | two round wing buttons, 14 mm across: left flaps up-left, right flaps up-right, **both together flap straight up**. Under them is the rocker for the aim-assisted dart, engraved with a double-ended dart through an aiming reticle. All symmetric about the centreline. |
| Power | slide switch on the player's left side, at the controller |

## Stack-up (front to back)

1. **Face panel.** This is 1.0 mm clear acrylic, laser-cut, with the art printed on its back. The screen window is left clear. It sits on the shell face, inset 2.4 mm from the edge, so the case is still 23.0 mm thick with the panel on. The keys stand 1.8 mm (wings) and 1.5 mm (rocker) above it.
2. **Front shell.** Its printed face is 0.8 mm thick; the panel stuck on top makes it 1.8 mm. It holds the screen window, the wing and rocker caps (held in by their flanges), and the posts the ONE board rests on.
3. **Waveshare ESP32-S3-Touch-LCD-3.5B.** It lies face down, with the glass on the front skin.
4. **ONE board** (1.6 mm, green). It is a plate behind the controls with a strip up the right side. The switches are on its front face. The strip carries the 2 × 16 header, whose short pins push into the Waveshare J8 socket.
5. **Battery** (THOR-503450, 5 × 34 × 52 mm). It lies on the Waveshare board's back, beside the ONE strip.
6. **Speaker.** This is the Waveshare's own boxed speaker, about 30 × 20 × 5.6 mm (**confirm**). It sits in a frame on the back shell and fires out through the grille.
7. **Back shell.** It hooks on at the top. Its four standoffs press the Waveshare board onto the front, and its posts hold the ONE strip down. It has a pocket for the header tails.
   Six M2 × 8 screws go in from the back: four into the Waveshare's own mounting holes, and two at the bottom through the ONE board into the front bosses.

## What the ONE board carries

| Ref | Part | LCSC | Job |
|---|---|---|---|
| J1 | PZ254-2-16-Z-8.5 2 × 16 header | C2894977 | Plugs into the Waveshare J8. **Long pins go through the board**, so the 3 mm end mates. |
| SW1, SW2 | TS-1187A-B-A-B tact switch | C318884 | Left / right wing button (GPIO17 / GPIO18) |
| SW3, SW4 | TS-1187A-B-A-B tact switch | C318884 | Dart rocker, left / right end (GPIO21 / GPIO38) |
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
| Printed parts | `cad/one/stl/`: front, back, two wing buttons, rocker. Each wing button has a wing engraved 0.5 mm deep on top, and the rocker has a dart and reticle. Fill them with a blue paint pen, or leave them plain. |
| Face panel | 1.0 mm clear cast acrylic, cut from `cad/one/panel/one_panel_cut.dxf` and back-printed (see below) |
| Thin double-sided tape | To stick the panel down: clear adhesive transfer tape, or thin strips under the black areas only |

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

## Face panel order

The panel is one flat piece, so any shop that does laser cutting and UV printing on acrylic can make it.
The files are in `cad/one/panel/` and are made by `make_panel.py`:

| File | What it is |
|---|---|
| `one_panel_cut.dxf` / `.svg` | Cut lines in mm, seen from the front: the outline and three cut-outs (two wing buttons, the rocker). Nothing on the panel is narrower than 3 mm. |
| `one_panel_print_MIRRORED.png` | The art to print on the **back** of the panel (600 dpi, 1 mm bleed). The screen window is transparent: **no ink there**. |
| `one_panel_white.png` | White underprint, printed behind the colour so the art isn't see-through. It covers everything except the window. |
| `one_panel_print.png` | The same art as you'll see it from the front, for checking. |
| `one_panel_proof.png` | The art with the cut lines (magenta) and the clear window (blue) marked. |

What to ask the shop for: **1.0 mm clear cast acrylic, cut to the DXF, reverse-printed (colour then white) from the
mirrored PNG, window left clear.** If they mirror files themselves, send `one_panel_print.png` and say so.

Cheaper route: order only a clear cut panel and print the art yourself on clear or white sticker vinyl.
Cut out the screen window and stick it on the back of the panel; the result looks the same from the front.

## Assembly

1. Press the two round wing buttons (engraved wing pointing up and outwards) and the rocker into the front shell from the inside. Slide the filament axle through the rocker.
2. Lay the Waveshare board screen down in the front shell, with USB-C at the top.
3. Lower the ONE board on, so that J1 goes straight into the Waveshare J8 socket. Press it evenly until it sits on the posts.
4. Set the power switch to OFF. Plug the battery into J2 on the ONE board, then lay the battery on the Waveshare board's back. Add the foam pad if you are using it.
5. Plug the speaker into the Waveshare J9 and press it into the frame on the back shell.
6. Hook the back shell on at the top, swing it closed, and fit the six M2 × 8 screws from the back.
7. Peel the panel's backing film. Put tape on the black areas of its back, line it up inside the rim and press it down.
8. Switch on. Charge through the Waveshare USB-C.
9. If the picture is upside down, open service mode and **hold RIGHT for 1 s**. The setting is saved; power-cycle the handheld to play.

## Firmware setting

The dart mode defaults to **ROCKER ONLY**, so holding both wing buttons only ever flaps straight up and never fires a dart.
A bench test with no rocker can switch to mode C (hold both for 0.2 s to dart) in service mode with a LEFT tap.

## Still to confirm on real parts

- Panel fit: the panel is drawn 1.0 mm thick. Acrylic sheet is often ±0.1 mm and tape adds about 0.1 mm, so the panel may sit slightly proud.
- J8 socket depth. The design assumes about 4 mm with a 3 mm pin mate.
- Speaker box size and where its port is.
- SS-12D06-G030 pin offset (assumed 3.45 mm from the body rear), and which throw is ON.
- USB-C height on the Waveshare edge.
- That the power knob sits flush with the wall.
- JLC's orientation for J1 (reversed) and J2.
