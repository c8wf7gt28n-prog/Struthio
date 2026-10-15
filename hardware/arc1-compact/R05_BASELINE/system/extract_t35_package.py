#!/usr/bin/env python3
"""Extract factual package records, not board nets, from the vendor XLSX.

Standard library only. Raw manufacturer workbook is not redistributed here.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from collections import Counter

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
COLUMNS = ['bank', 'manufacturer_pin_name', 'configuration_functions',
           'ddr_interface', 'lvds_pair', 'ddio', 'clock_region', 'ball']


def extract(path: Path):
    with ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            strings = [''.join(n.itertext()) for n in root.findall('s:si', NS)]
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        matches = [s for s in workbook.findall('s:sheets/s:sheet', NS) if s.attrib['name'] == 'T35F400']
        if len(matches) != 1:
            raise ValueError('Expected exactly one T35F400 sheet')
        relationship_id = matches[0].attrib['{' + NS['r'] + '}id']
        relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target = next(r.attrib['Target'] for r in relationships if r.attrib['Id'] == relationship_id)
        member = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        sheet = ET.fromstring(z.read(member))
        records = []
        for row in sheet.findall('s:sheetData/s:row', NS):
            values = {}
            for cell in row.findall('s:c', NS):
                column = re.match(r'[A-Z]+', cell.attrib['r']).group()
                if column not in 'ABCDEFGH' or len(column) != 1:
                    continue
                v = cell.find('s:v', NS)
                raw = v.text if v is not None and v.text is not None else ''
                if cell.attrib.get('t') == 's':
                    raw = strings[int(raw)]
                elif cell.attrib.get('t') == 'inlineStr':
                    raw = ''.join(cell.find('s:is', NS).itertext())
                values[column] = raw
            if re.fullmatch(r'[A-Z]{1,2}[0-9]{1,2}', values.get('H', '')):
                record = {key: values.get(column, '') for key, column in zip(COLUMNS, 'ABCDEFGH')}
                record['source_row'] = row.attrib['r']
                record['board_net'] = ''
                records.append(record)
    if len(records) != 400 or len({r['ball'] for r in records}) != 400:
        raise ValueError('Expected 400 unique source balls; no partial inventory accepted')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    records = extract(args.workbook)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'T35F400_package_source_facts.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS + ['source_row', 'board_net'])
        writer.writeheader(); writer.writerows(records)
    report = {
        'scope': 'MANUFACTURER_PACKAGE_FACTS_NOT_PCB_ASSIGNMENTS',
        'source_url': 'https://www.efinixinc.com/support/docsdl.php?pn=T35-PINOUT&s=ef',
        'source_version_from_index': 'v1.5 March2025',
        'source_workbook_sha256': hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
        'sheet': 'T35F400', 'source_columns': 'A-H', 'records': len(records),
        'unique_balls': len({r['ball'] for r in records}),
        'assigned_board_nets': sum(bool(r['board_net']) for r in records),
        'gpio_named_entries': sum(r['manufacturer_pin_name'].startswith('GPIO') for r in records),
        'ddr_interface_annotated_entries': sum(bool(r['ddr_interface']) for r in records),
        'lvds_annotated_entries': sum(bool(r['lvds_pair']) for r in records),
        'ddio_yes_entries': sum(r['ddio'].lower() == 'yes' for r in records),
        'bank_counts': dict(sorted(Counter(r['bank'] for r in records).items())),
        'native_efinity_verified': False, 'physical_board_verified': False,
        'raw_workbook_bundled': False,
        'notes': ['Counts are source facts; annotations may overlap and are not free-pin counts.',
                  'No clocks, bank voltages, DDR lane assignments or user nets were allocated.']}
    (args.output / 'package_source_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
