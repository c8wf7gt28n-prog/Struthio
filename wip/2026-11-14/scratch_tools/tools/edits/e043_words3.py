import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'stac_words.py', [('''KEEP = re.compile(r'^word\\s+([A-Za-z][A-Za-z0-9-]{1,23})\\s*=\\s*(\\S.*)$', re.DOTALL)
FORGET = re.compile(r'^forget\\s+([A-Za-z][A-Za-z0-9-]{1,23})\\s*$')
''', '''KEEP = re.compile(r'^word\\s+(\\S{1,40})\\s*=\\s*(\\S.*)$', re.DOTALL)        # the name is judged by words.keep, which says what a word may be
SHOW = re.compile(r'^word\\s+([A-Za-z][A-Za-z0-9-]{1,23})\\s*$')
FORGET = re.compile(r'^forget\\s+(\\S{1,40})\\s*$')
'''), ('''def keep(kernel, principal, name, line):
    line = ' '.join(str(line).replace('\\u200b', '').split())
    if _taken(name):
''', '''def _named(name):
    """The Kernel checks that a name is text; what a word may be is checked here, for every way of asking."""
    if not isinstance(name, str) or not re.fullmatch(NAME['pattern'], name):
        raise ValueError('A word is 2 to 24 small letters, digits or hyphens, and starts with a letter')
    return name


def keep(kernel, principal, name, line):
    name = _named(name);line = ' '.join(str(line).replace('\\u200b', '').split())
    if not 3 <= len(line) <= LINE['maxLength']:
        raise ValueError('A word keeps one staC line, at most %d characters' % LINE['maxLength'])
    if _taken(name):
'''), ('''def forget(kernel, principal, name):
    with kernel.db() as db:
''', '''def forget(kernel, principal, name):
    name = _named(name)
    with kernel.db() as db:
'''), ('''    gone = FORGET.match(text)
    if gone:
        return '/words.forget ' + json.dumps({'name': gone.group(1).lower()}, ensure_ascii=False, separators=(', ', ': '))
    if text.lower() == 'words':
        return 'words.list | pick words | select name,line'
    return None
''', '''    gone = FORGET.match(text)
    if gone:
        return '/words.forget ' + json.dumps({'name': gone.group(1).lower()}, ensure_ascii=False, separators=(', ', ': '))
    shown = SHOW.match(text)
    if shown:                                  # `word waits`: what that word stands for
        return 'words.list | pick words | where name=%s | select name,line' % shown.group(1).lower()
    if text.lower() == 'words':
        return 'words.list | pick words | select name,line'
    return None
''')])
edit(W + 'typebar_qt.py', [('''                written = expand_this(self.host, command(written) or expand(known_to(self.host), written))
            except ValueError:pass
            kind = stac_hint_kind(written) or kind
            words = {'stac': 'staC on Ctrl+Enter', 'inspect': 'Preview on Ctrl+Enter'}.get(kind)
''', '''                written = expand_this(self.host, command(written) or expand(known_to(self.host), written))
            except ValueError:pass
            kind = stac_hint_kind(written) or kind
            words = {'stac': 'staC on Ctrl+Enter', 'inspect': 'Preview on Ctrl+Enter'}.get(kind)
            if written.startswith(('/words.keep ', '/words.forget ')):      # a line about the owner's own words: it changes them, and says so
                kind, words = 'word', ('Keeps this word' if written.startswith('/words.keep ') else 'Forgets this word') + ' on Ctrl+Enter'
''')])
print('ok')
