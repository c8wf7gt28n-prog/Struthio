import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)
edit('workbench/field_do.py', [
("""    if not steps and obj.stac:
        steps = [Step('See what the records say about it', 'read', obj.stac)]
    return [step for step in steps if step.line][:9]""",
 """    if not steps and obj.stac:
        steps = [Step('See what the records say about it', 'read', obj.stac)]
    return [step for step in (_by_scope(step) for step in steps if step.line) if step is not None][:9]


def _by_scope(step):
    \"\"\"Whether a step runs by itself is the Kernel's word, not this module's: a line whose operation the Kernel registers as a
    read runs at once; any other scope waits for the owner, whatever the step was written as. A staC line is a read by the
    language's own rule (it refuses anything else). An operation the Kernel does not know is not offered.\"\"\"
    try:
        operation, _ = call(step.line)
    except (ValueError, TypeError):
        return None
    if not step.line.strip().startswith('/'):
        step.kind = 'read';step.scope = 'read';return step
    from .engineering_kernel import CAPABILITIES
    scope = CAPABILITIES.get(operation)
    if scope is None:return None
    step.scope = scope;step.kind = 'read' if scope == 'read' else 'write'
    return step"""),
])
edit('workbench/shell2.py', [
("""        if card.ran is not None:return           # one go, one run
        operation, arguments = line_call(card.step.line)
        r = engineering(self.host.root).dispatch(operation, arguments, operator())""",
 """        if card.ran is not None:return           # one go, one run
        try:
            operation, arguments = line_call(card.step.line)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
        except Exception as exc:  # noqa: BLE001 - a line that cannot be run is said as a refusal, never raised into the window
            r = {'ok': False, 'error': {'message': str(exc)[:300]}}"""),
("""            operation, arguments = line_call(step.line)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
            ok = bool(r.get('ok'));card.results.append""",
 """            try:
                operation, arguments = line_call(step.line)
                r = engineering(self.host.root).dispatch(operation, arguments, operator())
            except Exception as exc:  # noqa: BLE001 - said as a refusal; the list stops here
                r = {'ok': False, 'error': {'message': str(exc)[:300]}}
            ok = bool(r.get('ok'));card.results.append"""),
])
print('edits applied')
