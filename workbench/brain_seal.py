"""The sealed room: Kas's model can only answer (0.8.7, slice A1).

"The model proposes; the system disposes." These walls make sure that answering is all her model can do. Every wall is
checked each time the model starts, before it is marked Ready, by asking the server and reading its process, never the
model itself:

1. Its launch line comes from an allow-list (lint). Agent tools (a shell among them), MCP, downloads, prompt logs, slot
   files, extra endpoints and a key on the command line are refused by name, the names taken from the b11669 help text;
   anything else that is not on the list is refused too. --offline is always there.
2. Its environment comes from an allow-list: PATH, the locale and its own library folder; for Vulkan, XDG_RUNTIME_DIR
   and a shader cache under Graphite's own state. A key the owner's shell sets for another tool (LLAMA_API_KEY,
   HF_TOKEN), GGML_BACKEND_PATH, LLAMA_CACHE, debug switches and proxies never reach it.
3. It listens on a private socket in a 0700 folder (loopback only where no socket can be had) and knows one key, hers,
   kept in a file.
4. It has its own empty network: brain_worker._child_setup unshares a user and a network namespace before exec. Where
   the computer refuses, NETWORK_NOT_SEALED is recorded and said in words, and the model still starts offline.
5. The seal check (check()): /tools refused, /slots and POST /props not served, chat refused without her key and with a
   second key, its network its own, its environment only allowed names, no connection out and no network port open.
   A failure means the model is not Ready, and she says why in one line.

Standard library only: brain_worker imports this in the supervisor process.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import secrets
import socket
import sys
import tempfile
from pathlib import Path

SCHEMA = 'graphite.model-seal/1'
REFUSED = 'MODEL_SEAL_REFUSED'
SOCKET_NAME = 'm.sock'
SOCKET_LIMIT = 107  # bytes in a UNIX socket path (sun_path less its closing zero)
NOT_SEALED_MARK = 'GRAPHITE_NETWORK_NOT_SEALED'  # what brain_worker writes to the runtime log when the computer refuses
SEALED_WORDS = 'Sealed: it can only answer. No tools, no network, only the key I made, and only Graphite can reach it.'
NOT_SEALED_WORDS = 'Not sealed from the network on this computer; started offline.'
PROCESSOR_SEALED = 'Use the processor, sealed'  # open question 4's default: the sealed processor one press away


class SealRefused(ValueError):
    """The model is not Ready: one wall did not hold. The message is her one line, after the code."""

    def __init__(self, check, why):
        self.check = check
        self.words = "I didn't start the model: " + why + '. Nothing was asked of it.'
        super().__init__(REFUSED + ': ' + self.words)


# ---------------------------------------------------------------------------------------------- 1. the launch line

_INT = re.compile(r'^[0-9]{1,7}$')


def _number(value):
    return bool(_INT.match(value))


def _path(value):
    """An absolute local path: never a URL, never two lines."""
    return (os.path.isabs(value) and '\n' not in value and '\x00' not in value
            and not re.match(r'^[A-Za-z][A-Za-z0-9+.-]*://', value))


def _host(value):
    """Loopback, or a private socket path ending in .sock that fits the socket limit. Never a list, never 0.0.0.0."""
    return value == '127.0.0.1' or (_path(value) and value.endswith('.sock') and len(os.fsencode(value)) <= SOCKET_LIMIT)


# Every argument Graphite may give the runtime, with the shape of its value (None: a switch). Closed: anything else is
# refused. --checkpoint-min-step is admitted for slice A2's launch line (design 4.2); nothing else is open for it.
ALLOWED = {
    '--model': _path, '--host': _host, '--port': lambda v: _number(v) and 0 < int(v) < 65536, '--api-key-file': _path,
    '--ctx-size': _number, '--threads': _number, '-ngl': lambda v: v == 'auto' or _number(v), '--parallel': _number,
    '--threads-http': _number, '--batch-size': _number, '--ubatch-size': _number, '--cache-ram': _number,
    '--ctx-checkpoints': _number, '--checkpoint-min-step': _number, '--fit': lambda v: v in ('on', 'off'),
    '--load-mode': lambda v: v == 'none', '--device': lambda v: v == 'none' or bool(re.fullmatch(r'Vulkan[0-9]{1,2}', v)),
    '--no-cache-idle-slots': None, '--no-webui': None, '--no-ui-mcp-proxy': None, '--no-slots': None,
    '--no-context-shift': None, '--no-warmup': None, '--offline': None}
REQUIRED = ('--model', '--host', '--api-key-file', '--offline', '--no-slots', '--no-webui', '--no-ui-mcp-proxy')

# Refused by name, every alias as `llama-server --help` of b11669 prints it (b087d/synth/help_b11669.txt), with the reason
# she gives. The list names the dangerous ones; the allow-list above is what keeps everything else out.
FORBIDDEN_GROUPS = {
    'AGENT_TOOLS': ('it would turn on agent tools, a shell among them',
                    ('--tools', '--tools-runtime', '-ag', '--agent', '--mcp-servers-config', '--mcp-servers-json',
                     '--ui-mcp-proxy', '--webui-mcp-proxy')),
    'DOWNLOADS': ('it would let the runtime download from the internet',
                  ('-mu', '--model-url', '-dr', '--docker-repo', '-hf', '-hfr', '--hf-repo', '-hff', '--hf-file', '-hft',
                   '--hf-token', '-hfd', '-hfrd', '--hf-repo-draft', '--spec-draft-hf', '-mmu', '--mmproj-url',
                   '--mmproj-auto', '-cl', '--cache-list', '--embd-gemma-default', '--fim-qwen-1.5b-default',
                   '--fim-qwen-3b-default', '--fim-qwen-7b-default', '--fim-qwen-7b-spec', '--fim-qwen-14b-spec',
                   '--fim-qwen-30b-default', '--gpt-oss-20b-default', '--gpt-oss-120b-default',
                   '--vision-gemma-4b-default', '--vision-gemma-12b-default')),
    'NETWORK': ('it would open the runtime to the network',
                ('--rpc', '--reuse-port', '--cors-origins', '--cors-methods', '--cors-headers', '--cors-credentials',
                 '--ssl-key-file', '--ssl-cert-file')),
    'WRITES_TO_DISK': ('it would write prompts or model state to disk',
                       ('--log-prompts-dir', '--slot-save-path', '--log-file', '-lcd', '--lookup-cache-dynamic')),
    'VERBOSE_LOGS': ('it would write what is asked into its log',
                     ('-v', '--verbose', '--log-verbose', '-lv', '--verbosity', '--log-verbosity')),
    'ENDPOINTS': ('it would open more doors than answering',
                  ('--props', '--metrics', '--slots', '--path', '--media-path', '--ui', '--webui', '--ui-config',
                   '--webui-config', '--ui-config-file', '--webui-config-file', '--api-prefix', '--embedding',
                   '--embeddings', '--rerank', '--reranking', '--lora-init-without-apply')),
    'OTHER_MODELS': ('it would change which model or template answers',
                     ('--models-dir', '--models-preset', '--models-max', '--models-autoload', '--lora', '--lora-scaled',
                      '--control-vector', '--control-vector-scaled', '--control-vector-layer-range', '-md',
                      '--model-draft', '--spec-draft-model', '-mm', '--mmproj', '--chat-template',
                      '--chat-template-file', '--override-kv', '--spec-default')),
    'KEY_ON_COMMAND_LINE': ('it would put a key on the command line, where other programs can read it', ('--api-key',)),
    'RUNS_PROGRAMS': ('it would let the runtime run other programs', ('--video-ffmpeg-dir',)),
    'READS_FILES': ('it would let the runtime read files I did not choose',
                    ('--grammar-file', '-jf', '--json-schema-file', '-lcs', '--lookup-cache-static')),
}
FORBIDDEN = {name: group for group, (_, names) in FORBIDDEN_GROUPS.items() for name in names}


def _refuse_argument(token, why):
    raise SealRefused('launch_line', 'its launch line holds ' + token + ', and ' + why)


def lint(arguments):
    """Check the runtime's arguments (without the program itself) against the allow-list. Returns what the seal
    record keeps (the count and a digest of the names and non-path values); raises SealRefused otherwise."""
    args = list(arguments)
    seen = []
    shape = []
    index = 0
    while index < len(args):
        token = args[index]
        if not isinstance(token, str):
            _refuse_argument(repr(token), 'it is not on my list')
        if token not in ALLOWED:
            # The runtime's parser takes --name=value and reads _ as - in long names: refuse those spellings by name too.
            name = token.split('=', 1)[0]
            name = name.replace('_', '-') if name.startswith('--') else name
            group = FORBIDDEN.get(token) or FORBIDDEN.get(name)
            _refuse_argument(token[:80], FORBIDDEN_GROUPS[group][0] if group else 'it is not on my list')
        if token in seen:
            _refuse_argument(token, 'it is given twice')
        seen.append(token)
        check = ALLOWED[token]
        if check is None:
            shape.append(token)
            index += 1
            continue
        if index + 1 >= len(args) or not isinstance(args[index + 1], str) or not check(args[index + 1]):
            _refuse_argument(token, 'its value is not one I allow')
        value = args[index + 1]
        shape.append([token, '<path>' if check in (_path, _host) and value != '127.0.0.1' else '<port>' if token == '--port'
                      else value])
        index += 2
    missing = [name for name in REQUIRED if name not in seen]
    if missing:
        raise SealRefused('launch_line', 'its launch line lacks ' + missing[0])
    host = args[args.index('--host') + 1]
    if host.endswith('.sock') and '--port' in seen:
        _refuse_argument('--port', 'a private socket takes no port')
    if host == '127.0.0.1' and '--port' not in seen:
        raise SealRefused('launch_line', 'its launch line names loopback without a port')
    return {'arguments': len(args), 'digest': hashlib.sha256(json.dumps(shape).encode()).hexdigest()}


# ---------------------------------------------------------------------------------------------- 2. the environment

LOCALE = re.compile(r'^(LANG|LANGUAGE|LC_[A-Z]+)$')
VULKAN_NAMES = ('XDG_RUNTIME_DIR', 'MESA_SHADER_CACHE_DIR')
WINDOWS_NAMES = ('SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'PATHEXT', 'NUMBER_OF_PROCESSORS',
                 'PROCESSOR_ARCHITECTURE')  # what a Windows process needs to start; untested here


def allowed_name(name, backend=None):
    """Whether the runtime may be given this environment variable (for this backend; any backend when None)."""
    key = name.upper() if os.name == 'nt' else name
    if key in ('PATH', 'LD_LIBRARY_PATH') or LOCALE.match(key):
        return True
    if key in VULKAN_NAMES:
        return backend in (None, 'VULKAN')
    return os.name == 'nt' and key in WINDOWS_NAMES


def environment(source, backend='CPU', library=None, cache=None):
    """The runtime's whole environment, built from the allow-list, never from what the owner's shell happens to hold:
    PATH and the locale from `source`, LD_LIBRARY_PATH set to the runtime's own folder, and for Vulkan XDG_RUNTIME_DIR
    and MESA_SHADER_CACHE_DIR, a shader cache Graphite names under its own state (created 0700)."""
    env = {key: value for key, value in source.items()
           if (key == 'PATH' or LOCALE.match(key) or (os.name == 'nt' and key.upper() in WINDOWS_NAMES))}
    env.setdefault('PATH', os.defpath)
    if library is not None and os.name != 'nt':
        env['LD_LIBRARY_PATH'] = str(library)
    if backend == 'VULKAN':
        if source.get('XDG_RUNTIME_DIR'):
            env['XDG_RUNTIME_DIR'] = source['XDG_RUNTIME_DIR']
        if cache is not None:
            Path(cache).mkdir(parents=True, mode=0o700, exist_ok=True)
            env['MESA_SHADER_CACHE_DIR'] = str(cache)
    return env


def child_environment(source):
    """What the supervisor (brain_worker) hands the native runtime: its own environment less anything off the list
    (PYTHONPATH, which the supervisor itself needs, among them)."""
    return {key: value for key, value in source.items() if allowed_name(key)}


# ---------------------------------------------------------------------------------------------- 3. the private socket

def socket_path(base):
    """Where the runtime listens: `base`/m.sock (base is the start's own 0700 folder) when the path fits the socket
    limit, else m.sock in a short 0700 folder of its own under XDG_RUNTIME_DIR or the temporary folder. Returns
    (path, folder made for it or None); (None, None) where no socket can be had (Windows), which means loopback."""
    if os.name == 'nt' or not hasattr(socket, 'AF_UNIX'):
        return None, None
    path = Path(base) / SOCKET_NAME
    if len(os.fsencode(str(path))) <= SOCKET_LIMIT:
        return path, None
    for parent in (os.environ.get('XDG_RUNTIME_DIR'), tempfile.gettempdir()):
        if not parent or not os.path.isdir(parent):
            continue
        folder = Path(tempfile.mkdtemp(prefix='graphite-', dir=parent))  # 0700
        if len(os.fsencode(str(folder / SOCKET_NAME))) <= SOCKET_LIMIT:
            return folder / SOCKET_NAME, folder
        folder.rmdir()
    return None, None


def network_seal_possible():
    """Whether this system has network namespaces to try (Linux). Whether the computer allows them is learnt by trying."""
    return sys.platform.startswith('linux')


class UnixConnection(http.client.HTTPConnection):
    """HTTP over the worker's private socket. No proxy, no redirect, nothing on the network."""

    def __init__(self, path, timeout):
        super().__init__('localhost', timeout=timeout)
        self.unix_path = str(path)

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self.unix_path)
        except BaseException:
            sock.close()
            raise
        self.sock = sock


def connection(worker, timeout):
    if worker.get('socket'):
        return UnixConnection(worker['socket'], timeout)
    return http.client.HTTPConnection('127.0.0.1', int(worker['port']), timeout=timeout)


def exchange(worker, method, path, body=None, key=None, timeout=10.0, limit=65536):
    """One request to the worker; returns (status, at most limit+1 bytes of the body). Raises OSError or
    http.client.HTTPException when it does not answer."""
    headers = {'Content-Type': 'application/json'}
    if key is not None:
        headers['Authorization'] = 'Bearer ' + key
    conn = connection(worker, timeout)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        return response.status, response.read(limit + 1)
    finally:
        conn.close()


# ---------------------------------------------------------------------------------------------- 5. the seal check

def runtime_pid(supervisor):
    """The native runtime: the supervisor's (brain_worker's) child. None where it cannot be read."""
    if not sys.platform.startswith('linux'):
        return None
    try:
        children = Path('/proc', str(supervisor), 'task', str(supervisor), 'children').read_text().split()
        if children:
            return int(children[0])
    except (OSError, ValueError):
        pass
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[1]) == int(supervisor):
                return int(path.name)
        except (OSError, ValueError, IndexError):
            continue
    return None


def environment_names(pid):
    raw = Path('/proc', str(pid), 'environ').read_bytes()
    return sorted({item.split(b'=', 1)[0].decode('utf-8', 'replace') for item in raw.split(b'\0') if item})


def network_namespace(pid='self'):
    return os.readlink('/proc/%s/ns/net' % pid)


def _address(text):
    """(is loopback, is unspecified, port) for one /proc/net address field (hex, as the kernel prints it)."""
    host, port = text.split(':')
    raw = bytes.fromhex(host)
    if len(raw) == 4:
        raw = raw[::-1]
    else:
        raw = b''.join(raw[i:i + 4][::-1] for i in range(0, 16, 4))
    unspecified = not any(raw)
    if len(raw) == 4:
        loopback = raw[0] == 127
    else:
        loopback = raw == b'\0' * 15 + b'\1' or (raw[:12] == b'\0' * 10 + b'\xff\xff' and raw[12] == 127)
    return loopback, unspecified, int(port, 16)


def inet_sockets(pid):
    """The runtime's own internet sockets, read from its file table and its own network's tables: a list of
    {protocol, state, local_loopback, local_port, remote_loopback, remote_unspecified, remote_port}."""
    inodes = set()
    for fd in Path('/proc', str(pid), 'fd').iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith('socket:['):
            inodes.add(target[8:-1])
    found = []
    for protocol in ('tcp', 'tcp6', 'udp', 'udp6'):
        try:
            lines = Path('/proc', str(pid), 'net', protocol).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 10 or fields[9] not in inodes:
                continue
            local, remote = _address(fields[1]), _address(fields[2])
            found.append({'protocol': protocol, 'state': fields[3], 'local_loopback': local[0], 'local_port': local[2],
                          'remote_loopback': remote[0], 'remote_unspecified': remote[1], 'remote_port': remote[2]})
    return found


def _reached_out(sockets):
    return [s for s in sockets if s['remote_port'] and not s['remote_unspecified'] and not s['remote_loopback']]


def _listens(sockets):
    # TCP LISTEN (0A), or a UDP socket bound to a port and not connected: a way in other than her private socket, or what
    # an outward attempt leaves behind in its own empty network (a failed UDP connect still binds a port). The pinned
    # runtime behind its socket holds no internet socket at all (trust lens, measured), so either refuses Ready.
    return [s for s in sockets if s['local_port'] and (s['state'] == '0A' or (s['protocol'].startswith('udp')
                                                                              and not s['remote_port']))]


def not_sealed_reason(log):
    """Why the computer refused the network namespace, as brain_worker wrote it into the runtime log."""
    try:
        with Path(log).open('rb') as stream:
            head = stream.read(65536).decode('utf-8', 'replace')
    except (OSError, TypeError):
        return None
    match = re.search(NOT_SEALED_MARK + r': ([A-Z0-9_]+)', head)
    return 'COMPUTER_REFUSED: ' + match.group(1) if match else None


HTTP_CHECKS = (
    # name, method, path, the answer that keeps it sealed, sent with her key?
    ('tools', 'GET', '/tools', 403, True),
    ('slots', 'GET', '/slots', 501, True),
    ('props_change', 'POST', '/props', 501, True),
    ('without_key', 'POST', '/v1/chat/completions', 401, False),
    ('second_key', 'POST', '/v1/chat/completions', 401, 'SECOND'),
)
REFUSALS = {
    'tools': 'it offers built-in tools',
    'slots': 'it lets its slots be read',
    'props_change': 'it lets its settings be changed',
    'without_key': 'it answers without my key',
    'second_key': "it accepted a key I didn't make",
    'environment': 'it was given settings outside my list ({names})',
    'reached_out': 'it reached out to the network',
    'listens': 'it opened a network socket of its own beside its private socket',
    'network': 'it shares Graphite\'s network although I gave it its own',
    'runtime_process': 'I could not see its own process to check it',
    'transport': 'it is not behind its private socket',
}
NO_ANSWER = 'it did not answer my checks'


def check(worker, log=None, backend='CPU'):
    """The seal check, run every time the model starts, before Ready. Returns the seal record (no paths, no key, no
    pid in what the digest covers); raises SealRefused with her one line when a wall does not hold."""
    key = Path(worker['key_file']).read_text().strip()
    chat = json.dumps({'messages': [{'role': 'user', 'content': '.'}], 'max_tokens': 1, 'temperature': 0}).encode()
    checks = []
    for name, method, path, want, keyed in HTTP_CHECKS:
        sent = key if keyed is True else secrets.token_urlsafe(32) if keyed == 'SECOND' else None
        body = chat if path == '/v1/chat/completions' else b'{}' if method == 'POST' else None
        try:
            status, _ = exchange(worker, method, path, body, sent, timeout=10.0, limit=4096)
        except (OSError, http.client.HTTPException):
            status = 'NO_ANSWER'
        checks.append({'name': name, 'asked': method + ' ' + path, 'expected': want, 'got': status, 'ok': status == want})
        if status == 'NO_ANSWER':
            raise SealRefused(name, NO_ANSWER)
        if status != want:
            raise SealRefused(name, REFUSALS[name])
    transport = 'PRIVATE_SOCKET' if worker.get('socket') else 'LOOPBACK'
    requested = bool(worker.get('network_seal_requested'))
    names = None
    if sys.platform.startswith('linux'):
        pid = runtime_pid(worker['pid'])
        if pid is None:
            raise SealRefused('runtime_process', REFUSALS['runtime_process'])
        try:
            names = environment_names(pid)
            own = network_namespace(pid) != network_namespace()
            sockets = inet_sockets(pid)
        except (OSError, ValueError):
            raise SealRefused('runtime_process', REFUSALS['runtime_process']) from None
        extra = [name for name in names if not allowed_name(name, backend)]
        checks.append({'name': 'environment', 'asked': 'its environment', 'expected': 'only names on my list',
                       'got': names, 'ok': not extra})
        if extra:
            raise SealRefused('environment', REFUSALS['environment'].format(names=', '.join(extra[:4])))
        out = _reached_out(sockets)
        checks.append({'name': 'reached_out', 'asked': 'its connections', 'expected': 'none out', 'got': len(out),
                       'ok': not out})
        if out:
            raise SealRefused('reached_out', REFUSALS['reached_out'])
        doors = _listens(sockets) if transport == 'PRIVATE_SOCKET' else [
            s for s in _listens(sockets) if not s['local_loopback'] or s['local_port'] != int(worker.get('port') or 0)]
        checks.append({'name': 'listens', 'asked': 'its network ports', 'expected': 'none open', 'got': len(doors),
                       'ok': not doors})
        if doors:
            raise SealRefused('listens', REFUSALS['listens'])
        if own:
            network, reason = 'OWN_EMPTY_NETWORK', None
        elif requested:
            # The child cannot leave a namespace it was given; sharing Graphite's means the computer refused one.
            network, reason = 'NETWORK_NOT_SEALED', not_sealed_reason(log) or 'COMPUTER_REFUSED: UNKNOWN'
        else:
            network, reason = 'NETWORK_NOT_SEALED', worker.get('network_seal_reason') or 'NOT_ASKED'
        checks.append({'name': 'network', 'asked': 'its network', 'expected': 'its own',
                       'got': 'its own' if own else 'shared', 'ok': own})
    else:
        network, reason = 'NETWORK_NOT_SEALED', 'NO_NETWORK_NAMESPACES_ON_THIS_SYSTEM'
        checks.append({'name': 'network', 'asked': 'its network', 'expected': 'its own', 'got': 'not readable here',
                       'ok': False})
    if transport == 'LOOPBACK' and network == 'OWN_EMPTY_NETWORK':
        # Loopback inside its own network is unreachable from Graphite; it answered, so something is not as built.
        raise SealRefused('transport', REFUSALS['transport'])
    record = {'schema': SCHEMA, 'state': 'SEALED' if network == 'OWN_EMPTY_NETWORK' else 'NETWORK_NOT_SEALED',
              'network': network, 'network_reason': reason, 'transport': transport, 'backend': backend,
              'offline': True, 'checks': checks, 'environment_names': names,
              'launch_line': worker.get('launch_line'), 'runtime': {k: (worker.get('runtime') or {}).get(k)
                                                                  for k in ('build', 'platform', 'archive_sha256')}}
    record['digest'] = digest(record)
    return record


def digest(record):
    """What the qualification key takes from the seal (design 5.5): every wall's outcome, the names it was given, the
    launch line's shape and the runtime; never a path, the key or a process number."""
    kept = {key: record.get(key) for key in ('schema', 'state', 'network', 'transport', 'backend', 'offline',
                                              'environment_names', 'launch_line', 'runtime')}
    kept['checks'] = [[c['name'], c['expected'], c['got'] if c['name'] != 'environment' else None, c['ok']]
                      for c in record.get('checks') or []]
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------------------------- her words

FOLD = {
    'tools': 'built-in tools: asked, refused',
    'slots': 'its slots: asked, not served',
    'props_change': 'changing its settings: asked, not served',
    'without_key': 'without my key: refused',
    'second_key': 'a second key: refused',
    'reached_out': 'connections out: none',
    'listens': 'network sockets of its own: none',
}


def words(seal):
    """The one line under the model's name, or None when no seal is recorded (a model started before 0.8.7)."""
    if not isinstance(seal, dict):
        return None
    return SEALED_WORDS if seal.get('state') == 'SEALED' else NOT_SEALED_WORDS


def fold(seal):
    """'How I know': each check made at start and its result, in words."""
    if not isinstance(seal, dict):
        return []
    lines = []
    for item in seal.get('checks') or []:
        if item['name'] in FOLD:
            lines.append(FOLD[item['name']])
        elif item['name'] == 'environment':
            lines.append('its settings from me: %d names, all on my list' % len(item['got'] or []))
        elif item['name'] == 'network':
            lines.append('network: none, its own empty network' if item['ok'] else
                         'network: not sealed on this computer; started offline, with no network features')
    lines.append('reached through a private socket only' if seal.get('transport') == 'PRIVATE_SOCKET'
                 else "reached on this computer's loopback only, with my key")
    lines.append('its launch line: every argument on my list; no tools, no downloads, no prompt log')
    return lines


def processor_offered(seal):
    """Open question 4's default: the Radeon runs without its own network only when it could not be seen inside one;
    then the sealed processor is one press away. Not offered when the computer refuses namespaces altogether."""
    return isinstance(seal, dict) and seal.get('backend') == 'VULKAN' and seal.get('state') != 'SEALED' \
        and seal.get('network_reason') == 'VULKAN_NOT_SEEN_IN_ITS_OWN_NETWORK'
