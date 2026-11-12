"""SW-002 portable, inert view projections and independent presentation bounds."""
from __future__ import annotations
import hashlib,json,math,re

VERSION='arc.slate-view/1'
VIEWS=('object','sources','evidence','review','pdf')
MAX_CONTENT=96*1024
MAX_TEXT=48*1024
MAX_BLOCKS=24
DEFAULT_LAYOUT={'scroll':0,'zoom':1.0}
REMOTE_OPERATIONS=frozenset({'ledger.deck.list','ledger.deck.read','ledger.deck.image','ledger.deck.present'})

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def view(value):
    if value not in VIEWS:raise ValueError('WINDOW_VIEW_UNAVAILABLE')
    return value
def presentation(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULT_LAYOUT):raise ValueError('WINDOW_VIEW_PRESENTATION_FIELDS')
    result={**DEFAULT_LAYOUT,**value}
    if type(result['scroll']) is not int or not 0<=result['scroll']<=10_000_000 or type(result['zoom']) not in (int,float) or not math.isfinite(result['zoom']) or not .5<=result['zoom']<=3:raise ValueError('WINDOW_VIEW_PRESENTATION_RANGE')
    return result
def text(value,limit=MAX_TEXT):
    raw=str(value).encode('utf-8');short=raw[:limit].decode('utf-8',errors='ignore')
    return short,len(raw)>limit
def block(title,value,*,collapsed=False):
    body=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)
    body,truncated=text(body)
    return {'title':str(title)[:180],'text':body,'truncated':truncated,'format':'plain-text','collapsed':bool(collapsed)}
def projection(window,kind,blocks,image=None):
    view(kind)
    value={'schema':VERSION,'window_id':window['id'],'object_id':window['overview']['object_id'],
        'source_revision':window['overview']['source_revision'],'state_revision':window['generation'],
        'title':window['overview']['title'],'view':kind,'blocks':blocks,'image':image,
        'effects':['read'],'physical_qualification':False,
        'notice':'Reviewed reading view. Original identity stays attached; sharing grants no execution or engineering acceptance.'}
    validate(value)
    return value
def validate(value):
    if not isinstance(value,dict) or set(value)!={'schema','window_id','object_id','source_revision','state_revision','title','view','blocks','image','effects','physical_qualification','notice'}:raise ValueError('WINDOW_VIEW_SCHEMA')
    if value['schema']!=VERSION or not re.fullmatch(r'sw_[0-9a-f]{32}',value['window_id']) or any(not re.fullmatch(r'[a-f0-9]{64}',value[k]) for k in ('object_id','source_revision')):raise ValueError('WINDOW_VIEW_IDENTITY')
    view(value['view'])
    if type(value['state_revision']) is not int or value['state_revision']<1 or not isinstance(value['title'],str) or len(value['title'])>300 or value['effects']!=['read'] or value['physical_qualification'] is not False:raise ValueError('WINDOW_VIEW_AUTHORITY')
    if not isinstance(value['blocks'],list) or not 1<=len(value['blocks'])<=MAX_BLOCKS:raise ValueError('WINDOW_VIEW_BLOCK_LIMIT')
    for row in value['blocks']:
        if not isinstance(row,dict) or set(row)!={'title','text','truncated','format','collapsed'} or row['format']!='plain-text' or type(row['truncated']) is not bool or type(row['collapsed']) is not bool or not all(isinstance(row[k],str) for k in ('title','text')) or len(row['title'])>180 or len(row['text'].encode())>MAX_TEXT:raise ValueError('WINDOW_VIEW_BLOCK_SCHEMA')
    image=value['image']
    if image is not None and (not isinstance(image,dict) or set(image)!={'sha256','width','height','type'} or image['type']!='image/png' or not re.fullmatch(r'[a-f0-9]{64}',image['sha256']) or any(type(image[k]) is not int or not 1<=image[k]<=2000 for k in ('width','height'))):raise ValueError('WINDOW_VIEW_IMAGE_SCHEMA')
    if len(canonical(value))>MAX_CONTENT:raise ValueError('WINDOW_VIEW_CONTENT_LIMIT')
    return value
