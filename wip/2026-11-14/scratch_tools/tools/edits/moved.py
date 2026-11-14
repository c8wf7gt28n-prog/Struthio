import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_model.py', [
("""    compact: bool = False               # a shelf of many small things: a sheet carries its name and state; the foot says the rest
""", """    compact: bool = False               # a shelf of many small things: a sheet carries its name and state; the foot says the rest
    moved: tuple = ()                   # results that changed when a calculation was brought up to date: (old words, new words, its title)
"""),
])
edit('workbench/field_source.py', [
("""        self.replaced = set()        # calculations another calculation says it replaces (a recheck makes a new page)
""", """        self.replaced = set()        # calculations another calculation says it replaces (a recheck makes a new page)
        self.results = {}            # a calculation's result as words ("3.36 W"), by its id
        self.replaces = {}           # new calculation id -> the id of the one it replaced
"""),
("""            if derivation and derivation.get('replaces'):self.replaced.add('document:' + str(derivation['replaces']))""",
 """            if derivation and derivation.get('replaces'):
                self.replaced.add('document:' + str(derivation['replaces']));self.replaces[ident] = 'document:' + str(derivation['replaces'])
            value = ((((derivation or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value')
            if isinstance(value, dict) and value.get('decimal') is not None:
                self.results[ident] = ('%s %s' % (value['decimal'], value.get('unit') or '')).strip()"""),
("""    if not title and len(investigations) == 1:
        question, state = investigations[0]""", """    moved = _moved(reader)
    for obj in reader.objects:   # a finding whose words still carry a result that has since been worked again: it waits, and says which
        if obj.kind != 'finding' or obj.state != STATE_CURRENT:continue
        for was, now, name in moved:
            if was in obj.title and now not in obj.title:
                obj.state = STATE_RECHECK;obj.lines = ('says %s; now %s' % (was, now),) + tuple(obj.lines)[:2];break
    if not title and len(investigations) == 1:
        question, state = investigations[0]"""),
("""    return Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside), reader


# ---- the programs face""", """    return Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside, moved=moved), reader


def _moved(reader):
    \"\"\"Results that changed when a calculation was brought up to date: (old words, new words, the calculation's title), the new
    words being those of the page that stands now, however many times it was worked again. A match of words, not a recorded
    link: it is how the desk notices a finding that still quotes the old number.\"\"\"
    newer = {old: new for new, old in reader.replaces.items()};out = []
    for old in newer:
        last = old;hops = 0
        while last in newer and hops < 50:last = newer[last];hops += 1
        was = reader.results.get(old);now = reader.results.get(last)
        if was and now and was != now and (was, now, reader.names.get(last, '')) not in out:out.append((was, now, reader.names.get(last, '')))
    return tuple(out)


# ---- the programs face"""),
])
edit('workbench/field_do.py', [
("""    if path and path.get('review') == 'NEEDS_REVIEW':""", """    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if was in obj.title and now not in obj.title), None) if finding else None
    if quoted:                                # its words carry a result that has since been worked again
        was, now, name = quoted
        out.append(Step('Write it again with %s' % now, 'write', op('investigation.claim', id=inv, text=str(obj.title).replace(was, now), role='FINDING'),
                        'a new finding with the number “%s” gives now; it stands on nothing until its sources are cited for it' % name, 'execute'))
        if not (path and path.get('review') == 'NEEDS_REVIEW'):
            out.append(Step('Retire this one', 'write', op('investigation.review', claim=claim, decision='RETIRE'),
                            'it is taken out of what is known; its words say %s' % was, 'approve'))
    if path and path.get('review') == 'NEEDS_REVIEW':"""),
("""    for obj in field.objects:
        if obj.needs_attention():
            waiting.append((obj, obj.state, steps_for(kernel, principal, obj, field)));seen.add(obj.id)""",
 """    for obj in field.objects:
        if obj.needs_attention():
            why = obj.state
            if obj.kind == 'finding':
                quoted = next(((was, now, name) for was, now, name in field.moved if was in obj.title and now not in obj.title), None)
                if quoted:why = 'its words say %s; “%s” now gives %s' % quoted[:1] + (quoted[2], quoted[1])
            waiting.append((obj, why, steps_for(kernel, principal, obj, field)));seen.add(obj.id)"""),
])
print('edits applied')
