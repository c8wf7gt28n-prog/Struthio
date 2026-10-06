# Production gates — open

This is a cross-platform debug package. It is not a fabrication release.

## PCB
- R21 native board is included and preserved unchanged. Complete schematic-to-board reconciliation and electrical intent review.
- Re-run native KiCad DRC/ERC with the final tool/version and confirm all nets, constraints, clearances, creepage, impedance, and board stackup.
- Select exact orderable/assembly parts, approved footprints, alternate parts, BOM/CPL, and assembly-side constraints. Verify all JLCPCB capabilities and quoting limits against current files before ordering.
- Complete power-tree, MIPI, USB, audio, battery/charging, connector, protection, programming, and test-point review.

## Case and screen
- R10 is the front shell/screen/control candidate only. Create the matching rear enclosure and fastener/seal strategy.
- Confirm the HOTHMI module drawing, active area, FPC orientation/exit/fold, connector and clearance against the actual supplier drawing.
- Verify buttons, switch travel, hard stops, printed part tolerances, 2 mm minimum webs, flex/board clearance, and full assembled thickness.
- Build the speaker chambers, acoustic outlet path and seals around the actual drivers; current R10 shell has grille openings but no validated chambers or speakers.
- Resolve the battery position, connector, protection, cable path, clearances, and serviceability.

## Acrylic face layer
- 0.20 mm is a planning assumption, not a selected stock thickness. Choose the actual film/adhesive stack and vendor process.
- Verify perimeter, control/vent cutouts, optical clarity, haze/reflection, screen readability, corner radii, application registration, and tolerance.
- Create final printed artwork, ink/white-mask separations, relief/texture and adhesive instructions only after the visible design is approved.
- Obtain a supplier preflight for SVG/DXF layer naming, polarity, kerf/offset, and material compensation.

Release only after these gates are closed and a physical fit/acoustic/optical prototype passes review.
