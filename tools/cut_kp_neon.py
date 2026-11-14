"""The owner's neon kp logo, cut to its clean drawing: branding/kasandra/kp_neon.png.

The owner, 14 November 2026: "New logo for our upper right progman.exe menu ;) ... Omg I love it", and "Retire any other kp
icon". The file as given (1586 x 992, SHA-256 70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e) is the
drawing with real alpha and, round it, a neon fringe stored in pixels of alpha 1 to 9 (of 255) that carry saturated colour:
drawn as stored the fringe vanishes, and restored to full strength it turns to grey mush. So the asset is the drawing alone:
every pixel of alpha 200 or more exactly as given (its colour and its alpha), every other pixel clear, trimmed to the
drawing (x 102 to 1502 and y 80 to 917 of the file: 1401 x 838). The neon round it is drawn by Graphite
(workbench/kp_logo.py), at the strength of the Glow dial, and is none on the Clean desk.

    python -B tools/cut_kp_neon.py OWNER_FILE [program root]

A file that is not the owner's (by its SHA-256) is refused and nothing is written. The result's SHA-256 is recorded in
branding/kasandra/README.md and in workbench/kasandra_art.py MARKS: the program shows only those bytes.
"""
import hashlib
import sys
from pathlib import Path

SOURCE_SHA256 = '70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e'
SOURCE_SIZE = (1586, 992)
KEEP = 200          # the drawing: alpha this or more; the fringe below it is cleared


def cut(source_path, root):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage
    data = Path(source_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise SystemExit('%s is not the owner\'s file (its SHA-256 differs); nothing written' % source_path)
    image = QImage();image.loadFromData(data)
    image = image.convertToFormat(QImage.Format_ARGB32)
    if (image.width(), image.height()) != SOURCE_SIZE:raise SystemExit('unexpected size; nothing written')
    w, h = image.width(), image.height();bpl = image.bytesPerLine();bits = bytearray(image.constBits())
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        row = y * bpl
        for x in range(w):
            at = row + 4 * x
            if bits[at + 3] >= KEEP:
                left, right, top, bottom = min(left, x), max(right, x), min(top, y), max(bottom, y)
            else:bits[at:at + 4] = b'\0\0\0\0'
    clean = QImage(bytes(bits), w, h, bpl, QImage.Format_ARGB32).copy(QRect(left, top, right - left + 1, bottom - top + 1))
    out = Path(root) / 'branding' / 'kasandra' / 'kp_neon.png'
    if not clean.save(str(out), 'PNG'):raise SystemExit('could not write %s' % out)
    print('%s  %d x %d  (x %d-%d, y %d-%d of the file)  SHA-256 %s' % (out, clean.width(), clean.height(), left, right, top, bottom,
                                                                     hashlib.sha256(out.read_bytes()).hexdigest()))
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:raise SystemExit(__doc__)
    cut(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parents[1])
