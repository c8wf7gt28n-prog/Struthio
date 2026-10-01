# STRUTHIO A1 "portable arcade" CAD

- `STRUTHIO082.scad`: R.A. Peddycoart's A0.8.2 robust-lower-chassis revision, **kept exactly as received**.
- `STRUTHIO083.scad`: the same file with four fit fixes (header "A0.8.3 FIT FIXES"). **Print from this one.**
  1. USB-C opening and its U-boss follow the bottom arch (the A0.8.2 cut left ~1.1 mm of wall across the port, and the boss poked out of the arch).
  2. Side service slot (and the optional power-switch aperture) starts inside the cavity (A0.8.2's cut missed the waist wall).
  3. Button stems stop 0.10 mm short of the B3F plungers (A0.8.2 pressed them 0.9 mm, more than the 0.25 mm travel).
  4. Battery reference sits on the board's back face.

## Export and check

    ./export_a1.sh      # STLs, sticker template SVG, preview renders, then check_a1.py

`check_a1.py` verifies: one watertight solid per part, USB-C and service openings clear, nothing outside the outline, stem-to-plunger gap between 0 and 0.25 mm, caps captured. Run against A0.8.2 it fails on exactly the four problems above.

Outputs: `stl/struthio_a083_{front,back,left_button,right_button}.stl`, `svg/struthio_a083_front_sticker.svg`, `renders/` (`views/*.scad` set the preview cameras).

The tunable industrial-design block at the top of the SCAD is the place to edit; keep the LOCKED A0 datums until the fit coupon (`part="front_fit_coupon"`) and one cap have been printed and tested. See section 11 of `docs/STRUTHIO_ESP32_HANDHELD_v0.7.docx`.
