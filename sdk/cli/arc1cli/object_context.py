"""Portable selected-object identities, bounded history and late-result tickets."""
from __future__ import annotations
import hashlib,json,re

VERSION='arc.object-context/1'
KINDS=('component','net','job','file','requirement')

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def selector(value):
    if not isinstance(value,dict) or set(value)-{'kind','target','map'}:raise ValueError('OBJECT_SELECTOR_FIELDS')
    kind=value.get('kind');target=value.get('target')
    if kind not in KINDS or not isinstance(target,str) or not 0<len(target)<=500 or any(ord(x)<32 for x in target):raise ValueError('OBJECT_SELECTOR_INVALID')
    result={'kind':kind,'target':target}
    if kind=='job' and not re.fullmatch('[a-f0-9]{32}',target):raise ValueError('OBJECT_JOB_ID')
    if 'map' in value:
        if kind not in ('component','net') or not isinstance(value['map'],str) or not re.fullmatch('[a-f0-9]{32}',value['map']):raise ValueError('OBJECT_MAP_ID')
        result['map']=value['map']
    return result

def identity(value,native=None):return digest({'selector':selector(value),'native_identity':native})

def principal_key(principal):
    return digest({'identity':principal.identity,'scopes':sorted(principal.scopes),'paths':list(principal.paths),'tools':list(principal.tools),'mode':principal.mode})

class Ticket:
    def __init__(self):self.epoch=0;self.current=None
    def begin(self,value,caller):
        self.epoch+=1;self.current=(self.epoch,digest(selector(value)),caller);return self.current
    def invalidate(self):self.epoch+=1;self.current=None
    def accepts(self,ticket,value,caller):return isinstance(ticket,tuple) and ticket==self.current and ticket[1:]==(digest(selector(value)),caller)

class History:
    """Locators and observed revisions only. Cached content/grants are forbidden."""
    def __init__(self,value=None):
        self.entries=[];self.index=-1
        if value is not None:
            if not isinstance(value,dict) or set(value)!={'schema','entries','index'} or value['schema']!=VERSION:raise ValueError('OBJECT_HISTORY_SCHEMA')
            entries=value['entries'];index=value['index']
            if not isinstance(entries,list) or len(entries)>20 or type(index)!=int or not (-1<=index<len(entries)) or (entries and index<0):raise ValueError('OBJECT_HISTORY_LIMIT')
            for entry in entries:
                if not isinstance(entry,dict) or set(entry)!={'selector','revision','object_id'}:raise ValueError('OBJECT_HISTORY_FIELDS')
                selector(entry['selector'])
                if any(not isinstance(entry[k],str) or not re.fullmatch('[a-f0-9]{64}',entry[k]) for k in ('revision','object_id')):raise ValueError('OBJECT_HISTORY_ID')
                self.entries.append({'selector':selector(entry['selector']),'revision':entry['revision'],'object_id':entry['object_id']})
            self.index=index
    def add(self,context):
        entry={'selector':selector(context['selector']),'revision':context['revision'],'object_id':context['object_id']}
        if self.current and self.current['selector']==entry['selector']:
            self.entries[self.index]=entry;return
        self.entries=self.entries[:self.index+1]+[entry];self.entries=self.entries[-20:];self.index=len(self.entries)-1
    @property
    def current(self):return self.entries[self.index] if self.index>=0 else None
    def at(self,step):
        index=self.index+step
        return self.entries[index] if 0<=index<len(self.entries) else None
    def export(self):return {'schema':VERSION,'entries':self.entries,'index':self.index}
