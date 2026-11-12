"""Fixed, resource-bounded SymPy and QF_LIRA adapters over validated math nodes."""
from __future__ import annotations
import importlib.metadata
import json
import os
import subprocess
import sys
from fractions import Fraction
from . import math_model as core
from .math_units import rational, unit_spec

PINS={'sympy':'1.14.0','z3-solver':'4.15.4.0','mpmath':'1.3.0'}


def status():
    rows={}
    for name,pin in PINS.items():
        try:version=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:version=None
        rows[name]={'installed':version,'required':pin,'state':'PINNED' if version==pin else 'MISSING' if version is None else 'DIFFERENT_VERSION'}
    return rows


def solve(ir, backend, seconds=4):
    ir=core.validate(ir['model'])
    if backend not in ('SYMPY','Z3'):raise ValueError('Unknown mathematical backend')
    try:core.affine(ir)
    except core.MathError as exc:
        if backend=='Z3' or ir['model']['constraints']:
            return {'state':exc.code,'reason':str(exc),'backend':backend,'domain_conditions':ir['domain_conditions']}
    package='sympy' if backend=='SYMPY' else 'z3-solver';available=status()
    if available[package]['state']!='PINNED' or backend=='SYMPY' and available['mpmath']['state']!='PINNED':
        return {'state':'UNAVAILABLE','reason':'Install the pinned optional requirements-math.txt dependencies','backend':backend,'dependencies':available}
    request={'model':ir['model'],'backend':backend}
    try:
        child=subprocess.run([sys.executable,'-m','workbench.math_backend','_worker'],input=json.dumps(request),
            capture_output=True,text=True,timeout=min(5,max(1,seconds)),env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    except subprocess.TimeoutExpired:return {'state':'UNKNOWN','reason':'BACKEND_WALL_TIME_LIMIT','backend':backend,'domain_conditions':ir['domain_conditions']}
    if child.returncode or len(child.stdout)>262144:
        return {'state':'UNKNOWN','reason':'BACKEND_RESOURCE_OR_PROCESS_FAILURE','backend':backend,'exit_code':child.returncode,'domain_conditions':ir['domain_conditions']}
    try:answer=json.loads(child.stdout)
    except ValueError:return {'state':'UNKNOWN','reason':'BACKEND_RESULT_NOT_PARSED','backend':backend}
    if answer.get('state')=='FEASIBLE' and not core.witness_check(ir,answer.get('assignments',{})):
        return {'state':'UNKNOWN','reason':'BACKEND_WITNESS_REJECTED_BY_EXACT_IR','backend':backend}
    answer.update(backend=backend,version=available[package]['installed'],model_digest=ir['model_digest'],
        domain_conditions=ir['domain_conditions'],assumptions=ir['model']['assumptions'],
        scope='DECLARED_MODEL_CONSEQUENCE',physical_qualification=False,limits={'wall_seconds':min(5,max(1,seconds)),'cpu_seconds':3,'address_space_mib':512},
        witness_check='EXACT_IR_RECHECKED' if answer.get('state')=='FEASIBLE' else 'NO_WITNESS_CLAIM')
    if answer.get('state')=='FEASIBLE':answer['evaluation']=core.evaluate(ir,answer.get('assignments',{}))
    else:answer['evaluation']=core.evaluate(ir)
    return answer


def z3_solve(ir):
    import z3
    forms=core.affine(ir);variables=ir['model']['variables']; nodes={n['id']:n for n in ir['model']['nodes']}
    symbols={name:(z3.Int(name) if v['domain']=='integer' else z3.Real(name)) for name,v in variables.items()}
    def q(value):return z3.RealVal(str(value.numerator)+'/'+str(value.denominator))
    def term(ident):
        constant,coefficients=forms[ident]
        return q(constant)+sum((q(c)*symbols[name] for name,c in coefficients.items()),z3.RealVal(0))
    solver=z3.Solver();solver.set(timeout=2500,rlimit=150000)
    for name,v in variables.items():
        if 'value' in v:solver.add(symbols[name]==q(rational(v['value'])))
        if 'lower' in v:solver.add(symbols[name]>=q(rational(v['lower'])))
        if 'upper' in v:solver.add(symbols[name]<=q(rational(v['upper'])))
    for ident in ir['model']['constraints']:
        x=term(ident);op=nodes[ident]['op']
        solver.add({'eq':lambda:x==0,'ne':lambda:x!=0,'lt':lambda:x<0,'le':lambda:x<=0,'gt':lambda:x>0,'ge':lambda:x>=0}[op]())
    for guard in ir['domain_conditions']:solver.add(term(guard['denominator'])!=0)
    state=solver.check()
    if state==z3.unsat:return {'state':'INFEASIBLE','fragment':'QF_LIRA'}
    if state!=z3.sat:return {'state':'UNKNOWN','reason':solver.reason_unknown(),'fragment':'QF_LIRA'}
    model=solver.model();assignments={}
    for name,symbol in symbols.items():
        value=model.eval(symbol,model_completion=True)
        if z3.is_int_value(value):assignments[name]=str(value.as_long())
        elif z3.is_rational_value(value):assignments[name]=str(Fraction(value.numerator_as_long(),value.denominator_as_long()))
        else:return {'state':'UNKNOWN','reason':'NON_RATIONAL_WITNESS'}
    return {'state':'FEASIBLE','assignments':assignments,'fragment':'QF_LIRA','meaning':'One witness satisfies this model; it is not a universal guarantee'}


def sympy_solve(ir):
    import sympy as s
    variables=ir['model']['variables'];symbols={name:s.Symbol(name,real=True) for name in variables};terms={}
    def q(value):return s.Rational(value.numerator,value.denominator)
    for n in ir['model']['nodes']:
        op=n['op']
        if op=='quantity':x=q(rational(n['value'])*unit_spec(n['unit'])[1])
        elif op=='variable':
            v=variables[n['name']];x=(q(rational(v['value'])) if 'value' in v else symbols[n['name']])*q(unit_spec(v['unit'])[1])
        elif op=='neg':x=-terms[n['argument']]
        elif op=='power':x=terms[n['argument']]**n['exponent']
        else:
            a,b=terms[n['left']],terms[n['right']]
            if op=='add':x=a+b
            elif op=='sub':x=a-b
            elif op=='mul':x=a*b
            elif op=='div':x=a/b
            else:x={'eq':s.Eq,'ne':s.Ne,'lt':s.Lt,'le':s.Le,'gt':s.Gt,'ge':s.Ge}[op](a,b)
        terms[n['id']]=x
    normalized={i:str(s.cancel(terms[i]))[:4000] if ir['signatures'][i]['kind']=='quantity' else str(terms[i])[:4000] for i in ir['model']['outputs']}
    initial=core.evaluate(ir)
    if not initial.get('missing'):
        return {'state':initial['state'],'assignments':{},'symbolic_outputs':normalized}
    nodes={n['id']:n for n in ir['model']['nodes']};equations=[]
    for ident in ir['model']['constraints']:
        node=nodes[ident]
        if node['op']!='eq':return {'state':'UNSUPPORTED','reason':'SymPy solve profile admits linear equalities; use Z3 for inequalities','symbolic_outputs':normalized}
        equations.append(terms[node['left']]-terms[node['right']])
    unknown=[name for name,v in variables.items() if 'value' not in v]
    if not equations:return {'state':'UNKNOWN','reason':'SYMBOLIC_OUTPUT_WITH_FREE_VARIABLES','symbolic_outputs':normalized}
    solution=s.linsolve(equations,[symbols[name] for name in unknown])
    if solution is s.EmptySet or solution==s.EmptySet:return {'state':'INFEASIBLE','symbolic_outputs':normalized}
    values=list(solution)
    if len(values)!=1 or any(not value.is_Rational for value in values[0]):
        return {'state':'UNKNOWN','reason':'UNDERDETERMINED_LINEAR_EQUALITIES','symbolic_outputs':normalized}
    assignments={name:str(Fraction(int(value.p),int(value.q))) for name,value in zip(unknown,values[0])}
    if not core.witness_check(ir,assignments):return {'state':'INFEASIBLE','reason':'Unique linear solution violates declared domain','symbolic_outputs':normalized}
    return {'state':'FEASIBLE','assignments':assignments,'symbolic_outputs':normalized,'meaning':'Unique solution of the admitted equalities, checked against original domain conditions'}


def worker():
    # A fixed trusted adapter, not the user-program experiment runner of I03.
    if os.name=='posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(3,3));resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
    request=json.loads(sys.stdin.read(65537));ir=core.validate(request['model'])
    try:result=z3_solve(ir) if request['backend']=='Z3' else sympy_solve(ir)
    except core.MathError as exc:result={'state':exc.code,'reason':str(exc)}
    except (ValueError,TypeError,ZeroDivisionError,NotImplementedError) as exc:result={'state':'UNKNOWN','reason':type(exc).__name__}
    print(json.dumps(result))


if __name__=='__main__':worker()
