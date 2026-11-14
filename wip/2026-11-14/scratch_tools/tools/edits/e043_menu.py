import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'context_menu.py', [('''                     ('What I doubt', 'field.doubt | pick rows | where verdict=doubt | select title,about,why'),
''', '''                     ('What I doubt', 'field.doubt | pick rows | where verdict=doubt | select title,about,why'),
                     ('The brief, line by line', 'field.brief | pick lines | select text'),
'''), ('''                     ('Work that is not finished', 'jobs | where state is not Completed | select tool,state'))
        out.append(Entry('field:stac', 'This face in staC', 'command', icon='line', tip='Read-only staC lines for what the Field shows; each goes to the writing strip',
''', '''                     ('Work that is not finished', 'jobs | where state is not Completed | select tool,state'))
            out.append(Entry('field:brief', 'The brief', 'command', view.brief_asked.emit, icon='line', caption='B',
                             tip='The desk written up as one page, from the records. Stacy shows every line; keeping it as a page asks first'))
        try:                                  # the owner's own staC words go with the lines of every face
            from .stac_words import known_to
            lines = tuple(lines) + tuple(('Your word “%s”' % name, code) for name, code in sorted(known_to(host).items()))
        except Exception:  # noqa: BLE001 - the menu is never stopped because the words could not be read
            pass
        out.append(Entry('field:stac', 'This face in staC', 'command', icon='line', tip='Read-only staC lines for what the Field shows; each goes to the writing strip',
'''), ('''    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     tip='The steps the records offer for this. A read runs at once; one that changes something asks first'))
''', '''    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     tip='The steps the records offer for this. A read runs at once; one that changes something asks first'))
    if view.face == 'work':
        out.append(Entry('field:brief', 'The brief of the desk', 'command', view.brief_asked.emit, icon='line', caption='B',
                         tip='The whole desk written up as one page, from the records. Stacy shows every line; keeping it as a page asks first'))
''')])
print('ok')
