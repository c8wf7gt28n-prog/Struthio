#!/usr/bin/env python3
"""Write bench-data.js for the studio's BENCH and DOCS tabs.

    python3 -B CHECKS/build_bench_data.py

BENCH: the bring-up procedure (LAYERS/01_PCB/BRINGUP_PROCEDURE.md) parsed into phases and steps, so a board's
measurements can be recorded step by step on a phone. DOCS: the current package documents as text, so the studio can
search and show them offline (the deploy bundle carries no other files). Each entry carries its path and SHA-256 so a
record or a quote can be traced to the file it came from. Nothing in the package is changed.
"""
from pathlib import Path
import hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
OUT = ROOT / 'bench-data.js'
PROCEDURE = 'LAYERS/01_PCB/BRINGUP_PROCEDURE.md'
DOCS = [   # (path from the package root, or from the repository for the firmware, title)
    ('README.txt', 'Package README'),
    ('PRODUCTION_GATES.md', 'Production gates'),
    ('QC_REPORT.txt', 'QC report'),
    ('DECISIONS_R32.md', 'Decisions R32'),
    ('CHANGELOG.md#latest', 'Changelog: this revision'),
    ('LAYERS/01_PCB/README_PCB_LAYER.md', 'PCB layer'),
    ('LAYERS/01_PCB/RELEASE_GATES.md', 'PCB release gates'),
    (PROCEDURE, 'Bring-up procedure'),
    ('LAYERS/01_PCB/DISPLAY_PORT.md', 'Display port'),
    ('LAYERS/01_PCB/FIRMWARE_PINMAP.md', 'Firmware pin map'),
    ('ASSEMBLY/ASSEMBLY_SEQUENCE.md', 'Assembly sequence'),
    ('CHECKS/PREORDER_REVIEW_R26/README.md', 'Pre-order review: summary'),
    ('CHECKS/PREORDER_REVIEW_R26/POWER_findings.md', 'Pre-order review: power'),
    ('CHECKS/PREORDER_REVIEW_R26/P4CORE_findings.md', 'Pre-order review: ESP32-P4 core'),
    ('CHECKS/PREORDER_REVIEW_R26/DISPLAY_findings.md', 'Pre-order review: display'),
    ('CHECKS/PREORDER_REVIEW_R26/AUDIO_IO_findings.md', 'Pre-order review: audio, controls, USB'),
    ('CHECKS/PREORDER_REVIEW_R26/FIRMWARE_findings.md', 'Pre-order review: firmware'),
    ('REFERENCES/CASE_R13_CONTROLS_PROTOTYPE/README.md', 'Case R13 controls prototype (reference)'),
    ('REFERENCES/CASE_R1_STREAMLINE_STUDY/README.md', 'Case R1 outline study (reference)'),
    ('@firmware/slim4/docs/FIRST_BOOT.md', 'Firmware: first boot, self-test, console'),
    ('@firmware/slim4/RELEASE_NOTES_R12.md', 'Firmware R12 release notes'),
    ('@firmware/slim4/README.md', 'Firmware README'),
]


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def procedure():
    text = (ROOT / PROCEDURE).read_text()
    phases, cur = [], None
    for line in text.splitlines():
        m = re.match(r'## Phase ([A-Z]) — (.*)', line)
        if m:
            cur = {'id': m.group(1), 'title': m.group(2).strip(), 'note': '', 'steps': []}
            phases.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith('## '):
            cur = None
            continue
        if re.match(r'\| [A-Z]\d+ \|', line):
            c = cells(line)
            assert len(c) == 4, line
            assert c[0][0] == cur['id'], line
            cur['steps'].append({'id': c[0], 'probe': c[1], 'expected': c[2], 'wrong': c[3]})
        elif line.strip() and not line.startswith('|'):
            cur['note'] = (cur['note'] + ' ' + line.strip()).strip()
    ids = [s['id'] for p in phases for s in p['steps']]
    assert len(ids) == len(set(ids)), 'duplicate step ids'
    assert [p['id'] for p in phases] == list('ABCDEFGH'), [p['id'] for p in phases]
    title = text.splitlines()[0].lstrip('# ').strip()
    return {'source': PROCEDURE, 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'title': title, 'phases': phases}


def doc(path, title):
    if path.startswith('@'):
        f, shown = REPO / path[1:], path[1:]
    else:
        f, shown = ROOT / path.split('#')[0], 'hardware/slim4/' + path.split('#')[0]
    raw = f.read_text()
    text = raw
    if path.endswith('#latest'):           # the current package's entries only: the file holds every revision since R1
        parts = re.split(r'\n(?=# )', raw)
        rev = parts[0].split()[1]
        text = '\n'.join(x for x in parts if x.split()[1] == rev)
    return {'path': shown, 'title': title, 'sha256': hashlib.sha256(raw.encode()).hexdigest(), 'text': text}


def main():
    data = {'procedure': procedure(), 'docs': [doc(p, t) for p, t in DOCS]}
    OUT.write_text('window.STRUTHIO_BENCH = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';\n')
    n = sum(len(p['steps']) for p in data['procedure']['phases'])
    print(f"bench-data.js: {len(data['procedure']['phases'])} phases, {n} steps; {len(data['docs'])} documents; "
          f"{OUT.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
