"""Slate: the owner's chat helper, answered by Google Gemini with a free key (Qt-free).

The owner makes a free key once at aistudio.google.com/apikey (any Google account)
and pastes it into Slate. Slate checks the key straight away with a real request,
then picks a free Flash model the key can use. Google renames models often, so
the model is chosen from the key's own model list (``gemini-flash-latest`` when
offered) and Slate falls back to the next Flash model if one is refused or busy.

Request format, header and error shapes follow ai.google.dev (checked October 2026):
POST v1beta/models/{model}:generateContent with the key in ``x-goog-api-key``;
an invalid key answers 400 with reason API_KEY_INVALID.

Privacy: on the free tier Google may use what is sent to improve its products.
Only the owner's messages (and the open file, when the paperclip toggle is on)
are sent. Replies are text for the owner to read; Slate changes no files and runs nothing.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

from .session import config_dir

SCHEMA = 'arc1.clip-settings/3'
API = 'https://generativelanguage.googleapis.com/v1beta'
KEY_URL = 'https://aistudio.google.com/apikey'
KEY_ENV = 'GEMINI_API_KEY'
PREFERRED_ALIASES = ('gemini-flash-latest', 'gemini-flash-lite-latest')
NOT_CHAT = ('image', 'tts', 'live', 'audio', 'transcribe', 'embedding', 'computer', 'banana', 'robotics', 'vision',
            'aqa', 'learnlm', 'gemma')
MAX_FILE_CHARS = 24000
MAX_HISTORY = 40
SYSTEM_PROMPT = (
    'You are Graphite, the assistant inside the Graphite workspace, the development environment for the ARC-1 '
    'Adaptive RISC-V Console (F133 and D213 processors, two FPGAs). STRUTHIO Arcade 1.8 is the '
    'authoritative JavaScript behavior reference. Its working portable C11 port is in software/struthio, '
    'with host gameplay, deterministic saves and tick-by-tick parity scenarios. The C hello_arc1 example uses a host '
    'simulator. Answer briefly and concretely; use fenced code blocks for code. No ARC-1 board '
    'has been qualified; never claim that something ran on hardware when it was only a browser '
    'preview or host simulation. Graphite has a Development Lab for source-bound baseline versus '
    'candidate host checks. A passing candidate is not promoted hardware; respect stale evidence '
    'markers and independent review. The imported C bootstrap is an immutable snapshot. Graphite bounded '
    'jobs propose isolated candidates; only the kernel grants scope and the operator accepts source. '
    'Native graphics are diagnostic and audio rendering remains unfinished.')


class ClipError(Exception):
    """A problem explained in plain words. ``kind``: key, quota, model, network, blocked, other."""
    def __init__(self, text, kind='other'):
        super().__init__(text)
        self.kind = kind


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
        raise ClipError('Windows could not %s the key' % ('protect' if encrypt else 'read'))
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


def looks_like_key(text):
    """A pasted key: one token, no spaces, long enough. Google documents no fixed prefix."""
    t = (text or '').strip()
    return 30 <= len(t) <= 200 and re.fullmatch(r'[A-Za-z0-9._\-~+/=]+', t) is not None


# --------------------------------------------------------------------------- settings

def _settings_document(path):
    try:
        if path.stat().st_size>65536:raise OSError('Graphite settings exceed the supported size')
        value=json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:return {'schema':SCHEMA}
    except (ValueError,TypeError):raise OSError('Graphite settings are invalid; preserve the file and inspect it')
    if not isinstance(value,dict) or value.get('schema')!=SCHEMA:raise OSError('Unsupported Graphite settings schema')
    return value


def _preferences(document):
    model=document.get('model','');include=document.get('include_file',False)
    if not isinstance(model,str) or len(model)>200 or any(ord(c)<32 for c in model):
        raise OSError('Graphite model preference must be text without control characters, at most 200 characters')
    if type(include) is not bool:raise OSError('Graphite source-sharing preference must be true or false')
    return {'model':model,'include_file':include}


def preferences():
    """Only non-secret preferences and an opaque revision; never open the key."""
    import hashlib
    document=_settings_document(settings_path())
    values=_preferences(document)
    return {**values,'revision':document.get('preferences_revision') or
            hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()}


def _write_settings_document(path,document):
    import tempfile
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(prefix='.clip-',suffix='.json',dir=path.parent)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
            json.dump(document,stream,indent=2);stream.write('\n')
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def update_preferences(changes,revision=None):
    """Edit existing non-secret fields while retaining credential bytes verbatim."""
    from .config_lock import locked
    import uuid
    if not isinstance(changes,dict) or set(changes)-{'model','include_file'}:raise ValueError('Unsupported provider preference')
    if 'model' in changes and (not isinstance(changes['model'],str) or len(changes['model'])>200 or any(ord(c)<32 for c in changes['model'])):
        raise ValueError('Model preference must be at most 200 characters without control characters')
    if 'include_file' in changes and type(changes['include_file']) is not bool:raise ValueError('Source sharing must be true or false')
    path=settings_path()
    with locked(path):
        document=_settings_document(path)
        document.update(changes);document['preferences_revision']=revision or uuid.uuid4().hex
        _write_settings_document(path,document)
    return preferences()


class Settings:
    def __init__(self, key='', model='', include_file=False):
        self.key = key or ''
        self.model = model or ''                   # chosen from the key's model list
        self.include_file = bool(include_file)
        self._loaded=None

    def api_key(self):
        """The key pasted into Slate wins; otherwise the GEMINI_API_KEY variable."""
        return self.key or os.environ.get(KEY_ENV, '')

    def ready(self):
        return bool(self.api_key())

    def describe(self):
        if not self.ready():
            return 'Google Gemini · free key needed'
        return 'Google Gemini · %s' % (self.model or 'free')

    @classmethod
    def load(cls, path=None):
        p = Path(path) if path else settings_path()
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            result=cls();result._loaded={'key':'','model':'','include_file':False};return result
        if not isinstance(d, dict) or d.get('schema') != SCHEMA:
            result=cls();result._loaded={'key':'','model':'','include_file':False};return result
        model = d.get('model') if isinstance(d.get('model'), str) else ''
        result=cls(open_key(d.get('key')), model, d.get('include_file'))
        result._loaded={'key':result.key,'model':result.model,'include_file':result.include_file}
        return result

    def save(self, path=None):
        p = Path(path) if path else settings_path()
        from .config_lock import locked
        import uuid
        with locked(p):
            data=_settings_document(p);latest={**_preferences(data),'key':open_key(data.get('key'))}
            wanted={'key':self.key,'model':self.model,'include_file':self.include_file}
            for key in wanted:
                if self._loaded is not None and wanted[key]==self._loaded[key]:wanted[key]=latest[key]
                elif self._loaded is not None and latest[key] not in (self._loaded[key],wanted[key]):
                    raise OSError('Graphite preferences changed while this editor was open; reload before saving')
            changed=any(wanted[key]!=latest[key] for key in wanted)
            if wanted['key']!=latest['key'] or 'key' not in data:data['key']=seal_key(wanted['key'])
            data.update(model=wanted['model'],include_file=wanted['include_file'])
            if changed:data['preferences_revision']=uuid.uuid4().hex
            _write_settings_document(p,data)
            self.key,self.model,self.include_file=wanted['key'],wanted['model'],wanted['include_file'];self._loaded=wanted


# --------------------------------------------------------------------------- messages

def with_file(text, file_name=None, file_text=None):
    """The owner's message, optionally followed by the open file (trimmed)."""
    if not file_name or file_text is None:
        return text
    body = file_text if len(file_text) <= MAX_FILE_CHARS else file_text[:MAX_FILE_CHARS] + '\n... (trimmed)'
    return '%s\n\nOpen file `%s`:\n```\n%s\n```' % (text, file_name, body)


def contents(history):
    """history: [(role, text)] with role 'user' or 'assistant'; newest last. Gemini calls the reply 'model'."""
    out = []
    for role, text in history[-MAX_HISTORY:]:
        if role in ('user', 'assistant') and text:
            out.append({'role': 'model' if role == 'assistant' else 'user', 'parts': [{'text': text}]})
    while out and out[0]['role'] != 'user':        # a conversation must start with the user
        out.pop(0)
    return out


# --------------------------------------------------------------------------- HTTP

def _explain(code, body):
    """Turns a Google error into words the owner can act on."""
    try:
        err = json.loads(body).get('error', {})
    except (ValueError, AttributeError):
        err = {}
    status, message = err.get('status', ''), err.get('message', '')
    reasons = {d.get('reason') for d in err.get('details', []) if isinstance(d, dict)}
    retry = next((d.get('retryDelay') for d in err.get('details', []) if isinstance(d, dict) and d.get('retryDelay')),
                 None)
    if 'API_KEY_INVALID' in reasons or 'API key not valid' in message:
        return ClipError("Google says this key isn't valid. Copy it again from %s (Create API key, then Copy)."
                         % KEY_URL, 'key')
    if code == 403 or status == 'PERMISSION_DENIED':
        return ClipError("This key isn't allowed to use Gemini (it may be blocked or limited to another API). "
                         'Create a new key at %s.' % KEY_URL, 'key')
    if code == 429 or status == 'RESOURCE_EXHAUSTED':
        wait = (' Try again in %s.' % retry) if retry else ' Try again in a minute; daily limits reset overnight.'
        return ClipError("Google's free limit is used up for now." + wait, 'quota')
    if 'location is not supported' in message.lower():
        return ClipError("Google doesn't offer the free Gemini API in your country yet.", 'key')
    if code == 404 or status == 'NOT_FOUND':
        return ClipError('That Gemini model is not available to this key.', 'model')
    if code >= 500:
        return ClipError('Google is busy right now (error %d). Try again in a moment.' % code, 'network')
    return ClipError(('Google refused the request (error %d). %s' % (code, message)).strip(), 'other')


def _request(url, key, payload=None, timeout=60, opener=urllib.request.urlopen):
    headers = {'x-goog-api-key': key}
    data = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST' if data else 'GET', headers=headers)
    try:
        with opener(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', 'replace')
        except OSError:
            body = ''
        raise _explain(e.code, body)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ClipError("Can't reach Google (%s). Check the internet connection." % getattr(e, 'reason', e),
                        'network')
    except ValueError:
        raise ClipError('Google sent a reply Graphite could not read.', 'other')


# --------------------------------------------------------------------------- models

def list_models(key, opener=urllib.request.urlopen):
    """Model ids this key can chat with (generateContent)."""
    ids, token = [], None
    for _ in range(5):
        url = API + '/models?pageSize=1000' + ('&pageToken=' + token if token else '')
        data = _request(url, key, opener=opener)
        for m in data.get('models', []):
            if isinstance(m, dict) and 'generateContent' in m.get('supportedGenerationMethods', []):
                ids.append(m.get('name', '').split('/', 1)[-1])
        token = data.get('nextPageToken')
        if not token:
            break
    return ids


def _version(model_id):
    m = re.match(r'gemini-(\d+(?:\.\d+)?)-flash(-lite)?(.*)$', model_id)
    if not m:
        return None
    stable = m.group(3) in ('', '-latest') or re.fullmatch(r'-\d{3}', m.group(3)) is not None
    return (0 if m.group(2) else 1, 1 if stable else 0, float(m.group(1)))


def pick_models(ids):
    """Chat models best first: the Flash alias, then newest stable Flash, then Flash-Lite, previews last."""
    usable = [i for i in ids if 'flash' in i and not any(word in i for word in NOT_CHAT)]
    ranked = [a for a in PREFERRED_ALIASES[:1] if a in usable]
    versions = sorted((v, i) for i in usable if (v := _version(i)) is not None)
    ranked += [i for v, i in sorted(versions, key=lambda p: (p[0][0], p[0][1], p[0][2]), reverse=True)
               if i not in ranked]
    ranked += [a for a in PREFERRED_ALIASES[1:] if a in usable and a not in ranked]
    return ranked


# --------------------------------------------------------------------------- chat

def generate(key, model, history, timeout=120, opener=urllib.request.urlopen):
    payload = {'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]}, 'contents': contents(history)}
    data = _request('%s/models/%s:generateContent' % (API, model), key, payload, timeout, opener)
    cands = data.get('candidates') or []
    if not cands:
        reason = (data.get('promptFeedback') or {}).get('blockReason')
        raise ClipError('Google blocked this message%s. Try wording it differently.'
                        % (' (%s)' % reason if reason else ''), 'blocked')
    first = cands[0]
    parts = (first.get('content') or {}).get('parts') or []
    text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict) and not p.get('thought')).strip()
    if not text:
        why = first.get('finishReason', '')
        if why in ('SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'RECITATION', 'SPII'):
            raise ClipError('Google withheld the answer (%s). Try wording it differently.' % why, 'blocked')
        raise ClipError('Google sent an empty answer%s.' % (' (%s)' % why if why else ''), 'other')
    if first.get('finishReason') == 'MAX_TOKENS':
        text += '\n\n*(Answer cut short by Google.)*'
    return text


def ask(settings, history, opener=urllib.request.urlopen, sleep=time.sleep):
    """Answers the conversation. May set settings.model (the caller saves settings)."""
    key = settings.api_key()
    if not key:
        raise ClipError('I need your free Google key first.', 'key')
    tried, candidates = [], [settings.model] if settings.model else []
    last = None
    for attempt in range(4):
        if not candidates:
            candidates = [m for m in pick_models(list_models(key, opener)) if m not in tried]
            if not candidates:
                raise last or ClipError('This key has no Gemini Flash model to chat with.', 'model')
        model = candidates.pop(0)
        try:
            text = generate(key, model, history, opener=opener)
        except ClipError as e:
            last = e
            if e.kind == 'network' and 'busy' in str(e) and attempt == 0:
                sleep(2)
                candidates.insert(0, model)        # one quiet retry of the same model
                continue
            if e.kind in ('model', 'quota'):       # Flash-Lite has its own free quota
                tried.append(model)
                if settings.model == model:
                    settings.model = ''
                continue
            raise
        settings.model = model
        return text
    raise last


def check_key(key, opener=urllib.request.urlopen):
    """Proves a key works end to end: lists its models and gets a real one-word answer.
    Returns the model that answered."""
    s = Settings(key)
    ask(s, [('user', 'Reply with the single word: ready')], opener=opener)
    return s.model
