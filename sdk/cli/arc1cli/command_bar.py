"""Portable command-bar defaults and saved-favourite normalization."""

GROUPS = ('File', 'Edit', 'View', 'Options', 'Help')
MENU_TITLES = {'Options': 'Tools'}
DEFAULTS = {
    'File': ('open', 'save', 'save_all'),
    'Edit': ('undo', 'redo', 'find'),
    'View': ('focus_layout', 'split_editor', 'inspector'),
    'Options': ('build', 'run', 'tests'),
    'Help': ('orange_book', 'genesis', 'database_rom'),
}
# Former factory groups, upgraded only when a saved group still matches one exactly.
LEGACY_DEFAULTS = {
    'File': (('desk', 'open', 'save'),),
    'View': (('nav', 'nor', 'native_pcb'),),
    'Help': (('orange_book', 'keys', 'readiness'), ('orange_book', 'clip', 'database_rom')),
}


def normalize_favorites(saved, allowed, migrate_legacy=True):
    """Keep intentional choices, including empty groups, within three slots.

    Pre-versioned profiles upgrade exact former factory groups by default.
    Explicit version-two choices remain literal, including those same groups.
    Unknown identifiers are never turned into callable commands.
    """
    saved = saved if isinstance(saved, dict) else {}
    result = {}
    for group in GROUPS:
        choices = saved.get(group)
        if not isinstance(choices, list) or migrate_legacy and tuple(choices) in LEGACY_DEFAULTS.get(group, ()):
            choices = DEFAULTS[group]
        result[group] = []
        for key in choices:
            if isinstance(key, str) and key in allowed[group] and key not in result[group]:
                result[group].append(key)
                if len(result[group]) == 3:
                    break
    return result


# Shared by the existing Qt menus and the settings adapter; IDs grant no authority.
MENU_DEFINITIONS = {
            'File':['engineering','native_game','development','ledger','desk','new','open','quick','viewer','recovery',None,'save','save_all','close',None,'browse','refresh','newgame'],
            'Edit':['undo','redo',None,'cut','copy','paste','select',None,'find','find_next','replace','goto','project_search','definition','completion'],
            # Specialized workspaces live in three submenus so View fits on one screen.
            'View':['home','engineering_layout','focus_layout','object_glass',None,'fullscreen','reading','prose_more','prose_less','nav','inspector','output','problems','wrap','dual','split_editor','pin','reopen',None,
                    ('&Hardware workspaces',['brain_link','board','native_pcb','cad_checks','kibot_outputs','spice_checks','yosys_synthesis','fpga_implementation','hdl_waveforms','schematics','nor','hardware_proof','hardware_review','budgets','readiness']),
                    ('&Engineering workspaces',['developer_tools','arcos','trace','register','cartdock']),
                    ('&Knowledge && assets',['database_rom','vendor_vault','assets']),
                    None,'reset'],
            'Options':['discovery','algorithms','atlas','ledger_settings','ledger_commands','ledger_activity','stacy_knowledge','reading',None,'build','build_all','tests','run','stop','master_stop',None,'next','prev','boot',
                       'pkg','import','inspect_cart','stream','compare',None,'remote_link','palette','doctor','hw','inventory'],
            'Help':['orange_book','genesis','clip','database_rom',None,'setup_guide','manual','keys','readiness','about'],
        }

GROUP_LABELS = dict(File="Work", Edit="Revise", View="Arrange", Options="Tools", Help="Guide")
FAVORITE_KEYS = {"favorites."+group.casefold():group for group in GROUPS}

def allowed_groups():
    return {group:[key for entry in entries if entry is not None
        for key in (entry[1] if isinstance(entry,tuple) else [entry])]
        for group,entries in MENU_DEFINITIONS.items()}

def session_favorites(state):
    return normalize_favorites(state.get("toolbar_favorites",{}),allowed_groups(),
        migrate_legacy=state.get("toolbar_favorites_version",1)!=2)
