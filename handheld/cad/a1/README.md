# STRUTHIO A1 "portable arcade" CAD

| File | What it is |
| --- | --- |
| `STRUTHIO082.scad` | R.A. Peddycoart's A0.8.2 robust-lower-chassis revision, **kept exactly as received** |
| `STRUTHIO083.scad` | A0.8.2 + four fit fixes (USB-C opening, service slot, button pre-travel, battery datum) |
| `STRUTHIO084.scad` | A0.8.3 + the STRUTHIO identity and three more fixes. **Print from this one.** |

A0.8.4, truly STRUTHIO:
- **Wing caps.** The controls are the game's LEFT WING and RIGHT WING. The gold caps have a rounded root, three scalloped primaries and a groove along each feather. They are 28 x 18.5 mm, and `BUTTON_STYLE="round"` restores the A0.8.2 discs.
- **The game palette** (`rules.mjs`): navy shell, gold wings, void art panel.
- **Front art sticker** from the box art, cut exactly to the CAD template (`art/`).
- **Rear mark.** The STRUTHIO wordmark and a gold-ring emblem are debossed 0.5 mm into the battery blister.
- **Fixes:**
  - `wing2d` offsets after scaling. A0.8.2 gave only 58% of each clearance in Y.
  - The art panel's top corners are inset downward. A0.8.2 ran the sticker 4.4 mm up over the screen.
  - The panel now sits below the lens land and is widened to the bottom contour, so the wing tips no longer cut it into slivers.
  - The button holes, backer plate and collars follow the button outline.

## Export and check

    ./export_a1.sh

This exports:
- the STLs (`stl/struthio_a084_*.stl`) and the sticker template (`svg/`);
- the preview renders (`renders/`; `views/*.scad` set the cameras);
- the sticker art: `art/sticker_front_print.png` (600 dpi, 1.5 mm bleed) and `art/sticker_front_proof.png`. This step needs Node + Playwright and is skipped if they are absent;
- the player's-view front, `renders/a084_struthio_front.png`.

It then runs `check_a1.py`, which verifies:
- every part is one watertight solid, and nothing sits outside the outline;
- the USB-C and service openings are clear;
- each stem rests 0 to 0.25 mm before its plunger;
- each cap neck passes its opening and each flange is captured and clears the backer;
- at least 1.5 mm of shell separates each wing from the grille;
- the sticker sits below the lens land, with six clean holes.

Run against A0.8.2, the checks fail at its problems.

Edit the tunable block at the top of the SCAD. Keep the LOCKED A0 datums until the fit coupon (`part="front_fit_coupon"`), a test sticker and one cap have been printed and tested. See section 11 of `docs/STRUTHIO_ESP32_HANDHELD_v0.10.docx`.
