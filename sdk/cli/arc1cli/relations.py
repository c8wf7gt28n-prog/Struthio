"""Bounded native KiCad netlist relationships, independent of GUI/provider.

An edge means common membership in a netlist net. It never asserts routed
copper, signal direction, current flow or physical operation.
"""
from collections import defaultdict, deque
import hashlib
import re
import xml.etree.ElementTree as ET


def is_power(name):
    return bool(re.search(r'(^|[/_+])(GND|AGND|DGND|VCC|VDD|VBUS|VCORE|[0-9]+V[0-9])', name, re.I))


class NetGraph:
    def __init__(self, data):
        if not isinstance(data,bytes) or len(data)>16*1024*1024:raise ValueError('NETLIST_SIZE_LIMIT')
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('XML_ENTITIES_FORBIDDEN')
        tree=ET.fromstring(data)
        self.sha256=hashlib.sha256(data).hexdigest()
        self.components={};self.nets={};self.members=defaultdict(set)
        self.sheets={s.get('name'):s.findtext('title_block/source') or s.findtext('source')
                     for s in tree.findall('./design/sheet')}
        for c in tree.findall('./components/comp'):
            ref=c.get('ref')
            if not isinstance(ref,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,50}',ref) or ref in self.components:raise ValueError('NATIVE_COMPONENT_ID')
            sheet=c.find('sheetpath')
            self.components[ref]={'reference':ref,'value':c.findtext('value') or '',
                'footprint':c.findtext('footprint') or '', 'native_uuid':c.findtext('tstamps') or '',
                'sheet_name':sheet.get('names','') if sheet is not None else '', 'pins':[]}
        if len(self.components)>5000:raise ValueError('COMPONENT_LIMIT')
        count=0
        for n in tree.findall('./nets/net'):
            name=n.get('name')
            if not isinstance(name,str) or len(name)>500 or name in self.nets:raise ValueError('NATIVE_NET_ID')
            pins=[]
            for node in n.findall('node'):
                ref=node.get('ref');pin=node.get('pin')
                if ref not in self.components or not isinstance(pin,str):raise ValueError('DANGLING_NATIVE_PIN')
                row={'reference':ref,'pin':pin,'function':node.get('pinfunction',''),
                     'pin_type':node.get('pintype',''),'net':name}
                pins.append(row);self.components[ref]['pins'].append(row.copy());self.members[ref].add(name);count+=1
                if count>50000:raise ValueError('PIN_LIMIT')
            self.nets[name]={'name':name,'code':n.get('code'),'pins':pins,'power_net':is_power(name),
                             'unconnected':name.startswith('unconnected-') or len(pins)<2}
        if len(self.nets)>20000:raise ValueError('NET_LIMIT')
        self.pin_count=count

    def neighbors(self, reference, include_power=False, limit=24, net_kind='all'):
        if reference not in self.components:raise ValueError('UNKNOWN_COMPONENT')
        joined=defaultdict(list)
        for name in sorted(self.members[reference]):
            net=self.nets[name]
            if net['unconnected'] or (net['power_net'] and not include_power):continue
            if net_kind=='usb-data' and not (re.search(r'(USB|HUB)',name,re.I) and re.search(r'_D[PM]$',name)):continue
            for pin in net['pins']:
                if pin['reference']!=reference and name not in joined[pin['reference']]:joined[pin['reference']].append(name)
        found=[{'reference':ref,'value':self.components[ref]['value'],'nets':names,
                'relation':'NATIVE_SCHEMATIC_NET'} for ref,names in sorted(joined.items())]
        return found[:limit],len(found)

    def trace(self,start,end,max_hops=12,include_power=False,net_kind='all'):
        if start not in self.components or end not in self.components:raise ValueError('UNKNOWN_TRACE_ENDPOINT')
        if type(max_hops) is not int or not 1<=max_hops<=16:raise ValueError('TRACE_DEPTH_LIMIT')
        queue=deque([(start,[],{start})]);seen={start}
        while queue:
            ref,edges,visited=queue.popleft()
            if ref==end:return {'state':'FOUND','edges':edges,'nodes':[start]+[e['to'] for e in edges],
                'relation':'NATIVE_SCHEMATIC_NET','max_hops':max_hops,'electrical_operation_verified':False}
            if len(edges)>=max_hops:continue
            neighbors,_=self.neighbors(ref,include_power,5000,net_kind)
            for other in neighbors:
                target=other['reference']
                if target in seen:continue
                seen.add(target)
                edge={'from':ref,'to':target,'nets':other['nets'],'relation':'NATIVE_SCHEMATIC_NET'}
                queue.append((target,edges+[edge],visited|{target}))
        return {'state':'NO_PATH_WITHIN_LIMIT','edges':[],'nodes':[], 'max_hops':max_hops,
                'relation':'NATIVE_SCHEMATIC_NET','electrical_operation_verified':False}
