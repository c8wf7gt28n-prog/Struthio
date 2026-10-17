"""ARC-1 Workbench portable/per-user installer with a Finder-style drag target.

No privileges or registry writes. Windows only for actual installation.
Drag left source tile onto the right destination tile, or click Install.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

ROOT=Path(__file__).resolve().parents[1]
BRAND='#DA741C';BG='#F4EAE0';DARK='#332923'
IGNORED={'__pycache__','.git','.venv','node_modules','build','.pytest_cache'}

def destination() -> Path:
    base=os.getenv('LOCALAPPDATA')
    if os.name!='nt' or not base:raise RuntimeError('Windows 11 per-user installation only; use the portable folder on other systems.')
    return Path(base)/'Programs'/'ARC-1 Workbench'

def _shortcut(folder:Path,launch:Path):
    # PowerShell is installed with Windows 11. No administrator rights required.
    ps= r'''$ErrorActionPreference = 'Stop'
$sh = New-Object -ComObject WScript.Shell
$start = [Environment]::GetFolderPath('StartMenu')
$dir = Join-Path $start 'Programs'
$shortcut = $sh.CreateShortcut((Join-Path $dir 'ARC-1 Workbench.lnk'))
$shortcut.TargetPath = $env:ARC1_START
$shortcut.WorkingDirectory = $env:ARC1_FOLDER
$shortcut.Description = 'ARC-1 Workbench - Adaptive RISC-V Console Development'
$shortcut.Save()
'''
    env=dict(os.environ,ARC1_START=str(launch),ARC1_FOLDER=str(folder))
    completed=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],
                 env=env,capture_output=True,text=True,timeout=30)
    if completed.returncode!=0:raise RuntimeError('Start Menu shortcut failed: '+completed.stderr[-400:])

def install()->Path:
    target=destination()
    if target.resolve()==ROOT.resolve() or ROOT.resolve().is_relative_to(target.resolve()):
        raise RuntimeError('Cannot install into the source tree')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.parent/(target.name+'.incoming')
    backup=target.parent/(target.name+'.previous')
    if temp.exists() or backup.exists():
        raise RuntimeError('A previous incomplete install exists; examine the .incoming/.previous folders before retrying.')
    try:
        shutil.copytree(ROOT,temp,ignore=shutil.ignore_patterns(*IGNORED,'*.pyc','*.pyo'),symlinks=False)
        if not (temp/'START_ARC1.cmd').is_file():raise RuntimeError('Installer sanity check failed')
        if target.exists():target.rename(backup)
        try:temp.rename(target)
        except Exception:
            if backup.exists():backup.rename(target)
            raise
    finally:
        if temp.exists():shutil.rmtree(temp)
    # Keep an existing backup until shortcut succeeds (for lossless recovery).
    try:_shortcut(target,target/'START_ARC1.cmd')
    except Exception:
        # Installed app remains available even without the optional shortcut.
        if backup.exists():shutil.rmtree(backup)
        raise
    if backup.exists():shutil.rmtree(backup)
    return target

class DragInstall(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ARC-1 Workbench — Install to My Apps')
        self.geometry('655x310');self.resizable(False,False);self.configure(bg=BG)
        tk.Label(self,text='ARC-1 WORKBENCH',font=('Segoe UI',19,'bold'),bg=BG,fg=DARK).pack(pady=(19,3))
        tk.Label(self,text='Drag the application into My Apps to install. No administrator access required.',
                 font=('Segoe UI',10),bg=BG,fg='#685A51').pack()
        icons=tk.Frame(self,bg=BG);icons.pack(fill='x',pady=(23,7),padx=55)
        self.source=tk.Label(icons,text='ARC-1\nWORKBENCH',font=('Segoe UI',15,'bold'),
                width=16,height=5,bg='#402D24',fg='#F9CF94',cursor='hand2',relief='ridge',bd=3)
        self.source.pack(side='left')
        tk.Label(icons,text='→',font=('Segoe UI',32),bg=BG,fg=BRAND).pack(side='left',expand=True)
        self.target=tk.Label(icons,text='MY APPS\n(LOCAL USER)',font=('Segoe UI',14,'bold'),
                width=16,height=5,bg='#F6D8AF',fg=DARK,relief='ridge',bd=3)
        self.target.pack(side='right')
        self.source.bind('<ButtonRelease-1>',self.drop)
        self.source.bind('<B1-Motion>',self.drag)
        tk.Button(self,text='Install to My Apps',command=self.install_now,bg='#E9A352',fg=DARK,
                  activebackground='#FFBA67',font=('Segoe UI',10,'bold')).pack(pady=7)
        tk.Label(self,text='You can also drag the extracted application folder anywhere and run START_ARC1.cmd.',
                  font=('Segoe UI',9),fg='#725D52',bg=BG).pack()
    def drag(self,event):
        x=self.winfo_pointerx()-self.target.winfo_rootx()
        y=self.winfo_pointery()-self.target.winfo_rooty()
        self.target.configure(bg='#FFB961' if 0<=x<self.target.winfo_width() and 0<=y<self.target.winfo_height() else '#F6D8AF')
    def drop(self,event):
        self.drag(event)
        x=self.winfo_pointerx()-self.target.winfo_rootx()
        y=self.winfo_pointery()-self.target.winfo_rooty()
        if 0<=x<self.target.winfo_width() and 0<=y<self.target.winfo_height():self.install_now()
        self.target.configure(bg='#F6D8AF')
    def install_now(self):
        try:
            dst=destination()
            if not messagebox.askyesno('Install ARC-1 Workbench',f'Copy the application into:\n{dst}\n\nand create a Start Menu shortcut?'):
                return
            p=install()
            messagebox.showinfo('Installation completed',f'Installed to:\n{p}\n\nLaunch ARC-1 Workbench from the Start Menu.')
        except Exception as e:messagebox.showerror('Installation did not complete',str(e))

if __name__=='__main__':DragInstall().mainloop()
