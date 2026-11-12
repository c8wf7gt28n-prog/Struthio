"""Validated reading preferences. Legacy profiles inherit their previous prose size."""
DEFAULT = {'family':'IBM Plex Sans','ui_pt':14.0,'navigation_pt':15.0,
           'code_pt':14.0,'prose_pt':16.0,'prose_family':'IBM Plex Sans',
           'code_family':'IBM Plex Mono','line_height':1.4,'reduce_motion':False}
# Before 2.0 these were the defaults. A profile that still holds exactly them never chose a font, so 2.0 shows Plex.
OLD_DEFAULT_FAMILIES = ('DejaVu Sans', 'DejaVu Sans', 'DejaVu Sans Mono')


# The one place the size limits live. Paper v1.1: text must reach 200% (14 pt interface → 28 pt), never shrunk to fit.
RANGES = (('ui_pt', 9, 28), ('navigation_pt', 9, 28), ('code_pt', 9, 32), ('prose_pt', 9, 40), ('line_height', 1.0, 1.8))


def clean(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULT):
        raise ValueError('READING_PROFILE_FIELDS')
    data={**DEFAULT,**value}
    if 'prose_family' not in value:
        data['prose_family']=data['family']
    if 'prose_pt' not in value and 'ui_pt' in value:
        data['prose_pt']=value['ui_pt']
    for key in ('family','prose_family','code_family'):
        name=data[key]
        if not isinstance(name,str) or not 1<=len(name)<=100 or any(c in name for c in "'\";{}<>\n\r\\"):
            raise ValueError('READING_FONT_INVALID')
    for key,lo,hi in RANGES:
        n=data[key]
        if type(n) not in (int,float) or not lo<=n<=hi:
            raise ValueError('READING_RANGE: '+key)
    if type(data['reduce_motion']) is not bool:
        raise ValueError('READING_MOTION_INVALID')
    return data
