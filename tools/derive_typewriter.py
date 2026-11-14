"""Build Kasandra's two typewriter faces from Special Elite (Apache 2.0). Build time only: the program loads the files
this writes and never runs this.

    Kasandra Elite       the words face: Special Elite with a slashed zero, an l that stands on a right foot only (so
                         l, 1 and I are told apart), and tabular figures (every digit 1254 units wide, no kerning between
                         two digits, so a column of numbers lines up). Every other glyph, its hinting and its metrics are
                         kept byte for byte.
    Kasandra Elite Mono  the face for lines, numbers, addresses, Terminal and tags: the same outlines on a fixed 0.6 em
                         pitch, on IBM Plex Mono's line (ascent 2099, descent 563 per 2048 units), so a row measured in
                         Plex Mono keeps its height; no kerning or ligatures.

The owner, 14 November 2026, asked for every face of the window in this typewriter face. The derived faces are named for
her appearance, never for anything else.

Run (fontTools 4.40 or later and skia-pathops):

    python -I tools/derive_typewriter.py [program root]

The result is byte-reproducible: the source's timestamps are kept and nothing is stamped with the build's time.
"""
import math
import sys
from pathlib import Path

import pathops
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram

SOURCE_SHA = 'a776fcb4ceb8bdf03e2967688ebdad42680de5b91a7e62c17e718ae212d14bc4'
DIGITS = 'zero one two three four five six seven eight nine'.split()
FIGURE = 1254                       # every digit's advance in the words face: the widest digit's (four)
CELL = 1229                         # the mono face's pitch: 0.6 em of 2048 units, Plex Mono's 600 of 1000
ROOM = CELL - 40                    # ink wider than this is narrowed about its centre, so neighbours never touch
ASCENT, DESCENT = 2099, 563         # IBM Plex Mono's line (hhea 1025/-275 per 1000), in 2048 units
WORDS_NOTE = 'Derived from Special Elite (Apache 2.0) for Graphite: slashed zero, l on a right foot, tabular figures'


def outline(glyphset, name):
    """The glyph's outline as a skia path (components drawn in)."""
    pen = DecomposingRecordingPen(glyphset);glyphset[name].draw(pen)
    path = pathops.Path();pen.replay(path.getPen())
    return path


def rect(x0, y0, x1, y1):
    path = pathops.Path();pen = path.getPen()
    pen.moveTo((x0, y0));pen.lineTo((x1, y0));pen.lineTo((x1, y1));pen.lineTo((x0, y1));pen.closePath()
    return path


def bar(x0, y0, x1, y1, half):
    """A straight stroke from (x0, y0) to (x1, y1), `half` units either side of its centre line."""
    length = math.hypot(x1 - x0, y1 - y0);nx, ny = -(y1 - y0) / length * half, (x1 - x0) / length * half
    path = pathops.Path();pen = path.getPen()
    pen.moveTo((x0 + nx, y0 + ny));pen.lineTo((x1 + nx, y1 + ny));pen.lineTo((x1 - nx, y1 - ny));pen.lineTo((x0 - nx, y0 - ny));pen.closePath()
    return path


def glyph_of(path, dx=0):
    """A TrueType glyph from a path, moved dx units along, with an empty instruction program."""
    pen = TTGlyphPen(None);path.draw(TransformPen(pen, (1, 0, 0, 1, dx, 0)) if dx else pen)
    glyph = pen.glyph();glyph.program = ttProgram.Program();glyph.program.fromBytecode(b'')
    return glyph


def set_names(font, family, note):
    table = font['name'];ps = family.replace(' ', '') + '-Regular'
    for number in (1, 3, 4, 6, 10, 16, 17):table.removeNames(nameID=number)
    for platform, encoding, language in ((1, 0, 0), (3, 1, 0x409)):
        for number, text in ((1, family), (3, family + ' 1.000 (derived from Special Elite)'), (4, family + ' Regular'), (6, ps),
                             (10, note), (16, family), (17, 'Regular')):
            table.setName(text, number, platform, encoding, language)


def words(source, out):
    """Kasandra Elite. Only zero to nine and l are written again; the font is opened without recalculation, so every
    other glyph is written back with its own bytes."""
    font = TTFont(source, recalcBBoxes=False, recalcTimestamp=False)
    glyf, hmtx, cmap = font['glyf'], font['hmtx'], font.getBestCmap()
    assert [cmap[ord(c)] for c in '0123456789'] == DIGITS and cmap[ord('l')] == 'l'
    glyphset = font.getGlyphSet()
    shapes = {name: outline(glyphset, name) for name in DIGITS + ['l']}
    # the zero takes a slash in the face's own weight across its counter; the l loses the left half of its foot
    shapes['zero'] = pathops.op(shapes['zero'], bar(330, 330, 890, 1150, 62), pathops.PathOp.UNION)
    shapes['l'] = pathops.op(shapes['l'], rect(-200, -200, 446, 132), pathops.PathOp.DIFFERENCE)
    changed = {}
    for name, path in shapes.items():
        advance = FIGURE if name in DIGITS else hmtx[name][0]
        dx = math.floor((FIGURE - hmtx[name][0]) / 2 + 0.5) if name in DIGITS else 0
        if name in DIGITS and name != 'zero':      # a digit only moves: its own contours, shifted, so its drawing is unchanged
            glyph = glyf[name];glyph.coordinates.translate((dx, 0));glyph.program = ttProgram.Program();glyph.program.fromBytecode(b'')
        else:
            glyph = glyph_of(path, dx)
        glyph.recalcBounds(glyf);glyf[name] = glyph;changed[name] = glyph
        hmtx[name] = (advance, glyph.xMin)
    maxp, head = font['maxp'], font['head']
    for glyph in changed.values():
        points, contours = glyph.getMaxpValues()[:2]
        maxp.maxPoints = max(maxp.maxPoints, points);maxp.maxContours = max(maxp.maxContours, contours)
        head.xMin = min(head.xMin, glyph.xMin);head.yMin = min(head.yMin, glyph.yMin)
        head.xMax = max(head.xMax, glyph.xMax);head.yMax = max(head.yMax, glyph.yMax)
    font['hhea'].advanceWidthMax = max(width for width, _ in hmtx.metrics.values())
    digits = set(DIGITS)
    # Two digits never kern, so every pair of digits is two figures wide (the kern table, and GPOS pair kerning)
    for table in font['kern'].kernTables if 'kern' in font else ():
        for pair in [p for p in table.kernTable if p[0] in digits and p[1] in digits]:del table.kernTable[pair]
    if 'GPOS' in font:
        for lookup in font['GPOS'].table.LookupList.Lookup:
            for sub in lookup.SubTable:
                if lookup.LookupType == 2 and sub.Format == 1:
                    for first, pairs in zip(sub.Coverage.glyphs, sub.PairSet):
                        if first in digits:
                            pairs.PairValueRecord = [r for r in pairs.PairValueRecord if r.SecondGlyph not in digits]
                            pairs.PairValueCount = len(pairs.PairValueRecord)
                elif lookup.LookupType == 2 and sub.Format == 2:      # class kerning: refuse rather than leave a digit pair kerned
                    classed = set(sub.Coverage.glyphs) & digits and set(sub.ClassDef2.classDefs) & digits
                    assert not classed, 'class kerning between digits: not handled'
    set_names(font, 'Kasandra Elite', WORDS_NOTE + '.')
    font.save(out)
    return out


def mono(words_face, out):
    """Kasandra Elite Mono: every glyph of the words face on one pitch, its ink centred in the cell."""
    font = TTFont(words_face, recalcTimestamp=False)
    glyf, hmtx = font['glyf'], font['hmtx'];glyphset = font.getGlyphSet()
    drawn = {}
    for name in font.getGlyphOrder():
        recording = DecomposingRecordingPen(glyphset);glyphset[name].draw(recording)
        bounds = BoundsPen(glyphset);recording.replay(bounds)
        advance = hmtx[name][0]
        if advance == 0:                         # a mark that sits on the letter before it stays without width
            transform = (1, 0, 0, 1, 0, 0);advance = 0
        elif bounds.bounds is None:              # a space: only its width changes
            transform = (1, 0, 0, 1, 0, 0);advance = CELL
        else:
            x0, _, x1, _ = bounds.bounds;centre = (x0 + x1) / 2;scale = min(1.0, ROOM / max(1.0, x1 - x0))
            transform = (scale, 0, 0, 1, CELL / 2 - centre * scale, 0);advance = CELL
        pen = TTGlyphPen(None);recording.replay(TransformPen(pen, transform))
        glyph = pen.glyph();glyph.program = ttProgram.Program();glyph.program.fromBytecode(b'')
        drawn[name] = (glyph, advance)
    for name, (glyph, advance) in drawn.items():
        glyf[name] = glyph;glyph.recalcBounds(glyf);hmtx[name] = (advance, glyph.xMin if glyph.numberOfContours else 0)
    for tag in ('kern', 'GPOS', 'GSUB', 'fpgm', 'prep', 'cvt ', 'hdmx', 'LTSH', 'VDMX'):
        if tag in font:del font[tag]
    gasp = newTable('gasp');gasp.version = 1;gasp.gaspRange = {0xFFFF: 0x000A};font['gasp'] = gasp
    maxp = font['maxp'];maxp.maxFunctionDefs = maxp.maxInstructionDefs = maxp.maxSizeOfInstructions = 0
    hhea, os2, post = font['hhea'], font['OS/2'], font['post']
    hhea.ascent, hhea.descent, hhea.lineGap = ASCENT, -DESCENT, 0
    os2.version = max(4, os2.version)            # USE_TYPO_METRICS is read from version 4 on
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ASCENT, -DESCENT, 0
    os2.usWinAscent, os2.usWinDescent = ASCENT, DESCENT
    os2.fsSelection |= 1 << 7
    post.isFixedPitch = 1;os2.panose.bProportion = 9;os2.xAvgCharWidth = CELL;hhea.advanceWidthMax = CELL
    set_names(font, 'Kasandra Elite Mono', WORDS_NOTE + '; fixed 0.6 em pitch on IBM Plex Mono\'s line, no kerning or ligatures.')
    font.save(out)
    return out


def main(root):
    import hashlib
    folder = Path(root) / 'branding' / 'fonts' / 'typewriter'
    source = folder / 'SpecialElite-Regular.ttf'
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise SystemExit('SpecialElite-Regular.ttf is not the bundled release; nothing written')
    elite = words(str(source), str(folder / 'KasandraElite-Regular.ttf'))
    fixed = mono(elite, str(folder / 'KasandraEliteMono-Regular.ttf'))
    for path in (elite, fixed):print('%s · SHA-256 %s' % (Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
