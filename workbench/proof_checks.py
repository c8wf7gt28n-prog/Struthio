"""Pure verification primitives. A valid fixture never certifies a real board."""
from decimal import Decimal, localcontext
import math, struct


def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Finite numeric '+name+' required')
    if positive and value <= 0:
        raise ValueError('Positive '+name+' required')
    return Decimal(str(value))


def power(case, limits, allowance_v=0):
    """Independent Decimal evaluation of three worst-case DC inequalities."""
    with localcontext() as ctx:
        ctx.prec = 40
        rt, rb, st, sb = [number(case[k], k, True) for k in
            ('feedback_top_ohm','feedback_bottom_ohm','sense_top_ohm','sense_bottom_ohm')]
        t = number(limits['resistor_tolerance'], 'tolerance')
        if not 0 <= t < 1: raise ValueError('Tolerance outside [0,1)')
        fb0,fb1,s0,s1,h,i,v0,v1=[number(limits[k],k,True) for k in
            ('fb_min','fb_max','sense_min','sense_max','hysteresis_max','bias_abs_a','core_min','core_max')]
        if fb0>fb1 or s0>s1 or v0>=v1: raise ValueError('Reversed limits')
        a=number(allowance_v,'allowance')
        if a<0: raise ValueError('Negative allowance')
        lo=(1-t)/(1+t);hi=(1+t)/(1-t)
        reglo=fb0*(1+rt/rb*lo);reghi=fb1*(1+rt/rb*hi)
        triplo=s0*(1+st/sb*lo)-i*st*(1-t)
        releasehi=(s1+h)*(1+st/sb*hi)+i*st*(1+t)
        margins={'brownout_headroom_v':triplo-v0,'startup_headroom_v':reglo-releasehi,'upper_operating_headroom_v':v1-reghi}
        remaining={k:float(v-a) for k,v in margins.items()}
        return dict(status='VALID' if all(v>0 for v in remaining.values()) else 'INVALID',
            margins_v={k:float(v) for k,v in margins.items()},remaining_v=remaining,
            assumption_allowance_v=float(a),scope='DC inequalities only; load/ripple/thermal/delay/PCB drop excluded')


def pins(fixture):
    pads=fixture.get('pads');assignments=fixture.get('assignments');banks=fixture.get('banks')
    if not isinstance(pads,dict) or not pads or not isinstance(assignments,list) or not assignments or not isinstance(banks,dict):
        raise ValueError('Nonempty package pads, assignments and banks required')
    if any(not isinstance(v,dict) for v in pads.values()):raise ValueError('Each package pad must be an object')
    errors=[];unknown=[];seen={};ports=set()
    for row in assignments:
        if not isinstance(row,dict) or not isinstance(row.get('port'),str) or not row.get('port') or not isinstance(row.get('pin'),(str,int)) or isinstance(row.get('pin'),bool) or not isinstance(row.get('io_type'),str):
            raise ValueError('Each assignment requires a port, pin and IO type')
        if 'requires_clock' in row and not isinstance(row['requires_clock'],bool):raise ValueError('requires_clock must be Boolean')
        port=row['port'];pin=str(row['pin']);io=row['io_type']
        if port in ports: errors.append('DUPLICATE_PORT '+port)
        ports.add(port)
        if pin in seen: errors.append('DUPLICATE_PAD '+pin+' '+seen[pin]+' '+port)
        seen[pin]=port
        pad=pads.get(pin)
        if pad is None: errors.append('ILLEGAL_PAD '+pin);continue
        if pad.get('kind')!='IO':errors.append('NON_IO_PAD '+pin)
        bank=str(pad.get('bank'));rail=banks.get(bank)
        expected={'LVCMOS33':'3V3','LVCMOS25':'2V5','LVCMOS18':'1V8'}.get(io)
        if expected is None or rail is None:unknown.append('UNSUPPORTED_IO_OR_BANK '+port)
        elif rail!=expected:errors.append('BANK_VOLTAGE_CONFLICT '+port+' '+str(rail)+' / '+io)
        if row.get('requires_clock') and not pad.get('clock'):errors.append('NON_CLOCK_PAD '+pin)
    return dict(status='INVALID' if errors else 'UNPROVEN' if unknown else 'VALID',errors=errors,missing_proof=unknown,
        scope='Legality relative to supplied package/rail table; caller provenance must be checked separately')


def boot_artifact(data, claim, expected_sha, actual_sha):
    errors=[];unproven=[];kind='unknown';machine=None
    if expected_sha!=actual_sha:errors.append('HASH_MISMATCH')
    if data.startswith(b'\x7fELF'):
        kind='ELF'
        if len(data)<20 or data[5] not in (1,2):errors.append('MALFORMED_ELF')
        else: machine=struct.unpack('<H' if data[5]==1 else '>H',data[18:20])[0]
    elif data.startswith(b'MZ'):kind='PE_HOST_CONTAINER'
    if claim=='ROM_BOOTABLE':
        if kind in ('ELF','PE_HOST_CONTAINER'):
            errors.append('EXECUTABLE_CONTAINER_IS_NOT_VERIFIED_ROM_IMAGE')
        else:unproven.extend(['Vendor ROM header/checksum and exact SoC required','DDR/startup/linker evidence and target execution missing'])
    elif claim=='HOST_EXECUTABLE':
        if kind not in ('ELF','PE_HOST_CONTAINER'):errors.append('NOT_RECOGNIZED_EXECUTABLE')
    else:raise ValueError('Unsupported artifact claim')
    return dict(status='INVALID' if errors else 'UNPROVEN' if unproven else 'VALID',format=kind,elf_machine=machine,
        errors=errors,missing_proof=unproven,device_boot_verified=False,
        scope='Container and hash screening only; HOST_EXECUTABLE validity does not imply execution safety')


def propagate(nodes, edges, failed):
    known={n['id'] for n in nodes}
    if not set(failed)<=known:raise ValueError('Unknown fault node')
    for e in edges:
        if e['from'] not in known or e['to'] not in known:raise ValueError('Dangling dependency')
    unavailable=set(failed)
    for _ in nodes:
        new=unavailable|{e['to'] for e in edges if e['from'] in unavailable}
        if new==unavailable:break
        unavailable=new
    return dict(injected=sorted(failed),unavailable=sorted(unavailable),
        interpretation='Dependency model only, not a physical fault injection or proof of target recovery')
