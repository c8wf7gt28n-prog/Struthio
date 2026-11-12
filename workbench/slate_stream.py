"""Bounded authenticated loopback SSE, with final-only validation by the caller."""
from __future__ import annotations
import json
import time
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from . import local_brain as brain, record_io


def prompt_size(worker, messages):
    prompt = brain.request(worker, '/apply-template', {'messages': messages, 'add_generation_prompt': True,
        'chat_template_kwargs': brain.TEMPLATE_OPTIONS}, timeout=10)['prompt']
    tokens = brain.request(worker, '/tokenize', {'content': prompt, 'add_special': False}, timeout=10)['tokens']
    if not isinstance(tokens, list): raise ValueError('LOCAL_TOKENIZER_RESPONSE_INVALID')
    return len(tokens)


def prefix_key(worker, owner, context_digest, messages):
    if worker.get('context_reuse') != 'PINNED_SINGLE_SLOT' or not worker.get('verified_files'):
        return None
    return record_io.digest({'worker': brain.worker_identity(worker), 'runtime': worker['runtime'],
        'owner': owner, 'context': context_digest, 'limit': worker['context'], 'messages': messages,
        'template_options': brain.TEMPLATE_OPTIONS})


def fit_history(worker, messages, output_tokens):
    """Keep the system evidence and latest question when recent dialogue is too large."""
    selected = list(messages)
    if len(selected) > 2 and selected[1]['role'] != 'user':
        selected.pop(1)
    while True:
        measured = prompt_size(worker, selected)
        if measured + output_tokens + 32 <= worker['context']:
            return selected, measured
        if len(selected) <= 2:
            raise ValueError('CONTEXT_BUDGET_EXCEEDED: the current question and its supplied evidence exceed the worker budget')
        selected.pop(1)
        while len(selected) > 2 and selected[1]['role'] != 'user':
            selected.pop(1)


def events(response, cancelled, deadline):
    """Parse SSE framing, including comments, split data lines and a bounded body."""
    data = []; size = 0; event_size = 0
    while True:
        if cancelled(): raise ValueError('MODEL_OPERATION_CANCELLED')
        if time.monotonic() > deadline: raise ValueError('LOCAL_STREAM_TIME_BUDGET')
        raw = response.readline(65537)
        size += len(raw); event_size += len(raw)
        if len(raw) > 65536 or event_size > 131072 or size > 2097152: raise ValueError('LOCAL_STREAM_BYTE_BOUND')
        if not raw:
            if data: yield '\n'.join(data)
            return
        line = raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if data: yield '\n'.join(data)
            data = []; event_size = 0
        elif line.startswith('data:'): data.append(line[5:].removeprefix(' '))
        elif not line.startswith((':', 'event:', 'id:', 'retry:')): raise ValueError('LOCAL_STREAM_INVALID_FRAME')


def complete(worker, messages, max_tokens=512, schema=None, on_delta=None, cancelled=lambda: False,
             seconds=120, measured_prompt=None, *, kernel, cache_key=None):
    if not brain.worker_live(worker): raise ValueError('MODEL_WORKER_NOT_LIVE')
    measured_prompt = prompt_size(worker, messages) if measured_prompt is None else measured_prompt
    if measured_prompt + max_tokens + 32 > worker['context']: raise ValueError('CONTEXT_BUDGET_EXCEEDED: reduce context or output tokens')
    # Every resident generation consumes the previous slot claim. Only a
    # completed, revision-checked source answer can publish a fresh one.
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = brain.get(kernel, 'prepared_context', {}, db)
        reuse = bool(cache_key and previous.get('key') == cache_key and
                     previous.get('worker') == brain.worker_identity(worker))
        if previous:
            brain.put(kernel, 'prepared_context', {}, db=db)
    payload = {'messages': messages, 'max_tokens': max_tokens, 'temperature': 0, 'stream': True,
        'stream_options': {'include_usage': True}, 'cache_prompt': reuse, 'chat_template_kwargs': brain.TEMPLATE_OPTIONS}
    if schema: payload['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'slate_result', 'strict': True, 'schema': schema}}
    key = Path(worker['key_file']).read_text().strip()
    request = Request('http://127.0.0.1:' + str(worker['port']) + '/v1/chat/completions', data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
    began = time.monotonic(); first = None; text = ''; finish = None; done = False; usage = {}; timings = {}
    opener = build_opener(ProxyHandler({}), brain.NoRedirect())
    try:
        with opener.open(request, timeout=seconds) as response:
            if response.headers.get_content_type() != 'text/event-stream': raise ValueError('LOCAL_STREAM_CONTENT_TYPE')
            for event in events(response, cancelled, began + seconds):
                if event == '[DONE]': done = True; break
                value = record_io.strict_json(event)
                if not isinstance(value, dict) or value.get('error'): raise ValueError('LOCAL_STREAM_SERVER_ERROR')
                if isinstance(value.get('usage'), dict): usage = value['usage']
                if isinstance(value.get('timings'), dict): timings = value['timings']
                choices = value.get('choices', [])
                if not isinstance(choices, list) or len(choices) > 1: raise ValueError('LOCAL_STREAM_CHOICE_BOUND')
                for choice in choices:
                    if choice.get('index', 0) != 0: raise ValueError('LOCAL_STREAM_CHOICE_INDEX')
                    delta = choice.get('delta') or {}
                    if delta.get('tool_calls') or choice.get('message'): raise ValueError('LOCAL_STREAM_UNEXPECTED_ACTION_CHANNEL')
                    content = delta.get('content')
                    if content is not None:
                        if not isinstance(content, str): raise ValueError('LOCAL_STREAM_DELTA_TYPE')
                        if finish is not None and content: raise ValueError('LOCAL_STREAM_CONTENT_AFTER_FINISH')
                        if content and first is None: first = time.monotonic() - began
                        text += content
                        if len(text) > 65536: raise ValueError('LOCAL_STREAM_OUTPUT_BOUND')
                        if on_delta and content: on_delta(text)
                    if choice.get('finish_reason') is not None:
                        if finish is not None: raise ValueError('LOCAL_STREAM_DUPLICATE_FINISH')
                        finish = choice['finish_reason']
    except HTTPError as exc: raise ValueError('LOCAL_STREAM_HTTP_' + str(exc.code)) from exc
    if cancelled(): raise ValueError('MODEL_OPERATION_CANCELLED')
    if time.monotonic() - began > seconds: raise ValueError('LOCAL_STREAM_TIME_BUDGET')
    if not done or finish != 'stop': raise ValueError('LOCAL_RESPONSE_INCOMPLETE: no validated result was committed')
    if not text.strip(): raise ValueError('LOCAL_RESPONSE_EMPTY')
    details = usage.get('prompt_tokens_details')
    reused = details.get('cached_tokens') if isinstance(details, dict) else timings.get('cache_n')
    if type(reused) is not int or not 0 <= reused <= measured_prompt:
        reused = None
    return {'text': text, 'finish_reason': finish, 'stream_complete': True, 'usage': usage, 'timings': timings,
        'first_token_seconds': first, 'elapsed_seconds': time.monotonic() - began, 'prompt_tokens_measured': measured_prompt,
        'context_limit': worker['context'], 'prefix_reuse_requested': reuse, 'observed_reused_tokens': reused,
        'input_messages_digest': record_io.digest(messages), 'memory': brain.usage(worker), 'transport': 'AUTHENTICATED_LOOPBACK_SSE'}


def preview(text, structured=True):
    """Display only provisional answer prose, never partial actions or patches."""
    if not structured: return text
    # Only a top-level text member is presentation. An action argument named
    # "text" must never become the streamed answer preview.
    depth = 0; index = 0; tail = None
    while index < len(text):
        char = text[index]
        if char in '{[': depth += 1
        elif char in '}]': depth -= 1
        elif char == '"':
            start = index; index += 1; escape = False
            while index < len(text):
                if not escape and text[index] == '"': break
                escape = text[index] == '\\' and not escape
                index += 1
            if index >= len(text): return ''
            if depth == 1:
                try: name = json.loads(text[start:index + 1])
                except ValueError: return ''
                after = index + 1
                while after < len(text) and text[after].isspace(): after += 1
                if name == 'text' and after < len(text) and text[after] == ':':
                    after += 1
                    while after < len(text) and text[after].isspace(): after += 1
                    if after < len(text) and text[after] == '"': tail = text[after:]; break
        index += 1
    if tail is None: return ''
    try:
        value, _ = json.JSONDecoder().raw_decode(tail)
        return value if isinstance(value, str) else ''
    except ValueError:
        # Reuse JSON's string decoder, discarding an incomplete escape at the end.
        body = tail[1:]
        for removed in range(min(12, len(body)) + 1):
            part = body[:len(body) - removed] if removed else body
            try: return json.loads('"' + part + '"')
            except ValueError: continue
        return ''
