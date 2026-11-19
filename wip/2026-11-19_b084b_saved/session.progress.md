# session builder: progress

Scripts in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/b084b/session/
(mkcopy.sh, t.sh, repro.sh + repro_probe.py, sweep.sh + sweep.py; logs/).

## Done
- Reproduced item 1 on a copy (repro.sh, three starts through the start-script probe):
  A (rooms open once, then not reopened): saved deferred = [DocumentsTab, FilesTab, AgendaTab] and stays.
  B (owner reopens Documents and Files each start): deferred grows by one per room per start:
  [] -> [Documents, Files] -> [Documents, Files, Documents, Files]. Nothing on stderr: open_record simply has no entry
  for these kinds (returns None) -> set aside.
- Sweep (before) running: logs/sweep.before.txt

## Plan (next)
- workspace_tabs: restore entries through shell2.open_destination for desk rooms (Documents, Files+folder, Trash,
  Agenda, Changes, Deployment, Continuing, Investigations, Library+kind, program rooms, bridge navigation tabs);
  they wait for the bridge; 'room' flag in the row so a Preview before them does not set them aside; deferred deduped,
  rows restored drop their deferred twins; bounded (20).
- Say once per start, in Activity/Log (activity.record 'ledger.restore'), what was not reopened and why, plain words.
- Tests in test_session_start.py; strip_host root -> temp dir (activity writes there).
