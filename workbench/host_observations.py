"""Bounded, source-labelled observations of the current Ledger host."""
from pathlib import Path
import time


def cpu():
    try:
        with open('/proc/stat') as stream:parts=stream.readline().split()
        if parts[0]!='cpu':return None
        values=[int(value) for value in parts[1:9]]
        if len(values)<5 or min(values)<0:return None
        total=sum(values);busy=total-values[3]-values[4]
        return [busy,total]
    except (OSError,ValueError,IndexError):return None


def memory():
    try:
        info={}
        with open('/proc/meminfo') as stream:
            for line in stream:
                key,_,text=line.partition(':')
                if key in ('MemTotal','MemAvailable'):info[key]=int(text.split()[0])*1024
        total=info['MemTotal'];available=info['MemAvailable']
        if not 0<=available<=total or total<=0:return None
        return dict(used=total-available,total=total,percent=round(100*(total-available)/total))
    except (OSError,ValueError,KeyError,IndexError):return None


def gpu():
    samples=[]
    try:paths=sorted(Path('/sys/class/drm').glob('card*/device/gpu_busy_percent'))[:8]
    except OSError:return None
    for path in paths:
        try:
            with path.open() as stream:value=int(stream.read(32).strip())
            if 0<=value<=100:samples.append(value)
        except (OSError,ValueError):pass
    return max(samples) if samples else None


def snapshot():
    return dict(schema='ledger.host-observations/1',sampled_at=time.time(),basis='CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION',
        cpu=dict(counters=cpu(),source='/proc/stat',unit='jiffies',state='TWO_INCREASING_SAMPLES_REQUIRED'),
        ram=dict(sample=memory(),source='/proc/meminfo:MemTotal,MemAvailable',unit='bytes'),
        gpu=dict(percent=gpu(),source='/sys/class/drm/card*/device/gpu_busy_percent',basis='BUSIEST_REPORTED_ADAPTER'),
        txt=dict(percent=None,state='UNAVAILABLE',reason='The runtime does not publish trusted live context occupancy.'))


def cpu_percent(previous,current):
    if previous is None or current is None:return None
    busy=current[0]-previous[0];total=current[1]-previous[1]
    return round(100*busy/total) if total>0 and 0<=busy<=total else None
