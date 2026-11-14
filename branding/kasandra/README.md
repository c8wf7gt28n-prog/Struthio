# Kasandra

The owner's second appearance for Graphite (0.8.0): Rules ▸ Desk artwork ▸ Appearance ▸ Kasandra, used from the next start.

- `catalog.json`: the stills, the places they fit (slots), the states of the work each was made for, focal points for
  cropping, sizes and SHA-256 sums. `workbench/kasandra_art.py` reads it; a still whose bytes do not match is not shown.
- `art/`: the eight stills (WebP). `preview/`: small copies of them.
- `palette.json`: the colours by role, as the pack gave them. The colours in force are `workbench/boss_theme.py`
  PALETTES['kasandra'], which follow it.
- `wordmark.webp`: the owner's wordmark, "kasandra protocol" in circuit traces (14 November 2026), trimmed and scaled to
  1400 px wide. SHA-256 0a8d44e549b4c9904df11496fb81106c918680c4c84a268098067dc919deb1e6.

0.8.3 (14 November 2026). Each file below is shown only when its bytes match the SHA-256 given here
(`workbench/kasandra_art.py` MARKS).

- `hologram.webp`: the owner's hologram of Kasandra, 800 x 875, clear edges, violet, its glitch lines drawn in. It stands
  in the left pane's empty lower part (`workbench/hologram_qt.py`).
  SHA-256 b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec.
- `kp_neon.png`: the owner's neon kp logo, the only kp mark ("New logo for our upper right progman.exe menu ;) ... Omg I
  love it"; "Retire any other kp icon"). It is Apps in the head's upper right, about 44 px tall (`workbench/kp_logo.py`),
  its neon drawn round it by Graphite at the strength of the Glow dial. The owner's file (1586 x 992, real alpha) stored its
  neon fringe in pixels of alpha 1 to 9 carrying saturated colour, which cannot be shown as it was; this is its clean
  drawing: every pixel of alpha 200 or more as given, every other pixel clear, trimmed to the drawing (x 102-1502, y 80-917
  of the file), 1401 x 838, cut by `tools/cut_kp_neon.py`.
  The owner's file: SHA-256 70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e (not kept here).
  The clean drawing: SHA-256 f3c6e5fb5cd0f2d61019187bae0d70771378fba5a6c7da27dd8d15d486fd2cc0.

The art was made for this project from the owner's references; it contains no frames or official artwork from Serial
Experiments Lain, whose atmosphere it borrows. Like all artwork under branding/, it is kept back by the owner (RIGHTS.md).
