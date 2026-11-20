"""A stand-in for the local model worker, for smoke scripts and later checks only (0.8.7, slice E0). Never wired into the app.

Two stand-ins and one stand-in kind:

FakeWorker(script, time=VirtualTime(), ...)
    A turns.ask port in process. Each complete() takes the next step of the script: a string (the answer), a dict
    {'text', 'ms' (latency; default from the read and write rates), 'finish' ('stop' or 'length'), 'fail' (a PortError
    code), 'cancel' (True: no answer by the deadline, turns.Late)} or a callable(messages, grammar) giving either. It keeps
    its last prompt like a server with prompt reuse (`cache=True`): kept() and cache_n are the shared token prefix, so a
    second question of the same kind re-reads only message 4. Time is virtual: a step's latency advances `time` and a late
    one is returned with its elapsed time past the deadline, as a real late answer is (ask() records and checks it, and
    gives the fallback). `calls` holds every request it saw: messages, grammar, answer cap, deadline, odds.

FakeServer(script, context=4096)
    A loopback HTTP stand-in for llama-server's five endpoints Graphite uses (/health, /props, /apply-template, /tokenize,
    /v1/chat/completions), with the Bearer key check. `worker()` gives a worker record local_brain.request accepts, so a
    check can run ask() through turns.LocalPort and local_brain.completion with no model. `bodies` holds every request
    body as sent (a grammar in the body, cache_prompt, t_max_predict_ms, and whether a forgotten text is sent again).
    A step may also carry 'sleep_ms' (real time, kept short) to make the client's timeout fire. (A3) A request with
    "stream": true is answered as llama-server streams: one SSE event per token, 'token_ms' (real time) apart, the
    timings in the last event, then [DONE]; `closed` counts streams the client closed before the end.

FAKE, register_fake()
    A stand-in kind ("which of these numbered options"), the example lanes B and C can copy: options are (label, is_read)
    pairs; the grammar admits 0 to n; parse is model_words.option; the check takes a read, refuses a change (the model
    picks, never writes: a change chosen only by the model is never taken), and leaves "none" UNSETTLED; the fallback is
    the buttons (ASK_OWNER).

The tokenizer here is a deterministic stand-in (words, signs, spaces and ChatML markers), not any model's vocabulary.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import threading
import time
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import grammars, model_words, turns


class VirtualTime:
    """Milliseconds that move only when told (a TurnRequest's now_ms, a FakeWorker's latency)."""

    def __init__(self, start=0):
        self.ms = int(start)

    def __call__(self):return self.ms

    def advance(self, ms):self.ms += int(ms)


def chatml(messages, add_generation_prompt=True):
    """ChatML, the shape of the Qwen templates, for counting with no server. Not the model's own template."""
    out = ''.join('<|im_start|>%s\n%s<|im_end|>\n' % (m['role'], m['content']) for m in messages)
    return out + ('<|im_start|>assistant\n' if add_generation_prompt else '')


TOKEN = re.compile(r'<\|[a-z_]+\|>|\w+|[^\w\s]|\s+')


def tokens(text):
    return TOKEN.findall(text)


def _shared(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:break
        n += 1
    return n


def _step(step, messages, grammar):
    if callable(step):step = step(messages, grammar)
    if isinstance(step, str):step = {'text': step}
    if not isinstance(step, dict):raise TypeError('FAKE_STEP: a string, a dict or a callable giving one')
    return step


class FakeWorker:
    def __init__(self, script=(), *, time=None, model='fake-model', cache=True, context=4096, read_rate=70, write_rate=5,
                 enforce_grammar=False, live=True):
        self.script = list(script);self.time = time if time is not None else VirtualTime()
        self._model = model;self.cache = cache;self.context = context
        self.read_rate = Fraction(read_rate);self.write_rate = Fraction(write_rate)
        self.enforce_grammar = enforce_grammar;self._live = live
        self.calls = [];self._last = []

    def live(self):return self._live

    def model(self):return self._model

    def key(self):return 'fake:' + hashlib.sha256(self._model.encode()).hexdigest()[:16]

    def count(self, messages):return len(tokens(chatml(messages)))

    def kept(self, messages):
        return _shared(tokens(chatml(messages)), self._last) if self.cache else 0

    def complete(self, messages, *, answer_tokens, grammar, deadline_ms, odds=0, prompt_tokens=None, on_progress=None,
                 cancelled=None):
        if not self.script:raise turns.PortError('FAKE_SCRIPT_EMPTY')
        if cancelled is not None and cancelled():raise turns.PortError('STOPPED')
        step = _step(self.script.pop(0), messages, grammar)
        seen = tokens(chatml(messages));kept = self.kept(messages)
        self.calls.append({'messages': json.loads(json.dumps(messages)), 'grammar': grammar, 'answer_tokens': answer_tokens,
                           'deadline_ms': deadline_ms, 'odds': odds, 'kept': kept})
        if step.get('fail'):raise turns.PortError(step['fail'])
        self._last = seen
        if step.get('cancel'):
            self.time.advance(deadline_ms);raise turns.Late(deadline_ms)
        text = step.get('text', '');finish = step.get('finish', 'stop')
        if self.enforce_grammar and grammar and not grammars.matches(grammar, text):raise turns.PortError('FAKE_GRAMMAR_REFUSES')
        written = tokens(text)
        if len(written) > answer_tokens:text = ''.join(written[:answer_tokens]);finish = 'length';written = written[:answer_tokens]
        new = len(seen) - kept
        ms = step.get('ms')
        if ms is None:ms = math.ceil(Fraction(new * 1000) / self.read_rate) + math.ceil(Fraction(len(written) * 1000) / self.write_rate)
        self.time.advance(min(ms, deadline_ms) if deadline_ms else ms)
        if on_progress is not None:     # A3: one progress event per token written, the last at the answer's time
            for n in range(1, len(written) + 1):on_progress(n, int(ms) if n == len(written) else int(ms) * n // (len(written) + 1))
        return {'text': text, 'finish': finish, 'elapsed_ms': int(ms),
                'timings': {'prompt_n': new, 'cache_n': kept, 'predicted_n': len(written), 'prompt_ms': ms, 'predicted_ms': 0},
                'odds': step.get('odds')}


# -- the HTTP stand-in ----------------------------------------------------------------------------------------------------------
class FakeServer:
    def __init__(self, script=(), *, context=4096, model_id='f' * 64, key='fake-worker-key'):
        self.script = list(script);self.context = context;self.model_id = model_id;self.bodies = [];self.closed = 0
        self._dir = tempfile.mkdtemp(prefix='fake-worker-');self.key_file = Path(self._dir) / 'key'
        self.key_file.write_text(key);self.key_file.chmod(0o600);self._key = key
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):pass

            def _send(self, code, value):
                raw = json.dumps(value).encode()
                self.send_response(code);self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)));self.end_headers();self.wfile.write(raw)

            def _authorised(self):
                if self.headers.get('Authorization') != 'Bearer ' + server._key:
                    self._send(401, {'error': 'unauthorised'});return False
                return True

            def _stream(self, step, text, seen):
                """A3: llama-server's streamed answer, one event per token, token_ms apart."""
                self.send_response(200);self.send_header('Content-Type', 'text/event-stream');self.end_headers()
                pieces = tokens(text)
                events = [{'choices': [{'index': 0, 'delta': {'content': p}, 'finish_reason': None}]} for p in pieces]
                events.append({'choices': [{'index': 0, 'delta': {}, 'finish_reason': step.get('finish', 'stop')}],
                               'usage': {'prompt_tokens': len(seen), 'completion_tokens': len(pieces)},
                               'timings': {'prompt_n': len(seen), 'cache_n': 0, 'predicted_n': len(pieces),
                                           'prompt_ms': 1.0, 'predicted_ms': 1.0}})
                try:
                    for value in events:
                        if step.get('token_ms'):time.sleep(step['token_ms'] / 1000)
                        self.wfile.write(b'data: ' + json.dumps(value).encode() + b'\n\n');self.wfile.flush()
                    self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
                except OSError:
                    server.closed += 1

            def do_GET(self):
                if not self._authorised():return
                server.bodies.append((self.path, None))
                if self.path == '/health':return self._send(200, {'status': 'ok'})
                if self.path == '/props':return self._send(200, {'default_generation_settings': {'n_ctx': server.context}})
                self._send(404, {'error': 'not here'})

            def do_POST(self):
                if not self._authorised():return
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
                server.bodies.append((self.path, body))
                if self.path == '/apply-template':return self._send(200, {'prompt': chatml(body['messages'])})
                if self.path == '/tokenize':
                    return self._send(200, {'tokens': [int(hashlib.sha256(t.encode()).hexdigest()[:6], 16) for t in tokens(body['content'])]})
                if self.path == '/v1/chat/completions':
                    if not server.script:return self._send(500, {'error': 'script empty'})
                    step = _step(server.script.pop(0), body['messages'], body.get('grammar'))
                    if step.get('sleep_ms'):time.sleep(step['sleep_ms'] / 1000)
                    if step.get('fail'):return self._send(500, {'error': step['fail']})
                    text = step.get('text', '');seen = tokens(chatml(body['messages']))
                    if body.get('stream'):return self._stream(step, text, seen)
                    return self._send(200, {'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text},
                                                         'finish_reason': step.get('finish', 'stop')}],
                                            'usage': {'prompt_tokens': len(seen), 'completion_tokens': len(tokens(text))},
                                            'timings': {'prompt_n': len(seen), 'cache_n': 0, 'predicted_n': len(tokens(text)),
                                                        'prompt_ms': 1.0, 'predicted_ms': 1.0}})
                self._send(404, {'error': 'not here'})

        self._server = ThreadingHTTPServer(('127.0.0.1', 0), Handler);self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True);self._thread.start()

    def worker(self):
        """A worker record local_brain.request and local_brain.worker_live accept (this process stands in for the worker)."""
        from .operation_stop import process_identity
        return {'pid': os.getpid(), 'start': process_identity(os.getpid()), 'port': self.port, 'key_file': str(self.key_file),
                'context': self.context, 'model_id': self.model_id, 'runtime': {'simulated': True, 'name': 'fake_worker'},
                'backend': 'CPU'}

    def completions(self):
        """The chat request bodies as sent, in order."""
        return [body for path, body in self.bodies if path == '/v1/chat/completions']

    def stop(self):
        self._server.shutdown();self._server.server_close()
        try:
            self.key_file.unlink();os.rmdir(self._dir)
        except OSError:
            pass

    def __enter__(self):return self

    def __exit__(self, *exc):self.stop()


# -- the stand-in kind ----------------------------------------------------------------------------------------------------------
FAKE_BRIEF = ('You choose one of the numbered options for a desk on this computer. Answer only with the option\'s number, or 0 '
              'if none of them fits. Do not explain.')


def _fake_stable(inputs):
    return '\n'.join('%d. %s' % (i, label) for i, (label, _) in enumerate(inputs['options'], 1))


def _fake_last(inputs):
    return 'Question: ' + inputs['question']


def _fake_grammar(inputs):
    return grammars.choice(len(inputs['options']))


def _fake_parse(said, inputs):
    return model_words.option(said, len(inputs['options']))


def _fake_check(n, inputs):
    if n == 0:return turns.Verdict('UNSETTLED', value=None, why=('NONE_FITS',), checks=(('range', True, '0'),))
    label, is_read = inputs['options'][n - 1]
    if not is_read:
        return turns.Verdict('REFUSED', why=('MODEL_PICK_CHANGE',), checks=(('range', True, str(n)), ('read', False, label)))
    return turns.Verdict('TAKEN', value=n, checks=(('range', True, str(n)), ('read', True, label)))


def _fake_fallback(inputs):
    return turns.Fallback('ASK_OWNER', tuple(label for label, _ in inputs['options']))


FAKE = turns.TurnKind(name='FAKE', version=1, switch='choosing', brief=lambda: FAKE_BRIEF, stable=_fake_stable, last=_fake_last,
                      grammar=_fake_grammar, caps=turns.Caps(new_tokens=300, answer_tokens=4, deadline_ms=6000),
                      parse=_fake_parse, check=_fake_check, fallback=_fake_fallback, paper='')


def register_fake():
    return turns.register(FAKE)
