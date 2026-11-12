"""Exact maths: units and dimensions, missing versus zero denominators, executable text refused before any backend, sweeps
that break at undefined samples with exact boundaries, and math.prepare/run bound to its source with read-only authority.
No solver process starts here; the SymPy and Z3 solvers are tested on demand in test_exact_math_solvers (requirements-math.txt)."""
from fractions import Fraction
import unittest
from unittest.mock import patch
from workbench import math_model as m,math_backend as b
from workbench.stac.quantities import Quantity,DimensionError
from workbench.math_units import unit_spec
from tests_integrated import test_problem as fixtures  # run per module from the program root
from workbench.problem_checks import bound
from workbench.engineering_kernel import Principal,operator


class ExactMath(unittest.TestCase):
    def test_memory_decimal_binary_and_compound_units(self):
        self.assertEqual(Quantity('1','MiB').converted('MB').value,Quantity('1.048576','MB').value)
        self.assertEqual(Quantity('1000','ms').compare(Quantity('1','s')),0)
        self.assertEqual(Quantity('1','W').compare(Quantity('1','V*A')),0)
        self.assertEqual(unit_spec('MiB/s')[1],Fraction(1048576))
        with self.assertRaises(DimensionError):Quantity('1','MiB').converted('W')
        with self.assertRaises(ValueError):unit_spec('KB')

    def test_missing_and_zero_denominator_remain_distinct(self):
        unknown=m.compile_expression('x / x',{'x':{'unit':'1'}})
        self.assertEqual(m.evaluate(unknown)['state'],'UNKNOWN');self.assertTrue(unknown['domain_conditions'])
        self.assertEqual(m.evaluate(unknown,{'x':'0'})['state'],'DOMAIN_ERROR')  # the SymPy reading is in test_exact_math_solvers

    def test_dimension_errors_and_executable_text_never_reach_backend(self):
        with self.assertRaises(m.MathError):m.compile_expression('v + i',{'v':{'unit':'V'},'i':{'unit':'A'}})
        for expression in ['__import__("os").system("id")','x.__class__','x[0]','[x for x in y]']:
            with self.assertRaises(m.MathError):m.compile_expression(expression,{'x':{'unit':'1'}})
        ir=m.compile_expression('x * x > 1',{'x':{'unit':'1'}})
        with patch.object(b.subprocess,'run') as process:
            result=b.solve(ir,'Z3');self.assertEqual(result['state'],'UNSUPPORTED');process.assert_not_called()

    def test_graph_breaks_at_undefined_samples_and_boundary_is_exact(self):
        ir=m.compile_expression('1 / x',{'x':{'unit':'1','value':'1'}})
        result=m.sweep(ir,'x','-1','1',3)
        self.assertEqual(result['samples'][1]['state'],'DOMAIN_ERROR');self.assertIsNone(result['samples'][1]['value'])
        ir=m.compile_expression('a + b + w <= cap',{'a':{'unit':'MiB','value':'6'},'b':{'unit':'MiB','value':'6'},'w':{'unit':'MiB','value':'5'},'cap':{'unit':'MiB','value':'16'}})
        self.assertEqual(m.sweep(ir,'w','0','10',3)['boundaries'][0]['input']['rational'],'4')


class MathematicalBindings(fixtures.ProblemBindings):
    # Reuse the existing disposable-copy fixture, not its test methods.
    def test_math_is_source_bound_and_cannot_expand_read_only_authority(self):
        args={**bound(self.problem),'expression':'voltage * assumed_typical_current','assumptions':['Typical-current model.'],'output_unit':'W'}
        action=self.call('math.prepare',args);old=self.call('math.run',{'action':action['id']})['receipt']
        self.assertEqual(old['snapshot']['outputs'][0]['value']['rational'],'5/4')
        self.assertTrue(self.call('math.run',{'action':action['id']})['replayed'])
        pending=self.call('math.prepare',args)
        work=self.root/'Files'/self.copy['work']/'power.csv';work.write_text(work.read_text().replace('120','125'))
        self.assertFalse(self.kernel.dispatch('math.run',{'action':pending['id']},self.p)['ok'])
        self.assertEqual(self.call('math.get',{'id':action['id']})['receipt'],old)
        self.assertFalse(self.kernel.dispatch('math.prepare',args,Principal(self.p.identity))['ok'])
        self.assertFalse(self.kernel.dispatch('math.get',{'id':action['id']},operator('another-owner'))['ok'])

    def test_interval_placeholder_cannot_be_silently_treated_as_a_scalar(self):
        model=m.compile_expression('lifetime_A + lifetime_A',{'lifetime_A':{'unit':'s'}})['model']
        response=self.kernel.dispatch('math.prepare',{**bound(self.problem),'model':model},self.p)
        self.assertFalse(response['ok']);self.assertIn('scalar quantity',response['error']['message'])


# Only the binding tests above run here; the fixture's own tests run in test_problem.
for name in tuple(vars(fixtures.ProblemBindings)):
    if name.startswith('test_'):setattr(MathematicalBindings,name,None)


if __name__=='__main__':unittest.main()
