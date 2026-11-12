"""Media: audio and video, played inside Ledger with Qt Multimedia. Play, pause, scrub; the facts the file states.

Formats are recognised from their bytes (MP3, WAV, FLAC, Ogg, AIFF, MP4/M4A/MOV, Matroska/WebM, AVI). Playback uses
whatever decoders this computer's Qt build has; a file it cannot decode says so instead of failing silently.
For editing audio or video, use a dedicated program.
"""
from __future__ import annotations
import struct

KINDS = ('audio', 'video')
VIDEO_SUFFIXES = {'.mp4', '.m4v', '.mov', '.mkv', '.webm', '.avi', '.mpg', '.mpeg', '.ogv', '.wmv', '.3gp'}
AUDIO_BRANDS = (b'M4A ', b'M4B ', b'M4P ', b'mp42')


def claim(source, head):
    suffix = source.suffix
    if head.startswith(b'ID3') or (len(head) > 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0 and suffix in ('.mp3', '.mp2', '.aac')):return 'audio'
    if head.startswith(b'RIFF') and head[8:12] == b'WAVE':return 'audio'
    if head.startswith(b'RIFF') and head[8:12] == b'AVI ':return 'video'
    if head.startswith((b'fLaC', b'FORM')) and (head.startswith(b'fLaC') or head[8:12] in (b'AIFF', b'AIFC')):return 'audio'
    if head.startswith(b'OggS'):return 'video' if suffix == '.ogv' or b'theora' in head[:200] else 'audio'
    if head.startswith(b'\x1aE\xdf\xa3'):return 'audio' if suffix in ('.mka', '.weba') else 'video'
    if len(head) > 12 and head[4:8] == b'ftyp':
        brand = head[8:12]
        if brand in (b'heic', b'heix', b'mif1', b'avif', b'msf1'):return None  # pictures, for Images+
        return 'audio' if suffix in ('.m4a', '.m4b', '.aac') or brand in (b'M4A ', b'M4B ') else 'video'
    return None


def wav_facts(raw):
    facts = [];at = 12
    while at + 8 <= len(raw):
        chunk, size = raw[at:at + 4], struct.unpack('<I', raw[at + 4:at + 8])[0]
        if chunk == b'fmt ' and size >= 16:
            fmt, channels, rate, byte_rate, _, bits = struct.unpack('<HHIIHH', raw[at + 8:at + 24])
            facts += [('Channels', str(channels)), ('Sample rate', '%d Hz' % rate), ('Bits', str(bits))]
            facts.append(('_byte_rate', byte_rate))
        if chunk == b'data':
            rate = dict(facts).get('_byte_rate')
            if rate:facts.append(('Length', '%.1f s' % (size / rate)))
            break
        at += 8 + size + (size & 1)
    return [(k, v) for k, v in facts if not k.startswith('_')]


def describe(source, view):
    head = source.read(0, 64 * 1024)
    container = ('WAV' if head[8:12] == b'WAVE' else 'MP3' if head.startswith(b'ID3') or head[:1] == b'\xff' else 'FLAC' if head.startswith(b'fLaC')
                 else 'Ogg' if head.startswith(b'OggS') else 'Matroska/WebM' if head.startswith(b'\x1aE\xdf\xa3') else 'AIFF' if head.startswith(b'FORM')
                 else 'AVI' if head[8:12] == b'AVI ' else 'MPEG-4 (' + head[8:12].decode('ascii', 'replace').strip() + ')' if head[4:8] == b'ftyp' else 'media')
    view['summary'].append(('Container', container))
    if container == 'WAV':view['summary'] += wav_facts(head)
    view['media'] = True


DESCRIBERS = {'audio': describe, 'video': describe}


def MediaPage(tab):
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtMultimedia import QAudioOutput, QMediaMetaData, QMediaPlayer
    from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget
    from ..shell2 import sentence
    page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 8, 0, 0)
    if tab.source.path is None:
        box.addWidget(QLabel('Media inside an archive plays after you save a copy of it.'));return page
    player = QMediaPlayer(page);audio = QAudioOutput(page);player.setAudioOutput(audio);page.player = player
    if tab.view['kind'] == 'video':
        from PySide6.QtMultimediaWidgets import QVideoWidget
        screen = QVideoWidget();screen.setMinimumHeight(240);player.setVideoOutput(screen);box.addWidget(screen, 1)
    words = QLabel();box.addWidget(words)
    slider = QSlider(Qt.Horizontal);slider.setAccessibleName('Position');box.addWidget(slider)
    facts = QLabel();facts.setWordWrap(True);facts.setStyleSheet('color:#6c675e');box.addWidget(facts)
    if tab.view['kind'] == 'audio':box.addStretch(1)

    def clock(ms):
        s = int(ms // 1000);return '%d:%02d' % (s // 60, s % 60)

    def refresh(*_):
        playing = player.playbackState() == QMediaPlayer.PlayingState
        sentence('{play}  ·  ' + clock(player.position()) + ' of ' + clock(player.duration()) + '  ·  {back}',
                 {'play': ('pause' if playing else 'play', player.pause if playing else player.play), 'back': ('back to the start', lambda:player.setPosition(0))}, words)

    def metadata():
        data = player.metaData();found = []
        for key, label in ((QMediaMetaData.Title, 'Title'), (QMediaMetaData.ContributingArtist, 'Artist'), (QMediaMetaData.AlbumTitle, 'Album'),
                           (QMediaMetaData.Resolution, 'Picture'), (QMediaMetaData.Duration, None)):
            try:value = data.value(key)
            except RuntimeError:continue  # a value this Qt build cannot convert is left out, not shown wrong
            if label is None:continue
            if value not in (None, '') and str(value) not in ('', 'UnspecifiedFormat'):found.append(label + ': ' + str(value).replace('QSize(', '').rstrip(')'))
        facts.setText('  ·  '.join(found))

    def failed(error, text):
        facts.setText('This computer cannot play it: ' + (text or 'no decoder') + '. The facts and bytes are still shown.')

    player.durationChanged.connect(lambda d:(slider.setRange(0, int(d)), refresh()))
    player.positionChanged.connect(lambda p:(slider.blockSignals(True), slider.setValue(int(p)), slider.blockSignals(False), refresh()))
    player.playbackStateChanged.connect(refresh);player.metaDataChanged.connect(metadata);player.errorOccurred.connect(failed)
    slider.sliderMoved.connect(lambda v:player.setPosition(v))
    player.setSource(QUrl.fromLocalFile(str(tab.source.path)));refresh()
    page.destroyed.connect(lambda *_:None)
    return page


def pages(tab, view):
    if not view.get('media'):return []
    return [('Play', lambda:MediaPage(tab))]


def thumbnail(path, kind, size):
    """A still frame for video, when this computer can decode one within a second; otherwise the plain card."""
    if kind != 'video':return None
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
    from PySide6.QtCore import Qt
    player = QMediaPlayer();sink = QVideoSink();player.setVideoSink(sink);found = {}
    loop = QEventLoop()

    def frame(f):
        image = f.toImage()
        if not image.isNull() and 'image' not in found:found['image'] = image.scaled(size, size, Qt.KeepAspectRatio);loop.quit()
    sink.videoFrameChanged.connect(frame);player.errorOccurred.connect(lambda *_:loop.quit())
    QTimer.singleShot(1000, loop.quit);player.setSource(QUrl.fromLocalFile(str(path)));player.play();loop.exec()
    player.stop();player.setSource(QUrl())
    return found.get('image')
