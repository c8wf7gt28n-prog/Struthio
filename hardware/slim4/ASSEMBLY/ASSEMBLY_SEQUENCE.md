# R26 assembly sequence (CASE R12 on PCB R21)

`STRUTHIO_SLIM4_R26_ASSEMBLY.step` holds every part in its rest position. PCB solids in it are envelopes derived from the PCB layer JSON (board outline, part courtyards × heights from `CHECKS/COMPONENT_ENVELOPES_R21.json`); the KiCad file remains the PCB authority.

J1 (panel FPC), J3 (battery) and J4/J5 (speakers) are on the board's back side and face the rear shell, so they are plugged before the board goes in. Parts and tapes are as specified in `DECISIONS_R26.md`.

1. **Rear shell.** Fit the power plunger into the Ø2.8 bore from inside (collar on the floor). Lay the 0.20 mm foam pad in the window area of the floor.
2. **Speakers.** Seat each CMS-18138A-SP, with its leads (PRODUCTION_GATES.md item 12), on the four ledges of its chamber, face up. Pass the lead through the chamber's feedthrough notch toward J4 (left) / J5 (right).
3. **Board, upside down on the bench.** Plug the FH12-20 extension FPC into J1 (insertion from the tab side, +Y). Plug the speaker leads into J4 and J5. Plug the cell's 3-pin lead into J3 (pin 1 BAT+, 2 NTC, 3 GND).
4. **Board into the rear shell.** Turn the board over and lower it onto the rear supports, letting the cell drop through the board window onto the pad and feeding the FPC around the bottom tab edge. Seal the speaker feedthroughs (RTV).
5. **Screen into the front shell, shell face down.** Peel one liner of the 0.10 mm display tape frame and lay it on the LCD module front with its window on the active area. Peel the second liner and set the 0.70 mm cover glass on the tape, centred on the active area (0.5 mm of tape under its border). Lower module and glass into the pocket from the back, FPC end toward the DART opening: the glass enters the rebate and the tape's outer band bonds the module to the ledge. Press for 10 s.
6. **Controls.** Snap the DART rocker trunnions into the pivot bosses (0.10 mm running clearance). Drop the two flap caps into their holes from below (flange under the plate).
7. **Panel FPC.** Join the panel tail to the extension FPC; lay the run under the module, down to the board between the DART switches.
8. **Close.** Peel the top liner of the 0.10 mm lap tape ring and lay it on the rear-shell lip top. Lower the front shell: the skirt lands on the rear wall (hard stop), the tape bonds the lip to the plate underside, and the six front clamp posts trap the board on the matching rear posts. To open, slide a thin blade along the seam to release the tape and replace the ring.
9. **Check, then film.** Before applying the film: each flap cap clicks its own switch (SW1, SW2); the rocker clicks SW3 and SW4; the power plunger clicks SW5; RESET (SW6) and BOOT (SW7) are reachable through the pinholes. Then apply the ACRYLIC R2 film, registering the flap and DART cutouts on the raised relief; its edge sits 0.20 mm inside the case edge all round.
