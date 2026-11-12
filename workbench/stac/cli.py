"""Command-line access to typed evidence, the chronicle, and private staC exports."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .language import CompileError, Context, compile_text, intent_hash
from .runtime import RunError, evaluate
from . import chronicle, semantics, controlled_language, redirection

HELP = '''staC 0.6 — evidence-driven ARC engineering intent + chronology

Syntax: use ARC1@R10 | part U45 | fact tCEM | COMMAND

Commands:
  use ARC1@R10    Historical native source context (first stage)
  use LEDGER@CURRENT  Registered Ledger job evidence context (read-only)
  spec U45.tCEM   Short form: part | fact | claim | witness | verify
  assess U45.tCEM Short form: verified requirement | compliance assessment
  why U45.tCEM   Short form: verified source-provenance lookup
  gaps U45.tCEM  Short form: missing trusted evidence obligations
  result JOB_ID   Short form: job ID | verify-test (32 lower-hex job ID)
  job JOB_ID      Read a registered Kernel job (no execution)
  verify-test     Correlate fresh Kernel job/evidence; NEVER hardware qualification
  part U45        Inspect native component through Ledger Brain Link
  trace U23 J10   Inspect schematic path (never routed or physical proof)
  rom status      Report mounted reference volumes
  vendor status   Report vendor-original availability
  fact tCEM       Exact reviewed source/variant binding or explicit UNKNOWN
  why             Display source identities and qualification limitations
  gaps            Show observable unresolved proof obligations
  assess          Evaluate whether a bound fact actually proves compliance
  suppose 2.5us   Exact hypothetical value, not a test or measurement
  compare < 3us   Typed predicate (< <= > >= == !=), no proof of hardware
  > NAME.json     Export JSON result within .ledger/stac/io/exports (use --json)
  >> NAME.ndjson  Append a single JSON record to an export file (use --json)
  2> NAME.log     Write errors only to an export file
  < NAME.stac     Run a pre-existing one-line script from .ledger/stac/io/scripts
  challenge       List falsification questions, with no tool invocation
  packet          Compile local-only versioned Engineering Knowledge Packet
  question        Construct a typed, unresolved engineering compliance question
  obligations     Inspect structured, source-qualified proof obligations
  claim           Construct an unverified typed vendor-requirement claim
  witness         Attach a candidate original-page locator (not verified yet)
  verify          Independently re-check original page, source identity and fitment

Examples:
  stac run 'use ARC1@R10 | spec U45.tCEM | why'
  stac run 'use ARC1@R10 | assess U45.tCEM | gaps'
  stac run 'use LEDGER@CURRENT | result aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | gaps'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | why'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | gaps'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | assess'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | suppose 2.5us'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | suppose 2.5us | compare <= 3us'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | challenge'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | packet' --json
  stac compile 'use ARC1@R10 | part U45 | fact tCEM | packet' --json
  stac semantics 'use ARC1@R10 | part U45 | fact tCEM | question' --json
  stac translate 'What evidence is missing for U45 tCEM in ARC-1 R10?' --json
  stac run 'use ARC1@R10 | part U45 | fact tCEM | question | obligations'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | claim | witness | verify'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | claim | witness | verify | gaps'
  stac run 'use ARC1@R10 | part U45 | fact tCEM | suppose 2.5us | compare < 3us > timing.json' --json
  stac run '< memory.stac >> observations.ndjson' --json
  stac run - --json < program.stac > output.json 2> errors.log
  stac repl
  stac chronicle record 'use ARC1@R10 | part U45 | fact tCEM | gaps'
  stac chronicle history --component U45
  stac chronicle known-at 2026-10-26T10:00:00Z --component U45
  stac chronicle whatif --changed-source cad/path_from_recorded_manifest
  stac chronicle verify
  stac chronicle seal
  stac chronicle kernel-tail --limit 10

No shell expansion, arbitrary SQL, web/model calls, executing tests or design
mutations. Internal redirection is a separate bounded USER export/read layer;
ordinary host UNIX shell redirection can use any path authorized by the OS.
No `2>&1`, here-documents, or shell command substitution inside staC.
Chronicle recording is opt-in and only stores compact read observations
under .ledger/stac/. A prediction/whatif NEVER invokes a tool. Packet export is LOCAL ONLY; external sharing requires a separate
approval and redaction workflow not available in this release.
'''


def _human(data):
    if data.get('ok') is False:return 'staC error: '+str(data.get('error','unknown error'))
    if data.get('schema') in ('arc.stac.ir/0.2','arc.stac.ir/0.4','arc.stac.ir/0.5','arc.stac.ir/0.6'):
        return (f"COMPILED {data['result_type']} · effects={','.join(data['effects']) or 'none'}\n"
                f"intent_digest={intent_hash(data)}\nbinding=SYMBOLIC_UNPINNED")
    result=data.get('result',{})
    kind=result.get('type');value=result.get('payload',{})
    lines=[f'staC result: {kind}',f"source_binding: {data['binding']['state']}"]
    if data.get('resolved_program_digest'):
        lines.append('resolved_program_digest: '+data['resolved_program_digest'])
    if kind=='PartInspection':
        c=value.get('component',{})
        lines.extend([f"component: {c.get('reference','?')} / {c.get('value','?')}",
                      f"native_revision: {value.get('revision','?')}",
                      f"native_source_state: {value.get('state','UNKNOWN')}",
                      'physical_qualification: NOT_DEMONSTRATED'])
    elif kind=='ConnectivityTrace':
        tr=value.get('trace',{})
        lines.extend(['schematic_path: '+' → '.join(tr.get('nodes',[])),
                      'graph_state: '+str(tr.get('state','UNKNOWN')),
                      'physical_qualification: NOT_DEMONSTRATED'])
    elif kind=='FactInquiry':
        lines.extend([f"component: {value.get('component','?')} / {value.get('native_mpn','?')}",
                      f"property: {value.get('property','?')}",
                      f"fact_state: {value.get('state','UNKNOWN')}",
                      f"reason: {value.get('reason','UNKNOWN')}"])
        f=value.get('reviewed_fact')
        if f:
            lines.extend([f"reviewed_fact: {f.get('fact_id')}",
                          f"grade: {f.get('grade')}",
                          f"upper_limit: {f.get('max')} {f.get('unit')}",
                          f"operating_conditions: {f.get('conditions')}"])
            source=value.get('original_page') or {}
            lines.append(f"original: {source.get('document_id')} page_index={source.get('page_index')} hash={str(source.get('source_sha256'))[:16]}")
        lines.append('physical_qualification: NOT_DEMONSTRATED')
    elif kind=='GapReport':
        for item in value.get('gaps',[]):lines.append(f"- {item['code']}: {item['detail']}")
        if not value.get('gaps'):lines.append('No gaps identified by this limited query (not complete qualification).')
    elif kind=='ProvenanceReport':
        lines.extend([f"source_revision: {value.get('native_source_revision','UNRESOLVED')}",
                      f"manufacturer_original_proven: {value.get('manufacturer_original_proven',False)}",
                      f"native_file_references: {len(value.get('source_files',[]))}"])
        for source in value.get('source_files',[])[:6]:
            lines.append('  '+str(source.get('state'))+' '+str(source.get('path'))+' #'+str(source.get('sha256') or '?')[:12])
        for note in value.get('notes',[]):lines.append('note: '+note)
    elif kind=='QualificationAssessment':
        lines.extend([f"state: {value.get('state')}",f"claim_scope: {value.get('claim_scope')}",
                      f"reviewed_upper_limit: {value.get('reviewed_upper_limit')}",
                      'proof_obligations:'])
        lines.extend('  - '+x for x in value.get('proof_obligations',[]))
    elif kind=='ScenarioAssessment':
        lines.extend([f"scenario_state: {value.get('state')}",
                      f"assumption: {value.get('assumed_quantity')} [HYPOTHETICAL]",
                      f"reviewed_upper_limit: {value.get('reviewed_upper_limit')}",
                      f"numeric_comparison: {value.get('numeric_comparison')}",
                      'NOT A TEST RESULT; NO PHYSICAL QUALIFICATION'])
    elif kind=='PredicateAssessment':
        lines.extend([f"predicate: {value.get('predicate')}",
                      f"hypothetical_result: {value.get('comparison_holds')}",
                      f"evidence_state: {value.get('evidence_state')}",
                      'HYPOTHETICAL ONLY: NOT A TEST, VENDOR LIMIT OR PHYSICAL QUALIFICATION'])
    elif kind=='EngineeringQuestion':
        lines.extend([f"question_type: {value.get('question_type')}",
                      f"state: {value.get('state')}",
                      f"applicability: {value.get('evidence',{}).get('applicability')}",
                      'open proof obligations:'])
        lines.extend('  - '+x['code'] for x in value.get('proof_obligations',[]) if x['state']=='OPEN')
        lines.append('No physical qualification or measurement inferred')
    elif kind=='ObligationReport':
        lines.extend(['open proof obligations:'] + ['  - '+str(code) for code in value.get('open',[])])
        lines.extend(['satisfied source bindings:'] + ['  - '+str(code) for code in value.get('satisfied',[])])
        lines.append('No physical qualification or measurement inferred')
    elif kind=='ChallengeReport':
        lines.append('Proposed falsification questions (no tools executed):')
        lines.extend(f"  - {item.get('question')}" for item in value.get('questions',[]))
    elif kind in ('ClaimCandidate', 'WitnessCandidate', 'WitnessJudgment'):
        lines.extend([f"claim_digest: {value.get('claim_digest')}",
                      f"witness_state: {value.get('state')}",
                      f"evidence_state: {value.get('evidence_state')}",
                      f"reason: {value.get('reason','No trusted verification performed')}",
                      'claim_scope: MANUFACTURER_REQUIREMENT_ONLY',
                      'physical_qualification: NOT_DEMONSTRATED'])
        for need in value.get('outstanding_obligations',[]):lines.append('  OPEN '+str(need))
    elif kind in ('KernelJobInspection','KernelTestWitness'):
        lines.extend([f"job_id: {value.get('id',value.get('job_id'))}",
                      f"state: {value.get('state')}",
                      f"tool: {value.get('tool')}",
                      f"evidence_id: {value.get('evidence_id')}",
                      f"source_applicability: {value.get('source_applicability','NOT_ASSESSED')}",
                      f"outcome: {value.get('recorded_tool_outcome','NOT_ESTABLISHED')}",
                      'RAW_ARTIFACT_NOT_VERIFIED; NO PHYSICAL QUALIFICATION'])
    elif kind=='KnowledgePacket':
        lines.extend([f"packet_sha256: {value.get('packet_sha256')}",
                      f"knowledge_state: {value.get('knowledge_state')}",
                      f"reviewed_requirement: {bool(value.get('reviewed_requirement'))}",
                      'cloud_disclosure: NOT_AUTHORIZED'])
    elif kind=='ROMStatus':
        for volume in value.get('volumes',[]):lines.append(f"volume {volume.get('volume_id')}: records={volume.get('records')} mounts={volume.get('mounts')}")
        lines.append('ROM inventory does not prove current hardware qualification.')
    elif kind=='VendorStatus':
        lines.append('vendor_status: '+str(value.get('status','UNKNOWN')))
        if value.get('reason'):lines.append('reason: '+str(value['reason']))
    elif kind=='Context':lines.append('selected_context: '+str(value))
    lines.append('model_invoked: no')
    return '\n'.join(lines)




def _resolve_program_io(raw: str, root: Path):
    """Resolve stdin or a private script and preserve separate export destinations."""
    if raw == '-':
        raw = redirection.stdin_text(sys.stdin)
    io = redirection.parse(raw)
    command = redirection.script_text(root, io.script) if io.script else io.program
    return command, io


def _formatted(data, json_output: bool, append: bool, name: str | None):
    """Format exactly one result; append-mode JSON uses JSON Lines framing."""
    if json_output:
        if append or (name is not None and name.endswith('.ndjson')):
            return json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'
        return json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    return _human(data) + '\n'


def _stream_result(root: Path, io, data, json_output: bool, action: str):
    json_output = json_output or action == 'semantics'
    target = io.stdout
    if target is not None:
        ext=Path(target.name).suffix.lower()
        if ext in ('.json','.ndjson') and not json_output:
            raise redirection.RedirectError('Use --json when redirecting to .json/.ndjson')
        if target.append and ext=='.json':
            raise redirection.RedirectError('Append structured records to .ndjson, not .json')
    rendered = _formatted(data,json_output, bool(target and target.append), target.name if target else None)
    if target:
        redirection.export(root,target,rendered)
    else:
        print(rendered,end='')
    if io.stderr:
        redirection.export(root,io.stderr,'')


def _stream_error(root: Path, io, exc: Exception, use_json: bool = False):
    if use_json:
        rendered=json.dumps({'schema':'arc.stac.error/0.5','ok':False,'error':str(exc)},ensure_ascii=False)+'\n'
    else:
        rendered='staC error: '+str(exc)+'\n'
    if io is not None and io.stderr is not None:
        redirection.export(root,io.stderr,rendered)
    else:
        print(rendered,end='',file=sys.stderr)


def main(argv=None):
    parser=argparse.ArgumentParser(description='staC 0.6 — typed ARC engineering-intent language and chronicle',
                                   formatter_class=argparse.RawDescriptionHelpFormatter,epilog=HELP)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2],
                        help='Explicit ARC Ledger project root')
    sub=parser.add_subparsers(dest='action',required=True)
    c=sub.add_parser('compile',help='Parse and type-check without touching sources')
    c.add_argument('program',help='Quoted staC pipeline')
    c.add_argument('--json',action='store_true')
    tr=sub.add_parser('translate',help='Finite controlled-English templates to typed staC IR (no LLM)')
    tr.add_argument('phrase',help='Single-line controlled English request')
    tr.add_argument('--json',action='store_true')
    sem=sub.add_parser('semantics',help='Static typed AST/effect inspection without executing')
    sem.add_argument('program',help='Quoted staC pipeline')
    sem.add_argument('--json',action='store_true')
    r=sub.add_parser('run',help='Read-only Ledger Kernel execution')
    r.add_argument('program',help='Quoted staC pipeline')
    r.add_argument('--json',action='store_true')
    q=sub.add_parser('repl',help='Interactive staC console')
    q.add_argument('--json',action='store_true')
    ch=sub.add_parser('chronicle',help='Opt-in CCC read-only observation chronology')
    ca=ch.add_subparsers(dest='chronicle_action',required=True)
    observe=ca.add_parser('record', help='Run a read-only staC program and record a compact observation')
    observe.add_argument('program', help='Quoted read-only staC program')
    observe.add_argument('--json',action='store_true')
    history=ca.add_parser('history',help='Inspect recorded read observations')
    history.add_argument('--limit',type=int,default=20)
    history.add_argument('--since',default=None,help='Timezone-aware ISO 8601 instant')
    history.add_argument('--until',default=None,help='Timezone-aware ISO 8601 instant')
    history.add_argument('--component',default=None)
    history.add_argument('--json',action='store_true')
    at=ca.add_parser('known-at',help='Show the latest *recorded* observation before this time')
    at.add_argument('instant',help='Timezone-aware ISO 8601')
    at.add_argument('--component',required=True)
    at.add_argument('--json',action='store_true')
    preview=ca.add_parser('whatif',help='Preview tracked dependencies of a hypothetical source change')
    preview.add_argument('--changed-source',required=True,help='Project-relative path of a captured source dependency')
    preview.add_argument('--json',action='store_true')
    check=ca.add_parser('verify',help='Verify complete local hash chain and optional anchored prefix')
    check.add_argument('--json',action='store_true')
    seal=ca.add_parser('seal',help='Create a separate local head checkpoint (not independently trusted)')
    seal.add_argument('--json',action='store_true')
    tail=ca.add_parser('kernel-tail',help='Read recent authoritative Ledger activity (not ingested into Chronicle)')
    tail.add_argument('--limit',type=int,default=10)
    tail.add_argument('--json',action='store_true')
    sub.add_parser('language',help='Display command reference')
    args=parser.parse_args(argv)
    if args.action=='language':print(HELP);return 0
    if args.action=='chronicle':
        try:
            action=args.chronicle_action
            if action=='record':
                from ..engine import engineering as Kernel
                ir=compile_text(args.program)
                result=evaluate(ir,Kernel(args.root))
                data=chronicle.observe(args.root,ir,result)
            elif action=='history':
                data=chronicle.history(args.root,args.limit,args.since,args.until,args.component)
            elif action=='known-at':
                data=chronicle.known_at(args.root,args.instant,args.component)
            elif action=='whatif':
                data=chronicle.whatif_source_changed(args.root,args.changed_source)
            elif action=='verify':
                data=chronicle.verify(args.root)
            elif action=='seal':
                data=chronicle.seal(args.root)
            elif action=='kernel-tail':
                if not 1<=args.limit<=100:raise chronicle.ChronicleError('INVALID_LIMIT')
                from ..engine import engineering as Kernel
                from .runtime import _kernel_read
                data=_kernel_read(Kernel(args.root),'ledger.activity',{'limit':args.limit})
            else:raise chronicle.ChronicleError('UNKNOWN_CHRONICLE_COMMAND')
            if args.json:
                print(json.dumps(data,ensure_ascii=False,indent=2))
            else:
                if action=='history':
                    print('Chronicle: '+str(data['total_matching'])+' matching recorded observations')
                    for entry in data['events']:
                        print(f"{entry['sequence']:04d}  {entry['recorded_utc']}  {entry['subject']}  {entry['result_summary']['result_type']}")
                    if data['truncated']:print('More observations omitted; raise --limit to inspect.')
                elif action=='kernel-tail':
                    print('Ledger Kernel activity (retained recent view, not the staC chronicle)')
                    for entry in data.get('events',[]):print(str(entry.get('at'))+' '+str(entry.get('operation'))+' '+str(entry.get('state')))
                    if data.get('gap'):print('Activity cursor gap reported')
                else:
                    print(json.dumps(data,ensure_ascii=False,indent=2))
            return 0
        except (CompileError,RunError,chronicle.ChronicleError,ValueError,OSError) as exc:
            if getattr(args,'json',False):
                print(json.dumps({'schema':'arc.stac.ccc.error/0.3','ok':False,'error':str(exc)},ensure_ascii=False))
            else:print('staC chronicle error: '+str(exc),file=sys.stderr)
            return 2
    if args.action=='translate':
        try:
            out=controlled_language.translate(args.phrase)
            if args.json:
                print(json.dumps(out,ensure_ascii=False,indent=2))
            else:
                print('staC controlled translation (not executed): '+out['program'])
                print('intent_digest: '+out['intent_digest'])
            return 0
        except (controlled_language.TranslationError,ValueError) as exc:
            if args.json:print(json.dumps({'schema':'arc.stac.controlled.error/0.4','ok':False,'error':str(exc)},ensure_ascii=False))
            else:print('staC translation error: '+str(exc),file=sys.stderr)
            return 2
    if args.action=='repl':
        print('staC 0.6 · read-only · type help for commands; exit to quit')
        ctx=None;k=None
        while True:
            try:line=input('staC> ').strip()
            except (KeyboardInterrupt,EOFError):print();return 0
            if not line:continue
            if line in ('quit','exit'):return 0
            if line in ('help','?'):print(HELP);continue
            try:
                plan=redirection.parse(line)
                command=redirection.script_text(args.root,plan.script) if plan.script else plan.program
                compiled=compile_text(command,initial_context=ctx) if plan.script else plan.compile_inline(ctx)
                if command.lower().startswith('use ') and len(compiled['nodes'])==1:
                    ctx=Context(compiled['context']['project'],compiled['context']['board'])
                    print(f'Context: {ctx.project}@{ctx.board} (read-only)');continue
                if k is None:
                    from ..engine import engineering as Kernel
                    k=Kernel(args.root)
                out=evaluate(compiled,k)
                _stream_result(args.root,plan,out,args.json,'run')
            except (CompileError,RunError,ValueError,OSError,redirection.RedirectError) as exc:
                try:_stream_error(args.root,locals().get('plan'),exc,args.json)
                except (OSError,redirection.RedirectError):print('staC error: '+str(exc),file=sys.stderr)
            finally:
                if 'plan' in locals():del plan
        return 0
    if args.action in ('run','compile','semantics') and args.program.lstrip().startswith(('map ','source ','packet ','investigation ')):
        try:
            from ..engine import engineering as Kernel
            from ..engineering_kernel import operator
            from .. import stac_bridge
            if args.action=='run':
                reply=Kernel(args.root).dispatch('stac.run',{'program':args.program},operator())
                if not reply['ok']:raise ValueError(reply['error']['message'])
                out=reply['result']
            else:out=stac_bridge.compile_program(args.program)
            print(json.dumps(out,ensure_ascii=False,indent=2));return 0
        except (ValueError,OSError) as exc:
            print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 2
    plan=None
    try:
        command,plan=_resolve_program_io(args.program,args.root)
        ir=compile_text(command) if plan.script else plan.compile_inline()
        if args.action=='compile':out=ir
        elif args.action=='semantics':out=semantics.inspect(ir)
        else:
            from ..engine import engineering as Kernel
            out=evaluate(ir,Kernel(args.root))
        _stream_result(args.root,plan,out,args.json,args.action)
        return 0
    except (CompileError,RunError,ValueError,OSError,redirection.RedirectError) as exc:
        try:_stream_error(args.root,plan,exc,args.json)
        except (OSError,redirection.RedirectError):print('staC error: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
