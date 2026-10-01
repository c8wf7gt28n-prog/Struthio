# STRUTHIO HANDHELD · the manual's text (v0.9, the C port and the A1 portable arcade). Layout helpers are
# in build_manual.py. Every figure quoted here comes from handheld/run_tests.sh
# or the documents in handheld/docs; keep them in step when either changes.
import os

VERSION = 'v0.9'
DATE = '2026-10-01'
FILENAME = 'STRUTHIO_ESP32_HANDHELD_v0.9.docx'
TITLE = 'STRUTHIO ESP32-S3 Handheld Manual v0.9 - the C port and the A1 portable arcade'
SUBJECT = 'The C port of STRUTHIO ARCADE 1.8.0 on the Prototype A0 handheld: architecture, controls, graphics, firmware, build, verification and bring-up'
DESCRIPTION = 'v0.9: board adapter ported from the vendor example, real-header compile, band order. v0.8: A1 made truly STRUTHIO (CAD A0.8.4). v0.7: A1 portable-arcade hardware. v0.6: rewritten for the C port. v0.5: bit-exact simulation. v0.4: A0 CAD and wiring lock.'
HEADER = 'STRUTHIO  /  ESP32-S3 HANDHELD  /  C PORT MANUAL'
FOOTER_VERSION = 'C Port Manual v0.9'


def write(d, root, v04):
    R = lambda *p: os.path.join(root, *p)

    # ---- cover ---------------------------------------------------------------------------
    d.cover('STRUTHIO', 'ESP32-S3 DEDICATED HANDHELD',
            'Manual for the C port of STRUTHIO ARCADE 1.8.0 on Prototype A0',
            f'C PORT MANUAL  /  {VERSION}  /  {DATE}',
            'Supersedes the v0.4 prototype path. The game now runs as portable C, proven against the browser build tick '
            'for tick; the browser renderer is ported and measured; the firmware is written. v0.7 adds the A1 hardware: '
            'a portable arcade in the spirit of the 1990s LCD handhelds. What remains needs the board.')
    d.gold('WHAT THIS MANUAL DESCRIBES', [
        'The handheld software as it exists in `handheld/` on branch `claude/handheld-core-port`: the C simulation, the '
        'two-button input layer, the C port of the browser renderer, the asset pack, the ESP-IDF firmware, the host '
        'tools that prove each of them, and the hardware they run on.',
        'The browser build (JavaScript, STRUTHIO ARCADE 1.8.0) is no longer the thing being planned. It is the '
        'reference the C port is checked against: its sources are hashed, its games are recorded, and its frames are '
        'captured. Nothing in the handheld runs JavaScript.'])
    d.label('STATE OF THE PORT IN ONE PARAGRAPH')
    d.p('The C core reproduces the browser simulation bit for bit: 75,144 recorded ticks across five traces give the '
        'same SHA-256 state digest on every tick. The C scene builder produces the browser\'s exact draw list on every '
        'one of those ticks. The C panel renderer draws the browser\'s picture at 320 x 480 from an 8.3 MB asset pack, '
        'within 24.9-30.3 dB of the browser frame. The firmware is written around all of it and type-checks against a '
        'stand-in for the ESP-IDF headers. It has not yet been built with the real toolchain or run on the board.')
    d.cover_end()

    # ---- 1 -------------------------------------------------------------------------------
    d.h1('1. Status: what is proven and what is not')
    d.p('Every claim in this manual is one of three kinds. **Proven** means a check in `handheld/run_tests.sh` '
        'demonstrates it on every run. **Measured** means a number was taken on the host and is reported as such. '
        '**Not yet** means it needs the physical board, parts or the ESP-IDF toolchain.')
    d.table(['Area', 'Status', 'Evidence'], [
        ['Simulation (physics, AI, jousts, eggs, rings, rounds, lives, scoring)', '**Proven bit-exact**',
         '`host/replay`: per-tick SHA-256, digest chain and final digest equal the browser on 5 traces, 75,144 ticks'],
        ['Input normalizer (flap queue, 100 ms chord, 8-tick flap buffer)', '**Proven bit-exact**', 'the same replay checks every input frame'],
        ['Rulebook constants', '**Proven**', '`core/struthio_rules.h` is generated from `rules.mjs`; the core static_asserts against it'],
        ['Scene builder (every quad the browser draws)', '**Proven equal**', '`host/scene_check`: instance-list hash equals the browser on all 75,144 ticks'],
        ['Rasterizer, materials, post (float reference)', 'Measured', '`host/raster_check` vs WebGPU at 768 x 1152: 35.7-50.6 dB over 18 frames'],
        ['Device panel renderer + asset pack', 'Measured', '`host/panel_check`: game picture 24.9-30.3 dB, HUD 43.2 dB; two-core band split identical to one pass'],
        ['Decomposed ambience used by the device', '**Proven**', '`host/amb_test`: worst difference 0.00000 against the shader formula'],
        ['Wing buttons (debounce, chord timing, DART trials, service hold)', 'Host-tested', '`firmware/host_test`; DART trial report on the bots\' press timelines'],
        ['Firmware (tasks, 60 Hz loop, frames, NVS, watchdog, service mode)', 'Compiled against the real headers', '`firmware/idf_check`: every source against ESP-IDF 5.5.5 and the board drivers, real sdkconfig, -Werror (syntax and types; not linked)'],
        ['Two-core band hand-off to the panel', '**Proven on host**', '`host/band_order_test`: 0 bands misplaced; the earlier scheme misplaced ~79%'],
        ['`idf.py build`, flashing, on-device replay', '**Not yet**', 'the Xtensa toolchain download is blocked in the build environment'],
        ['Panel, power and backlight for the Waveshare 3.5B', 'Ported, not run', 'from Waveshare\'s own ESP-IDF example (pins, init order, AXS15231B init commands, AXP2101 rails); needs the board'],
        ['Audio (ES8311)', '**Not yet**', 'stub; no device sound assets yet'],
        ['Renderer speed on the ESP32-S3', '**Not yet**', '8-10 ms per frame on one x86 core; the device figure comes from the boot log'],
        ['Fit, switch feel, battery, speaker, USB-C extension', '**Not yet**', 'needs prints and parts (CAD unchanged from v0.4)'],
    ], [3.2, 1.4, 4.4])
    d.gold('A0 PASS CONDITION (UNCHANGED)', 'POWER ON -> STRUTHIO STARTS -> A PLAYABLE ROUND IS COMPLETED USING ONLY THE TWO PHYSICAL BUTTONS.')

    # ---- 2 -------------------------------------------------------------------------------
    d.h1('2. Architecture of the C port')
    d.p('The port keeps the game and replaces the platform. The simulation and the input normalizer are translated '
        'line for line; the renderer is translated stage by stage and fed from baked assets; everything specific to the '
        'board sits behind one adapter file. Each layer is portable C11 that builds and is tested on a desktop.')
    d.table(['Layer', 'Files', 'What it is'], [
        ['Simulation core', '`core/struthio_sim.c`, `struthio_core.h`, `struthio_tower.c` (generated), `struthio_rules.h` (generated)',
         'The 1.8.0 game: state, physics, AI, jousts, eggs, rings, rounds, events. No heap, no floats in state.'],
        ['Digests', '`core/struthio_digest.c`', 'Canonical JSON and SHA-256, byte-identical to the browser\'s `digest()`. Validation only.'],
        ['Input normalizer', '`core/struthio_input.c`', 'The browser InputNormalizer, wing path: flap queue, chord rewrite, flap buffer.'],
        ['Replay', '`core/struthio_replay.c`', 'Plays a golden trace through the normalizer and the sim; used on the host and in service mode.'],
        ['Wing buttons', '`firmware/main/struthio_buttons.c`', 'GPIO samples -> debounced presses with raw-edge times -> normalizer; DART trials; service hold.'],
        ['Scene builder', '`render/struthio_scene.c`, `struthio_scene_data.c` (generated)', 'Port of `scene.mjs`, ring effects, bird animation, camera and session feel: the browser\'s quad list.'],
        ['Reference rasterizer', '`render/struthio_raster.c`', 'Float port of the WebGPU sprite pass and post pass, used to prove the materials.'],
        ['Panel renderer', '`render/struthio_panel.c`', 'The device renderer: 320 x 480 in 16-line bands, HUD layers, lookup-table post.'],
        ['Asset pack', '`render/struthio_pak.c`, `host/make_pak.c`', 'Textures and HUD at panel density in one file, mapped from flash.'],
        ['Greybox renderer', '`render/struthio_greybox.c`', 'Simple fallback picture when no asset pack is flashed; used by service mode.'],
        ['Firmware', '`firmware/main/main.c`, `service.c`', 'Tasks, 60 Hz clock, frame hand-off, NVS, watchdog, service mode.'],
        ['Board adapter', '`firmware/main/board_waveshare_35b.c`, `board.h`', 'Panel, power, backlight, audio. The one file finished on the bench.'],
    ], [1.6, 3.0, 4.4])
    d.h2('Runtime topology')
    d.code([
        'POWER ON -> ROM -> 2nd-stage bootloader -> app_main()',
        '  wing GPIO17/18 (pull-up, active low) -> NVS: best score, DART trial',
        '  board_power_init, board_display_init',
        '  both wings held 650 ms within the 800 ms boot guard?  -> SERVICE MODE (never returns)',
        '  board_audio_init, backlight, map asset pack (falls back to greybox if absent)',
        '  new_run(): seed from esp_random(), st_start_run()',
        '  core 0: wings   1 kHz   debounce -> normalizer',
        '  core 1: game    60 Hz   normalizer frame -> st_step -> events -> scene + HUD (every tick)',
        '                          -> frame slot published every 2nd tick',
        '  core 0: render  <=30 fps  even 16-line bands -> panel as each band finishes',
        '  core 1: render1 with render: odd bands of the same frame (below game priority)'])
    d.h2('Tasks and priorities')
    d.table(['Task', 'Core', 'Priority', 'Rate', 'Rule'], [
        ['`wings`', '0', '10', '1 kHz', 'Samples both switches; never blocks.'],
        ['`game`', '1', '9', '60 Hz fixed', 'Rational microsecond schedule (exactly 60 ticks/s on average); on a stall longer than 4 ticks it resynchronises instead of bursting. Watchdog-registered.'],
        ['`render`', '0', '5', '<= 30 fps', 'Takes the newest published frame; may drop frames; never slows the game. Writes NVS.'],
        ['`render1`', '1', '4', 'with `render`', 'Renders the odd bands of the frame `render` hands it.'],
    ], [1.2, 0.6, 0.8, 1.2, 5.2])
    d.p('Frames are handed over through three slots in PSRAM (each holds a quad list, the HUD model and the frame '
        'parameters). The game task always writes a slot that is neither the newest published one nor the one being '
        'drawn, so neither side ever waits for the other.')

    # ---- 3 -------------------------------------------------------------------------------
    d.h1('3. Playing: the two wing buttons')
    d.p('Normal power-on goes straight into a run. There is no menu, no START button and no touch input.')
    d.table(['Action', 'Buttons', 'Notes'], [
        ['Flap left / right', 'press that wing', 'Flaps at once; the chord window adds no latency to the first press.'],
        ['Steer', 'hold a wing', 'Continuous horizontal control while the switch is down.'],
        ['Straight-up flap', 'both wings within 100 ms', 'The opposite wing inside 100 ms rewrites the pending flap to STRAIGHT, exactly as the browser does.'],
        ['DART (trial C, default)', 'hold both wings 200 ms', 'Dives toward the side the bird faces. Trials A and B can be selected in service mode.'],
        ['New run after GAME OVER', 'hold both wings', 'Accepted one second after GAME OVER; a single flap cannot skip the result screen.'],
        ['Service mode', 'hold both wings while powering on', 'Hidden diagnostics; power-cycle to play.'],
    ], [2.0, 2.2, 4.8])
    d.h2('Why DART is trial C')
    d.p('The browser fires DART with a downward flick, which two buttons cannot make. Three gestures were implemented '
        'and replayed against the golden bots\' millisecond press timelines, counting darts the bots never asked for:')
    d.table(['Trial', 'Gesture', 'Unwanted darts per minute', 'Why'], [
        ['A  HOLD', 'one wing held 230 ms', '69-78', 'Steering is holding a wing.'],
        ['B  TAP-HOLD', 'release, re-press within 220 ms, hold 60 ms', '40-49', 'Flapping while steering is a quick re-press.'],
        ['C  BOTH-HOLD', 'both wings held 200 ms', '0.3-2.0', 'Uses the one idle gesture: both wings held after the straight-up chord.'],
    ], [1.4, 2.6, 1.8, 3.2])
    d.warn('STILL A DECISION FOR A HUMAN THUMB', 'C is the default because it is the only trial that does not collide with '
           'normal play on recorded inputs. It is locked only after real play on real switches (bring-up step 7).')

    # ---- 4 -------------------------------------------------------------------------------
    d.h1('4. The simulation core')
    d.p('`core/` is a platform port of the 1.8.0 simulation: every stage runs in the same order with the same integer '
        'arithmetic. A tick is one call:')
    d.code([
        'st_state_t s;  st_events_t ev;',
        'st_state_init(&s, seed);          // ATTRACT shell, empty world, 11 lives',
        'st_start_run(&s, &ev);            // PLAY shell, tower built',
        'for (;;) {',
        '    st_input_t in = st_norm_frame(&norm, st_can_accept_buffered_flap(&s));',
        '    st_step(&s, &in, &ev);        // one deterministic 60 Hz tick; events carry serials',
        '}'])
    d.table(['Property', 'Value'], [
        ['Logical scene', '256 x 384 px, 256 integer subpixels per pixel, wrap 65,536 subpixels'],
        ['Tick', '60 Hz fixed'],
        ['State', '`st_state_t`, 2,388 bytes, no pointers, no floats; copied whole for snapshots'],
        ['Actors / events', 'up to 24 actors, 96 events per tick'],
        ['Tower', '43 platforms, 10 ring sets of 6 (generated from `tower.mjs`)'],
        ['Cost', '0.9-2.0 µs per tick on x86-64; about 60 µs with the per-tick SHA-256. The ESP32-S3 figure comes from service mode.'],
    ], [2.0, 7.0])
    d.h2('Where the JavaScript semantics were preserved')
    d.table(['Trap', 'How the C core handles it'], [
        ['Integer width', 'Explicit `int32_t` state, `int64_t` intermediates where JavaScript Number was wider.'],
        ['Truncating division, modulo', 'The authority\'s `trunc`/`mod` helpers ported as helpers; no raw `%` on signed values.'],
        ['RNG', 'xorshift32 ported exactly; one changed bit would fail the replay within a few ticks.'],
        ['Event order', 'Same step sequence as `step.mjs`; events and their serials are part of each tick\'s digest.'],
        ['Floating point', 'The only doubles are the tower\'s altitude-band comparisons, which the authority also does in IEEE double.'],
        ['Constants', '`struthio_rules.h` is generated from `rules.mjs`; the core `static_assert`s its own constants against it.'],
    ], [2.2, 6.8])
    d.h2('Port authority')
    d.p('`docs/PORT_AUTHORITY.md` lists the SHA-256 of every browser source the core is a port of (rules, fixed, '
        'rng, canonical, sha256, state, world, physics, ai, tower, step, game, input, session, camera). '
        '`tools/port_authority.mjs --check` fails if any of them changes, until the change is ported and the goldens '
        're-recorded. Against the 1.6.0 snapshot v0.4 used, only `step.mjs` differs: since 1.7.0, rising straight up '
        'always wins a joust. That is why the port follows 1.8.0.')

    # ---- 5 -------------------------------------------------------------------------------
    d.h1('5. Input: from switch to input frame')
    d.steps([
        'The `wings` task samples GPIO17 and GPIO18 at 1 kHz (FreeRTOS tick 1 ms).',
        'Each switch is debounced independently: 8 ms stable. The debounced press keeps the time of its **raw** edge, so the chord window measures real thumb timing, not debounce delay.',
        'A press becomes a wing "pointer" in the normalizer: it queues a directional flap at once (4-deep queue).',
        'The opposite wing within 100 ms rewrites the pending flap to STRAIGHT, or queues a STRAIGHT chord if the flap already fired. The chord depends only on press times.',
        'Every 60 Hz tick the game task takes one input frame: held state for steering, at most one flap, chord and DART edges. A flap that cannot fire yet waits up to 8 ticks, gated like the browser session.',
        'After a death or GAME OVER the normalizer is cleaned up exactly as the browser session does.'])
    d.p('The v0.4 mapper differed from the browser on three points (one queued flap, a chord that needed the first '
        'wing still held, no flap buffer). v0.5 replaced it with an exact port; the replay proves the frames equal.')

    # ---- 6 -------------------------------------------------------------------------------
    d.h1('6. Graphics: the browser\'s picture in C', new_page=True)
    d.p('v0.4 planned a "deliberately small" renderer that would not emulate WebGPU. The port went the other way: the '
        'browser renderer is translated stage by stage, and each stage is measured against what Chromium actually '
        'renders, captured headless with the real WebGPU renderer and DOM HUD.')
    d.figure(R('docs', 'renders', 'panel_vs_browser_2809.png'),
             'FIGURE 1 - The C panel renderer (left) and the browser (right) at the same tick of the mortal trace. 320 x 480, as on the panel.', 0.82)
    d.h2('The pipeline')
    d.table(['Stage', 'Browser source', 'C', 'Proof'], [
        ['Scene: sprites, islands, rings, props, popups, banners, menu as instanced quads', '`render/scene.mjs`, ring-fx, bird-animation, camera, session feel',
         '`struthio_scene.c`', 'equal draw list on all 75,144 ticks'],
        ['Sprite pass: depth, premultiplied blend, materials', 'WGSL in `renderer.mjs`', '`struthio_raster.c`', '35.7-50.6 dB vs WebGPU at 3x'],
        ['Post: tone, Arcade grade, bloom, scanlines, vignette', 'WGSL post pass', '`st_raster_post`', 'quality 0 and 2 compared'],
        ['HUD bar, toasts, page frame', 'DOM + CSS', 'captured layers, composed by `struthio_panel.c`', '43.2 dB vs the DOM render'],
        ['Device picture', 'the canvas in a 320 x 480 window', '`struthio_panel.c` + asset pack', '24.9-30.3 dB (below)'],
    ], [2.6, 2.4, 2.0, 2.0])
    d.h2('What the panel shows')
    d.p('In a 320 x 480 window the arcade page lays its 768 x 1152 canvas out at 286 x 429 at (17, 51), with the HUD '
        'bar above and the frame around it. The handheld reproduces that page, with the wing buttons in place of the '
        'touch deck. The browser shows the canvas with nearest-pixel scaling, which drops thin lines, stars and glyph '
        'strokes. The handheld instead targets the full canvas area-filtered to 286 x 429: textures are prefiltered to '
        'that density offline, so the device reads about one texel per pixel.')
    d.h2('The panel renderer')
    d.bullets([
        'Draws straight into 16-line bands (30 per frame); there is no framebuffer. Each band is cleared, the quads that touch it are drawn with a 16-bit depth test and premultiplied blending, then post, then the HUD.',
        'Post at quality 0: tone (exposure 1.8, white 1.6) per channel through a 256-entry table, then the Arcade grade through a 65,536-entry RGB565 table.',
        'The world plates carry the ambience per texel (lit, star coverage, glint weights). Per plate row and per frame terms are computed once, so no transcendental function runs per pixel except the twinkle of actual star texels.',
        'The turning moon reads a per-texel latitude/longitude table and a filtered longitude map: no trigonometry per pixel.',
        'The HUD model ports `hud.mjs` and its CSS: toast fade 160 ms, gold-ring pulse 1.2 s to brightness 1.35, bar fade-in 140 ms.',
        'Bands go out in RGB565, byte-swapped for the panel. Even bands are drawn on core 0 and odd bands on core 1; the host check proves the split frame is identical to one pass.'])
    d.h2('The asset pack')
    d.p('`host/make_pak` builds `build/assets/struthio.pak` (8.3 MB) from the browser\'s exported textures and the HUD '
        'capture. `idf.py flash` writes it to the `assets` partition; the firmware maps it and reads textures through '
        'the flash cache. It is never copied to RAM.')
    d.table(['Entry', 'Size', 'Format'], [
        ['`world_rear`, `world_near`', '286 x 858 each', 'RGB565 + ambience bytes (lit, star coverage, moon-disk flag / alpha, glint weights)'],
        ['`bird_ink6`, `bird_ink1/2/3`', '572 x 429 each', 'RGB565 + 8-bit alpha; player and rival inks pre-applied'],
        ['`atlas`', '763 x 763', 'RGB565 + 8-bit alpha; island palette pre-applied'],
        ['`atlas_hi`', '512 x 568', 'full-resolution glyph and swatch strip (drawn magnified)'],
        ['`globe_map`, `globe_lut`', '384 x 192, disk box', 'the moon\'s longitude map and per-texel row/longitude'],
        ['`chrome`', '320 x 480', 'the page frame, RGB565'],
        ['427 HUD layers', '613 KB', 'run-length coded premultiplied RGBA; round toasts coded against a base toast'],
    ], [2.4, 1.8, 4.8])
    d.h2('Measured against the browser')
    d.table(['Check', 'Result'], [
        ['Game picture vs the browser frame area-filtered to 286 x 429, nearest sampling (default), 18 frames', '24.9-30.3 dB'],
        ['Same, bilinear sampling (`BILINEAR=1`, 4 reads per pixel)', '28.2-31.2 dB'],
        ['For scale: the browser\'s own nearest-pixel display vs the same reference', '27-29 dB'],
        ['HUD from the pack vs the DOM HUD, after RGB565', '43.2 dB'],
        ['Host time per 320 x 480 frame (one x86 core)', '8-10 ms'],
    ], [6.6, 2.4])
    d.p('The remaining differences sit on sprite edges, where a pixel\'s footprint straddles texels; flat areas match.')
    d.figure(R('docs', 'renders', 'panel_vs_browser_climb_6000.png'),
             'FIGURE 2 - C panel (left) and browser (right), climb trace tick 6000.', 0.82)
    d.h2('Not reproduced on the device')
    d.bullets([
        'Bloom, halo, scanlines and vignette (quality 1-2). The reference rasterizer has them; the device runs quality 0 to keep frame time.',
        'The islands\' 0-4% brightness pulse on the music beat.',
        'Text is Chromium\'s greyscale anti-aliasing, captured with `--disable-lcd-text`; the HUD is a set of captured layers, not a font renderer.'])

    # ---- 7 -------------------------------------------------------------------------------
    d.h1('7. Firmware')
    d.h2('Boot sequence')
    d.steps([
        'Configure GPIO17/18 as pulled-up inputs; initialise NVS (erased and re-initialised if its format changed).',
        'Load the DART trial (`dart`, default C) and the best score (`best`).',
        'Allocate the greybox framebuffer and a DMA band; initialise power and the panel.',
        'Boot guard: for 800 ms, if both wings have been held 650 ms, enter service mode.',
        'Reset the input state (presses during the guard are discarded), initialise audio, backlight on.',
        'Map the asset pack. With a working panel and a valid pack the panel renderer runs; otherwise the greybox renderer.',
        'Start a run with a seed from the hardware RNG and start the tasks. No splash, no menu.'])
    d.h2('Memory')
    d.table(['Item', 'Size', 'Where'], [
        ['Frame slots (quad list 4,096 x 80 B + HUD model + parameters) x 3', '~984 KB', 'PSRAM'],
        ['Post lookup tables', '130 KB', 'internal RAM (PSRAM fallback)'],
        ['Band workspaces x 2 (colour, depth, HUD row)', '2 x 35 KB', 'internal RAM'],
        ['Band line buffers x 2 (16 x 320 RGB565)', '2 x 10 KB', 'internal DMA RAM'],
        ['Game state, scene state', '2.4 KB + 17 KB', 'internal RAM'],
        ['Asset pack', '8.3 MB', 'flash, memory-mapped'],
    ], [5.2, 1.6, 2.2])
    d.h2('Flash partitions (16 MB)')
    d.table(['Name', 'Type', 'Offset', 'Size', 'Use'], [
        ['nvs', 'data / nvs', '0x9000', '24 KB', 'best score, DART trial'],
        ['phy_init', 'data / phy', '0xF000', '4 KB', 'RF calibration'],
        ['factory', 'app', '0x10000', '4 MB', 'firmware, embedded `climb.trace` for service mode'],
        ['assets', 'data / 0x40', 'after factory', '11 MB', 'the asset pack (8.3 MB used)'],
    ], [1.2, 1.4, 1.4, 1.0, 4.0])
    d.h2('Persistence and recovery')
    d.bullets([
        'NVS holds two values: `best` (high score) and `dart` (DART trial). Writes happen in the render task, never inside a game tick.',
        'Power-off ends the run; there is no checkpoint.',
        'Task watchdog: 3 s, panic and reboot. A hung game or render task returns the toy to a fresh run.'])
    d.h2('Service mode')
    d.p('Hold both wings while powering on. The screen and the USB log show:')
    d.bullets([
        'build, reset reason, free PSRAM and internal heap;',
        'live wing states, debounced press counts, darts fired, the active DART trial;',
        '**on-device golden replay**: the embedded `climb.trace` (10,011 ticks) through the C core with every tick\'s SHA-256 checked against the browser, then again without digests to time the bare simulation (both include a one-tick yield every 256 ticks, so they over-report slightly);',
        'a panel benchmark: full 320 x 480 presents, ms per frame.'])
    d.p('LEFT tap cycles the DART trial (A, B, C, off; saved). RIGHT tap re-runs the replay and benchmark. '
        'Power-cycle to play.')

    # ---- 8 -------------------------------------------------------------------------------
    d.h1('8. Building, testing and flashing')
    d.h2('On a desktop (no board needed)')
    d.code([
        'handheld/run_tests.sh             # every check that does not need the board',
        'make -C handheld/host test        # bit-exact replay of the five goldens',
        'make -C handheld/host scene       # scene builder vs the browser draw lists',
        'make -C handheld/host pak         # build/assets/struthio.pak',
        'make -C handheld/firmware/host_test run       # button tests + DART report',
        'make -C handheld/firmware/host_test compile   # hardware-independent sources vs a header shim',
        'handheld/firmware/idf_check/idf_check.sh      # every source vs the real ESP-IDF 5.5.5 headers'])
    d.p('Needs Node 22 and a C compiler. The graphics comparisons need the browser references in `handheld/build/reference` '
        '(not committed: they are large). Produce them with headless Chromium:')
    d.code([
        'node handheld/tools/reference/capture.mjs --frames --textures   # WebGPU via SwiftShader',
        'node handheld/tools/reference/hud_capture.mjs                  # DOM HUD layers'])
    d.p('`run_tests.sh` runs the scene, rasterizer, HUD and panel comparisons and builds the pack when those references '
        'exist, and says SKIP when they do not.')
    d.h2('On the board')
    d.code([
        'make -C handheld/host pak         # the asset pack',
        'cd handheld/firmware',
        'idf.py set-target esp32s3',
        'idf.py build flash monitor        # app + asset pack to the assets partition'])
    d.p('ESP-IDF 5.5 or newer (Waveshare\'s requirement for this board). `sdkconfig.defaults` sets 16 MB flash, the '
        'custom partition table, octal PSRAM at 80 MHz, 240 MHz CPU, 1 kHz FreeRTOS tick, the 3 s task watchdog and the '
        'USB Serial/JTAG console. Without the pack in flash the build warns and the firmware runs the greybox renderer.')
    d.warn('NOT YET BUILT WITH THE REAL TOOLCHAIN', ['The build environment cannot download the Xtensa compiler. Instead, '
           '`firmware/idf_check/idf_check.sh` fetches ESP-IDF 5.5.5 and the board driver components by git (pinned), '
           'generates the real `sdkconfig.h` from `sdkconfig.defaults` with Espressif\'s kconfgen, and compiles every '
           'firmware source against them with -Wall -Wextra -Werror. That catches wrong struct fields, signatures and '
           'missing functions; deliberately broken copies are rejected.',
           'It is still not `idf.py build`: nothing is compiled for Xtensa or linked. The first real build may need small fixes.'])

    # ---- 9 -------------------------------------------------------------------------------
    d.h1('9. How the port is verified')
    d.p('The rule from v0.4 stands: do not judge the port by whether a bird appears to move similarly. Each layer is '
        'compared with the browser on recorded data, and a mismatch is a bug until explained.')
    d.h2('Golden traces')
    d.p('`tools/golden_export.mjs` runs the unmodified browser `Game` and `InputNormalizer` headless while a bot presses '
        'two virtual wing buttons with millisecond timing. Each tick stores the presses, the frame the normalizer '
        'produced and the first 64 bits of the tick\'s SHA-256 state digest (`STRGOLD1` format). The C side replays the '
        'same presses through its own normalizer and simulation, serialises its state to the same canonical JSON, hashes '
        'it and must match on every tick.')
    d.table(['Trace', 'Ticks', 'Covers'], [
        ['climb', '10,011', 'three round clears, gold ring, jousts, eggs, darts, chords (test shield on)'],
        ['mortal', '14,143', 'real lives: 12 deaths, an extra life, GAME OVER'],
        ['duel', '20,000', 'joust losses, frequent darts and chords'],
        ['late', '10,990', 'rounds 9-11 (8-rival cap, top tiers, short egg timers)'],
        ['raw', '20,000', 'frames straight into the sim: chord during cooldown, side-less darts'],
    ], [1.2, 1.0, 6.8])
    d.p('Mutation check: deliberately breaking gravity, ring slack, an AI branch, the egg-landing margin or the chord '
        'window each fails within a few hundred ticks. One mutation is not caught: the straight-up joust threshold '
        'moved from 24 to 25 subpixels, because no trace hits that exact boundary.')
    d.h2('Everything run_tests.sh checks')
    d.table(['Check', 'Proves'], [
        ['Port authority `--check`', 'the browser sources are the ones the port follows'],
        ['Regenerated tower, rules, scene data', 'generated C matches the arcade sources'],
        ['Golden re-export `--check`', 'the goldens still come from the browser byte for byte'],
        ['`host/replay`', 'bit-exact simulation and normalizer on 75,144 ticks'],
        ['`host/amb_test`', 'the device\'s decomposed ambience equals the shader'],
        ['`host/scene_check`', 'the C draw list equals the browser\'s on every tick'],
        ['`host/raster_check`', 'C rasterizer vs WebGPU frames, quality 0 and 2, >= 30 dB'],
        ['`make_pak`, `panel_check --hud`, `panel_check`', 'pack builds; HUD and game picture vs the browser; two-core split identical'],
        ['`firmware/host_test run`', 'buttons: debounce, chord, DART trials, service hold'],
        ['`firmware/host_test compile`', 'firmware type-checks against the IDF shim'],
    ], [3.4, 5.6])

    # ---- 10 ------------------------------------------------------------------------------
    d.h1('10. Hardware: the A0 bench prototype', new_page=True)
    d.p('A0 proves the electronics and the two-button game on the bench. Its locks are unchanged from v0.4, and the software '
        'was written around them. Section 11 turns A0 into a finished-looking handheld.')
    d.table(['Item', 'A0 choice', 'Status'], [
        ['Carrier', 'Waveshare ESP32-S3-Touch-LCD-3.5B, portrait: ESP32-S3R8 240 MHz, 8 MB PSRAM, 16 MB flash, 320 x 480 AXS15231B QSPI, AXP2101, ES8311 + NS4150B', 'LOCKED FOR A0'],
        ['Left wing', 'GPIO17 (header pin 16), switch to GND, pull-up, active low', 'LOCKED FOR A0'],
        ['Right wing', 'GPIO18 (header pin 18), switch to GND, pull-up, active low', 'LOCKED FOR A0'],
        ['Switch', 'Omron B3F-4050, 12 x 12 mm projected plunger, 7.3 mm, 1.27 N (B3F-4055 firmer alternative)', 'FEEL TEST REQUIRED'],
        ['Speaker', '8 ohm, ~1 W, ~28 mm mono; low gain on first power-up', 'TO TEST'],
        ['USB-C', 'short full-data male-to-female extension through the bottom of the shell', 'PART NOT CHOSEN'],
        ['Battery', 'protected LiPo; CAD reference cavity ~36 x 52 x 6.2 mm', 'DEFERRED'],
        ['Shell envelope', '88 x 128 x 25 mm (shrink target 85 x 125 x 23 mm)', 'LOCKED FOR FIT TEST'],
    ], [1.4, 5.6, 2.0])
    d.p('GPIO17/18 are published as free GPIOs and sit next to each other on the header. GPIO0, 3, 45 and 46 are '
        'strapping pins and GPIO19/20 are native USB, so none of those are used for the wings. No extra wire is needed '
        'for DART: trial C uses the same two switches.')
    d.warn('THE WINGS SHARE PINS WITH THE CAMERA CONNECTOR', 'Waveshare\'s example uses GPIO17 as the camera\'s VSYNC and '
           'GPIO18 as its HREF. The wings work only with no camera module fitted and the camera never initialised; '
           'STRUTHIO has no camera code. Leave the camera FPC connector empty.')
    d.h2('Board pin map')
    d.p('From Waveshare\'s ESP-IDF example (commit 840daf2); the schematic for the revision in hand is the authority.')
    d.table(['Function', 'Pins'], [
        ['LCD AXS15231B, QSPI on SPI2', 'CS 12, SCLK 5, D0-D3 1-4; backlight 6 (LEDC, 5 kHz); reset via the TCA9554 expander, EXIO1'],
        ['I2C', 'SDA 8, SCL 7: AXP2101 (0x34), TCA9554, ES8311, touch, IMU, RTC'],
        ['I2S (ES8311)', 'MCLK 44, BCLK 13, LRCK 15, DOUT 16, DIN 14'],
        ['SD card', 'CMD 10, CLK 11, D0 9'],
        ['Camera (unused)', 'XCLK 38, PCLK 41, VSYNC 17 (left wing), HREF 18 (right wing), data 45 47 48 46 42 40 39 21'],
        ['BOOT, USB, UART0 TX', '0; 19 and 20; 43'],
    ], [2.4, 6.6])
    d.p('Almost every GPIO is spoken for. With no camera fitted, the spare pins for the slide-switch signal wiring or later '
        'buttons are 21, 38-42, 47 and 48 (not 45 or 46: strapping). With no SD card, 9-11 are free too.')
    d.h2('The board adapter')
    d.p('`firmware/main/board_waveshare_35b.c` and `board_pmu.cpp` are ported from Waveshare\'s ESP-IDF example '
        '(Apache-2.0), not written from memory:')
    d.bullets([
        'I2C on 7/8. The AXP2101 gets the vendor\'s rail voltages and enables, charger and power key, through XPowersLib (MIT, vendored).',
        'The TCA9554 LCD reset pulse: EXIO1 low 100 ms, high 200 ms.',
        'The AXS15231B over QSPI at 40 MHz with the vendor\'s 32 init commands. The driver comes from the component registry, version 2.1.1; 2.0.2 fixed a deadlock on a failed transfer.',
        'The display is switched on with `disp_on_off(panel, false)`: this driver\'s sense is inverted.',
        'The LEDC backlight on GPIO6.',
        '`board_display_lines` waits for the driver\'s transfer-done callback, so a band buffer is never overwritten while it is still on the bus.',
        'XPowersLib\'s Kconfig defaults to the AXP192 chip on ESP32-S3; `sdkconfig.defaults` sets the AXP2101.'])
    d.h2('No row address: bands in order')
    d.p('In QSPI mode the AXS15231B is sent no row address. The driver writes a band at y 0 as RAMWR (start of frame) and every '
        'other band as RAMWRC (continue at the write pointer). So a frame must reach the panel top to bottom with no gaps. '
        'The two render cores now hand a turn back and forth: band k waits until band k-1 is on the bus, while the other '
        'core already renders the next band. The adapter counts any band that would land on the wrong rows, and the log '
        'prints the count (`band-order`).')
    d.p('`host/band_order_test` runs the real band renderer on two threads into a simulated panel with exactly this write '
        'model: the earlier "send whichever band is ready" scheme misplaced 4,736 of 6,000 bands; the turn scheme misplaces none.')
    d.h2('Minimal BOM')
    d.table(['Qty', 'Part', 'Requirement'], [
        ['1', 'Main carrier', 'Waveshare ESP32-S3-Touch-LCD-3.5B'],
        ['2', 'Wing switch', 'Omron B3F-4050 candidate'],
        ['2', 'Small switch PCB', '~18 x 18 mm perfboard or simple daughterboard'],
        ['1', 'Speaker', '8 ohm, ~1 W, ~28 mm'],
        ['1', 'Battery', 'defer final lock'],
        ['1', 'USB-C extension', 'short male-to-female, full data + power'],
        ['1', 'Button harness', '3 wires: GPIO17, GPIO18, GND'],
        ['4', 'Case screws', 'M2-class'],
        ['1 set', 'Printed shell', 'A0 front + rear + 2 wing caps'],
    ], [0.8, 2.4, 5.8])
    d.h2('Enclosure CAD (unchanged from v0.4)')
    d.p('`cad/struthio_a0_enclosure.scad` is the parametric source; `cad/stl/` holds the front shell, rear shell and '
        'mirrored wing caps, each watertight. The carrier is rotated portrait, which puts its USB-C inside the shell; '
        'hence the extension. `SWITCH_PCB_PLANE_Z` shims the switch plane after the first cap print.')
    d.figure(v04('image4.png'), 'FIGURE 3 - Prototype A0 engineering lock (v0.4 CAD): 88 x 128 x 25 mm envelope, portrait carrier, two wing controls. Its 230 ms hold-to-DART note is the v0.4 trial A; the default is now trial C (section 3).', 1.0)


    # ---- 11: A1, the portable arcade (CAD A0.8.3) ---------------------------------------
    d.h1('11. A1: a portable arcade', new_page=True)
    d.p('STRUTHIO is meant to feel like the dedicated LCD games of the early 1990s: one game per device, switch it on and '
        'play, a chunky moulded body, big action buttons, full-colour art on the face, a screwed-shut back. The plastic '
        'idea is a **portable arcade**: the screen in a moulded bezel at the top, a printed art panel below it, and two big '
        'gold buttons, held in a tapered body that flares out at the bottom like the period handhelds.')
    d.gold('A1 AUTHORITY: CAD A0.8.4, FROM R.A. PEDDYCOART\'S A0.8.2', [
        '`cad/a1/STRUTHIO082.scad` is the author\'s robust-lower-chassis revision, kept exactly as received. '
        '`STRUTHIO083.scad` adds four fit fixes; `STRUTHIO084.scad` adds the STRUTHIO identity and three more fixes the '
        'identity work exposed. Print from A0.8.4.',
        'It keeps the A0 hardware datums (88 x 128 mm footprint, LCD, wing switch and screw positions) and is still a '
        'candidate until the board, front shell and one wing cap have been fit-tested.'])
    d.figure(R('cad', 'a1', 'renders', 'a084_struthio_front.png'),
             'FIGURE 4 - A1 as the player sees it, assembled from the A0.8.4 CAD to scale: navy shell, gold LEFT WING and '
             'RIGHT WING caps, the art sticker cut to the CAD template (STRUTHIO logo and the joust from the game\'s box '
             'art), and a real frame from the C panel renderer in the screen opening.', 0.62)
    d.h2('Truly STRUTHIO: the identity pass (A0.8.4)')
    d.p('The heritage shell could have been any 1990s handheld. A0.8.4 makes every visible part come from the game:')
    d.table(['Element', 'From the game', 'In A0.8.4'], [
        ['The two buttons', 'The controls are LEFT WING and RIGHT WING (`rules.mjs` input regions)', 'Wing-shaped gold caps: rounded root toward the screen, three scalloped primaries sweeping outward, a groove along each feather'],
        ['Colours', 'The game palette in `rules.mjs`', 'Navy #102838 shell, gold #E2A93F wings, void #07131F art panel, ring cyan #20C4D7 accent'],
        ['Front art', 'The STRUTHIO box art (`arcade/assets/art/hero-art.webp`)', 'Sticker with the STRUTHIO logo over the joust, cut exactly to the CAD template, 600 dpi with 1.5 mm bleed'],
        ['Screen', 'The game itself', 'The C port\'s picture (section 6), not an illustration'],
        ['Back', 'The gold ring every round ends at', 'STRUTHIO wordmark and a gold-ring emblem debossed 0.5 mm into the battery blister'],
    ], [1.6, 3.2, 4.2])
    d.figure(R('cad', 'a1', 'renders', 'a084_identity_details.png'),
             'FIGURE 5 - The wing caps as installed (player\'s view) and the rear shell with the debossed STRUTHIO mark and gold ring.', 1.0)
    d.figure(R('cad', 'a1', 'art', 'sticker_front_proof.png'),
             'FIGURE 6 - Front sticker proof: art with bleed (dashed), cut line (magenta) and the cut-away wing and grille '
             'holes. Print file: `cad/a1/art/sticker_front_print.png` (600 dpi).', 0.8)
    d.figure(R('docs', 'renders', 'a1_concept_sheet.png'),
             'FIGURE 7 - The author\'s A1 concept renders: cream shell, rear model label and pixel-ostrich art, slide POWER '
             'switch, USB-C bottom, and the 88 x 128 x 23 mm envelope (18.6 mm at the top, 22.5 mm at the speaker).', 1.0)
    d.figure(R('cad', 'a1', 'renders', 'a084_sheet.png'),
             'FIGURE 8 - The A0.8.4 CAD as exported: front, assembly, rear shell with the battery and speaker blisters, and the centre section.', 1.0)
    d.h2('What the A0.8.4 shell is')
    d.table(['Feature', 'A0.8.4', 'Status'], [
        ['Footprint', '88 x 128 mm, the A0 box; shrink target 85 x 125 mm after the fit proof', 'Locked for fit test'],
        ['Depth', 'Thin contour: 18.6 mm where only the board is, 22.5 mm over the speaker, 23.0 mm over the battery (A0: 25 mm everywhere)', 'Candidate'],
        ['Silhouette', 'Rounded superellipse crown, narrow waist, flared lower body and feet, shallow bottom arch (1.8 mm rise)', 'Tunable block'],
        ['Screen', 'Locked LCD opening inside a 56.5 x 81 mm lens land, recessed 0.55 mm', 'Opening locked; land tunable'],
        ['Art panel', 'Trapezoid sticker recess from y -27.2 (0.5 mm below the lens land) to the bottom contour, 72 mm wide at the top, 78 mm at the bottom, 0.28 mm deep', 'Tunable'],
        ['Buttons', '28 x 18.5 mm gold wing caps, 1.8 mm proud, feather grooves, on the A0 switch centres (x +/-21.5, y -47.5); `BUTTON_STYLE="round"` restores the 23 mm discs', 'Feel test'],
        ['Speaker', 'Four 9 mm slots between the wings, 2.75 mm of shell either side; speaker raised 3.5 mm to y -43.5', 'Candidate'],
        ['Lower chassis', '1.8 mm internal backer plate and collars that follow the button outline, U-boss behind the USB-C opening', 'Candidate'],
        ['Rear', 'No screws through the front (4 M2 from the back); STRUTHIO wordmark and gold ring debossed into the battery blister', 'Candidate'],
        ['Front controls', 'Two wing buttons only. No START, SOUND, ALL CLEAR or touch on the front', '**Locked**'],
        ['Power', 'Side slide switch in the concept renders; the CAD has an optional side aperture (`OPTIONAL_POWER_SWITCH`, off)', 'Part not chosen'],
        ['Service access', 'Side slot to the board\'s PWR / BOOT / RESET keys', 'Fit test'],
    ], [1.6, 5.4, 2.0])
    d.h2('Fit fixes since A0.8.2')
    d.p('All parts export as single watertight solids. Probing the exported meshes and the sticker template found seven '
        'places where a part no longer met its neighbours. Each fix is commented in the SCAD header:')
    d.table(['Problem in A0.8.2', 'Cause', 'Fix (version)'], [
        ['USB-C opening blocked by ~1.1 mm of wall; the U-boss poked ~1 mm out of the bottom arch', 'Cut and boss placed from the old square bottom (y -64); the arch puts the centre edge at y -62.2', 'Follow the arch, `BOTTOM_EDGE_CENTER_Y` (0.8.3)'],
        ['Side service slot did not open', 'Cut started at x 41.4; the waist puts the outer wall at x ~41.0', 'Starts inside the cavity; same for the power aperture (0.8.3)'],
        ['Buttons held pressed', 'Stem tip at z 7.3, B3F plunger tip at 13.7 - 7.3 = 6.4: 0.9 mm into a 0.25 mm-travel switch', 'Stem stops 0.10 mm short and follows `SWITCH_PCB_PLANE_Z` (0.8.3)'],
        ['Battery reference 0.15 mm inside the board envelope', 'Started at z 14.7, board back at 14.85', 'Sits on the board\'s back face (0.8.3)'],
        ['Wing clearances only 58% in Y', '`wing2d` offset in unit space, then scaled non-uniformly', 'Offset after scaling: true mm in X and Y (0.8.4)'],
        ['Art sticker covered the bottom 2.6 mm of the screen and overlapped the lens land', 'Top corners inset upward (+R), so the panel ran to y -19.8, not -24.2', 'Corners fixed; top at -27.2 (0.8.4)'],
        ['Wing tips cut the sticker into slivers; 32 mm wings left 0.8 mm of shell beside the grille', 'Panel too small for wing caps; A0.8.2\'s wing fallback too wide', 'Panel 72 / 78 mm to the bottom contour; wings 28 mm; collars follow the outline (0.8.4)'],
    ], [3.0, 3.2, 2.8])
    d.p('`cad/a1/export_a1.sh` exports the STLs, the sticker template, the art and the renders, then runs `check_a1.py`:')
    d.bullets([
        'one watertight solid per part; nothing outside the outline;',
        'USB-C and side service openings clear;',
        'each stem resting 0 to 0.25 mm before its B3F plunger;',
        'each cap neck passing its opening with 0.2 mm clearance all round, its flange overlapping the opening by 0.3 mm all round (captured) and clearing the backer plate;',
        'at least 1.5 mm of shell between each wing opening and the grille;',
        'the art sticker below the lens land, with exactly six holes (two wings, four slots), each 0.8 mm inside its edge.'])
    d.p('Run against A0.8.2 the checks fail at exactly the problems above; with A0.8.2\'s 32 mm wings the grille check fails '
        'at 0.79 mm.')
    d.h2('Concept renders vs the CAD: to settle')
    d.table(['Concept render', 'CAD A0.8.3', 'To decide'], [
        ['Rear label: "Li-Ion 2000 mAh"', 'Battery cavity 36 x 52 x 6.2 mm', 'Cells of that footprint and thickness are usually well under 2000 mAh; pick the cell from the measured draw and its datasheet, then set the label'],
        ['Slide POWER switch on the side', 'Optional aperture on the right side, off by default', 'Choose the switch and the side; see "Power" below'],
        ['Speaker vents on the rear shell', 'Front grille, closed rear blister', 'Keep the front grille; rear vents only if the speaker is too quiet'],
        ['Cream or graphite shell', 'Navy (STRUTHIO palette) preview colour', 'Pick a filament: navy keeps the game palette; cream is the heritage alternative'],
        ['Art panel shows the STRUTHIO logo and the arena', 'Art made: `art/sticker_front_print.png`, cut to the A0.8.4 template', 'Print a test sticker and check colour and registration'],
    ], [2.6, 2.6, 3.8])
    d.h2('Buttons')
    d.p('The wing buttons decide whether STRUTHIO feels like a toy or like a dev board. Build both constructions and choose '
        'by thumb, in the same sessions as the DART test:')
    d.table(['', 'A  Tactile (A0, CAD default)', 'B  Rubber dome (1990s feel)'], [
        ['Mechanism', 'Omron B3F-4050 under the wing cap', 'Hard cap on a silicone dome; a carbon pill shorts gold interdigitated pads on a small PCB'],
        ['Feel', 'Crisp click, short travel', 'Soft, quiet, longer travel: the period handheld feel'],
        ['Parts', 'Off-the-shelf switch, 18 x 18 mm perfboard', 'Custom button PCB (ENIG pads) and domes; the CAD switch plane moves'],
        ['Electrical', 'Clean contact, short bounce', 'Contact resistance of tens to hundreds of ohms and a slower make: re-check the 8 ms debounce and the internal pull-up'],
        ['Risk', 'Clicky, less toy-like', 'Feel varies with dome choice; needs a PCB spin'],
    ], [1.4, 3.4, 4.2])
    d.p('Housekeeping stays off the front, as the CAD locks it: GAME OVER restarts with both wings held, service mode is '
        'both wings at power-on, and a hung game is reset by the watchdog. The BOOT and RESET keys stay inside, reached '
        'through the side service slot during bring-up.')
    d.h2('Power')
    d.p('The period handhelds ran for a long time on a few cells because a reflective LCD draws almost nothing. STRUTHIO\'s '
        'backlit IPS panel and dual-core renderer draw far more, so battery life is the one place A1 cannot match them. '
        'The thin-contour shell is built around one protected LiPo in the 36 x 52 x 6.2 mm cavity, charged by the board '
        'from USB-C; there is no room for AA cells (they are 14.5 mm thick behind a board that ends at 14.85 mm).')
    d.p('**The slide POWER switch** in the concept renders gives the old-fashioned hard OFF / ON. The board\'s own PWR key '
        'is momentary (AXP2101), so a latching slide switch cannot simply replace it. Two ways to wire it, to choose after '
        'reading the schematic:')
    d.bullets([
        '**In the battery lead:** the switch breaks the LiPo positive. OFF is truly off and draws nothing; with USB-C connected the board still runs and charging needs the switch ON. Simplest, closest to the originals.',
        '**As a signal:** the switch drives a spare GPIO; firmware asks the AXP2101 to power down when it opens, and the PWR key (or USB) wakes it. Keeps charging in either position; needs firmware and the PMIC\'s register details.'])
    d.warn('POWER SAFETY', ['Use only a protected LiPo, and check the connector polarity before plugging it in (the A0 rule).',
           'A switch in the battery lead must be rated for the peak current; never switch the negative lead.',
           'Never connect AA, NiMH or any non-lithium pack to the board\'s battery connector: its charger would try to charge it.'])
    d.p('**Battery life is measured, not guessed.** Hours = usable watt-hours / measured watts. Example only: a 1,000 mAh '
        'LiPo holds about 3.7 Wh, so at 1 W it would last roughly 3.5 hours. Measure the draw in play, at idle and at each '
        'backlight level (bring-up step 11) before choosing a cell or printing a capacity on the label. Auto power-off '
        '(sleep after idle at GAME OVER, a wing press wakes it) is a firmware proposal that would help.')
    d.h2('Screen window and art panel')
    d.bullets([
        'A clear 1.0-1.5 mm acrylic or polycarbonate lens sits in the 0.55 mm lens-land recess around the screen.',
        'The art panel is a printed sticker in the 0.28 mm recess below the screen; `part="sticker"` exports its cut template (`svg/struthio_a083_front_sticker.svg`), with holes for both buttons and the grille. Laminate it so play cannot rub it off.',
        'Keep at least 0.4 mm between the lens and the display glass and never clamp the glass (A0 rule).',
        'The IPS panel is bright; a matte or anti-glare lens is an option if reflections bother players.'])
    d.h2('Shell, finish and labels')
    d.table(['Item', 'A1'], [
        ['Material', 'PETG or ASA for strength (PLA for fit checks only); the originals were moulded ABS'],
        ['Walls and closure', '2.4 mm walls, 3 mm front, 2.2 mm rear skin; 4 x M2 screws from the back into the front'],
        ['Colours', 'Navy shell, gold wings (STRUTHIO palette); cream or graphite are the concept-render alternatives'],
        ['Front art', 'Sticker in the art-panel recess: STRUTHIO logo over the joust, from the game\'s box art (`art/sticker_front_print.png`)'],
        ['Rear label', 'Model plate: "STRUTHIO  MODEL S3-01  ESP32-S3 HANDHELD  3.5\\" 320 x 480 LCD", the cell chemistry and capacity (once measured), "MADE FOR HIGHER FLIGHT", R.A. PEDDYCOART'],
        ['Rear mark', 'STRUTHIO wordmark and gold ring debossed in the battery blister (A0.8.4); a printed label can add the pixel ostrich'],
    ], [2.0, 7.0])
    d.h2('Reference-unit study')
    d.p('One afternoon with one or two used early-1990s LCD handhelds settles most of the feel questions. For each, record '
        'in `docs/A1_REFERENCE_UNITS.md`: outer size, depth and weight; button cap size, travel and force (a kitchen scale '
        'and a ruler are enough) and the dome feel; screen window inset and lens thickness; battery door and screws; grille '
        'pattern; label placement. Compare with A0.8.3 and change its tunable block only from these measurements. A1 '
        'borrows the genre, never another company\'s names, logos or trade dress.')
    d.h2('A1 changes to the electronics')
    d.table(['Change', 'What it needs', 'Status'], [
        ['Slide POWER switch', 'A latching switch and the side aperture; battery-lead or GPIO wiring (above)', 'Part and wiring not chosen'],
        ['Rubber-dome wing buttons (option B)', 'Button PCB with gold interdigitated pads; GPIO17/18/GND harness unchanged', 'After the feel test'],
        ['Low-battery warning', 'AXP2101 battery level to a HUD icon', 'Firmware proposal'],
        ['Auto power-off', 'Deep sleep with a wing as the wake source', 'Firmware proposal'],
    ], [2.6, 4.4, 2.0])
    d.h2('A1 BOM additions (candidates, not locked)')
    d.table(['Qty', 'Part', 'Requirement'], [
        ['1', 'Lens', '1.0-1.5 mm clear acrylic or polycarbonate, cut to the lens land'],
        ['1', 'Front art sticker', 'Printed and laminated, cut to the A0.8.3 template'],
        ['1', 'Slide switch', 'Latching, side-actuated, rated for the battery current; fits the side aperture'],
        ['1', 'LiPo cell', 'Protected, fits 36 x 52 x 6.2 mm; capacity from the measured draw'],
        ['1 set', 'Labels', 'Rear model plate and rear art'],
        ['1 set', 'Rubber domes + button PCB', 'Option B wing buttons only'],
    ], [0.8, 2.6, 5.6])
    d.h2('A1 acceptance tests (in addition to section 12)')
    d.table(['Test', 'Method', 'Pass'], [
        ['CAD checks', '`cad/a1/export_a1.sh`', 'A1 CHECK: all pass'],
        ['Test sticker', 'Print the proof at 100% and lay it in the printed recess', 'Cut line meets the recess; wing and grille holes clear the caps and slots'],
        ['Fit coupon', 'Print `part="front_fit_coupon"`, place the board and one cap', 'Glass untouched; cap moves freely; no click at rest; clicks within 0.35 mm of travel'],
        ['Button feel', '3 players, 10 minutes each, tactile and rubber-dome buttons', 'A clear preference; no missed or double flaps'],
        ['Power switch', '50 OFF / ON cycles', 'Starts into a run every time; OFF draws nothing measurable (battery-lead wiring)'],
        ['Drop', 'Five drops from 1 m onto carpet', 'No rattles, cracks or loose parts; the game still plays'],
        ['Runtime', 'Play from full until the low-battery cut-off', 'Measured hours recorded; the label states them honestly'],
    ], [1.6, 3.6, 3.8])
    d.p('If STRUTHIO is ever sold or given as a toy, the applicable toy-safety rules apply (for example EN 71 in Europe and '
        'ASTM F963 in the United States, which among other things cover battery compartments and small parts), as do '
        'lithium-battery rules. That is outside A1, which is a prototype for adults to test.')

    # ---- 12 ------------------------------------------------------------------------------
    d.h1('12. Bring-up on the board')
    d.p('Before the board arrives, `handheld/run_tests.sh` must pass. Then, in this order, so faults stay separable:')
    d.steps([
        'Record the board revision and compare its schematic with `firmware/main/board_pins.h`. Leave the camera connector empty. Flash and run Waveshare\'s own example once, unchanged, to prove the board.',
        '`idf.py build flash monitor` without the asset pack first. The board adapter is already ported (section 10). Expect `AXP2101 id ...` and `AXS15231B 320x480 QSPI at 40 MHz` in the log and the greybox picture on the panel. If the screen stays dark, check the TCA9554 reset pulse and the backlight duty first.',
        'Hold both wings at power-on. Record GOLDEN PASS, sim µs per tick, digest µs per tick and the panel ms per frame.',
        'Confirm GPIO17/18 read high idle and low pressed with the display active (service mode shows live states and counts).',
        '`make -C handheld/host pak`, flash again with the pack. Read `scene` and `render` µs in the log every 300 frames: the first device measurement of the C renderer.',
        'Play. Confirm the 100 ms chord and thumb-test DART trial C, then A and B. Lock one only after real play.',
        'Watch `band-order` in the log: it must stay 0. If bands tear or shift, check the transfer-done wait first, then try larger bands.',
        'Wire the audio (ES8311 + NS4150B) at low gain with the 8-ohm speaker.',
        'Print the front shell only; test the LCD opening and board width. Then one wing cap; tune `SWITCH_PCB_PLANE_Z`. Then the rear shell.',
        'Battery last: polarity, charge, low-battery and shutdown behaviour before enclosing the cell. Measure the current in play, at idle and at each backlight level: the A1 runtime comes from these numbers.'])
    d.h2('If the renderer is too slow')
    d.p('The frame budget at 30 fps is 33 ms over two cores, and the scene builder runs in the game task every tick. '
        'In order of cost to fidelity:')
    d.bullets([
        'Check that the post tables and band workspaces landed in internal RAM: the tables fall back to PSRAM silently when internal RAM is short.',
        'Profile the scene builder: it keeps double precision so its draw list equals the browser\'s, and the ESP32-S3 has no double-precision FPU. A float build is possible if the draw list stays within tolerance.',
        'Profile flash-cache misses on the textures; move the hottest (birds) to PSRAM.',
        'Last resort: render at 20 fps. The simulation stays at 60 Hz either way.'])
    d.h2('Acceptance tests')
    d.table(['Test', 'Method', 'Pass'], [
        ['Cold boot', 'power-cycle 20 times', '20/20 reach a live run without touch, menu or debug'],
        ['Input bounce', 'tap each switch 100 times', 'no phantom double flaps; logged presses match'],
        ['Chord', '50 two-button chords at varied timing', 'straight-up at the 100 ms window, no lag on the first press'],
        ['DART', 'repeated sessions with the chosen trial', 'no recurring accidental DART'],
        ['Simulation', 'service-mode golden replay', 'GOLDEN PASS on the device'],
        ['Frame pacing', 'worst visible scene, 10 minutes', 'no tearing; 30 fps held or a lower target chosen; zero missed game deadlines'],
        ['Persistence', 'set a high score, power off/on', 'the score returns'],
        ['Watchdog', 'inject a task hang', 'the device resets into a new run'],
        ['Soak', '30-60 minutes of play', 'no crash, corruption or thermal problem'],
    ], [1.6, 3.2, 4.2])

    # ---- 12 ------------------------------------------------------------------------------
    d.h1('13. Known deviations from the browser')
    d.p('Every intentional difference is named here rather than left to drift.')
    d.table(['Deviation', 'Why'], [
        ['DART is a held two-wing gesture (trial C), not a downward flick', 'two buttons cannot flick; pending a thumb test'],
        ['GAME OVER needs both wings held to start a new run', 'a stray flap from the last fight must not skip the result'],
        ['No title / attract screen: power-on starts a run', 'appliance behaviour; the menu shows only on GAME OVER'],
        ['Picture is the area-filtered canvas, not nearest-pixel', 'keeps thin detail at 286 x 429'],
        ['Post at quality 0 (no bloom, scanlines, vignette)', 'frame time on the device'],
        ['No island music pulse (0-4%)', 'no music yet; small effect'],
        ['Display at <= 30 fps, simulation at 60 Hz', 'panel bandwidth and render time; to be measured'],
        ['Audio: not yet implemented (cue hook only)', 'needs the board'],
        ['A1 has a slide POWER switch and (proposed) auto power-off, which the browser does not have', 'the handheld\'s own housekeeping, 1990s style'],
    ], [4.6, 4.4])
    d.h2('Risk register')
    d.table(['Risk', 'Impact', 'Mitigation / trigger'], [
        ['Renderer too slow on the ESP32-S3', 'High', 'measured at bring-up step 6; see section 12 for the order of fixes'],
        ['QSPI panel bandwidth', 'High', '40 MHz quad = 20 MB/s raw, 307 KB a frame: ~15 ms of bus time per frame, overlapped with rendering; 30 fps target'],
        ['First real `idf.py build` finds problems', 'Low-medium', 'the real-header check already passes; what is left is codegen, linking and component versions'],
        ['A camera module fitted by mistake', 'Medium', 'the wings share its VSYNC/HREF pins; keep the connector empty, say so on the label'],
        ['DART gesture under a real thumb', 'High', 'trials A/B/C switchable in service mode without a rebuild'],
        ['Flash-cache contention between textures and the panel DMA', 'Medium', 'move hot textures to PSRAM'],
        ['Simulation drift after a browser update', 'High', 'port authority `--check` and the goldens fail until ported'],
        ['Enclosure built too early', 'Medium', 'no final shell until the bare-board prototype passes A0'],
        ['Battery life far below the 1990s originals', 'Medium', 'measure first; auto-off, backlight levels, LiPo size; say so on the box'],
        ['Thin-contour shell too tight for real parts', 'Medium', 'fit coupon first; the A0 datums and the 25 mm A0 envelope remain the fallback'],
        ['Rubber-dome feel or bounce unsuitable', 'Medium', 'keep the B3F tactile construction'],
        ['Look too close to another company\'s product', 'Medium', 'STRUTHIO art and palette only; no third-party marks or trade dress'],
    ], [3.2, 1.0, 4.8])

    # ---- 13 ------------------------------------------------------------------------------
    d.h1('14. Next work and open decisions')
    d.steps([
        'Bring up the board (section 12) and record the first device numbers: µs per tick, scene µs, render ms, panel ms.',
        'Lock the DART gesture after a thumb test.',
        'Lock 30 fps or a higher rate from the measurements.',
        'Audio: one embedded music stream and pre-rendered SFX cues through the ES8311; audio never touches the game state.',
        'Battery, then the full A0 shell.',
        'A1 (section 11): print the A0.8.4 fit coupon and a test sticker, then the shell; button feel test (tactile vs rubber dome); choose the slide switch and its wiring; measure the draw and pick the cell; print-ready front sticker for the template; reference-unit study.'])
    d.p('Open decisions: whether retail boot shows a sub-second mark or nothing; USB-only updates or a hidden OTA path; '
        'the shell shrink from 88 x 128 x 25 mm toward 85 x 125 x 23 mm after the fit print.')

    # ---- 14 ------------------------------------------------------------------------------
    d.h1('15. Repository map')
    d.code([
        'handheld/',
        '  core/       C11 simulation, normalizer, digests, replay (portable, no heap)',
        '  render/     scene builder, reference rasterizer, panel renderer, pack loader, greybox',
        '  firmware/   ESP-IDF app (main.c, service.c, buttons, board adapter), host tests, IDF shim',
        '  host/       replay, scene/raster/panel checks, amb_test, make_pak',
        '  tools/      golden exporter, generators, port authority, browser reference capture, this manual',
        '  golden/     five browser-recorded traces',
        '  cad/        A0 enclosure (OpenSCAD source, STLs, renders); a1/: A1 CAD (A0.8.2 as received, A0.8.3 fit-fixed, A0.8.4 STRUTHIO), checks, art, renders',
        '  docs/       this manual, graphics port, validation report, bring-up, wiring, BOM, port authority',
        '  run_tests.sh'])
    d.p('This manual is generated: `python3 handheld/tools/manual/build_manual.py STRUTHIO_ESP32_HANDHELD_v0.4.docx` '
        '(the v0.4 manual supplies the page design and the industrial-design figures).')
    d.h2('References')
    d.bullets([
        'Waveshare ESP32-S3-Touch-LCD-3.5B: https://docs.waveshare.com/ESP32-S3-Touch-LCD-3.5B',
        'Waveshare 3.5B resources, schematics, drawings, examples: https://docs.waveshare.com/ESP32-S3-Touch-LCD-3.5B/Resources-And-Documents',
        'Espressif ESP32-S3 datasheet (strapping pins, USB pins): https://documentation.espressif.com/esp32_s3_datasheet_en.pdf',
        'Espressif ESP32-S3 hardware design guidelines: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/',
        'Omron B3F tactile switch datasheet: https://components.omron.com/us-en/datasheet_pdf/A070-E1.pdf',
        'NS4150B amplifier reference: https://dl.espressif.com/dl/schematics/NS4150B.pdf'])

    # ---- appendix ------------------------------------------------------------------------
    d.h1('Appendix A. Industrial design direction (carried from v0.3)', new_page=True)
    d.p('Concept visualisations for planning, not fabrication authority. Geometry in sections 10 and 11 is the engineering authority.')
    d.figure(v04('image3.png'), 'FIGURE A - Preferred product direction: graphite shell, warm retro stripes, two dominant wing controls, portrait display.', 1.0)
    d.figure(v04('image1.png'), 'FIGURE B - Integrated final-design board: front, perspective, rear, side, packaging and exploded assembly.', 1.0)
    d.figure(v04('image2.png'), 'FIGURE C - Heritage handheld direction: two buttons first, the game screen second, everything else hidden.', 1.0)
    d.h1('Appendix B. Change history', new_page=True)
    d.table(['Version', 'Date', 'Change'], [
        ['v0.1-v0.2', '2026-09', 'Prototype path from STRUTHIO ARCADE 1.6.0; industrial design boards.'],
        ['v0.3', '2026-09-28', 'CAD and ESP32-S3 engineering kickoff.'],
        ['v0.4', '2026-09-28', 'A0 enclosure files, GPIO17/18 wing lock, host-tested input scaffold.'],
        ['v0.5', '2026-10-01', 'Simulation ported to C, bit-exact with 1.8.0 on 75,144 ticks; exact normalizer; DART trials measured; firmware on the core.'],
        ['v0.6', '2026-10-01', 'Browser renderer ported (scene builder equal on every tick; materials and post measured vs WebGPU; HUD captured); asset pack; two-core panel renderer; firmware renders the browser picture. Manual rewritten for the C port.'],
        ['v0.7', '2026-10-01', 'Hardware chapter for A1, a 1990s-style "portable arcade": R.A. Peddycoart\'s CAD A0.8.2 adopted as the authority and fit-fixed as A0.8.3 (USB-C opening, service slot, button pre-travel, battery datum; checked by cad/a1/check_a1.py); concept renders; buttons, slide POWER switch, screen and art panel, shell and labels, reference-unit study, A1 BOM and tests; player\'s instruction sheet (Appendix C).'],
        ['v0.8', '2026-10-01', 'A1 made truly STRUTHIO (CAD A0.8.4): wing-shaped LEFT/RIGHT WING caps, the game palette, front art sticker from the box art cut to the CAD template, debossed STRUTHIO mark and gold ring; three more fit fixes (wing clearances, art panel over the screen, wing slivers); checks extended to caps, grille web and sticker.'],
        ['v0.9', '2026-10-01', 'ESP32 preparation: board adapter ported from Waveshare\'s example (AXP2101, TCA9554 reset, AXS15231B QSPI, backlight); pin map (the wings share the camera\'s VSYNC/HREF); bands sent strictly in order (the panel has no row address over QSPI; proven by host/band_order_test); every firmware source compiled against the real ESP-IDF 5.5.5 headers (firmware/idf_check).'],
    ], [1.2, 1.4, 6.4])
    d.h1('Appendix C. Player\'s instruction sheet (draft)', new_page=True)
    d.p('The folded sheet that goes in the box, in the 1990s style: short, friendly, nothing a player does not need. '
        'Rules are taken from the game itself (STRUTHIO ARCADE 1.8.0, as ported).')
    d.callout('STRUTHIO PORTABLE ARCADE  -  HOW TO PLAY', [
        '**TURN ON.** Slide the POWER switch on the side to ON. The game starts by itself.',
        '**FLY.** Press the LEFT WING or the RIGHT WING to flap that way. Hold a wing to steer.',
        '**STRAIGHT UP.** Press both wings together.',
        '**DART.** Hold both wings down to dive the way you are facing.',
        '**JOUST.** Meet a rival with your lance higher than theirs to knock them off. Rising straight up always wins. Lances level? You both bounce.',
        '**EGGS.** A beaten rival leaves an egg. Grab it before it hatches: 250, 500, 750, then 1,000 points for each egg in a row.',
        '**RINGS.** Fly through the six rings (500 points each). When all six are yours, the gold ring opens at the moon: reach it to clear the round.',
        '**LIVES.** You start with 11 jousts. Extra ones at 30,000 points and every 100,000 after. Keep out of the lava.',
        '**GAME OVER.** Hold both wings to play again.'], fill='F0EFE7', bar='E2A93F')
    d.callout('BUTTONS AND CARE', [
        'Your STRUTHIO has just two buttons: the wings do everything.',
        'Charge with a USB-C cable at the bottom. If the game ever stops responding, slide POWER to OFF and back to ON.',
        'Keep away from water and heat. Do not open the case: there are no parts inside you can service.'], fill='EAF4F4', bar='20C4D7')
    d.p('The POWER switch wording and the charging line depend on the switch wiring still to choose (section 11); edit the sheet when it is locked.',
        size=17, color='60656C')
