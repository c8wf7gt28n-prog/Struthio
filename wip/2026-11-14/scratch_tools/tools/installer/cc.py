import json,sys
d=json.loads(open(sys.argv[1]).read())
def show(o,ind=0):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='parts' and isinstance(v,list):
                print(' '*ind+'parts: <%d rows> total %d'%(len(v),sum(p['bytes'] for p in v)));continue
            if isinstance(v,(dict,list)):
                print(' '*ind+str(k)+':');show(v,ind+2)
            else:print(' '*ind+str(k)+': '+repr(v))
    elif isinstance(o,list):
        for i,v in enumerate(o[:40]):
            if isinstance(v,(dict,list)):print(' '*ind+'-');show(v,ind+2)
            else:print(' '*ind+'- '+repr(v))
        if len(o)>40:print(' '*ind+'... %d more'%(len(o)-40))
show(d)
