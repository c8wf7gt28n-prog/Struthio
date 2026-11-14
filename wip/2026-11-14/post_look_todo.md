# After the look pass (#50) merges, before 0.8.3 ships

1. Burnt-yellow highlight, Kasandra only (owner: "highlighting should be in our burnt yellow ... especially in menus";
   "You measure what is visually pleasing"; "careful how that makes the graphite not look green").
   - Menus and the right-click: solid bar #e2a72e with ink #171b3c (7.79:1), the edge #ffd27a.
   - Lists, trees, tabs, focus: soft #5a3f0c, edge #e2a72e, words #ffd27a (6.86:1 words on fill).
   - Opaque only: never wash yellow over cyan or the old blue (hue goes 86-156, green). Graphite appearance unchanged.
   - Tokens: Kasandra AMBER/AMBER_SOFT/AMBER_EDGE/AMBER_TEXT carry focus and highlight; check every use (151 places).
2. The neon kp logo for the Apps button ("our upper right progman.exe menu"):
   - Source: scratchpad/in/logo_neon/kp_neon.png, SHA-256 70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e,
     1586x992, real alpha. Its neon fringe is stored in alpha=1 pixels (invisible when drawn correctly).
   - Use the clean drawing (pixels with alpha >= 200), content box x102-1504 y80-918; Graphite draws the neon glow
     (wide glow, close glow, cyan ghost left, magenta ghost right, Screen), scaled by the Glow dial; Clean draws none.
   - About 44 px tall in the head (about 74 px wide). Mock: work/neon/kp_neon_drawn_view.png.
   - The owner: "Retire any other kp icon". The neon logo is the ONLY kp mark: delete branding/kasandra/kp_monogram.png and the
     cream emblem the look pass adds (and any small copies it generates), their README lines and SHA entries; port
     test_kasandra's monogram test (tests_integrated/test_kasandra.py:115) to the neon logo; grep for any other kp use.
     The window icon stays Graphite's sharpened point (qt_app.py:2342), and the game keeps its own; neither is a kp mark.
