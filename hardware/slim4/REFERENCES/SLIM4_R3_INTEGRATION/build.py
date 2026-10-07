"""R3 whole-device integration study. Not an electrical layout or fabrication release."""
from pathlib import Path
import json,csv
import numpy as np
import cadquery as cq
from shapely.geometry import Polygon as SP, box as SB
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,Circle
out=Path(__file__).resolve().parent
# Approved R2 XY outline: retain the same cubic control points and sampling.
B=4.;AW=58.104;AH=103.296;H=135.296;W=104.;stem=66.104;a=stem/2;r=6
pts=[]
def line(p):pts.append(tuple(p))
def bez(p0,p1,p2,p3,n=14):
 for t in np.linspace(0,1,n)[1:]:line((1-t)**3*np.array(p0)+3*(1-t)**2*t*np.array(p1)+3*(1-t)*t*t*np.array(p2)+t**3*np.array(p3))
line((0,0));line((a-r,0));bez((a-r,0),(a-2,0),(a,2),(a,r));line((a,70));bez((a,70),(a,83),(W/2,81),(W/2,103));bez((W/2,103),(W/2,124),(51,H),(44,H));bez((44,H),(36,H),(33,H-4),(24,H-4));line((0,H-4));right=pts.copy();pts += [(-x,y) for x,y in right[-2:0:-1]]
outline=SP(pts);inner=outline.buffer(-1.6,join_style=1);boardarea=outline.buffer(-2.4,join_style=1).intersection(SB(-60,3,60,117.4).union(SB(-26,117.4,26,128)))
boardarea=boardarea.difference(SB(-18,18,18,72).buffer(1))
def prism(poly,z,h):
 wp=cq.Workplane('XY').polyline(list(poly.exterior.coords)[:-1]).close()
 for ring in poly.interiors:wp=wp.polyline(list(ring.coords)[:-1]).close()
 return wp.extrude(h).translate((0,0,z))
def box(w,l,h,x,y,z):return cq.Workplane('XY').box(w,l,h,centered=(True,True,False)).translate((x,y,z))
board=prism(boardarea,5.5,1);lcd=box(60.3,111.4,1.75,0,57.91,1.2);battery=box(34,52,3.5,0,45,4)
cores=[];lids=[];air=[];speakers=[];guides=[];caps=[];switches=[]
# Rebuild air spaces against inset enclosure profile: clipping the old solid alone would open leaks.
outermask=prism(outline,0,20);innermask=prism(inner,0,20)
for s in [-1,1]:
 x=s*40;local=box(24,36,10.5,x,108,6.5).intersect(outermask)
 fa=box(20.8,32.8,2,x,108,8).intersect(innermask)
 ra=box(20.8,32.8,2.9,x,108,12.5).intersect(innermask)
 seat=box(13.6,18.6,2.5,x,108,10)
 core=local.cut(fa).cut(ra).cut(seat)
 riser=box(20,8,6.5,x,122,0).intersect(outermask)
 vent=box(16,4,10,x,122,0).intersect(innermask)
 core=core.union(riser).cut(vent)
 lid=core.intersect(box(130,160,1.6,0,70,15.4));core=core.cut(box(130,160,5,0,70,15.4))
 cores.append(core);lids.append(lid);air.append(ra)
 speakers.append(box(13,18,2.5,x,108,10))
 # Shift cap and direct-actuation switch together 0.75 outward for LCD/guide clearance.
 bx=s*40.75
 guides.append(cq.Workplane('XY').center(bx,102).circle(9.8).circle(8.2).extrude(2.2))
 caps.append(cq.Workplane('XY').center(bx,102).circle(8).extrude(1.5).translate((0,0,-1.5)))
 switches.append(box(8.6,4.8,3,bx,102,2.5))
for s in [-1,1]:switches.append(box(8.6,4.8,3,s*16,119.296,2.5))
# Explicit circuit-region reserves, NOT exact package placement / passives.
rows=[('P4_CLUSTER','ESP32-P4NRW32X + local passives',0,84,16,16,6.5,2.2,'rear'),('FLASH','flexible capacity NOR',17,83,10,10,6.5,1.2,'rear'),('XTAL','40MHz crystal + matching',-15,84,6,6,6.5,1.3,'rear'),('CORE_DCDC','revision-specific P4 core supply',0,101,10,8,6.5,2.2,'rear'),('SYS_POWER','buck-boost + LCD supplies',-17,103,16,14,6.5,2.6,'rear'),('LCD_FPC','connector + latch access TBD',17,109,18,6,6.5,2,'rear'),('BACKLIGHT','boost + support',17,97,10,8,6.5,2.5,'rear'),('AMP_L','MAX98360C + bypass',-22,117,8,8,6.5,1.5,'rear'),('AMP_R','MAX98360C + bypass',22,117,8,8,6.5,1.5,'rear'),('USB_C','socket/protection reserve',0,7,12,10,6.5,3.3,'rear'),('CHARGER','power path + charge support',17,8,14,10,6.5,2,'rear'),('BAT_CONN','keyed battery plug reserve',-24,64,7,8,6.5,3,'rear')]
regions=[box(w,l,h,x,y,z) for _,_,x,y,w,l,z,h,_ in rows]
with open(out/'placement_regions.csv','w') as f:
 wr=csv.writer(f);wr.writerow(['region','function','center_x_mm','center_y_mm','width_mm','length_mm','z_min_mm','height_mm','board_side']);wr.writerows(rows)
ass=cq.Assembly(name='SLIM4_R3_INTEGRATION_STUDY')
objects=[(board,'single_motherboard',(.12,.5,.3)),(lcd,'LCD_envelope_flex_missing',(.12,.15,.2)),(battery,'battery_candidate',(.7,.7,.7))]
for i,group in enumerate([cores,lids,speakers,guides,caps,switches]):
 for j,obj in enumerate(group):objects.append((obj,f'{["core","lid","speaker","guide","cap","switch"][i]}_{j}',[(.3,.45,.6),(.2,.3,.4),(.6,.3,.8),(.5,.5,.5),(1,.55,.1),(.45,.45,.45)][i]))
for row,obj in zip(rows,regions):objects.append((obj,row[0]+'_RESERVE',(.75,.7,.3)))
for obj,name,color in objects:ass.add(obj,name=name,color=cq.Color(*color))
ass.export(str(out/'SLIM4_R3_integration.step'));cq.exporters.export(board,str(out/'PCB_MECHANICAL_RESERVE.step'))
# DXF, board edge and battery cutout only.
wp=cq.Workplane('XY').polyline(list(boardarea.exterior.coords)[:-1]).close()
for ring in boardarea.interiors:wp=wp.polyline(list(ring.coords)[:-1]).close()
cq.exporters.export(wp,str(out/'PCB_MECHANICAL_RESERVE.dxf'))
# Collision report, excluding deliberately touching support surfaces and overlapping diagnostic region names.
pairs=[]
for i,(obj,name,_) in enumerate(objects):
 for other,oname,_ in objects[i+1:]:
  v=obj.intersect(other).val().Volume()
  if v>1e-5:pairs.append({'a':name,'b':oname,'intersection_mm3':round(v,5)})
unsupported=[]
for row,obj in zip(rows,regions):
 _,_,x,y,w,l,z,h,_=row
 if not boardarea.covers(SB(x-w/2,y-l/2,x+w/2,y+l/2)):unsupported.append(row[0])
checks={'outline_width_mm':W,'outline_height_mm':H,'button_diameter_mm':16,'button_centers_x_mm':[-40.75,40.75],'button_move_outward_mm':.75,'guide_inner_diameter_mm':16.4,'guide_outer_diameter_mm':19.6,'guide_wall_mm':1.6,'nominal_guide_to_lcd_x_gap_mm':40.75-9.8-30.15,'pcb_thickness_mm':1,'pcb_solid_count':len(board.solids().vals()),'pcb_area_mm2':boardarea.area,'rear_air_cc':[a.val().Volume()/1000 for a in air],'all_solids_valid':all(obj.val().isValid() for obj,_,_ in objects),'solid_intersections':pairs,'regions_outside_board':unsupported,'limits':'Envelope intersections only; region reserves are not footprints. Rear grip surface blending, tolerances, gaskets, wire exit, cap motion and full electrical layout unresolved.'}
(out/'checks.json').write_text(json.dumps(checks,indent=2))
fig,axs=plt.subplots(1,2,figsize=(14,11),facecolor='#f5f8fb');fig.subplots_adjust(left=.05,right=.97,top=.85,bottom=.15,wspace=.1)
for ax in axs:
 ax.set_aspect('equal');ax.set_xlim(-58,58);ax.set_ylim(140,-3);ax.axis('off');ax.add_patch(Polygon(pts,fc='#dde5ed',ec='#1b3b54',lw=1.5));ax.add_patch(Polygon(list(boardarea.exterior.coords),fc='#b2d5c0',ec='#37815b',lw=1))
 for ring in boardarea.interiors:ax.add_patch(Polygon(list(ring.coords),fc='#f5f8fb',ec='#37815b'))
 ax.add_patch(Rectangle((-17,19),34,52,fc='#c7cdd5',ec='#7e8b99'));ax.text(0,45,'BATTERY\nwindow',ha='center',va='center',fontsize=11,color='#394b60')
axs[0].set_title('PCB / CIRCUIT SPACE RESERVATIONS',fontsize=12,pad=15)
for row in rows:
 name,_,x,y,w,l,z,h,_=row;axs[0].add_patch(Rectangle((x-w/2,y-l/2),w,l,fc='#f1d58b',ec='#ad8432',lw=.7));axs[0].text(x,y,name.replace('_','\n'),ha='center',va='center',fontsize=6.5)
for s in [-1,1]:
 axs[0].add_patch(Rectangle((s*40.75-4.3,99.6),8.6,4.8,fc='#ed9635'));axs[0].text(s*40.75,97,'FLAP',ha='center',fontsize=8)
 axs[0].add_patch(Rectangle((s*16-4.3,116.896),8.6,4.8,fc='#ed9635'));axs[0].text(s*16,125,'DART',ha='center',fontsize=8)
axs[1].set_title('MECHANICAL OVERLAP / DEPTH SEPARATED',fontsize=12,pad=15)
axs[1].add_patch(Rectangle((-30.15,2.21),60.3,111.4,fill=False,ec='#415a72',ls='--'))
for s in [-1,1]:
 poly=outline.intersection(SB(s*40-12,90,s*40+12,126));axs[1].add_patch(Polygon(list(poly.exterior.coords),fc='#aacfe8',ec='#416d8c',alpha=.8))
 axs[1].add_patch(Rectangle((s*40-6.5,99),13,18,fc='#b899e0',ec='#7554a0'))
 axs[1].add_patch(Circle((s*40.75,102),9.8,fill=False,ec='#c37713',lw=1.5));axs[1].add_patch(Circle((s*40.75,102),8,fc='#ffc165',alpha=.55,ec='#c37713'))
 axs[1].text(s*40,130,'SHARED\nHANDLE',ha='center',fontsize=8,color='#415a72')
axs[1].text(0,83,'Dashed: LCD module\nOrange: cap / guide\nPurple: speaker behind PCB',ha='center',fontsize=9,color='#334e68',linespacing=1.5)
fig.text(.055,.945,'STRUTHIO / R3 HARDWARE INTEGRATION',fontsize=24,weight='bold',color='#193a54')
fig.text(.055,.90,'Approved 104 mm outline • 16 mm caps • one connected motherboard • shaped audio cores',fontsize=13,color='#486177')
fig.text(.055,.105,'GUIDE CLEARANCE FIX: both cap / switch centers move 0.75 mm outward; enclosure width stays unchanged.',fontsize=11,weight='bold',color='#193a54')
fig.text(.055,.068,'Planning geometry only. Circuit regions include estimated support space, not validated footprints or routed nets.',fontsize=11,color='#486177')
fig.text(.055,.038,'Core rear depth remains a 17 mm local envelope. The final curved rear surface, seals and moving mechanisms still require detailing.',fontsize=10,color='#486177')
fig.savefig(out.parent/'STRUTHIO_SLIM4_R3_Integration.png',dpi=170)
print(json.dumps(checks))
