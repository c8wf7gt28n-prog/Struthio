# R25 assembly sequence (CASE R11 on PCB R21)

`STRUTHIO_SLIM4_R25_ASSEMBLY.step` holds every part in its rest position. PCB solids in it are envelopes derived from the PCB layer JSON (board outline, part courtyards × heights from `CHECKS/COMPONENT_ENVELOPES_R21.json`); the KiCad file remains the PCB authority.

J1 (panel FPC), J3 (battery) and J4/J5 (speakers) are on the board's back side and face the rear shell, so they are plugged before the board goes in.

1. **Rear shell.** Fit the power plunger into the Ø2.8 bore from inside (collar on the floor). Lay the 0.20 mm foam pad in the window area of the floor.
2. **Speakers.** Seat each CMS-18138A-SP (factory-wired) on the four ledges of its chamber, face up. Pass the lead through the chamber's feedthrough notch toward J4 (left) / J5 (right).
3. **Board, upside down on the bench.** Plug the FH12-20 extension FPC into J1 (insertion from the tab side, +Y). Plug the speaker leads into J4 and J5. Plug the cell's 3-pin lead into J3.
4. **Board into the rear shell.** Turn the board over and lower it onto the rear supports, letting the cell drop through the board window onto the pad and feeding the FPC around the bottom tab edge. Seal the speaker feedthroughs (RTV).
5. **Front shell, face down.** Bond the lens into its rebate. Bond the LCD module front face to the pocket ledge (adhesive frame), FPC end toward the DART opening. Snap the DART rocker trunnions into the pivot bosses. Drop the two flap caps into their holes from below (flange under the plate).
6. **Panel FPC.** Join the panel tail to the extension FPC; lay the run under the module, down to the board between the DART switches.
7. **Close.** Lower the front shell onto the rear shell; the plain 1.0 mm lap joint closes (no detent is modelled yet) and the six front clamp posts trap the board on the matching rear posts.
8. **Check, then film.** Before applying the film: each flap cap clicks its own switch (SW1, SW2); the rocker clicks SW3 and SW4; the power plunger clicks SW5; RESET (SW6) and BOOT (SW7) are reachable through the pinholes. Then apply the ACRYLIC R1 film, registering the flap and DART cutouts on the raised relief.
