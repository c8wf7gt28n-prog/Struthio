from pathlib import Path
import runpy, json, math, io, contextlib
import cadquery as cq
ROOT=Path(__file__).resolve().parents[2]
CASE=Path(__file__).resolve().parent
ACRYLIC=ROOT/'LAYERS'/'03_ACRYLIC'; ACRYLIC.mkdir(parents=True,exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()): ns=runpy.run_path(str(CASE/'build_r10.py'))
def val(x): return x.val() if hasattr(x,'val') else x
def assembly(name,items,path):
    a=cq.Assembly(name=name)
    for part,label,color in items:a.add(part,name=label,color=color)
    a.save(str(path))
def stl(items,path):
    cq.exporters.export(cq.Compound.makeCompound([val(p) for p,_,_ in items]),str(path),exportType='STL',tolerance=.12,angularTolerance=.12)
navy=cq.Color(.08,.20,.32);trim=cq.Color(.10,.24,.37);lcdcol=cq.Color(.22,.63,.70);lenscol=cq.Color(.40,.75,.86);orange=cq.Color(.96,.48,.08)
case_items=[(ns['shell'],'R10_FRONT_SHELL_2MM_MIN',navy)]
case_items += [(p,n,trim) for p,n in ns['sculpture']]
case_items += [(ns['lcd'],'HOTHMI_LCD_MODULE_R10',lcdcol),(ns['lens'],'PROTECTIVE_LENS_R10',lenscol)]
case_items += [(p,n,orange) for p,n in ns['controls']]
assembly('STRUTHIO_CASE_FRONT_R10',case_items,CASE/'STRUTHIO_CASE_FRONT_R10.step');stl(case_items,CASE/'STRUTHIO_CASE_FRONT_R10.stl')
assembly('CASE_FRONT_SHELL_R10',[(ns['shell'],'FRONT_SHELL_2MM_MIN',navy)],CASE/'CASE_FRONT_SHELL_R10.step');stl([(ns['shell'],'FRONT_SHELL_2MM_MIN',navy)],CASE/'CASE_FRONT_SHELL_R10.stl')
assembly('CASE_SCREEN_STACK_R10',[(ns['lcd'],'HOTHMI_LCD_MODULE',lcdcol),(ns['lens'],'PROTECTIVE_LENS',lenscol)],CASE/'CASE_SCREEN_STACK_R10.step')
assembly('CASE_CONTROLS_R10',[(p,n,trim) for p,n in ns['sculpture']]+[(p,n,orange) for p,n in ns['controls']],CASE/'CASE_CONTROLS_R10.step')
film=[(ns['face_sticker'],'CLEAR_FACE_FILM_0P20MM_ASSUMED',cq.Color(.55,.83,.88))]
assembly('STRUTHIO_ACRYLIC_CLEAR_FACE_FILM_R0',film,ACRYLIC/'STRUTHIO_ACRYLIC_FACE_FILM_R0.step');stl(film,ACRYLIC/'STRUTHIO_ACRYLIC_FACE_FILM_R0.stl')
def rr(cx,cy,w,h,r,n=8):
    pts=[]
    for ax,ay,start in [(cx+w/2-r,cy-h/2+r,-90),(cx+w/2-r,cy+h/2-r,0),(cx-w/2+r,cy+h/2-r,90),(cx-w/2+r,cy-h/2+r,180)]:
        for i in range(n+1):
            a=math.radians(start+i*90/n);pts.append((ax+r*math.cos(a),ay+r*math.sin(a)))
    return pts
def circle(cx,cy,r,n=64):return [(cx+r*math.cos(2*math.pi*i/n),cy+r*math.sin(2*math.pi*i/n)) for i in range(n)]
loops=[ns['outline']]+[circle(x,102,8.5) for x in (-40.75,40.75)]+[rr(0,118,50,8,3.9)]
for x in (-41.5,41.5):
    for y in (120.7,122.6,124.5):loops.append(rr(x,y,12.2,1,.49))
def pathd(pts):return 'M '+' '.join((f'{x:.4f},{y:.4f}' if i==0 else f'L {x:.4f},{y:.4f}') for i,(x,y) in enumerate(pts))+' Z'
d=' '.join(pathd(x) for x in loops)
svg='\n'.join(['<?xml version="1.0" encoding="UTF-8"?>', '<svg xmlns="http://www.w3.org/2000/svg" width="104mm" height="135.3mm" viewBox="-52 0 104 135.3">','<title>STRUTHIO acrylic face film R0 cutline — planning only</title>','<desc>Clear 0.20 mm assumed face film. Display window remains continuous with no screen cutout. Coordinates are mm on shared R21/R10 XY datum. Cut paths require supplier tolerance review.</desc>',f'<g id="CUTLINE" fill="none" stroke="#d34b56" stroke-width="0.15" fill-rule="evenodd" transform="translate(0 135.3) scale(1 -1)"><path d="{d}"/></g>','</svg>',''])
(ACRYLIC/'ACRYLIC_FACE_FILM_CUTLINE_R0.svg').write_text(svg)
def dxf(pts):
    q='0\nLWPOLYLINE\n100\nAcDbEntity\n8\nCUTLINE\n100\nAcDbPolyline\n90\n'+str(len(pts))+'\n70\n1\n'
    for x,y in pts:q+=f'10\n{x:.5f}\n20\n{y:.5f}\n'
    return q
header='0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n'
(ACRYLIC/'ACRYLIC_FACE_FILM_CUTLINE_R0.dxf').write_text(header+''.join(map(dxf,loops))+'0\nENDSEC\n0\nEOF\n')
meta={'layer':'ACRYLIC','revision':'R0','status':'clear-film cutline study; NOT production artwork','units':'mm','shared_xy_datum':'SLIM4_R21 PCB XY; film lower face Z=7.65 mm','outer_size_mm':[104.0,135.3],'film_thickness_mm_assumed':0.20,'screen_window':'No screen cutout; clear film continuous across lens. Print/white/relief not designed.','cutouts_mm':{'flap_centers':[[-40.75,102],[40.75,102]],'dart_pill_center':[0,118],'vent_x':[-41.5,41.5],'vent_y':[120.7,122.6,124.5]},'release_gate':'Confirm material, optics, perimeter, adhesive, control and vent clearances, tolerance, and supplier process before cutting.'}
(ACRYLIC/'ACRYLIC_LAYER_R0_CUT_SPEC.json').write_text(json.dumps(meta,indent=2)+'\n')
def mesh(name,shape,group,color,opacity=1,tol=.45):
    verts,tris=val(shape).tessellate(tol,.32);rows=[]
    for t in tris:
        p=[[round(float(verts[i].x),3),round(float(verts[i].y),3),round(float(verts[i].z),3)] for i in t];a,b,c=p;u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];shade=round(.72+.28*abs(n[2])/(math.sqrt(sum(k*k for k in n)) or 1),3);rows.append({'p':p,'s':shade})
    return {'name':name,'group':group,'color':color,'opacity':opacity,'triangles':rows}
case_data=[mesh('R10 MOLDED FRONT SHELL · 2.0 MM MINIMUM',ns['shell'],'shell','#193c59',1,.4)]
case_data += [mesh(n,p,'controls','#315876',1,.3) for p,n in ns['sculpture']]
case_data += [mesh('HOTHMI 4.7 INCH LCD MODULE · R10 DATUM',ns['lcd'],'display','#59636b',1,.45),mesh('PROTECTIVE LENS · 59.2 × 104.4 × 0.70 MM',ns['lens'],'display','#72c8d2',.32,.3)]
case_data += [mesh(n,p,'controls','#f08b23',1,.3) for p,n in ns['controls']]
acrylic_data=[mesh('CLEAR ACRYLIC FACE FILM · ASSUMED 0.20 MM',ns['face_sticker'],'acrylic','#a8e6ef',.23,.3)]
case_json={'layer':'CASE','revision':'R10','status':'front case candidate; rear/audio/battery enclosure not included','source':'LAYERS/02_CASE/export_layer_formats.py','units':'mm','shared_xy_datum':'SLIM4_R21 PCB XY','case_outline_mm':[104,135.3],'parts':case_data}
(ROOT/'LAYERS'/'02_CASE'/'CASE_LAYER_R10_MESH.json').write_text(json.dumps(case_json,indent=2)+'\n')
(ROOT/'case-layer-data.js').write_text('window.STRUTHIO_CASE_R10='+json.dumps(case_json,separators=(',',':'))+';\n')
acrylic_json={'layer':'ACRYLIC','revision':'R0','status':'clear film only; artwork pending','source':'LAYERS/02_CASE/export_layer_formats.py','units':'mm','shared_xy_datum':'SLIM4_R21 PCB XY','thickness_mm_assumed':.2,'parts':acrylic_data}
(ACRYLIC/'ACRYLIC_LAYER_R0_MESH.json').write_text(json.dumps(acrylic_json,indent=2)+'\n')
(ROOT/'acrylic-layer-data.js').write_text('window.STRUTHIO_ACRYLIC_R0='+json.dumps(acrylic_json,separators=(',',':'))+';\n')
print('Separate STEP/STL/SVG/DXF layer files and PWA mesh sources written.')
