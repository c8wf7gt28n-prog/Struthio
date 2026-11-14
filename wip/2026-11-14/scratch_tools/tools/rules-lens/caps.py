import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from workbench import engineering_kernel as ek
ops = ['intake.namespaces','references.sources','intake.items','office.list','office.get','documents.list','documents.get','investigation.list','investigation.sheet','investigation.path','conditions.list']
from workbench import activity
import inspect
src = inspect.getsource(ek.Kernel._dispatch)
for op in ops:
    mod = None
    if op in ek.PROGRAM_HANDLERS: mod = 'PROGRAM_HANDLERS:' + ek.PROGRAM_HANDLERS[op].__name__
    else:
        for name in dir(ek):
            m = getattr(ek, name)
            if hasattr(m, 'FIELDS') and hasattr(m, 'dispatch') and op in getattr(m, 'FIELDS'):
                mod = (mod + ',' if mod else '') + name
    print('%-22s scope=%-8s observer=%s handler=%s' % (op, ek.CAPABILITIES.get(op), op in activity.OBSERVER_OPERATIONS, mod))
