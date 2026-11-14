"""Static cross-consistency check of the Graphite transfer metadata. Reads only; executes nothing from the data."""
import hashlib, html, json, re, sys
from pathlib import Path

T = Path(sys.argv[1])          # Graphite_Transfer
R = Path(sys.argv[2])          # restored tree
GROUPS = ('App', 'Records', 'System', 'Wheels')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


print('=== 1. RELEASE_PARTS.json vs SHA256SUMS vs SUMMARY.json')
summary = json.loads((T / 'Verification/SUMMARY.json').read_text())
rp = {}
tot_all = 0
for g in GROUPS:
    d = json.loads((T / g / 'RELEASE_PARTS.json').read_text())
    rp[g] = d
    sums = {}
    for line in (T / g / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        sums[name.strip()] = digest
    parts = d['parts']
    names = [p['name'] for p in parts]
    ok_names = set(names) == set(sums)
    ok_hash = all(sums.get(p['name']) == p['sha256'] for p in parts)
    total = sum(p['bytes'] for p in parts)
    tot_all += total
    largest = max(p['bytes'] for p in parts)
    sg = summary['groups'][g]
    print(f"{g}: parts={len(parts)} sums_lines={len(sums)} names_match={ok_names} sha_match={ok_hash} "
          f"total_bytes={total} largest={largest} | SUMMARY parts={sg['parts']} largest_zip={sg['largest_zip']} "
          f"summary_match={(sg['parts'] == len(parts) and sg['largest_zip'] == largest)}")
    print(f"   checkpoint={d['checkpoint']!r} payload_entries={d['payload_entries']} source_archive_bytes={d['source_archive_bytes']} "
          f"split_files={len(d['file_chunks'])} all<=limit={all(p['bytes'] <= d['part_limit_bytes'] for p in parts)}")
    for name, meta in d['file_chunks'].items():
        cs = meta['chunks']
        print(f"   split: {name} bytes={meta['bytes']} chunks={len(cs)} chunk_sum_ok={sum(c['bytes'] for c in cs) == meta['bytes']} sizes={[c['bytes'] for c in cs]}")
print('TOTAL bytes of the 50 numbered parts:', tot_all, 'count:', sum(len(rp[g]['parts']) for g in GROUPS))

print()
print('=== 2. cache-checks.json parts vs RELEASE_PARTS.json')
cc = json.loads((T / 'Verification/cache-checks.json').read_text())
for c in cc['caches']:
    g = c['cache']
    same = c['parts'] == rp[g]['parts']
    print(f"{g}: parts_identical_to_RELEASE_PARTS={same} original_files={c['original_files']} original_bytes={c['original_bytes']} "
          f"split_files_match={sorted(c['split_files']) == sorted(rp[g]['file_chunks'])} "
          f"original_archive_sha256={c['original_archive_sha256'][:16]}.. vs RELEASE_PARTS source_archive_sha256={rp[g]['source_archive_sha256'][:16]}..")
print('total_parts', cc['total_parts'], '== System+Wheels', len(rp['System']['parts']) + len(rp['Wheels']['parts']))

print()
print('=== 3. DOWNLOADS.html')
page = (T / 'DOWNLOADS.html').read_text()
links = re.findall(r'<a href="([^"]+)">([^<]+)</a>(?:<span>([^<]*)</span>)?', page)
print('anchor count:', len(links))
hosts = sorted({re.match(r'https?://([^/]+)/', html.unescape(u)).group(1) for u, _, _ in links})
print('hosts:', hosts)
ids = [re.search(r'file_id=([^&]+)', html.unescape(u)).group(1) for u, _, _ in links]
print('unique file_ids:', len(set(ids)), 'of', len(ids))
by_name = {}
for u, text, span in links:
    by_name[text.replace('Download ', '').strip()] = (u, span)
all_parts = {p['name']: p for g in GROUPS for p in rp[g]['parts']}
missing_links = sorted(set(all_parts) - set(by_name))
extra_links = sorted(set(by_name) - set(all_parts))
print('parts without a link:', missing_links)
print('links that are not numbered parts:', extra_links)
bad = []
for name, p in all_parts.items():
    span = by_name.get(name, (None, None))[1]
    shown = f"{p['bytes'] / 1e6:.2f} MB"
    if span != shown:
        bad.append((name, span, shown))
print('size labels that differ from bytes/1e6 rounded to 2dp:', bad)
m = re.search(r'The largest is ([\d,]+) bytes', page)
print('page says largest:', m.group(1), '| actual largest:', max(p['bytes'] for p in all_parts.values()),
      [n for n, p in all_parts.items() if p['bytes'] == max(q['bytes'] for q in all_parts.values())])
for s in re.findall(r'<summary>([^<]+)</summary>', page):
    print('   section:', s)

print()
print('=== 4. OFFLINE_FILES.json / DEBIAN_USB.sha256')
off_path = T / 'App/OFFLINE_FILES.json'
off = json.loads(off_path.read_text())
files = off['files']
print('schema', off['schema'], 'target', off.get('target'), 'python_target', off.get('python_target'))
debs = {k: v for k, v in files.items() if k.startswith('debs/')}
whls = {k: v for k, v in files.items() if k.startswith('wheels/')}
other = [k for k in files if k not in debs and k not in whls]
print('entries', len(files), 'debs', len(debs), 'wheels', len(whls), 'other', other)
print('deb bytes', sum(v['bytes'] for v in debs.values()), 'wheel bytes', sum(v['bytes'] for v in whls.values()))
print('OFFLINE_FILES.json size', off_path.stat().st_size, 'sha256', sha(off_path))
usb = {}
for line in (T / 'App/DEBIAN_USB.sha256').read_text().splitlines():
    digest, name = line.split(None, 1)
    usb[name.strip()] = digest
print('DEBIAN_USB.sha256 lines', len(usb))
print('OFFLINE_FILES.json digest in DEBIAN_USB matches file in START_HERE App/:', usb.get('OFFLINE_FILES.json') == sha(off_path))
usb_rest = {k: v for k, v in usb.items() if k != 'OFFLINE_FILES.json'}
print('DEBIAN_USB names == OFFLINE_FILES names:', set(usb_rest) == set(files),
      '| digests equal:', all(files[k]['sha256'] == v for k, v in usb_rest.items() if k in files))
print('only in DEBIAN_USB:', sorted(set(usb_rest) - set(files)))
print('only in OFFLINE_FILES:', sorted(set(files) - set(usb_rest)))
groupmap = {'OFFLINE_FILES.json': 0, 'debs': 0, 'wheels': 0, 'unmapped': []}
for k in usb:
    if k == 'OFFLINE_FILES.json': groupmap['OFFLINE_FILES.json'] += 1
    elif re.fullmatch(r'debs/[^/\s]+\.deb', k): groupmap['debs'] += 1
    elif re.fullmatch(r'wheels/[^/\s]+\.whl', k): groupmap['wheels'] += 1
    else: groupmap['unmapped'].append(k)
print('mapping:', groupmap)
# split files named in RELEASE_PARTS must be in the inventory with same bytes/sha
for g in ('System', 'Wheels'):
    for name, meta in rp[g]['file_chunks'].items():
        f = files.get(name)
        print(f"   split {g}: {name} in inventory={f is not None} bytes/sha equal={(f and f['bytes'] == meta['bytes'] and f['sha256'] == meta['sha256'])}")
sys_c = next(c for c in cc['caches'] if c['cache'] == 'System')
whl_c = next(c for c in cc['caches'] if c['cache'] == 'Wheels')
deb_sum = sum(v['bytes'] for v in debs.values()); whl_sum = sum(v['bytes'] for v in whls.values())
print('System original_bytes - deb bytes =', sys_c['original_bytes'] - deb_sum, '(OFFLINE_FILES.json is', off_path.stat().st_size, 'bytes; DEBIAN_USB.sha256 is', (T / 'App/DEBIAN_USB.sha256').stat().st_size, ')')
print('Wheels original_bytes - wheel bytes =', whl_c['original_bytes'] - whl_sum)
print('System original_files', sys_c['original_files'], 'vs debs', len(debs), '| payload_entries', rp['System']['payload_entries'])
print('Wheels original_files', whl_c['original_files'], 'vs wheels', len(whls), '| payload_entries', rp['Wheels']['payload_entries'])

print()
print('=== 5. Wheels')
for k, v in sorted(whls.items()):
    stem = k.split('/', 1)[1][:-4]
    name, ver, *tags = stem.split('-')
    print(f"   {name} {ver} tags={'-'.join(tags)} bytes={v['bytes']}")

print()
print('=== 6. Debs')
rows = []
for k, v in debs.items():
    base = k.split('/', 1)[1][:-4]
    pkg, ver, arch = base.split('_')
    rows.append((pkg, ver.replace('%3a', ':'), arch, v['bytes']))
archs = {}
for r in rows: archs[r[2]] = archs.get(r[2], 0) + 1
print('count', len(rows), 'arch breakdown', archs)
print('largest 15:')
for r in sorted(rows, key=lambda r: -r[3])[:15]: print('   ', r[3], r[0], r[1], r[2])
pat = re.compile(r'^(python3|python3\.\d+|python3-venv|python3\.\d+-venv|python3-pip|python3-pip-whl|python3-setuptools-whl|python3-minimal|libpython3.*|sudo|xinit|xauth|fluxbox|xserver-xorg.*|xserver-common|x11-xserver-utils|dbus.*|network-manager.*|wpasupplicant|libreoffice.*|firmware-.*|mesa-.*|libvulkan1|vulkan-tools|libgl1.*|libegl.*|poppler-utils|linux-image.*|initramfs.*|systemd.*|libsystemd.*|libpam-systemd|udev|libc6|libc-bin|base-files|base-passwd|adduser|ca-certificates|openssl|libssl3t64|polkit.*|policykit.*|lightdm.*|gdm3|sddm|xdm|slim|nodm|wireshark.*|bubblewrap|kicad.*|default-jdk.*|openjdk.*|build-essential|gcc.*|git|nodejs|iverilog|clangd.*|fonts-.*|libllvm.*|modemmanager|ppp|isc-dhcp.*|dnsmasq.*|iwd|wireless-.*|iw|rfkill|bluez.*|cups.*|avahi.*|apparmor|ucf|debconf|dpkg|apt|libapt.*|perl.*|coinor.*|uno-libs.*|ure)$')
print('notable:')
for r in sorted(rows):
    if pat.match(r[0]): print('   ', r[0], r[1], r[2], r[3])
print('all package names:')
print(' '.join(sorted(r[0] for r in rows)))

print()
print('=== 7. App payload manifest (restored tree)')
mpath = R / 'MANIFEST.json'
man = json.loads(mpath.read_text())
print('MANIFEST.json sha256', sha(mpath), 'pinned', rp['App']['payload_manifest_sha256'], 'equal', sha(mpath) == rp['App']['payload_manifest_sha256'])
print('manifest keys', [k for k in man if k != 'files'], {k: man[k] for k in man if k != 'files' and not isinstance(man[k], (dict, list))})
print('files in manifest', len(man['files']), '| payload_entries', rp['App']['payload_entries'], '| difference', rp['App']['payload_entries'] - len(man['files']))
print('MANIFEST.json listed in its own files:', 'MANIFEST.json' in man['files'])
print('total payload bytes per manifest', sum(v['bytes'] for v in man['files'].values()))
for name, meta in rp['App']['file_chunks'].items():
    f = man['files'].get(name)
    print(f"   split App: {name} in manifest={f is not None} equal={(f and f['bytes'] == meta['bytes'] and f['sha256'] == meta['sha256'])}")
for n in ('INSTALL_LS.py', 'PREPARE_DEBIAN.sh', 'INSTALL_DEBIAN.sh', 'INSTALL_LEDGER.sh', 'START_MINIMAL_DEBIAN.sh', 'LS_XSESSION.sh', 'START_OFFICE.sh', 'INSTALL_GRAPHITE.sh', 'OFFLINE_FILES.json', 'DEBIAN_USB.sha256', 'RELEASE_PARTS.json'):
    print(f"   {n}: in payload manifest={n in man['files']}")
for n in ('INSTALL_LS.py', 'PREPARE_DEBIAN.sh'):
    a = T / 'App' / n; b = R / n
    print(f"   {n}: START_HERE App copy == restored payload copy: {sha(a) == sha(b)} ; top-level copy equal: {(T / n).exists() and sha(T / n) == sha(b)}")
print('count of .py files in manifest:', sum(1 for k in man['files'] if k.endswith('.py')))

print()
print('=== 8. Remaining download burden')
app_missing = ['Graphite_0.2a13_part_02.zip', 'Graphite_0.2a13_part_03.zip', 'Graphite_0.2a13_part_04.zip']
a = sum(all_parts[n]['bytes'] for n in app_missing)
b = sum(p['bytes'] for p in rp['Records']['parts'])
c = sum(p['bytes'] for p in rp['System']['parts'])
d = sum(p['bytes'] for p in rp['Wheels']['parts'])
print('(a) App 02+03+04:', a, [all_parts[n]['bytes'] for n in app_missing])
print('(b) Records 2 parts:', b)
print('(c) System 21 parts:', c)
print('(d) Wheels 18 parts:', d)
print('a+b:', a + b, '| a+b+c+d:', a + b + c + d, '| parts:', 3 + 2 + 21 + 18)
print('App total:', sum(p['bytes'] for p in rp['App']['parts']))
