"""The sealed room on the real runtime and a real model (0.8.7, slice A1). needs: model.

The trust lens's two hand scripts (the sealed 4B on a socket in its own network, and the inherited-key run) as a model
check beside joined_model_checks.py. In an invented, empty workspace it starts the model through Graphite's own path
(brain.model.use: both allow-lists, the private socket, its own network, the seal check before Ready) with two canaries
set in Graphite's own environment, an LLAMA_API_KEY and an HF_TOKEN such as the owner's shell may hold for another tool,
and then checks every wall again from outside, as the trust lens did by hand:

  the seal record      Ready came with a seal record: its state (SEALED, or NETWORK_NOT_SEALED with the reason and her
                       words), the transport and each check made at start
  the inherited key    chat with the canary LLAMA_API_KEY gives 401 (before 0.8.7 it gave 200)
  her key              chat with her own key gives 200 and an answer, through the private socket
  other keys           no key 401, a second random key 401; /tools 403; /slots and POST /props 501
  its environment      /proc/<runtime>/environ holds neither canary and only allow-listed names
  its network          its network namespace differs from Graphite's; it holds no internet socket at all

It passes (PASSED) when every wall holds; PASSED_NOT_SEALED_STARTED_OFFLINE when every wall holds but the computer
refused the network namespace (or the Radeon was not seen inside one), which the report says in her words. On the
ThinkPad it runs with --backend VULKAN on the first evening (open question 4). Nothing of the owner's is read: the model
file is named by its base name only; the seal record holds no path, key or process number.

    python -B -m workbench.seal_model_checks --model Qwen3.5-4B-Q4_K_M.gguf --keep <a new folder> --output seal.json [--backend CPU|VULKAN|AUTO]
"""
import argparse
import json
import os
import secrets
import time
from pathlib import Path
from unittest.mock import patch

from . import brain_seal, locations, local_brain
from .baseline import environment
from .problem_checks import invoke

NEEDS = ('model',)
CONFIG = {'context': 2048, 'threads': 4, 'memory_mb': 4480}
WALLS = ('seal_record', 'inherited_key', 'her_key', 'without_key', 'second_key', 'tools', 'slots', 'props_change',
         'environment', 'network', 'no_internet_socket')


def frozen(backend):
    """What is fixed before the model starts: the walls, what each must give, and the configuration."""
    return {'schema': 'graphite.seal-model-check/1', 'frozen_before_inference': True, 'backend': backend,
            'model_config': CONFIG, 'walls': list(WALLS),
            'expect': {'inherited_key': 401, 'her_key': 200, 'without_key': 401, 'second_key': 401, 'tools': 403,
                       'slots': 501, 'props_change': 501, 'environment': 'only allow-listed names, neither canary',
                       'network': 'its own (or NETWORK_NOT_SEALED said in words)', 'no_internet_socket': 0}}


def checks(model_path, base, output=None, backend='CPU'):
    from .engineering_kernel import Kernel, operator
    base = Path(base);base.mkdir(parents=True, exist_ok=False);home = base / 'Home';home.mkdir()
    root = base / 'Office';profile = base / 'profile'
    spec = frozen(backend);(base / 'frozen-evaluation.json').write_text(json.dumps(spec, indent=2) + '\n')
    canary_key = 'seal-canary-' + secrets.token_hex(12);canary_hf = 'hf_seal_canary_' + secrets.token_hex(12)
    value = {'state': 'IN_PROGRESS', 'model': Path(model_path).name, 'backend_requested': backend, 'config': CONFIG,
             'walls': [], 'cloud_calls': 0}

    def save():
        if output:Path(output).write_text(json.dumps(value, indent=2) + '\n')

    def wall(name, expected, got, ok, note=None):
        value['walls'].append({'name': name, 'expected': expected, 'got': got, 'ok': bool(ok), **({'note': note} if note else {})})

    env = {**environment(os.environ, root, profile), 'HOME': str(home), 'LLAMA_API_KEY': canary_key, 'HF_TOKEN': canary_hf}
    with patch.dict(os.environ, env), patch.object(Path, 'home', return_value=home):
        locations.office(root);kernel = Kernel(root);p = operator()

        def wait(job, seconds=300):
            until = time.monotonic() + seconds
            while kernel.record('jobs', job['id'])['state'] in ('Queued', 'Running') and time.monotonic() < until:time.sleep(0.2)
            result = invoke(kernel, 'brain.result', {'id': job['id']}, p)
            if result['state'] != 'Completed':raise ValueError(str(result.get('error') or result)[:600])
            return result['result']
        try:
            registered = wait(invoke(kernel, 'brain.model.add', {'path': str(Path(model_path).resolve()), 'managed_copy': False,
                                                                  'origin': 'Explicit local model file for the sealed-room check.'}, p))
            started = time.monotonic()
            try:
                wait(invoke(kernel, 'brain.model.use', {'id': registered['model_id'], 'options': {**CONFIG, 'backend': backend}}, p))
            except ValueError as exc:
                said = str(exc)
                value.update(state='FAILED', reason=said.split(brain_seal.REFUSED + ': ', 1)[-1][:400])
                save();return value
            value['activation_seconds'] = round(time.monotonic() - started, 3)
            worker = local_brain.get(kernel, 'worker', {})
            seal = worker.get('seal') or {}
            value.update(backend=worker.get('backend'), transport=seal.get('transport'), seal_state=seal.get('state'),
                         network_reason=seal.get('network_reason'), words=brain_seal.words(seal), how_i_know=brain_seal.fold(seal),
                         seal_digest=seal.get('digest'), checks_at_start=seal.get('checks'))
            wall('seal_record', 'a seal record with every check passed', seal.get('state'),
                 bool(seal) and all(c['ok'] for c in seal.get('checks', []) if c['name'] != 'network'))
            key = Path(worker['key_file']).read_text().strip()
            chat = json.dumps({'messages': [{'role': 'user', 'content': 'Reply with the word ready.'}], 'max_tokens': 4,
                               'temperature': 0, 'chat_template_kwargs': local_brain.TEMPLATE_OPTIONS}).encode()

            def asked(method, path, sent, body=None):
                try:return brain_seal.exchange(worker, method, path, body, sent, timeout=60.0, limit=65536)
                except OSError as exc:return type(exc).__name__, b''
            status, _ = asked('POST', '/v1/chat/completions', canary_key, chat)
            wall('inherited_key', 401, status, status == 401, 'an LLAMA_API_KEY set in Kas\'s own environment')
            began = time.monotonic();status, raw = asked('POST', '/v1/chat/completions', key, chat)
            answer = None
            if status == 200:
                try:answer = json.loads(raw)['choices'][0]['message'].get('content')
                except (ValueError, KeyError, IndexError, TypeError):answer = None
            wall('her_key', 200, status, status == 200 and isinstance(answer, str) and answer.strip() != '',
                 'answer %r in %.2f s' % (answer, time.monotonic() - began))
            for name, method, path, want, keyed in brain_seal.HTTP_CHECKS:
                sent = key if keyed is True else secrets.token_urlsafe(32) if keyed == 'SECOND' else None
                body = chat if path == '/v1/chat/completions' else b'{}' if method == 'POST' else None
                status, _ = asked(method, path, sent, body)
                wall(name, want, status, status == want)
            pid = brain_seal.runtime_pid(worker['pid'])
            if pid is None:
                wall('environment', 'readable', None, False, 'the runtime process was not found');wall('network', 'its own', None, False)
                wall('no_internet_socket', 0, None, False)
            else:
                names = brain_seal.environment_names(pid)
                extra = [n for n in names if not brain_seal.allowed_name(n, worker.get('backend'))]
                wall('environment', 'only allow-listed names, neither canary', names,
                     not extra and 'LLAMA_API_KEY' not in names and 'HF_TOKEN' not in names)
                own = brain_seal.network_namespace(pid) != brain_seal.network_namespace()
                wall('network', 'its own', 'its own' if own else 'shared', own or seal.get('state') == 'NETWORK_NOT_SEALED',
                     None if own else 'NETWORK_NOT_SEALED: ' + str(seal.get('network_reason')))
                sockets = brain_seal.inet_sockets(pid)
                wall('no_internet_socket', 0, len(sockets), not sockets)
            failed = [w['name'] for w in value['walls'] if not w['ok']]
            value['state'] = 'FAILED' if failed else 'PASSED' if seal.get('state') == 'SEALED' else 'PASSED_NOT_SEALED_STARTED_OFFLINE'
            if failed:value['failed'] = failed
            save();return value
        finally:
            local_brain.stop(kernel, 'SEAL_CHECK_FINISHED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True);parser.add_argument('--keep', type=Path, required=True)
    parser.add_argument('--output', type=Path);parser.add_argument('--backend', choices=('CPU', 'VULKAN', 'AUTO'), default='CPU')
    args = parser.parse_args()
    value = checks(args.model, args.keep, args.output, args.backend)
    print(json.dumps({'state': value['state'], 'backend': value.get('backend'), 'seal': value.get('seal_state'),
                      'words': value.get('words'), 'walls': [(w['name'], w['got'], w['ok']) for w in value['walls']],
                      **({'reason': value['reason']} if value.get('reason') else {})}))
    return 0 if value['state'].startswith('PASSED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
