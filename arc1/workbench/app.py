"""ARC-1 Workbench R08: orange Aqua visual design / File Manager interaction.

Human UI: folder tree, directory contents, menu bar, editor and console.
Agent UI: separate workbench.agent stdio JSON-lines endpoint.
No physical device flashing is implemented.
"""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from .bootlogic import BootModel
from .output_router import OutputRouter
from .cartridge import package_game, inspect_cartridge, simulate_stream, CartridgeError
from .launcher import HostLauncher, LauncherError, games_on_shelf, prepare
from .workspaces import WorkspaceStore, PRESETS
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DnDBase = TkinterDnD.Tk
except ImportError:
    DnDBase = tk.Tk
    DND_FILES = None
from tkinter import filedialog, messagebox, ttk, simpledialog

ROOT=Path(__file__).resolve().parents[1]
# ARC-1 logo palette (shared with the Qt theme): near-black, brushed steel, ARC-1 orange.
BLACK='#0b0b0c'; PANEL='#141517'; RAISED='#1d1f22'; STEEL_DARK='#2a2d31'; LINE='#33373c'
STEEL='#a9aeb4'; TEXT='#e4e6e8'; MUTED='#7d838a'; SELECT='#ffffff'
ORANGE='#ff5a1a'; ORANGE_DEEP='#c8400c'; ORANGE_SOFT='#3a1d10'
BG=BLACK; HILITE=ORANGE_SOFT; NAVY=RAISED; INK=TEXT; SUB=STEEL; GREEN='#5fd08f'
ACTION={
 'Build F133 stage':['firmware','image','--target','f133'],
 'Build D213 stage':['firmware','image','--target','d213'],
 'Build both stages':['firmware','image','--target','all'],
 'Build LCD module':['firmware','build','--target','status-lcd'],
 'Build game':['build','examples/hello_arc1'],
 'Firmware tests':['firmware','test'],
 'Game tests':['test','examples/hello_arc1'],
 'Simulate game':['sim','examples/hello_arc1','--frames','120','--dump','0,60,119'],
 'Hardware report':['hw','inspect'],
 'Brand verification':['brand'],
 'System check':['doctor'],
}
DIRS=('firmware','sdk','workbench','examples','cartridges','hardware','branding','docs','tests')
IGNORED={'__pycache__','.git','build','.venv','node_modules'}
EDIT_EXT={'.c','.h','.S','.s','.py','.md','.json','.txt','.ld','.csv','.cmd','.sh','.yaml','.yml'}

class AquaButton(tk.Canvas):
    """Compact restrained controls: graphite, subtle geometry, orange active marker."""
    def __init__(self,parent,text,command,primary=False):
        import tkinter.font as tkfont
        self.command=command;self.text=text;self.primary=primary;self.pressed=False;self.hover=False
        self.font=tkfont.Font(family='Segoe UI',size=9,weight='bold' if primary else 'normal')
        super().__init__(parent,height=30,width=max(57,self.font.measure(text)+23),
                         background=parent.cget('bg'),highlightthickness=0,bd=0,relief='flat',
                         cursor='hand2',takefocus=1)
        self.bind('<Configure>',self._paint);self.bind('<Enter>',self._enter)
        self.bind('<Leave>',self._leave);self.bind('<Button-1>',self._press)
        self.bind('<ButtonRelease-1>',self._release)
        self.bind('<Return>',self._key);self.bind('<space>',self._key)
        self.bind('<FocusIn>',self._paint);self.bind('<FocusOut>',self._paint)
        self._paint()
    def _paint(self,event=None):
        self.delete('all')
        w=max(25,self.winfo_width());h=max(25,self.winfo_height())
        shade=STEEL_DARK if not self.hover else LINE
        if self.pressed:shade=ORANGE_SOFT
        self.create_rectangle(1,1,w-2,h-2,fill=shade,outline=LINE if not self.hover else MUTED,width=1)
        self.create_line(2,2,w-3,2,fill='#44494f')          # brushed-steel top edge
        if self.primary:self.create_rectangle(2,h-4,w-3,h-2,fill=ORANGE,outline='')
        if self.focus_get()==self:self.create_rectangle(3,3,w-4,h-4,outline=ORANGE,dash=(2,2))
        self.create_text(w/2,h/2,text=self.text,font=self.font,fill=TEXT)
    def _enter(self,event):self.hover=True;self._paint()
    def _leave(self,event):self.hover=False;self.pressed=False;self._paint()
    def _press(self,event):self.focus_set();self.pressed=True;self._paint()
    def _release(self,event):
        activate=self.pressed and 0<=event.x<=self.winfo_width() and 0<=event.y<=self.winfo_height()
        self.pressed=False;self._paint()
        if activate:self.command()
    def _key(self,event):self.command();return 'break'

class Workbench(DnDBase):
    def __init__(self):
        super().__init__()
        self.title('ARC-1 Workbench R09 — Adaptive RISC-V Development')
        self.geometry('1440x900');self.minsize(1050,670)
        self.configure(bg=BG)
        self.open_file=None;self.modified=False;self.busy=False
        self.router=OutputRouter();self.output_visible=True;self.output_autorevealed=False
        self.boot_model=BootModel();self.boot_sequence=['f133','nor','d213','fpga12','fpga45','ready']
        self.work_queue=queue.Queue();self.selected_dir=ROOT
        self.internal_drag=None;self.agent_dnd_available=(DND_FILES is not None)
        self.workspaces=WorkspaceStore();self.host_launcher=HostLauncher(ROOT);self.launch_window=None
        self.launch_preview=None;self.launch_preview_files=[];self.launch_preview_idx=0
        self._style();self._layout();self._menu();self._shortcuts()
        self.populate_tree();self.show_directory(ROOT)
        self.open_source(ROOT/'firmware'/'stage'/'f133_stage.c',confirm=False)
        self.after(180,self.restore_workspace)
        self.after(80,self.poll_output)
        self.protocol('WM_DELETE_WINDOW',self.on_close)

    def _style(self):
        for name,value in (('*Menu.background',RAISED),('*Menu.foreground',TEXT),
                           ('*Menu.activeBackground',ORANGE_SOFT),('*Menu.activeForeground',SELECT),
                           ('*Menu.disabledForeground',MUTED),('*Menu.selectColor',ORANGE),
                           ('*Menu.relief','flat'),('*Menu.borderWidth',1),
                           ('*Background',BG),('*Foreground',TEXT),
                           ('*Entry.background',PANEL),('*Entry.foreground',TEXT),('*Entry.insertBackground',ORANGE),
                           ('*Entry.selectBackground',ORANGE_SOFT),('*Entry.selectForeground',SELECT),
                           ('*Listbox.background',PANEL),('*Listbox.foreground',TEXT),
                           ('*Listbox.selectBackground',ORANGE_SOFT),('*Listbox.selectForeground',SELECT),
                           ('*Text.background',PANEL),('*Text.foreground',TEXT),('*Text.insertBackground',ORANGE),
                           ('*Text.selectBackground',ORANGE_SOFT),('*Text.selectForeground',SELECT),
                           ('*Button.background',STEEL_DARK),('*Button.foreground',TEXT),
                           ('*Button.activeBackground',LINE),('*Button.activeForeground',SELECT),
                           ('*Checkbutton.selectColor',PANEL),('*Radiobutton.selectColor',PANEL),
                           ('*highlightBackground',LINE),('*highlightColor',ORANGE)):
            self.option_add(name,value)
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',background=BG,foreground=TEXT,fieldbackground=PANEL,bordercolor=LINE,
                        lightcolor=STEEL_DARK,darkcolor=BLACK,troughcolor=BLACK,
                        selectbackground=ORANGE_SOFT,selectforeground=SELECT,insertcolor=ORANGE)
        style.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=INK,
                        rowheight=29,borderwidth=0,font=('Segoe UI',10))
        style.configure('Treeview.Heading',background=RAISED,foreground=STEEL,bordercolor=LINE,
                        lightcolor=RAISED,darkcolor=RAISED,
                        font=('Segoe UI',9,'bold'),relief='flat',padding=(7,7))
        style.map('Treeview.Heading',background=[('active',STEEL_DARK)],foreground=[('active',TEXT)])
        style.map('Treeview',background=[('selected',ORANGE_SOFT)],foreground=[('selected',SELECT)])
        style.configure('TPanedwindow',background=BG)
        style.configure('TNotebook',background=BG,borderwidth=0,bordercolor=LINE,lightcolor=BG,darkcolor=BG)
        style.configure('TNotebook.Tab',background=RAISED,foreground=STEEL,padding=(20,9),
                        bordercolor=LINE,lightcolor=RAISED,darkcolor=RAISED,font=('Segoe UI',10))
        style.map('TNotebook.Tab',background=[('selected',PANEL),('active',STEEL_DARK)],
                  foreground=[('selected',ORANGE),('active',TEXT)],lightcolor=[('selected',ORANGE)])
        for bar in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
            style.configure(bar,background=STEEL_DARK,troughcolor=BLACK,arrowcolor=ORANGE,bordercolor=LINE,
                            lightcolor=STEEL_DARK,darkcolor=STEEL_DARK)
            style.map(bar,background=[('active',LINE),('pressed',ORANGE_DEEP)])
    def _button(self,parent,text,callback,primary=False):
        return AquaButton(parent,text,callback,primary=primary)
    def _aqua_header(self):
        # Compact orange Aqua title bar: branding without a 93px billboard.
        top=tk.Canvas(self,height=51,bg=BLACK,highlightthickness=0)
        top.pack(side='top',fill='x');top.pack_propagate(False)
        for y in range(0,50,2):
            t=y/50
            a=(34,36,40);b=(11,11,12)           # brushed steel fading to black
            r,g,bl=[int(a[i]*(1-t)+b[i]*t) for i in range(3)]
            top.create_rectangle(0,y,2300,y+2,fill=f'#{r:02x}{g:02x}{bl:02x}',outline='')
        top.create_rectangle(0,48,2500,51,fill=ORANGE,outline='')
        try:
            self.brand_image=tk.PhotoImage(file=str(ROOT/'workbench'/'logo_compact.png'))
            top.create_image(9,4,image=self.brand_image,anchor='nw')
        except tk.TclError:
            top.create_text(14,9,text='ARC-1',anchor='nw',fill=ORANGE,font=('Segoe UI',18,'bold'))
        top.create_text(169,9,text='Workbench',fill=TEXT,anchor='nw',font=('Segoe UI',18,'bold'))
        top.create_text(322,19,text='ADAPTIVE RISC-V DEVELOPMENT',fill=STEEL,anchor='nw',font=('Segoe UI',9))
        self.top_status=top.create_text(1404,26,text='R09  /  HOST SIM  /  BOARD OFFLINE',
                                        anchor='e',fill=ORANGE,font=('Segoe UI',9,'bold'))
        def reposition(event):top.coords(self.top_status,max(680,event.width-17),26)
        top.bind('<Configure>',reposition)
        return top

    def _layout(self):
        self._aqua_header()
        self.toolbar=tk.Frame(self,bg=RAISED,bd=0,highlightthickness=1,highlightbackground=LINE);self.toolbar.pack(side='top',fill='x')
        for title,call in [('Open',self.choose_file),('Save',self.save_source),('Find',self.find_text),
                           ('F133 Build',lambda:self.run_action('Build F133 stage')),
                           ('D213 Build',lambda:self.run_action('Build D213 stage')),
                           ('Build Both',lambda:self.run_action('Build both stages')),
                           ('Run Tests',lambda:self.run_action('Firmware tests')),
                           ('Cartridge',self.open_launcher),('Agent API',self.show_agent_help)]:
            self._button(self.toolbar,title,call,primary=(title=='Build Both')).pack(side='left',padx=(3,1),pady=3)
        self.addr=tk.StringVar(value='C:\\ARC-1\\')
        addrrow=tk.Frame(self,bg=BG);addrrow.pack(fill='x',padx=7,pady=(4,4))
        tk.Label(addrrow,text='Directory:',bg=BG,fg=INK).pack(side='left')
        tk.Entry(addrrow,textvariable=self.addr,state='readonly',font=('Consolas',9),bg=PANEL,readonlybackground=PANEL,fg=INK,relief='flat',highlightthickness=1,highlightbackground=LINE,highlightcolor=ORANGE).pack(side='left',fill='x',expand=True,padx=8)
        tk.Label(addrrow,text='F133 + D213 / RV64   •   STAGING ONLY',bg=BG,fg=ORANGE).pack(side='right')
        main=tk.PanedWindow(self,orient='horizontal',sashwidth=5,bg=LINE,bd=0,relief='flat')
        self.main_pane=main
        main.pack(fill='both',expand=True,padx=7,pady=(0,4))
        treebox=tk.Frame(main,bg=PANEL);main.add(treebox,minsize=175,width=240,stretch='never')
        tk.Label(treebox,text='  PROJECT NAVIGATOR',anchor='w',bg=NAVY,fg=TEXT,padx=7,pady=4,font=('Segoe UI',10,'bold')).pack(fill='x')
        self.dir_tree=ttk.Treeview(treebox,show='tree',selectmode='browse')
        tree_y=ttk.Scrollbar(treebox,orient='vertical',command=self.dir_tree.yview)
        self.dir_tree.configure(yscrollcommand=tree_y.set)
        tree_y.pack(side='right',fill='y');self.dir_tree.pack(side='left',fill='both',expand=True)
        self.dir_tree.bind('<<TreeviewSelect>>',self.on_dir_select)
        self.dir_tree.bind('<<TreeviewOpen>>',self.on_dir_open)
        if DND_FILES:
            self.dir_tree.drop_target_register(DND_FILES)
            self.dir_tree.dnd_bind('<<Drop>>',self.handle_external_drop)
        content=tk.PanedWindow(main,orient='vertical',sashwidth=5,bg=LINE);main.add(content,minsize=400,stretch='always')
        self.vertical_pane=content
        filesbox=tk.Frame(content,bg=PANEL);content.add(filesbox,minsize=95,height=174);self.files_box=filesbox
        tk.Label(filesbox,text='  FILES   /   DOUBLE-CLICK TO OPEN',anchor='w',bg=NAVY,fg=TEXT,padx=7,pady=4,font=('Segoe UI',10,'bold')).pack(fill='x')
        self.file_tree=ttk.Treeview(filesbox,columns=('type','size'),show='tree headings',selectmode='browse')
        self.file_tree.heading('#0',text='Name',anchor='w');self.file_tree.heading('type',text='Type',anchor='w');self.file_tree.heading('size',text='Size',anchor='e')
        self.file_tree.column('#0',width=380);self.file_tree.column('type',width=140);self.file_tree.column('size',width=100,anchor='e')
        fy=ttk.Scrollbar(filesbox,orient='vertical',command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=fy.set)
        fy.pack(side='right',fill='y');self.file_tree.pack(fill='both',expand=True)
        self.file_tree.bind('<Double-1>',self.on_file_open)
        self.file_tree.bind('<ButtonPress-1>',self.start_internal_drag,add='+')
        self.file_tree.bind('<ButtonRelease-1>',self.finish_internal_drag,add='+')
        if DND_FILES:
            self.file_tree.drop_target_register(DND_FILES)
            self.file_tree.dnd_bind('<<Drop>>',self.handle_external_drop)
        editbox=tk.Frame(content,bg=PANEL);content.add(editbox,minsize=160,height=463)
        pathrow=tk.Frame(editbox,bg=RAISED);pathrow.pack(fill='x')
        self.file_path=tk.StringVar(value='No file open')
        tk.Label(pathrow,textvariable=self.file_path,bg=RAISED,fg=INK,font=('Segoe UI',9,'bold'),anchor='w').pack(side='left',padx=5,fill='x',expand=True)
        self.dirty=tk.Label(pathrow,text='',bg=RAISED,fg=ORANGE,font=('Segoe UI',9,'bold'))
        self.dirty.pack(side='right',padx=10)
        self._button(pathrow,'Output F10',self.toggle_output).pack(side='right',padx=(2,7),pady=1)
        editorframe=tk.Frame(editbox,bg=PANEL);editorframe.pack(fill='both',expand=True)
        self.editor=tk.Text(editorframe,undo=True,wrap='none',font=('Consolas',11),bg=PANEL,fg=INK,
                            insertbackground=ORANGE,selectbackground=ORANGE_SOFT,selectforeground=SELECT,relief='flat',bd=0,padx=12,pady=12)
        sy=ttk.Scrollbar(editorframe,orient='vertical',command=self.editor.yview)
        sx=ttk.Scrollbar(editorframe,orient='horizontal',command=self.editor.xview)
        self.editor.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');self.editor.pack(fill='both',expand=True)
        self.editor.bind('<<Modified>>',self.on_modified)
        self.editor.bind('<KeyRelease>',lambda e:self.editor_status())
        outputframe=tk.Frame(content,bg=PANEL);content.add(outputframe,minsize=90,height=140);self.output_box=outputframe
        self.tabs=ttk.Notebook(outputframe);self.tabs.pack(fill='both',expand=True)
        consolebox=tk.Frame(self.tabs,bg=PANEL);self.tabs.add(consolebox,text='Build Console  /  DOS Commands')
        self.console=tk.Text(consolebox,height=9,state='disabled',bg=BLACK,fg=TEXT,insertbackground=ORANGE,font=('Consolas',9),wrap='word')
        cy=ttk.Scrollbar(consolebox,command=self.console.yview);self.console.configure(yscrollcommand=cy.set)
        cy.pack(side='right',fill='y');self.console.pack(fill='both',expand=True)
        self.write_console('ARC-1 WORKBENCH R09  |  HOST ONLY  |  Use Build menu or Alt+B.\nC:\\ARC-1> ')
        agentframe=tk.Frame(self.tabs,bg=PANEL);self.tabs.add(agentframe,text='Agent API')
        self.agent_info=tk.Text(agentframe,bg=PANEL,fg=INK,insertbackground=ORANGE,font=('Consolas',9),wrap='word',relief='flat',padx=12,pady=8)
        self.agent_info.pack(fill='both',expand=True)
        self.agent_info.insert('1.0','ARC-1 Agent Interface v1 — separate headless UI\n\n'
          'Windows Command Prompt:  py -3 arc1 agent\n'
          'Source editing opt-in: py -3 arc1 agent --allow-writes\n\n'
          'Request (one JSON object per line):\n'
          '{"id":1,"method":"hello"}\n'
          '{"id":2,"method":"capabilities"}\n'
          '{"id":3,"method":"build.both"}\n'
          '{"id":4,"method":"files.list","params":{"path":"firmware"}}\n\n'
          'R07: launcher.list, launcher.launch_sim, launcher.status, launcher.stop_sim\n'
          'See docs/AGENT_INTERFACE_R07.md. No flash methods or arbitrary shell commands.\n')
        self.agent_info.configure(state='disabled')
        activity=tk.Frame(self.tabs,bg=PANEL)
        self.tabs.add(activity,text='Agent Activity')
        self.agent_activity=tk.Text(activity,state='disabled',bg=PANEL,fg=INK,font=('Consolas',9))
        self.agent_activity.pack(fill='both',expand=True)
        self._set_readonly(self.agent_activity,'No live agent event stream connected.\nThe headless agent API runs independently; event sharing is a future integration.\nNo activity is invented.')
        buildframe=tk.Frame(self.tabs,bg=PANEL)
        self.tabs.insert(1,buildframe,text='Build Output')
        self.build_log=tk.Text(buildframe,height=7,state='disabled',bg=BLACK,fg=TEXT,insertbackground=ORANGE,font=('Consolas',9))
        self.build_log.pack(fill='both',expand=True)
        problemsframe=tk.Frame(self.tabs,bg=PANEL)
        self.tabs.insert(2,problemsframe,text='Problems')
        self.problem_log=tk.Text(problemsframe,height=7,state='disabled',bg=PANEL,fg=INK,font=('Consolas',9))
        self.problem_log.pack(fill='both',expand=True)
        debugframe=tk.Frame(self.tabs,bg=PANEL)
        self.tabs.insert(3,debugframe,text='Debug')
        self.debug_log=tk.Text(debugframe,height=7,state='disabled',bg=PANEL,fg=INK,font=('Consolas',9))
        self.debug_log.pack(fill='both',expand=True)
        self._set_readonly(self.problem_log,'No compiler diagnostics yet. Run Build to examine errors.')
        self._set_readonly(self.debug_log,'HOST SIMULATION ONLY. No physical registers, traces or board telemetry.')
        self._set_readonly(self.build_log,'No build has run in this session.')
        info=tk.Frame(main,bg=PANEL,width=234);self.diagnostic_panel=info;self.diagnostics_visible=True
        main.add(info,minsize=228,width=260,stretch='never')
        tk.Label(info,text='  BOOT DIAGNOSTICS',bg=NAVY,fg=TEXT,anchor='w',padx=7,pady=4,font=('Segoe UI',10,'bold')).pack(fill='x')
        tk.Label(info,text='16 × 2  CHARACTER DISPLAY',bg=PANEL,fg=SUB,
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=13,pady=(15,6))
        bezel=tk.Frame(info,bg=STEEL_DARK,padx=7,pady=7,highlightthickness=2,
                       highlightbackground=ORANGE_DEEP);bezel.pack(fill='x',padx=13,pady=(0,8))
        self.lcd=tk.Label(bezel,text='ARC-1  POWER   \nRAILS CHECK     ',
                 font=('Courier New',13,'bold'),bg='#120804',fg=ORANGE,
                 justify='center',height=3,width=20)
        self.lcd.pack(fill='x')
        tk.Label(info,text='HOST SIMULATOR  •  NOT DEVICE TELEMETRY',bg=PANEL,
                 fg=ORANGE,font=('Segoe UI',8,'bold'),wraplength=240).pack(padx=9,pady=(2,12))
        controls=tk.Frame(info,bg=PANEL);controls.pack(fill='x',padx=12)
        self._button(controls,'Next test',self.advance_boot,primary=True).pack(side='left',padx=(0,5),fill='x',expand=True)
        self._button(controls,'Fault',self.inject_fault).pack(side='left',fill='x',expand=True)
        self._button(info,'Reset simulated boot',self.reset_boot).pack(fill='x',padx=12,pady=(6,14))
        tk.Label(info,text='SIMULATED BOOT EVIDENCE',bg=PANEL,fg=SUB,
                 font=('Segoe UI',9,'bold')).pack(anchor='w',padx=13,pady=(0,5))
        self.proof_labels={}
        for bit,name in [('f133','F133   SYSTEM'),('nor','NOR    VERIFY'),('d213','D213   VIDEO'),
                         ('fpga12','12F    CONFIG'),('fpga45','45F    CONFIG')]:
            row=tk.Frame(info,bg=PANEL);row.pack(fill='x',padx=14,pady=3)
            tk.Label(row,text=name,bg=PANEL,fg=INK,font=('Consolas',9)).pack(side='left')
            val=tk.Label(row,text='UNVERIFIED',bg=PANEL,fg=MUTED,font=('Consolas',8,'bold'))
            val.pack(side='right');self.proof_labels[bit]=val
        tk.Frame(info,height=1,bg=LINE).pack(fill='x',padx=14,pady=13)
        tk.Label(info,text='BOARD NOT CONNECTED',bg=PANEL,fg=ORANGE,
                 font=('Segoe UI',10,'bold')).pack(anchor='w',padx=13)
        tk.Label(info,text='Firmware link-stage files are NOT bootable.  '
                 'USB and physical flash writes are not enabled.',bg=PANEL,fg=SUB,
                 font=('Segoe UI',9),justify='left',wraplength=234).pack(anchor='w',padx=13,pady=(8,10))
        status=tk.Frame(self,bg=RAISED,relief='flat',bd=0,height=34)
        status.pack(fill='x',side='bottom');status.pack_propagate(False)
        self.edit_status=tk.Label(status,text='Ready',bg=RAISED,fg=TEXT,
                 font=('Segoe UI',9),anchor='w')
        self.edit_status.pack(side='left',fill='x',expand=True,padx=15)
        tk.Label(status,text='AGENT JSON-LINES READY    •    HARDWARE OFFLINE    •    DEPLOY LOCKED',
                 bg=RAISED,fg=ORANGE,font=('Segoe UI',9,'bold')).pack(side='right',padx=12)
        self._refresh_boot()

    def _refresh_boot(self):
        a,b=self.boot_model.lcd()
        self.lcd.configure(text=a+'\n'+b)
        from .bootlogic import BITS
        for k,w in self.proof_labels.items():
            verified=bool(self.boot_model.verified & BITS[k])
            w.configure(text='SIM PASS' if verified else 'UNVERIFIED',
                        fg=GREEN if verified else MUTED)

    def reset_boot(self):
        self.boot_model=BootModel()
        self._refresh_boot()
        self.write_console('\nHOST SIMULATION: Boot model reset. Physical board remains offline.\n')

    def inject_fault(self):
        try:self.boot_model.fault(0x1203)
        except ValueError:self.reset_boot();self.boot_model.fault(0x1203)
        self._refresh_boot()
        self.write_console('\nHOST SIMULATION: Latched fault 0x1203. No device telemetry.\n')

    def _menu(self):
        bar=tk.Menu(self)
        f=tk.Menu(bar,tearoff=0)
        f.add_command(label='Open...\tCtrl+O',command=self.choose_file)
        f.add_command(label='Save\tCtrl+S',command=self.save_source)
        f.add_command(label='Quick open...\tCtrl+P',command=self.quick_open)
        f.add_separator();f.add_command(label='Exit',command=self.on_close)
        bar.add_cascade(label='File',menu=f)
        e=tk.Menu(bar,tearoff=0)
        for title,cb in [('Undo',lambda:self.editor.event_generate('<<Undo>>')),
                          ('Cut',lambda:self.editor.event_generate('<<Cut>>')),
                          ('Copy',lambda:self.editor.event_generate('<<Copy>>')),
                          ('Paste',lambda:self.editor.event_generate('<<Paste>>')),
                          ('Find...\tCtrl+F',self.find_text)]:e.add_command(label=title,command=cb)
        bar.add_cascade(label='Edit',menu=e)
        v=tk.Menu(bar,tearoff=0)
        v.add_command(label='Go to project root',command=lambda:self.show_directory(ROOT))
        v.add_command(label='Firmware folder',command=lambda:self.show_directory(ROOT/'firmware'))
        v.add_command(label='SDK folder',command=lambda:self.show_directory(ROOT/'sdk'))
        v.add_command(label='Cartridge shelf',command=lambda:self.show_directory(ROOT/'cartridges'))
        v.add_separator()
        v.add_command(label='Toggle diagnostics pane\tF9',command=self.toggle_diagnostics)
        v.add_command(label='Toggle output panel\tF10',command=self.toggle_output)
        v.add_separator()
        for preset in PRESETS:v.add_command(label=f'{preset} workspace',command=lambda p=preset:self.apply_workspace(p))
        bar.add_cascade(label='View',menu=v)
        b=tk.Menu(bar,tearoff=0)
        for name in ACTION:
            b.add_command(label=name,command=lambda n=name:self.run_action(n))
        bar.add_cascade(label='Build',menu=b)
        cart=tk.Menu(bar,tearoff=0)
        cart.add_command(label='Game launcher...\tF6',command=self.open_launcher)
        cart.add_command(label='Package example game...',command=self.make_cartridge)
        cart.add_command(label='Import existing cartridge...',command=self.import_cartridge_dialog)
        cart.add_command(label='Inspect cartridge...',command=self.inspect_cartridge_dialog)
        cart.add_command(label='Simulate USB asset streaming...',command=self.stream_cartridge_dialog)
        cart.add_separator()
        cart.add_command(label='Open cartridge shelf',command=lambda:self.show_directory(ROOT/'cartridges'))
        bar.add_cascade(label='Cartridge',menu=cart)
        t=tk.Menu(bar,tearoff=0)
        t.add_command(label='Agent API / protocol',command=self.show_agent_help)
        t.add_command(label='Inspect host simulation status',command=self.inspect_host_debug)
        t.add_command(label='Command palette...\tCtrl+Shift+P',command=self.command_palette)
        t.add_command(label='Hardware deployment status',command=lambda:messagebox.showinfo('Deployment','Not available. Linked-stage files are NOT bootable and physical NOR flashing is disabled.'))
        bar.add_cascade(label='Tools',menu=t)
        h=tk.Menu(bar,tearoff=0)
        h.add_command(label='Workbench Help (F1)',command=self.show_help)
        h.add_command(label='About',command=lambda:messagebox.showinfo('ARC-1 Workbench','ARC-1 Workbench R09\nAdaptive RISC-V Console\nClassic Windows File Manager / Word 6-inspired interface\nDevelopment host only'))
        bar.add_cascade(label='Help',menu=h)
        self.configure(menu=bar)

    def _shortcuts(self):
        self.bind_all('<Control-o>',lambda e:self.choose_file())
        self.bind_all('<Control-s>',lambda e:self.save_source())
        self.bind_all('<Control-f>',lambda e:self.find_text())
        self.bind_all('<F1>',lambda e:self.show_help())
        self.bind_all('<F9>',lambda e:self.toggle_diagnostics())
        self.bind_all('<F10>',lambda e:self.toggle_output())
        self.bind_all('<F6>',lambda e:self.open_launcher())
        self.bind_all('<Control-p>',lambda e:self.quick_open())
        self.bind_all('<Control-P>',lambda e:self.command_palette())
        self.bind_all('<Control-Shift-P>',lambda e:self.command_palette())
        self.bind_all('<F5>',lambda e:self.run_action('Build both stages'))
        self.bind_all('<Alt-b>',lambda e:self.run_action('Build both stages'))

    def populate_tree(self):
        self.dir_tree.delete(*self.dir_tree.get_children())
        item=self.dir_tree.insert('', 'end',text='ARC-1  [Project]',values=(str(ROOT),),open=True)
        self.node_paths={item:ROOT}
        for folder in DIRS:
            if (ROOT/folder).is_dir():self._tree_append(item,ROOT/folder)
    def _tree_append(self,parent,path):
        nid=self.dir_tree.insert(parent,'end',text=path.name,open=False)
        self.node_paths[nid]=path
        if self._subdirs(path):self.dir_tree.insert(nid,'end',text='...',tags=('placeholder',))
    def _subdirs(self,path):
        try:return sorted((p for p in path.iterdir() if p.is_dir() and not p.is_symlink() and p.name not in IGNORED and not p.name.startswith('.')),key=lambda x:x.name.lower())
        except OSError:return []
    def on_dir_open(self,event):
        current=self.dir_tree.focus()
        if not current:return
        kids=self.dir_tree.get_children(current)
        if len(kids)==1 and 'placeholder' in self.dir_tree.item(kids[0],'tags'):
            self.dir_tree.delete(kids[0])
            for path in self._subdirs(self.node_paths[current]):self._tree_append(current,path)
    def on_dir_select(self,event):
        current=self.dir_tree.focus()
        if current in self.node_paths:self.show_directory(self.node_paths[current])
    def show_directory(self,path):
        if not path.is_dir():return
        self.selected_dir=path
        rel='\\'.join(path.relative_to(ROOT).parts)
        self.addr.set('C:\\ARC-1\\'+rel+('\\' if rel else ''))
        self.file_tree.delete(*self.file_tree.get_children())
        try:items=sorted((x for x in path.iterdir() if x.name not in IGNORED and not x.name.startswith('.') and not x.is_symlink()),key=lambda p:(p.is_file(),p.name.lower()))
        except OSError:items=[]
        self.file_paths={}
        for p in items[:500]:
            desc='<DIR>' if p.is_dir() else (p.suffix.lower() or 'File')
            sz='' if p.is_dir() else f'{p.stat().st_size:,}'
            iid=self.file_tree.insert('','end',text=('[+]  ' if p.is_dir() else '      ')+p.name,values=(desc,sz))
            self.file_paths[iid]=p
    def on_file_open(self,event):
        selected=self.file_tree.focus()
        path=self.file_paths.get(selected)
        if path is None:return
        if path.is_dir():self.show_directory(path)
        elif path.suffix in EDIT_EXT:self.open_source(path)
        elif path.suffix.lower()=='.arc1cart':
            try:
                v=inspect_cartridge(path)
                messagebox.showinfo('ARC-1 cartridge verified',
                    f"{v['name']}  v{v['game_version']}\nAssets: {v['asset_count']} / {v['asset_bytes']} bytes\n"
                    'Host archive only; contains no ARC-1 executable.')
            except (OSError,CartridgeError) as ex:messagebox.showerror('Cartridge rejected',str(ex))
        else:messagebox.showinfo('ARC-1 Workbench','This file is binary or outside the text editor. Use an appropriate external viewer.')
    def _confirm_edit(self):
        if not self.modified:return True
        ans=messagebox.askyesnocancel('Unsaved file','Save changes before opening another file?')
        if ans is None:return False
        if ans:return self.save_source()
        return True
    def open_source(self,path,confirm=True):
        if confirm and not self._confirm_edit():return False
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file() or path.suffix not in EDIT_EXT:
            return False
        try:
            if path.stat().st_size>1048576:raise ValueError('file over 1MiB editor limit')
            content=path.read_text(encoding='utf-8')
        except (OSError,UnicodeError,ValueError) as ex:
            messagebox.showerror('Open failed',str(ex));return False
        self.open_file=path
        self.editor.delete('1.0','end');self.editor.insert('1.0',content)
        self.editor.edit_modified(False);self.modified=False;self.dirty.configure(text='')
        self.file_path.set(str(path.relative_to(ROOT)).replace('/','\\'))
        self.editor_status()
        return True
    def choose_file(self):
        fn=filedialog.askopenfilename(initialdir=str(self.selected_dir),title='Open ARC-1 source')
        if fn:self.open_source(Path(fn))
    def save_source(self):
        if self.open_file is None:return False
        if not self.open_file.resolve().is_relative_to(ROOT.resolve()):return False
        try:self.open_file.write_text(self.editor.get('1.0','end-1c'),encoding='utf-8')
        except OSError as ex:
            messagebox.showerror('Save failed',str(ex));return False
        self.editor.edit_modified(False);self.modified=False;self.dirty.configure(text='')
        self.write_console(f'\nSAVED {self.open_file.relative_to(ROOT)}\n')
        self.editor_status()
        return True
    def on_modified(self,event):
        if self.editor.edit_modified():
            if self.open_file:self.modified=True;self.dirty.configure(text='* MODIFIED')
            self.editor.edit_modified(False)
    def editor_status(self):
        row,col=self.editor.index('insert').split('.')
        self.edit_status.configure(text=f'Ln {row}, Col {int(col)+1}    |    INS    |    '+('Modified' if self.modified else 'Saved')+'    |    ARC-1 source editor')
    def find_text(self):
        q=simpledialog.askstring('Find','Find what?',parent=self)
        if q:
            pos=self.editor.search(q,'insert','end',nocase=True)
            if not pos:pos=self.editor.search(q,'1.0','end',nocase=True)
            if pos:
                self.editor.tag_remove('sel','1.0','end');self.editor.tag_add('sel',pos,f'{pos}+{len(q)}c')
                self.editor.mark_set('insert',pos);self.editor.see(pos);self.editor.focus_set()
            else:messagebox.showinfo('Find','Text not found.')
    def _set_readonly(self, widget, text):
        widget.configure(state='normal')
        widget.delete('1.0','end')
        widget.insert('1.0',text)
        widget.configure(state='disabled')

    def toggle_output(self, *, manual=True):
        if self.output_visible:
            self.vertical_pane.forget(self.output_box)
            self.output_visible=False
        else:
            self.vertical_pane.add(self.output_box,minsize=70,height=160)
            self.output_visible=True
        if manual:self.output_autorevealed=False

    def reveal_output(self, tab=0):
        if not self.output_visible:
            self.toggle_output(manual=False)
            self.output_autorevealed=True
        self.tabs.select(tab)

    def write_console(self,text):
        self.console.configure(state='normal');self.console.insert('end',text);self.console.see('end');self.console.configure(state='disabled')
    def run_action(self,name):
        if self.busy or name not in ACTION:return
        if self.modified and not self._confirm_edit():return
        self.busy=True
        self.router.start(name)
        argv=[sys.executable,str(ROOT/'arc1'),*ACTION[name]]
        self.reveal_output(1)
        self.write_console(f'\nC:\\ARC-1> arc1 {" ".join(ACTION[name])}\n')
        self.edit_status.configure(text='RUNNING: '+name)
        def worker():
            try:
                p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
                result=(p.returncode,(p.stdout or '')+(p.stderr or ''))
            except (OSError,subprocess.TimeoutExpired) as e: result=(99,str(e))
            self.work_queue.put((name,*result))
        threading.Thread(target=worker,daemon=True).start()
    def poll_output(self):
        try:
            while True:
                name,code,output=self.work_queue.get_nowait()
                self.router.append(output)
                self.router.finish(code)
                self._set_readonly(self.build_log,output.rstrip()+'\n'+('PASS' if code==0 else 'NOT COMPLETED')+f' [exit {code}]')
                self._set_readonly(self.problem_log,self.router.summary())
                self.write_console(output.rstrip()+'\n'+('PASS' if code==0 else 'NOT COMPLETED')+f' [exit {code}]\nC:\\ARC-1> ')
                if code!=0:self.reveal_output(2)
                self.edit_status.configure(text=f'{name}: '+('PASS' if code==0 else 'FAILED / NOT AVAILABLE'))
                self.busy=False
        except queue.Empty:pass
        self.after(80,self.poll_output)
    def advance_boot(self):
        if self.boot_model.fault_code is not None:
            self.write_console('\nBOOT SIM: latched fault; reset simulation before proceeding.\n')
            return
        for event in self.boot_sequence:
            if event not in self.boot_model.history:
                try:self.boot_model.mark(event)
                except ValueError as e:self.write_console(f'\nBOOT SIM DENIED: {e}\n');return
                self._refresh_boot()
                self.write_console(f'\nHOST SIM ONLY: Accepted synthetic evidence for {event.upper()} (not physical).\n')
                return
        self.write_console('\nHOST SIM: all synthetic tests completed. BOARD IS NOT CONNECTED.\n')
    def show_agent_help(self):
        self.tabs.select(1)
        messagebox.showinfo('ARC-1 Agent Interface','A second machine-facing user interface is available:\n\n  py -3 arc1 agent\n\nJSON-Lines over standard input and output; no browser or GUI automation required.\nSee docs/AGENT_INTERFACE_R04.md')
    def show_help(self):
        messagebox.showinfo('ARC-1 Workbench Help','Compact Orange Aqua + Finder-inspired workflow:\n\nFile > Open, Save; Edit > Find, Cut, Copy, Paste.\nDirectory tree (left) and contents pane (top center).\nDouble-click file to edit; drag internal files to folders to COPY.\nDrop .arc1cart files from Explorer onto the file tree if tkinterdnd2 is installed.\nCartridge menu packages, validates and launches the local host demo.\nF6 Launcher  Ctrl+P Quick Open  Ctrl+Shift+P Commands.\nF9 hides diagnostics; F10 toggles the bottom output panel. Build opens it when needed.\n\nCtrl+O Open  Ctrl+S Save  Ctrl+F Find\nF5 / Alt+B Build both stages  F1 Help\n\nFirmware images are non-bootable link-stage artifacts. No flash writes are permitted.')
    def toggle_diagnostics(self):
        if self.diagnostics_visible:
            self.main_pane.forget(self.diagnostic_panel)
            self.diagnostics_visible=False
        else:
            self.main_pane.add(self.diagnostic_panel,minsize=228,width=260,stretch='never')
            self.diagnostics_visible=True

    def cartridge_shelf(self):
        shelf=ROOT/'cartridges'
        shelf.mkdir(exist_ok=True)
        return shelf

    def make_cartridge(self):
        dest=self.cartridge_shelf()/'hello_arc1.arc1cart'
        try:
            result=package_game(ROOT/'examples'/'hello_arc1',dest)
            self.show_directory(self.cartridge_shelf())
            self.write_console(f"\nCARTRIDGE PACKAGED: {result['name']} / {result['asset_count']} assets / "
                              f"{result['asset_bytes']} bytes\nHOST PACKAGE ONLY: No target executable.\n")
            self.edit_status.configure(text='Cartridge packaged (host-only)')
        except (CartridgeError,OSError) as ex:messagebox.showerror('Cartridge package failed',str(ex))

    def import_cartridge(self,path:Path,*,confirm=True):
        path=Path(path).resolve()
        if path.suffix.lower()!='.arc1cart':raise CartridgeError('expected a .arc1cart archive')
        result=inspect_cartridge(path)
        dest=self.cartridge_shelf()/path.name
        if path==dest:return result
        if confirm and not messagebox.askyesno('Copy to ARC-1 cartridge shelf',
               f"Copy verified cartridge {path.name} to the local shelf?\n\n"+str(dest)):
            return None
        if dest.exists() and not messagebox.askyesno('Replace cartridge?',f'{dest.name} exists. Replace it?'):
            return None
        import tempfile
        fd,tmp=tempfile.mkstemp(prefix='.arc1-import-',dir=dest.parent)
        try:
            with os.fdopen(fd,'wb') as f, path.open('rb') as src:shutil.copyfileobj(src,f)
            if inspect_cartridge(Path(tmp))['cartridge_sha256']!=result['cartridge_sha256']:
                raise CartridgeError('copy checksum mismatch')
            os.replace(tmp,dest)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        self.show_directory(self.cartridge_shelf())
        self.write_console(f'\nIMPORTED VERIFIED HOST CARTRIDGE: {dest.name}\n')
        return result

    def import_cartridge_dialog(self):
        path=filedialog.askopenfilename(title='Import .arc1cart',filetypes=[('ARC-1 cartridge','*.arc1cart')])
        if path:
            try:self.import_cartridge(Path(path))
            except (CartridgeError,OSError) as e:messagebox.showerror('Import rejected',str(e))

    def inspect_cartridge_dialog(self):
        path=filedialog.askopenfilename(initialdir=str(self.cartridge_shelf()),filetypes=[('ARC-1 cartridge','*.arc1cart')])
        if path:
            try:
                r=inspect_cartridge(Path(path))
                messagebox.showinfo('Verified host cartridge',f"{r['name']} v{r['game_version']}\n"
                       f"Assets: {r['asset_count']} / {r['asset_bytes']} bytes\n"
                       'HOST ARCHIVE ONLY — game executable not included')
            except (CartridgeError,OSError) as e:messagebox.showerror('Verification failed',str(e))

    def stream_cartridge_dialog(self):
        path=filedialog.askopenfilename(initialdir=str(self.cartridge_shelf()),filetypes=[('ARC-1 cartridge','*.arc1cart')])
        if path:
            try:
                r=simulate_stream(Path(path))
                self.write_console('\nVIRTUAL USB ASSET STREAM — deterministic host model\n'+
                                   json.dumps(r,indent=2)+'\n')
                self.tabs.select(0)
            except (CartridgeError,OSError) as e:messagebox.showerror('Stream test failed',str(e))

    def start_internal_drag(self,event):
        iid=self.file_tree.identify_row(event.y)
        self.internal_drag=(self.file_paths.get(iid),event.x_root,event.y_root) if iid else None

    def finish_internal_drag(self,event):
        drag=self.internal_drag;self.internal_drag=None
        if not drag or drag[0] is None:return
        src,x,y=drag
        if abs(event.x_root-x)+abs(event.y_root-y)<22:return
        target_widget=self.winfo_containing(event.x_root,event.y_root)
        target=None
        if target_widget==self.dir_tree:
            iy=event.y_root-self.dir_tree.winfo_rooty()
            iid=self.dir_tree.identify_row(iy)
            target=self.node_paths.get(iid)
        elif target_widget==self.file_tree:
            iy=event.y_root-self.file_tree.winfo_rooty()
            iid=self.file_tree.identify_row(iy)
            target=self.file_paths.get(iid)
        if target and target.is_dir() and src.is_file():
            # Keep source untouched. Never overwrite silently.
            dest=target/src.name
            if dest==src or dest.exists():return
            if not target.resolve().is_relative_to(ROOT.resolve()):return
            if messagebox.askyesno('Copy file',f'Copy {src.name} to\n{target.relative_to(ROOT)}?'):
                try:shutil.copy2(src,dest);self.show_directory(target)
                except OSError as ex:messagebox.showerror('Copy failed',str(ex))

    def handle_external_drop(self,event):
        if not DND_FILES:return
        try:paths=self.tk.splitlist(event.data)
        except tk.TclError:paths=[]
        for name in paths:
            try:self.import_cartridge(Path(name),confirm=True)
            except (CartridgeError,OSError) as ex:messagebox.showerror('Drop rejected',str(ex))

    def save_workspace(self):
        name=self.workspaces.state['active']
        values={'diagnostics':self.diagnostics_visible,'output_visible':(self.workspaces.state['layouts'][self.workspaces.state['active']]['output_visible'] if self.output_autorevealed else self.output_visible)}
        if hasattr(self,'vertical_pane'):
            try:
                self.update_idletasks()
                values['file_pane_px']=max(80,min(600,self.files_box.winfo_height()))
                values['output_pane_px']=max(80,min(600,self.output_box.winfo_height()))
            except (ValueError,tk.TclError,IndexError,TypeError):pass
        if self.selected_dir.is_relative_to(ROOT) and self.selected_dir!=ROOT:
            folder=self.selected_dir.relative_to(ROOT).parts[0]
            if folder in ('firmware','sdk','examples','cartridges','tests','workbench','docs'):
                values['folder']=folder
        self.workspaces.set_active(name,**values)
        self.workspaces.state['recent_file']=str(self.open_file.relative_to(ROOT)).replace('\\','/') if self.open_file and self.open_file.is_relative_to(ROOT) else None
        self.workspaces.state['editor_index']=self.editor.index('insert')
        self.workspaces.save()

    def restore_workspace(self):
        cfg=self.workspaces.state
        self.apply_workspace(cfg['active'],remember=False)
        name=cfg.get('recent_file')
        if name:
            p=(ROOT/name).resolve()
            if p.is_relative_to(ROOT) and p.is_file():
                self.open_source(p,confirm=False)
                try:self.editor.mark_set('insert',cfg.get('editor_index','1.0'));self.editor.see('insert')
                except tk.TclError:pass

    def apply_workspace(self,name,remember=True):
        if name not in PRESETS:return
        if remember:self.save_workspace()
        layout=self.workspaces.state['layouts'][name]
        show=layout['diagnostics']
        if show!=self.diagnostics_visible:self.toggle_diagnostics()
        folder=ROOT/layout['folder']
        if folder.is_dir():self.show_directory(folder)
        try:
            total=self.vertical_pane.winfo_height()
            files=min(layout['file_pane_px'],max(95,total-300))
            output=min(layout['output_pane_px'],max(90,total-files-180))
            self.vertical_pane.paneconfigure(self.files_box,height=files)
            self.vertical_pane.paneconfigure(self.output_box,height=output)
        except (tk.TclError,AttributeError):pass
        if layout.get('output_visible',True)!=self.output_visible:self.toggle_output(manual=False)
        self.output_autorevealed=False
        self.workspaces.state['active']=name
        if remember:self.workspaces.save()
        self.edit_status.configure(text=f'{name} workspace  |  HOST ONLY  |  Hardware offline')

    def _choice_window(self,title,entries,on_pick):
        """Keyboard-first filterable list shared by quick-open and command palette."""
        win=tk.Toplevel(self);win.title(title);win.geometry('650x470');win.configure(bg=BG)
        win.transient(self)
        term=tk.StringVar();entry=tk.Entry(win,textvariable=term,font=('Segoe UI',12),bg=PANEL,fg=INK,insertbackground=ORANGE,relief='flat')
        entry.pack(fill='x',padx=13,pady=12)
        lb=tk.Listbox(win,font=('Consolas',10),bg=PANEL,fg=INK,selectbackground=ORANGE_SOFT,selectforeground=SELECT,activestyle='none')
        lb.pack(fill='both',expand=True,padx=13,pady=(0,10))
        mapping=[]
        def refresh(*args):
            mapping[:]=[x for x in entries if term.get().lower() in x[0].lower()][:250]
            lb.delete(0,'end')
            for label,_ in mapping:lb.insert('end',label)
            if mapping:lb.selection_set(0);lb.activate(0)
        def choose(event=None):
            if not mapping:return
            sel=lb.curselection();index=sel[0] if sel else 0
            action=mapping[index][1];win.destroy();on_pick(action)
        term.trace_add('write',refresh);refresh()
        entry.bind('<Return>',choose);entry.bind('<Down>',lambda e:(lb.focus_set(),lb.selection_set(0),'break')[-1])
        lb.bind('<Return>',choose);lb.bind('<Double-1>',choose)
        win.bind('<Escape>',lambda e:win.destroy());entry.focus_set()
        return win

    def quick_open(self):
        entries=[]
        for folder in DIRS:
            base=ROOT/folder
            if base.is_dir():
                for path in base.rglob('*'):
                    if len(entries)>3000:break
                    if path.is_file() and path.suffix in EDIT_EXT and path.stat().st_size<=1048576 and not any(x in IGNORED for x in path.parts):
                        entries.append((str(path.relative_to(ROOT)).replace('\\','/'),path))
        self._choice_window('Quick Open — Ctrl+P',sorted(entries),self.open_source)

    def command_palette(self):
        cmds=[('Build: '+k,lambda key=k:self.run_action(key)) for k in ACTION]
        cmds += [('Workspace: '+k,lambda key=k:self.apply_workspace(key)) for k in PRESETS]
        cmds += [('Cartridge: Open launcher',self.open_launcher),('Cartridge: Package sample',self.make_cartridge),
                 ('File: Quick open',self.quick_open),('View: Toggle diagnostics',self.toggle_diagnostics)]
        self._choice_window('Commands — Ctrl+Shift+P',cmds,lambda fn:fn())

    def open_launcher(self):
        if self.launch_window is not None and self.launch_window.winfo_exists():
            self.launch_window.lift();self.launch_window.focus_force();return
        win=tk.Toplevel(self);win.title('ARC-1 Game Shelf — HOST SIMULATION');win.geometry('900x650');win.minsize(680,450)
        win.configure(bg=BG);self.launch_window=win
        banner=tk.Frame(win,bg=NAVY);banner.pack(fill='x')
        tk.Label(banner,text='ARC-1  /  GAME CARTRIDGES',font=('Segoe UI',14,'bold'),fg=ORANGE,bg=NAVY,pady=9).pack(side='left',padx=12)
        tk.Label(banner,text='SIMULATED HOST  •  NOT ON ARC-1 HARDWARE',fg=STEEL,bg=NAVY,font=('Segoe UI',9)).pack(side='right',padx=12)
        body=tk.PanedWindow(win,orient='horizontal',sashwidth=5,bg=LINE);body.pack(fill='both',expand=True,padx=9,pady=8)
        shelf=tk.Frame(body,bg=PANEL);body.add(shelf,width=285,minsize=210)
        tk.Label(shelf,text='GAME SHELF',font=('Segoe UI',11,'bold'),bg=PANEL,fg=INK,pady=8).pack(fill='x')
        listbox=tk.Listbox(shelf,font=('Segoe UI',11),bg=PANEL,fg=INK,activestyle='none',selectbackground=ORANGE_SOFT,selectforeground=SELECT,height=12)
        listbox.pack(fill='both',expand=True,padx=8,pady=8)
        right=tk.Frame(body,bg=PANEL);body.add(right,minsize=350)
        self.launch_summary=tk.StringVar(value='Select a cartridge to inspect.')
        tk.Label(right,textvariable=self.launch_summary,bg=PANEL,fg=SUB,font=('Segoe UI',10),justify='left',anchor='w',wraplength=500).pack(fill='x',padx=12,pady=8)
        display=tk.Frame(right,bg=BLACK,height=365);display.pack(fill='both',expand=True,padx=10,pady=4);display.pack_propagate(False)
        self.launch_picture=tk.Label(display,text='HOST FRAME PREVIEW\n\nSelect a game, then Run.',bg=BLACK,fg=STEEL,font=('Consolas',12),justify='center')
        self.launch_picture.pack(expand=True,fill='both')
        self.launch_message=tk.StringVar(value='Launcher idle · BOARD OFFLINE')
        tk.Label(right,textvariable=self.launch_message,bg=PANEL,fg=ORANGE,font=('Segoe UI',9,'bold')).pack(pady=4)
        controls=tk.Frame(right,bg=PANEL);controls.pack(pady=10)
        items=[]
        def refresh():
            nonlocal items
            items=games_on_shelf(ROOT);listbox.delete(0,'end')
            for item in items:listbox.insert('end',('✓ ' if item['valid'] else '✗ ')+item['name'])
            if items:listbox.selection_set(0);select()
        def selected():
            pick=listbox.curselection()
            return items[pick[0]] if pick and pick[0]<len(items) else None
        def select(event=None):
            item=selected()
            if not item:return
            if not item['valid']:
                self.launch_summary.set(item['error']);return
            try:
                plan=prepare(item['path'],ROOT)
                self.launch_summary.set(f"{plan['name']}  v{plan['game_version']}\n"
                  f"Verified cartridge: {plan['asset_bytes']} asset bytes\n"
                  'Executable: local host SDK build (NOT in cartridge)\nEvidence: HOST_TEST only')
            except LauncherError as e:
                self.launch_summary.set(f'{e.code}: {e}\nBuild the host example before launching.')
        def run():
            item=selected()
            if not item:return
            try:
                report=self.host_launcher.start(item['path'],frames=120)
                self.launch_message.set('Running host-compiled game; waiting for frame output...')
            except LauncherError as e:
                self.launch_message.set(f'{e.code}: {e}')
                messagebox.showerror('Host launch rejected',f'{e.code}\n{e}',parent=win)
        def stop():
            self.host_launcher.stop();self.launch_message.set('Stop requested for host simulator')
        self._button(controls,'Run host game',run,primary=True).pack(side='left',padx=3)
        self._button(controls,'Stop',stop).pack(side='left',padx=3)
        self._button(controls,'Refresh',refresh).pack(side='left',padx=3)
        listbox.bind('<<ListboxSelect>>',select)
        def tick():
            if not win.winfo_exists():return
            s=self.host_launcher.status()
            if s['state'] in ('COMPLETED','FAILED','STOPPED'):
                result=s.get('result',{})
                key=(s['state'],result.get('trace_sha256'),result.get('code'))
                if getattr(win,'_last_report',None)!=key:
                    win._last_report=key
                    self.launch_message.set(f"{s['state']}: {result.get('code','')}  |  HOST ONLY")
                    if s['state']=='COMPLETED':
                        self.launch_preview_files=result.get('preview_frames',[])
                        self.launch_preview_idx=0
                        if self.launch_preview_files:self._animate_host_frames(win)
            win.after(220,tick)
        def closing():
            if self.host_launcher.status()['state']=='RUNNING':stop()
            win.destroy();self.launch_window=None
        win.protocol('WM_DELETE_WINDOW',closing)
        refresh();win.after(220,tick)

    def _animate_host_frames(self,win):
        if not win.winfo_exists() or not self.launch_preview_files:return
        index=self.launch_preview_idx%len(self.launch_preview_files)
        path=(ROOT/self.launch_preview_files[index]).resolve()
        if path.is_file() and path.is_relative_to(ROOT):
            try:
                pic=tk.PhotoImage(file=str(path))
                # Reference simulator is 320 x 180; display pixel-doubled if useful.
                if pic.width()<=400:pic=pic.zoom(2,2)
                self.launch_picture.configure(image=pic,text='');self.launch_picture.image=pic
            except tk.TclError:
                self.launch_picture.configure(text='Frame created; display unavailable')
        self.launch_preview_idx+=1
        if self.launch_preview_idx<len(self.launch_preview_files):win.after(550,lambda:self._animate_host_frames(win))

    def inspect_host_debug(self):
        state=self.host_launcher.status()
        import json as _json
        self.reveal_output(3)
        self._set_readonly(self.debug_log,'HOST GAME SIMULATION\n\n'+_json.dumps(state,indent=2,default=str)+
            '\n\nNo physical ARC-1 debugger is connected.')

    def on_close(self):
        if not self._confirm_edit():return
        try:
            self.save_workspace()
            self.host_launcher.stop()
        finally:self.destroy()

def main():
    Workbench().mainloop()
    return 0

if __name__=='__main__':raise SystemExit(main())
