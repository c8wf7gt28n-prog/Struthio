"""Registered narrow record check, used by baseline and candidate jobs."""
import argparse
import json
from pathlib import Path
from .register_proposals import validate_current


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['validate']);p.add_argument('--root',type=Path,default=Path.cwd());a=p.parse_args()
    result=validate_current(a.root);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
