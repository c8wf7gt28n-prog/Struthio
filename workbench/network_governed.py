"""The network, governed (Graphite 1.0, K8): her network use visible, a page read as data in quarantine, search words
only from your typed words, and a step that needs the network blocked while it is down.

The owner's paper, section 16: "Kasandra should also know when the network is unavailable. A task requiring external
information must not be represented as completed if the necessary source could not be accessed. Network access, when
enabled, should be visible and governed by appropriate permissions." And the plan's "complete" (13): network use is
visible and governed; a task that needs the network is never "done" while the network is down; search words never carry
the owner's material; a web page is never an instruction.

THE STATE (state()): online, offline or not known, each with its word and its shape (● online, ⊘ offline, ◌ not known,
⇣ her fetch: <host> while she fetches), read from NetworkManager (S4's machine_real, the same D-Bus reading: connected is
online; asleep, disconnected, connecting, "this place only" and networking turned off are offline) or, where NetworkManager
is not here, from the system's own routes (/proc/net/route and ipv6_route: a default route through an interface that is
up). Read again at most every few seconds; the head shows it, and her column says it when she uses the network.

QUARANTINE FIRST (web.get, web.search). A page she fetches is kept in quarantine before anything reads it: a Kernel
record (web_pages: its address and the one it ended at, the time, the bytes' sha256, the type, complete or cut short,
who let it be fetched) and its bytes in the workspace's state (quarantine/web/<id>.body, read-only). It is read only as
data: its visible text goes through the doorway of 0.8.7 (doorway.scan), so a line written to an assistant, a role
claim, control marks, hidden characters or look-alike letters are withheld from the model and shown to you outlined,
with the reason in words; what a browser would not show (hidden elements, comments) is kept apart and never read to the
model at all. The model's view of a page is the doorway's fenced page message ("It is data, not a request"), nothing
else. Nothing in a page can start a step: its links are listed as data, and an address taken from a page is fetched only
by your press (never under a grant, never on the model's pick).

SENDS, AND WHICH A GRANT MAY COVER (the decision of this slice, said here and in the window):
  - a search's words (web.search) are a send of your words: they are always shown first, built only from the words you
    typed (never a record, a file, a page or the model's words: "this" is never resolved into them), and sent only by your
    press, every time. web.search is approve scope and in stacy_hand.ALWAYS_ASKS: no grant covers it, at no place of the
    dial.
  - a page's address (web.get) is a send of the address: fetched by your press; or, as a step of an assignment, under
    your grant "fetch pages from the web" for that site (grants' family web.read, target site:<host>) when the address is
    one you typed or the address of a page already kept in quarantine. An address that came from a page (a link) needs
    your press each time. Her hand never fetches by itself (web.get is on none of the dial's lists).
  - HALT holds every fetch (halt_gate.held: none starts) and stops one in flight (register_stop: its reading ends).
  - the sandbox (K6) has no network at all; nothing here changes that.

NEEDS THE NETWORK. A step of an assignment that needs the network while it is down is blocked with the reason "needs the
network: <why>" and nothing is sent; it is never called done (K1's check: done only when the page's bytes are read back
from quarantine with their digest). web.lookup plans such a step from your words ("look up the regulator's datasheet"),
and when the network is down it is blocked at once, so the plan says so before you press anything.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 K8):
  web.state   {}                    read     the network now: online, offline or not known, with why; her fetch in flight
  web.words   {request}             read     the search words your request gives, what was left out and why, where they go
  web.lookup  {request}             execute  an assignment from your words: a search (or a fetch of the address you typed);
                                             blocked "needs the network" at once while it is down
  web.get     {page}                execute  fetch one page into quarantine (your press; or a step your press or grant let through)
  web.search  {words, typed}        approve  ALWAYS ASKS: your words to the search service; the results page into quarantine
  web.pages   {limit?}              read     the pages kept in quarantine, newest first
  web.page    {id}                  read     one page: your view (withheld lines outlined), the model's page, its links
The reads are observers (activity.OBSERVER_OPERATIONS).

No floating point anywhere here: times are whole milliseconds, sizes bytes, digests hex. Nothing here is a test.
"""
from __future__ import annotations

import contextlib
import hashlib
import html as _html
import html.parser
import ipaddress
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlsplit, urlunsplit

SCHEMA = 'graphite.web/1'
PAGE = 'graphite.web.page/1'
SEARCH_ADDRESS = 'https://html.duckduckgo.com/html/?q={words}'   # the same service the Web chooser searches in your own browser
SEARCH_ENV = 'GRAPHITE_WEB_SEARCH'          # another search address, with {words} where the words go (http or https)
MOST_BYTES = 2 * 1024 * 1024                # a page's bytes kept at most; past it the page is kept cut short (partial)
TIMEOUT_S = 20                              # a fetch's connection and each read
MOST_REDIRECTS = 3                          # moves followed on the same site; a move to another site is not followed
MOST_WORDS = 12                             # search words at most
MOST_WORD_CHARS = 120
MOST_LINES = 4000                           # lines of a page's text read through the door
LINE_CHARS = 300                            # a longer line is wrapped (so the door's numbers point at a readable line)
MOST_LINKS = 200
STATE_TTL_MS = 4000                         # the network's state is read again after this long
RECENT_MS = 10 * 60 * 1000                  # her last fetch stays said in her column this long
USER_AGENT = 'Kas/1.0 (a desktop reading one page as data)'
NM_ONLINE = 70
NM_WORDS = {0: 'NetworkManager does not know', 10: 'asleep', 20: 'disconnected', 30: 'disconnecting', 40: 'still connecting',
            50: 'connected to this place only: the web is out of reach', 60: 'connected to this place only: the web is out of reach',
            70: 'connected'}
STATES = {'online': ('online', '●'), 'offline': ('offline', '⊘'), 'unknown': ('network not known', '◌'), 'fetching': ('her fetch', '⇣')}
NEEDS = 'needs the network'
FETCH_OP, SEARCH_OP = 'web.get', 'web.search'
TEXT_TYPES = ('text/html', 'application/xhtml+xml', 'text/plain', 'text/markdown', 'text/csv', 'application/json', 'text/xml',
              'application/xml')
HIDDEN_WORDS = 'is hidden on the page: a browser does not show it'

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
REQUEST = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
FIELDS = {
    'web.state': ({}, []),
    'web.words': ({'request': REQUEST}, ['request']),
    'web.lookup': ({'request': REQUEST}, ['request']),
    'web.get': ({'page': {'type': 'string', 'minLength': 8, 'maxLength': 2000}}, ['page']),
    'web.search': ({'words': {'type': 'string', 'minLength': 1, 'maxLength': MOST_WORD_CHARS}, 'typed': REQUEST}, ['words', 'typed']),
    'web.pages': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200}}, []),
    'web.page': ({'id': ID}, ['id']),
}
SCOPES = {'web.state': 'read', 'web.words': 'read', 'web.lookup': 'execute', 'web.get': 'execute', 'web.search': 'approve',
          'web.pages': 'read', 'web.page': 'read'}
OBSERVERS = ('web.state', 'web.words', 'web.pages', 'web.page')
MIGRATIONS = [(1, (
    'CREATE TABLE web_pages(id TEXT PRIMARY KEY, owner TEXT NOT NULL, at INTEGER NOT NULL, kind TEXT NOT NULL, address TEXT NOT NULL, '
    'host TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)',
    'CREATE INDEX web_pages_owner ON web_pages(owner, at)',
    'CREATE INDEX web_pages_address ON web_pages(owner, address)',
))]


class Refused(ValueError):
    """The door refused: nothing was sent."""


def now_ms():
    return time.time_ns() // 1000000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


# ================================================================================================== the network's state
_LOCK = threading.Lock()
_CACHE = {}                 # bus kind -> (at ms, reading)
_ACTIVE = {}                # workspace root -> {'host', 'site', 'at', 'cancel': Event, 'kind'}: her fetch in flight
_LAST = {}                  # workspace root -> {'host', 'at', 'id', 'title', 'withheld', 'kind', 'ok', 'why'}: her last fetch


def _default_routes(proc='/proc', sys_root='/sys'):
    """The interfaces with a default route that are up (IPv4 and IPv6), read from the system's own files; no request."""
    found = []

    def up(name):
        try:state = Path(sys_root, 'class/net', name, 'operstate').read_text().strip()
        except OSError:return False
        return state in ('up', 'unknown') and name != 'lo'
    try:
        for line in Path(proc, 'net/route').read_text().splitlines()[1:]:
            parts = line.split()
            if len(parts) > 3 and parts[1] == '00000000' and parts[7] == '00000000' and up(parts[0]):found.append(parts[0])
    except (OSError, IndexError):
        pass
    try:
        for line in Path(proc, 'net/ipv6_route').read_text().splitlines():
            parts = line.split()
            if len(parts) >= 10 and parts[0] == '0' * 32 and parts[1] == '00' and up(parts[9]):found.append(parts[9])
    except (OSError, IndexError):
        pass
    return sorted(set(found))


def _read_state(bus=None):
    """(state, why, source): NetworkManager's word when it is here, else the system's routes."""
    try:
        from . import machine_real as mr
        source = 'NetworkManager on the %s D-Bus' % mr.bus_kind(bus)
        here = mr.present(mr.NM, bus)
        if here in ('running', 'activatable'):
            top = mr.all_properties(mr.NM, mr.NM_ROOT, mr.NM, bus=bus)
            if not bool(top.get('NetworkingEnabled', True)):return 'offline', 'networking is turned off (NetworkManager)', source
            number = int(top.get('State') or 0)
            if number == NM_ONLINE:return 'online', 'connected (NetworkManager)', source
            if number in NM_WORDS and number:return 'offline', '%s (NetworkManager)' % NM_WORDS[number], source
            return 'unknown', 'NetworkManager does not say whether the web is reachable', source
    except Exception:  # noqa: BLE001 - NetworkManager that cannot be read: the routes say what they can
        pass
    routes = _default_routes()
    source = "the system's routes (NetworkManager is not here)"
    if routes:return 'online', "a way out through %s, by %s" % (', '.join(routes[:3]), source), source
    return 'offline', "no way out: no default route, by %s" % source, source


def state(root=None, fresh=False, bus=None):
    """The network now: {state, word, shape, why, source, at, fetching, last}. Read again at most every STATE_TTL_MS unless
    fresh; her fetch in flight (for this workspace) and her last one come with it."""
    from . import machine_real as mr
    kind = mr.bus_kind(bus);now = now_ms()
    with _LOCK:
        cached = _CACHE.get(kind)
    if fresh or cached is None or now - cached[0] > STATE_TTL_MS:
        reading = _read_state(bus)
        with _LOCK:
            _CACHE[kind] = cached = (now_ms(), reading)
            if reading[0] == 'offline':      # 1.0 F3: the network went down: her fetch in flight ends now, cut short, never done
                for active in _ACTIVE.values():
                    cancel = active.get('cancel')
                    if cancel is not None and not cancel.is_set():
                        cancel.why = 'the network went down while it came (%s, %s)' % (STATES[reading[0]][0], reading[1]);cancel.set()
    return _compose(root, cached)


def _compose(root, cached):
    value, why, source = cached[1]
    word, shape = STATES[value]
    key = str(root) if root is not None else None
    with _LOCK:
        active = dict(_ACTIVE.get(key) or {}) if key else {}
        last = dict(_LAST.get(key) or {}) if key else {}
    active.pop('cancel', None)
    out = {'schema': SCHEMA, 'state': value, 'word': word, 'shape': shape, 'why': why, 'source': source, 'at': cached[0],
           'fetching': (active or None) if value != 'offline' else None, 'last': last or None}      # 1.0 F3: never "her fetch" while it is down
    if active and value == 'offline':
        out['ending'] = active      # 1.0 F3: a fetch still closing after the network went down (cut short, never done)
    if out['fetching']:
        out['said'] = '%s %s: %s' % (STATES['fetching'][1], STATES['fetching'][0], active.get('host', ''))
    else:
        out['said'] = '%s %s' % (shape, word)
    return out


def peek(root=None, bus=None):
    """state() from what was read last, never reading the network now (for a paint); 'not known' until it is read."""
    from . import machine_real as mr
    with _LOCK:
        cached = _CACHE.get(mr.bus_kind(bus))
    return _compose(root, cached or (0, ('unknown', 'not read yet', '')))


def stale(bus=None):
    """Whether the state should be read again (the window reads it on its own timer)."""
    from . import machine_real as mr
    with _LOCK:
        cached = _CACHE.get(mr.bus_kind(bus))
    return cached is None or now_ms() - cached[0] > STATE_TTL_MS


def forget_state():
    """The next state() reads the network again (after a change you made in the Machine tab, say)."""
    with _LOCK:_CACHE.clear()


def needs_words(reading):
    """'needs the network: <why>' for a state that is not online."""
    return '%s: %s, %s' % (NEEDS, reading['word'], reading['why'])


# ================================================================================================== your words, as typed
LOOKUP = re.compile(
    r"^\s*(?:(?:kas(?:andra)?|please|hey)\s*[,:]?\s+)*(?:(?:could|can|would|will)\s+you\s+(?:please\s+)?)?(?:please\s+)?"
    r"(?P<verb>look\s+up|search\s+(?:the\s+web|the\s+internet|online|the\s+net)\s+for|search\s+for|search|find\s+online|"
    r"find\s+on\s+the\s+web|fetch|read\s+the\s+page|get\s+the\s+page)\s+(?P<rest>.+?)\s*[.?!]*\s*$", re.I)
TRAILING = re.compile(r"\s+(?:online|on\s+the\s+web|on\s+the\s+internet|on\s+the\s+net|for\s+me|please)\s*$", re.I)
ADDRESS = re.compile(r"(?<![\w@])(?:https?://[^\s<>\"'`]+|www\.[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s<>\"'`]*)?)", re.I)
# Words that point at the desk ("this", "it"): never resolved into search words, so nothing of the desk is sent.
POINTING = {'this', 'that', 'these', 'those', 'it', 'its', 'here', 'there', 'them', 'they', 'above', 'below', 'attached', 'open',
            'selected', 'current', 'same', 'one', 'ones'}
FILLER = {'the', 'a', 'an', 'for', 'me', 'please', 'of', 'on', 'about', 'some', 'any', 'my', 'our', 'your', 'online', 'web', 'internet'}
WORD = re.compile(r"[^\s\"“”«»<>(){}\[\],;:!?]+")
EDGE = "'‘’`.-"


def reads_as(request):
    """Whether your words ask her to look something up on the web, and how: {'kind': 'search' | 'fetch', 'start', 'end',
    'rest', 'verb'}, or None. Only the first line counts; a pasted block never does."""
    text = str(request or '')
    first = text.split('\n', 1)[0]
    m = LOOKUP.match(first)
    if not m:return None
    rest_start, rest_end = m.start('rest'), m.end('rest')
    t = TRAILING.search(first[rest_start:rest_end])
    if t:rest_end = rest_start + t.start()
    if rest_end <= rest_start:return None
    address = ADDRESS.search(first, rest_start, rest_end)
    verb = ' '.join(m.group('verb').lower().split())
    if verb == 'search' and not address:      # a bare "search X" stays the workspace's own search (the Search chooser)
        return None
    if address:
        end = address.end()
        while end > address.start() and first[end - 1] in '.,;:!?)':end -= 1
        return {'kind': 'fetch', 'start': address.start(), 'end': end, 'rest': first[address.start():end], 'verb': verb}
    return {'kind': 'search', 'start': rest_start, 'end': rest_end, 'rest': first[rest_start:rest_end], 'verb': verb}


def words_of(request):
    """The search words your typed request gives: {words, start, end, kept: [[start, end]], left_out: [{word, why}], to,
    host, sends}. Every word kept is a word you typed, in your order; "this", "it" and the like are left out (never resolved
    into what is on the desk), as are pasted blocks, words with characters you cannot see, numbers shaped like an account
    number or a key, and filler. A request that is not a lookup gives its own words (the Web reading page's box)."""
    from . import doorway
    text = str(request or '')
    read = reads_as(text)
    if read is not None and read['kind'] == 'fetch':
        return {'schema': SCHEMA, 'words': '', 'start': read['start'], 'end': read['end'], 'kept': [], 'left_out': [],
                'address': read['rest'], 'to': '', 'host': '', 'sends': '', 'kind': 'fetch'}
    start, end = (read['start'], read['end']) if read else (0, len(text.split('\n', 1)[0]))
    pasted = [(s['start'], s['end']) for s in doorway.quoted_spans(text) if s['kind'] == 'PASTED']
    door = doorway.scan(text[start:end])
    secret_spans = [(start + s, start + e) for n in door.secrets for s, e, kind in door.secrets[n]] if door.lines and len(door.lines) == 1 else []
    kept, left = [], []
    for m in WORD.finditer(text, start, end):
        s, e = m.start(), m.end()
        while s < e and text[s] in EDGE:s += 1
        while e > s and text[e - 1] in EDGE:e -= 1
        if s >= e:continue
        word = text[s:e]
        bare = word.replace('’', "'").casefold()
        if any(a <= s < b for a, b in pasted):left.append({'word': word, 'why': 'it was pasted, not typed'});continue
        if any(ord(c) in doorway.NAMES or doorway._invisible(ord(c)) for c in word):
            left.append({'word': doorway.skeleton(word)[0], 'why': 'it has characters you cannot see'});continue
        if any(a < e and s < b for a, b in secret_spans):left.append({'word': '[withheld]', 'why': 'a number shaped like an account number or a key is never sent'});continue
        if bare in POINTING:left.append({'word': word, 'why': 'it points at what is on the desk, and the desk is never sent'});continue
        if bare in FILLER:continue
        if bare.endswith("'s") and bare[:-2] in POINTING:left.append({'word': word, 'why': 'it points at what is on the desk, and the desk is never sent'});continue
        kept.append([s, e])
    if len(kept) > MOST_WORDS:
        for s, e in kept[MOST_WORDS:]:left.append({'word': text[s:e], 'why': 'past the first %d words' % MOST_WORDS})
        kept = kept[:MOST_WORDS]
    words = ' '.join(text[s:e] for s, e in kept)[:MOST_WORD_CHARS].strip()
    to = search_address(words) if words else ''
    host = urlsplit(to).hostname or '' if to else ''
    return {'schema': SCHEMA, 'kind': 'search', 'words': words, 'start': start, 'end': end, 'kept': kept, 'left_out': left,
            'to': to, 'host': host, 'sends': ('these words, to %s: %s' % (host, words)) if words else ''}


def search_address(words):
    template = os.environ.get(SEARCH_ENV) or SEARCH_ADDRESS
    if '{words}' not in template or not template.lower().startswith(('http://', 'https://')):template = SEARCH_ADDRESS
    return template.replace('{words}', quote_plus(words))


# ================================================================================================== an address
def check_address(text):
    """{address, host, site, scheme}: an http or https address with a host, no name and password in it, no fragment; or
    Refused with the reason."""
    raw = str(text or '').strip()
    if raw.lower().startswith('www.'):raw = 'https://' + raw
    if not raw or len(raw) > 2000 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw):
        raise Refused('WEB_ADDRESS: an address is one line of text with no spaces')
    parts = urlsplit(raw)
    if parts.scheme.lower() not in ('http', 'https'):raise Refused('WEB_ADDRESS: only http and https pages are fetched (not %s)' % (parts.scheme or 'this')[:20])
    if '@' in parts.netloc:raise Refused('WEB_ADDRESS: an address with a name or a password in it is never sent')
    host = (parts.hostname or '').lower()
    if not host:raise Refused('WEB_ADDRESS: the address names no site')
    try:port = parts.port
    except ValueError:raise Refused('WEB_ADDRESS: the port is not a number') from None
    try:host.encode('idna')
    except UnicodeError:raise Refused('WEB_ADDRESS: the site name cannot be written as an address') from None
    shown = host if port is None else '%s:%d' % (host, port)
    netloc = ('[%s]' % host if ':' in host else host) + ('' if port is None else ':%d' % port)
    address = urlunsplit((parts.scheme.lower(), netloc, parts.path or '/', parts.query, ''))
    return {'address': address, 'host': shown, 'site': 'site:' + shown, 'scheme': parts.scheme.lower()}


def _loopback(host):
    name = host.rsplit(':', 1)[0] if host.count(':') == 1 else host
    if name in ('localhost',):return True
    try:return ipaddress.ip_address(name.strip('[]')).is_loopback
    except ValueError:return False


# ================================================================================================== the fetch itself
class _Moved(Exception):
    def __init__(self, where):super().__init__(where);self.where = where


def _opener(address):
    import urllib.request

    class Same(urllib.request.HTTPRedirectHandler):
        max_redirections = MOST_REDIRECTS

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = urlsplit(newurl);old = urlsplit(req.full_url)
            if new.scheme.lower() not in ('http', 'https') or (new.hostname or '').lower() != (old.hostname or '').lower() or new.port != old.port:
                raise _Moved(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    host = (urlsplit(address).hostname or '').lower()
    proxies = {} if _loopback(host) else urllib.request.getproxies()
    return urllib.request.build_opener(urllib.request.ProxyHandler(proxies), Same)


def _fetch(address, cancel):
    """GET one address: {final, status, type, charset, body, complete}. No cookie, no referrer, no name; at most
    MOST_BYTES are read (in pieces, so HALT is heard between them)."""
    import urllib.error
    import urllib.request
    request = urllib.request.Request(address, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html, text/plain;q=0.9, */*;q=0.2',
                                                       'Accept-Encoding': 'identity'})
    try:
        response = _opener(address).open(request, timeout=TIMEOUT_S)
    except _Moved as moved:
        where = urlsplit(moved.where).hostname or moved.where[:80]
        raise Refused('WEB_MOVED: the page moved to another site (%s); it was not followed: fetch it there by your press' % where) from None
    except urllib.error.HTTPError as error:
        raise Refused('WEB_ANSWER: %s answered %d (%s); nothing was kept' % (urlsplit(address).hostname, error.code, str(error.reason)[:80])) from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        why = getattr(error, 'reason', error)
        raise Refused('WEB_UNREACHED: %s could not be reached (%s); nothing was kept' % (urlsplit(address).hostname, str(why)[:120])) from None
    import http.client
    with response:
        kind = (response.headers.get_content_type() or 'application/octet-stream').lower()
        charset = response.headers.get_content_charset() or ''
        declared = _declared(response.headers)      # 1.0 F3: the length the page said it has (none when chunked or unsaid)
        chunks, size, complete, cut = [], 0, True, ''
        while True:
            if cancel.is_set():
                if getattr(cancel, 'why', ''):      # 1.0 F3: the network went down while it came: what came is kept, cut short
                    complete, cut = False, cancel.why;break
                raise Refused('WEB_HALTED: HALT stopped her fetch; what was read is thrown away and nothing was kept')
            try:piece = response.read(65536)
            except (http.client.IncompleteRead, OSError) as broke:      # 1.0 F3: the connection broke (reset, timed out, ended early)
                part = getattr(broke, 'partial', b'') or b''
                if part:chunks.append(part);size += len(part)
                complete, cut = False, 'the connection broke after %d bytes (%s)' % (size, str(broke)[:80] or type(broke).__name__);break
            if not piece:break
            chunks.append(piece);size += len(piece)
            if size > MOST_BYTES:complete, cut = False, 'longer than the %d bytes kept' % MOST_BYTES;break
        if complete and declared is not None and size < declared:      # 1.0 F3: the connection ended before the page said it would
            complete, cut = False, 'the connection ended at %d of the %d bytes the page declared' % (size, declared)
        if complete and cancel.is_set() and getattr(cancel, 'why', ''):complete, cut = False, cancel.why      # 1.0 F3
        body = b''.join(chunks)[:MOST_BYTES]
        return {'final': response.geturl(), 'status': int(getattr(response, 'status', 200) or 200), 'type': kind, 'charset': charset,
                'body': body, 'complete': complete, 'cut': cut, 'declared': declared}


def _declared(headers):
    """1.0 F3: the page's declared length (Content-Length, identity encoding), or None when it declares none."""
    if (headers.get('Transfer-Encoding') or '').strip().lower() not in ('', 'identity'):return None
    try:
        value = int(str(headers.get('Content-Length') or '').strip())
    except ValueError:
        return None
    return value if value >= 0 else None


# ================================================================================================== a page, as text
SKIP = {'script', 'style', 'noscript', 'template', 'svg', 'math', 'iframe', 'object', 'embed', 'canvas', 'head', 'select', 'button'}
BLOCK = {'p', 'div', 'br', 'li', 'ul', 'ol', 'tr', 'table', 'section', 'article', 'header', 'footer', 'nav', 'main',
         'aside', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'blockquote', 'dt', 'dd', 'dl', 'figure', 'figcaption', 'hr', 'form',
         'address', 'caption', 'details', 'summary', 'label', 'fieldset', 'legend', 'body', 'html'}
VOID = {'br', 'img', 'meta', 'link', 'input', 'hr', 'wbr', 'area', 'base', 'col', 'embed', 'param', 'source', 'track'}
HIDING = re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])|opacity\s*:\s*0(?![.\d]*[1-9])', re.I)


class _Text(html.parser.HTMLParser):
    """A page's visible text in lines, what a browser hides (hidden elements, comments) apart, its title and its links."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base;self.stack = [];self.line = [];self.lines = [];self.hidden = [];self.links = [];self.title = []
        self.in_title = False;self.anchor = None

    def _hiding(self):return any(h for _, h, _ in self.stack)

    def _skipping(self):return any(s for _, _, s in self.stack)

    def flush(self):
        text = ' '.join(''.join(self.line).split())
        self.line = []
        if not text:return
        (self.hidden if self._hiding() else self.lines).append(text)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower();a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'title':self.in_title = True
        if tag in BLOCK:self.flush()
        if tag in ('td', 'th') and ''.join(self.line).strip():self.line.append(' · ')      # a table's row reads as one line
        if tag == 'a' and a.get('href'):
            target = urljoin(self.base, a['href'].strip())
            if urlsplit(target).scheme.lower() in ('http', 'https') and len(self.links) < MOST_LINKS:
                self.anchor = {'address': target.split('#', 1)[0], 'text': [], 'hidden': self._hiding()}
        if tag in VOID:return
        hides = 'hidden' in a or a.get('aria-hidden', '').lower() == 'true' or bool(HIDING.search(a.get('style', '')))
        if hides:self.flush()
        self.stack.append((tag, hides, tag in SKIP))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title':self.in_title = False
        if tag == 'a' and self.anchor is not None:
            self.anchor['text'] = ' '.join(''.join(self.anchor['text']).split())[:200]
            if not any(l['address'] == self.anchor['address'] for l in self.links):self.links.append(self.anchor)
            self.anchor = None
        if not any(t == tag for t, _, _ in self.stack):
            if tag in BLOCK:self.flush()
            return
        while self.stack:
            t, h, _ = self.stack[-1]
            if h or t in BLOCK:self.flush()      # while it is still open: its text goes where it belongs (hidden or seen)
            self.stack.pop()
            if t == tag:break

    def handle_data(self, data):
        if self.in_title:self.title.append(data);return
        if self._skipping():return
        self.line.append(data)
        if self.anchor is not None and not self._hiding():self.anchor['text'].append(data)

    def handle_comment(self, data):
        text = ' '.join(data.split())
        if text and not self._skipping():self.hidden.append('(a comment in the page) ' + text[:LINE_CHARS])

    def close(self):
        super().close();self.flush()


def _wrap(lines):
    out = []
    for line in lines:
        while len(line) > LINE_CHARS:
            cut = line.rfind(' ', 0, LINE_CHARS)
            cut = cut if cut > LINE_CHARS // 2 else LINE_CHARS
            out.append(line[:cut].rstrip());line = line[cut:].lstrip()
        if line:out.append(line)
    return out


def as_text(got):
    """{title, lines, hidden, links, readable, note}: what of a fetched body is read as text."""
    kind = got['type']
    if kind not in TEXT_TYPES and not kind.startswith('text/'):
        return {'title': '', 'lines': [], 'hidden': [], 'links': [], 'readable': False,
                'note': 'a %s: kept in quarantine with its digest; its text is not read here' % kind}
    charset = got.get('charset') or ''
    body = got['body']
    if not charset and kind in ('text/html', 'application/xhtml+xml'):
        m = re.search(rb'<meta[^>]+charset=["\']?([A-Za-z0-9_-]{2,40})', body[:4096], re.I)
        charset = m.group(1).decode('ascii') if m else ''
    try:text = body.decode(charset or 'utf-8', 'replace')
    except LookupError:text = body.decode('utf-8', 'replace')
    if kind in ('text/html', 'application/xhtml+xml'):
        parser = _Text(got['final'])
        try:
            parser.feed(text);parser.close()
        except Exception:  # noqa: BLE001 - a page too broken to read is kept, and said so
            return {'title': '', 'lines': [], 'hidden': [], 'links': [], 'readable': False, 'note': 'the page could not be read as text'}
        title = ' '.join(''.join(parser.title).split())[:200]
        return {'title': title, 'lines': _wrap(parser.lines)[:MOST_LINES], 'hidden': _wrap(parser.hidden)[:MOST_LINES], 'links': parser.links,
                'readable': True, 'note': ''}
    lines = [' '.join(l.split()) if kind != 'text/plain' else l.rstrip() for l in text.splitlines()]
    return {'title': '', 'lines': _wrap([l for l in lines if l.strip()])[:MOST_LINES], 'hidden': [], 'links': [], 'readable': True, 'note': ''}


# ================================================================================================== quarantine
def ensure(db):
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS web_pages_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied INTEGER NOT NULL)')
    applied = dict(db.execute('SELECT version, digest FROM web_pages_migrations'))
    known = {version: digest(list(sql)) for version, sql in MIGRATIONS}
    if any(known.get(v) != d for v, d in applied.items()):raise ValueError('WEB_MIGRATION_UNSUPPORTED: use a compatible program')
    for version, statements in MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        db.execute('INSERT INTO web_pages_migrations VALUES(?,?,?)', (version, known[version], now_ms()))


def _present(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_pages'").fetchone() is not None


def _area(kernel):
    return Path(kernel.dbpath).parent / 'quarantine' / 'web'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha(path):
    try:return _sha(Path(path).read_bytes())
    except OSError:return None


def _door(page):
    from . import doorway
    return doorway.scan('\n'.join(page.get('lines') or ()))


def _keep(kernel, principal, kind, where, got, read, by, words=''):
    """The page into quarantine: its bytes (read-only) and its record, in one go; its digest read back from disk."""
    ident = uuid.uuid4().hex;at = now_ms()
    area = _area(kernel);area.mkdir(parents=True, exist_ok=True)
    try:os.chmod(area, 0o700)
    except OSError:pass
    path = area / (ident + '.body')
    path.write_bytes(got['body'])
    os.chmod(path, 0o400)
    sha = _sha(got['body'])
    door = _door(read)
    try:final = check_address(got['final']) if got.get('final') else where
    except Refused:final = where
    payload = {'schema': PAGE, 'id': ident, 'owner': principal.identity, 'kind': kind, 'address': where['address'],
               'final': final['address'], 'host': where['host'], 'site': where['site'], 'at': at, 'status': got['status'],
               'type': got['type'], 'bytes': len(got['body']), 'sha256': sha, 'complete': bool(got['complete']),
               'cut': str(got.get('cut') or '')[:200], 'declared': got.get('declared'),      # 1.0 F3: why it is cut short, and the length it declared
               'title': read['title'], 'lines': read['lines'], 'hidden': read['hidden'], 'links': read['links'][:MOST_LINKS],
               'readable': read['readable'], 'note': read['note'], 'by': by, 'words': words,
               'door': {'rules': door.rules, 'withheld': door.withheld(), 'aimed': bool(door.aimed()), 'lines': len(door.lines)}}
    raw = canonical(payload)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ensure(db)
        db.execute('INSERT INTO web_pages VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (ident, principal.identity, at, kind, where['address'], where['host'], sha, len(got['body']), raw, _sha(raw.encode())))
    if _file_sha(path) != sha:raise Refused('WEB_NOT_KEPT: the page did not read back from quarantine with its digest')
    return payload


def _load(db, ident, owner):
    if not _present(db):raise ValueError('WEB_PAGE: there is no such page in quarantine')
    row = db.execute('SELECT payload, digest FROM web_pages WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if row is None:raise ValueError('WEB_PAGE: there is no such page in quarantine')
    value = json.loads(row[0]);value['intact'] = _sha(row[0].encode()) == row[1]
    return value


def admitted(kernel, owner, address):
    """Whether a page at this address is kept in quarantine for you already (a page you may fetch again under your grant)."""
    try:
        with kernel.db() as db:
            if not _present(db):return False
            return db.execute('SELECT 1 FROM web_pages WHERE owner=? AND address=? LIMIT 1', (owner, address)).fetchone() is not None
    except Exception:  # noqa: BLE001
        return False


def page_view(kernel, ident, principal):
    """One page: your view (every line, the withheld ones outlined with the reason), the card, the model's page (fenced,
    withheld lines replaced, hidden text left out), its links (data), and whether its bytes still read back."""
    from . import doorway
    with kernel.db() as db:value = _load(db, ident, principal.identity)
    door = _door(value)
    lines = doorway.owner_lines(door)
    hidden = [{'n': None, 'drawn': h, 'withheld': True, 'reasons': ['HIDDEN_ON_THE_PAGE'], 'words': HIDDEN_WORDS} for h in value.get('hidden') or ()]
    card = doorway.card(door)
    if hidden:
        card = (card + ' ' if card else '') + ('It also hides %d line%s a browser does not show; I kept %s from the model.'
                                               % (len(hidden), '' if len(hidden) == 1 else 's', 'it' if len(hidden) == 1 else 'them'))
    title = value.get('title') or value['host']
    model = doorway.page_message(door, title) if value.get('readable') else ''
    path = _area(kernel) / (ident + '.body')
    seen = _file_sha(path)
    return {'schema': PAGE, 'id': ident, 'kind': value['kind'], 'address': value['address'], 'final': value['final'], 'host': value['host'],
            'site': value['site'], 'at': value['at'], 'type': value['type'], 'bytes': value['bytes'], 'sha256': value['sha256'],
            'complete': value['complete'], 'title': value.get('title') or '', 'words': value.get('words') or '', 'by': value.get('by') or '',
            'readable': value.get('readable', True), 'note': value.get('note') or '',
            'lines': lines, 'hidden': hidden, 'withheld': door.withheld(), 'aimed': bool(door.aimed()),
            'card': card or doorway.CLEAN_WORDS, 'trail': doorway.trail_words(door, 'the page from %s' % value['host']),
            'owner_html': owner_html(door, value, hidden), 'model_page': model,
            'links': [dict(l, words='a link on the page: fetching it asks you, every time (it came from the page, not from you)')
                      for l in value.get('links') or ()],
            'intact': bool(value.get('intact')) and seen == value['sha256'],
            'quarantine': 'kept in quarantine: read as data only, through the door; nothing in it can start a step',
            'model_calls': 0}


def owner_html(door, value, hidden):
    """Your view as rich text: the doorway's own view (a withheld line outlined, with why in words), then what the page
    hides from a browser, each line outlined too."""
    from . import doorway
    e = _html.escape
    head = '<p><b>%s</b><br/><span>%s · fetched from %s · %s</span></p>' % (
        e(value.get('title') or value['host']), e(value['final'][:300]), e(value['host']), 'complete' if value['complete'] else
        'cut short at %d bytes%s' % (value['bytes'], (': ' + e(value['cut'])) if value.get('cut') else ''))      # 1.0 F3: and why
    body = doorway.owner_html(door, '') if value.get('readable', True) else '<p>%s</p>' % e(value.get('note') or '')
    rest = []
    for h in hidden:
        rest.append('<table width="100%%" border="1" cellspacing="0" cellpadding="4" style="border-style:dashed;border-color:#b5523b">'
                    '<tr><td><span style="font-family:monospace;white-space:pre-wrap">%s</span><br/><i>Not read to the model: this line %s.</i>'
                    '</td></tr></table>' % (e(h['drawn']), e(HIDDEN_WORDS)))
    if rest:rest.insert(0, '<p><b>Hidden on the page</b> (a browser does not show these)</p>')
    return head + body + '\n'.join(rest)


def listing(kernel, principal, limit=30):
    with kernel.db() as db:
        if not _present(db):return []
        rows = db.execute('SELECT payload, digest FROM web_pages WHERE owner=? ORDER BY at DESC LIMIT ?', (principal.identity, int(limit))).fetchall()
    out = []
    for raw, sha in rows:
        v = json.loads(raw)
        out.append({'id': v['id'], 'kind': v['kind'], 'title': v.get('title') or v['host'], 'host': v['host'], 'address': v['address'],
                    'at': v['at'], 'bytes': v['bytes'], 'complete': v['complete'], 'withheld': len((v.get('door') or {}).get('withheld') or ()),
                    'hidden': len(v.get('hidden') or ()), 'aimed': bool((v.get('door') or {}).get('aimed')), 'words': v.get('words') or '',
                    'intact': _sha(raw.encode()) == sha})
    return out


# ================================================================================================== who may send
def _halt_free(kernel):
    try:
        from . import halt_gate
        if halt_gate.held(kernel):raise Refused('WEB_HELD: HALT holds her work: nothing was fetched')
    except ImportError:
        pass


def _owners_press(principal):
    return 'approve' in principal.scopes and principal.mode != 'Tutor'


def _permit(kernel, site):
    """The permit a step's own dispatch runs in (K1 with K3's in_force): your press on that step, or your grant."""
    try:
        from . import grants
        if not grants.permitted_object(kernel, FETCH_OP, site):return None
        return (grants._PERMIT.get() or {}).get('grant') or 'your press'
    except Exception:  # noqa: BLE001 - without K3 there is no permit, so only your press fetches
        return None


def _online(kernel):
    reading = state(getattr(kernel, 'root', None), fresh=True)
    if reading['state'] != 'online':raise Refused('WEB_OFFLINE: %s. Nothing was sent.' % needs_words(reading))
    return reading


@contextlib.contextmanager
def _fetching(kernel, where, kind):
    key = str(getattr(kernel, 'root', ''))
    cancel = threading.Event();cancel.why = ''      # 1.0 F3: why it was cut ('' for HALT)
    with _LOCK:_ACTIVE[key] = {'host': where['host'], 'site': where['site'], 'at': now_ms(), 'kind': kind, 'cancel': cancel}
    try:
        yield cancel
    finally:
        with _LOCK:_ACTIVE.pop(key, None)


def _note_last(kernel, value):
    with _LOCK:_LAST[str(getattr(kernel, 'root', ''))] = value


def halt_stop(kernel, principal):
    """HALT's stop hook: her fetch in flight ends at its next piece; nothing of it is kept."""
    key = str(getattr(kernel, 'root', ''))
    with _LOCK:active = _ACTIVE.get(key)
    if not active:return ''
    active['cancel'].set()
    return 'her fetch from %s was stopped; nothing of it is kept' % active['host']


def _receipts(kernel, principal, op, where, page=None, refused=''):
    """Receipts (K2) of a fetch you pressed for directly; a step's own are written by its journal."""
    try:
        from . import grants
        if grants._PERMIT.get() is not None:return []
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import tools_registry as tr
        place = {'path': where['address'][:300]}
        if refused:
            return tr.record(kernel, tr.receipt('network.fetch', op, where['site'], 'refused', 'observed', False, refused, place=place, owner=principal.identity))
        sent = tr.receipt('network.fetch', op, where['site'], 'dispatched', 'observed', False, 'sent; the page is not yet read back from quarantine',
                          place=place, basis='the call came back', owner=principal.identity)
        whole = bool(page['complete'])      # 1.0 F3: a page cut short is kept, never verified
        done = tr.receipt('network.fetch', op, 'web:' + page['id'], 'verified' if whole else 'not verified', 'observed', whole,
                          ('kept in quarantine and read back with its digest (%d bytes from %s)' % (page['bytes'], page['host'])) if whole else
                          ('cut short, kept in quarantine as it came (%d bytes from %s): %s' % (page['bytes'], page['host'], page.get('cut') or 'not whole')),
                          revision=page['sha256'], place=place, basis='sha256', owner=principal.identity, follows=sent['id'])
        return tr.record(kernel, sent, done)
    except Exception:  # noqa: BLE001 - receipts that cannot be kept never undo the fetch
        return []


def _summary(page, door_count):
    whole = bool(page.get('complete', True))      # 1.0 F3: a page cut short is not a fetch that came
    return {'host': page['host'], 'at': page['at'], 'id': page['id'], 'title': page.get('title') or page['host'], 'kind': page['kind'],
            'withheld': door_count, 'hidden': len(page.get('hidden') or ()), 'ok': whole,
            'why': '' if whole else 'cut short: %s' % (page.get('cut') or 'it did not come whole')}


def _run(kernel, principal, kind, where, by, words=''):
    _halt_free(kernel)
    _online(kernel)
    try:
        with _fetching(kernel, where, kind) as cancel:
            got = _fetch(where['address'], cancel)
    except Refused as why:
        _note_last(kernel, {'host': where['host'], 'at': now_ms(), 'id': '', 'title': '', 'kind': kind, 'ok': False,
                            'why': str(why).split(': ', 1)[-1][:200], 'withheld': 0, 'hidden': 0})
        _receipts(kernel, principal, FETCH_OP if kind == 'page' else SEARCH_OP, where, refused=str(why).split(': ', 1)[-1])
        raise
    read = as_text(got)
    page = _keep(kernel, principal, kind, where, got, read, by, words)
    _note_last(kernel, _summary(page, len(page['door']['withheld'])))
    receipts = _receipts(kernel, principal, FETCH_OP if kind == 'page' else SEARCH_OP, where, page)
    view = page_view(kernel, page['id'], principal)
    view['receipts'] = [r.get('id') for r in receipts]
    view['said'] = 'Fetched from %s and kept in quarantine (%d bytes%s), read as data. %s' % (
        page['host'], page['bytes'], '' if page['complete'] else ', cut short: %s; not whole, so nothing rests on it' % (page.get('cut') or 'it did not come whole'),
        view['card'])      # 1.0 F3: why it is cut short
    return view


def get(kernel, args, principal):
    """web.get: one page into quarantine, by your press or in a step your press or grant let through."""
    where = check_address(args['page'])
    if principal.mode == 'Tutor':raise Refused('WEB_NOT_YOURS: Tutor never sends anything off this computer')
    if _owners_press(principal):by = 'your press'
    else:
        permit = _permit(kernel, where['site'])
        if permit is None:
            raise Refused('WEB_NOT_YOURS: a page is fetched by your press, or by a step of an assignment your press or your grant '
                          'let through; nothing was sent')
        by = 'your press on the step' if permit == 'your press' else 'your grant (%s)' % str(permit)[:32]
    return _run(kernel, principal, 'page', where, by)


def search(kernel, args, principal):
    """web.search: your words to the search service, by your press only (approve; always asks); the results page into
    quarantine, its links listed as data."""
    if not _owners_press(principal):raise Refused('WEB_NOT_YOURS: search words are sent only by your press')
    built = words_of(args['typed'])
    if built.get('kind') != 'search' or not built['words']:raise Refused('WEB_WORDS: your request gives no words to search for; nothing was sent')
    if ' '.join(args['words'].split()) != built['words']:
        raise Refused('WEB_WORDS: these are not the words built from what you typed ("%s"); nothing was sent' % built['words'][:80])
    where = check_address(built['to'])
    return _run(kernel, principal, 'search', where, 'your press', built['words'])


# ================================================================================================== an assignment from your words
def lookup(kernel, args, principal):
    """web.lookup: an assignment from your words, with one step that needs the network: a search with the words you typed,
    or a fetch of the address you typed. While the network is down the step is blocked at once: "needs the network"."""
    from . import assignments as A
    request = ' '.join(str(args['request']).split('\n', 1)[0].split())
    read = reads_as(request)
    if read is None:raise ValueError('WEB_NOT_A_LOOKUP: your words do not ask to look something up on the web ("look up …", "search the web for …", "fetch <address>")')
    if read['kind'] == 'fetch':
        where = check_address(read['rest'])
        step = {'key': 'fetch', 'title': 'Fetch the page from %s' % where['host'], 'operation': FETCH_OP, 'tool_key': 'network.fetch',
                'arguments': {'page': where['address']}, 'origins': {'page': {'kind': 'OWNER_WORDS', 'start': read['start'], 'end': read['end']}},
                'expected': 'the page, kept in quarantine and read as data through the door'}
        words = {'kind': 'fetch', 'address': where['address'], 'host': where['host']}
        title = 'Fetch %s' % where['host']
    else:
        words = words_of(request)
        if not words['words']:raise ValueError('WEB_WORDS: nothing of your words is left to search for (%s)' % '; '.join(
            '%s: %s' % (w['word'], w['why']) for w in words['left_out'][:3]))
        first, last = words['kept'][0][0], words['kept'][-1][1]
        step = {'key': 'search', 'title': 'Search the web for “%s”' % words['words'], 'operation': SEARCH_OP, 'tool_key': 'network.fetch',
                'arguments': {'words': words['words'], 'typed': request},
                'origins': {'words': {'kind': 'OWNER_WORDS', 'start': first, 'end': last}, 'typed': {'kind': 'OWNER_WORDS', 'start': 0, 'end': len(request)}},
                'expected': 'the results page, kept in quarantine and read as data; its links listed, none followed'}
        title = 'Look up %s' % words['words']
    value = A.start(kernel, {'objective': request, 'title': title[:200], 'steps': [step]}, principal)
    reading = state(getattr(kernel, 'root', None), fresh=True)
    blocked = ''
    if reading['state'] != 'online':
        blocked = needs_words(reading)
        block(kernel, value['id'], step['key'], blocked, principal)
        value = A.status(kernel, value['id'], principal)
    return {'schema': SCHEMA, 'assignment': value, 'words': words, 'state': reading, 'blocked': blocked, 'step': step['key'],
            'said': ('Step 1 is blocked: %s. Nothing was sent.' % blocked) if blocked else
                    ('%s waits for your press: %s' % (step['title'], words.get('sends') or 'the address goes to %s' % words.get('host')))}


def block(kernel, ident, key, reason, principal):
    """A step that needs the network while it is down: blocked, with the reason, before anything is prepared or sent."""
    from . import assignments as A
    with A._writing(kernel) as db:
        value = A._load(db, ident, principal)
        live = next((s for s in value['steps'] if s['key'] == key), None)
        if live is None or live['status'] not in ('proposed', 'authorised'):return False
        live.update(status='blocked', reason=reason)
        A._save(db, value);A._journal(db, value, live, 'BLOCKED', 'Step %d is blocked: %s. Nothing was sent.' % (live['n'], reason))
    return True


def waiting_on_network(kernel, principal, limit=8):
    """Your open assignments with a step blocked because the network was down: [{id, title, step, n, reason, operation}]."""
    from . import assignments as A
    out = []
    try:
        for row in A.active_work(kernel, principal, limit=limit):
            if row.get('state_words') != NEEDS:continue
            view = A.status(kernel, row['id'], principal)
            step = next((s for s in view['steps'] if s['status'] == 'blocked' and str(s['reason']).startswith(NEEDS)), None)
            if step:out.append({'id': view['id'], 'title': view['title'], 'step': step['key'], 'n': step['n'], 'reason': step['reason'],
                                'operation': step['operation'], 'digest': view['plan_digest']})
    except Exception:  # noqa: BLE001 - a column that cannot read this says nothing of it
        return out
    return out


# ================================================================================================== the check (K1 and K2)
try:
    from . import assignments as _asg
except Exception:  # noqa: BLE001 - without K1 there are no steps to check
    _asg = None


if _asg is not None:
    class WebFetch(_asg.Check):
        """web.get and web.search: done only when the page's bytes read back from quarantine with the digest its record
        holds. While the network is down the step is blocked, "needs the network", before anything is sent."""
        kind = 'web';effect = 'a page fetched from the web, kept in quarantine and read as data';standin_ms = 6000;repeatable = False
        how = "the page's bytes read back from quarantine with their digest"
        expected = 'the page, kept in quarantine and read as data through the door'

        def prepare(self, kernel, read, arguments):
            reading = state(getattr(kernel, 'root', None), fresh=True)
            if reading['state'] != 'online':raise _asg.Blocked(needs_words(reading))
            return {'state': reading['state'], 'why': reading['why']}

        def verify(self, kernel, read, arguments, result, prepared, step):
            if not isinstance(result, dict) or not result.get('id'):raise _asg.NotVerified('no page came back')
            seen = self._observed(kernel, result['id'], step)
            # 1.0 F3: verified only when the page is whole and the network is up as it is checked: a page cut short while the
            # network went down, or any page checked while it is down, is "needs the network", never done.
            reading = state(getattr(kernel, 'root', None), fresh=True)
            cut = '' if seen['complete'] else (seen.get('cut') or 'it did not come whole')
            if reading['state'] != 'online':
                raise _asg.Blocked('%s; %s' % (needs_words(reading), ('the page from %s was cut short (%s): kept in quarantine, not counted done' % (seen['host'], cut))
                                               if cut else 'the page from %s came, and the network is down as it is checked: not counted done' % seen['host']))
            if cut:raise _asg.NotVerified('the page from %s was cut short (%s): it is kept in quarantine and not counted done' % (seen['host'], cut))
            return seen

        @staticmethod
        def _observed(kernel, ident, step=None):
            with kernel.db() as db:
                row = db.execute('SELECT payload FROM web_pages WHERE id=?', (ident,)).fetchone() if _present(db) else None
            if row is None:raise _asg.NotVerified('the page is not in quarantine')
            value = json.loads(row[0])
            seen = _file_sha(_area(kernel) / (ident + '.body'))
            if seen != value['sha256']:raise _asg.NotVerified('the page does not read back from quarantine with its digest')
            held = len((value.get('door') or {}).get('withheld') or ()) + len(value.get('hidden') or ())
            return {'object': 'web:' + ident, 'revision': value['sha256'], 'by': 'sha256', 'complete': bool(value['complete']),
                    'cut': value.get('cut') or '',      # 1.0 F3
                    'how': 'observed', 'page': ident, 'host': value['host'], 'path': value['address'][:300],
                    'words': 'fetched from %s, kept in quarantine and read back (%d bytes%s); read as data, %d line%s withheld from the model'
                             % (value['host'], value['bytes'], '' if value['complete'] else ', cut short', held, '' if held == 1 else 's')}

        def still(self, kernel, read, step):
            ident = (step.get('observation') or {}).get('page')
            if not ident:return ''
            try:self._observed(kernel, ident)
            except _asg.NotVerified as why:return str(why)
            return ''
else:
    WebFetch = None


def available():
    return True, ''


def install():
    """Fill K2's slot for the network (tool 22), name its words for K1, and give HALT its stop."""
    try:
        from . import tools_registry as tr
        tool = tr.fill('network.fetch', available=available, operations=(FETCH_OP, SEARCH_OP), callable='workbench.network_governed:get',
                       check=WebFetch() if WebFetch else None)
        tool.arguments = (tr.Arg('page', "a page's address (http or https): one you typed, or a page already kept in quarantine",
                                 ('OWNER_WORDS', 'RECORD'), required=False),
                          tr.Arg('words', 'search words: your typed words only, never the desk', ('OWNER_WORDS',), required=False),
                          tr.Arg('typed', 'your request as you typed it (the words are built from it, and checked against it)',
                                 ('OWNER_WORDS',), required=False))
        tool.preconditions = ('the network is up (NetworkManager, or the system\'s routes)', 'HALT does not hold her work',
                              'your press; for a page, or your grant for its site')
        tool.grant = ('a page: your press, or your grant "fetch pages from the web" for its site (an address you typed, or a page '
                      'already in quarantine); search words: your press, every time')
        tool.verify = "the page's bytes read back from quarantine with their digest; its text read through the doorway"
    except Exception:  # noqa: BLE001 - without K2's registry the operations still stand
        pass
    if _asg is not None:
        _asg.TOOL_WORDS.setdefault('web', 'the web')
        _asg.GRANT_WORDS.setdefault(FETCH_OP, 'fetch a page from the web')
        _asg.GRANT_WORDS.setdefault(SEARCH_OP, 'send search words to the web')
    try:
        from . import halt_gate
        halt_gate.register_stop('web', halt_stop)
    except Exception:  # noqa: BLE001 - without K3 nothing holds a fetch but your own Stop
        pass


install()


# ================================================================================================== the Kernel's door
def dispatch(kernel, op, args, principal):
    if op == 'web.state':return state(getattr(kernel, 'root', None))
    if op == 'web.words':return words_of(args['request'])
    if op == 'web.lookup':return lookup(kernel, args, principal)
    if op == 'web.get':return get(kernel, args, principal)
    if op == 'web.search':return search(kernel, args, principal)
    if op == 'web.pages':return {'schema': SCHEMA, 'pages': listing(kernel, principal, args.get('limit', 30)),
                                 'state': state(getattr(kernel, 'root', None))}
    if op == 'web.page':return page_view(kernel, args['id'], principal)
    raise ValueError('Unknown web operation')
