import json, sys, re, collections
d = json.load(open(sys.argv[1]))
cats = collections.defaultdict(list)
for k, v in d.items():
    docs = sorted(v)
    if ' ' in k or k.startswith(('python', 'OUT/')):
        c = 'x_command_or_output_placeholder'
    elif re.search(r'\.(PENDING|cut_lines|SPECS|decide|show_home|FOCUSED_MODULES|PointerTests)$', k) or k in ('tools/call', 'tools/list', 'agent.step', 'tools/check_', 'tools/ui_fit', 'docs/RELEASE_NOTES_', 'tools/effects/roots/network/expiry', 'project/assignment', 'project/idea') or k.startswith('_'):
        c = 'x_not_a_file_reference'
    elif k.startswith('.ledger/') or k in ('launch-error.log', 'last-session.json', 'readiness.json', 'READ_ME.txt', 'BACKUP.json', 'baseline-report.json', 'my-baseline.json', 'REPORT.json', 'clip.json', 'remote-config.json', 'workspace.json', 'seen.json', 'sent.json', 'pill.json', 'signature.json', 'ledger-card.json', 'workstation-card.json', 'file.json', 'candidates.patch', 'open-current.sh', 'ledger-release-1.zip', 'invoice.pdf', 'pellet_order.md', 'rail.txt', 'bench.txt', 'game.c', 'source.png'):
        c = 'runtime_created_or_example_name'
    elif k in ('RELEASE_PARTS.json', 'OFFLINE_FILES.json', 'START_HERE.md'):
        c = 'kit_level_file_outside_manifest'
    elif k.endswith('.gguf'):
        c = 'external_model_weights'
    elif k.startswith('build/') or k.startswith('v01_reruns/') or re.search(r'(-ui|_ui)\.json$|_1920\.png$|_1366\.png$|Machine_View\.png$|Cabinet_Record\.png$|With_Strip\.png$', k):
        c = 'DANGLING_check_outputs_and_captures'
    elif re.search(r'_RESULT\.json$|^I01_|I05_VISIBLE|README_(INTEGRATION|WORKSHOP)_01\.txt$|_CAPABILITIES\.json$', k):
        c = 'DANGLING_pass_receipts'
    elif k.startswith('examples/clock_lab/'):
        c = 'DANGLING_model_trial_run_records'
    elif k.startswith(('software/', 'hardware/')):
        c = 'DANGLING_third_party_licence_paths'
    elif k.startswith('tests/') or k.startswith('tools/') or k == 'continue_service.py':
        c = 'DANGLING_code_files'
    else:
        c = 'DANGLING_documents_and_assets'
    cats[c].append((k, docs))
for c in sorted(cats):
    print(f"## {c}: {len(cats[c])}")
    for k, docs in sorted(cats[c]):
        print(f"    {k}   <= {', '.join(docs)[:140]}")
tot = sum(len(v) for c, v in cats.items() if c.startswith('DANGLING'))
print('TOTAL DANGLING distinct:', tot, 'of', len(d))
