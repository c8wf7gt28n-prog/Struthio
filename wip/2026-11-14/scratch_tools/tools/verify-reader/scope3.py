"""Unreadable sheets and scope: (a) an EMPTY second workspace while the profile's sheets cannot be read; (b) the worked case while
they cannot be read: how many does the status line count and how many does the surface show as 'not read'?"""
from common import *
from workbench.field_source import read_field, problems
from workbench import office_service
other = RUN / 'other-ws'; other.mkdir(); k2 = Kernel(other); k = Kernel(RUN / 'ws'); hold_processes()
def damaged(key, kernel=None, principal=None): raise ValueError('OFFICE_RECORD_DAMAGED')
office_service.get = damaged
for tag, kern in (('empty second workspace', k2), ('worked case', k)):
    f, r = read_field(kern, P)
    print('%-24s census: %s | status sentence: %r | drawn as not read: %s' % (tag, f.census(), problems(r), [o.title for o in f.objects if o.state == 'not read']))
