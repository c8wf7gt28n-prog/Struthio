from fractions import Fraction as F
from datetime import date, timedelta
import calendar
def cents_down(x): import math; return F(math.floor(x*100),100)
def cents_near(x):
    # half up, positive values
    import math; return F(math.floor(x*100+F(1,2)),100)
def show(x): return f"{float(x):.6f} ({x})"
print("Nov 20 2026 weekday", date(2026,11,20).strftime('%A'))
# Budget groceries
rem = F('600') - F('412.37'); print("groceries remaining", rem, "per day", show(rem/10), "per week", show(rem/10*7), cents_down(rem/10), cents_down(rem*7/10))
# Household
fixed = F('1450')+F('512.40')+F('55'); print("fixed", fixed)
lo, hi = F('84.10'), F('142.55')
d_robust = (F(2400)-fixed-hi)/10; d_best=(F(2400)-fixed-lo)/10
print("robust per day", show(d_robust), cents_down(d_robust), "week", show(d_robust*7), cents_down(d_robust*7))
print("best per day", show(d_best), "week", show(d_best*7))
print("break-even E for 28/day", F(2400)-fixed-280, "witness total", fixed+hi+280)
# dates
print("cancel by", date(2027,1,15)-timedelta(days=30))
print("Dec16->Jan15", (date(2027,1,15)-date(2026,12,16)).days)
print("refill last dose day", date(2026,11,1)+timedelta(days=44), "order by", date(2026,11,1)+timedelta(days=44)-timedelta(days=3))
# subscriptions
print("year at 15.49", F('15.49')*12, "rise pct", show((F('15.49')-F('13.99'))/F('13.99')*100))
print("Oct14->Nov14", (date(2026,11,14)-date(2026,10,14)).days)
# statement reconcile
print("1204.56-216.43", F('1204.56')-F('216.43'), "swap", F('1204.56')+F('216.43'))
# month end
for y in (2027,2028): print(y, "Jan31+1mo clip", date(y,2,calendar.monthrange(y,2)[1]))
# loans
def payment(P, apr, n):
    r = F(apr)/1200
    return P*r/(1-(1+r)**-n), r
def schedule(P, apr, n, rounding='near'):
    exact, r = payment(P, apr, n)
    pay = cents_near(exact)
    bal = P; total_int = F(0); rows=[]
    for m in range(1, n+1):
        i = cents_near(bal*r)
        if m == n: p = bal + i
        else: p = pay
        bal = bal + i - p; total_int += i; rows.append((m, p, i, bal))
    return exact, pay, total_int, rows
P = F(18000)
eA, pA, iA, rA = schedule(P, '6.9', 60)
eB, pB, iB, rB = schedule(P, '5.9', 60)
print("A payment exact", show(eA), "rounded", pA, "interest", iA, "last", rA[-1][1])
print("B payment exact", show(eB), "rounded", pB, "interest", iB, "last", rB[-1][1])
fee = F(450)
print("B interest+fee", iB+fee, "A minus (B+fee)", iA-(iB+fee))
# break-even if paid off at month m: cost = interest paid through m (+fee for B)
for m in range(1,61):
    cA = sum(r[2] for r in rA[:m]); cB = sum(r[2] for r in rB[:m]) + fee
    if cB < cA:
        print("B cheaper from payoff after month", m, "cA", cA, "cB", cB); break
m=24; print("at 24: A", sum(r[2] for r in rA[:m]), "B", sum(r[2] for r in rB[:m])+fee)
# truncation variant (interest rounded down)
def schedule_down(P, apr, n):
    exact, r = payment(P, apr, n); pay=cents_near(exact); bal=P; ti=F(0)
    for m in range(1,n+1):
        i = cents_down(bal*r); p = pay if m<n else bal+i; bal=bal+i-p; ti+=i
    return ti
print("A interest if rounded down monthly", schedule_down(P,'6.9',60), "B", schedule_down(P,'5.9',60))
# medicine window
# weight check: leaflet 5 mg/kg/day; prescribed 400 mg/day; weight 82 +-1.5
for w in (F(82), F(79)):
    print("weight", w, "range mg", (w-F('1.5'))*5, (w+F('1.5'))*5, "break-even kg", F(400)/5)
