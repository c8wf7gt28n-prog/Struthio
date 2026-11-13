"""Bounded read-only GGUF inspection; no model/runtime imports or tensor loads.

Format: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
This independent inspector follows the public format, not pickle or executable metadata.
"""
from __future__ import annotations
import hashlib,io,json,math,re,struct
from pathlib import Path

SCALARS={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
TYPES={0:('F32',1,4),1:('F16',1,2),2:('Q4_0',32,18),3:('Q4_1',32,20),
       6:('Q5_0',32,22),7:('Q5_1',32,24),8:('Q8_0',32,34),9:('Q8_1',32,40),
       10:('Q2_K',256,84),11:('Q3_K',256,110),12:('Q4_K',256,144),13:('Q5_K',256,176),
       14:('Q6_K',256,210),15:('Q8_K',256,292),30:('BF16',1,2)}
ARCHITECTURES={'llama','qwen2','qwen3','qwen3moe','qwen35','qwen35moe','gemma','gemma2','gemma3','phi3','gpt2','smollm3'}  # qwen35moe: Qwen3.6-35B-A3B, the owner's model (0.8.0)
MAX_HEADER=128*1024*1024

class Reader:
    def __init__(self,stream,size):self.stream=stream;self.size=size;self.endian='<';self.capture=None
    def read(self,n):
        if n<0 or self.stream.tell()+n>min(self.size,MAX_HEADER):raise ValueError('GGUF_HEADER_LIMIT_OR_TRUNCATED')
        raw=self.stream.read(n)
        if len(raw)!=n:raise ValueError('GGUF_TRUNCATED')
        if self.capture is not None:self.capture.update(raw)
        return raw
    def number(self,kind):return struct.unpack(self.endian+kind,self.read(struct.calcsize(kind)))[0]
    def string(self,keep=True,limit=2*1024*1024):
        length=self.number('Q')
        if length>limit:raise ValueError('GGUF_STRING_LIMIT')
        raw=self.read(length)
        return raw.decode('utf-8',errors='strict') if keep else None
    def value(self,kind,keep=True):
        if kind in SCALARS:
            result=self.number(SCALARS[kind])
            if isinstance(result,float) and not math.isfinite(result):raise ValueError('GGUF_NONFINITE_METADATA')
            return result if keep else None
        if kind==8:return self.string(keep)
        if kind==9:
            subtype=self.number('I');count=self.number('Q')
            if subtype==9 or subtype not in (*SCALARS,8) or count>2_000_000:raise ValueError('GGUF_ARRAY_LIMIT_OR_TYPE')
            # Vocabulary arrays stay indexable metadata summaries, never a huge UI list.
            if subtype in SCALARS:
                self.read(count*struct.calcsize(SCALARS[subtype]))
            else:
                for _ in range(count):self.string(False)
            return {'array_type':subtype,'count':count} if keep else None
        raise ValueError('GGUF_UNKNOWN_METADATA_TYPE')

def inspect(path):
    path=Path(path).expanduser().absolute()
    if path.suffix.lower()!='.gguf' or not path.is_file() or any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('Select a regular local .gguf file; linked files are not supported')
    size=path.stat().st_size
    with path.open('rb') as stream:
        reader=Reader(stream,size)
        if reader.read(4)!=b'GGUF':raise ValueError('GGUF_MAGIC_INVALID')
        version_bytes=reader.read(4);version=struct.unpack('<I',version_bytes)[0]
        if version not in (2,3):
            reader.endian='>';version=struct.unpack('>I',version_bytes)[0]
        if version not in (2,3):raise ValueError('GGUF_VERSION_UNSUPPORTED')
        tensor_count=reader.number('Q');key_count=reader.number('Q')
        if tensor_count>200_000 or key_count>10_000:raise ValueError('GGUF_TABLE_LIMIT')
        metadata={};metadata_hashes={}
        for _ in range(key_count):
            key=reader.string(limit=1024)
            if not key or key in metadata:raise ValueError('GGUF_DUPLICATE_OR_EMPTY_KEY')
            reader.capture=hashlib.sha256()
            metadata[key]=reader.value(reader.number('I'))
            metadata_hashes[key]=reader.capture.hexdigest();reader.capture=None
        tensors=[];regions=[];parameters=0;quantization={};names=set()
        for i in range(tensor_count):
            name=reader.string(limit=4096);dimensions=reader.number('I')
            if not name or name in names or not 1<=dimensions<=4:raise ValueError('GGUF_TENSOR_SCHEMA')
            names.add(name);shape=[reader.number('Q') for _ in range(dimensions)]
            if any(n<1 or n>2**32 for n in shape):raise ValueError('GGUF_TENSOR_DIMENSION')
            count=math.prod(shape)
            if count>2**48:raise ValueError('GGUF_TENSOR_SIZE_LIMIT')
            kind=reader.number('I');offset=reader.number('Q');description=TYPES.get(kind)
            # Unknown quantization is shown explicitly and held from this adapter's qualification.
            label=description[0] if description else 'UNSUPPORTED_TYPE_'+str(kind)
            tensor_bytes=None
            if description:
                _,block,unit=description
                if shape[0]%block:raise ValueError('GGUF_TENSOR_BLOCK_ALIGNMENT')
                tensor_bytes=count//block*unit
            regions.append((offset,tensor_bytes));parameters+=count
            quantization[label]=quantization.get(label,0)+1
            if i<256:tensors.append({'name':name,'shape':shape,'type':label,'offset':offset,'bytes':tensor_bytes})
        alignment=metadata.get('general.alignment',32)
        if type(alignment)!=int or alignment<1 or alignment>4096 or alignment&(alignment-1):raise ValueError('GGUF_ALIGNMENT_INVALID')
        data_start=(stream.tell()+alignment-1)//alignment*alignment
        previous_end=0
        for offset,length in sorted(regions):
            if offset%alignment or offset<previous_end or data_start+offset>=size:raise ValueError('GGUF_TENSOR_OFFSET_INVALID')
            if length is not None:
                if data_start+offset+length>size:raise ValueError('GGUF_TENSOR_DATA_TRUNCATED')
                previous_end=offset+length
        architecture=metadata.get('general.architecture','')
        if not isinstance(architecture,str) or not re.fullmatch(r'[a-z0-9_]{1,64}',architecture):raise ValueError('GGUF_ARCHITECTURE_METADATA_TYPE')
        for key in ('general.name','general.license','general.source.url','general.url','tokenizer.chat_template'):
            if key in metadata and not isinstance(metadata[key],str):raise ValueError('GGUF_TEXT_METADATA_TYPE: '+key)
        return {'schema':'arc.gguf-inspection/1','file':path.name,'bytes':size,'version':version,
                'byte_order':'little' if reader.endian=='<' else 'big','architecture':architecture,
                'architecture_profile':'SUPPORTED_FOR_TRIAL' if architecture in ARCHITECTURES else 'UNSUPPORTED_ARCHITECTURE',
                'metadata':metadata,'metadata_hashes':metadata_hashes,'tensor_count':tensor_count,'tensor_preview':tensors,
                'tensor_preview_truncated':tensor_count>256,'parameter_count':parameters,'quantization':quantization,
                'data_offset':data_start,'inspection_only':True,'runtime_started':False}

def identity(path,cancelled=lambda:False):
    path=Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('MODEL_LOCATION_CHANGED_OR_LINKED')
    before=path.stat();digest=hashlib.sha256()
    with path.open('rb') as stream:
        while raw:=stream.read(4*1024*1024):
            if cancelled():raise ValueError('MODEL_INSPECTION_CANCELLED')
            digest.update(raw)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
        raise ValueError('MODEL_CHANGED_DURING_INSPECTION')
    return {'name':path.name,'bytes':after.st_size,'sha256':digest.hexdigest()}

def inspect_set(source,role='chat',projector=None,cancelled=lambda:False):
    source=Path(source).expanduser().absolute()
    if source.is_dir():
        files=sorted(p for p in source.glob('*.gguf') if not p.name.lower().startswith(('mmproj','mtp-')))
        first=[p for p in files if not re.search(r'-\d{5}-of-\d{5}\.gguf$',p.name) or re.search(r'-00001-of-\d{5}\.gguf$',p.name)]
        if len(first)!=1:raise ValueError('MODEL_FOLDER_AMBIGUOUS: choose one model file or one complete shard set')
        source=first[0]
        projectors=sorted(source.parent.glob('mmproj*.gguf'))
        if projector is None and len(projectors)==1:projector=projectors[0]
    main=inspect(source);meta=main['metadata'];count=meta.get('split.count',1)
    if type(count)!=int or not 1<=count<=256:raise ValueError('MODEL_SHARD_COUNT_INVALID')
    match=re.fullmatch(r'(.+)-(\d{5})-of-(\d{5})\.gguf',source.name)
    if count>1:
        if not match or int(match[3])!=count:raise ValueError('MODEL_SHARD_NAMES_INCOMPLETE')
        files=[source.with_name(f'{match[1]}-{i+1:05d}-of-{count:05d}.gguf') for i in range(count)]
    else:files=[source]
    members=[];total_tensors=0
    for number,path in enumerate(files):
        if not path.is_file():raise ValueError('MODEL_SHARD_MISSING: '+path.name)
        header=inspect(path);m=header['metadata']
        if count>1 and (m.get('split.no')!=number or m.get('split.count')!=count or header['architecture']!=main['architecture']):
            raise ValueError('MODEL_SHARDS_MISMATCHED')
        if count>1 and (header['byte_order']!=main['byte_order'] or any(
            header['metadata_hashes'][key]!=main['metadata_hashes'][key]
            for key in set(header['metadata_hashes'])&set(main['metadata_hashes']) if not key.startswith('split.'))):
            raise ValueError('MODEL_SHARDS_METADATA_MISMATCHED')
        members.append({**identity(path,cancelled),'path':str(path),'role':'weights'})
        total_tensors+=header['tensor_count']
    if count>1 and meta.get('split.tensors.count') not in (None,total_tensors):raise ValueError('MODEL_SHARD_TENSOR_COUNT_MISMATCH')
    if projector is not None:
        projector=Path(projector).expanduser().absolute();header=inspect(projector)
        if header['architecture']!='clip':raise ValueError('MODEL_PROJECTOR_ARCHITECTURE_MISMATCH')
        expected=meta.get(main['architecture']+'.embedding_length')
        dimension=header['metadata'].get('clip.vision.projection_dim')
        if not expected or dimension!=expected:raise ValueError('MODEL_PROJECTOR_PAIRING_UNVERIFIED: projection dimension must match model embedding length')
        members.append({**identity(projector,cancelled),'path':str(projector),'role':'projector'})
    if role=='vision' and not any(m['role']=='projector' for m in members):raise ValueError('MODEL_PROJECTOR_MISSING')
    if role not in ('chat','vision','embedding'):raise ValueError('MODEL_ROLE_INVALID')
    if main['tensor_count']==0:raise ValueError('MODEL_CONTAINS_NO_TENSORS')
    immutable={'role':role,'files':[{k:m[k] for k in ('name','bytes','sha256','role')} for m in members]}
    file_set_id=hashlib.sha256(json.dumps(immutable,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'schema':'arc.model-file-set/1','id':file_set_id,'role':role,'files':members,'inspection':main,
            'total_bytes':sum(m['bytes'] for m in members),'declared_license':meta.get('general.license','NOT_DECLARED'),
            'declared_origin':meta.get('general.source.url',meta.get('general.url','NOT_DECLARED')),
            'message_template':meta.get('tokenizer.chat_template'),'qualification':'NOT_TESTED'}
