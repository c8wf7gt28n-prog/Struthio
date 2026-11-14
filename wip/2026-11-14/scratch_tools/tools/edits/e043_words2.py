import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'shell2.py', [('''    def ask(self, text, about=None):
        thing = self.what_if(text)
''', '''    def own_word(self, text):
        """A line that is one of the owner's own staC words (or says something about them), asked in conversation: she does
        what the line says. `word NAME = LINE` keeps and `forget NAME` lets go, said in a sentence; a word, or `words`, is
        read and shown as any staC line is. True when the line was one of these."""
        from .stac_words import command, expand, known_to
        made = command(text)
        if made is not None and made.startswith('/'):
            from .engine import engineering
            from .engineering_kernel import operator
            from .field_do import call as line_call
            self.thing = None;self.mine(text)
            operation, arguments = line_call(made)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
            self.host._stac_words = None
            self.say(str(r['result'].get('words') or 'Done.') if r.get('ok') else 'I could not: ' + str((r.get('error') or {}).get('message'))[:300])
            return True
        line = made if made is not None else expand(known_to(self.host), text)
        if line == text or str(line).lower().startswith('explain '):return False
        try:
            from .field_page import expand_this
            line = expand_this(self.host, line)
        except ValueError as exc:
            self.thing = None;self.mine(text);self.say(str(exc));return True
        self.thing = None;self.mine(text)
        name = text.strip().split()[0]
        self.answer_in_stac({'title': name, 'stac': line, 'kind': 'word'}, 'Your words, each with its line:' if made is not None else 'Your word “%s” is this line:' % name)
        return True

    def ask(self, text, about=None):
        if self.own_word(text):return
        thing = self.what_if(text)
''')])
print('ok')
