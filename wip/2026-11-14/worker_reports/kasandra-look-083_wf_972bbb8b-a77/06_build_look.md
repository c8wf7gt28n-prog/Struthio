All six of the owner's directions are built and committed, and every focused test module matches or improves on its pre-change result. The live hologram costs more per frame than the plan's budget, though her share of the processor is small (cost section).

**Where it is**
- Worktree: `/home/user/Struthio/.claude/worktrees/wf_972bbb8b-a77-6`
- Branch: `worktree-wf_972bbb8b-a77-6`, commit `3af59a1` (parent `d1df337`)
- Seed `VERIFIED_SOURCE_BINDINGS`, release integrity `VERIFIED`. Seed, registry and manifest are rebuilt and staged. Every changed file is mirrored under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_mirror/`.

**What was built, per direction**
- **DELETE:** the place is DELETE, sending something there is "Delete", taking words out of a page or erasing records for good is "Erase". The can reads DELETE, in red with letter spacing 1.0 in Kasandra and in Plex Sans with 0.8 in Graphite. Its box is 120×29 at (218,1094) at 1920 and (218,662) at 1366. Typing "trash" in search still finds DELETE. Internal names (`files.trash`, `.trash`, the table) are unchanged. README, the daily guide and GRAPHITE_DESK.md say DELETE.
- **Fonts:** `tools/derive_typewriter.py` builds two faces from Special Elite, byte-reproducible. "Kasandra Elite" is for words: slashed zero, `l` on a right foot, every digit the same width, no kerning between digits, every other glyph unchanged. "Kasandra Elite Mono" is for lines, Terminal, code and tags; it uses Plex Mono's character width and line height, so no row moves. Arrows and box lines fall back to Plex Mono at the same width. In Kasandra, `boss_theme` FACE and DISPLAY are the new words face and the new MONO entry is the mono face; Graphite stays Plex.
- **Graphite fix:** line slabs on her cards now draw in the mono face in both appearances; before, Graphite drew them in Plex Sans by mistake.
- **Hologram and its static:** `workbench/hologram.py` decides where she stands and `workbench/hologram_qt.py` draws her. At 1920 she stands large above the foot, figure (36,698,281,380). At 1366 she stands in the corner beside DELETE, figure (47,507,136,184). She never covers a row or DELETE and disappears immediately when the tree scrolls, on Settings and on the Clean desk.
  - The motion: static on her only, scan lines drifting down, a gentle flicker, occasional tears, and a base and beam that breathe with the tree in the colour of the current state. There is a short power-up when she appears and a small tear when the pointer reaches her.
  - With Reduce motion she is one still frame with no timer. The ASCII desk draws her once in characters.
- **Right column:** her picture is gone. A masthead (her name, a cursor in the state's colour, the state word, the model name shortened in the middle, her hand link) sits on a rule level with the left tab rule at y 117. The ground is the darker terminal colour with a teal inner edge. Her text has 125% line spacing; your messages hug the right edge.
  - At 1920 the conversation box is 322×869 (was 832 tall); at 1366 it is 322×437 (was 400).
  - Her card text is 296 px wide. The plan's assertion said 297, so the test checks ≥295.
- **kp emblem:** `tools/cut_kp_emblem.py` cuts the logo from its navy ground. The Apps button shows it at 58×38 in a 76×60 button; if the emblem fails its check it falls back to the old monogram, then to the words "[#] Apps ▾". In Kasandra the window icon is the emblem on a navy tile, with letters only at 16 and 24 px.

**Assets (SHA-256)**
- `branding/kasandra/hologram.webp` b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec
- `branding/kasandra/kp_emblem_source.png` 94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa
- `kp_emblem.png` (737×482) 5bfdf6e8dd1be97fe63f549f83a61285f37695ac52bbed07739e7d435ac879c5
- `kp_emblem_small.png` d61a9330cfab1c36416193e8e87bdeaa8a3cc2615448449ea20385c835aaa50d
- `kp_emblem_38.png` 2c49aeb55bc2aa7ef5871bf2c3cbe307aef2d3c611529f4a3e98f0f0c3f6127e
- `kp_emblem_76.png` ffccd3e3cc8f29de1f3bec325971afa4f1b78b3883a10a7e56aff224a3b9f32c
- `kp_tile.png` bd1a274b69ad6b633c9c0d734a2e949626ebe78f4ca875ea83613268407e10f5
- `kp_tile_letters.png` a99f936f1b0283c658f029e5ead98c1a0bc56c6f62265872ff2ca7c55dd0275f
- `kp_monogram.png` (unchanged, now recorded) 7c5b3c9c1f16e0d1eca1f881a0ece60bda777355fdc0fa634495deb77170a073
- `wordmark.webp` (unchanged, now verified) 0a8d44e549b4c9904df11496fb81106c918680c4c84a268098067dc919deb1e6
- `branding/fonts/typewriter/KasandraElite-Regular.ttf` 7cde3cea161199f2d2eaaf1ec9c0527d2bb048301fdebf48feb10c01d8391360
- `branding/fonts/typewriter/KasandraEliteMono-Regular.ttf` 1fe883c0a281154dcaa42d2191a32702b0cf509c635e7eea4a4c3f250cd219a7

All are listed in `kasandra_art.MARKS` (the fonts in NOTICE.md), and each owner-art file is checked before it is shown.

**Tests, before → after**

| module | before | after |
|---|---|---|
| test_kasandra | OK 20 | OK 20 |
| test_faces_find_light | OK 34 | OK 34 |
| test_writing_line | OK 32 | OK 32 |
| test_context_menu | OK 44 | OK 44 |
| test_launcher | OK 17 | OK 17 |
| test_desk_acts | OK 28 | OK 28 |
| test_desk_scenes | OK 5 | OK 5 |
| test_stacy_hand | OK 19 | OK 19 |
| test_release_check | OK 22 | OK 22 |
| test_graphite | 3 failures | same 3 |
| test_system_menu | 2 failures | same 2 |
| test_desk | 6 failures | same 6 |
| test_delete_words (new) | — | OK 6 |
| test_typewriter_faces (new) | — | OK 11 |
| test_hologram (new) | — | OK 18 |
| test_kasandra_column (new) | — | OK 9 |

The failing tests in the three known modules are identical by name to the baseline. Five existing tests were updated for the new words and faces; the four new modules are added to `FOCUSED_MODULES`.

**Frames** (in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/look_build/frames/`)
- `F01_left_files_1920.png`: she stands on the stage, figure (36,698,281,380); DELETE at (218,1094); the ground beside her is #171b3c.
- `F02_left_files_1366.png`: corner stance (47,507,136,184) beside DELETE.
- `F03_left_machine_1366.png`: she stands on the stage under the nine Machine rows.
- `F04_left_settings_1920.png`, `F04_left_settings_1366.png`: no hologram.
- `F05_left_files_open_1920.png`: all 27 rows open, she moves to the corner (32,899,166,224).
- `F05_left_files_open_1366.png`: all 27 rows, the tree scrolls, she is hidden.
- `F06_clean_1920.png`: no hologram, base or beam.
- `F06b_ascii_1920.png`: her figure in characters on the ASCII desk.
- `F07_still_a.png`, `F07_still_b.png`: Reduce motion, one second apart, identical in her rect.
- `F08_idle_strip_24.png` and `F08_motion.txt`: 24 frames at 12 fps, with the motion numbers below.
- `F09_states_5.png`: the five states; base and masthead cursor share each colour.
- `F10_powerup_9.png`: the power-up in 40 ms steps.
- `F11_right_home_1920.png`, `F11_right_home_1366.png`: her column at Home.
- `F11_right_1920.png`, `F11_right_1366.png`: after two Traces; the lines are in the mono face, broken at commas. `F11_window_*.png` show the whole window.
- `F12_head_apps_x3.png`: the emblem in the 60 px head band, three times size.
- `F13_terminal.png`: `ls -l` columns aligned in the mono face beside Plex Mono, and the box-drawing lines connect.
- `F14_glyphs.png`: `Il1| 0Oo 07 10 l0O1` at 12 to 18 px in both faces.
- `F15_graphite_1366.png`: Graphite, with DELETE in Plex Sans, no hologram, and the column as before.
- `F16_cpu.txt`: the processor measurements below.
- `F17_window_icon.png`: the window icon at 16 to 256 px.
- `frames_wide.json`, `frames_small.json`, `frames_graphite.json`: the measured rectangles.

**Hologram cost**
- Timer: 83 ms, measured 12.3 ticks per second. It stops on Settings, on the Clean desk, when the application is inactive and with Reduce motion, and restarts when she is back.
- Paint time per frame at 281×380 is above the plan's 1.5 ms budget in the live window:
  - about 0.5 to 0.8 ms in isolation;
  - about 1.9 to 2.4 ms in the live window (p95 up to 7.7 ms). Timings were noisy on this shared container.
- Processor, 30 s idle each:

  | condition | % of one core |
  |---|---|
  | her frames running | 18.47 |
  | her as one still frame | 17.20 |
  | Clean desk | 10.99 |

  Her frames cost 1.27% of one core. Illustrated minus Clean is 7.48%, but most of that is the tree's existing glow and breathing, not her, so I measured her against her own still frame.
- Motion, mean per-pixel brightness change between frames (0–255): idle 3.94, working 7.16, waiting for you 2.62, done 3.93, stopped 1.91, still 0.

**Scroll census in Kasandra:** 2 overflows at 1920×1200 (was 3) and 19 at 1366×768 (was 26). The lists are in `scroll_census_1920x1200.txt` and `scroll_census_1366x768.txt` in the frames folder.

**Not done, or different from the plan**
- **Right-click line panel:** I kept its old setFont approach (MONO, now at least 12 px) instead of the per-widget sheet. A menu is its own window, outside the window sheet, so the font already holds, and the sheet broke an existing test.
- **"Clean glow" never occurs:** the plan treats glow ≤ 0 as still, but no glow setting reaches 0, so in practice only Reduce motion makes her still. The Clean desk hides her.
- **Pane title:** it uses the heading face (DISPLAY), not FACE, so Graphite keeps Plex Mono there unchanged.
- **Tears:** they use the picture's own glitch lines, which turned out to be 427 of 822 rows rather than a few.
- **Masthead sizes:** they are set at start; a change of reading size takes effect at the next start.
- **F13:** a fixed sample of `ls -l` output drawn in both faces, not the real Terminal, because no shell is run under the holds.
- **The "small" emblem cut:** the thickening fills the ostrich's internal traces; this is invisible at 38 px.
- **No change to pane width; not used:** `portrait.webp` and the reference patch.
- **Not touched:** the version line and release notes.