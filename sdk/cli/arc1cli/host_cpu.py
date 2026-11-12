"""Read-only Linux system CPU activity. No Qt, process enumeration or telemetry.

Activity is aggregate non-idle accounting time across logical CPUs; idle and
iowait are treated as idle. Guest fields are excluded from the sum. It is not
load average, temperature, per-process CPU use or ARC-1 hardware evidence.
See https://docs.kernel.org/filesystems/proc.html and proc_stat(5).
"""
from pathlib import Path
import sys
import time


def parse_proc_stat(line):
    if len(line)>2048:raise ValueError('CPU counter line too long')
    fields=line.split()
    if len(fields)<9 or fields[0]!='cpu':raise ValueError('Missing aggregate CPU counters')
    counters=tuple(int(x) for x in fields[1:9])
    if any(x<0 for x in counters):raise ValueError('Negative CPU counter')
    return counters


def activity_between(before,after):
    if len(before)!=8 or len(after)!=8 or any(type(x) is not int or x<0 for x in before+after):
        raise ValueError('Invalid CPU counters')
    delta=tuple(b-a for a,b in zip(before,after))
    if any(x<0 for x in delta):raise ValueError('CPU accounting reset or decreased')
    total=sum(delta)
    if total<=0:raise ValueError('No CPU accounting interval')
    return 100.0*(total-delta[3]-delta[4])/total


class HostCpuSampler:
    """Nonblocking interval sampling; unavailable is never reported as zero."""
    def __init__(self,reader=None,clock=time.monotonic,interval=1.0):
        self.reader=reader or self._read;self.clock=clock;self.interval=max(1.,float(interval))
        self.previous=None;self.last_read=None;self.percent=None;self.sampled=None
        self.reason='Waiting for two CPU counter samples';self.window=None

    @staticmethod
    def _read():
        if not sys.platform.startswith('linux'):raise OSError('Host CPU sampling is not instrumented on this platform')
        with Path('/proc/stat').open('r',encoding='ascii') as f:return parse_proc_stat(f.readline(2049))

    def snapshot(self):
        now=self.clock()
        if self.last_read is None or now-self.last_read>=self.interval:
            previous_time=self.last_read;self.last_read=now
            try:
                current=self.reader()
                if self.previous is not None:
                    self.percent=round(activity_between(self.previous,current),1)
                    self.sampled=now;self.window=now-previous_time;self.reason=''
                self.previous=current
            except (OSError,ValueError,TypeError) as exc:
                self.previous=None;self.percent=None;self.sampled=None;self.window=None;self.reason=str(exc)
        age=None if self.sampled is None else max(0.,now-self.sampled)
        stale=age is not None and age>self.interval*3
        return {'status':'STALE' if stale else 'MEASURED' if self.percent is not None else 'NOT_INSTRUMENTED',
                'percent':None if stale else self.percent,'age_seconds':None if age is None else round(age,2),
                'interval_seconds':self.window,'source':'Linux /proc/stat aggregate CPU counters',
                'reason':'No fresh CPU sample' if stale else self.reason,'scope':'Host system CPU activity, not ARC-1 or Ledger-only utilization'}
