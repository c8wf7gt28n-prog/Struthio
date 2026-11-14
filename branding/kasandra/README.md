# Kasandra

The owner's second appearance for Graphite (0.8.0): Rules ▸ Desk artwork ▸ Appearance ▸ Kasandra, used from the next start.

- `catalog.json`: the stills, the places they fit (slots), the states of the work each was made for, focal points for
  cropping, sizes and SHA-256 sums. `workbench/kasandra_art.py` reads it; a still whose bytes do not match is not shown.
- `art/`: the eight stills (WebP). `preview/`: small copies of them.
- `palette.json`: the colours by role, as the pack gave them. The colours in force are `workbench/boss_theme.py`
  PALETTES['kasandra'], which follow it.
- `wordmark.webp`: the owner's wordmark, "kasandra protocol" in circuit traces (14 November 2026), trimmed and scaled to
  1400 px wide. SHA-256 0a8d44e549b4c9904df11496fb81106c918680c4c84a268098067dc919deb1e6.

- `kp_monogram.png`: the owner's monogram, "kp" (kasandra protocol) with teal traces (14 November 2026), cut from its
  dark ground to a clear one and set at 256 x 256. Since 0.8.3 the Apps button's fallback when the emblem's bytes do not
  check. SHA-256 7c5b3c9c1f16e0d1eca1f881a0ece60bda777355fdc0fa634495deb77170a073.

0.8.3 (14 November 2026). Each file below is shown only when its bytes match the SHA-256 given here
(`workbench/kasandra_art.py` MARKS).

- `hologram.webp`: the owner's hologram of Kasandra, 800 x 875, clear edges, violet, its glitch lines drawn in. It stands
  in the left pane's empty lower part (`workbench/hologram_qt.py`).
  SHA-256 b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec.
- `kp_emblem_source.png`: the owner's new kp emblem as given (1254 x 1254, on its flat navy ground): the source of every
  cut below (`tools/cut_kp_emblem.py`). SHA-256 94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa.
- `kp_emblem.png`: the emblem cut from its ground, 737 x 482, clear round it: the master.
  SHA-256 5bfdf6e8dd1be97fe63f549f83a61285f37695ac52bbed07739e7d435ac879c5.
- `kp_emblem_small.png`: the same with its thin pink and violet strokes thickened, for small sizes.
  SHA-256 d61a9330cfab1c36416193e8e87bdeaa8a3cc2615448449ea20385c835aaa50d.
- `kp_emblem_38.png`: the Apps button at 1x, 58 x 38, from the small cut.
  SHA-256 2c49aeb55bc2aa7ef5871bf2c3cbe307aef2d3c611529f4a3e98f0f0c3f6127e.
- `kp_emblem_76.png`: the Apps button at 2x, 116 x 76, from the master.
  SHA-256 ffccd3e3cc8f29de1f3bec325971afa4f1b78b3883a10a7e56aff224a3b9f32c.
- `kp_tile.png`: the window icon in Kasandra, 256 x 256: the emblem on its navy in a rounded square.
  SHA-256 bd1a274b69ad6b633c9c0d734a2e949626ebe78f4ca875ea83613268407e10f5.
- `kp_tile_letters.png`: the window icon at 16 and 24 px, 64 x 64: the same tile with the letters kp only.
  SHA-256 a99f936f1b0283c658f029e5ead98c1a0bc56c6f62265872ff2ca7c55dd0275f.

The art was made for this project from the owner's references; it contains no frames or official artwork from Serial
Experiments Lain, whose atmosphere it borrows. Like all artwork under branding/, it is kept back by the owner (RIGHTS.md).
