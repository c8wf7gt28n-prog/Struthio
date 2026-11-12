"""Universal viewer: identify any file by its contents and describe it for reading.

Everything here is read-only and bounded. Nothing is mounted, executed or
written. A file is identified by its bytes first and its name second, then
described as a view model the desktop draws and Slate can read:

  text and code · Markdown · JSON · CSV · PDF · images · DOCX/XLSX/ODF text
  ZIP · TAR · gzip/bzip2/xz · 7z/RAR (7-Zip) · FAT12/16/32 images · MBR/GPT disks
  NTFS · ext2/3/4 · ISO 9660 (7-Zip) · ELF · SQLite · Gerber RS-274X · Excellon
  KiCad · STL · STEP · anything else as hex

Archives and disk images are trees: ``member(source, path)`` returns the bytes
of one member, which is described the same way, so a C file inside a ZIP inside
a FAT image opens like any other C file.
"""
from __future__ import annotations
import bz2
import codecs
import gzip
import hashlib
import io
import json
import lzma
import math
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import tarfile
import zipfile
from pathlib import Path

MAX_READ = 64 * 1024 * 1024        # bytes read from any one file or member
MAX_TEXT = 2 * 1024 * 1024         # characters shown as text
MAX_HEX = 64 * 1024                # bytes shown as hex
MAX_ENTRIES = 20000                # tree entries listed
MAX_TABLE_ROWS = 2000
CODE = {'.c': 'c', '.h': 'c', '.cpp': 'cpp', '.hpp': 'cpp', '.cc': 'cpp', '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.rs': 'rust', '.go': 'go', '.java': 'java', '.cs': 'csharp', '.sh': 'shell', '.v': 'verilog', '.sv': 'verilog', '.vhd': 'vhdl',
        '.s': 'assembly', '.asm': 'assembly', '.ld': 'linker', '.mk': 'make', '.cmake': 'cmake', '.toml': 'toml', '.yaml': 'yaml',
        '.yml': 'yaml', '.ini': 'ini', '.xml': 'xml', '.html': 'html', '.css': 'css', '.sql': 'sql', '.lua': 'lua', '.json': 'json'}
# Checked in order: silkscreen, mask and paste before copper, so "TopSilkLayer" is not copper.
GERBER_LAYERS = [(r'(?i)(\.gto|f[._]silk|top.?silk|silk.?top|topoverlay)', 'Top silkscreen'), (r'(?i)(\.gbo|b[._]silk|bot(tom)?.?silk|silk.?bot|bottomoverlay)', 'Bottom silkscreen'),
                 (r'(?i)(\.gts|f[._]mask|top.?(solder)?.?mask)', 'Top solder mask'), (r'(?i)(\.gbs|b[._]mask|bot(tom)?.?(solder)?.?mask)', 'Bottom solder mask'),
                 (r'(?i)(\.gtp|f[._]paste|top.?paste)', 'Top paste'), (r'(?i)(\.gbp|b[._]paste|bot(tom)?.?paste)', 'Bottom paste'),
                 (r'(?i)(\.gko|\.gm1|\.gml|edge[._]cuts|outline|keep.?out)', 'Board outline'),
                 (r'(?i)(\.gtl|f[._]cu|top.?(layer|copper)|(^|[^a-z])top([^a-z]|$))', 'Top copper'),
                 (r'(?i)(\.gbl|b[._]cu|bot(tom)?.?(layer|copper)|(^|[^a-z])bot(tom)?([^a-z]|$))', 'Bottom copper'),
                 (r'(?i)\.g(\d+)$|in(\d+)[._]cu|inner', 'Inner copper')]


class ViewError(ValueError):
    pass


# Sources ---------------------------------------------------------------------

class Source:
    """A readable thing: a file on disk, or bytes taken out of an archive or disk image."""

    def __init__(self, name, path=None, data=None):
        self.name = name;self.path = Path(path) if path is not None else None;self.data = data
        self.size = self.path.stat().st_size if self.path is not None else len(data)

    @classmethod
    def file(cls, path):
        path = Path(path).expanduser()
        if not path.is_file():raise ViewError('Not a readable file: ' + str(path))
        return cls(path.name, path=path)

    def stream(self):
        return open(self.path, 'rb') if self.path is not None else io.BytesIO(self.data)

    def read(self, offset=0, length=None):
        length = self.size - offset if length is None else length
        length = max(0, min(length, self.size - offset, MAX_READ))
        with self.stream() as f:
            f.seek(offset);return f.read(length)

    def all(self):
        if self.size > MAX_READ:raise ViewError('This file is larger than the %d MB viewing limit' % (MAX_READ // 1048576))
        return self.read()

    @property
    def suffix(self):
        return Path(self.name).suffix.lower()


def sha256(source):
    h = hashlib.sha256()
    with source.stream() as f:
        while chunk := f.read(1048576):h.update(chunk)
    return h.hexdigest()


# Identification --------------------------------------------------------------

def identify(source):
    """The kind of a file, from its bytes first and its name second."""
    head = source.read(0, 4096);name = source.name.lower();suffix = source.suffix
    from .view_modules import claim
    claimed = claim(source, head)  # the viewer modules' own kinds: spreadsheets, meshes, drawings, media, more pictures
    if claimed:return claimed
    if head.startswith(b'%PDF'):return 'pdf'
    if head.startswith((b'\x89PNG', b'\xff\xd8\xff', b'GIF8', b'BM')) or head[:4] == b'RIFF' and head[8:12] == b'WEBP':return 'image'
    if head.startswith(b'PK\x03\x04') or head.startswith(b'PK\x05\x06'):
        if suffix in ('.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp'):return 'document'
        return 'zip'
    if head.startswith(b'\x1f\x8b'):return 'tar' if is_tar(source) else 'gzip'
    if head.startswith(b'BZh'):return 'tar' if is_tar(source) else 'bzip2'
    if head.startswith(b'\xfd7zXZ\x00'):return 'tar' if is_tar(source) else 'xz'
    if head.startswith(b'7z\xbc\xaf\x27\x1c') or head.startswith(b'Rar!\x1a\x07'):return 'archive7z'
    if len(head) > 262 and head[257:262] == b'ustar':return 'tar'
    if head.startswith(b'\x7fELF'):return 'elf'
    if head.startswith(b'SQLite format 3\x00'):return 'sqlite'
    if head[3:11] == b'NTFS    ':return 'ntfs'
    if head[3:11] == b'EXFAT   ':return 'exfat'
    if source.size > 1082 and source.read(1080, 2) == b'\x53\xef':return 'ext'
    if source.size > 32774 and source.read(32769, 5) == b'CD001':return 'iso'
    if len(head) >= 512 and head[510:512] == b'\x55\xaa':
        if fat_bpb(head):return 'fat'
        if source.size > 1024 and source.read(512, 8) == b'EFI PART' or any(head[446 + 16 * i + 4] for i in range(4)):return 'disk'
    text = sniff_text(head)
    if head.lstrip().startswith((b'(kicad_sch', b'(kicad_pcb', b'(kicad_symbol_lib', b'(footprint', b'(module')):return 'kicad'
    if text is not None:
        upper = text[:4096].upper()
        if 'ISO-10303-21' in upper:return 'step'
        if upper.lstrip().startswith('SOLID') and 'FACET' in upper:return 'stl'
        if re.search(r'%FS[LT]?[AI]X\d\dY\d\d', upper) or re.search(r'%MO(MM|IN)\*%', upper) or suffix in ('.gbr', '.ger', '.gtl', '.gbl', '.gto', '.gbo', '.gts', '.gbs', '.gko', '.gm1') and 'D0' in upper:return 'gerber'
        if upper.lstrip().startswith('M48') or suffix in ('.drl', '.xln', '.exc') and re.search(r'T\d+C', upper):return 'excellon'
        if suffix == '.csv' or suffix == '.tsv':return 'csv'
        if suffix == '.json':return 'json'
        if suffix in ('.md', '.markdown'):return 'markdown'
        return 'code' if suffix in CODE or name in ('makefile', 'gnumakefile', 'dockerfile') else 'text'
    if suffix == '.stl' and source.size >= 84 and source.size == 84 + 50 * struct.unpack('<I', source.read(80, 4))[0]:return 'stl'
    return 'binary'


def sniff_text(head):
    """Decoded text when the bytes look like text, otherwise None."""
    if not head:return ''
    for bom, encoding in ((codecs.BOM_UTF8, 'utf-8-sig'), (codecs.BOM_UTF16_LE, 'utf-16'), (codecs.BOM_UTF16_BE, 'utf-16')):
        if head.startswith(bom):return head.decode(encoding, 'replace')
    if b'\x00' in head:return None
    try:text = head.decode('utf-8')
    except UnicodeDecodeError as exc:
        if exc.start >= len(head) - 4:text = head[:exc.start].decode('utf-8')   # a character cut at the edge
        else:text = head.decode('cp1252', 'replace')
    control = sum(1 for ch in text if ord(ch) < 32 and ch not in '\t\r\n\f\x1b')
    return text if control <= len(text) // 50 else None


def decode(raw):
    """Text and the encoding it was read in."""
    for bom, encoding in ((codecs.BOM_UTF8, 'utf-8-sig'), (codecs.BOM_UTF16_LE, 'utf-16'), (codecs.BOM_UTF16_BE, 'utf-16')):
        if raw.startswith(bom):return raw.decode(encoding, 'replace'), encoding.replace('-sig', ' with BOM')
    try:return raw.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:return raw.decode('cp1252', 'replace'), 'windows-1252'


def is_tar(source):
    try:
        with tarfile.open(fileobj=source.stream(), mode='r:*') as archive:return archive.next() is not None
    except (tarfile.TarError, OSError, EOFError, lzma.LZMAError, zlib_error()):
        return False


def zlib_error():
    import zlib
    return zlib.error


# Describing ------------------------------------------------------------------

def describe(source, with_hash=True):
    """A read-only view model of one file."""
    kind = identify(source)
    view = {'schema': 'arc.universal-view/1', 'name': source.name, 'kind': kind, 'size': source.size,
            'sha256': sha256(source) if with_hash else None, 'summary': [], 'notice': None}
    try:
        DESCRIBERS.get(kind, describe_binary)(source, view)
    except Exception as exc:  # 4.5: any damaged file (a cut-off PDF, a broken spreadsheet) falls back to its bytes, never a crash
        view['notice'] = 'Shown as raw bytes: this ' + kind + ' could not be read (' + (str(exc) or type(exc).__name__)[:200] + ')'
        describe_binary(source, view, keep_notice=True)
    view['summary'].insert(0, ('Size', human(source.size)))
    return view


def human(size):
    for unit in ('bytes', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or unit == 'TB':return ('%d %s' % (size, unit)) if unit == 'bytes' else ('%.1f %s' % (size, unit))
        size /= 1024


def hexdump(raw, offset=0):
    lines = []
    for i in range(0, len(raw), 16):
        row = raw[i:i + 16]
        lines.append('%08x  %-48s  %s' % (offset + i, ' '.join('%02x' % b for b in row), ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))
    return '\n'.join(lines)


def describe_binary(source, view, keep_notice=False):
    raw = source.read(0, MAX_HEX);view['hex'] = hexdump(raw)
    if not keep_notice and view['kind'] == 'binary':view['notice'] = 'The file type was not identified. Showing the first %s as hex.' % human(len(raw))
    if len(raw) < source.size:view['hex_truncated'] = True


def describe_text(source, view):
    raw = source.read(0, MAX_TEXT * 2)
    text, encoding = decode(raw)
    view['text'] = text[:MAX_TEXT];view['language'] = CODE.get(source.suffix, 'markdown' if view['kind'] == 'markdown' else 'text')
    lines = text.count('\n') + (1 if text and not text.endswith('\n') else 0)
    view['summary'] += [('Encoding', encoding), ('Lines', str(lines)), ('Line endings', 'Windows (CRLF)' if '\r\n' in text else 'Unix (LF)')]
    if len(raw) < source.size or len(text) > MAX_TEXT:view['notice'] = 'Showing the first %s.' % human(len(raw))


def describe_json(source, view):
    describe_text(source, view)
    try:
        value = json.loads(view['text']);view['text'] = json.dumps(value, indent=2, ensure_ascii=False)[:MAX_TEXT]
        view['summary'].append(('JSON', type(value).__name__ + (' with %d items' % len(value) if isinstance(value, (list, dict)) else '')))
    except ValueError as exc:
        view['notice'] = 'Not valid JSON (' + str(exc)[:120] + '); shown as text.'


def describe_csv(source, view):
    import csv
    describe_text(source, view)
    sample = view['text'][:65536]
    try:dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
    except csv.Error:dialect = csv.excel_tab if source.suffix == '.tsv' else csv.excel
    rows = []
    for row in csv.reader(io.StringIO(view['text']), dialect):
        rows.append(row)
        if len(rows) > MAX_TABLE_ROWS:break
    if rows:
        width = max(len(r) for r in rows)
        view['table'] = {'columns': rows[0] + [''] * (width - len(rows[0])), 'rows': [r + [''] * (width - len(r)) for r in rows[1:MAX_TABLE_ROWS + 1]]}
        view['summary'] += [('Columns', str(width)), ('Rows shown', str(len(view['table']['rows'])))]


def describe_pdf(source, view):
    view['pdf'] = True
    try:
        import pypdf
        with source.stream() as stream:
            reader = pypdf.PdfReader(stream)
            view['summary'].append(('Pages', str(len(reader.pages))))
            meta = reader.metadata or {}
            for key, label in (('/Title', 'Title'), ('/Author', 'Author'), ('/Producer', 'Producer')):
                if meta.get(key):view['summary'].append((label, str(meta[key])[:120]))
            text = []
            for page in reader.pages[:20]:
                text.append(page.extract_text() or '')
                if sum(map(len, text)) > MAX_TEXT:break
        view['text'] = '\n\n'.join(text)[:MAX_TEXT];view['language'] = 'text'
    except ImportError:
        view['notice'] = 'Page text needs pypdf; pages are still shown.'


def describe_image(source, view):
    view['image'] = True
    head = source.read(0, 64)
    if head.startswith(b'\x89PNG') and len(head) >= 24:
        width, height = struct.unpack('>II', head[16:24]);view['summary'].append(('Pixels', '%d × %d' % (width, height)))


def xml_text(raw):
    text = re.sub(r'</w:p>|</text:p>|</a:p>|<w:tab/>|</row>', '\n', raw.decode('utf-8', 'replace'))
    text = re.sub(r'<[^>]+>', '', text)
    import html
    return html.unescape(re.sub(r'\n{3,}', '\n\n', text))


def describe_document(source, view):
    with zipfile.ZipFile(io.BytesIO(source.all())) as archive:
        names = archive.namelist();parts = []
        if 'word/document.xml' in names:parts = ['word/document.xml'];view['summary'].append(('Format', 'Word document'))
        elif 'xl/sharedStrings.xml' in names or any(n.startswith('xl/worksheets/') for n in names):
            parts = ['xl/sharedStrings.xml'] if 'xl/sharedStrings.xml' in names else []
            view['summary'].append(('Format', 'Excel workbook · ' + str(sum(1 for n in names if n.startswith('xl/worksheets/sheet'))) + ' sheets'))
        elif any(n.startswith('ppt/slides/slide') for n in names):
            parts = sorted(n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n));view['summary'].append(('Format', 'PowerPoint · %d slides' % len(parts)))
        elif 'content.xml' in names:parts = ['content.xml'];view['summary'].append(('Format', 'OpenDocument'))
        text = '\n'.join(xml_text(archive.read(n)[:MAX_READ]) for n in parts if n in names)
    view['text'] = text.strip()[:MAX_TEXT];view['language'] = 'text'
    view['notice'] = 'Text only. Open it in Office to see layout, tables and formatting.'


# Archives --------------------------------------------------------------------

def entry(path, size, directory=False, note=None):
    value = {'path': path.strip('/'), 'size': size, 'directory': directory}
    if note:value['note'] = note
    return value


def tree_view(view, entries, label):
    files = [e for e in entries if not e['directory']]
    view['tree'] = entries[:MAX_ENTRIES]
    view['summary'] += [(label, '%d files, %d folders' % (len(files), len(entries) - len(files))), ('Unpacked size', human(sum(e['size'] for e in files)))]
    if len(entries) > MAX_ENTRIES:view['notice'] = 'Listing the first %d entries.' % MAX_ENTRIES


def describe_zip(source, view):
    with zipfile.ZipFile(source.stream()) as archive:
        entries = [entry(i.filename, i.file_size, i.is_dir(), 'encrypted' if i.flag_bits & 1 else None) for i in archive.infolist()]
    tree_view(view, entries, 'ZIP')


def describe_tar(source, view):
    with tarfile.open(fileobj=source.stream(), mode='r:*') as archive:
        entries = []
        for i in archive:
            entries.append(entry(i.name, i.size, i.isdir(), None if i.isreg() or i.isdir() else 'link or device, not opened'))
            if len(entries) > MAX_ENTRIES:break
    tree_view(view, entries, 'TAR')


def describe_compressed(source, view):
    inner = Path(source.name).stem or 'content';view['tree'] = [entry(inner, -1)]
    view['summary'].append(('Compressed', view['kind'] + ' · one file: ' + inner))


# Disk images: FAT, MBR and GPT ---------------------------------------------------

def fat_bpb(sector):
    """FAT boot-sector values, or None when the sector is not a FAT volume."""
    bps, spc, reserved, nfats, root_entries, total16, media, fatsz16 = struct.unpack('<HBHBHHBH', sector[11:24])
    total32, fatsz32 = struct.unpack('<II', sector[32:40])
    if bps not in (512, 1024, 2048, 4096) or spc == 0 or spc & (spc - 1) or nfats not in (1, 2) or reserved == 0:return None
    fatsz = fatsz16 or fatsz32;total = total16 or total32
    if not fatsz or not total:return None
    root_sectors = (root_entries * 32 + bps - 1) // bps
    first_data = reserved + nfats * fatsz + root_sectors
    if first_data >= total:return None
    clusters = (total - first_data) // spc
    kind = 'FAT12' if clusters < 4085 else 'FAT16' if clusters < 65525 else 'FAT32'
    return {'bps': bps, 'spc': spc, 'reserved': reserved, 'nfats': nfats, 'root_entries': root_entries, 'fatsz': fatsz, 'total': total,
            'first_data': first_data, 'clusters': clusters, 'type': kind, 'root_cluster': struct.unpack('<I', sector[44:48])[0] if kind == 'FAT32' else 0,
            'label': (sector[71:82] if kind == 'FAT32' else sector[43:54]).decode('ascii', 'replace').strip()}


class Fat:
    """A read-only FAT12/16/32 volume at ``offset`` bytes into a source."""

    def __init__(self, source, offset=0):
        self.source = source;self.offset = offset
        self.bpb = fat_bpb(source.read(offset, 512))
        if not self.bpb:raise ViewError('Not a FAT volume')
        b = self.bpb;self.cluster_bytes = b['bps'] * b['spc'];self.kind = b['type']
        self.fat = source.read(offset + b['reserved'] * b['bps'], min(b['fatsz'] * b['bps'], MAX_READ))
        self.eoc = {'FAT12': 0xFF8, 'FAT16': 0xFFF8, 'FAT32': 0x0FFFFFF8}[self.kind]

    def next(self, cluster):
        if self.kind == 'FAT12':
            at = cluster + cluster // 2;value = struct.unpack('<H', self.fat[at:at + 2])[0]
            return value >> 4 if cluster & 1 else value & 0xFFF
        if self.kind == 'FAT16':return struct.unpack('<H', self.fat[cluster * 2:cluster * 2 + 2])[0]
        return struct.unpack('<I', self.fat[cluster * 4:cluster * 4 + 4])[0] & 0x0FFFFFFF

    def chain(self, cluster, limit):
        seen = set()
        while 2 <= cluster < self.eoc and cluster not in seen and len(seen) * self.cluster_bytes < limit:
            seen.add(cluster);yield cluster
            if (cluster + 1) * (4 if self.kind == 'FAT32' else 2) > len(self.fat):break
            cluster = self.next(cluster)

    def cluster_data(self, cluster):
        b = self.bpb
        return self.source.read(self.offset + (b['first_data'] + (cluster - 2) * b['spc']) * b['bps'], self.cluster_bytes)

    def read_chain(self, cluster, size):
        out = bytearray()
        for c in self.chain(cluster, max(size, self.cluster_bytes)):
            out += self.cluster_data(c)
            if len(out) >= size:break
        return bytes(out[:size])

    def root(self):
        b = self.bpb
        if self.kind == 'FAT32':return self.read_chain(b['root_cluster'], MAX_READ // 16)
        start = self.offset + (b['reserved'] + b['nfats'] * b['fatsz']) * b['bps']
        return self.source.read(start, b['root_entries'] * 32)

    @staticmethod
    def entries(raw):
        """(name, attributes, first cluster, size) for each live entry of a directory."""
        long_parts = []
        for i in range(0, len(raw) - 31, 32):
            e = raw[i:i + 32]
            if e[0] == 0:break
            if e[0] == 0xE5:long_parts = [];continue
            attr = e[11]
            if attr == 0x0F:
                long_parts.insert(0, (e[1:11] + e[14:26] + e[28:32]).decode('utf-16-le', 'replace'));continue
            if attr & 0x08:long_parts = [];continue
            base, ext = e[0:8].decode('cp437').rstrip(), e[8:11].decode('cp437').rstrip()
            if e[12] & 0x08:base = base.lower()
            if e[12] & 0x10:ext = ext.lower()
            short = base + ('.' + ext if ext else '')
            name = ''.join(long_parts).split('\x00')[0].rstrip('￿') if long_parts else short
            long_parts = []
            if name in ('.', '..'):continue
            cluster = (struct.unpack('<H', e[20:22])[0] << 16) | struct.unpack('<H', e[26:28])[0]
            yield name, attr, cluster, struct.unpack('<I', e[28:32])[0]

    def walk(self):
        out = [];stack = [('', self.root(), 0)];seen = set()
        while stack and len(out) < MAX_ENTRIES:
            prefix, raw, depth = stack.pop()
            for name, attr, cluster, size in self.entries(raw):
                path = prefix + name
                if attr & 0x10:
                    out.append(entry(path, 0, True))
                    if depth < 32 and cluster not in seen and cluster >= 2:
                        seen.add(cluster);stack.append((path + '/', self.read_chain(cluster, MAX_READ // 16), depth + 1))
                else:out.append(entry(path, size))
        return sorted(out, key=lambda e: e['path'].casefold())

    def find(self, path):
        raw = self.root();parts = [p for p in path.split('/') if p]
        for index, part in enumerate(parts):
            match = next(((n, a, c, s) for n, a, c, s in self.entries(raw) if n.casefold() == part.casefold()), None)
            if match is None:raise ViewError('Not found in the image: ' + path)
            name, attr, cluster, size = match
            if index == len(parts) - 1:
                if attr & 0x10:raise ViewError('That is a folder: ' + path)
                if size > MAX_READ:raise ViewError('This file is larger than the viewing limit')
                return self.read_chain(cluster, size)
            raw = self.read_chain(cluster, MAX_READ // 16)
        raise ViewError('Not found in the image: ' + path)


def describe_fat(source, view):
    fat = Fat(source)
    view['summary'] += [('File system', fat.kind), ('Volume label', fat.bpb['label'] or '(none)'), ('Cluster size', human(fat.cluster_bytes))]
    tree_view(view, fat.walk(), 'Contents')


GPT_TYPES = {'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7': 'Basic data (FAT / NTFS / exFAT)', '0fc63daf-8483-4772-8e79-3d69d8477de4': 'Linux file system',
             'c12a7328-f81f-11d2-ba4b-00a0c93ec93b': 'EFI system', 'e3c9e316-0b5c-4db8-817d-f92df00215ae': 'Microsoft reserved',
             '0657fd6d-a4ab-43c4-84e5-0933c84b4f4f': 'Linux swap', 'de94bba4-06d1-4d40-a16a-bfd50179d6ac': 'Windows recovery'}


def guid(raw):
    a, b, c = struct.unpack('<IHH', raw[:8])
    return '%08x-%04x-%04x-%s-%s' % (a, b, c, raw[8:10].hex(), raw[10:16].hex())


def partitions(source):
    """Partitions of a whole-disk image: (number, start byte, size bytes, type label)."""
    mbr = source.read(0, 512);found = []
    if source.read(512, 8) == b'EFI PART':
        header = source.read(512, 92);table, count, size = struct.unpack('<QII', header[72:88])
        raw = source.read(table * 512, min(count * size, 1048576))
        for i in range(0, len(raw), size):
            kind = guid(raw[i:i + 16])
            if kind == '00000000-0000-0000-0000-000000000000':continue
            first, last = struct.unpack('<QQ', raw[i + 32:i + 48])
            name = raw[i + 56:i + 128].decode('utf-16-le', 'replace').split('\x00')[0]
            found.append((len(found) + 1, first * 512, (last - first + 1) * 512, GPT_TYPES.get(kind, 'GPT ' + kind) + (' · ' + name if name else '')))
        return 'GPT', found
    for i in range(4):
        e = mbr[446 + 16 * i:462 + 16 * i];kind = e[4]
        start, count = struct.unpack('<II', e[8:16])
        if kind and count:found.append((i + 1, start * 512, count * 512, MBR_TYPES.get(kind, 'type 0x%02x' % kind)))
    return 'MBR', found


MBR_TYPES = {0x01: 'FAT12', 0x04: 'FAT16', 0x06: 'FAT16', 0x0b: 'FAT32', 0x0c: 'FAT32 (LBA)', 0x0e: 'FAT16 (LBA)', 0x07: 'NTFS / exFAT',
             0x83: 'Linux', 0x82: 'Linux swap', 0x05: 'Extended', 0x0f: 'Extended', 0xee: 'GPT protective', 0xef: 'EFI system'}


def probe_volume(source, offset):
    sector = source.read(offset, 512)
    if fat_bpb(sector):return fat_bpb(sector)['type']
    if sector[3:11] == b'NTFS    ':return 'NTFS'
    if sector[3:11] == b'EXFAT   ':return 'exFAT'
    if source.read(offset + 1080, 2) == b'\x53\xef':return 'ext2/3/4'
    return None


def describe_disk(source, view):
    scheme, parts = partitions(source);entries = []
    view['summary'].append(('Partition table', scheme + ' · %d partitions' % len(parts)))
    for number, start, size, label in parts:
        volume = probe_volume(source, start)
        folder = 'Partition %d' % number
        entries.append(entry(folder, size, True, (volume or label) + ' · ' + human(size)))
        if volume and volume.startswith('FAT'):
            for e in Fat(source, start).walk():entries.append({**e, 'path': folder + '/' + e['path']})
        elif volume:
            entries.append(entry(folder + '/(open this partition with 7-Zip)', 0, False, volume + ' contents are listed when the partition is opened'))
    view['tree'] = entries
    view['summary'].append(('Contents', '%d entries' % len(entries)))


def partition_source(source, number):
    scheme, parts = partitions(source)
    for n, start, size, label in parts:
        if n == number:
            if size > MAX_READ * 64:raise ViewError('This partition is too large to open here; open the disk with 7-Zip instead')
            return Source(source.name + ' · partition %d' % n, data=source.read(start, size)) if size <= MAX_READ else OffsetSource(source, start, size, n)
    raise ViewError('No partition %d' % number)


class OffsetSource(Source):
    """A window into a larger source, without copying it."""

    def __init__(self, parent, start, size, number):
        self.parent = parent;self.start = start;self.name = parent.name + ' · partition %d' % number;self.path = None;self.data = None;self.size = size

    def stream(self):
        raise ViewError('Large partitions are read by position only')

    def read(self, offset=0, length=None):
        length = self.size - offset if length is None else length
        return self.parent.read(self.start + offset, max(0, min(length, self.size - offset, MAX_READ)))


# NTFS, ext, ISO, 7z and RAR: read through 7-Zip, never mounted ---------------------

def seven_zip():
    return shutil.which('7z') or shutil.which('7zz') or shutil.which('7za')


def seven_list(source):
    tool = seven_zip()
    if not tool:raise ViewError('Install 7-Zip to browse this (Debian: sudo apt install 7zip)')
    path = materialize(source)
    try:
        r = subprocess.run([tool, 'l', '-slt', '-ba', '-spd', '--', str(path)], capture_output=True, text=True, timeout=120, errors='replace')
    finally:release(source, path)
    if r.returncode not in (0, 1):raise ViewError('7-Zip could not read it: ' + (r.stderr or r.stdout).strip()[-200:])
    entries = [];current = {}
    for line in r.stdout.splitlines() + ['']:
        if not line.strip():
            if 'Path' in current:
                entries.append(entry(current['Path'].replace('\\', '/'), int(current.get('Size') or 0), current.get('Folder') == '+' or 'D' in current.get('Attributes', '')[:1]))
            current = {};continue
        key, _, value = line.partition(' = ');current[key.strip()] = value
    # File-system metadata (NTFS $MFT, the ext journal) is not the owner's content.
    return [e for e in entries if not e['path'].startswith(('[SYS]', '[SYSTEM]', '$'))]


def seven_member(source, member):
    tool = seven_zip()
    if not tool:raise ViewError('Install 7-Zip to open this (Debian: sudo apt install 7zip)')
    path = materialize(source)
    try:
        process = subprocess.Popen([tool, 'e', '-so', '-spd', '-y', '--', str(path), member], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        data = process.stdout.read(MAX_READ + 1);process.stdout.close()
        try:process.wait(timeout=120)
        except subprocess.TimeoutExpired:process.kill();raise ViewError('7-Zip took too long')
    finally:release(source, path)
    if len(data) > MAX_READ:raise ViewError('This file is larger than the viewing limit')
    return data


def materialize(source):
    """A path 7-Zip can open. Bytes from inside another container go to a private temporary file."""
    if source.path is not None:return source.path
    import tempfile
    fd, name = tempfile.mkstemp(prefix='ledger-view-');os.chmod(name, 0o600)
    with os.fdopen(fd, 'wb') as f:f.write(source.read())
    return Path(name)


def release(source, path):
    if source.path is None:Path(path).unlink(missing_ok=True)


def describe_seven(source, view):
    labels = {'ntfs': 'NTFS', 'ext': 'ext2/3/4', 'iso': 'ISO 9660', 'archive7z': '7z / RAR', 'exfat': 'exFAT'}
    view['summary'].append(('Format', labels.get(view['kind'], view['kind'])))
    if view['kind'] == 'ext':
        sb = source.read(1024, 1024);count, free = struct.unpack('<II', sb[4:12]);block = 1024 << struct.unpack('<I', sb[24:28])[0]
        label = sb[120:136].split(b'\x00')[0].decode('utf-8', 'replace')
        view['summary'] += [('Volume label', label or '(none)'), ('Block size', human(block)), ('Journal', 'yes (ext3/ext4)' if struct.unpack('<I', sb[92:96])[0] & 4 else 'no (ext2)')]
    if view['kind'] == 'ntfs':
        bps, spc = struct.unpack('<HB', source.read(11, 3));view['summary'].append(('Cluster size', human(bps * spc)))
    try:
        tree_view(view, seven_list(source), 'Contents')
    except ViewError as exc:
        view['notice'] = str(exc);describe_binary(source, view, keep_notice=True)


# ELF --------------------------------------------------------------------------

ELF_MACHINES = {3: 'x86', 8: 'MIPS', 20: 'PowerPC', 40: 'ARM', 62: 'x86-64', 183: 'AArch64', 243: 'RISC-V', 258: 'LoongArch'}
ELF_TYPES = {1: 'relocatable object', 2: 'executable', 3: 'shared object or PIE', 4: 'core dump'}


def describe_elf(source, view):
    raw = source.read(0, MAX_READ);bits = {1: 32, 2: 64}.get(raw[4]);end = {1: '<', 2: '>'}.get(raw[5])
    if not bits or not end:raise ViewError('Unknown ELF class')
    if bits == 64:
        e_type, machine, _, entry_point, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack(end + 'HHIQQQIHHHHHH', raw[16:64])
    else:
        e_type, machine, _, entry_point, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack(end + 'HHIIIIIHHHHHH', raw[16:52])
    view['summary'] += [('ELF', '%d-bit, %s-endian' % (bits, 'little' if end == '<' else 'big')), ('Type', ELF_TYPES.get(e_type, str(e_type))),
                        ('Machine', ELF_MACHINES.get(machine, str(machine))), ('Entry point', '0x%x' % entry_point)]
    sections = []
    for i in range(min(shnum, 512)):
        at = shoff + i * shentsize
        if at + shentsize > len(raw):break
        if bits == 64:name, kind, flags, addr, off, size = struct.unpack(end + 'IIQQQQ', raw[at:at + 40])
        else:name, kind, flags, addr, off, size = struct.unpack(end + 'IIIIII', raw[at:at + 24])
        sections.append([name, kind, flags, addr, off, size])
    names = sections[shstrndx] if shstrndx < len(sections) else None
    def string(table, index):
        if not table:return ''
        start = table[4] + index;stop = raw.find(b'\x00', start)
        return raw[start:stop].decode('utf-8', 'replace') if 0 <= start < len(raw) else ''
    rows = []
    for name, kind, flags, addr, off, size in sections:
        rows.append([string(names, name), {1: 'PROGBITS', 2: 'SYMTAB', 3: 'STRTAB', 4: 'RELA', 8: 'NOBITS', 11: 'DYNSYM'}.get(kind, str(kind)), '0x%x' % addr, human(size)])
    view['table'] = {'columns': ['Section', 'Kind', 'Address', 'Size'], 'rows': rows}
    for name, kind, flags, addr, off, size in sections:
        if kind in (2, 11):view['summary'].append(('Symbols' if kind == 2 else 'Dynamic symbols', str(size // (24 if bits == 64 else 16))))
    view['summary'].append(('Sections', str(len(sections))));view['summary'].append(('Program headers', str(phnum)))
    view['notice'] = 'Read-only inspection. Nothing is run.'


# SQLite -----------------------------------------------------------------------

def describe_sqlite(source, view):
    path = materialize(source)
    try:
        db = sqlite3.connect('file:' + str(path) + '?mode=ro&immutable=1', uri=True)
        try:
            tables = db.execute("SELECT name,type,sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name").fetchall()
            rows = []
            for name, kind, sql in tables[:500]:
                try:count = db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                except sqlite3.Error:count = '?'
                rows.append([name, kind, str(count)])
            view['table'] = {'columns': ['Table', 'Kind', 'Rows'], 'rows': rows}
            view['text'] = '\n\n'.join(sql or '' for _, _, sql in tables)[:MAX_TEXT];view['language'] = 'sql'
            view['summary'].append(('SQLite', '%d tables and views' % len(tables)))
        finally:db.close()
    finally:release(source, path)
    view['notice'] = 'Opened read-only and immutable; the database is never changed.'


# Gerber and Excellon ------------------------------------------------------------

def gerber_layer(name):
    for pattern, label in GERBER_LAYERS:
        if re.search(pattern, name):return label
    return 'Layer'


def parse_gerber(text):
    """Primitives of an RS-274X file in millimetres: lines, arcs as lines, flashes and regions."""
    unit = 1.0;integer, decimal = 2, 4;zeros = 'L';apertures = {};current = None;x = y = 0.0;mode = 1;region = None;polarity = 'D'
    lines, flashes, regions, problems = [], [], [], []
    def coordinate(value):
        if value is None:return None
        if '.' in value:return float(value) * unit
        sign = -1 if value.startswith('-') else 1;digits = value.lstrip('+-')
        if zeros == 'T':digits = digits.ljust(integer + decimal, '0')
        return sign * int(digits or '0') / (10 ** decimal) * unit
    for block in re.split(r'\*', re.sub(r'\s+', '', text)):
        if not block:continue
        block = block.strip('%')
        if block.startswith('FS'):
            m = re.match(r'FS([LT]?)([AI]?)X(\d)(\d)Y(\d)(\d)', block)
            if m:zeros = m.group(1) or 'L';integer, decimal = int(m.group(3)), int(m.group(4))
            continue
        if block.startswith('MO'):unit = 25.4 if 'IN' in block else 1.0;continue
        if block.startswith('LP'):polarity = block[2:3] or 'D';continue
        if block.startswith('AD'):
            m = re.match(r'ADD(\d+)([A-Za-z_][A-Za-z0-9_.]*),?([0-9.X\-]*)', block)
            if m:
                params = [float(v) * unit for v in m.group(3).split('X') if v not in ('', '-')]
                apertures[int(m.group(1))] = (m.group(2), params)
                if m.group(2) not in ('C', 'R', 'O', 'P') and m.group(2) not in problems:problems.append(m.group(2))
            continue
        if block.startswith(('AM', 'TF', 'TA', 'TO', 'TD', 'IN', 'IP', 'LN', 'SR', 'G04', 'M02', 'M00', 'G90', 'G91', 'G70', 'G71', 'G74', 'G75')) or block.startswith('0') and region is None and not block[1:2].isdigit():
            if block.startswith('G70'):unit = 25.4
            if block.startswith('G71'):unit = 1.0
            continue
        if block.startswith('G36'):region = [[]];continue
        if block.startswith('G37'):
            if region:regions.extend([(r, polarity) for r in region if len(r) > 2])
            region = None;continue
        m = re.match(r'(?:G0?([123]))?(?:G54)?(?:D(\d+))?$', block)
        if m and (m.group(1) or m.group(2)) and not re.search(r'[XYIJ]', block):
            if m.group(1):mode = int(m.group(1))
            if m.group(2) and int(m.group(2)) >= 10:current = int(m.group(2))
            continue
        m = re.match(r'(?:G0?([123]))?(?:X([+-]?[\d.]+))?(?:Y([+-]?[\d.]+))?(?:I([+-]?[\d.]+))?(?:J([+-]?[\d.]+))?(?:D0?([123]))?$', block)
        if not m:continue
        if m.group(1):mode = int(m.group(1))
        nx = coordinate(m.group(2));ny = coordinate(m.group(3));nx = x if nx is None else nx;ny = y if ny is None else ny
        i = coordinate(m.group(4)) or 0.0;j = coordinate(m.group(5)) or 0.0;op = int(m.group(6)) if m.group(6) else 1
        if op == 1:
            points = [(x, y), (nx, ny)] if mode == 1 else arc_points(x, y, nx, ny, i, j, mode == 2)
            if region is not None:
                if not region[-1]:region[-1].append((x, y))
                region[-1].extend(points[1:])
            else:
                width = (apertures.get(current, ('C', [0.1]))[1] or [0.1])[0]
                for a, b in zip(points, points[1:]):lines.append((a[0], a[1], b[0], b[1], width, polarity))
        elif op == 2:
            if region is not None and region[-1]:region.append([])
        elif op == 3:flashes.append((nx, ny, apertures.get(current, ('C', [0.1])), polarity))
        x, y = nx, ny
    return {'lines': lines, 'flashes': flashes, 'regions': regions, 'apertures': len(apertures), 'unsupported_apertures': problems}


def arc_points(x, y, nx, ny, i, j, clockwise):
    cx, cy = x + i, y + j;r = math.hypot(x - cx, y - cy) or 1e-9
    a0 = math.atan2(y - cy, x - cx);a1 = math.atan2(ny - cy, nx - cx)
    if clockwise:
        while a1 >= a0:a1 -= 2 * math.pi
    else:
        while a1 <= a0:a1 += 2 * math.pi
    if abs(a1 - a0) < 1e-9 or (abs(nx - x) < 1e-9 and abs(ny - y) < 1e-9):a1 = a0 + (-2 * math.pi if clockwise else 2 * math.pi)
    steps = max(4, int(abs(a1 - a0) / (math.pi / 32)))
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / steps), cy + r * math.sin(a0 + (a1 - a0) * k / steps)) for k in range(steps + 1)]


def parse_excellon(text):
    unit = 1.0;tools = {};current = None;holes = [];body = False;x = y = 0.0;implied = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):continue
        if line.startswith(('METRIC', 'M71')):unit = 1.0
        if line.startswith(('INCH', 'M72')):unit = 25.4
        if line in ('%', 'M95'):body = True;continue
        m = re.match(r'T(\d+)(?:F[\d.]+)?(?:S[\d.]+)?C([\d.]+)', line)
        if m:tools[int(m.group(1))] = float(m.group(2)) * unit;continue
        m = re.match(r'T(\d+)$', line)
        if m:current = int(m.group(1));continue
        m = re.match(r'(?:X([+-]?[\d.]+))?(?:Y([+-]?[\d.]+))?$', line)
        if body and m and (m.group(1) or m.group(2)):
            def value(v, old):
                nonlocal implied
                if v is None:return old
                if '.' in v:return float(v) * unit
                implied = True;return int(v) / (1000.0 if unit == 1.0 else 10000.0) * unit
            x, y = value(m.group(1), x), value(m.group(2), y)
            holes.append((x, y, tools.get(current, 0.8)))
    return {'holes': holes, 'tools': tools, 'implied_decimals': implied}


def bounds(points):
    xs = [p[0] for p in points];ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def describe_gerber(source, view):
    text, _ = decode(source.all());value = parse_gerber(text)
    points = [(l[0], l[1]) for l in value['lines']] + [(l[2], l[3]) for l in value['lines']] + [(f[0], f[1]) for f in value['flashes']] + [p for r, _ in value['regions'] for p in r]
    box = bounds(points);view['gerber'] = {'layers': [{'name': source.name, 'role': gerber_layer(source.name), **value}], 'bounds': box}
    view['summary'] += [('Layer', gerber_layer(source.name)), ('Size', '%.2f × %.2f mm' % (box[2] - box[0], box[3] - box[1])),
                        ('Contents', '%d strokes, %d pads, %d regions, %d apertures' % (len(value['lines']), len(value['flashes']), len(value['regions']), value['apertures']))]
    if value['unsupported_apertures']:view['notice'] = 'Aperture macros (%s) are drawn as circles; check them in a CAM viewer.' % ', '.join(value['unsupported_apertures'][:5])
    view['text'] = text[:MAX_TEXT];view['language'] = 'text'


def describe_excellon(source, view):
    text, _ = decode(source.all());value = parse_excellon(text)
    box = bounds([(h[0], h[1]) for h in value['holes']])
    view['gerber'] = {'layers': [{'name': source.name, 'role': 'Drill', 'lines': [], 'flashes': [], 'regions': [], 'holes': value['holes']}], 'bounds': box}
    view['summary'] += [('Layer', 'Drill'), ('Holes', str(len(value['holes']))), ('Tools', ', '.join('T%d %.2f mm' % (k, v) for k, v in sorted(value['tools'].items())) or 'none')]
    if value['implied_decimals']:view['notice'] = 'Coordinates without decimal points were read as 3.3 (mm) or 2.4 (inch).'
    view['text'] = text[:MAX_TEXT];view['language'] = 'text'


def board(sources):
    """Several Gerber and drill sources drawn together, top copper last."""
    order = ['Board outline', 'Bottom copper', 'Inner copper', 'Bottom solder mask', 'Bottom silkscreen', 'Layer', 'Top solder mask', 'Top copper', 'Top paste', 'Bottom paste', 'Top silkscreen', 'Drill']
    layers = []
    for source in sources:
        view = {'summary': [], 'kind': identify(source)}
        if view['kind'] == 'gerber':describe_gerber(source, view)
        elif view['kind'] == 'excellon':describe_excellon(source, view)
        else:continue
        layers += view['gerber']['layers']
    layers.sort(key=lambda l: order.index(l['role']) if l['role'] in order else 5)
    points = []
    for l in layers:
        points += [(a[0], a[1]) for a in l['lines']] + [(f[0], f[1]) for f in l['flashes']] + [(h[0], h[1]) for h in l.get('holes', [])]
    return {'layers': layers, 'bounds': bounds(points)}


# STEP, STL, KiCad ----------------------------------------------------------------

def describe_step(source, view):
    describe_text(source, view)
    header = view['text'][:20000]
    for key, label in (('FILE_NAME', 'File name'), ('FILE_SCHEMA', 'Schema'), ('FILE_DESCRIPTION', 'Description')):
        m = re.search(key + r"\s*\(\s*\(?'([^']*)'", header)
        if m:view['summary'].append((label, m.group(1)[:120]))
    view['summary'].append(('Solids', str(view['text'].count('MANIFOLD_SOLID_BREP'))))
    view['notice'] = 'STEP geometry is shown in the 3D assembly view when the file is in the workspace; here it is read as text.'


def describe_stl(source, view):
    head = source.read(0, 84)
    if head[:5].lower() == b'solid' and b'facet' in source.read(0, 4096).lower():
        text, _ = decode(source.read(0, MAX_READ));count = text.lower().count('facet normal');view['summary'].append(('STL', 'text · %d triangles' % count))
    else:view['summary'].append(('STL', 'binary · %d triangles' % struct.unpack('<I', head[80:84])[0]))
    view['stl'] = True


def describe_kicad(source, view):
    describe_text(source, view);first = view['text'].lstrip()[:40]
    view['summary'].append(('KiCad', first.split()[0].lstrip('(') if first else 'file'));view['kicad'] = True


DESCRIBERS = {'text': describe_text, 'code': describe_text, 'markdown': describe_text, 'json': describe_json, 'csv': describe_csv,
              'pdf': describe_pdf, 'image': describe_image, 'document': describe_document, 'zip': describe_zip, 'tar': describe_tar,
              'gzip': describe_compressed, 'bzip2': describe_compressed, 'xz': describe_compressed, 'fat': describe_fat, 'disk': describe_disk,
              'ntfs': describe_seven, 'ext': describe_seven, 'iso': describe_seven, 'archive7z': describe_seven, 'exfat': describe_seven,
              'elf': describe_elf, 'sqlite': describe_sqlite, 'gerber': describe_gerber, 'excellon': describe_excellon,
              'step': describe_step, 'stl': describe_stl, 'kicad': describe_kicad, 'binary': describe_binary}
from .view_modules import describers as _module_describers  # noqa: E402
DESCRIBERS.update(_module_describers())
CONTAINERS = {'zip', 'tar', 'gzip', 'bzip2', 'xz', 'fat', 'disk', 'ntfs', 'ext', 'iso', 'archive7z', 'exfat'}


def member(source, path):
    """One member of an archive or disk image, as a new Source."""
    kind = identify(source);name = Path(path).name or path
    if kind == 'zip':
        with zipfile.ZipFile(source.stream()) as archive:
            info = archive.getinfo(path)
            if info.flag_bits & 1:raise ViewError('This member is encrypted')
            if info.file_size > MAX_READ:raise ViewError('This member is larger than the viewing limit')
            return Source(name, data=archive.read(info))
    if kind == 'tar':
        with tarfile.open(fileobj=source.stream(), mode='r:*') as archive:
            info = archive.getmember(path)
            if not info.isreg():raise ViewError('Links and devices are not opened')
            if info.size > MAX_READ:raise ViewError('This member is larger than the viewing limit')
            return Source(name, data=archive.extractfile(info).read())
    if kind in ('gzip', 'bzip2', 'xz'):
        opener = {'gzip': gzip.GzipFile, 'bzip2': bz2.BZ2File, 'xz': lzma.LZMAFile}[kind]
        with opener(source.stream()) as f:data = f.read(MAX_READ + 1)
        if len(data) > MAX_READ:raise ViewError('The unpacked file is larger than the viewing limit')
        return Source(name, data=data)
    if kind == 'fat':return Source(name, data=Fat(source).find(path))
    if kind == 'disk':
        first, _, rest = path.partition('/')
        m = re.match(r'Partition (\d+)$', first)
        if not m:raise ViewError('Choose a file inside a partition')
        part = partition_source(source, int(m.group(1)))
        if not rest or rest.startswith('(open'):return part
        return member(part, rest)
    if kind in ('ntfs', 'ext', 'iso', 'archive7z', 'exfat'):return Source(name, data=seven_member(source, path))
    raise ViewError('This file has no members')


# Kernel: Slate, the CLI and MCP read files through the same viewer ----------------

FIELDS = {'viewer.describe': ({'path': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
                               'member': {'type': 'string', 'minLength': 1, 'maxLength': 4096}}, ['path'])}
SCOPES = {'viewer.describe': 'read'}
SLATE_TEXT = 8000
SLATE_ENTRIES = 300


def allowed(kernel, path):
    """Files Slate may view: inside the workspace (including what the Office received), never Ledger's own state or the program."""
    from . import locations
    path = Path(path).expanduser()
    if not path.is_absolute():path = kernel.root / path
    path = path.resolve();root = kernel.root.resolve()
    receiving = (kernel.state / 'receiving').resolve()
    if path.is_relative_to(receiving):return path
    if not path.is_relative_to(root) or path.is_relative_to(kernel.state.resolve()):
        raise ValueError('VIEWER_OUTSIDE_WORKSPACE: open files from elsewhere on the desktop with File → Open in Universal Viewer')
    if locations.contains_program(root) and any(part.startswith('.') for part in path.relative_to(root).parts):
        raise ValueError('VIEWER_PRIVATE_FILE')
    return path


def dispatch(kernel, op, args, principal):
    source = Source.file(allowed(kernel, args['path']))
    if args.get('member'):source = member(source, args['member'])
    view = describe(source)
    compact = {k: v for k, v in view.items() if k not in ('text', 'tree', 'table', 'gerber', 'hex')}
    compact['summary'] = [list(row) for row in view['summary']]
    if view.get('text') is not None:compact['text'] = view['text'][:SLATE_TEXT];compact['text_truncated'] = len(view['text']) > SLATE_TEXT
    if view.get('tree') is not None:compact['entries'] = view['tree'][:SLATE_ENTRIES];compact['entries_total'] = len(view['tree'])
    if view.get('table'):compact['table'] = {'columns': view['table']['columns'], 'rows': view['table']['rows'][:50]}
    if view.get('gerber'):compact['layers'] = [{'role': l['role'], 'strokes': len(l['lines']), 'pads': len(l['flashes']), 'holes': len(l.get('holes', []))} for l in view['gerber']['layers']]
    if 'hex' in view and view.get('text') is None:compact['hex'] = view['hex'][:2000]
    compact['authority'] = 'READ_ONLY_FILE_VIEW'
    return compact
