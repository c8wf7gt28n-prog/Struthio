"""The activity tail in plain words. The full event stays in the line's tooltip."""

WORDS = {
    'ledger.open': 'Graphite opened', 'ledger.view': 'Opened', 'ledger.navigate': 'Went to', 'ledger.settings.set': 'Changed a setting',
    'receiving.receive': 'Received files', 'investigation.create': 'Opened an investigation', 'investigation.step': 'Ran a step of an investigation', 'investigation.continue': 'Continued an investigation', 'investigation.refresh': 'Compared an investigation\'s sources again', 'investigation.check': 'Bound a claim to a check', 'investigation.claim': 'Wrote down a claim', 'investigation.add_source': 'Read a source into an investigation', 'investigation.evidence': 'Linked evidence to a claim', 'investigation.review': 'Decided on a changed source', 'investigation.stop': 'Stopped an investigation', 'receiving.advance': 'Moved a delivery along', 'intake.import': 'Snapshotted files',
    'intake.review': 'Read the received files', 'intake.bundle.decide': 'Accepted files', 'intake.decide': 'Decided on a file',
    'references.index': 'Built the catalog', 'language.run': 'Ran staC', 'stac.run': 'Ran staC', 'stac.observe': 'Recorded a staC observation',
    'matrix.mark': 'Marked a staC result', 'matrix.promote': 'Proposed a lesson', 'matrix.export': 'Exported the training set',
    'matrix.forget': 'Cleared the instruction matrix', 'brain.ask': 'Asked Graphite', 'brain.model.add': 'Requested model inspection',
    'brain.model.use': 'Requested model change', 'brain.model.qualify': 'Requested model qualification', 'brain.restore': 'Requested previous model', 'brain.stop': 'Stopped the brain',
    'jobs.submit': 'Started a job', 'brain.respond': 'Graphite answering', 'intake.scan': 'Snapshotted files',
    'brain.inspect': 'Model inspection', 'brain.activate': 'Model activation', 'brain.qualify': 'Model qualification', 'references.state': 'Catalog', 'jobs.cancel': 'Cancelled a job', 'notebook.save': 'Saved a notebook', 'office.save': 'Saved an Office file',
    'memory.lesson.review': 'Reviewed a lesson', 'agenda.add': 'Added to the Agenda', 'agenda.suggest': 'Graphite suggested a next step', 'agenda.accept': 'Added a suggestion to Next', 'agenda.decline': 'Set a suggestion aside', 'agenda.nice': 'Changed how nice an Agenda item is', 'agenda.move': 'Reordered the Agenda', 'agenda.pause': 'Paused an Agenda item', 'agenda.resume': 'Resumed an Agenda item', 'agenda.cancel': 'Removed an Agenda item', 'agenda.run_next': 'Worked on the Agenda', 'agenda.seen': 'Saw a watched change', 'files.mkdir': 'Made a folder', 'files.rename': 'Renamed', 'files.copy': 'Copied', 'files.move': 'Moved', 'files.trash': 'Moved to Trash', 'files.restore': 'Restored from Trash', 'files.write': 'Wrote a file', 'files.cells': 'Changed cells in a workbook', 'files.propose': 'Graphite proposed a change to a file', 'files.decide': 'Decided on a proposed change', 'files.revert': 'Went back to an earlier version', 'files.export': 'Exported', 'files.smart': 'Made a smart folder', 'files.keep': 'Kept a received file in Files', 'copies.merge': 'Brought an outside change into a working copy', 'console.shell': 'Shell:', 'copies.start': 'Started a working copy', 'copies.propose': 'Froze a working copy for review', 'copies.apply': 'Updated an original from its working copy', 'copies.save_new': 'Saved a working copy as a new file', 'copies.refresh': 'Compared a working copy with its changed original', 'copies.discard': 'Discarded a working copy', 'copies.undo': 'Undid an update to an original', 'copies.recover': 'Checked unfinished updates', 'ledger.work.resume': 'Resumed work', 'master.stop': 'Master Stop', 'pills.pair': 'Paired with another computer', 'pills.unpair': 'Forgot a paired computer', 'pills.accept': 'Accepted a pill as a working copy', 'pills.return': 'Packed a result pill', 'pills.fetch': 'Fetched pills over the link', 'pills.send': 'Sent a pill over the link', 'confine.run': 'Ran a command, confined, in a working copy', 'confine.inspect': 'Looked inside a working copy, confined',
}
STATES = {'REQUEST_COMPLETED': '', 'COMPLETED': '', 'READY': '', 'FOCUSED': '', 'REQUEST_RECEIVED': '…',
          'DENIED_OR_FAILED': '· failed', 'Completed': '· done', 'completed': '· done', 'Failed': '· failed', 'Queued': '· queued', 'Running': '· running', 'FAILED': '· failed', 'DENIED': '· refused', 'CANCELLED': '· cancelled', 'BLOCKED': '· waiting for a project'}
QUIET_ORIGINS = {'GUI', 'DESKTOP', 'desktop-owner', 'owner', 'Kernel', 'KERNEL'}


def readable(event):
    operation = event.get('operation', '');state = event.get('state', '');detail = (event.get('detail') or '').strip()
    words = WORDS.get(operation) or WORDS.get(operation.rsplit('.', 1)[0]) or operation
    if operation == 'ledger.view':
        detail = detail.replace('Preview · ', '').replace('◆ ', '')
        if detail.lower().startswith('no active document'):return 'Nothing open'
    if operation == 'ledger.open' and state == 'READY':detail = ''
    origin = event.get('origin', '')
    who = '' if origin in QUIET_ORIGINS else origin.title() + ' · '
    tail = STATES.get(state, '· ' + state.replace('_', ' ').lower())
    return (who + words + (' ' + detail if detail and operation in ('ledger.view', 'ledger.navigate') else (' · ' + detail if detail else '')) + (' ' + tail if tail else '')).strip()


def in_flight(events):
    """Requests whose completion has not been recorded yet."""
    done = {e.get('correlation_id') for e in events if e.get('state') != 'REQUEST_RECEIVED'}
    return {e.get('correlation_id') for e in events if e.get('state') == 'REQUEST_RECEIVED' and e.get('correlation_id') not in done}
