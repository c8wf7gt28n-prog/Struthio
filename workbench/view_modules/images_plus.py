"""Images+: more picture formats, camera details, and small fixes that save a changed copy.

Qt reads PNG, JPEG, GIF, BMP, WebP, TIFF, SVG, ICO, TGA and more. HEIC and AVIF need a decoder this computer may not
have; they are named honestly instead of shown as noise. Rotate, crop and resize work on what you see and are saved as
a new file beside the original, which is never changed. For painting and retouching, use GIMP or similar.
"""
from __future__ import annotations
import struct

KINDS = ('image',)
HEIF_BRANDS = (b'heic', b'heix', b'hevc', b'heim', b'heis', b'mif1', b'msf1', b'avif', b'avis')
EXIF_TAGS = {0x010F: 'Camera make', 0x0110: 'Camera model', 0x0112: 'Orientation', 0x0132: 'Taken', 0x9003: 'Taken', 0xA002: 'Width',
             0xA003: 'Height', 0x829A: 'Exposure', 0x829D: 'F-number', 0x8827: 'ISO', 0x920A: 'Focal length'}
ORIENTATION = {1: 'upright', 3: 'upside down', 6: 'turned right', 8: 'turned left'}


def claim(source, head):
    suffix = source.suffix
    if head.startswith((b'II*\x00', b'MM\x00*')):return 'image'
    if head.startswith(b'\x00\x00\x01\x00') and suffix in ('.ico', '.cur'):return 'image'
    if len(head) > 12 and head[4:8] == b'ftyp' and head[8:12] in HEIF_BRANDS:return 'image'
    if suffix in ('.svg', '.svgz'):
        start = head[:1024].lower()
        if b'<svg' in start or (suffix == '.svgz' and head.startswith(b'\x1f\x8b')):return 'image'
    if suffix in ('.tga', '.pbm', '.pgm', '.ppm', '.xpm', '.xbm'):return 'image'
    return None


def exif(raw):
    """A few readable facts from a JPEG's EXIF block. Standard library only; anything odd is skipped."""
    found = {}
    at = raw.find(b'Exif\x00\x00')
    if at < 0:return found
    tiff = raw[at + 6:]
    if len(tiff) < 8:return found
    order = '<' if tiff[:2] == b'II' else '>'

    def value(kind, count, offset_or_value):
        size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}.get(kind, 0) * count
        data = offset_or_value if size <= 4 else tiff[struct.unpack(order + 'I', offset_or_value)[0]:][:size]
        if kind == 2:return data[:count].split(b'\x00')[0].decode('latin-1', 'replace').strip()
        if kind == 3:return struct.unpack(order + 'H', data[:2])[0]
        if kind == 4:return struct.unpack(order + 'I', data[:4])[0]
        if kind == 5:
            n, d = struct.unpack(order + 'II', data[:8]);return n / d if d else 0
        return None

    def directory(offset, depth=0):
        if depth > 2 or offset + 2 > len(tiff):return
        count = struct.unpack(order + 'H', tiff[offset:offset + 2])[0]
        for i in range(min(count, 200)):
            entry = tiff[offset + 2 + 12 * i:offset + 14 + 12 * i]
            if len(entry) < 12:return
            tag, kind, n = struct.unpack(order + 'HHI', entry[:8])
            if tag == 0x8769:directory(struct.unpack(order + 'I', entry[8:12])[0], depth + 1);continue
            if tag in EXIF_TAGS:
                try:found.setdefault(EXIF_TAGS[tag], value(kind, n, entry[8:12]))
                except (struct.error, ZeroDivisionError):pass
    try:directory(struct.unpack(order + 'I', tiff[4:8])[0])
    except struct.error:pass
    return found


def describe(source, view):
    from ..universal_view import describe_image
    describe_image(source, view)
    head = source.read(0, 64)
    if len(head) > 12 and head[4:8] == b'ftyp' and head[8:12] in HEIF_BRANDS:
        view['image'] = False
        view['notice'] = 'A HEIC/AVIF picture. This computer has no decoder for it yet; the facts and bytes are shown. Ledger never sends it anywhere to convert it.'
        view['summary'].append(('Format', head[8:12].decode('ascii', 'replace').upper()));return
    if head.startswith(b'\xff\xd8'):
        facts = exif(source.read(0, 128 * 1024))
        for label, value in facts.items():
            if value in (None, ''):continue
            if label == 'Orientation':value = ORIENTATION.get(value, str(value))
            elif label == 'Exposure' and isinstance(value, float):value = ('1/%d s' % round(1 / value)) if 0 < value < 1 else '%g s' % value
            elif label == 'F-number' and isinstance(value, float):value = 'f/%.1f' % value
            elif label == 'Focal length' and isinstance(value, float):value = '%g mm' % value
            view['summary'].append((label, str(value)))
    if source.path is None:return  # inside an archive: the bytes are shown; Qt's readers are given files only
    try:
        from PySide6.QtGui import QImageReader
        reader = QImageReader(str(source.path));size = reader.size()
        if size.isValid() and not any(k == 'Pixels' for k, _ in view['summary']):view['summary'].append(('Pixels', '%d × %d' % (size.width(), size.height())))
        fmt = bytes(reader.format()).decode() if reader.format() else ''
        if fmt:view['summary'].append(('Format', fmt.upper()))
        if reader.imageCount() > 1:view['summary'].append(('Frames', str(reader.imageCount())))
    except Exception:
        pass


DESCRIBERS = {'image': describe}


def pages(tab, view):
    if view.get('kind') != 'image' or not view.get('image'):return []
    return [('Adjust', lambda:AdjustPage(tab))]


def AdjustPage(tab):
    """Rotate, crop, resize; saved as a changed copy beside the original."""
    from PySide6.QtCore import QRect, QSize, Qt
    from PySide6.QtGui import QImage, QPixmap, QTransform
    from PySide6.QtWidgets import QFileDialog, QInputDialog, QLabel, QRubberBand, QScrollArea, QVBoxLayout, QWidget
    from ..shell2 import QUIET, sentence

    class Canvas(QLabel):
        def __init__(self):
            super().__init__();self.band = QRubberBand(QRubberBand.Rectangle, self);self.origin = None;self.selection = None
            self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        def mousePressEvent(self, event):
            self.origin = event.position().toPoint();self.band.setGeometry(QRect(self.origin, QSize()));self.band.show()

        def mouseMoveEvent(self, event):
            if self.origin is not None:self.band.setGeometry(QRect(self.origin, event.position().toPoint()).normalized())

        def mouseReleaseEvent(self, event):
            if self.origin is None:return
            rect = QRect(self.origin, event.position().toPoint()).normalized();self.origin = None
            self.selection = rect if rect.width() > 4 and rect.height() > 4 else None
            if self.selection is None:self.band.hide()
            page.refresh()

    page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 8, 0, 0)
    original = QImage();original.loadFromData(tab.source.read())
    state = {'image': original}
    words = QLabel();box.addWidget(words)
    note = QLabel('Drag across the picture to choose a crop. The original file is never changed: Save a changed copy writes a new file.')
    note.setWordWrap(True);note.setStyleSheet('color:%s' % QUIET);box.addWidget(note)
    scroll = QScrollArea();canvas = Canvas();scroll.setWidget(canvas);scroll.setWidgetResizable(False);box.addWidget(scroll, 1)

    def scale():
        image = state['image'];width = max(200, scroll.viewport().width() - 8)
        return min(1.0, width / max(1, image.width()))

    def show():
        image = state['image'];f = scale()
        canvas.setPixmap(QPixmap.fromImage(image).scaled(QSize(int(image.width() * f), int(image.height() * f)), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        canvas.adjustSize();canvas.band.hide();canvas.selection = None;page.refresh()

    def rotate(angle):
        state['image'] = state['image'].transformed(QTransform().rotate(angle));show()

    def crop():
        if canvas.selection is None:return
        f = scale();r = canvas.selection
        state['image'] = state['image'].copy(QRect(int(r.x() / f), int(r.y() / f), int(r.width() / f), int(r.height() / f)));show()

    def resize():
        image = state['image']
        width, ok = QInputDialog.getInt(page, 'Resize', 'New width in pixels (height follows)', image.width(), 1, 20000)
        if ok and width != image.width():state['image'] = image.scaledToWidth(width, Qt.SmoothTransformation);show()

    def reset():
        state['image'] = original;show()

    def save():
        from pathlib import Path
        base = tab.source.path or Path(tab.source.name)
        suggested = str(base.with_name(base.stem + ' changed' + (base.suffix if base.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff') else '.png')))
        target, _ = QFileDialog.getSaveFileName(page, 'Save a changed copy', suggested, 'Pictures (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)')
        if not target:return
        if tab.source.path is not None and Path(target).resolve() == Path(tab.source.path).resolve():
            note.setText('That is the original. Choose another name: the original is never changed.');return
        ok = state['image'].save(target)
        note.setText(('Saved a changed copy: ' + target) if ok else 'Could not save to ' + target)

    def refresh():
        image = state['image']
        sentence('%d × %d  ·  {left}  ·  {right}  ·  {crop}  ·  {resize}  ·  {reset}  ·  {save}' % (image.width(), image.height()),
                 {'left': ('rotate left', lambda:rotate(-90)), 'right': ('rotate right', lambda:rotate(90)),
                  'crop': ('crop to selection' if canvas.selection else 'crop (drag first)', crop), 'resize': ('resize…', resize),
                  'reset': ('start over', reset), 'save': ('save a changed copy…', save)}, words)
    page.refresh = refresh
    if original.isNull():words.setText('This picture could not be decoded for adjusting.');return page
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, show);refresh()
    return page
