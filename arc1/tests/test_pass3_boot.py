from workbench.bootlogic import BootModel,simulate
from workbench.agent import handle,AgentError
m=BootModel()
assert m.stage=='power' and 'RAILS' in m.lcd()[1]
try:m.mark('ready');raise AssertionError('READY gate bypassed')
except ValueError:pass
m.mark('f133');m.mark('nor');m.mark('d213');m.mark('fpga12');m.mark('fpga45');m.mark('ready')
assert m.stage=='ready' and m.verified==31
x=handle({'id':1,'method':'boot.simulate','params':{'events':['f133','nor','d213','fpga12','fpga45','ready']}})
assert x['evidence']=='HOST_SIM_ONLY' and x['stage']=='ready' and x['physical_boot_proven'] is False
m=BootModel();m.fault(0x1203)
assert '1203' in m.lcd()[1]
try:m.mark('f133');raise AssertionError('fault not latched')
except ValueError:pass
try:handle({'method':'boot.simulate','params':{'events':['ready']}});raise AssertionError('agent bypassed gate')
except AgentError:pass
print('PASS R05 Python boot/agent model and gates')
