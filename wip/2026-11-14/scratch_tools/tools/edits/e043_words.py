import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'stac_words.py', [('''    """What the writing line does with a typed line before anything else: a line about words becomes its operation line; a
    line that starts with one of the owner's words is written out. The second value says whether the words changed
    (so the next line reads them fresh)."""''', '''    """What the writing line does with a typed line before anything else: a line about words becomes the line it stands for,
    and a line that starts with one of the owner's words is written out. After a line that keeps or forgets a word, the
    words are read fresh the next time."""''')])
edit(W + 'engineering_kernel.py', [('''from . import field_service  # Graphite 0.4.1: the desk as something staC can read (field.read, field.trace, field.whatif: three reads, recorded additions)
''', '''from . import field_service  # Graphite 0.4.1: the desk as something staC can read (field.read, field.trace, field.whatif: three reads, recorded additions)
from . import stac_words  # Graphite 0.4.3: the owner's own staC words (words.list, words.keep, words.forget: recorded additions)
'''), ('''    **field_service.SCOPES,
''', '''    **field_service.SCOPES,
    **stac_words.SCOPES,
'''), ('''        if op in field_service.FIELDS:return field_service.dispatch(self,op,a,p)
''', '''        if op in field_service.FIELDS:return field_service.dispatch(self,op,a,p)
        if op in stac_words.FIELDS:return stac_words.dispatch(self,op,a,p)
''')])
edit(W + 'engineering_cli.py', [('''    from .field_service import FIELDS as FIELD_FIELDS
''', '''    from .field_service import FIELDS as FIELD_FIELDS
    from .stac_words import FIELDS as WORD_FIELDS
'''), ('''        **FIELD_FIELDS,
''', '''        **FIELD_FIELDS,
        **WORD_FIELDS,
''')])
edit(W + 'activity.py', [("""'field.read','field.trace','field.whatif','field.doubt','field.ripple','field.brief'})""", """'field.read','field.trace','field.whatif','field.doubt','field.ripple','field.brief','words.list'})""")])
edit(W + 'typebar_qt.py', [('''        try:                                  # `this` is the sheet selected in the Field: written out here, so what runs is what shows
            from .field_page import expand_this
            text = expand_this(self.host, text)
''', '''        try:                                  # the owner's own words, then `this` (the sheet selected in the Field): written out here, so what runs is what shows
            from .field_page import expand_this
            from .stac_words import written_out
            text = expand_this(self.host, written_out(self.host, text))
'''), ('''            try:
                from .field_page import expand_this
                written = expand_this(self.host, written)
            except ValueError:pass
''', '''            try:
                from .field_page import expand_this
                from .stac_words import command, expand, known_to
                written = expand_this(self.host, command(written) or expand(known_to(self.host), written))
            except ValueError:pass
''')])
edit(W + 'shell2.py', [('''        from .field_page import expand_this
        text = expand_this(host, text)        # `this`: the sheet selected in the Field
''', '''        from .field_page import expand_this
        from .stac_words import command, expand, known_to
        made = command(text)
        if made is not None and made.startswith('/'):      # keeping or forgetting a word changes something: it is not previewed, it is said
            return [('section', 'PREVIEW', None), ('note', ('Ctrl+Enter keeps this word' if made.startswith('/words.keep') else 'Ctrl+Enter forgets this word'), None)]
        text = expand_this(host, made or expand(known_to(host), text))        # the owner's words, then `this`: the sheet selected in the Field
''')])
print('ok')
