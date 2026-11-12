"""Program packaging is distinct from project evidence and acceptance."""
import json
from pathlib import Path

PROFILE='project/program_profile.json'
PROJECT_PREFIXES=('hardware.','boot.','firmware.','arcos.','struthio.','console.','native.',
                  'register.','vendor.','book.','records.','proof.','qualification.',
                  'simulation.','links.','baseline.','guidance.','coverage.')

def detached(root):
    path=Path(root)/PROFILE
    if not path.is_file():
        # A concern workspace says whether it attaches a project; an unmarked folder is a legacy full workspace.
        from .locations import marker
        value=marker(root)
        return bool(value) and value['kind']=='NO_PROJECT'
    value=json.loads(path.read_text())
    if value.get('schema')!='arc.program-profile/1' or value.get('kind')!='PROGRAM_ONLY':
        raise ValueError('Unsupported program profile; project state cannot be inferred')
    return True

def status(root):
    empty=detached(root)
    return {'schema':'arc.project-attachment/1','state':'PROJECT_NOT_ATTACHED' if empty else 'LEGACY_WORKSPACE',
            'program_only':empty,'project_accepted':False,
            'notice':'Original user work is sealed separately. Archive intake and independent V1 review are Pass 4.' if empty else 'Source presence is not independent acceptance.'}

# Operations outside the project families above that still read project sources.
PROJECT_OPERATIONS=frozenset({'cad.inspect','workshop.component_context','workshop.prepare','hdl.value','hdl.compare_pump',
    'desktop.code','desktop.compile_commands','desktop.debug.build','desktop.debug.open','clip.prepare','clip.submit',
    'workspace.select','workspace.resolve'})

def requires_project(operation,args):
    if operation=='jobs.submit' and args.get('tool') in ('math.joined','math.method','math.session'):return False
    if operation=='jobs.submit':return args.get('tool') not in ('lab.qualify','lab.python','lab.board','math.office','ledger.kernel_tests','brain.inspect','brain.qualify','brain.activate','brain.respond','brain.reason','brain.task_qualify','brain.change_draft','intake.scan','intake.review','intake.export','references.index','references.render','references.export','references.verify','study.read','knowledge.verify','knowledge.page','knowledge.map','references.compile','knowledge.investigate')
    return operation.startswith(PROJECT_PREFIXES) or operation in ('project.inspect','project.inventory') or operation in PROJECT_OPERATIONS

def refusal(value):
    """The reason when a result is the explicit missing-project answer, otherwise None."""
    return value.get('reason') if isinstance(value,dict) and value.get('status')=='PROJECT_NOT_ATTACHED' else None

def unavailable(operation):
    return {'status':'PROJECT_NOT_ATTACHED','operation':operation,'available':False,
            'reason':'Attach and review a project before this operation. Original work remains in the sealed archive.',
            'data':None,'physical_hardware':False}
