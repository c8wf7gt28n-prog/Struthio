"""Bounded derived geometry. Never writes authoritative CAD."""
import argparse, hashlib, json, math, struct, time
from pathlib import Path

STEP='hardware/compact-arc1/R10_WORK/cad/pcb/ARC1_R10.step'
PCB='hardware/compact-arc1/R10_WORK/cad/ARC1_R10.kicad_pcb'
MAX_BYTES=32*1024*1024
MAX_TRIANGLES=100000


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(root,relative):
    root=Path(root).resolve();p=root/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or any(part.startswith('.') for part in Path(relative).parts):
        raise ValueError('Geometry needs a public project-relative path')
    if any(q.is_symlink() for q in [p,*p.parents] if q!=root and q.is_relative_to(root)) or not p.resolve().is_relative_to(root) or not p.is_file():
        raise ValueError('Geometry must be an ordinary file inside the project')
    if p.stat().st_size>MAX_BYTES:raise ValueError('Geometry exceeds 32 MiB limit')
    return p


def validate_triangles(triangles):
    if not isinstance(triangles,list) or not triangles or len(triangles)>MAX_TRIANGLES:
        raise ValueError('Invalid triangle count')
    for triangle in triangles:
        if not isinstance(triangle,list) or len(triangle)!=3:raise ValueError('Invalid triangle')
        for point in triangle:
            if not isinstance(point,list) or len(point)!=3:raise ValueError('Invalid vertex')
            if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>=1e6 for v in point):
                raise ValueError('Invalid geometry coordinates')
    return triangles


def stl(path):
    data=path.read_bytes();triangles=[]
    if len(data)>=84 and len(data)==84+50*struct.unpack_from('<I',data,80)[0]:
        count=struct.unpack_from('<I',data,80)[0]
        if count>MAX_TRIANGLES:raise ValueError('Mesh exceeds triangle budget')
        for i in range(count):
            row=struct.unpack_from('<12fH',data,84+i*50)
            triangles.append([list(row[j:j+3]) for j in (3,6,9)])
    else:
        vertices=[]
        for line in data.decode('ascii').splitlines():
            words=line.split()
            if words and words[0]=='vertex':
                if len(words)!=4:raise ValueError('Invalid STL vertex')
                vertices.append([float(x) for x in words[1:]])
                if len(vertices)>MAX_TRIANGLES*3:raise ValueError('Mesh exceeds triangle budget')
        if len(vertices)%3 or not vertices:raise ValueError('Invalid STL triangles')
        triangles=[vertices[i:i+3] for i in range(0,len(vertices),3)]
    if not triangles or not all(math.isfinite(v) and abs(v)<1e6 for t in triangles for p in t for v in p):
        raise ValueError('Empty, nonfinite or excessive mesh coordinates')
    return triangles


def convert(root,relative=STEP):
    started=time.monotonic();root=Path(root).resolve();path=inside(root,relative)
    if path.suffix.lower()=='.stl':
        triangles=stl(path);version='Ledger bounded STL reader/1';units='UNSPECIFIED (STL has no units)'
    elif path.suffix.lower() in ('.step','.stp'):
        from OCP.STEPControl import STEPControl_Reader
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_FACE,TopAbs_REVERSED
        from OCP.TopoDS import TopoDS
        from OCP.BRep import BRep_Tool
        from OCP.TopLoc import TopLoc_Location
        from importlib.metadata import version as installed
        # External STEP references are not part of the supported importer.
        text=path.read_text(errors='strict')
        if any(tag in text.upper() for tag in ('EXTERNALLY_DEFINED','DOCUMENT_FILE','EXTERNAL_SOURCE')):
            raise ValueError('External STEP references are unsupported')
        reader=STEPControl_Reader()
        if reader.ReadFile(str(path))!=IFSelect_RetDone:raise ValueError('STEP reader rejected input')
        reader.TransferRoots();shape=reader.OneShape()
        BRepMesh_IncrementalMesh(shape,0.25,False,0.5,False)
        explorer=TopExp_Explorer(shape,TopAbs_FACE);triangles=[]
        while explorer.More():
            face=TopoDS.Face_s(explorer.Current());loc=TopLoc_Location()
            mesh=BRep_Tool.Triangulation_s(face,loc)
            if mesh:
                for i in range(1,mesh.NbTriangles()+1):
                    ids=mesh.Triangle(i).Get()
                    if face.Orientation()==TopAbs_REVERSED:ids=ids[::-1]
                    vertices=[mesh.Node(n).Transformed(loc.Transformation()) for n in ids]
                    triangles.append([[p.X(),p.Y(),p.Z()] for p in vertices])
                    if len(triangles)>MAX_TRIANGLES:raise ValueError('STEP exceeds triangle budget')
            explorer.Next()
        if not triangles:raise ValueError('STEP contains no triangulated faces')
        version='cadquery-ocp '+installed('cadquery-ocp');units='mm (OpenCASCADE STEP transfer default)'
    else:raise ValueError('Supported inspection formats: STEP and STL; other CAD stays available as source')
    validate_triangles(triangles)
    return dict(schema='arc-ledger.mesh/1',source=relative,sha256=sha(path),
                converter=version,converter_sha256=sha(Path(__file__)),units=units,
                parameters=dict(linear_deflection=0.25,angular_deflection=0.5),
                triangles=triangles,duration_seconds=time.monotonic()-started,
                physical_validation=False,assembled_coordinates=True)


def cache(root,relative=STEP):
    p=inside(root,relative)
    key=hashlib.sha256((relative+sha(p)+sha(Path(__file__))).encode()).hexdigest()
    return Path(root)/'build/geometry'/(key+'.json')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',default=STEP)
    a=p.parse_args();out=cache(a.root,a.source)
    result=convert(a.root,a.source);out.parent.mkdir(parents=True,exist_ok=True)
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(result));temp.replace(out)
    print(json.dumps(dict(path=str(out),triangles=len(result['triangles']),duration_seconds=result['duration_seconds'])))

if __name__=='__main__':main()
