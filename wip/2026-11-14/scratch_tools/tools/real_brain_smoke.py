"""Real-worker smoke of the model memory rules (0.8.1/0.8.2) with small models here; the owner's 35B is the target.
Auto activation of the 4B (its frozen headroom), a reply, a handover to the 2B (the launch waits for the old worker's memory),
and back. Run from a Graphite tree: python -B real_brain_smoke.py <tree> <4B.gguf> <2B.gguf> <new folder> <out.json>."""
import json, os, sys, time
from pathlib import Path
from unittest.mock import patch
tree, big, small, base, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
sys.path.insert(0, tree)
from workbench import locations, local_brain, resource_control
from workbench.baseline import environment
from workbench.engineering_kernel import Kernel, operator
base.mkdir(parents=True, exist_ok=False); home = base / 'Home'; home.mkdir(); root = base / 'Office'; profile = base / 'profile'
report = {'steps': []}
def note(name, **values):
    values['step'] = name; values['t'] = round(time.monotonic() - start, 1); report['steps'].append(values)
    print(json.dumps(values)[:400], flush=True); out.write_text(json.dumps(report, indent=1))
start = time.monotonic()
with patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home)}), patch.object(Path, 'home', return_value=home):
    locations.office(root); kernel = Kernel(root); p = operator()
    def call(op, args):
        r = kernel.dispatch(op, args, p)
        if not r.get('ok'):raise RuntimeError('%s refused: %s' % (op, r.get('error')))
        return r['result']
    def wait(job, limit=300):
        until = time.monotonic() + limit
        while kernel.record('jobs', job['id'])['state'] in ('Queued', 'Running') and time.monotonic() < until:time.sleep(.25)
        return call('brain.result', {'id': job['id']})
    try:
        host = local_brain.brain_runtime.host()
        note('host', available_mib=(host.get('available_ram_bytes') or 0) // 2**20, total_mib=(host.get('total_ram_bytes') or 0) // 2**20)
        ids = {}
        for name, path in (('4b', big), ('2b', small)):
            r = wait(call('brain.model.add', {'path': str(path), 'origin': 'Small reference model for a rules smoke here', 'managed_copy': False}))
            ids[name] = r['result']['model_id']; note('added ' + name, state=r['state'])
        job = call('brain.model.use', {'id': ids['4b'], 'options': {'context': 4096, 'threads': 4, 'backend': 'CPU'}})      # Auto: no memory cap
        frozen = job.get('brain_launch') or {}
        note('submitted 4b on Auto', memory_mb=(frozen.get('options') or {}).get('memory_mb'), auto_headroom_mb=frozen.get('auto_headroom_mb'),
             admission=(job.get('resource_request') or {}))
        r = wait(job); s = call('brain.status', {})
        note('4b activated', job=r['state'], status=s.get('state'), detail=str(r.get('result') or r.get('error'))[:200])
        r = wait(call('brain.ask', {'message': 'Say the word ready and nothing else.', 'mode': 'chat'}), 180)
        note('4b reply', job=r['state'], text=str((r.get('result') or {}).get('text') or r.get('error'))[:160])
        t0 = time.monotonic(); r = wait(call('brain.model.use', {'id': ids['2b'], 'options': {'context': 4096, 'threads': 4, 'backend': 'CPU'}}))
        s = call('brain.status', {})
        note('handover to 2b', job=r['state'], seconds=round(time.monotonic() - t0, 1), status=s.get('state'), model=str((s.get('selection') or {}).get('model_id', ''))[:12],
             detail=str(r.get('result') or r.get('error'))[:200])
        r = wait(call('brain.ask', {'message': 'Say the word ready and nothing else.', 'mode': 'chat'}), 180)
        note('2b reply', job=r['state'], text=str((r.get('result') or {}).get('text') or r.get('error'))[:160])
        t0 = time.monotonic(); r = wait(call('brain.model.use', {'id': ids['4b'], 'options': {'context': 4096, 'threads': 4, 'backend': 'CPU'}}))
        s = call('brain.status', {})
        note('handover back to 4b', job=r['state'], seconds=round(time.monotonic() - t0, 1), status=s.get('state'), detail=str(r.get('result') or r.get('error'))[:200])
        report['state'] = 'PASSED' if all(x.get('job', 'Completed') == 'Completed' for x in report['steps']) else 'FAILED'
    except Exception as exc:
        report['state'] = 'ERROR'; note('error', error=str(exc)[:600])
    finally:
        try:local_brain.stop(kernel, 'SMOKE_FINISHED')
        except Exception:pass
        out.write_text(json.dumps(report, indent=1)); print('SMOKE', report.get('state'), flush=True)
