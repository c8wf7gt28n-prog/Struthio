"""On demand: the SymPy and Z3 solvers in their child worker (python -m workbench.math_backend _worker), with an independent
witness re-check of every answer. Needs requirements-math.txt (sympy and z3-solver); outside the release check's focused set
because it starts a process. Run it by hand: python3 -m unittest -v tests_integrated.test_exact_math_solvers"""
import importlib.util,unittest
from workbench import math_model as m,math_backend as b

MISSING=[name for name in ('sympy','z3') if importlib.util.find_spec(name) is None]


@unittest.skipIf(MISSING,'needs requirements-math.txt: '+', '.join(MISSING)+' not installed')
class Solvers(unittest.TestCase):
    def test_symbolic_reading_keeps_a_missing_denominator_unknown_with_its_domain_condition(self):
        unknown=m.compile_expression('x / x',{'x':{'unit':'1'}})
        symbolic=b.solve(unknown,'SYMPY')
        self.assertEqual(symbolic['state'],'UNKNOWN');self.assertTrue(symbolic['domain_conditions'])

    def test_actual_solvers_and_independent_witness_check(self):
        ir=m.compile_expression('x + 2 == 5',{'x':{'unit':'1'}})
        for name in ('SYMPY','Z3'):
            result=b.solve(ir,name);self.assertEqual(result['state'],'FEASIBLE',result);self.assertEqual(result['assignments']['x'],'3')
            self.assertEqual(result['witness_check'],'EXACT_IR_RECHECKED')
        impossible=m.compile_expression('x > 1',{'x':{'unit':'1','upper':'1'}})
        self.assertEqual(b.solve(impossible,'Z3')['state'],'INFEASIBLE')
        known=m.compile_expression('x == 2',{'x':{'unit':'1','value':'1'}})
        self.assertFalse(m.witness_check(known,{'x':'2'}))



if __name__=='__main__':unittest.main()
