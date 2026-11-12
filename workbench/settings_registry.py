"""Canonical metadata for the first shared settings adapters; no value store.

Legacy category names and staC keys remain stable. Navigation roles are distinct
from cabinet records, and only scopes with real backing stores are advertised.
"""
import re
from . import reading_profile
from .presentation_preferences import DEFAULTS, OUTPUT_TABS, LAYOUT_RANGES, CURSIVE_DEFAULT


def spec(key, label, category, default, kind, description, **extra):
    project = key.startswith('operations.') or key.startswith('stacy.') and key != 'stacy.reactions'
    visual = key.startswith('reading.') or key in ('stacy.reactions', 'workspace.mode')
    application = 'next_launch' if key == 'workspace.startup' else 'immediate' if visual or key.endswith('enabled') else 'next_use'
    group = ('Behavior' if key in ('stacy.enabled', 'stacy.reactions') else
             'Providers' if key == 'stacy.provider' else 'Tools') if key.startswith('stacy.') else category
    store = ('Session reading_profile' if key.startswith('reading.') else
             'Session layout.stacy_reactions' if key == 'stacy.reactions' else
             'Session view_preferences' if key.startswith('workspace.') else
             '.ledger/master-stop/priority.json' if key == 'operations.priority' else 'Kernel settings: ledger.' + key)
    result=dict(key=key, label=label, category=category, default=default, type=kind,
                description=description, root='Slate' if key.startswith('stacy.') else 'Ledger', group=group,
                scope='Project private' if project else 'Connected session profile',
                scope_id='project_private' if project else 'session_profile',
                supported_scopes=['project_private' if project else 'session_profile'],
                application=application, effect={'immediate':'Immediately after consumer readback',
                    'next_use':'Next request or owned work', 'next_launch':'Next desktop launch'}[application],
                store=store, dependencies=[], overrides=[])
    result.update(extra)
    return result


SPECS = [
    spec('reading.family', 'Interface font', 'Appearance', reading_profile.DEFAULT['family'], 'string', 'Unavailable fonts use the existing local fallback.'),
    spec('reading.prose_family', 'Prose font', 'Appearance', reading_profile.DEFAULT['prose_family'], 'string', 'Prose font is separate from interface and source code.'),
    spec('reading.code_family', 'Code font', 'Appearance', reading_profile.DEFAULT['code_family'], 'string', 'Unavailable or non-fixed-pitch choices use a local monospaced fallback.'),
    *[spec('reading.'+key, label, 'Appearance', reading_profile.DEFAULT[key], 'number', label+' in the existing reading profile.', minimum=lo, maximum=hi)
      for key, label, lo, hi in [(k, {'ui_pt':'Interface text (pt)', 'navigation_pt':'Tree text (pt)',
          'code_pt':'Code text (pt)', 'prose_pt':'Prose text (pt)', 'line_height':'Document line spacing'}[k], a, b)
          for k, a, b in reading_profile.RANGES]],
    spec('reading.reduce_motion', 'Reduce motion', 'Appearance', False, 'boolean', 'Use quiet/static optional presentation.'),
    spec('stacy.reactions', 'Graphite reactions', 'Slate', True, 'boolean', 'Optional idle and job reactions; does not start tools.'),
    spec('stacy.enabled', 'Allow new Graphite AI activity', 'Slate', True, 'boolean', 'OFF blocks new model activation, qualification and inference. Running requests may finish; ordinary Graphite tools stay available.'),
    spec('stacy.provider', 'Graphite chat provider', 'Slate', 'local', 'string', 'Select the provider for the next request. This does not load a local model or configure a Gemini credential.', choices=['local','gemini']),
    spec('stacy.actions', 'Enable Graphite action proposals', 'Slate', False, 'boolean', 'Gemini may propose registered commands for review. This grants no source acceptance authority.'),
    spec('stacy.share_activity', 'Share activity context', 'Slate', False, 'boolean', 'Include redacted activity, settings and workspace metadata in the next Gemini request. Source sharing remains separate.'),
    spec('workspace.startup', 'Startup', 'Workspace', 'last', 'string', 'Choose the policy consumed at the next desktop launch.', choices=['last','home']),
    spec('workspace.mode', 'Workspace arrangement', 'Workspace', 'engineering', 'string', 'Focus or engineering arrangement.', choices=['engineering','focus']),
    spec('operations.priority', 'Work CPU priority', 'Operations', 'normal', 'string', 'Background lowers Graphite work priority. Normal applies to new work; existing lower priorities remain until those processes exit.', choices=['normal','background']),
    spec('operations.services_enabled', 'Graphite services admission', 'Operations', True, 'boolean', 'The menu holds new work here while running jobs drain gracefully. Use the menu’s Graphite services for a complete service cycle.'),
]
SPECS += [
    spec('cabinet.sort','Cabinet sibling order','Workspace','natural','string',
         'Case-insensitive natural order keeps Project 2 before Project 10. Alphabetical order compares the label as text. This changes presentation only.',
         choices=['natural','alphabetical'],group='Cabinet',scope='Workspace private',scope_id='project_private',supported_scopes=['project_private'],
         store='Kernel settings: ledger.cabinet.sort',application='next_use',effect='Next cabinet refresh'),
    spec('appearance.cursive','Script for incidental text','Appearance',CURSIVE_DEFAULT,'boolean',
         'Use the existing script accent for incidental text. Working text stays in the reading fonts.',
         application='immediate',effect='After desktop presentation readback',store='Session cursive'),
    *[spec('layout.'+key,label,'Workspace',DEFAULTS[key],'integer',description,
           group='Layout',application='immediate',effect='After desktop layout readback',
           store='Session layout.'+key,minimum=LAYOUT_RANGES[key][0],maximum=LAYOUT_RANGES[key][1])
      for key,label,description in [
          ('navigator_width','Left column width','Requested width in pixels. Font and window constraints may require a wider column.'),
          ('output_height','Output panel height','Requested height in pixels. A hidden panel remains pending until shown.')]],
    spec('layout.output_visible','Show output panel','Workspace',DEFAULTS['output_visible'],'boolean',
         'Show the existing output dock. Workspace arrangement can also change panel visibility.',
         group='Layout',application='immediate',effect='After desktop layout readback',store='Session layout.output_visible'),
    spec('layout.output_tab','Selected output page','Workspace',DEFAULTS['output_tab'],'string',
         'Select the existing Output, Problems, Debug or Agent Activity page.',choices=list(OUTPUT_TABS),
         group='Layout',application='immediate',effect='After desktop layout readback',store='Session layout.output_tab'),
    spec('gemini.model','Gemini model preference','Slate','','string',
         'Model name for the next Gemini request. Empty retains the existing automatic choice. This does not make a cloud request.',
         root='Slate',group='Providers',scope='Personal Gemini preferences',scope_id='personal_profile',supported_scopes=['personal_profile'],
         store='Existing clip.json model field; credential bytes preserved',requires_owner=True,minLength=0,maxLength=200),
    spec('gemini.include_file','Include the current file with Gemini','Slate',False,'boolean',
         'Allow the existing Gemini chat control to attach the current file on the next request. No file is sent by changing this setting.',
         root='Slate',group='Providers',scope='Personal Gemini preferences',scope_id='personal_profile',supported_scopes=['personal_profile'],
         store='Existing clip.json include_file field; credential bytes preserved',requires_owner=True),
]
# Adapters over the original private profile; no parallel configuration values.
from sdk.cli.arc1cli.learning_contracts import WEIGHTS
MEMORY_STORE='Existing owner memory profile: stacy_memory/current'
MEMORY_META=dict(root='Slate',group='Memory',scope='Owner private memory in this workspace',scope_id='owner_memory',
    supported_scopes=['owner_memory'],store=MEMORY_STORE,adapter='memory_profile',requires_owner=True,
    application='next_use',effect='Next local response profile context; no model activation or weight training')
SPECS += [
    spec('memory.profile.enabled','Use personality reference','Slate',True,'boolean',
         'Use the imported owner reference and its direction preferences when the existing local profile-context path is selected. Does not load a model or enable new AI activity.',
         **MEMORY_META),
    spec('memory.soft_half_life_days','Soft feedback half-life (days)','Slate',90,'number',
         'Time for soft feedback weight to halve. Persistent owner corrections do not decay. This adjusts preference accounting, not engineering facts.',
         minimum=1,maximum=730,editor='number_text',**MEMORY_META),
    *[spec('memory.weight.'+kind,label,'Slate',weight,'number',
         'Relative influence in the existing collaboration-preference calculation. Does not change model weights, grants or evidence authority. Must be greater than zero and at most ten.',
         minimum=0,exclusiveMinimum=0,maximum=10,editor='number_text',**MEMORY_META)
      for kind,label,weight in [(kind,{'owner_correction':'Owner correction weight','owner_statement':'Owner statement weight',
          'owner_confirmed_choice':'Confirmed choice weight'}[kind],weight) for kind,weight in WEIGHTS.items()]]
]
MEMORY_KEYS=frozenset(row['key'] for row in SPECS if row.get('adapter')=='memory_profile')

SPECS += [spec('brain.'+key,label,'Slate',default,'integer',description,
    root='Slate',group='Local model',scope='Owner-controlled launch defaults in this workspace',
    scope_id='project_private',supported_scopes=['project_private'],requires_owner=True,
    store='Kernel settings: ledger.brain.'+key,adapter='model_launch',minimum=lo,maximum=hi,
    application='next_use',effect='Next explicit model load or qualification; running model stays in place',**extra)
    for key,label,default,lo,hi,description,extra in [
        ('context','Model context tokens',2048,512,8192,'Default context for a new local-model load. The model declaration and memory budget are checked before submission.',{}),
        ('threads','Model CPU threads',4,1,32,'Default CPU threads for a new local-model load. An explicit per-request value overrides this default.',{}),
        ('memory_mb','Model host memory budget (MiB)',0,0,262144,'Zero means Auto. A manual budget must be at least 512 MiB. Auto resolves against measured host RAM. CPU uses an address-space cap; Vulkan uses an RSS and host-headroom guard, not a hard GPU-allocation cap.',{'zero_label':'Auto','nonzeroMinimum':512}),
    ]]
MODEL_META=dict(root='Slate',group='Local model',scope='Owner-controlled launch defaults in this workspace',
    scope_id='project_private',supported_scopes=['project_private'],requires_owner=True,
    adapter='model_launch',application='next_use',
    effect='Next explicit model load or qualification; running model stays in place')
SPECS += [
    spec('brain.backend','Inference backend','Slate','AUTO','string',
         'Auto prefers the pinned Vulkan worker on an accessible AMD GPU. The live worker reports actual offload; CPU remains available.',
         store='Kernel settings: ledger.brain.backend',choices=['AUTO','CPU','VULKAN'],
         choice_labels={'AUTO':'Auto · prefer Radeon','CPU':'CPU','VULKAN':'Vulkan'},**MODEL_META),
    spec('brain.gpu_layers','GPU layers','Slate',-1,'integer',
         'Minus one lets llama.cpp fit GPU layers to its reported device budget. Zero uses CPU. Positive values request at most that many layers.',
         store='Kernel settings: ledger.brain.gpu_layers',minimum=-1,maximum=512,**MODEL_META),
    spec('brain.cpu_fallback','Allow CPU fallback','Slate',True,'boolean',
         'After an unavailable or failed Vulkan load, allow one recorded CPU attempt. Cancellation, changed model files and host-memory guard failures do not retry.',
         store='Kernel settings: ledger.brain.cpu_fallback',**MODEL_META),
]
MODEL_KEYS=frozenset(row['key'] for row in SPECS if row.get('adapter')=='model_launch')
SPECS += [spec('operations.'+key,label,'Work',default,'integer',description,
    root='Ledger',group='Shared resources',requires_owner=True,minimum=lo,maximum=hi,
    application='next_use',effect='Next resource admission; running tools keep their existing limits')
    for key,label,default,lo,hi,description in [
        ('reserve_mb','Foreground RAM reserve (MiB)',2048,256,16384,'Keep this much measured host RAM outside new worker admissions. Clamped to one quarter of measured host RAM on smaller machines. This is not a hard OS reservation.'),
        ('compute_slots','Concurrent CPU calculations',1,1,3,'Admit this many heavy CPU jobs alongside one serialized model-turn lane. At most four native jobs run. Active operations finish at their boundary.'),
        ('background_threads','Background library threads',2,1,8,'Thread hint for cooperative numerical libraries in background job children; clamped to leave one logical CPU when possible. It is not a CPU-time quota.'),
    ]]

# Preserve the existing public batch contract; new favorite adapters use single-key Set.
SESSION_BATCH_KEYS = frozenset(row['key'] for row in SPECS if row['store'].startswith('Session '))
from sdk.cli.arc1cli.command_bar import FAVORITE_KEYS, GROUP_LABELS, DEFAULTS as FAVORITE_DEFAULTS, allowed_groups
SPECS += [spec(key,GROUP_LABELS[group]+' favorites','Workspace',list(FAVORITE_DEFAULTS[group]),'array',
    'Choose up to three existing commands in order. Empty keeps this group unpinned. Changing favorites never runs a command.',
    group='Favorites',store='Session toolbar_favorites.'+group,application='immediate',
    effect='After desktop favorites readback; available under Commands / Favorite commands',
    editor='favorite_slots',favorite_group=group,allowed_items=allowed_groups()[group],maxItems=3,uniqueItems=True)
    for key,group in FAVORITE_KEYS.items()]
SPECS += [spec('catalog.view','Existing catalogue view','Workspace','works','string',
    'Choose the presentation under Existing views. Cabinet filing, record identity and ownership do not change.',
    choices=['works','offices','work','archive'],choice_labels={'works':'Properties & works','offices':'Offices','work':'Work & ideas','archive':'Archive'},
    group='Cabinet',scope='Connected personal catalogue profile',scope_id='catalog_profile',supported_scopes=['catalog_profile'],
    store='Existing Concern catalogue preferences.view',application='immediate',effect='After Existing views consumer readback')]
# INTEGRATION-01: one bounded adapter over the existing per-pane hardware view map (single-key Set only; batch enum unchanged).
VIEW_MODES=('Auto view','Details','Thumbnails')
VIEW_MODES_KEY='hardware.category_views'
SPECS += [spec(VIEW_MODES_KEY,'Hardware category views','Workspace',{},'object',
    'Choose Auto view, Details or Thumbnails for each hardware category pane, keyed device/group. Panes not listed use Auto view. This changes file presentation only; no source is moved or opened.',
    group='Hardware',store='Session category_views',application='immediate',effect='After hardware pane readback; closed panes have no effect to report',
    editor='view_modes',view_modes=list(VIEW_MODES),maxProperties=100)]
# DESKTOP-01: the optional writing marker (VS03) over the existing presentation profile; the 41 prior definitions are untouched
# (single-key Set only; the public batch enum stays 17 keys).
WRITING_MARKER_KEY='appearance.writing_marker'
SPECS += [spec(WRITING_MARKER_KEY,'Writing marker','Appearance',True,'boolean',
    'Show a small graphite X in the page margin beside the line you are writing on, in the yellow writing passages (cabinet writing and title, New Idea sheet, settings value, return thread). Reduce motion keeps it still. Insertion, selection and keyboard editing are the same either way.',
    application='immediate',effect='After desktop presentation readback',store='Session writing_marker')]
# AGENT-02: whether a running assignment continues in the Graphite service (internally the Ledger service) when the window closes.
# The consumers are the desktop's close (agent_qt.continue_setting, read through ledger.settings.effective) and the service's
# 5 s tick (agent_loop.continue_when_closed reads the same Kernel settings row); single-key Set only.
CONTINUE_KEY='agent.continue_when_closed'
SPECS += [spec(CONTINUE_KEY,'Continue assignments while Graphite is closed','Slate',True,'boolean',
    'With the Graphite service running, an assignment keeps going there when you close the window, one step at a time, and Today tells you what it did. Off, closing the window pauses it and Today offers to resume it. Opening Graphite again takes the work back to this window.',
    root='Slate',group='Assignments',scope='Project private',scope_id='project_private',supported_scopes=['project_private'],
    store='Kernel settings: ledger.'+CONTINUE_KEY,application='next_use',effect='The next time Graphite closes; the Graphite service reads it on every tick',
    requires_owner=True)]
BY_KEY = {row['key']:row for row in SPECS}
SESSION_KEYS = SESSION_BATCH_KEYS | frozenset(FAVORITE_KEYS) | frozenset({VIEW_MODES_KEY,WRITING_MARKER_KEY})
OWNER_KEYS = frozenset({'stacy.provider','stacy.enabled','operations.services_enabled'} |
                      {row['key'] for row in SPECS if row.get('requires_owner')})
for key in OWNER_KEYS:BY_KEY[key]['requires_owner']=True
for key, dependencies in {
    'stacy.actions':['stacy.enabled','stacy.provider'],
    'stacy.share_activity':['stacy.enabled','stacy.provider'],
    'stacy.provider':['stacy.enabled'],
}.items():
    BY_KEY[key]['dependencies'] = dependencies


def natural(text):
    return tuple((1,int(part)) if part.isdigit() else (0,part.casefold()) for part in re.split(r'(\d+)',text))


# Graphite 0.1: the definitions themselves carry Graphite's words (labels, descriptions, effects); keys, defaults, kinds,
# scopes, stores and the two root keys are unchanged. The roots are shown as Workspace and Assistant (root keys Ledger and
# Slate stay, as the owner's rename asked: internal identifiers, settings keys and project paths are kept).
ROOT_NAMES={'Ledger':'Workspace','Slate':'Assistant'}


def public(row):
    """A setting row as the settings page shows it: the definition with its root's shown name (root_name) beside the
    unchanged root key."""
    return {**row,'root_name':ROOT_NAMES.get(row.get('root'),row.get('root'))}


def nodes():
    """Portable settings nodes; never presented as physical folders or records. The roots show their shown names."""
    result=[]
    for root in ('Ledger','Slate'):
        root_id='settings:'+root.casefold()
        result.append(dict(id=root_id,parent=None,role='settings_root',label=ROOT_NAMES[root],target=None,scope=None,provider='shared_settings'))
        groups=sorted({r['group'] for r in SPECS if r['root']==root},key=natural)
        for group in groups:
            group_id=root_id+':'+group.casefold()
            result.append(dict(id=group_id,parent=root_id,role='settings_group',label=group,target=None,scope=None,provider='shared_settings'))
            for row in sorted((r for r in SPECS if r['root']==root and r['group']==group),key=lambda r:natural(r['label'])):
                result.append(dict(id='setting:'+row['key'],parent=group_id,role='setting',label=row['label'],
                                   target=row['key'],scope=row['scope_id'],provider='shared_settings'))
    return result
