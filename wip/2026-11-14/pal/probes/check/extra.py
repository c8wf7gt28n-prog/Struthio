import sys;sys.path.insert(0,sys.argv[1])
from workbench import math_model as m
free={'voltage':{'unit':'V','value':'12'},'current':{'unit':'mA','lower':'0','domain':'integer'},'limit':{'unit':'W','value':'6'}}
r=m.compile_expression('voltage * current <= limit',free)
print('free current witness 500/501:',m.witness_check(r,{'current':'500'}),m.witness_check(r,{'current':'501'}))
s=m.compile_expression('voltage * current < limit',free)
b=m.sweep(s,'current','0','1000',101)['boundaries'];print('strict integer boundary:',[(x['input']['rational'],x['relation']) for x in b])
print('strict integer witness 499/500:',m.witness_check(s,{'current':'499'}),m.witness_check(s,{'current':'500'}))
decl={'voltage':{'unit':'V','value':'12'},'current':{'unit':'mA','value':'280'},'limit':{'unit':'W','value':'6'}}
d=m.compile_expression('voltage * current <= limit',decl)
print('declared current: witness 280/500, evaluate 500:',m.witness_check(d,{'current':'280'}),m.witness_check(d,{'current':'500'}),m.evaluate(d,{'current':'500'})['state'])
# relation output with an output unit of another dimension
try:print(m.evaluate(d,output_unit='mA')['state'])
except Exception as e:print('evaluate relation output_unit=mA raises',type(e).__name__,e)
# sweep evaluates with output_unit; boolean row with V*I and W
print('sweep boolean value/limit unit:',m.sweep(d,'current','0','1000',2,output_unit='mW')['samples'][1]['value'])
