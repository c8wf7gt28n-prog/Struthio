"""What is talking to the network (HATCH DESK D5): the assignment that inspects this computer's network without a model.

The owner, 2026-11-06: "we should probably add a network traffic scanner or packet sniffer capability that the agent can
inspect." The owner asks in plain words ("What is talking to the network?", "which programs are using the internet", "what
ports are open", "capture the traffic on port 443") and Graphite reads the network and writes a findings page. Explicit words
choose the profile (fits(); never a model). The steps, each one registered operation:

  observe   network.observe {filter?}           the interfaces, every connection and the process that holds it (read scope)
  packets   network.capture.read {limit, filter?}   the latest capture's packet summaries, when there is one (read scope)
  capture   network.capture.start {filter?, seconds, packets}
            only when the request asks for a capture and none is there to read. The Kernel refuses it (an assignment never
            holds the approve scope: NETWORK_CAPTURE_NEEDS_OWNER) and keeps it as the capture's proposal; the assignment waits
            with the proposal's words in Needs you. The owner starts it (Log, Network, Capture…, with D3's confirmation) or not,
            and Resume reads what was captured and writes the page. Graphite never starts a capture by itself.
  write     documents.create {title, text}      the page "What is talking to the network": the request, who talks to whom (a line
                                                per process), what listens, the interfaces, the capture's busiest conversations,
                                                and that nothing was sent anywhere
  done      'Wrote what is talking to the network: …; the findings page is in Documents'

Findings (the Work block's Found line): one per process with open conversations (at most TALKERS), one for what listens, one
for the capture. A capture that cannot run on this computer is a QUESTION with the reason and how to enable it. Nothing here
starts a worker, a model, a capture or a native tool.
"""
from __future__ import annotations
import re
import time
from . import agent_profiles as base

TALKERS = 8               # processes written as findings at most
REMOTES = 4               # far ends named per process
CONVERSATIONS = 6         # busiest captured conversations on the page
LISTENERS = 12            # listening sockets named on the page
READ_LIMIT = 1000         # packet summaries read from the latest capture
PROPOSED_SECONDS = 60     # the capture the assignment proposes: the Log view's own bounds
PROPOSED_PACKETS = 2000
TITLE = 'What is talking to the network'
PURPOSES = {'observe': 'Looking at this computer’s connections and the programs that hold them', 'packets': 'Reading the latest packet capture',
            'capture': 'Asking you for a packet capture', 'packets_again': 'Reading the capture you started', 'write': 'Writing the findings page'}
OWNER_WORDS = 'NETWORK_CAPTURE_NEEDS_OWNER'
QUIET = ('LISTEN', 'UNCONN', 'TIME_WAIT', 'CLOSE')

# The owner's words. A question or an inspecting verb, and the network named strongly: "connections" alone is the quiet
# connections' word, so it counts only beside network, internet, open, tcp or udp.
_ASK = re.compile(r'\b(what|which|who|whom|whose|show|list|inspect|check|look|see|watch|scan|sniff|capture|tell\s+me|is\s+(?:there\s+)?anything|are\s+there|how\s+much|anything)\b')
_NET = re.compile(r'\b(?:network|internet|traffic|bandwidth|packets?|sockets?|listening|phoning\s+home|talking\s+to|online|'
                  r'(?:network|internet|open|tcp|udp|active)\s+connections?|connections?\s+(?:to|on)\s+(?:the\s+)?(?:network|internet)|'
                  r'connected\s+to\s+(?:the\s+)?(?:network|internet)|open\s+ports?|ports?\s+(?:are\s+|is\s+)?(?:open|listening)|port\s+\d{1,5})\b')
_CAPTURE = re.compile(r'\b(?:captur\w*|sniff\w*|record\w*|tap|watch\w*|tail\w*)\b.*\b(?:traffic|packets?|network)\b|\bpacket\s+capture\b|\bsniff\w*\b')
_PORT = re.compile(r'\bport\s+(\d{1,5})\b|(?<![\d.]):(\d{1,5})\b', re.ASCII)   # ASCII digits, as network_watch's grammar takes them
_ADDRESS = re.compile(r'(?<![\w.:])(\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?)(?![\w.])', re.ASCII)
_PROTOCOL = re.compile(r'\b(tcp|udp)\b')


def plain(text):
    return ' '.join(str(text or '').replace('’', "'").casefold().split())


def fits(words):
    """True for a plain question about this computer's network (explicit words, never a model)."""
    text = plain(words)
    return bool(text) and bool(_ASK.search(text)) and bool(_NET.search(text))


def wants_capture(words):
    return bool(_CAPTURE.search(plain(words)))


def filter_of(words):
    """The filter the request names, in network_watch's grammar: its ports, its IPv4 addresses and networks, tcp or udp."""
    from .network_watch import parse_filter
    text = plain(words); parts = []
    for match in _ADDRESS.finditer(text): parts.append(match.group(1))
    for match in _PORT.finditer(text):
        number = match.group(1) or match.group(2)
        if number and 1 <= int(number) <= 65535: parts.append('port ' + number)
    parts += sorted(set(_PROTOCOL.findall(text)))
    candidate = ' '.join(dict.fromkeys(parts))
    return candidate if candidate and not parse_filter(candidate)['errors'] else ''


def endpoint(host, port, service=None):
    host = str(host if host not in (None, '') else '*')
    if ':' in host: host = '[' + host + ']'
    return host + (':%s' % port if port not in (None, '', 0) else '') + (' (%s)' % service if service else '')


def who(row):
    """The program that holds a socket, as observe named it; a closing socket has none, and one whose program this account
    cannot see (another namespace, a kernel socket) is said to be so, never guessed."""
    closing = row.get('state') in ('TIME_WAIT', 'CLOSE', 'FIN_WAIT1', 'FIN_WAIT2', 'CLOSING', 'LAST_ACK')
    name = row.get('process') or ('no program (closing)' if closing else 'a program Graphite cannot see')
    return name + (' (pid %s)' % row['pid'] if row.get('pid') else '')


def talkers(connections):
    """{who: {'remotes': [endpoint, ...], 'count': n}} for the connections that talk (not listening, not closing), busiest first."""
    out = {}
    for c in connections or []:
        if c.get('state') in QUIET or c.get('remote') in (None, '', '0.0.0.0', '::'): continue
        row = out.setdefault(who(c), {'remotes': [], 'count': 0, 'protocols': set()})
        row['count'] += 1; row['protocols'].add(str(c.get('proto') or '').rstrip('6'))
        far = endpoint(c.get('remote'), c.get('rport'), c.get('rservice'))
        if far not in row['remotes']: row['remotes'].append(far)
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]['count'], kv[0])))


def listeners(connections):
    rows = []
    for c in connections or []:
        if c.get('state') not in ('LISTEN', 'UNCONN'): continue
        local = c.get('local'); only_here = str(local).startswith('127.') or local == '::1'
        words = '%s on %s %s%s%s' % (who(c), str(c.get('proto') or '').rstrip('6'), c.get('lport'), (' (%s)' % c['lservice']) if c.get('lservice') else '',
                                     ', this computer only' if only_here else '')
        if words not in rows: rows.append(words)
    return rows


def conversations(packets):
    """The busiest captured conversations: (far end, packets, bytes, processes), by packets."""
    table = {}
    for p in packets or []:
        sport, dport = p.get('sport'), p.get('dport')
        if isinstance(sport, int) and isinstance(dport, int) and sport < dport: far = endpoint(p.get('src'), sport)
        else: far = endpoint(p.get('dst'), dport)
        row = table.setdefault((str(p.get('proto') or ''), far), [0, 0, set()])
        row[0] += 1; row[1] += int(p.get('length') or 0)
        if p.get('process'): row[2].add(p['process'])
    ranked = sorted(table.items(), key=lambda kv: (-kv[1][0], kv[0]))
    return [{'proto': k[0], 'far': k[1], 'packets': v[0], 'bytes': v[1], 'processes': sorted(v[2])} for k, v in ranked]


def size(count):
    count = int(count or 0)
    for unit, step in (('MB', 1e6), ('kB', 1e3)):
        if count >= step: return '%.1f %s' % (count / step, unit)
    return '%d bytes' % count


def plural(n, word, many=None):
    return '%s %s' % ('{:,}'.format(n), word if n == 1 else (many or word + 's'))


class NetworkTalk(base.Profile):
    name = 'network_talk'
    title = TITLE
    words = ('Reads this computer’s network (its interfaces, every connection and the program that holds it, and the latest packet '
             'capture), writes a findings page, and asks you before any capture.')
    needs = ()

    def fits(self, words): return fits(words)

    # -- planning -------------------------------------------------------------------------------------------------------------
    def plan(self, context, kernel, principal):
        return [base.step('observe', PURPOSES['observe'], 'network.observe', {}), base.step('packets', PURPOSES['packets'], 'network.capture.read', {})]

    def filter(self, state):
        context = state.get('context') or {}
        return context['filter'] if 'filter' in context else filter_of(state.get('request'))

    def arguments(self, step, state, kernel, principal):
        key = step['key']; text = self.filter(state); context = state.get('context') or {}
        if key == 'observe': return {'filter': text} if text else {}
        if key in ('packets', 'packets_again'): return dict({'limit': READ_LIMIT}, **({'filter': text} if text else {}))
        if key == 'capture': return dict({'seconds': PROPOSED_SECONDS, 'packets': PROPOSED_PACKETS}, **({'filter': text} if text else {}))
        if key == 'write': return {'title': TITLE, 'text': '\n'.join(self.page(state)), 'origin': 'SLATE'}
        return dict(step.get('arguments') or {})

    def write_step(self):
        return base.step('write', PURPOSES['write'], 'documents.create', {})

    # -- the page -------------------------------------------------------------------------------------------------------------
    def page(self, state):
        context = state.get('context') or {}; seen = context.get('seen') or {}; capture = context.get('capture') or {}
        lines = ['Request: “%s”' % ' '.join(str(state.get('request') or '').split())[:1000]]
        counts = seen.get('counts') or {}; by_state = counts.get('by_state') or {}
        lines.append('Looked at this computer’s network on %s · %s (%d established, %d listening)%s' % (
            time.strftime('%Y-%m-%d %H:%M'), plural(int(counts.get('connections') or 0), 'connection'), int(by_state.get('ESTABLISHED') or 0),
            int(by_state.get('LISTEN') or 0) + int(by_state.get('UNCONN') or 0), (' · filter: ' + context['filter']) if context.get('filter') else ''))
        for name, row in list((seen.get('talkers') or {}).items())[:TALKERS * 2]:
            lines.append('Talking: %s · %s · %s%s' % (name, plural(row['count'], 'connection'), ', '.join(row['remotes'][:REMOTES]),
                                                     ' and %d more' % (len(row['remotes']) - REMOTES) if len(row['remotes']) > REMOTES else ''))
        if not seen.get('talkers'): lines.append('Talking: no program has an open conversation right now.')
        listening = seen.get('listeners') or []
        lines.append('Listening: ' + ('; '.join(listening[:LISTENERS]) + (' and %d more' % (len(listening) - LISTENERS) if len(listening) > LISTENERS else '')
                                      if listening else 'nothing.'))
        if seen.get('interfaces'): lines.append('Interfaces: ' + ' · '.join(seen['interfaces']))
        lines.append(self.capture_line(context, capture))
        for row in (context.get('busiest') or [])[:CONVERSATIONS]:
            lines.append('Captured: %s %s · %s, %s%s' % (row['proto'], row['far'], plural(row['packets'], 'packet'), size(row['bytes']),
                                                       (' · ' + ', '.join(row['processes'])) if row['processes'] else ''))
        lines.append('Graphite read the system’s own tables (/proc and /sys) and the capture’s headers only; nothing was sent anywhere.')
        return lines

    def capture_line(self, context, capture):
        count = int(context.get('captured') or 0)
        if count:
            said = capture.get('filter') or (capture.get('last') or {}).get('filter')
            return 'Capture: %s from the latest capture%s.' % (plural(count, 'packet header'), (' (filter: %s)' % said) if said else '')
        if capture.get('state') == 'UNAVAILABLE': return 'Capture: not available on this computer. ' + str(capture.get('reason') or '')
        if context.get('proposed'): return 'Capture: Graphite proposed one; none was taken.'
        return 'Capture: none was taken. Ask Graphite to capture, or start one yourself in Log, Network.'

    # -- reading the results --------------------------------------------------------------------------------------------------
    def interpret(self, step, result, state, kernel, principal):
        key = step['key']; result = result if isinstance(result, dict) else {}; context = state.get('context') or {}
        if key == 'observe':
            rows = result.get('connections') or []
            found = talkers(rows)
            interfaces = ['%s %s' % (i.get('name'), 'up' if i.get('up') else 'down' if i.get('up') is False else 'state unknown') for i in result.get('interfaces') or []]
            seen = {'counts': result.get('counts') or {}, 'talkers': {k: {**v, 'protocols': sorted(v['protocols'])} for k, v in found.items()},
                    'listeners': listeners(rows), 'interfaces': interfaces}
            claims = [{'role': 'FINDING', 'text': '%s talks to %s' % (name, ', '.join(row['remotes'][:REMOTES]))} for name, row in list(found.items())[:TALKERS]]
            if seen['listeners']: claims.append({'role': 'FINDING', 'text': 'Listening: ' + '; '.join(seen['listeners'][:6])})
            if not found: claims.append({'role': 'FINDING', 'text': 'No program has an open conversation on the network right now.'})
            return {'context_updates': {'seen': seen, 'capture': dict(result.get('capture') or {}), 'filter': self.filter(state)}, 'claims': claims}
        if key in ('packets', 'packets_again'):
            packets = result.get('packets') or []; capture = dict(result.get('capture') or context.get('capture') or {})
            updates = {'captured': len(packets) + int(result.get('rest') or 0), 'busiest': conversations(packets)[:CONVERSATIONS], 'capture': capture}
            claims = []; then = [self.write_step()] if key == 'packets' else []   # after packets_again the write is already planned
            if packets:
                top = updates['busiest'][0]
                claims.append({'role': 'FINDING', 'text': 'The latest capture holds %s; the busiest conversation is %s %s (%s)' % (
                    plural(updates['captured'], 'packet header'), top['proto'], top['far'], plural(top['packets'], 'packet'))})
                return {'context_updates': updates, 'claims': claims, 'steps': then}
            if key == 'packets' and wants_capture(state.get('request')):
                if capture.get('state') == 'UNAVAILABLE':
                    claims.append({'role': 'QUESTION', 'text': 'A packet capture is not available on this computer: ' + str(capture.get('reason') or '')})
                    return {'context_updates': updates, 'claims': claims, 'steps': [self.write_step()]}
                return {'context_updates': updates, 'steps': [base.step('capture', PURPOSES['capture'], 'network.capture.start', {})]}
            return {'context_updates': updates, 'steps': then}
        if key == 'capture':   # never by this profile's own principal; kept for a capture the Kernel did start
            return {'context_updates': {'proposed': True}, 'waiting': 'A capture is running. Resume reads it and writes the page once it has finished.',
                    'steps': [base.step('packets_again', PURPOSES['packets_again'], 'network.capture.read', {}), self.write_step()]}
        if key == 'write':
            doc = result.get('document') if isinstance(result.get('document'), dict) else result
            if not doc.get('id'): return {'waiting': 'The findings page was not created; ask again.'}
            talking = len((context.get('seen') or {}).get('talkers') or {})
            count = int(((context.get('seen') or {}).get('counts') or {}).get('connections') or 0)
            return {'context_updates': {'document': doc['id'], 'documents': list(dict.fromkeys(list(context.get('documents') or []) + [doc['id']]))},
                    'done': True, 'reason': 'Wrote what is talking to the network: %s, %s talking; the findings page is in Documents' % (
                        plural(count, 'connection'), plural(talking, 'program'))}
        return {}

    def failed(self, step, error, state, kernel, principal):
        key = step['key']; words = str(error)
        if key == 'capture':
            if OWNER_WORDS in words:
                said = words.split('nothing was captured.', 1)[-1].strip() or 'Graphite proposes a packet capture; only you can start it.'
                return {'context_updates': {'proposed': True},
                        'waiting': said + ' Then Resume: Graphite reads the capture and writes the page (Resume without a capture writes it without one).',
                        'steps': [base.step('packets_again', PURPOSES['packets_again'], 'network.capture.read', {}), self.write_step()]}
            return {'waiting': 'The capture Graphite proposed was refused: %s. Resume writes the page without one.' % words, 'steps': [self.write_step()]}
        if key in ('packets', 'packets_again'):
            return {'waiting': 'The capture could not be read (%s). Resume writes the page without it.' % words, 'steps': [self.write_step()]}
        if key == 'observe':
            return {'waiting': 'This computer’s network could not be read (%s). Resume tries again.' % words}
        return {'waiting': 'Step %s (%s) did not run: %s' % (key, step.get('purpose') or key, words)}

    def done(self, state):
        """Finished only when the page is written (interpret says so), or when the plan runs out."""
        return False

    def describe(self, state):
        if state.get('state') in ('WAITING', 'DONE') and state.get('reason'): return str(state['reason'])
        current = self.next(state)
        if current is None: return super().describe(state)
        plan = state.get('plan') or []
        return '%s (step %d of %d)' % (current['purpose'], min(state.get('cursor', 0) + 1, len(plan)), len(plan))


PROFILE = NetworkTalk()
# agent_profiles registers this profile when it imports this module; when this module is imported first, register it here.
if base.PROFILES.get(PROFILE.name) is not PROFILE: base.register(PROFILE)
