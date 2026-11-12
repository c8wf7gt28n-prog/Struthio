"""ARC-1 shared host-build output classifier. Never claims actual silicon telemetry."""
from __future__ import annotations
from dataclasses import dataclass
import re

# GCC/Clang: file:line[:col]: severity: text; MSVC: file(line,col): severity Cxxxx: text
_GNU = re.compile(r"^(.+?):(\d+)(?::(\d+))?:\s*(fatal error|error|warning|note):\s*(.*)$", re.I)
_MSVC = re.compile(r"^(.+?)\((\d+)(?:,(\d+))?\):\s*(fatal error|error|warning)\s*([A-Z]+\d+)?:\s*(.*)$", re.I)

@dataclass(frozen=True)
class Problem:
    source: str
    line: int
    column: int
    severity: str
    message: str
    def as_dict(self):
        return dict(source=self.source,line=self.line,column=self.column,severity=self.severity,message=self.message)

def parse_problems(output: str) -> list[Problem]:
    problems=[]
    for line in output.splitlines():
        a=_GNU.match(line.strip())
        if a:
            source,num,col,severity,message=a.groups()
            problems.append(Problem(source,int(num),int(col or 0),severity.lower(),message))
            continue
        b=_MSVC.match(line.strip())
        if b:
            source,num,col,severity,code,message=b.groups()
            problems.append(Problem(source,int(num),int(col or 0),severity.lower(),((code+' ') if code else '')+message))
    return problems

class OutputRouter:
    def __init__(self):
        self.command='';self.raw='';self.exit_code=None;self.problems=[]
    def start(self, command):
        self.command=str(command);self.raw='';self.exit_code=None;self.problems=[]
    def append(self, fragment):
        self.raw+=str(fragment)
        # Bounded output for high-volume compiler logs.
        if len(self.raw)>2_000_000:self.raw=self.raw[-2_000_000:]
    def finish(self, code):
        self.exit_code=int(code)
        self.problems=parse_problems(self.raw)
        return self.summary()
    def summary(self):
        if self.exit_code is None:return 'No completed build yet.'
        errors=sum(p.severity in ('fatal error','error') for p in self.problems)
        warnings=sum(p.severity=='warning' for p in self.problems)
        lines=[f'COMMAND: {self.command}', f'EXIT: {self.exit_code}  |  ERRORS: {errors}  |  WARNINGS: {warnings}']
        if not self.problems:
            lines.append('No recognized compiler errors/warnings.' if self.exit_code==0 else 'Command failed. Read Build Output for details; the exit code is authoritative.')
        for p in self.problems:
            loc=f'{p.source}:{p.line}'+(f':{p.column}' if p.column else '')
            lines.append(f'{p.severity.upper()}  {loc}  {p.message}')
        return '\n'.join(lines)
