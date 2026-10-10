"""Symmetric visible controls; fixed R26 actuator axes. Assembly prototypes."""
from pathlib import Path
import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import shutil,zipfile,json
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'input/STRUTHIO_SLIM4_R31_BUILDER_FILES/2_3D_PRINTING/STEP'
OUT=ROOT/'output/R13_SYMMETRIC_CONTROLS'
for d in ['STEP','STL','CAD']: (OUT/d).mkdir(parents=True,exist_ok=True)
def box(x,y,z,c): return cq.Workplane('XY').box(x,y,z).translate(c).val()
upper=box(300,400,40,(0,70,25.65)) # z >=5.65
lower=box(300,400,40,(0,70,-14.35))
panel=box(66.1,120.4,1.85,(1.2,49.6,5.925))
shapes={}; checks={}
for side,fn,flat in [('L','03_FLAP_CAP_L.step',-34.35),('R','04_FLAP_CAP_R.step',36.75)]:
 old=cq.importers.importStep(str(SRC/fn)).val()
 keep=box(200,400,40,(flat+(-100 if side=='L' else 100),70,5))
 hidden_flat = -32.35 if side=='L' else 34.75
 hidden_keep=box(200,400,40,(hidden_flat+(-100 if side=='L' else 100),70,5))
 s=old.intersect(lower).intersect(hidden_keep).fuse(old.intersect(upper).translate((1.2,0,0)).intersect(keep)).clean()
 shapes[side]=s
old=cq.importers.importStep(str(SRC/'05_DART_ROCKER.step')).val()
shapes['DART']=old.intersect(lower).fuse(old.intersect(upper).translate((1.2,0,0))).clean()
for name,s in shapes.items():
 assert s.isValid() and len(s.Solids())==1
 clash=s.intersect(panel).Volume(); assert clash<1e-6
 cq.exporters.export(s,str(OUT/'STEP'/f'R13_SYMMETRIC_{name}.step'))
 dest=OUT/'STL'/f'R13_SYMMETRIC_{name}.stl'
 cq.exporters.export(s,str(dest),tolerance=.01,angularTolerance=.10)
 import struct,collections
 data=dest.read_bytes(); n=struct.unpack_from('<I',data,80)[0]; edges=collections.Counter(); deg=0
 for i in range(n):
  a=struct.unpack_from('<12fH',data,84+50*i); v=[tuple(round(t,5) for t in a[j:j+3]) for j in (3,6,9)]
  deg+=len(set(v))<3
  for j in range(3): edges[tuple(sorted((v[j],v[(j+1)%3])))]+=1
 assert deg==0 and all(n==2 for n in edges.values())
 checks[name]={'valid_single_solid':True,'volume_mm3':s.Volume(),'conditional_panel_overlap_mm3':clash,'triangles':n,'closed_mesh_edges':True}
# Compare only the shifted visible surfaces: lower actuator mechanisms deliberately remain on PCB axes.
a=shapes['L'].intersect(upper).mirror('YZ',(1.2,0,0))
b=shapes['R'].intersect(upper)
err=a.cut(b).Volume()+b.cut(a).Volume(); assert err<1e-5
checks['visible_cap_mirror_difference_mm3']=err
r=shapes['DART'].intersect(upper); rm=r.mirror('YZ',(1.2,0,0))
err=r.cut(rm).Volume()+rm.cut(r).Volume(); assert err<1e-5
checks['visible_rocker_mirror_difference_mm3']=err
checks['visible_panel_edge_gap_mm']={'L':2.5,'R':2.5}
checks['bezel_width_mm']=2.0
checks['panel_clearance_mm']=.2
checks['button_side_clearance_mm']=.3
# Reference rails at front-plate height; must be integrated into the redesigned shell.
for side,x in [('L',-33.05),('R',35.45)]:
 rail=box(2,20,2,(x,102,6.65))
 assert rail.intersect(shapes[side]).Volume()<1e-6
 cq.exporters.export(rail,str(OUT/'STEP'/f'BEZEL_REFERENCE_{side}.step'))
(OUT/'GEOMETRY_CHECKS.json').write_text(json.dumps(checks,indent=2))
fig,ax=plt.subplots(figsize=(9,7))
ax.add_patch(Rectangle((-31.85,84),66.1,25.8,facecolor='#d5efef',edgecolor='#147a79',lw=2))
for x in [-34.05,34.45]:
 ax.add_patch(Rectangle((x,92),2,20,facecolor='#5c6470',edgecolor='none'))
for name,s in shapes.items():
 sec=cq.Workplane('XY',origin=(0,0,8)).add(s).section()
 for e in sec.edges().vals():
  pts=e.sample(100)[0]; ax.plot([p.x for p in pts],[p.y for p in pts],color='#365b8c',lw=2)
for x,y in [(-40.75,102),(40.75,102),(-16,119.296),(16,119.296)]: ax.plot(x,y,'+',color='#cc693b',ms=9)
ax.axvline(1.2,ls='--',color='#555',lw=1)
ax.text(1.2,88,'Fixed screen / visible centerline X = +1.20',ha='center',fontsize=11)
ax.text(-37,113,'2 mm solid bezel',ha='center',fontsize=10)
ax.text(39.4,113,'2 mm solid bezel',ha='center',fontsize=10)
ax.text(1.2,127,'Orange crosses: unchanged switch contact axes',ha='center',fontsize=10,color='#a14f26')
ax.set(xlim=(-54,56.4),ylim=(132,82),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title='R13 — symmetric visible controls\nSolid bezel allowance + 0.2 mm panel / 0.3 mm button clearance')
ax.grid(alpha=.15);fig.tight_layout();fig.savefig(OUT/'SYMMETRY_PREVIEW.png',dpi=180)
(OUT/'README.md').write_text('''# R13 symmetric controls — assembly prototypes

Visible centerline: X=+1.20 mm, matching the fixed panel body center.
Primary button face centers: X=-39.55 and +41.95 mm, Y=102 mm.
Visible screen-facing flats: X=-34.35 and +36.75 mm. Each visible panel-to-button separation is 2.50 mm: 0.20 mm panel clearance + 2.00 mm solid bezel + 0.30 mm button clearance. Lower retaining flanges retain the previous narrower cuts to preserve the stop legs. Bezel reference rails occupy Z=5.65..7.65 mm and are provided as STEP references, not separate parts for printing. Integrate them continuously into the future shell above and below the buttons; final retention and travel remain unverified.
DART visible face center: X=+1.20 mm. Upper material above Z=5.65 is translated +1.20 mm; all lower mechanism geometry retains the original coordinates except cap edge clearance cuts.

The contact nubs, stop legs and DART pivot stay at their original R26/R12 mechanism coordinates. Visible caps and rocker are reflection-symmetric around the screen-body centerline. Hidden lower mechanisms are intentionally not mirrored about that line because switch and pivot locations remain fixed.

Checks: valid single B-rep solids; closed STL edges; no degenerate STL triangles; zero nominal intersection with the conditional panel envelope; upper cap mirror and rocker mirror differences below 0.00001 mm³.

NOT A PRINT-READY CASE RELEASE. Existing R12 shell holes do not accommodate the shifted controls. Matching keyed guides, retention, travel stops and updated shell outline are still required. No moving assembly, tolerance-stack, fatigue or acoustic verification is claimed. Rocker force balance needs checking because the visible face is offset from its pivot. The upper/lower join is a boolean union, without a newly optimized fillet. Panel Z=5.00..6.85 mm remains an assumed old-case datum. Active-area center within the panel is not yet confirmed. Exterior shell and acoustic chambers are NOT changed in this package.

STL units are mm. STEP and editable generator included. Generator expects the source R31 case STEP files under case_update/input.
''')
shutil.copy2(Path(__file__),OUT/'CAD'/Path(__file__).name)
zipout=ROOT/'output/SLIM4_R13_SYMMETRIC_CONTROLS.zip'
with zipfile.ZipFile(zipout,'w',zipfile.ZIP_DEFLATED) as z:
 for p in OUT.rglob('*'):
  if p.is_file(): z.write(p,p.relative_to(OUT))
print(json.dumps(checks,indent=2));print(zipout)
