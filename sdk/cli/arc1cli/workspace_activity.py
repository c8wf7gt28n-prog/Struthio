"""Provider and GUI independent activity descriptions for Ledger clients."""
ACTIVITIES = (
    ('home', 'Home', 'console', 'show_start'),
    ('brain', 'Brain Link', 'brain-link', 'show_brain_link'),
    ('source', 'Source', 'c', 'open_source_workspace'),
    ('simulator', 'Simulator', 'trace', 'show_arcos'),
    ('book', 'Orange Book', 'manual', 'show_orange_book'),
)


def activity_for(kind, home=False):
    if home:
        return 'home'
    if kind in ('BrainLinkTab', 'CadViewerTab', 'HardwareOverviewTab', 'AssemblyTab'):
        return 'brain'
    if kind in ('OrangeBookTab', 'ManualTab', 'VendorTab', 'DatabaseROMTab'):
        return 'book'
    if kind in ('VirtualConsoleTab', 'NativeGameTab', 'ArcOSTab'):
        return 'simulator'
    return 'source'


def evidence_summary(job):
    """Return independent UI facts; lifecycle never becomes a test verdict."""
    state = str(job.get('state', 'Not run'))
    result = job.get('result') or {}
    return {'run': state, 'outcome': result.get('outcome', 'See evidence'),
            'review': 'Pending independent review', 'target': 'No physical board'}
