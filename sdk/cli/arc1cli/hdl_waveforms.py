"""Bounded, GUI-independent VCD reading and four-state cursor values.

Native files remain authoritative. This inspector covers digital VCD, not FST,
GHW, analog interpolation, delta-cycle reconstruction or physical timing.
"""
from bisect import bisect_right
import gzip
from io import StringIO
from pathlib import Path
import re
import zlib

UNITS={'s':10**15,'ms':10**12,'us':10**9,'ns':10**6,'ps':10**3,'fs':1}


def vcd_bytes(path,max_bytes=32*1024*1024):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>max_bytes:raise ValueError('VCD absent, linked or oversized')
    try:
        if path.suffix=='.gz':
            with gzip.open(path,'rb') as file:data=file.read(max_bytes+1)
        else:data=path.read_bytes()
    except (OSError,EOFError,zlib.error) as exc:raise ValueError('Invalid or truncated VCD archive') from exc
    if len(data)>max_bytes:raise ValueError('Decoded VCD exceeds bound')
    return data


def archive_vcd(path,data):
    """Retain exact native bytes compactly; do not change VCD content."""
    path=Path(path)
    if path.suffix!='.gz' or len(data)>32*1024*1024:raise ValueError('VCD archive destination or size is invalid')
    packed=gzip.compress(data,compresslevel=6,mtime=0)
    if gzip.decompress(packed)!=data:raise ValueError('VCD archive roundtrip differs')
    temporary=path.with_name(path.name+'.partial');temporary.write_bytes(packed);temporary.replace(path)
    if vcd_bytes(path)!=data:raise ValueError('Retained VCD archive differs from native bytes')


def parse_vcd(path,max_bytes=32*1024*1024,max_events=1000000,max_signals=512):
    data=vcd_bytes(path,max_bytes)
    scopes=[];variables={};codes={};tick_fs=None;header=True;block=None;time=0;events=0
    with StringIO(data.decode('ascii')) as file:
        for raw in file:
            if len(raw)>16384:raise ValueError('VCD line exceeds bound')
            line=raw.strip()
            if not line:continue
            if header:
                if block is not None:
                    block+= ' '+line
                    if '$end' not in line:continue
                    line=block;block=None
                if line.startswith(('$date','$version','$comment')):
                    if '$end' not in line:block=line
                    continue
                if line.startswith('$timescale'):
                    if '$end' not in line:block=line;continue
                    match=re.fullmatch(r'\$timescale\s+(1|10|100)\s*(s|ms|us|ns|ps|fs)\s+\$end',line)
                    if not match or tick_fs is not None:raise ValueError('Unsupported or duplicate VCD timescale')
                    tick_fs=int(match[1])*UNITS[match[2]];continue
                if line.startswith('$scope'):
                    fields=line.split()
                    if len(fields)!=4 or fields[-1]!='$end' or len(scopes)>=32:raise ValueError('Invalid VCD scope')
                    scopes.append(fields[2]);continue
                if line=='$upscope $end':
                    if not scopes:raise ValueError('Unbalanced VCD scope')
                    scopes.pop();continue
                if line.startswith('$var'):
                    fields=line.split()
                    if len(fields) not in (6,7) or fields[-1]!='$end' or fields[1] not in ('wire','reg','integer','parameter','event'):
                        raise ValueError('Unsupported VCD variable declaration')
                    kind,width,code,name=fields[1:5]
                    if not width.isdigit() or not 1<=int(width)<=1024:raise ValueError('VCD width exceeds bound')
                    full='.'.join(scopes+[name])
                    if full in variables or len(variables)>=max_signals or len(full)>512:raise ValueError('Duplicate or excessive VCD variables')
                    if code in codes and codes[code]['width']!=int(width):raise ValueError('VCD alias width differs')
                    row=codes.setdefault(code,{'width':int(width),'changes':[]})
                    variables[full]={'kind':kind,'width':int(width),'code':code,'changes':row['changes']};continue
                if line=='$enddefinitions $end':
                    if scopes or not variables or tick_fs is None:raise ValueError('Incomplete VCD header')
                    header=False;continue
                raise ValueError('Unsupported VCD header statement')
            if line.startswith('#'):
                if not line[1:].isdigit() or int(line[1:])<time:raise ValueError('VCD time moved backwards or is invalid')
                time=int(line[1:]);continue
            if line in ('$dumpvars','$end','$dumpall','$dumpon','$dumpoff'):continue
            if line.startswith('$comment'):
                if '$end' not in line:raise ValueError('Multiline data comment unsupported')
                continue
            if line[0] in '01xXzZ':value,code=line[0].lower(),line[1:]
            elif line[0] in 'bB':
                fields=line[1:].split()
                if len(fields)!=2:raise ValueError('Invalid vector change')
                value,code=fields;value=value.lower()
            else:raise ValueError('Unsupported VCD data statement')
            if code not in codes or not value or re.fullmatch('[01xz]+',value) is None:raise ValueError('Invalid or undeclared VCD value')
            row=codes[code];width=row['width']
            if len(value)>width:raise ValueError('VCD value exceeds declared width')
            value=value.rjust(width,value[0] if value[0] in 'xz' else '0');events+=1
            if events>max_events:raise ValueError('VCD change count exceeds bound')
            if not row['changes'] or row['changes'][-1][1]!=value:row['changes'].append([time,value])
    if header or block is not None:raise ValueError('Truncated VCD header')
    if not events:raise ValueError('VCD contains no changes')
    return {'schema':'arc.digital-vcd/1','tick_fs':tick_fs,'end_tick':time,'events':events,
            'signals':variables,'scope':'Digital four-state VCD; cursor uses the last recorded value at a tick. Raw file preserves recorded ordering.'}


def value_at(signal,tick):
    changes=signal['changes'];index=bisect_right(changes,tick,key=lambda pair:pair[0])-1
    return changes[index][1] if index>=0 else 'x'*signal['width']


def display_value(bits):
    if any(c in bits for c in 'xz'):return bits
    return str(int(bits,2)) if len(bits)==1 else '0x'+format(int(bits,2),'0'+str((len(bits)+3)//4)+'X')


def summary(trace):
    return {'schema':trace['schema'],'tick_fs':trace['tick_fs'],'end_tick':trace['end_tick'],'events':trace['events'],
            'signals':{name:{'width':row['width'],'transitions':len(row['changes']),
                             'has_unknown':any('x' in value or 'z' in value for _,value in row['changes'])}
                       for name,row in trace['signals'].items()},'scope':trace['scope']}
