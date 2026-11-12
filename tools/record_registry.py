"""Record Graphite's registry: write docs/GRAPHITE_0.1_REGISTRY.json from the live tree.

The release check (tools/check_release.py) compares the live program with this record. It holds:
- every public operation: its scope, a digest of its argument schema and a short digest of each top-level argument property;
- the job tools and the module each one runs;
- every setting definition's digest (and a short digest of each of its fields), the definitions' order and the settings digest;
- the adapters: the module and symbol that serve each operation, and the store and adapter each setting reads and writes;
- the schema digest (the workbench.doctor.inventory formula) and the counts.

Nothing is executed: the registry is read from engineering_kernel, engineering_cli and settings_registry as the program defines them.
The record carries no time stamp, so writing it again from an unchanged tree gives the same bytes.

Run it only when a change to an operation, a job tool, a setting definition or an adapter is meant:
  python3 tools/record_registry.py            write the record from the live tree
  python3 tools/record_registry.py --check    compare only; exit 1 and print the differences when the tree and the record differ
"""
import argparse,hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from workbench.version import title
RECORD='docs/GRAPHITE_0.1_REGISTRY.json'
SCHEMA='graphite.registry-record/1'
RELEASE=title()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def short(value):return sha(value)[:16]
def settings_digest(specs):return hashlib.sha256(json.dumps(specs,sort_keys=True).encode()).hexdigest()  # the formula the earlier records used


def live_sources():
    """The live registry as the program defines it: (inventory, job tool targets, operation handlers, setting definitions)."""
    from workbench.doctor import inventory
    from workbench.engineering_kernel import TOOLS
    from workbench.stacy_foundation import handler_map
    from workbench import settings_registry
    return inventory(),dict(TOOLS),handler_map(),list(settings_registry.SPECS)


def snapshot(sources=None):
    """The record's content for a registry; sources defaults to the live tree (tests pass fixtures)."""
    inventory,tools,handlers,specs=sources if sources is not None else live_sources()
    operations={}
    for row in inventory['operations']:
        arguments=row['arguments'];properties=arguments.get('properties') if isinstance(arguments,dict) else None
        operations[row['operation']]={'scope':row['scope'],'arguments':sha(arguments),
            'properties':{name:short(value) for name,value in sorted((properties or {}).items())}}
    settings={}
    for spec in specs:
        settings[spec['key']]={'definition':sha(spec),'fields':{name:short(value) for name,value in sorted(spec.items())}}
    adapters={'operations':{name:(handlers[name]['path']+'#'+handlers[name].get('symbol','')) if name in handlers else None for name in sorted(operations)},
        'settings':{spec['key']:{'store':spec.get('store'),'adapter':spec.get('adapter')} for spec in specs}}
    return {'schema':SCHEMA,'release':RELEASE,'generated_by':'tools/record_registry.py',
        'formulas':{'schema_digest':'sha256 of the workbench.doctor.inventory rows, canonical JSON (sorted keys, no spaces)',
            'arguments':'sha256 of the operation argument schema, canonical JSON; properties: its first 16 hex digits per top-level property',
            'definition':'sha256 of the setting definition, canonical JSON; fields: its first 16 hex digits per field',
            'settings_digest':'sha256 of json.dumps(settings_registry.SPECS, sort_keys=True)'},
        'counts':{'operations':len(operations),'job_tools':len(tools),'settings':len(specs),'adapters':sum(1 for v in adapters['operations'].values() if v)},
        'schema_digest':inventory['schema_digest'],'settings_digest':settings_digest(specs),
        'operations':operations,'job_tools':{name:list(target) if isinstance(target,(list,tuple)) else target for name,target in sorted(tools.items())},
        'settings_order':[spec['key'] for spec in specs],'settings':settings,'adapters':adapters}


def read(root=ROOT):
    """The record on disk, or None when it is absent or unreadable."""
    try:return json.loads((Path(root)/RECORD).read_text(encoding='utf-8'))
    except (OSError,ValueError):return None


def text(record):return json.dumps(record,indent=1,sort_keys=True,ensure_ascii=False)+'\n'


def write(root=ROOT,record=None):
    record=record if record is not None else snapshot();path=Path(root)/RECORD
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text(record),encoding='utf-8');return path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check',action='store_true',help='Compare the live tree with the record; write nothing')
    args=parser.parse_args(argv)
    live=snapshot()
    if args.check:
        sys.path.insert(0,str(ROOT/'tools'))
        from check_hatch import record_sections
        sections=record_sections(live,read())
        print(json.dumps(sections,indent=2));return 0 if all(v['state']=='PASSED' for v in sections.values()) else 1
    path=write(record=live)
    print(json.dumps({'state':'WRITTEN','record':RECORD,'path':str(path),**live['counts'],'schema_digest':live['schema_digest'],
        'settings_digest':live['settings_digest']},indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
