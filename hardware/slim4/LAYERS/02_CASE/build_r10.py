"""SLIM4 R10 exterior-shape candidate; R21 PCB reference remains unchanged."""
from pathlib import Path
import json, math
import cadquery as cq

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
MODEL = json.loads((ROOT / 'LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json').read_text())

# Smooth right-half silhouette, mirrored about the vertical centerline.
def cubic(p0, p1, p2, p3, n=24):
    pts=[]
    for i in range(1,n+1):
        t=i/n; u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

right=[(0,0),(27,0)]
right += cubic((27,0),(31,0),(33,2),(33,7))
right += [(33,70)]
right += cubic((33,70),(33,72.5),(32.8,74),(32.8,76))
right += cubic((32.8,76),(32.8,83),(52,85),(52,96),n=32)
# Side contour: a shallow finger scallop followed by a fuller palm heel.
right += cubic((52,96),(52,104),(51.5,108),(51.5,112),n=16)
right += cubic((51.5,112),(51.5,117),(49.8,119.0),(49.8,123),n=20)
right += cubic((49.8,123),(49.8,127),(51.5,128.5),(52,132),n=18)
right += cubic((52,132),(51.5,134.3),(47,135.3),(41,135.3),n=16)
# Shallow lower saddle blends tangentially through the centerline.
right += cubic((41,135.3),(30,135.3),(12,130.8),(0,130.8),n=28)
# Right half from crown to bottom, mirrored back to the crown.
outline=right + [(-x,y) for x,y in reversed(right[1:-1])]
outline=list(dict.fromkeys((round(x,5),round(y,5)) for x,y in outline))

def poly(points, z, depth):
    return cq.Workplane('XY').polyline(points).close().extrude(depth).translate((0,0,z))

# Two-millimeter structural front shell. Openings keep at least 2 mm of plastic
# around the active screen, 16 mm arcade caps, DART control and vent slots.
shell=poly(outline,5.65,2.0)
# Three-level screen seat: visible aperture, lens rebate, and rear LCD pocket.
screen_cut=(cq.Workplane('XY').box(58.8,104.0,4,centered=(True,True,False)).edges('|Z').fillet(2.5).translate((0,55.7,5)))
shell=shell.cut(screen_cut)
lens_rebate=(cq.Workplane('XY').box(59.4,104.6,.7,centered=(True,True,False)).edges('|Z').fillet(2.6).translate((0,55.7,6.95)))
shell=shell.cut(lens_rebate)
lcd_pocket=(cq.Workplane('XY').box(60.5,111.6,1.3,centered=(True,True,False)).translate((0,55.7,5.65)))
shell=shell.cut(lcd_pocket)
for x in (-40.75,40.75):
    hole=cq.Workplane('XY').center(x,102).circle(8.5).extrude(4).translate((0,0,5))
    shell=shell.cut(hole)
pillhole=(cq.Workplane('XY').box(50,8,4,centered=(True,True,False))
         .edges('|Z').fillet(3.9).translate((0,118,5)))
shell=shell.cut(pillhole)
for x in (-41.5,41.5):
    for y in (120.7,122.6,124.5):
        slot=cq.Workplane('XY').box(12,0.8,4,centered=(True,True,False)).edges('|Z').fillet(.39).translate((x,y,5))
        shell=shell.cut(slot)

# Molded surface sculpture sits above an uninterrupted 2.0 mm shell.
sculpture=[]
# Raised annular collars make the two arcade controls read as engineered
# bezels while leaving the 17 mm shell apertures and the 16 mm cap size intact.
for x,label in ((-40.75,'L'),(40.75,'R')):
    outer=cq.Workplane('XY').center(x,102).circle(9.0).extrude(.5).translate((0,0,7.85))
    inner=cq.Workplane('XY').center(x,102).circle(8.5).extrude(.52).translate((0,0,7.84))
    sculpture.append((outer.cut(inner),f'MOLDED_{label}_ARCADE_BUTTON_BEZEL'))
# Raised stepped DART surround; inner edge aligns with the existing pill opening.
pill_outer=(cq.Workplane('XY').box(52,10,.5,centered=(True,True,False))
            .edges('|Z').fillet(4.8).translate((0,118,7.85)))
pill_inner=(cq.Workplane('XY').box(50,8,.52,centered=(True,True,False))
            .edges('|Z').fillet(3.9).translate((0,118,7.84)))
sculpture.append((pill_outer.cut(pill_inner),'MOLDED_STEPPED_DART_PILL_SURROUND'))

boardface=cq.Workplane('XY').polyline(MODEL['board']['outer']).close()
for hole in MODEL['board'].get('holes',[]): boardface=boardface.polyline(hole).close()
board=boardface.extrude(1.6)
# Panel is shifted up in its flex-cable placement so the screen and lower control
# zone match the approved exterior; no PCB footprint, net, or coordinate changes.
lcd=cq.Workplane('XY').box(60.3,111.4,1.75,centered=(True,True,False)).translate((0,55.7,5.2))
lens=(cq.Workplane('XY').box(59.2,104.4,.7,centered=(True,True,False)).edges('|Z').fillet(2.5).translate((0,55.7,6.95)))
# 0.20 mm full-face acrylic graphic laminate; transparent across the screen.
face_sticker=poly(outline,7.65,.20)
for x in (-40.75,40.75):
    face_sticker=face_sticker.cut(cq.Workplane('XY').center(x,102).circle(8.5).extrude(.3).translate((0,0,7.64)))
sticker_pill=(cq.Workplane('XY').box(50,8,.3,centered=(True,True,False)).edges('|Z').fillet(3.9).translate((0,118,7.64)))
face_sticker=face_sticker.cut(sticker_pill)
for x in (-41.5,41.5):
    for y in (120.7,122.6,124.5):
        cut=(cq.Workplane('XY').box(12.2,1.0,.3,centered=(True,True,False)).edges('|Z').fillet(.49).translate((x,y,7.64)))
        face_sticker=face_sticker.cut(cut)
controls=[]
for x in (-40.75,40.75):
    controls.append((cq.Workplane('XY').center(x,102).circle(8).extrude(1.5).translate((0,0,7.85)),f'16mm ARCADE CAP {"L" if x<0 else "R"}'))
pill=(cq.Workplane('XY').box(49,7.5,1.5,centered=(True,True,False)).edges('|Z').fillet(3.6).translate((0,118,7.85)))
controls.append((pill,'CENTER DART PILL CAP — CONTACTS FIXED R21 DART SWITCHES'))
switches=[]
for x in (-16,16):
    switches.append(cq.Workplane('XY').box(8.6,4.8,3,centered=(True,True,False)).translate((x,119.296,1.6)))

assembly=cq.Assembly(name='STRUTHIO_SLIM4_R10_EXTERIOR_CASE_CANDIDATE')
assembly.add(shell,name='R10_2MM_MIN_FRONT_SHELL',color=cq.Color(.08,.20,.32))
for part,name in sculpture: assembly.add(part,name=name,color=cq.Color(.10,.24,.37))
assembly.add(board,name='FIXED_R21_PCB_DATUM',color=cq.Color(.12,.52,.29))
assembly.add(lcd,name='HOTHMI_MODULE_SHIFTED_ON_FPC_FOR_EXTERIOR',color=cq.Color(.22,.63,.70))
assembly.add(lens,name='PROTECTIVE_LENS_58P6x103P8x0P7',color=cq.Color(.40,.75,.86))
assembly.add(face_sticker,name='ACRYLIC_FACE_LAMINATE_0P20_CLEAR_SCREEN_ZONE',color=cq.Color(.10,.23,.34))
for part,name in controls: assembly.add(part,name=name,color=cq.Color(.96,.48,.08))
for i,part in enumerate(switches): assembly.add(part,name=f'FIXED_R21_DART_SWITCH_{i+1}',color=cq.Color(.82,.34,.10))
context_path=ROOT/'REFERENCES'/'R10_CONTEXT'/'STRUTHIO_R10_UNSEPARATED_CONTEXT_REFERENCE.step'
context_path.parent.mkdir(parents=True,exist_ok=True)
assembly.save(str(context_path))

checks={
 'revision':'R10','status':'EXTERIOR-SHAPE CANDIDATE — FIT AND FPC ROUTE NOT RELEASED',
 'exterior_outline_mm':[104.0,135.3], 'r21_pcb_changed':False,
 'minimum_front_shell_thickness_mm':2.0,
 'ergonomic_outline':{'finger_scallop_max_inset_mm':2.2,'full_palm_heel_width_mm':104.0,'center_saddle_lift_mm':4.5,'controls_pcb_and_screen_coordinates_changed':False},
 'molded_surface_relief_mm':0.5,
 'screen_stack':{'opening_mm':[58.8,104.0],'lens_rebate_mm':[59.4,104.6,0.7],'rear_LCD_clearance_pocket_mm':[60.5,111.6,1.3],'protective_lens_mm':[59.2,104.4,0.7],'lens_corner_radius_mm':2.5,'lcd_active_area_mm':[58.104,103.296],'acrylic_face_laminate_thickness_mm_assumed':0.20,'face_laminate_window':'clear and continuous across the display/lens'},
 'screen_bezel_nominal_mm':{'side_each':3.4,'top':3.5,'bottom_to_DART_surround':5.1},
 'sculpted_features':['raised 0.5 mm arcade bezels','raised stepped DART surround','stepped lens seat, rear LCD pocket and acrylic-laminate screen stack'],
 'lcd_module_mm':[60.3,111.4,1.75], 'lcd_center_y_mm':55.7,
 'lcd_shift_from_R4_fit_datum_mm':-14.8,
 'lcd_active_area_mm':[58.104,103.296],
 'flap_centers_mm':[[-40.75,102],[40.75,102]],'flap_cap_diameter_mm':16,
 'flap_cap_clearance_hole_diameter_mm':17.0,
 'minimum_nominal_outer_web_at_flap_holes_mm':2.75,
 'screen_opening_side_web_mm':3.4,
 'minimum_case_side_clearance_to_LCD_module_mm':2.65,
 'dart_pill_center_y_mm':118,'fixed_dart_switch_centers_mm':[[-16,119.296],[16,119.296]],
 'speaker_grille_slots':'3 x 12 x 0.8 mm openings each side; acoustic inlet/chamber not validated',
 'open_gates':['The button-hole outer web is 2.75 mm nominal at the tightest point; confirm print/process tolerance and avoid local sanding that reduces it below 2 mm.','Confirm HOTHMI FPC exit/fold can support the 14.8 mm panel shift without changing the PCB.','Confirm actual LCD active area, corner radius and laminate thickness; the current face-film thickness is a 0.20 mm planning assumption.','Check button cap travel, switch actuation, and physical clearances.','Complete a rear shell with 2 mm minimum structural walls and verify the total center/battery thickness; sub-12 mm is not yet proven.','Reconcile grille opening positions with speaker diaphragms and sealed acoustic chambers.','Print and hand-test the R10 side scallop and lower saddle to tune grip reach and comfort; this is currently a CAD silhouette study.','This is an exterior-shape and front-shell candidate, not a production/tooling release.']}
(OUT/'R10_FIT_CHECKS.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
