#!/usr/bin/env python3
"""STRUTHIO HANDHELD · Build Manual 1.3 -> 1.4: game sound.

Edits the owner's S13 docx in place and in its own styles: every "game audio is
pending / stub" statement becomes the real state (the browser's SFX synth and
conductor ported to C and checked sample by sample, the soundtrack in its own
flash partition, the ES8311 driver), the flash map and service-screen figures
are replaced, and a sound section, log lines, checklists, FAQ and verification
rows are added.
    python3 tools/manual/expand_v14.py S13.docx FIG_DIR OUT.docx
FIG_DIR: figs12.py output (f06_flashmap.png, f12_audio.png) and service.png.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as K

SRC, FIG, OUT = sys.argv[1:4]
FG = lambda n: os.path.join(FIG, n)
K.open_doc(SRC)
At = K.At

# ---- title and edition notes -------------------------------------------------------------------
K.replace_in(K.para('STRUTHIO HANDHELD BUILD MANUAL 1.3'), 'MANUAL 1.3', 'MANUAL 1.4')
K.replace_in(K.para('Prepared for R.A. Peddycoart'), 'audit-corrected from Build Manual 1.2, current v0.10 engineering material',
             'Build Manual 1.3 plus game sound (v0.11 engineering package)')
a = At(K.before_break(K.para('SOURCE OF TRUTH')))
a.h1('What 1.4 adds — game sound', newpage=False)
a.p('Edition 1.3 said, correctly at the time, that STRUTHIO had no game sound on the handheld. That is no longer true. '
    'The v0.11 engineering package adds the browser game\'s sound to the C port and to the firmware:')
a.bullets([
    ('Sound effects: ', 'the browser\'s synth and conductor are ported to C (audio/struthio_audio.c). On all five golden traces '
     'the C and the browser\'s own sound engine play the same 8,031 notes to within 2 parts in 32,768 (76–77 dB).'),
    ('Music: ', 'the 160-second soundtrack loop is stored as compressed audio (1.9 MB) in a new "music" area of the flash chip, '
     'and loops without a gap. It ducks under rings, jousts, deaths and round clears, as in the browser.'),
    ('Speaker driver: ', 'the ES8311 codec is driven the way Waveshare\'s own example drives it, at 48 kHz.'),
    ('Volume: ', 'five levels (0 = off). In service mode, hold LEFT for one second to step it; it is saved.'),
    ('Still to prove on the bench: ', 'nobody has heard it on a real board yet, and the five volume levels are starting values.'),
])
a.callout('Game sound is now part of the build. Step 8 proves the speaker hardware first (vendor example), then STRUTHIO\'s own sound.')

# ---- quick start -----------------------------------------------------------------------------------
qs = K.table_hdr('GateWhat you do')
r7 = K.row_with(qs, 'Run vendor audio example at low gain')
K.set_cell(K.cells(r7)[1], 'Vendor audio example at low gain, then STRUTHIO sound (service mode)')
K.set_cell(K.cells(r7)[2], 'Speaker clean; service mode shows AUDIO OK + MUSIC OK; sounds + music in play')
K.replace_in(K.para('Beginner ZIP checks:'), 'The normal build uses the PREBUILT struthio.pak supplied with the package;',
             'The normal build uses the PREBUILT struthio.pak and struthio_music.ima supplied with the package;')

# ---- Step 3: the zip -----------------------------------------------------------------------------
z = K.table_hdr('Folder or file')
pak = K.row_with(z, 'build/assets/struthio.pak')
K.add_row(z, ['build/assets/struthio_music.ima', 'The prebuilt soundtrack: 160 s loop, 24 kHz compressed (IMA ADPCM), 1.9 MB.', 'Yes: flashed by idf.py flash'], after=pak, like=pak)
rnd = K.row_with(z, 'render/')
K.add_row(z, ['audio/', 'The game\'s sound: the browser\'s synth and conductor in C, the music player, the output stage.', 'Yes, built automatically'], after=rnd, like=rnd)
cr = K.table_hdr('Check (run_tests.sh)')
K.add_row(cr, ['audio', 'The C sound engine plays the same notes as the browser\'s, sample by sample, on all five traces; the soundtrack encodes identically.'],
          after=K.row_with(cr, 'C core replay'), like=K.row_with(cr, 'C core replay'))

# ---- Step 5: logs, errors, flash map ------------------------------------------------------------------
lg = K.table_hdr('Log line (as printed)')
dart = K.row_with(lg, 'DART trial <A HOLD')
K.add_row(lg, ['ES8311 audio 48000 Hz mono', 'The audio codec answered and is set up.', 'Always (speaker fitted or not)'], after=dart, like=dart)
K.add_row(lg, ['audio ok|OFF, music 160 s loop|none, volume <n>/4', 'Sound started; the soundtrack was found; the saved volume.', '"audio ok, music 160 s loop"'],
          after=K.row_with(lg, 'ES8311 audio 48000'), like=dart)
tickrow = K.row_with(lg, 'tick <n> sim')
K.set_cell(K.cells(tickrow)[0], 'tick <n> sim <us> us (max <us>) scene <us> us render <us> us present <us> us missed <n> band-order <n> audio <us> us (max <us>) per 5333')
K.set_cell(K.cells(tickrow)[2], 'band-order 0; audio far below 5333')
er = K.table_hdr('If the log says')
last = K.row_with(er, 'assets: out of memory')
for vals in reversed([
        ['ES8311 not found', 'The codec did not answer on I2C.', 'Board revision; run the vendor audio example. The game still plays, silently.'],
        ['audio: I2S init failed / codec open failed', 'The audio clock or data line could not start.', 'Re-flash the unmodified firmware; report with the log.'],
        ['no music partition', 'The partition table on the board is older than v0.11.', 'Flash with idf.py flash (it writes the new table).'],
        ['music: not a STRUTHIO music file', 'build/assets/struthio_music.ima was missing at build time, or damaged.', 'Check the file, then flash again. Sound effects still play.']]):
    K.add_row(er, vals, after=last, like=last)
K.replace_figure('FIGURE 5.2', FG('f06_flashmap.png'),
                 'FIGURE 5.2 — The flash map from firmware/partitions.csv (v0.11). The art pack now has 9 MB (it uses 8.3 MB) and the '
                 'soundtrack its own 2.9 MB "music" area. High score, DART trial and volume live in nvs; "idf.py erase-flash" clears them.')
fl = K.paras_starting('The first flash takes longer')
if fl: K.replace_in(fl[0], 'the 8.3 MB asset pack is written too', 'the 8.3 MB asset pack and the 1.9 MB soundtrack are written too')

# ---- Step 7: service screen + performance line ----------------------------------------------------------
K.replace_figure('FIGURE 7.1', FG('service.png'))
sv = K.table_hdr('LineMeaning')
panel = K.row_with(sv, 'PANEL <n> MS/FRAME')
K.add_row(sv, ['AUDIO OK|NO CODEC  MUSIC OK|NONE  VOL <n>/4', 'Codec found; soundtrack found; volume level (0 = off).', 'AUDIO OK, MUSIC OK'], after=panel, like=panel)
help_row = K.row_with(sv, 'LEFT: NEXT DART TRIAL')
K.set_cell(K.cells(help_row)[0], 'LEFT TAP / LEFT HOLD 1 S / RIGHT TAP')
K.set_cell(K.cells(help_row)[1], 'LEFT tap: next DART trial (saved). LEFT held 1 s: next volume level (saved; a ring chime plays). '
           'RIGHT tap: run the checks again (the round-clear sting plays when they finish).')
dart_row = K.row_with(sv, 'DART <trial>  FIRED')
K.set_cell(K.cells(dart_row)[2], 'Change trial with a LEFT tap (taps act on release)')
pf = K.table_hdr('FieldMeaningGood')
bo = K.row_with(pf, 'Bands that reached the panel')
K.add_row(pf, ['audio / max', 'Time to make 5.33 ms of sound (256 samples), average and worst.', 'Far below 5,333 us'], after=bo, like=bo)

# ---- Step 8: the sound chapter ----------------------------------------------------------------------------
s8 = K.para('Step 8 — Prove the audio hardware')
K.set_text(s8, 'Step 8 — Prove the audio hardware, bring up game sound, and choose the beginner-safe power plan')
K.set_text(s8.getnext(), 'Once the board, firmware, and controls are proven, move to the support systems. Prove the speaker, codec and '
           'amplifier with Waveshare\'s known-good audio example first. Then STRUTHIO\'s own game sound: the same sound effects and music '
           'as the browser game, from v0.11 on.')
K.set_text(K.para('Connect the chosen test speaker'), 'Connect the chosen test speaker to the board speaker header shown in the current '
           'Waveshare material and the v0.10 schematic. Run Waveshare\'s audio-out / ES8311 example at low gain first. That proves the '
           'physical audio chain on its own, before any STRUTHIO code is involved.')
K.set_text(K.para('If the vendor audio example causes resets'), 'If the vendor audio example causes resets, noise, or display problems, '
           'remove the speaker and return to the last known-good state. When the vendor example plays cleanly, flash STRUTHIO v0.11: '
           'service mode should report AUDIO OK and MUSIC OK, the round-clear sting plays when its checks finish, and in play you hear '
           'every flap, ring, joust, egg and death over the music.')
K.set_text(K.para('\u2022 Prove playback with Waveshare'), '• Prove playback with Waveshare\'s vendor audio example first, then STRUTHIO\'s game sound at volume 1 or 2.')
K.set_text(K.para('\u2022 If vendor-example sound is distorted'), '• If sound is distorted, lower the volume (service mode, hold LEFT) and check the speaker, header and wiring before suspecting firmware.')
hdr = K.para('Audio: what to expect from the current firmware')
K.set_text(hdr, 'Game sound: what the firmware plays')
honest = K.table_with('Honest status: the STRUTHIO firmware does not play game sound yet')
K.set_cell(K.cells(K.rows(honest)[0])[0], 'Status (v0.11): the firmware plays the browser game\'s sound effects and music. It compiles against the real '
           'ESP-IDF headers and its sound engine is checked against the browser\'s on the desktop, but nobody has heard it on a board yet. '
           'That is this step\'s job.')
parts = K.table_hdr('PartWhat it does')
K.set_cell(K.cells(K.row_with(parts, 'Audio codec'))[2], 'I2C address 0x18 (SDA 8, SCL 7) for settings; I2S MCLK 44, BCLK 13, LRCK 15, DOUT 16; 48 kHz, 16-bit, mono')
K.set_cell(K.cells(K.row_with(parts, 'about 1 W'))[1], '6–8 Ω, about 1 W (confirm the part; see the Audio Guide above).')
a = At(K.before_break(K.para('Step 9 — Print and prove')))
# insert after the parts table: place the new content before "What the firmware sets in the power chip"
a = At(K.para('What the firmware sets in the power chip'))
a.figure(FG('f12_audio.png'), 'FIGURE 8.1 — The sound path. Everything up to the "+" is the browser game\'s own sound engine, ported to C and '
         'checked against it sample by sample; after it, the ES8311 codec and the board\'s amplifier.')
a.audio('AUDIO GUIDE — Chapter 12B: Hear STRUTHIO', [
    'Game sound has two halves. The sound effects are not recordings: like the browser game, the handheld synthesises every flap, '
    'chime and crash from a few numbers per sound, the instant the game reports the event. The music is a recording: the browser\'s '
    '160-second loop, squeezed into 1.9 megabytes so it fits in its own corner of the flash chip.',
    'Start quiet. The firmware remembers a volume from 0 to 4 and starts at 2. Enter service mode, let the checks finish and listen '
    'for the round-clear sting. Hold LEFT for one second to step the volume; a ring chime plays at each level. Level 0 is silent.',
    'Then play. Every flap should tick, a ring should chime and dip the music for a moment, a joust should crash, and a death should '
    'fall in pitch. If sound stutters while the screen is busy, write down the log\'s audio time and report it: the sound task runs '
    'above the renderer, so the picture should drop a frame before the sound drops a note.',
])
a.table(['Game event', 'Sound', 'Voice', 'Music ducks?'], [
    ['Flap', 'short noise tick (at most one per 85 ms)', 'noise, falling', 'no'],
    ['Ring', 'bright chime', 'sine, rising', 'yes, briefly'],
    ['Joust clash', 'low crash', 'noise, falling', 'yes, if you are in it'],
    ['Joust win', 'rising call', 'triangle', 'yes'],
    ['Player death', 'long falling tone', 'triangle, falls 19 semitones', 'yes'],
    ['Egg / hatch', 'plink', 'sine', 'no'],
    ['Gold ring open / round start', 'sting, on the next beat', 'pulse', 'no'],
    ['Round clear', 'long sting, on the next beat', 'pulse', 'yes'],
], [1.8, 2.6, 2.0, 1.4], fill='CFE2F3')
a.table(['Volume level', 'Codec output', 'Use'], [
    ['0', 'muted', 'silent play'], ['1', '45 %', 'first power-up with a new speaker'], ['2 (default)', '60 %', 'normal'],
    ['3', '72 %', 'louder rooms'], ['4', '85 %', 'maximum; listen for distortion'],
], [1.8, 2.0, 4.0])
a.p('The percentages are starting values in firmware/main/main.c (VOLUME_PERCENT). If level 4 distorts on your speaker or level 1 is '
    'too loud, change them there and flash again.', italic=True)
a.h2('Why the sound fits on the ESP32')
a.table(['Piece', 'Size', 'Where'], [
    ['Synth, conductor, music player', 'a few KB of code, about 4 KB of memory', 'the firmware, internal RAM'],
    ['Soundtrack', '1.9 MB (the browser\'s MP3 is 3.2 MB)', 'new "music" flash area, 2.9 MB'],
    ['Art pack (unchanged)', '8.3 MB', '"assets" flash area, now 9 MB (was 11 MB)'],
    ['Work per 5.33 ms of sound', 'a few voices, a few multiplies each', 'audio task, core 0, above the renderer'],
], [2.4, 2.8, 2.6])
a.p('The music is stored as IMA ADPCM, 4 bits per sample at 24,000 samples a second: about a quarter the size of plain audio and '
    'almost free to decode. An MP3 decoder would have saved space but cost processor time the screen needs.')

# ---- acceptance, A0/A1, checklists -------------------------------------------------------------------
K.set_text(K.para('• ☐ AUDIO HARDWARE PASS'), '• ☐ AUDIO PASS: the vendor audio example plays cleanly through the selected speaker, '
           'then STRUTHIO plays its sound effects and music in play without stutter or distortion at the chosen volume.')
mx = K.table_hdr('GateA0 FUNCTIONAL PASS')
ar = K.row_with(mx, 'Optional hardware integration proof')
K.set_cell(K.cells(ar)[1], 'Optional for the core A0 game pass. Vendor audio example clean; service mode AUDIO OK + MUSIC OK.')
K.set_cell(K.cells(ar)[2], 'Selected speaker mounted cleanly; game sound effects and music clear at the chosen volume, no stutter in a 10-minute session.')
K.set_text(K.para('☐ Waveshare/vendor audio example plays cleanly'), '☐ Waveshare/vendor audio example plays cleanly at low gain')
a = At(K.para('Mechanical fit').getprevious().getnext()) if False else At(K.paras_starting('Mechanical fit')[0])
a.checks(['Service mode: AUDIO OK, MUSIC OK, round-clear sting heard', 'Volume stepped with LEFT hold; level chosen and noted',
          'In play: flap, ring, joust, death sounds over the music', 'Log "audio" time recorded (budget 5,333 us)'])

# ---- software chapter, troubleshooting, reference sheets ---------------------------------------------
K.set_text(K.para('• Game audio: the ES8311 driver is a stub.'), '• Game sound: written and checked against the browser on the desktop; '
           'not yet heard on a board. The five volume levels are starting values.')
K.replace_in(K.para('• To confirm on the board in hand:'), ', the ES8311 address', '')
cm = K.table_hdr('FileJob')
rp = K.row_with(cm, 'render/struthio_greybox.c')
K.add_row(cm, ['audio/struthio_audio.c', 'The browser\'s sound engine in C: conductor (events → notes), synth (7 voices), soundtrack loop, output stage.'], after=rp, like=rp)
fs = K.table_hdr('SymptomCheck in this order')
lastrow = K.rows(fs)[-1]
for vals in reversed([
        ['No sound at all', 'Service screen AUDIO line → volume not 0 (hold LEFT) → vendor audio example → speaker on the right header'],
        ['Sound effects but no music', 'Service screen "MUSIC NONE" → struthio_music.ima present when you built? → flash again'],
        ['Sound crackles or stutters', 'Lower the volume → log "audio" max time → USB supply → speaker rubbing in the shell']]):
    K.add_row(fs, vals, after=lastrow, like=lastrow)
i2c = K.table_hdr('I2C device')
K.set_cell(K.cells(K.row_with(i2c, 'ES8311'))[1], '0x18')
K.set_cell(K.cells(K.row_with(i2c, 'ES8311'))[2], 'Audio codec (Waveshare example default)')
gl = K.table_hdr('TermMeaning')
first = K.rows(gl)[1]
K.add_row(gl, ['ADPCM', 'A simple way to store sound in 4 bits per sample; the soundtrack uses it (1.9 MB for 160 s).'], after=first, like=first)
duck_after = K.row_with(gl, 'Digest / SHA-256')
K.add_row(gl, ['Ducking', 'Turning the music down for a moment so a sound effect stands out.'], after=duck_after, like=duck_after)
cond = K.row_with(gl, 'Chord')
K.add_row(gl, ['Codec', 'The chip that turns numbers into a speaker signal (here the ES8311).'], after=cond, like=cond)

# ---- shop sheet E -------------------------------------------------------------------------------------------
pl = K.table_hdr('Scenesim')
hdr_row = K.rows(pl)[0]
# add an "audio us" column: copy the last cell of every row
import copy
for tr in K.rows(pl):
    tc = copy.deepcopy(K.cells(tr)[-1]); K.cells(tr)[-1].addnext(tc)
    K.set_cell(tc, 'audio us' if tr is hdr_row else '')
grid = pl.find(K.qn('w:tblGrid'))
if grid is not None:
    cols = grid.findall(K.qn('w:gridCol'))
    nw = int(sum(int(c.get(K.qn('w:w'))) for c in cols) / (len(cols) + 1))
    for c in cols: c.set(K.qn('w:w'), str(nw))
    g = copy.deepcopy(cols[-1]); cols[-1].addnext(g)
    for tr in K.rows(pl):
        for tc in K.cells(tr):
            w = tc.find(K.qn('w:tcPr')).find(K.qn('w:tcW'))
            if w is not None: w.set(K.qn('w:w'), str(nw))

# ---- FAQ, verification, history ----------------------------------------------------------------------------
K.set_text(K.para('Why is there no sound?'), 'Is there sound?  Yes, from v0.11: the browser game\'s sound effects and its music. '
           'If you hear nothing, check the service screen\'s AUDIO line and the volume (hold LEFT for one second in service mode).')
a = At(K.para('What battery should I buy?'))
a.p('The soundtrack is the browser\'s MP3, isn\'t it?  The same music, re-stored as compressed 24 kHz mono audio (ADPCM) so it fits '
    'in 1.9 MB and costs almost no processor time. On a 1 W speaker you will not hear the difference.', bold_lead='Does the music sound the same as the browser?  ') if False else \
    a.p('The same recording, re-stored as compressed 24 kHz mono audio so it fits in 1.9 MB and costs almost no processor time. '
        'On a small speaker the difference is hard to hear.', bold_lead='Does the music sound the same as the browser?  ')
a.p('No. A normal idf.py flash keeps it. idf.py erase-flash resets it to 2.', bold_lead='Will flashing reset my volume?  ')
vt = K.table_hdr('CheckResult')
hud = K.row_with(vt, 'HUD layers')
K.add_row(vt, ['Game sound vs browser', 'conductor + synth on all 5 traces: 8,031 notes, 76–77 dB SNR, max difference 2 LSB'], after=hud, like=hud)
K.add_row(vt, ['Soundtrack', '3,840,000 samples (160.0 s), seamless loop, 28 dB coding SNR (normal for 4-bit ADPCM), re-encodes byte for byte'],
          after=K.row_with(vt, 'Game sound vs browser'), like=hud)
K.set_cell(K.cells(K.row_with(vt, 'Firmware compile'))[1], 'all sources against ESP-IDF 5.5.5 headers, board and codec drivers, -Wall -Wextra -Werror')
eh = K.table_hdr('EditionWhat changed')
K.add_row(eh, ['v0.11 / Build Manual 1.4', 'Game sound: the browser\'s SFX synth and conductor in C (checked sample by sample), the soundtrack in its own flash area, ES8311 driver, volume in service mode.'])

K.doc.save(OUT)
print('wrote', OUT)
