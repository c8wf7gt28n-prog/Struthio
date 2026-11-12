"""Machine-readable UX asset catalog; no Qt dependency."""
from sdk.cli.arc1cli.ui_assets import AssetPack
from . import locations

FIELDS={'ux.catalog':({'query':{'type':'string','maxLength':200},'limit':{'type':'integer','minimum':1,'maximum':200}},[])}


def dispatch(kernel,op,args):return AssetPack(locations.program(kernel.root)).catalog(args.get('query',''),args.get('limit',100))
