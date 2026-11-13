# R23 edit 15, part B: J1's fan-out, hand-routed on F.Cu and locked.
#  The battery window gets 2.5 mm shorter (bottom edge Y 73 -> 70.5; it stays 38 x 53.5 mm, room for a 34 x 50 mm
#  503450 / 703450 cell). The new board strip above J1 carries nine rows, one per net, that drop straight into the
#  pads from above: the westmost pad has the northmost row. East of J1 the rows turn south into a column right of
#  U2 (x 16.4-18.8), which jogs 1.11 mm east below the strip so the two backlight lines can join it from J1's east
#  end, where they come in under the pad row (LED+ keeps 0.2 mm from everything: the open-LED limit is 38 V).
#  Below Y 82 the nine lines east of the backlight pair spread to a 0.45 mm pitch, so each can leave the column end.
#  The column ends at Y 90; part C routes from there to the sources. USB_CURR_OUT2, cut under J1's west end in
#  part A, is rejoined around pad 1.
exec(open(sys.argv[2]).read())
X0=1.9; X=lambda pin: X0-9.75+0.5*(pin-1)
# 1. battery window: move its bottom edge and corners up 2.5 mm
E=b.GetLayerID('Edge.Cuts'); moved=0
for d in b.GetDrawings():
    if d.GetLayer()!=E: continue
    ends=(d.GetStart(),d.GetEnd())
    if all(-19.01<=mm(p.x)<=19.01 and 16.9<=mm(p.y)<=73.01 for p in ends):
        for get,put in ((d.GetStart,d.SetStart),(d.GetEnd,d.SetEnd)):
            p=get()
            if mm(p.y)>=71.99: put(pcbnew.VECTOR2I(p.x,p.y-MM(2.5))); moved+=1
assert moved==68, moved   # 2 x 16 corner segments, the bottom edge and the two sides
# 2. PWR_WAKE and CHG_STATUS: drop the corner pieces south of their north runs (part C reconnects them)
for t in TR:
    if t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['F.Cu'] and t.GetNetname() in ('PWR_WAKE','CHG_STATUS') \
       and min(mm(t.GetStart().y),mm(t.GetEnd().y))>=72.45 and 15<mm(t.GetStart().x)<20: KILL.append(t)
# 3. the nine rows, their drops into the pads and the column
D=0.3                                                   # 45-degree corner size
ROWS=[('LCD_VCI_3V0',(10,11),70.80,18.79,0.152),('LCD_RESX',(14,),71.10,18.49,0.152),('LCD_1V8',(19,20),71.40,18.19,0.152),
      ('MIPI_DSI_CLK_P',(28,),71.75,17.84,0.152),('MIPI_DSI_CLK_N',(29,),72.01,17.58,0.152),
      ('MIPI_DSI_D1_P',(31,),72.36,17.23,0.152),('MIPI_DSI_D1_N',(32,),72.62,16.97,0.152),
      ('MIPI_DSI_D0_P',(34,),72.97,16.62,0.152),('MIPI_DSI_D0_N',(35,),73.23,16.36,0.152)]   # pairs at 0.26, groups at 0.30-0.35
JOG=1.11; YJ0=73.60; YEND=90.0; INTO=73.8
SPREAD={'LCD_VCI_3V0':(21.25,82.00),'LCD_RESX':(20.80,82.35),'LCD_1V8':(20.35,82.70),'MIPI_DSI_CLK_P':(19.90,83.05),
        'MIPI_DSI_CLK_N':(19.45,83.40),'MIPI_DSI_D1_P':(19.00,83.75),'MIPI_DSI_D1_N':(18.55,84.10),'MIPI_DSI_D0_P':(18.10,84.45),
        'MIPI_DSI_D0_N':(17.65,84.80)}
for n,pins,yr,xc,w in ROWS:
    N=net(n); xw=min(X(p) for p in pins)
    yj=YJ0-0.41421*(xc-16.36)                           # staggered so the 45-degree jogs stay 'pitch' apart
    xf,yh=SPREAD[n]                                      # widen to 0.45 mm pitch above Y 90, east line first
    add("F.Cu",[(xw,INTO),(xw,yr),(xc-D,yr),(xc,yr+D),(xc,yj),(xc+JOG,yj+JOG),(xc+JOG,yh),(xf,yh),(xf,YEND)],N,w)
    for p in pins:
        if X(p)!=xw: add("F.Cu",[(X(p),yr),(X(p),INTO)],N,w)
# 4. backlight: in under the pad row from the east, then into the column's west side
LK=net('LCD_LED_K'); LA=net('LCD_LED_A'); XK,XA=17.21,16.85; YK,YA=75.55,75.95
add("F.Cu",[(X(39),YK),(XK-D,YK),(XK,YK+D),(XK,YEND)],LK)
for p in (39,40): add("F.Cu",[(X(p),YK),(X(p),74.5)],LK)
add("F.Cu",[(X(38),74.5),(X(38),YA),(XA-D,YA),(XA,YA+D),(XA,YEND)],LA)
# 5. USB_CURR_OUT2: around J1's pad 1 (above the mounting tab)
add("F.Cu",[(-0.3,81.9),(-6.9,75.3),(-8.4,75.3),(-8.9,74.8),(-8.9,73.3)],net('USB_CURR_OUT2'),0.1)
for t in b.GetTracks():
    if not _dead(t): t.SetLocked(True)
