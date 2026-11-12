"""Closed-coordinator offline release installation and journal recovery."""
import argparse,json,os
from pathlib import Path
from .engineering_kernel import Kernel,operator


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--profile',type=Path);p.add_argument('--identity',default='desktop-owner');sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('install');a.add_argument('id');a.add_argument('--digest',required=True);a.add_argument('--directory',required=True)
 a=sub.add_parser('recover');a.add_argument('id');a.add_argument('--action',choices=['FINISH','REVERT_POINTER'],required=True)
 a=p.parse_args()
 if a.profile:
  from .baseline import environment
  os.environ.update(environment(os.environ,a.root,a.profile))
 k=Kernel(a.root)
 values={'id':a.id,'expected_digest':a.digest,'directory':a.directory} if a.command=='install' else {'id':a.id,'action':a.action}
 r=k.dispatch('releases.'+a.command,values,operator(a.identity));print(json.dumps(r,indent=2));return 0 if r['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
