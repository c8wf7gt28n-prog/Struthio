"""Small, validated, per-user Workbench preferences. Never stores executable code."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile

PRESETS={
    'Code': {'diagnostics':False,'output_visible':False,'file_pane_px':115,'output_pane_px':125,'folder':'firmware'},
    'Cartridge':{'diagnostics':False,'output_visible':False,'file_pane_px':240,'output_pane_px':160,'folder':'cartridges'},
    'Debug':{'diagnostics':True,'output_visible':True,'file_pane_px':115,'output_pane_px':260,'folder':'firmware'},
}
VERSION='arc1.workspaces/1'

def config_file():
    override=os.environ.get('ARC1_WORKBENCH_CONFIG_HOME')
    if override:return Path(override)/'workspace.json'
    if os.name=='nt':base=Path(os.environ.get('APPDATA',str(Path.home()/'AppData'/'Roaming')))/'ARC-1'/'Workbench'
    else:base=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'arc1-workbench'
    return base/'workspace.json'

class WorkspaceStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else config_file()
        self.state={'schema':VERSION,'active':'Code','layouts':{k:dict(v) for k,v in PRESETS.items()},'recent_file':None,'editor_index':'1.0'}
        self.load()
    def load(self):
        try:
            if self.path.stat().st_size>16_384:return
            data=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError,TypeError):return
        if not isinstance(data,dict) or data.get('schema')!=VERSION:return
        active=data.get('active')
        if active in PRESETS:self.state['active']=active
        incoming=data.get('layouts',{})
        if isinstance(incoming,dict):
            for preset in PRESETS:
                values=incoming.get(preset)
                if not isinstance(values,dict):continue
                layout=self.state['layouts'][preset]
                if type(values.get('diagnostics')) is bool:layout['diagnostics']=values['diagnostics']
                if type(values.get('output_visible')) is bool:layout['output_visible']=values['output_visible']
                for k in ('file_pane_px','output_pane_px'):
                    if type(values.get(k)) is int and 80<=values[k]<=600:layout[k]=values[k]
                folder=values.get('folder')
                if isinstance(folder,str) and folder in ('firmware','sdk','examples','cartridges','tests','workbench','docs'):
                    layout['folder']=folder
        f=data.get('recent_file')
        if isinstance(f,str) and len(f)<260 and '..' not in Path(f).parts and not Path(f).is_absolute():
            self.state['recent_file']=f
        ix=data.get('editor_index')
        import re
        if isinstance(ix,str) and re.fullmatch(r'\d{1,8}\.\d{1,5}',ix):self.state['editor_index']=ix
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.arc1-layout-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(self.state,f,sort_keys=True,indent=2);f.write('\n')
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    def set_active(self,name,**updates):
        if name not in PRESETS:raise ValueError('invalid preset')
        values=self.state['layouts'][name]
        for k,v in updates.items():
            if k in ('diagnostics','output_visible') and type(v) is bool:values[k]=v
            elif k in ('file_pane_px','output_pane_px') and type(v) is int and 80<=v<=600:values[k]=v
            elif k=='folder' and v in ('firmware','sdk','examples','cartridges','tests','workbench','docs'):values[k]=v
        self.state['active']=name
        self.save()
        return dict(values)
