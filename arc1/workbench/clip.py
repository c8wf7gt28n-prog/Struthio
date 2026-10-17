"""Clip: the chat helper between the owner and an AI model (Qt-free).

Two ways to reach ChatGPT, chosen in Clip's settings:

* ``api``    - Clip sends the conversation to the OpenAI API with the owner's own
               API key and shows the reply. Billed to that key; a ChatGPT
               subscription does not include API use.
* ``manual`` - no key. Clip copies each message to the clipboard and opens
               chatgpt.com; the owner pastes it, then presses ChatGPT's copy button
               on the answer and Clip picks the reply up from the clipboard.

Clip never types into, reads or scrapes a browser window: that breaks whenever the
site changes, cannot work on a minimized window, and automated extraction of
output is against OpenAI's terms. Nothing leaves the PC except the messages the
owner sends (plus the open file, only when "Include open file" is ticked).
The model's replies are text for the owner to read; Clip runs nothing.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from .session import config_dir

SCHEMA = 'arc1.clip-settings/1'
MODES = ('manual', 'api')
DEFAULT_MODEL = 'gpt-5-mini'
API_URL = 'https://api.openai.com/v1/chat/completions'
CHATGPT_URL = 'https://chatgpt.com/'
MAX_FILE_CHARS = 24000
MAX_HISTORY = 40
SYSTEM_PROMPT = (
    'You are Clip, the assistant inside ARC-1 Workbench, the development environment for the ARC-1 '
    'Adaptive RISC-V Console (F133 and D213 processors, two FPGAs). Answer briefly and concretely; '
    'use fenced code blocks for code. Builds, tests and games run in a host simulator: no ARC-1 board '
    'exists yet, so never claim that something ran on hardware.')


class ClipError(Exception):
    pass


def settings_path():
    return config_dir() / 'clip.json'


# --------------------------------------------------------------------------- API key storage

def _protect(data: bytes, encrypt: bool) -> bytes:
    """Windows DPAPI: only this Windows user account can decrypt the stored key."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    src, out = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), Blob()
    fn = ctypes.windll.crypt32.CryptProtectData if encrypt else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)):
        raise ClipError('Windows could not %s the API key' % ('protect' if encrypt else 'read'))
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def seal_key(key: str) -> dict:
    if not key:
        return {}
    if os.name == 'nt':
        return {'dpapi': base64.b64encode(_protect(key.encode('utf-8'), True)).decode('ascii')}
    return {'plain': key}           # protected by the file's 0600 permissions below


def open_key(sealed) -> str:
    if not isinstance(sealed, dict):
        return ''
    try:
        if 'dpapi' in sealed and os.name == 'nt':
            return _protect(base64.b64decode(sealed['dpapi']), False).decode('utf-8')
        return str(sealed.get('plain', ''))
    except (ClipError, ValueError, OSError):
        return ''


# --------------------------------------------------------------------------- settings

class Settings:
    def __init__(self, mode='manual', model=DEFAULT_MODEL, key='', include_file=False):
        self.mode = mode if mode in MODES else 'manual'
        self.model = (model or DEFAULT_MODEL).strip()
        self.key = key or ''
        self.include_file = bool(include_file)

    def api_key(self):
        """A key typed into Clip wins; otherwise the usual OPENAI_API_KEY variable."""
        return self.key or os.environ.get('OPENAI_API_KEY', '')

    def ready(self):
        return self.mode == 'manual' or bool(self.api_key())

    def describe(self):
        if self.mode == 'manual':
            return 'ChatGPT · copy & paste'
        return 'ChatGPT · API (%s)' % self.model if self.api_key() else 'ChatGPT · API key needed'

    @classmethod
    def load(cls, path=None):
        p = Path(path) if path else settings_path()
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return cls()
        if not isinstance(d, dict) or d.get('schema') != SCHEMA:
            return cls()
        return cls(d.get('mode'), d.get('model'), open_key(d.get('key')), d.get('include_file'))

    def save(self, path=None):
        p = Path(path) if path else settings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {'schema': SCHEMA, 'mode': self.mode, 'model': self.model, 'key': seal_key(self.key),
                'include_file': self.include_file}
        tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        if os.name != 'nt':
            tmp.chmod(0o600)
        os.replace(tmp, p)


# --------------------------------------------------------------------------- messages

def with_file(text, file_name=None, file_text=None):
    """The owner's message, optionally followed by the open file (trimmed)."""
    if not file_name or file_text is None:
        return text
    body = file_text if len(file_text) <= MAX_FILE_CHARS else file_text[:MAX_FILE_CHARS] + '\n... (trimmed)'
    return '%s\n\nOpen file `%s`:\n```\n%s\n```' % (text, file_name, body)


def build_messages(history):
    """history: [(role, text)] with role 'user' or 'assistant'; newest last."""
    msgs = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    for role, text in history[-MAX_HISTORY:]:
        if role in ('user', 'assistant') and text:
            msgs.append({'role': role, 'content': text})
    return msgs


def ask_openai(settings, history, timeout=120, opener=urllib.request.urlopen):
    key = settings.api_key()
    if not key:
        raise ClipError('No OpenAI API key. Add one in Clip settings (gear), or set OPENAI_API_KEY.')
    body = json.dumps({'model': settings.model, 'messages': build_messages(history)}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with opener(req, timeout=timeout) as r:
            data = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode('utf-8')).get('error', {}).get('message', '')
        except (ValueError, AttributeError, OSError):
            detail = ''
        hint = {401: 'The API key was rejected.', 429: 'Rate limit or no API credit left on this key.',
                404: 'Unknown model "%s"; change it in Clip settings.' % settings.model}.get(e.code, '')
        raise ClipError(('OpenAI error %d. %s %s' % (e.code, hint, detail)).strip())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ClipError('Could not reach OpenAI: %s' % getattr(e, 'reason', e))
    except ValueError:
        raise ClipError('OpenAI sent a reply Clip could not read.')
    try:
        text = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise ClipError('OpenAI sent a reply without text.')
    return (text or '').strip() or '(empty reply)'
