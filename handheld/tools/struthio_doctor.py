#!/usr/bin/env python3
"""STRUTHIO HANDHELD · setup doctor.

Checks the things the build manual asks you to check by hand, and says what to
do about each one: the package is complete and undamaged, the folder path is
safe, ESP-IDF 5.5.x is reachable, the firmware folder is set up, and which
serial port is the board. Windows, macOS and Linux; Python 3.8+.

    python tools/struthio_doctor.py            # full check (from the handheld folder)
    python tools/struthio_doctor.py --port     # print only the board's port (for scripts)
    python tools/struthio_doctor.py --verify   # package files only (SHA-256)
"""
import csv, hashlib, os, platform, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.dirname(HERE)                         # .../handheld
ROOT = os.path.dirname(HH)                         # the unzipped package folder
FW = os.path.join(HH, 'firmware')
ASSETS = os.path.join(HH, 'build', 'assets')
ESPRESSIF_VID = 0x303A                             # the ESP32-S3's own USB Serial/JTAG

results = []
def report(level, what, fix=''):
    results.append(level)
    print(f'{level:<5} {what}')
    if fix: print(f'      -> {fix}')

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def check_files():
    sums = os.path.join(ROOT, 'SHA256SUMS.txt')
    if not os.path.exists(sums):
        report('WARN', 'SHA256SUMS.txt not found next to the handheld folder',
               'unzip the whole package; this check needs the file list it ships with')
        return
    bad, missing, n = [], [], 0
    for line in open(sums, encoding='utf-8'):
        m = re.match(r'([0-9a-f]{64})\s+\*?(.+)', line.strip())
        if not m: continue
        n += 1
        path = os.path.join(ROOT, *m.group(2).split('/'))
        if not os.path.exists(path): missing.append(m.group(2))
        elif sha256(path) != m.group(1): bad.append(m.group(2))
    if missing: report('FAIL', f'{len(missing)} of {n} package files are missing, e.g. {missing[0]}', 'unzip the package again, all of it')
    if bad: report('FAIL', f'{len(bad)} package files differ from the release, e.g. {bad[0]}', 'unzip the package again; do not edit build/assets')
    if not missing and not bad: report('PASS', f'package complete: {n} files match SHA256SUMS.txt')

def check_assets():
    parts = {}
    with open(os.path.join(FW, 'partitions.csv')) as f:
        for row in csv.reader(l for l in f if l.strip() and not l.lstrip().startswith('#')):
            parts[row[0].strip()] = int(row[4].strip(), 0)
    for name, part in (('struthio.pak', 'assets'), ('struthio_music.ima', 'music')):
        p = os.path.join(ASSETS, name)
        if not os.path.exists(p):
            report('FAIL', f'build/assets/{name} is missing', 'unzip the package again; the build flashes this file')
            continue
        size = os.path.getsize(p)
        ok = size <= parts[part]
        report('PASS' if ok else 'FAIL', f'{name}: {size/2**20:.1f} MB fits the {part} partition ({parts[part]/2**20:.1f} MB)' if ok
               else f'{name} ({size} bytes) is larger than the {part} partition', '' if ok else 'unzip the package again')

def check_path():
    p = os.path.abspath(ROOT)
    if ' ' in p or '(' in p:
        report('FAIL', f'the package path contains a space or bracket: {p}', 'move the folder to C:\\struthio (Windows) or ~/struthio')
    elif not p.isascii():
        report('WARN', f'the package path has non-English letters: {p}', 'C:\\struthio or ~/struthio is safest')
    elif 'onedrive' in p.lower() or 'dropbox' in p.lower() or 'icloud' in p.lower():
        report('WARN', f'the package is inside a synced folder: {p}', 'syncing can lock build files; use C:\\struthio')
    else:
        report('PASS', f'package path is safe: {p}')

def check_python():
    v = sys.version_info
    report('PASS' if v >= (3, 9) else 'WARN', f'Python {v.major}.{v.minor}.{v.micro}',
           '' if v >= (3, 9) else 'ESP-IDF 5.5 needs Python 3.9 or newer')

def idf_version():
    exe = shutil.which('idf.py')
    if not exe: return None, None
    try:
        out = subprocess.run([exe, '--version'] if not exe.lower().endswith('.py') else [sys.executable, exe, '--version'],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        out = ''
    m = re.search(r'v(\d+\.\d+(?:\.\d+)?)', out or '')
    return exe, (m.group(1) if m else (out or '').strip())

def check_idf():
    exe, ver = idf_version()
    if not exe:
        where = ('open "ESP-IDF 5.5 CMD" from the Start menu, then run STRUTHIO.bat there' if os.name == 'nt'
                 else 'run:  . ~/esp/esp-idf/export.sh   (then try again)')
        report('FAIL', 'idf.py is not on the PATH of this terminal', where)
        return False
    if ver and ver.startswith('5.5'):
        report('PASS', f'ESP-IDF v{ver} ({exe})')
    else:
        report('WARN', f'ESP-IDF {ver or "version unknown"} found; this build is checked with v5.5.5',
               'install ESP-IDF v5.5.x (manual, Step 3) if the build fails')
    return True

def check_firmware_folder():
    sdk = os.path.join(FW, 'sdkconfig')
    if not os.path.exists(sdk):
        report('INFO', 'firmware not set up yet (normal before the first build)', 'menu option "Build" runs: idf.py set-target esp32s3')
    else:
        target = re.search(r'CONFIG_IDF_TARGET="(\w+)"', open(sdk).read())
        t = target.group(1) if target else '?'
        report('PASS' if t == 'esp32s3' else 'FAIL', f'firmware target: {t}', '' if t == 'esp32s3' else 'run: idf.py set-target esp32s3')
    cache = os.path.join(FW, 'build', 'CMakeCache.txt')
    if os.path.exists(cache):
        m = re.search(r'STRUTHIO_ART:\w+=(\w+)', open(cache, errors='ignore').read())
        art = m.group(1) if m else 'full'
        report('INFO', f'next flash writes the {"GREYBOX marker" if art == "greybox" else "full art pack"} (STRUTHIO_ART={art})')

def board_ports():
    try:
        from serial.tools import list_ports
    except ImportError:
        return None
    return [(p.device, p.vid, p.description) for p in list_ports.comports()]

def check_ports():
    ports = board_ports()
    if ports is None:
        report('INFO', 'pyserial not available here: cannot list serial ports', 'run this from the ESP-IDF terminal, which includes it')
        return
    board = [p for p in ports if p[1] == ESPRESSIF_VID]
    if board:
        for dev, vid, desc in board: report('PASS', f'board found on {dev} ({desc})')
    elif ports:
        report('WARN', 'no ESP32-S3 USB port found; other ports: ' + ', '.join(p[0] for p in ports),
               'plug the board in with a DATA cable; if nothing appears, try another cable / USB port')
    else:
        report('WARN', 'no serial ports at all', 'plug the board in with a USB-C DATA cable (charge-only cables show nothing)')

def check_desktop_tools():
    if os.name == 'nt':
        wsl = shutil.which('wsl')
        report('INFO' if wsl else 'WARN', 'WSL found: desktop checks can run (menu option D)' if wsl else 'WSL not found: desktop checks need it',
               '' if wsl else 'optional: in an Administrator PowerShell run  wsl --install')
    else:
        have = shutil.which('make') and (shutil.which('cc') or shutil.which('gcc') or shutil.which('clang'))
        report('PASS' if have else 'WARN', 'C compiler and make found (desktop checks)' if have else 'no C compiler / make (desktop checks)',
               '' if have else 'macOS: xcode-select --install   Linux: sudo apt install build-essential')

def main():
    if '--port' in sys.argv:
        ports = board_ports() or []
        board = [p[0] for p in ports if p[1] == ESPRESSIF_VID]
        print(board[0] if board else '')
        return 0 if board else 1
    print('STRUTHIO HANDHELD · setup doctor')
    print(f'{platform.system()} {platform.release()} · package: {ROOT}\n')
    check_files()
    if '--verify' in sys.argv:
        return 1 if 'FAIL' in results else 0
    check_assets(); check_path(); check_python()
    check_idf(); check_firmware_folder(); check_ports(); check_desktop_tools()
    fails, warns = results.count('FAIL'), results.count('WARN')
    print(f'\n{"ALL GOOD" if not fails and not warns else f"{fails} FAIL, {warns} WARN"}: '
          f'{"you can build and flash" if not fails else "fix the FAIL lines first (the arrow says how)"}')
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
