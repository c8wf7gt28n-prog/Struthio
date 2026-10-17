"""Host-only ARC-1 boot diagnostics state model; no device I/O."""
from dataclasses import dataclass, field

BITS = {'f133':1,'nor':2,'d213':4,'fpga12':8,'fpga45':16}
PREREQ = {'f133':0, 'nor':1, 'd213':3, 'fpga12':3, 'fpga45':7, 'ready':31}
MESSAGES = {
    'power':('ARC-1  POWER','RAILS CHECK'),
    'f133':('ARC-1  START','F133 BOOT'),
    'nor':('ARC-1  SYSTEM','NOR VERIFY'),
    'd213':('ARC-1  VIDEO','D213 INIT'),
    'fpga12':('ARC-1  FPGA12','CONFIG TEST'),
    'fpga45':('ARC-1  FPGA45','CONFIG TEST'),
    'cartridge':('ARC-1  STORAGE','USB GAME SCAN'),
    'ready':('ARC-1   READY','INSERT GAME'),
    'fault':('ARC-1   FAULT','SEE ERROR CODE'),
}
@dataclass
class BootModel:
    verified: int = 0
    stage: str = 'power'
    fault_code: int | None = None
    history: list[str] = field(default_factory=lambda:['power'])
    def mark(self,stage:str):
        if self.fault_code is not None: raise ValueError('latched fault')
        if stage not in PREREQ: raise ValueError('unknown or unsupported stage')
        if self.verified & PREREQ[stage] != PREREQ[stage]:
            raise ValueError('missing verified prerequisite')
        self.verified |= BITS.get(stage,0)
        self.stage=stage
        self.history.append(stage)
    def fault(self,code:int):
        if self.fault_code is not None:raise ValueError('fault already latched')
        if not isinstance(code,int) or not 1<=code<=65535:raise ValueError('fault code must be 1..65535')
        self.fault_code=code
        self.stage='fault'
        self.history.append('fault')
    def lcd(self):
        a,b=MESSAGES[self.stage]
        if self.fault_code is not None:b=f'FAULT 0x{self.fault_code:04X}'
        return a.ljust(16)[:16],b.ljust(16)[:16]
    def snapshot(self):
        return {'stage':self.stage,'verified_mask':self.verified,'fault_code':self.fault_code,
                'lcd_rows':list(self.lcd()),'history':self.history[:], 'evidence':'HOST_SIM_ONLY',
                'board_connected':False,'physical_boot_proven':False}

def simulate(events):
    if not isinstance(events,list) or len(events)>64: raise ValueError('events must be a list of 0..64 events')
    m=BootModel()
    for evt in events:
        if isinstance(evt,str):m.mark(evt)
        elif isinstance(evt,dict) and set(evt)=={'fault'}:m.fault(evt['fault'])
        else:raise ValueError('invalid simulated event')
    return m.snapshot()
