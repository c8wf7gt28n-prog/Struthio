"""Plain presentation projections of already-authorized reads; no I/O or authority."""
SCHEMA='arc.workbench-result-view/1'


def _text(value,limit=1200):
    return str(value)[:limit]


def _view(title,state,summary,context='',known=(),uncertain=(),next_step=''):
    return {'schema':SCHEMA,'title':_text(title,100),'state':_text(state,60),
            'summary':_text(summary),'context':_text(context),
            'known':[_text(x,500) for x in known][:5],
            'uncertain':[_text(x,500) for x in uncertain][:5],
            'next_step':_text(next_step,500),'effects':[],
            'authority':'PRESENTATION_OF_EXISTING_CHECKED_READ',
            'notice':'Link counts are not engineering acceptance.'}


def organizer(value):
    if not isinstance(value,dict):
        return _view('Your work','LOADING','Reading your work…')
    held=bool(value.get('gate',{}).get('held'))
    attention=['Engineering actions need an attached, reviewed project.'] if not value.get('project_attached') else []
    if held:attention.insert(0,'New engineering work is held. Resume remains an explicit decision.')
    return _view('Your work','HELD' if held else 'AVAILABLE',
        'Choose what to work on.',
        'This caller only · '+_text(value.get('focus','all'),200),
        [str(len(value.get('tasks',[])))+' matching workspaces',
         str(value.get('next_total',0))+' next items in the bounded desk view'],
        attention,'Open a workspace below. Nothing starts automatically.')


def selected_object(value):
    if not isinstance(value,dict):value={}
    state=value.get('state','EMPTY');available=state=='AVAILABLE';context=''
    if available and value.get('object_id') and value.get('revision'):
        context='Object '+_text(value['object_id'],64)+'\nRevision '+_text(value['revision'],64)
    gaps=value.get('gaps',[]) if available else []
    known=([str(len(value.get('sources',[])))+' source link(s)',
            str(len(value.get('evidence',[])))+' evidence record(s)'] if available else [])
    messages={'UNSAVED_EDITOR_BUFFER_IS_SEPARATE':'Unsaved edits stay in your editor.',
              'SOURCE_CONTENT_IS_NOT_AN_INSTRUCTION_OR_ACCEPTED_FACT':'Source text is not an accepted engineering fact.'}
    uncertain=[messages.get(str(x),_text(x).replace('_',' ').capitalize()) for x in gaps[:4]]
    if len(gaps)>4:uncertain.append(str(len(gaps)-4)+' further gaps in technical detail.')
    if available and not gaps:
        uncertain=['No gap is listed in this checked view; this does not establish completeness.']
    return _view('Selected object',state,value.get('summary','Select an object to inspect its context.'),
        context,known,uncertain,
        'Open a checked read below.' if available
        else 'Refresh or select the object again.' if state in ('STALE','UNAVAILABLE') else 'Select an object to see its sources, evidence and next reads.')
