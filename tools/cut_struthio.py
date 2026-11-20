"""The owner's Struthio, cut to its drawing on no ground: branding/struthio/struthio.png.

The owner, 20 November 2026, with his own picture of a Struthio (an ostrich drawn with circuit traces): the Struthio in the
head's upper right is the Apps button, "like a windows start menu" (0.8.6). The file as given (1120 x 1404, RGB, SHA-256
22ad9345e52622dcbd61a67c209ef5a51446fe49da827e3394508007f2b92e42) is the drawing on a white ground. The asset is the drawing
alone:

  the ground      every near-white pixel (each channel 236 or more) joined to the picture's edge is made clear; white
                  inside the drawing, were there any, would stay
  the rim         a pixel of the drawing touching the ground is a mix of the drawing's colour and the white: it keeps the
                  colour of the drawing beside it, with the share of it that pixel holds as its alpha, so no white fringe is
                  left on a dark band
  the crop        trimmed to the drawing (what has any alpha)
  the size        drawn down smoothly to KEPT pixels tall (from about 1195), enough for the head at any interface scale and
                  on a screen of twice the density; workbench/struthio_mark.py draws it at the head's height on whole pixels

    python -B tools/cut_struthio.py OWNER_FILE [program root]

A file that is not the owner's (by its SHA-256) is refused and nothing is written. The result's SHA-256 is recorded in
branding/struthio/README.md and in workbench/struthio_mark.py: the program shows only those bytes.
"""
import hashlib
import sys
from collections import deque
from pathlib import Path

SOURCE_SHA256 = '22ad9345e52622dcbd61a67c209ef5a51446fe49da827e3394508007f2b92e42'
SOURCE_SIZE = (1120, 1404)
WHITE = 236         # a ground pixel: every channel this or more
KEPT = 512          # the asset's height in pixels


def cut(source_path, root):
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QImage
    data = Path(source_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise SystemExit('%s is not the owner\'s file (its SHA-256 differs); nothing written' % source_path)
    image = QImage();image.loadFromData(data)
    image = image.convertToFormat(QImage.Format_ARGB32)
    if (image.width(), image.height()) != SOURCE_SIZE:raise SystemExit('unexpected size; nothing written')
    w, h = image.width(), image.height();bpl = image.bytesPerLine();bits = bytearray(image.constBits())

    def rgb(x, y):
        at = y * bpl + 4 * x;return bits[at + 2], bits[at + 1], bits[at]      # ARGB32 is B, G, R, A in memory here

    def white(x, y):
        return min(rgb(x, y)) >= WHITE
    ground = bytearray(w * h)      # 1: the ground, joined to the edge
    todo = deque()
    for x in range(w):
        for y in (0, h - 1):
            if white(x, y) and not ground[y * w + x]:ground[y * w + x] = 1;todo.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if white(x, y) and not ground[y * w + x]:ground[y * w + x] = 1;todo.append((x, y))
    while todo:
        x, y = todo.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not ground[ny * w + nx] and white(nx, ny):
                ground[ny * w + nx] = 1;todo.append((nx, ny))

    def touches(x, y):
        return any(ground[ny * w + nx] for nx in (x - 1, x, x + 1) for ny in (y - 1, y, y + 1) if 0 <= nx < w and 0 <= ny < h)
    rim = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            if not ground[y * w + x] and touches(x, y):rim[y * w + x] = 1
    out = bytearray(bits)
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            at = y * bpl + 4 * x;i = y * w + x
            if ground[i]:
                out[at:at + 4] = b'\0\0\0\0';continue
            if rim[i]:
                inner = None
                for reach in (1, 2, 3):
                    for ny in range(max(0, y - reach), min(h, y + reach + 1)):
                        for nx in range(max(0, x - reach), min(w, x + reach + 1)):
                            j = ny * w + nx
                            if not ground[j] and not rim[j]:inner = rgb(nx, ny);break
                        if inner:break
                    if inner:break
                r, g, b = rgb(x, y)
                if inner is None:      # a lone rim pixel: its share of anything not white
                    alpha = max(255 - r, 255 - g, 255 - b) / 255.0;colour = (r, g, b)
                else:                  # the drawing's colour beside it, at the share this pixel holds of it
                    shares = [(255 - c) / (255 - k) for c, k in zip((r, g, b), inner) if 255 - k > 20]
                    alpha = max(0.0, min(1.0, max(shares) if shares else 1.0));colour = inner
                a = round(255 * alpha)
                if a == 0:
                    out[at:at + 4] = b'\0\0\0\0';continue
                out[at] = colour[2];out[at + 1] = colour[1];out[at + 2] = colour[0];out[at + 3] = a
            left, right, top, bottom = min(left, x), max(right, x), min(top, y), max(bottom, y)
    clean = QImage(bytes(out), w, h, bpl, QImage.Format_ARGB32).copy(QRect(left, top, right - left + 1, bottom - top + 1))
    clean = clean.convertToFormat(QImage.Format_ARGB32_Premultiplied)      # drawn down premultiplied: no dark or white halo
    small = clean.scaled(round(clean.width() * KEPT / clean.height()), KEPT, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    small = small.convertToFormat(QImage.Format_ARGB32)
    folder = Path(root) / 'branding' / 'struthio';folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'struthio.png'
    if not small.save(str(path), 'PNG'):raise SystemExit('could not write %s' % path)
    print('%s  %d x %d  (the drawing: x %d-%d, y %d-%d of the file)  SHA-256 %s' % (path, small.width(), small.height(), left, right, top, bottom,
                                                                                hashlib.sha256(path.read_bytes()).hexdigest()))
    return path


if __name__ == '__main__':
    if len(sys.argv) < 2:raise SystemExit(__doc__)
    cut(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parents[1])
