"""Shared task vocabulary and finite read-only staC workbench extension."""
import hashlib
import json
import re
import shlex

LANES = ('Bring in','Understand','Build & prove','Follow through')
TASKS = (
    ('packages','Bring in','Inspect a package','See what a ZIP contains before copying it for review.','packages','desk | focus bring-in'),
    ('intake','Bring in','Review reference material','Choose a library, review originals and their dependencies.','intake','desk | focus bring-in'),
    ('object','Understand','Understand this object','Follow identity, sources, evidence and gaps in Object Glass.','object_glass','desk | focus understand'),
    ('connections','Understand','Find source connections','Explore source-bound relationships without promoting a reference.','sources','desk | focus understand'),
    ('capabilities','Build & prove','Find the next capability','Discover registered commands and inspect their prerequisites.','commands','desk | focus build'),
    ('engineering','Build & prove','Open engineering work','Use the existing candidate, job and evidence controls.','engineering','desk | focus build'),
    ('trail','Follow through','Follow the work','See what ran, what it produced and what needs attention.','trail','desk | focus follow-through'),
    ('memory','Follow through','Remember and reason','Use the existing staC, memory, study and recovery workspaces.','memory','desk | focus follow-through'),
)
FOCUS = {'bring-in':LANES[0],'understand':LANES[1],'build':LANES[2],'follow-through':LANES[3]}


def tasks(query='',focus='all'):
    lane = FOCUS.get(focus)
    return [{'id':i,'lane':l,'title':t,'detail':d,'destination':dest,'stac':stac}
            for i,l,t,d,dest,stac in TASKS if (not lane or l == lane) and
            (not query or query.casefold() in (' '.join((i,l,t,d))).casefold())]


def compile_read(program):
    if not isinstance(program,str) or not 1 <= len(program.encode()) <= 4096 or any(c in program for c in '\n\r\0'):
        raise ValueError('STAC_DESK_PROGRAM_BOUND')
    lexer = shlex.shlex(program,posix=True,punctuation_chars='|;&<>`$()')
    lexer.whitespace_split=True;lexer.commenters='';tokens=list(lexer)
    presentation = None
    if tokens == ['desk']:
        operation='ledger.organizer';arguments={};kind='WorkbenchOverview'
    elif len(tokens) == 4 and tokens[:3] == ['desk','|','focus'] and tokens[3] in FOCUS:
        operation='ledger.organizer';arguments={'focus':tokens[3]};kind='WorkbenchOverview'
    elif len(tokens) == 4 and tokens[:3] == ['desk','|','find'] and 1 <= len(tokens[3]) <= 200:
        operation='ledger.organizer';arguments={'query':tokens[3]};kind='WorkbenchOverview'
    elif len(tokens) == 4 and tokens[0] == 'package' and re.fullmatch('[a-f0-9]{32}',tokens[1]) and tokens[2] == '|' and tokens[3] in ('contents','gaps'):
        operation='intake.package.get';arguments={'id':tokens[1]};presentation=tokens[3]
        kind='PackageInventory' if presentation == 'contents' else 'PackageGaps'
    else:raise ValueError('STAC_DESK_SYNTAX')
    body={'schema':'arc.stac.workbench-ir/1','operation':operation,'arguments':arguments,
          'effects':['read'],'result_type':kind,'presentation':presentation}
    return {**body,'program_id':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),
            'authority':'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
