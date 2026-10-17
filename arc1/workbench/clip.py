"""Clip: the chat helper between the owner and an AI model (Qt-free).

Where Clip's messages go (Clip › Settings):

* ``local``  - default. A free AI model running on this PC through Ollama
               (ollama.com). No account, no key, nothing leaves the PC. Clip
               offers to install Ollama and download the model the first time.
* ``gemini`` - Google Gemini with a free API key from aistudio.google.com.
* ``api``    - OpenAI (ChatGPT's models) with the owner's paid API key.
* ``manual`` - ChatGPT in the browser by copy & paste (no key, but you leave
               Workbench to paste).

Clip never types into, reads or scrapes a browser window: that breaks whenever a
site changes, cannot work on a minimized window, and automated extraction of
ChatGPT output is against OpenAI's terms. Nothing leaves the PC except the
messages the owner sends to a cloud choice (plus the open file, only when the
paperclip toggle is on). Replies are text for the owner to read; Clip runs nothing.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request

from .session import config_dir

SCHEMA = 'arc1.clip-settings/2'
MODES = ('local', 'gemini', 'api', 'manual')
MODE_NAMES = {'local': 'Local AI on this PC (free, no account)', 'gemini': 'Google Gemini (free API key)',
              'api': 'OpenAI API (paid API key)', 'manual': 'ChatGPT website by copy & paste'}
DEFAULT_MODELS = {'local': 'qwen2.5-coder:7b', 'gemini': 'gemini-2.5-flash', 'api': 'gpt-5-mini', 'manual': ''}
KEY_ENV = {'gemini': 'GEMINI_API_KEY', 'api': 'OPENAI_API_KEY'}
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent'
OLLAMA_URL = os.environ.get('OLLAMA_HOST_URL', 'http://127.0.0.1:11434')
CHATGPT_URL = 'https://chatgpt.com/'
GEMINI_KEY_URL = 'https://aistudio.google.com/apikey'
MAX_FILE_CHARS = 24000
MAX_HISTORY = 40
SYSTEM_PROMPT = (
    'You are Clip, the assistant inside ARC-1 Workbench, the development environment for the ARC-1 '
    'Adaptive RISC-V Console (F133 and D213 processors, two FPGAs). Answer briefly and concretely; '
    'use fenced code blocks for code. Builds, tests and games run in a host simulator: no ARC-1 board '
    'exists yet, so never claim that something ran on hardware.')


class ClipError(Exception):
    pass


class NeedsSetup(ClipError):
    """Local AI is not ready; ``step`` is 'install' (no Ollama) or 'model' (model not downloaded)."""
    def __init__(self, step, text):
        super().__init__(text)
        self.step = step


def settings_path():
    return config_dir() / 'clip.json'


# --------------------------------------------------------------------------- key storage

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
    def __init__(self, mode='local', models=None, keys=None, include_file=False):
        self.mode = mode if mode in MODES else 'local'
        self.models = dict(DEFAULT_MODELS)
        self.models.update({k: v.strip() for k, v in (models or {}).items() if k in MODES and isinstance(v, str)
                            and v.strip()})
        self.keys = {k: v for k, v in (keys or {}).items() if k in KEY_ENV and isinstance(v, str)}
        self.include_file = bool(include_file)

    @property
    def model(self):
        return self.models.get(self.mode, '')

    def api_key(self, mode=None):
        """A key typed into Clip wins; otherwise the usual environment variable."""
        mode = mode or self.mode
        return self.keys.get(mode) or os.environ.get(KEY_ENV.get(mode, ''), '') if mode in KEY_ENV else ''

    def ready(self):
        return self.mode not in KEY_ENV or bool(self.api_key())

    def leaves_pc(self):
        return self.mode != 'local'

    def describe(self):
        if self.mode == 'local':
            return 'Local AI · %s · stays on this PC' % self.model
        if self.mode == 'manual':
            return 'ChatGPT · copy & paste'
        name = 'Gemini' if self.mode == 'gemini' else 'OpenAI'
        return '%s · %s' % (name, self.model) if self.api_key() else '%s · API key needed' % name

    @classmethod
    def load(cls, path=None):
        p = Path(path) if path else settings_path()
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return cls()
        if not isinstance(d, dict) or d.get('schema') != SCHEMA:
            return cls()
        keys = {k: open_key(v) for k, v in (d.get('keys') or {}).items()} if isinstance(d.get('keys'), dict) else {}
        models = d.get('models') if isinstance(d.get('models'), dict) else {}
        return cls(d.get('mode'), models, keys, d.get('include_file'))

    def save(self, path=None):
        p = Path(path) if path else settings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {'schema': SCHEMA, 'mode': self.mode, 'models': self.models,
                'keys': {k: seal_key(v) for k, v in self.keys.items() if v}, 'include_file': self.include_file}
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


def _post(url, payload, headers, timeout, opener, who):
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), method='POST',
                                 headers=dict(headers, **{'Content-Type': 'application/json'}))
    try:
        with opener(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode('utf-8')).get('error', '')
            detail = err.get('message', '') if isinstance(err, dict) else str(err)
        except (ValueError, AttributeError, OSError):
            detail = ''
        hint = {400: 'The request was refused.', 401: 'The API key was rejected.', 403: 'The API key was rejected.',
                404: 'Unknown model; change it in Clip settings.',
                429: 'Too many requests, or no credit left on this key. Wait a minute and try again.'}.get(e.code, '')
        raise ClipError(('%s error %d. %s %s' % (who, e.code, hint, detail)).strip())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ClipError('Could not reach %s: %s' % (who, getattr(e, 'reason', e)))
    except ValueError:
        raise ClipError('%s sent a reply Clip could not read.' % who)


def ask_openai(settings, history, timeout=120, opener=urllib.request.urlopen):
    key = settings.api_key('api')
    if not key:
        raise ClipError('No OpenAI API key. Add one in Clip settings, or set OPENAI_API_KEY.')
    data = _post(OPENAI_URL, {'model': settings.models['api'], 'messages': build_messages(history)},
                 {'Authorization': 'Bearer ' + key}, timeout, opener, 'OpenAI')
    try:
        return (data['choices'][0]['message']['content'] or '').strip() or '(empty reply)'
    except (KeyError, IndexError, TypeError):
        raise ClipError('OpenAI sent a reply without text.')


def ask_gemini(settings, history, timeout=120, opener=urllib.request.urlopen):
    key = settings.api_key('gemini')
    if not key:
        raise ClipError('No Gemini API key. Get a free one at %s and add it in Clip settings.' % GEMINI_KEY_URL)
    contents = [{'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [{'text': m['content']}]}
                for m in build_messages(history)[1:]]
    data = _post(GEMINI_URL % settings.models['gemini'],
                 {'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]}, 'contents': contents},
                 {'x-goog-api-key': key}, timeout, opener, 'Gemini')
    try:
        parts = data['candidates'][0]['content']['parts']
        return ''.join(p.get('text', '') for p in parts).strip() or '(empty reply)'
    except (KeyError, IndexError, TypeError):
        raise ClipError('Gemini sent no answer (it may have been blocked by its safety filter).')


# --------------------------------------------------------------------------- local AI (Ollama)

def ollama_exe():
    found = shutil.which('ollama')
    if found:
        return found
    if os.name == 'nt':
        p = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe'
        if p.is_file():
            return str(p)
    return None


def ollama_models(timeout=3, opener=urllib.request.urlopen):
    """Names of downloaded models, or None when the Ollama service is not running."""
    try:
        with opener(urllib.request.Request(OLLAMA_URL + '/api/tags'), timeout=timeout) as r:
            data = json.loads(r.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    return [m.get('name', '') for m in data.get('models', []) if isinstance(m, dict)]


def has_model(names, model):
    want = model if ':' in model else model + ':latest'
    return any(n == want or n == model for n in names)


def start_ollama(wait=15):
    """Starts the Ollama service if it is installed but not running. Returns the model list or None."""
    names = ollama_models()
    if names is not None:
        return names
    exe = ollama_exe()
    if not exe:
        return None
    kw = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kw['creationflags'] = 0x08000000                      # CREATE_NO_WINDOW
    else:
        kw['start_new_session'] = True
    try:
        subprocess.Popen([exe, 'serve'], **kw)
    except OSError:
        return None
    for _ in range(wait * 2):
        time.sleep(0.5)
        names = ollama_models()
        if names is not None:
            return names
    return None


def can_install_ollama():
    return os.name == 'nt' and shutil.which('winget') is not None


def install_ollama(timeout=1800):
    """Installs Ollama for this user with winget (Windows). Returns (ok, output tail)."""
    try:
        p = subprocess.run(['winget', 'install', '-e', '--id', 'Ollama.Ollama', '--accept-package-agreements',
                            '--accept-source-agreements'], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout, creationflags=0x08000000 if os.name == 'nt' else 0)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return p.returncode == 0, ((p.stdout or '') + (p.stderr or ''))[-300:]


def pull_model(model, progress=None, opener=urllib.request.urlopen):
    """Downloads a model through the running Ollama service; progress(text) gets updates."""
    req = urllib.request.Request(OLLAMA_URL + '/api/pull', data=json.dumps({'model': model}).encode(),
                                 method='POST', headers={'Content-Type': 'application/json'})
    last = 0.0
    try:
        with opener(req, timeout=3600) as r:
            for line in r:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('error'):
                    raise ClipError('Download failed: %s' % d['error'])
                total, done = d.get('total'), d.get('completed')
                if progress and time.time() - last > 0.5:
                    last = time.time()
                    if total and done:
                        progress('Downloading %s: %d%% of %.1f GB' % (model, 100 * done // total, total / 1e9))
                    else:
                        progress('Downloading %s: %s' % (model, d.get('status', '...')))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ClipError('Download failed: %s' % getattr(e, 'reason', e))


def ask_local(settings, history, timeout=600, opener=urllib.request.urlopen):
    names = start_ollama()
    if names is None:
        raise NeedsSetup('install', 'Local AI is not installed yet.')
    model = settings.models['local']
    if not has_model(names, model):
        raise NeedsSetup('model', 'The model %s is not downloaded yet.' % model)
    data = _post(OLLAMA_URL + '/api/chat', {'model': model, 'messages': build_messages(history), 'stream': False},
                 {}, timeout, opener, 'Local AI')
    try:
        return (data['message']['content'] or '').strip() or '(empty reply)'
    except (KeyError, TypeError):
        raise ClipError('Local AI sent a reply without text.')


def ask(settings, history):
    if settings.mode == 'local':
        return ask_local(settings, history)
    if settings.mode == 'gemini':
        return ask_gemini(settings, history)
    if settings.mode == 'api':
        return ask_openai(settings, history)
    raise ClipError('Copy & paste mode has no automatic reply.')
