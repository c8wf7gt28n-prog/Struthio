"""Local hardware facts for inference. No serial numbers, model load or network.

System RAM, DRM accounting and Vulkan device budgets are different observations;
they are never added together to invent a larger memory pool.
"""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time

RUNTIME_PACKAGES = ('libvulkan1', 'mesa-vulkan-drivers', 'firmware-amd-graphics',
                    'vulkan-tools', 'libstdc++6', 'libgomp1', 'libssl3t64', 'zlib1g',
                    'libzstd1', 'libgcc-s1', 'libc6')
BUILD_PACKAGES = ('build-essential', 'cmake', 'libvulkan-dev', 'glslc', 'spirv-headers')
_cache = None
_cache_at = 0.0


def read(path):
    try:return Path(path).read_text().strip()
    except (OSError,UnicodeError):return None


def integer(path):
    try:return int(read(path))
    except (TypeError,ValueError):return None


def packages():
    command = shutil.which('dpkg-query')
    if not command:return {}
    try:
        result = subprocess.run([command,'-W','-f=${Package}\t${Version}\t${db:Status-Status}\n',
                                 *RUNTIME_PACKAGES],capture_output=True,text=True,timeout=3)
        found = {}
        for line in result.stdout.splitlines():
            parts = line.split('\t')
            if len(parts)==3 and parts[2]=='installed':found[parts[0].split(':')[0]] = parts[1]
        return found
    except (OSError,subprocess.SubprocessError):return {}


def snapshot(refresh=False):
    global _cache,_cache_at
    if not refresh and _cache is not None and time.monotonic()-_cache_at < 60:
        return json.loads(json.dumps(_cache))
    cpu = read('/proc/cpuinfo') or '';blocks = [dict(line.split(':',1) for line in b.splitlines() if ':' in line)
                                               for b in cpu.split('\n\n') if b.strip()]
    normalized = [{k.strip():v.strip() for k,v in b.items()} for b in blocks]
    model = next((b['model name'] for b in normalized if 'model name' in b),platform.machine())
    physical = {(b.get('physical id','0'),b['core id']) for b in normalized if 'core id' in b}
    flags = set((normalized[0].get('flags','') if normalized else '').split())
    graphics = []
    for node in sorted(Path('/sys/class/drm').glob('renderD*')):
        device = node/'device'
        try:driver = (device/'driver').resolve().name if (device/'driver').exists() else None
        except OSError:driver = None
        graphics.append(dict(render_node='/dev/dri/'+node.name,vendor_id=read(device/'vendor'),
                             device_id=read(device/'device'),driver=driver,
                             accessible=os.access('/dev/dri/'+node.name,os.R_OK|os.W_OK),
                             reported_vram_bytes=integer(device/'mem_info_vram_total'),
                             reported_gtt_bytes=integer(device/'mem_info_gtt_total')))
    # Non-sensitive product identifiers only: serial/UUID and owner/account data are intentionally absent.
    installed = packages()
    found = dict(schema='graphite.inference-hardware/1',measured_on='CURRENT_EXECUTION_HOST',
                 machine=dict(vendor=read('/sys/class/dmi/id/sys_vendor'),product=read('/sys/class/dmi/id/product_name'),
                              version=read('/sys/class/dmi/id/product_version')),
                 cpu=dict(name=model,logical_cpus=os.cpu_count(),physical_cores=len(physical) or None,
                          features=sorted(flags & {'avx','avx2','f16c','avx_vnni','avx512f','avx512_vnni'})),
                 kernel=platform.release(),architecture=platform.machine(),graphics=graphics,
                 installed_packages=installed,missing_runtime_packages=[p for p in RUNTIME_PACKAGES if p not in installed and p!='vulkan-tools'],
                 memory_note='An integrated GPU shares system memory. DRM VRAM/GTT and Vulkan budgets are not extra RAM.',
                 owner_host_qualification='NOT_ESTABLISHED_BY_INVENTORY')
    found['fingerprint'] = hashlib.sha256(json.dumps(found,sort_keys=True).encode()).hexdigest()
    _cache,_cache_at = found,time.monotonic()
    return json.loads(json.dumps(found))


def radeon_available(profile):
    return any(g.get('vendor_id')=='0x1002' and g.get('driver')=='amdgpu' and g.get('accessible')
               for g in profile.get('graphics',[]))
