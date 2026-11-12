"""Focused Kernel connection concurrency check after the I02 fixture failure."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from .baseline import environment


def writer(root,who):
    from .engineering_kernel import Kernel
    kernel=Kernel(root)
    for i in range(80):
        with kernel.db() as db:db.execute('INSERT INTO audit VALUES(?,?,?,?)',(float(i),who,'guard-check','OK'))


def check(parent=None):
    from .engineering_kernel import Kernel
    from . import locations
    with tempfile.TemporaryDirectory(prefix='ledger-db-guard-',dir=parent) as temp:
        base=Path(temp);root=base/'Office';profile=base/'profile'
        with patch.dict(os.environ,environment(os.environ,root,profile)):
            locations.office(root);kernel=Kernel(root);other=Kernel(root)
            with kernel.db() as db:
                with other.db() as nested:nested.execute('SELECT 1').fetchone()
            children=[subprocess.Popen([sys.executable,'-m','workbench.database_checks','_writer',str(root),str(i)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=locations.child_env(root)) for i in range(2)]
            for _ in range(250):
                with kernel.db() as db:db.execute('SELECT COUNT(*) FROM audit').fetchone()
            for child in children:
                stdout,stderr=child.communicate(timeout=30)
                if child.returncode:raise ValueError('Concurrent Kernel writer failed: '+stderr[-500:])
            with kernel.db() as db:
                count=db.execute('SELECT COUNT(*) FROM audit').fetchone()[0];health=db.execute('PRAGMA quick_check').fetchone()[0]
            if count!=160 or health!='ok':raise ValueError('Database count/integrity mismatch')
            return {'state':'PASSED','concurrent_writers':2,'committed_records':count,'concurrent_reads':250,
                'nested_kernel_connections':'PASSED','quick_check':health,'scope':'Disposable Kernel DB; process/thread guard, WAL retained'}


def main():
    if len(sys.argv)>1 and sys.argv[1]=='_writer':writer(*sys.argv[2:]);return 0
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=check(args.parent);raw=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(raw)
    print(raw,end='');return 0


if __name__=='__main__':raise SystemExit(main())
