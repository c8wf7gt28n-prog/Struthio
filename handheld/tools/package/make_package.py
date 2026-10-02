#!/usr/bin/env python3
"""STRUTHIO HANDHELD · builds the release package the build manual describes.

    python3 tools/package/make_package.py OUT_DIR [MANUAL.pdf MANUAL.docx]

Writes OUT_DIR/struthio/ (the folder the manual calls C:\\struthio or
~/struthio) and OUT_DIR/STRUTHIO_HANDHELD.zip whose top folder is struthio/,
so "Extract All" to C:\\ gives exactly the paths the manual uses. Only what the
manual uses goes in; every file is listed in SHA256SUMS.txt, which
tools/struthio_doctor.py checks.
"""
import hashlib, os, shutil, stat, sys, zipfile

HH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.abspath(sys.argv[1])
MANUAL = sys.argv[2:4]
PKG = os.path.join(OUT, 'struthio')

# (source relative to handheld/, destination relative to struthio/)
TREES = [
    ('core', 'handheld/core'), ('render', 'handheld/render'), ('audio', 'handheld/audio'),
    ('golden', 'handheld/golden'), ('host', 'handheld/host'),
    ('firmware', 'handheld/firmware'),
    ('build/assets', 'handheld/build/assets'),
    ('cad/handheld', 'handheld/cad/handheld'),
]
FILES = [
    ('tools/struthio_doctor.py', 'handheld/tools/struthio_doctor.py'),
    ('docs/PINOUT_AND_WIRING.md', 'handheld/docs/PINOUT_AND_WIRING.md'),
    ('tools/launcher/STRUTHIO.bat', 'STRUTHIO.bat'),
    ('tools/launcher/struthio.sh', 'struthio.sh'),
    ('tools/launcher/README_FIRST.txt', 'README_FIRST.txt'),
]
SKIP_DIRS = {'build', '__pycache__', 'idf_check', 'node_modules', 'managed_components', '.git'}
SKIP_FILES = {'sdkconfig', 'sdkconfig.old', 'dependencies.lock', 'test_buttons', '.DS_Store'}

def keep_dir(rel, name):
    if name in SKIP_DIRS and not (rel == 'build' and name == 'assets'): return False
    return True

def copy_tree(src, dst):
    for d, dirs, files in os.walk(src):
        rel = os.path.relpath(d, src)
        dirs[:] = [x for x in dirs if keep_dir(rel, x)]
        for f in files:
            if f in SKIP_FILES or f.endswith(('.pyc', '.o')): continue
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            shutil.copy2(os.path.join(d, f), os.path.join(dst, rel, f))

def main():
    if os.path.exists(PKG): shutil.rmtree(PKG)
    os.makedirs(PKG)
    for s, d in TREES: copy_tree(os.path.join(HH, s), os.path.join(PKG, d))
    for s, d in FILES:
        os.makedirs(os.path.dirname(os.path.join(PKG, d)) or PKG, exist_ok=True)
        shutil.copy2(os.path.join(HH, s), os.path.join(PKG, d))
    os.chmod(os.path.join(PKG, 'struthio.sh'), 0o755)
    os.chmod(os.path.join(PKG, 'handheld', 'cad', 'handheld', 'export_handheld.sh'), 0o755)
    if MANUAL:
        os.makedirs(os.path.join(PKG, 'manual'), exist_ok=True)
        for m in MANUAL:
            shutil.copy2(m, os.path.join(PKG, 'manual', 'STRUTHIO_Build_Manual' + os.path.splitext(m)[1]))
    # the batch file must keep Windows line endings
    bat = os.path.join(PKG, 'STRUTHIO.bat')
    data = open(bat, 'rb').read().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    open(bat, 'wb').write(data)
    # checksums of everything except the checksum file itself and the user's port memory
    lines = []
    for d, dirs, files in os.walk(PKG):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, PKG).replace(os.sep, '/')
            lines.append(f'{hashlib.sha256(open(p, "rb").read()).hexdigest()}  {rel}')
    open(os.path.join(PKG, 'SHA256SUMS.txt'), 'w', newline='\n').write('\n'.join(lines) + '\n')
    z = os.path.join(OUT, 'STRUTHIO_HANDHELD.zip')
    if os.path.exists(z): os.remove(z)
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for d, dirs, files in os.walk(PKG):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(d, f)
                arc = os.path.relpath(p, OUT).replace(os.sep, '/')
                zi = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o755 if os.access(p, os.X_OK) else 0o644) << 16
                zf.writestr(zi, open(p, 'rb').read())
    n = len(lines)
    print(f'{PKG}: {n} files; {z}: {os.path.getsize(z)/1e6:.1f} MB')

if __name__ == '__main__':
    main()
