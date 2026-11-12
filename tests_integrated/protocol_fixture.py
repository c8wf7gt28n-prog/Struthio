"""Explicit HTTP protocol test double. This is not GGUF model inference."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from unittest.mock import patch
from workbench import local_brain as brain


class ProtocolWorker:
    def __init__(self, kernel, base):
        self.kernel = kernel; self.base = Path(base); self.after_delta = None; self.finish = 'stop'; self.done = True
        self.override = None; self.token_count = 400; self.requests = []; fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def do_POST(self):
                if self.headers.get('Authorization') != 'Bearer protocol-fixture-key':
                    self.send_error(401); return
                size = int(self.headers.get('Content-Length', 0)); data = json.loads(self.rfile.read(size)); fixture.requests.append((self.path, data))
                if self.path == '/apply-template': result = {'prompt': json.dumps(data['messages'])}
                elif self.path == '/tokenize': result = {'tokens': [0] * fixture.token_count}
                elif self.path == '/v1/chat/completions':
                    self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                    try:
                        content = fixture.reply(data['messages'])
                        for index in range(0, len(content), 41):
                            value = {'choices': [{'index': 0, 'delta': {'content': content[index:index + 41]}, 'finish_reason': None}]}
                            self.wfile.write(('data: ' + json.dumps(value) + '\n\n').encode()); self.wfile.flush()
                            if index == 0 and fixture.after_delta: fixture.after_delta()
                        value = {'choices': [{'index': 0, 'delta': {}, 'finish_reason': fixture.finish}], 'usage': {'completion_tokens': 42}}
                        self.wfile.write(('data: ' + json.dumps(value) + '\n\n').encode())
                        if fixture.done: self.wfile.write(b'data: [DONE]\n\n')
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError): pass
                    return
                else: self.send_error(404); return
                raw = json.dumps(result).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)

    def reply(self, messages):
        if self.override is not None: return self.override
        data = json.loads(messages[-1]['content']); props = data['output_contract']['properties']
        if 'base_sha256' in props:
            base = data['edit_base']['text']; start = base.index('blue')
            result = {'text': 'A draft replacing blue with black.', 'base_sha256': data['edit_base']['base_sha256'],
                'edits': [{'start': start, 'end': start + 4, 'old': 'blue', 'new': 'black'}]}
        elif 'actions' in props:
            result = {'text': 'Read the selected project.', 'interpretation': 'Inspect the project without changing it.', 'questions': [],
                      'actions': [{'operation': 'projects.get', 'arguments': {'id': '1' * 32}}]}
        elif 'needs_clarification' in props:
            result = {'text': 'The target and units are missing.', 'needs_clarification': True, 'questions': ['Which dimension and units?']}
        else:
            sources = [p for p in data['passages'] if p['kind'] in ('SOURCE', 'LEDGER_SOURCE', 'ENGINEERING_EVIDENCE')]
            result = {'state': 'ANSWER' if sources else 'INSUFFICIENT_EVIDENCE', 'text': 'The clock uses a 330 ohm resistor.' if sources else 'The selected passages do not say.',
                'citations': [sources[0]['alias']] if sources else []}
        return json.dumps(result)

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        key = self.base / 'protocol-key'; key.write_text('protocol-fixture-key'); key.chmod(0o600)
        weights = self.base / 'protocol-fixture.gguf'; weights.write_bytes(b'NOT_A_REAL_GGUF_PROTOCOL_FIXTURE_ONLY')
        ident = 'a' * 64
        self.worker = {'_protocol_fixture': True, 'model_id': ident, 'pid': 99999999, 'start': 'fixture-only',
            'port': self.server.server_port, 'key_file': str(key), 'context': 8192, 'load_seconds': .01,
            'runtime': {'build': 'PROTOCOL_TEST_DOUBLE_NOT_GGUF_INFERENCE', 'backend': 'TEST_ONLY'}}
        brain.put(self.kernel, 'model.' + ident, {'id': ident, 'files': [{'path': str(weights), 'name': weights.name,
            'bytes': weights.stat().st_size, 'sha256': hashlib.sha256(weights.read_bytes()).hexdigest()}]})
        brain.put(self.kernel, 'selection', {'model_id': ident}); brain.put(self.kernel, 'worker', self.worker)
        self.live = patch.object(brain, 'worker_live', side_effect=lambda w: bool(w and w.get('_protocol_fixture'))); self.live.start()
        self.launch = patch.object(self.kernel, 'launch', return_value=None); self.launch.start()
        return self

    def __exit__(self, *args):
        self.launch.stop(); self.live.stop(); self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
