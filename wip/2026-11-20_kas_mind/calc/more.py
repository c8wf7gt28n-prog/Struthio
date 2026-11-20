from fractions import Fraction as F
from datetime import date, timedelta
import math
def cents_near(x): return F(math.floor(x*100+F(1,2)),100)
def cents_down(x): return F(math.floor(x*100),100)
def sched(P, apr, n, rnd):
    r=F(apr)/1200; exact=P*r/(1-(1+r)**-n); pay=cents_near(exact); bal=P; out=[]
    for m in range(1,n+1):
        i=rnd(bal*r); p=pay if m<n else bal+i; bal=bal+i-p; out.append(i)
    return out
P=F(18000)
for name,rnd in (('near',cents_near),('down',cents_down)):
    a=sched(P,'6.9',60,rnd); b=sched(P,'5.9',60,rnd)
    tot=(sum(a), sum(b)+450, sum(a)-sum(b)-450)
    be=next(m for m in range(1,61) if sum(b[:m])+450 < sum(a[:m]))
    print(name, [str(float(t)) for t in tot], "B cheaper if kept past month", be-1, "i.e. from month", be)
for d in (date(2026,12,16),date(2026,12,15),date(2026,12,12),date(2027,1,15),date(2026,12,3),date(2026,11,24),date(2027,3,2),date(2027,1,30), date(2026,12,4)):
    print(d, d.strftime('%A'))
# business days
start=date(2026,11,20); d=start; n=0
while n<10:
    d+=timedelta(days=1)
    if d.weekday()<5: n+=1
print("10 working days after Nov 20, no holidays:", d)
# 24h window doses: list (datetime hour, tablets)
from datetime import datetime as DT
log=[(DT(2026,11,17,7,0),2),(DT(2026,11,17,11,30),2),(DT(2026,11,17,16,0),2),(DT(2026,11,17,21,0),2),(DT(2026,11,18,6,30),2)]
best=0;
for t0,_ in log:
    s=sum(k for t,k in log if t0<=t<t0+timedelta(hours=24)); best=max(best,(s,t0))if isinstance(best,tuple) else (s,t0)
print("max in any 24h window", best)
gaps=[(log[i+1][0]-log[i][0]) for i in range(len(log)-1)]; print("gaps", [str(g) for g in gaps])
# subscription yearly cost total of monthly subs example
subs=[F('15.49'),F('2.99'),F('11.00'),F('9.99')]
print("subs monthly", sum(subs), "year", sum(subs)*12)
