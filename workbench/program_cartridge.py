"""Inspect local iNES cartridges and hand an approved copy to native RetroArch."""
from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import threading
from pathlib import Path

from . import files_service, record_io


INSPECT = 'programs.cartridge.inspect'
LAUNCH = 'programs.cartridge.launch'
CORES = {'fceumm': 'FCEUmm', 'nestopia': 'Nestopia UE'}
SHA256 = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
FIELDS = {
    INSPECT: ({'path': files_service.REL}, ['path']),
    LAUNCH: ({'path': files_service.REL, 'expected_sha256': SHA256,
              'core': {'type': 'string', 'enum': list(CORES)}}, ['path', 'expected_sha256', 'core']),
}
SCOPES = {INSPECT: 'read', LAUNCH: 'approve'}
MAX_ROM_BYTES = 8 * 1024 * 1024


def read_rom(kernel, name):
    base = files_service.root(kernel, create=False)
    if base.is_symlink():
        raise ValueError('Cartridge Bay requires a local Files folder.')
    path = kernel.safe(name, base=base)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Choose a regular cartridge file from Files.')
        if info.st_size > MAX_ROM_BYTES:
            raise ValueError('Cartridge inspection is limited to 8 MiB.')
        data = stream.read(MAX_ROM_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) != info.st_size or info.st_mtime_ns != after.st_mtime_ns or info.st_ctime_ns != after.st_ctime_ns:
        raise ValueError('The cartridge changed while reading it. Inspect it again.')
    return data


def ines_header(data):
    if data[:4] != b'NES\x1a':
        return None, None, None, 'Choose an unpacked iNES cartridge. Other formats are unavailable in Cartridge Bay.'
    if len(data) < 16:
        return 'NES', 'iNES', None, 'The cartridge header is incomplete.'
    flags6, flags7 = data[6:8]
    if (flags7 & 0x0C) == 0x08:
        return 'NES', 'NES 2.0', None, 'NES 2.0 support is unavailable in Cartridge Bay.'
    if flags7 & 0x0F or any(data[12:16]):
        return 'NES', 'iNES', None, 'This cartridge has header flags outside the supported iNES format.'
    mapper = (flags7 & 0xF0) | (flags6 >> 4)
    trainer = 512 if flags6 & 4 else 0
    payload = 16 + trainer + data[4] * 16384 + data[5] * 8192
    if data[4] == 0 or len(data) != payload:
        return 'NES', 'iNES', mapper, 'The file length does not match the program and graphics banks declared in its iNES header.'
    return 'NES', 'iNES', mapper, None


def installed_tools():
    executable = shutil.which('retroarch')
    emulator = str(Path(executable).resolve()) if executable else None
    config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    folders = (Path('/usr/lib/x86_64-linux-gnu/libretro'), Path('/usr/lib/aarch64-linux-gnu/libretro'),
               Path('/usr/lib/libretro'), Path('/usr/lib64/libretro'), Path('/usr/lib/retroarch/cores'),
               Path('/usr/local/lib/libretro'), config / 'retroarch' / 'cores')
    cores = []
    for ident, name in CORES.items():
        candidates = (folder / f'{ident}_libretro.so' for folder in folders if folder.is_absolute())
        core = next((candidate for candidate in candidates if candidate.is_file()), None)
        if core is not None:
            cores.append({'id': ident, 'name': name, 'path': str(core.resolve())})
    return emulator, cores


def describe(name, data):
    system, form, mapper, reason = ines_header(data)
    emulator, cores = installed_tools()
    if reason:
        state = 'UNSUPPORTED'
    elif not emulator:
        state = 'TOOL_UNAVAILABLE'
        reason = 'Install native RetroArch and an NES core to play this local cartridge.'
    elif not cores:
        state = 'CORE_UNAVAILABLE'
        reason = 'RetroArch is installed. Install FCEUmm or Nestopia UE to play an NES cartridge.'
    else:
        state = 'READY'
        reason = 'Choose an installed NES core to try this iNES cartridge. Gameplay has not been checked.'
    return {'state': state, 'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'system': system, 'format': form, 'mapper': mapper, 'emulator': emulator, 'cores': cores,
            'launch_ready': state == 'READY', 'reason': reason}


def private_folder(path):
    path.mkdir(mode=0o700, exist_ok=True)
    if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError('Cartridge Bay requires a private local profile.')
    return path


def launch(kernel, record, data, core):
    profile_root = Path(kernel.state)
    if profile_root.is_symlink():
        raise ValueError('Cartridge Bay requires local Graphite state.')
    root = private_folder(profile_root / 'cartridge')
    profile = private_folder(root / f"{core['id']}-{record['sha256']}")
    lock_fd = os.open(profile / 'play.lock', os.O_RDONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(lock_fd, 'rb') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('This cartridge and core already have a session open.') from None
        for directory in ('saves', 'states', 'screenshots'):
            private_folder(profile / directory)
        # The config uses fixed paths relative to this profile and no source names.
        session = Path(tempfile.mkdtemp(prefix='session-', dir=profile))
        copy = session / 'cartridge.nes'
        copy.write_bytes(data)
        config = profile / 'retroarch.cfg'
        record_io.atomic(config, b'config_save_on_exit = "false"\n'
                         b'savefile_directory = "./saves"\n'
                         b'savestate_directory = "./states"\n'
                         b'screenshot_directory = "./screenshots"\n'
                         b'auto_overrides_enable = "false"\n'
                         b'game_specific_options = "false"\n'
                         b'history_list_enable = "false"\n'
                         b'cheevos_enable = "false"\n')
        log = session / 'retroarch.log'
        command = [record['emulator'], '--config', str(config), '-L', core['path'], str(copy)]
        with log.open('xb') as output:
            process = subprocess.Popen(command, cwd=profile, stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(lock.fileno(),))
    if process.poll() is not None:
        raise ValueError(f'RetroArch exited during startup. See {log}')
    threading.Thread(target=process.wait, daemon=True).start()
    return {'state': 'STARTED', 'pid': process.pid, 'working_copy': str(copy), 'source_sha256': record['sha256'],
            'core': core['id'], 'profile': str(profile), 'log': str(log)}


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS:
        raise ValueError('Unknown Cartridge Bay operation.')
    if operation == LAUNCH and ('approve' not in principal.scopes or principal.mode == 'Tutor'):
        raise ValueError('Launching a cartridge requires owner approval.')
    name = args['path']
    data = read_rom(kernel, name)
    record = describe(name, data)
    if operation == INSPECT:
        return record
    if record['sha256'] != args['expected_sha256']:
        raise ValueError('The cartridge changed since inspection. Inspect it again before launch.')
    if not record['launch_ready']:
        raise ValueError(record['reason'])
    core = next((item for item in record['cores'] if item['id'] == args['core']), None)
    if core is None:
        raise ValueError('The selected NES core is unavailable. Inspect the cartridge again.')
    return launch(kernel, record, data, core)
