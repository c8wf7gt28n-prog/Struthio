"""Explicit shortcut placement; domain ancestry remains in the Concern catalog.

This is presentation data, never a dispatcher or an ownership/filesystem model.
New workspaces must choose a placement; registration does not add a tree root.
"""
LEGACY_WORKSPACES = (
    ('Inquiries', 'discovery'), ('Algorithm & Theory Atlas', 'algorithms'), ('Tool Atlas', 'atlas'),
    ('Office', 'office'), ('Organizer', 'organizer'), ('Package desk', 'packages'), ('Commands', 'commands'),
    ('Work trail', 'trail'), ('Recent activity', 'activity'), ('Graphite Brain', 'brain'), ('Graphite intake', 'intake'),
    ('Exact references', 'references'), ('Source connections', 'sources'), ('Memory', 'memory'),
    ('Graphite awareness', 'stacy_awareness'), ('Graphite knowledge', 'stacy_knowledge'),
)
SECTION_ROLES = {'ARRIVE': 'ARRIVAL_VIEW', 'FILES': 'LOCATION_SHORTCUT', 'LIBRARY': 'TYPE_FILTER_VIEW',
                 'KEEP': 'SAVED_WORK_VIEW', 'SLATE': 'OPERATIONAL_VIEW', 'PROJECTS': 'PROJECT_WORK_VIEW'}
FOLD_ORDER = ('CONCERN', 'PROJECTS', 'KEEP', 'SLATE', 'LIBRARY', 'ARRIVE')


def paper_sections(library_kinds):
    """Keep existing captions, order, counters and destination contracts intact."""
    return (
        ('ARRIVE', (('Ingress', 'office', 'folder', 'inbox'), ('Deliveries', 'office', 'evidence', 'deliveries'))),  # D28: Ingress is the owner's word for the folder files come in through
        ('FILES', (('Files', 'files', 'folder', 'files'), ("Graphite's area", 'files:Slate', 'folder', 'slate_area'),
                   ('Working copies', 'files:Working copies', 'folder', 'working'), ('Egress', 'files:Egress', 'folder', 'exports'))),  # D28: Egress is the folder files leave from
        ('LIBRARY', tuple((label, 'library:' + key, 'page-link', key) for key, label, _ in library_kinds)
                    + (('Everything', 'library:all', 'search', 'all'),)),
        ('KEEP', (('Inquiries', 'discovery', 'page-link', 'inquiries'),
                  ('Investigations', 'investigations', 'trace', 'investigations'),
                  ('Notes & notebooks', 'organizer', 'page-link', None), ('Lessons', 'memory', 'source-fact', 'lessons'))),
        ('SLATE', (('Agenda', 'agenda', 'trace', 'agenda'), ('Brain', 'slate', 'brain-link', 'brain'), ('Instruction matrix', 'matrix', 'trace', 'matrix'))),
        ('PROJECTS', (('Project Desk', 'project_desk', 'page-link', 'project_desk'), ('Changes', 'changes', 'page-link', 'changes'),
                      ('Continuing work', 'continuing', 'page-link', 'continuing'), ('Exchange & deployment', 'deployment', 'page-link', 'deployment'),
                      ('No project attached', 'project', 'console', 'project'))),
    )


def shortcut_id(section, destination, counter):
    return section.lower() + ':' + (counter or destination)


def describe(library_kinds):
    """Portable inventory for review without creating Qt objects or reading state."""
    rows = []
    for section, items in paper_sections(library_kinds):
        for label, destination, icon, counter in items:
            rows.append({'id': shortcut_id(section, destination, counter), 'section': section,
                         'label': label, 'destination': destination, 'role': SECTION_ROLES[section],
                         'count_key': counter, 'authority': 'NAVIGATION_ONLY'})
    if len({row['id'] for row in rows}) != len(rows): raise ValueError('NAVIGATOR_SHORTCUT_ID_COLLISION')
    return {'schema': 'ledger.navigator-shortcuts/1', 'rows': rows,
            'domain_tree': 'Existing sdk.cli.arc1cli.concern_catalog; separate provider, not copied into shortcuts',
            'footer': ['Settings', 'Trash'], 'placement_policy': {'discovery': 'KEEP', 'algorithms': 'TOOLS_MENU', 'atlas': 'TOOLS_MENU'},
            'auto_fold_order': list(FOLD_ORDER),
            'notice': 'Shortcut grouping is not object ancestry, a file move, a permission grant or a second execution registry.'}
