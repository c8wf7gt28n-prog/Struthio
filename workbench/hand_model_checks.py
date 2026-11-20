"""Her hand's GOAL turn on a real local model: three requests, their goals frozen here before any model runs. needs: model.

Kasandra's hand, first slice. The GOAL turn is the one question her hand asks a model on the desk: which of these numbered
goals did the owner mean (pick mode, local_brain; the goals and the answer's reading are hand_words'). This check asks it
directly, without the deterministic match first, so it measures the model and nothing else.

The desk is the bench window's: Rail Demo bench readings, and Rail Demo limits in two revisions (Rev A ARCHIVED, Rev B CURRENT). The
requests, and the goals each must give (in the order said), are frozen in REQUESTS:

  1. "show me where the bench readings come from"                                 the trace of Rail Demo bench readings
  2. "where do the bench readings come from, and put the limits side by side"     that trace, then the two limits side by side
  3. "what's for dinner"                                                          none of these

It passes when every answer is exact, every turn takes at most 60 s, every prompt is at most 1,200 tokens and every answer
at most 32. It records each turn's seconds, its prompt and output tokens, prefill and decode speed, the tokens the model
reused from its last prompt (cache_n), and any goal picked beyond what was asked (over-picking). The model runs at a
4,096-token context with 4 threads, as on the machine this was built on; `--repeats` plays the three requests again on the
same model (the done rule asks for three runs).

    python -B -m workbench.hand_model_checks --model Qwen3.5-4B-Q4_K_M.gguf --keep <a new folder> --output result.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

from . import desk_ops, hand_words, locations, local_brain
from .baseline import environment
from .problem_checks import invoke

NEEDS = ('model',)
WORLD = desk_ops.World((desk_ops.Sheet('Rail Demo bench readings'),
                        desk_ops.Sheet('Rail Demo limits Rev A ARCHIVED', 'sheet', 'Rail Demo limits Rev B CURRENT', True),
                        desk_ops.Sheet('Rail Demo limits Rev B CURRENT', 'sheet', 'Rail Demo limits Rev A ARCHIVED', False)))
TRACE_BENCH = ('traced', {'s': 'Rail Demo bench readings'})
LIMITS_SIDE = ('side_by_side', {'a': 'Rail Demo limits Rev A ARCHIVED', 'b': 'Rail Demo limits Rev B CURRENT'})
REQUESTS = (
    {'name': 'trace', 'text': 'show me where the bench readings come from', 'expect': [TRACE_BENCH]},
    {'name': 'trace_and_side', 'text': 'where do the bench readings come from, and put the limits side by side', 'expect': [TRACE_BENCH, LIMITS_SIDE]},
    {'name': 'none', 'text': "what's for dinner", 'expect': []},
)
BOUNDS = {'seconds': 60.0, 'prompt_tokens': local_brain.PICK_PROMPT, 'output_tokens': local_brain.PICK_OUTPUT}
CONFIG = {'context': 4096, 'threads': 4, 'memory_mb': 4480}


def frozen():
    """What is fixed before inference: the requests, their goals, the bounds and the model's configuration."""
    return {'schema': 'graphite.hand-goal-check/1', 'frozen_before_inference': True, 'world': [s.title for s in WORLD.sheets],
            'requests': [{'name': r['name'], 'text': r['text'], 'expect': r['expect']} for r in REQUESTS],
            'bounds': BOUNDS, 'model_config': CONFIG, 'deterministic_match_bypassed': True,
            'expected_answers_exposed_to_model': False}


def ask(kernel, p, request):
    """One GOAL turn: the numbered goals, the model's pick, read by hand_words.read_pick (in local_brain)."""
    cands = hand_words.candidates(request['text'], WORLD)
    message = hand_words.pick_message(request['text'], cands)
    started = time.monotonic()
    job = invoke(kernel, 'brain.ask', {'message': message, 'mode': 'pick', 'picks': len(cands) + 1}, p)
    until = time.monotonic() + 180
    while kernel.record('jobs', job['id'])['state'] in ('Queued', 'Running') and time.monotonic() < until:time.sleep(0.05)
    seconds = time.monotonic() - started
    result = invoke(kernel, 'brain.result', {'id': job['id']}, p)
    out = {'name': request['name'], 'text': request['text'], 'candidates': [hand_words.ask_words(*c) for c in cands], 'seconds': round(seconds, 3),
           'job_state': result['state']}
    body = result.get('result') or {}
    metrics = body.get('metrics') or {};usage = metrics.get('usage') or {};timings = metrics.get('timings') or {}
    out.update(model_seconds=round(float(metrics.get('elapsed_seconds') or 0.0), 3), prompt_tokens=usage.get('prompt_tokens') or metrics.get('prompt_tokens_measured'),
               output_tokens=usage.get('completion_tokens'), prefill_tokens_per_second=timings.get('prompt_per_second'),
               decode_tokens_per_second=timings.get('predicted_per_second'), cache_n=timings.get('cache_n'),
               reused_tokens=metrics.get('observed_reused_tokens'), first_token_seconds=metrics.get('first_token_seconds'))
    proposal = body.get('proposal') or {}
    if result['state'] != 'Completed' or 'pick' not in proposal:
        out.update(valid=False, picked=None, exact=False, reason=str(body.get('reason') or result.get('error') or result['state'])[:400])
        return out
    picked = [list(cands[n - 1]) for n in proposal['pick']]
    want = [list(e) for e in request['expect']]
    out.update(valid=True, pick=proposal['pick'], picked=picked, exact=picked == want, over_picking=max(0, len(picked) - len(want)),
               missed=[w for w in want if w not in picked])
    return out


def passes(turn):
    return bool(turn.get('exact')) and turn['seconds'] <= BOUNDS['seconds'] and (turn.get('prompt_tokens') or 10 ** 9) <= BOUNDS['prompt_tokens'] \
        and (turn.get('output_tokens') or 10 ** 9) <= BOUNDS['output_tokens']


def checks(model_path, base, output=None, repeats=1):
    from .engineering_kernel import Kernel, operator
    base = Path(base);base.mkdir(parents=True, exist_ok=False);home = base / 'Home';home.mkdir();root = base / 'Office';profile = base / 'profile'
    spec = frozen();(base / 'frozen-evaluation.json').write_text(json.dumps(spec, indent=2) + '\n')
    with patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home)}), patch.object(Path, 'home', return_value=home):
        locations.office(root);kernel = Kernel(root);p = operator()

        def wait(job):
            until = time.monotonic() + 300
            while kernel.record('jobs', job['id'])['state'] in ('Queued', 'Running') and time.monotonic() < until:time.sleep(0.2)
            result = invoke(kernel, 'brain.result', {'id': job['id']}, p)
            if result['state'] != 'Completed':raise ValueError('The model did not start: ' + str(result)[:600])
            return result['result']
        registered = wait(invoke(kernel, 'brain.model.add', {'path': str(Path(model_path).resolve()), 'origin': 'Explicit local model file for the GOAL turn check.',
                                                              'managed_copy': False}, p))
        if hasattr(os, 'posix_fadvise'):
            with Path(model_path).open('rb') as stream:os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
        started = time.monotonic()
        activation = wait(invoke(kernel, 'brain.model.use', {'id': registered['model_id'], 'options': CONFIG}, p))
        value = {'state': 'IN_PROGRESS', 'model': Path(model_path).name, 'activation_seconds': round(time.monotonic() - started, 3),
                 'config': CONFIG, 'bounds': BOUNDS, 'runs': [], 'cloud_calls': 0}
        try:
            for n in range(int(repeats)):
                turns = [ask(kernel, p, r) for r in REQUESTS]
                value['runs'].append({'run': n + 1, 'turns': turns, 'passed': all(passes(t) for t in turns)})
                if output:Path(output).write_text(json.dumps(value, indent=2) + '\n')
            value['state'] = 'PASSED' if value['runs'] and all(r['passed'] for r in value['runs']) else 'FAILED'
            if output:Path(output).write_text(json.dumps(value, indent=2) + '\n')
            return value
        finally:
            local_brain.stop(kernel, 'HAND_GOAL_CHECK_FINISHED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True);parser.add_argument('--keep', type=Path, required=True)
    parser.add_argument('--output', type=Path);parser.add_argument('--repeats', type=int, default=1)
    args = parser.parse_args()
    value = checks(args.model, args.keep, args.output, args.repeats)
    print(json.dumps({'state': value['state'], 'runs': [[(t['name'], t['seconds'], t.get('prompt_tokens'), t.get('output_tokens'), t.get('exact')) for t in r['turns']] for r in value['runs']]}))
    return 0 if value['state'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
