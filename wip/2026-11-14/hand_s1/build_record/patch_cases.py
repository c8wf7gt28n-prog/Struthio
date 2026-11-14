p = 'tools/campaign_lib/cases_scene.py'
s = open(p).read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)


rep('''"""The scenes set (P01a..P01d): the owner's playable scene, played on a live offscreen window by desk acts alone.''', '''"""The scenes set: P01a..P01d, the owner's playable scene, played on a live offscreen window by desk acts alone; and since
Kasandra's hand, first slice, P02a..P02c (her door on the Field: the owner's words in Talk, her hand's acts) and P03a, P03b
(the owner takes the window back, and puts it back).''')
rep('''No model runs: the acts are the script.
"""''', '''No model runs: the acts are the script. P02 and P03 speak to her in Talk; her hand plans and acts with no model (the words
match her goals exactly), and each check of a step that speaks reads her record of the turn (`turn.*`) as well.
"""''')
rep("""RUNS = (('P01a', 'mouse'), ('P01b', 'keys'), ('P01c', 'mouse_still'), ('P01d', 'keys_still'))""", """RUNS = (('P01a', 'P01', 'mouse'), ('P01b', 'P01', 'keys'), ('P01c', 'P01', 'mouse_still'), ('P01d', 'P01', 'keys_still'),
        ('P02a', 'P02', 'mouse'), ('P02b', 'P02', 'mouse_still'), ('P02c', 'P02', 'ask'),
        ('P03a', 'P03', 'mouse'), ('P03b', 'P03', 'mouse_still'))
WORDS = {'mouse': 'by pointer', 'keys': 'by keys', 'mouse_still': 'by pointer, with less motion', 'keys_still': 'by keys, with less motion',
         'ask': 'at Ask first, then Approve'}""")
rep("""    out = {}
    for n, step in enumerate(scene['steps'], 1):
        want = dict(step.get('expect') or {})""", """    out = {}
    for n, step in enumerate(scene['steps'], 1):
        if 'only' in step and run_name not in step['only']:continue      # a step of another run
        want = dict(step.get('expect') or {})""")
rep("""        def after(n, step, row):
            settle()
            ctx.progress('act', n=n, act=step['act'], ok=row['ok'], by=row['by'], seconds=row['seconds'])""", """        def after(n, step, row):
            settle()
            ctx.progress('act', n=n, act=row['act'], ok=row['ok'], by=row['by'], seconds=row['seconds'])""")
rep("""def _cases():
    scene = load('P01');out = []
    for case_id, run_name in RUNS:
        run = next(r for r in scene['runs'] if r['name'] == run_name)
        words = {'mouse': 'by pointer', 'keys': 'by keys', 'mouse_still': 'by pointer, with less motion', 'keys_still': 'by keys, with less motion'}[run_name]
        out.append(Case(id=case_id, set='scenes', title='P01, the playable scene in After Hours 07, %s' % words, seed=SEED,
                        intent=scene.get('intent', scene['title']), needs=['after_hours_07'], budget_s=240,
                        inputs={'scene': 'P01', 'run': run_name, 'style': run['style'], 'reduce_motion': bool(run.get('reduce_motion'))},
                        expect=flattened(scene, run_name), fn=run_case))
    return out""", """def _cases():
    out = []
    for case_id, scene_id, run_name in RUNS:
        scene = load(scene_id)
        run = next(r for r in scene['runs'] if r['name'] == run_name)
        title = 'P01, the playable scene in After Hours 07' if scene_id == 'P01' else '%s, %s, in After Hours 07' % (scene_id, scene['title'])
        out.append(Case(id=case_id, set='scenes', title='%s, %s' % (title, WORDS[run_name]), seed=SEED,
                        intent=scene.get('intent', scene['title']), needs=['after_hours_07'], budget_s=240,
                        inputs={'scene': scene_id, 'run': run_name, 'style': run['style'], 'reduce_motion': bool(run.get('reduce_motion'))},
                        expect=flattened(scene, run_name), fn=run_case))
    return out""")
open(p, 'w').write(s)
print('ok')
