import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
files = d['files']
wheels = sorted(k for k in files if not k.startswith('debs/'))
debs = sorted(k for k in files if k.startswith('debs/'))
print('total', len(files), 'debs', len(debs), 'non-deb', len(wheels))
for w in wheels:
    print('  ', w, files[w]['bytes'])
print('deb bytes total', sum(files[k]['bytes'] for k in debs))
import re
names = [re.sub(r'^debs/', '', k).split('_')[0] for k in debs]
interesting = [n for n in names if re.search(r'python3|libreoffice|fluxbox|xorg|xinit|xserver|vulkan|mesa|firmware|tesseract|poppler|mupdf|java|jre|jdk|kicad|ngspice|yosys|wireshark|tcpdump|dumpcap|qt|xcb|pip|venv|ghostscript|qpdf|ocr', n)]
print(len(interesting), 'interesting:')
print(', '.join(interesting))
