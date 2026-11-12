"""Fixed, bounded host case runner used by Arc Ledger GUI and agents."""
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workbench import development
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('baseline','working','compare'))
    p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args(argv)
    try:
        result=development.run(a.root,a.mode)
        print('DEVELOPMENT_RESULT '+result['state']+' [HOST_SIM; pending independent review]',flush=True)
        return 0 if result['state']=='CANDIDATE_PASS' else 1
    except Exception as exc:
        print('Development check failed: '+str(exc),file=sys.stderr,flush=True);return 1
if __name__=='__main__':raise SystemExit(main())
