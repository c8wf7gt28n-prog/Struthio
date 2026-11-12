"""Offline-only image inspection. This module has no transport/discovery API."""
import hashlib
from . import elf_image,boot_image

VIRT_REGIONS=((0x80000000,0x200000),(0x82000000,0x4000000))


def plan(data,profile):
    if not isinstance(data,bytes) or len(data)>elf_image.MAX_FILE_BYTES:raise ValueError('IMAGE_SIZE')
    identity={'schema':'arc.offline-image-plan/1','image_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'profile':profile,'physical_write_enabled':False,'device_enumerations':0,'device_opens':0,'target_image_qualified':False,'board_boot_qualified':False,'fabrication':'HOLD','flashing':'HOLD'}
    if profile=='qemu-virt-rv64-existing':
        geometry=elf_image.inspect(data,allowed_regions=VIRT_REGIONS)
        return {**identity,'state':'PLAN_ACCEPTED','qualification':'GENERIC_VIRTUAL_GEOMETRY_ONLY','geometry':geometry,'source':'workbench/first_stage_tools.py REGIONS and software/boot/first_stage/qemu_virt.ld','physical_addresses_authorized':False}
    if profile=='r10-f133-board':
        return {**identity,'state':'BLOCKED','reason':'Exact F133 load regions, startup binding and recovery are unqualified; no address defaults are inferred.','load_regions':None,'commands':[]}
    if profile=='egon-format-tool-limit':
        geometry=boot_image.inspect(data,max_image_bytes=boot_image.HOST_RESOURCE_LIMIT)
        return {**identity,'state':'PLAN_ACCEPTED','qualification':'EGON_FORMAT_ONLY_HOST_RESOURCE_CEILING','geometry':geometry,'silicon_load_limit':None,'physical_addresses_authorized':False}
    raise ValueError('UNKNOWN_OFFLINE_PROFILE')
