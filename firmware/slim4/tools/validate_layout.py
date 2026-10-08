#!/usr/bin/env python3
"""Validate partition CSV alignment and address coverage for the SLIM4 64 MiB flash."""
import csv
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'partitions.csv'
rows=[]
names=set()
parts={}
for row in csv.reader(line for line in p.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')):
    name, kind, subtype, offset, size, *_ = [x.strip() for x in row]
    assert name not in names, f'duplicate partition name: {name}'
    names.add(name)
    parts[name]=(kind,subtype)
    off=int(offset,0); length=int(size,0)
    assert off%0x1000==0, f'{name}: offset not 4 KiB aligned'
    assert length%0x1000==0, f'{name}: size not 4 KiB aligned'
    assert length>0 and (off+length)<=0x4000000, f'{name}: outside 64 MiB flash'
    if kind=='app':
        assert off%0x10000==0, f'{name}: app offset not 64 KiB aligned'
        assert length%0x10000==0, f'{name}: app size not 64 KiB aligned'
        assert off+length<=0x1000000, f'{name}: app must end below 16 MiB (code cannot run from beyond 16 MiB)'
    rows.append((off,off+length,name))
rows.sort()
for a,b in zip(rows,rows[1:]):
    assert a[1]<=b[0], f'overlap: {a[2]} and {b[2]}'
assert rows[-1][1]==0x4000000, 'layout must end at 64 MiB boundary'
required={'nvs','otadata','recovery','ota_0','ota_1','assets','games'}
assert required <= names
assert parts['recovery']==('app','factory'), 'recovery must remain the factory app'
assert parts['ota_0']==('app','ota_0') and parts['ota_1']==('app','ota_1'), 'system A/B slots missing'
assert parts['ota_0'][1] != 'factory' and parts['ota_1'][1] != 'factory'
print(f'PASS: {len(rows)} partitions, 64 KiB app alignment, apps below 16 MiB, factory recovery + A/B slots, no overlaps, end=0x{rows[-1][1]:X}')
