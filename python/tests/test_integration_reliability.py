import math
import threading
import time
import unittest
from unittest.mock import patch

import calengine as np
from integration_engine import NumericalConvergenceError, CalculationCancelled
from numeric_methods import build_numeric_callable,find_symbolic_singularities
from parser_utils import evaluate_symbolic_function
from tab2_logic import compute_segmented_numerical_integral,prepare_tab2_inputs,compare_numerical_methods
from plot_utils import _approx_zero_crossings
from result_presenter import build_result_summary


class IntegrationReliabilityTests(unittest.TestCase):
    def calculate(self,text,method="Auto",a=0.,b=1.,options=None,delta=None):
        expression=evaluate_symbolic_function(text)
        function=build_numeric_callable(expression)
        return compute_segmented_numerical_integral(expression,method,function,a,b,delta,options=options or {})

    def test_periodic_singularities_are_bounded(self):
        started=time.monotonic()
        self.assertEqual(find_symbolic_singularities(evaluate_symbolic_function("tan(x)"),-1,1),[])
        self.assertEqual(find_symbolic_singularities(evaluate_symbolic_function("1/sin(x)"),-1,1),[0.])
        self.assertLess(time.monotonic()-started,2.)
        points=find_symbolic_singularities(evaluate_symbolic_function("tan(x)"),-4,4)
        self.assertEqual(len(points),2)
        self.assertAlmostEqual(points[0],-math.pi/2)

    def test_romberg_does_not_accept_aliased_constant_samples(self):
        value,error,_=self.calculate("cos(512*pi*x)","Romberg")
        self.assertAlmostEqual(value,0.,places=8)
        self.assertLess(error,1e-8)

    def test_structural_narrow_peak_is_resolved(self):
        for method in ("Auto","Gaussian Quadrature","Adaptive Simpson"):
            with self.subTest(method=method):
                value,error,_=self.calculate("exp(-100000000*(x-0.12345)^2)",method,options={"epsabs":1e-10,"epsrel":1e-10})
                self.assertAlmostEqual(value,math.sqrt(math.pi)/10000,places=9)
                self.assertLess(error,1e-8)

    def test_auto_uses_weighted_oscillatory_quadrature(self):
        value,error,segments=self.calculate("sin(10000*x)")
        self.assertAlmostEqual(value,(1-math.cos(10000))/10000,places=13)
        self.assertEqual(segments[0]["diagnostics"]["method"],"Oscillatory Quadrature")
        self.assertLess(segments[0]["diagnostics"]["evaluations"],100)

    def test_oscillatory_phase_and_negative_frequency(self):
        for text,frequency,phase in [("sin(1000*x+0.3)",1000.,.3),("cos(-1000*x+0.2)",-1000.,.2)]:
            value,_,_=self.calculate(text)
            expected=(math.cos(phase)-math.cos(frequency+phase))/frequency if text.startswith("sin") else (math.sin(frequency+phase)-math.sin(phase))/frequency
            self.assertAlmostEqual(value,expected,places=11)

    def test_nonconvergence_is_not_reported_as_success(self):
        with self.assertRaises(NumericalConvergenceError):
            self.calculate("sin(10000*x)","Adaptive Gauss-Kronrod",options={"max_evaluations":500})

    def test_integrable_endpoint_singularities(self):
        for text,expected in [("1/sqrt(x)",2.),("log(x)",-1.)]:
            value,_,_=self.calculate(text)
            self.assertAlmostEqual(value,expected,places=10)

    def test_internal_divergent_pole_remains_rejected(self):
        with self.assertRaisesRegex(ValueError,"singularity"):
            self.calculate("1/(x-1/4)")

    def test_reversed_and_zero_bounds(self):
        value,_,_=self.calculate("exp(x)",a=1.,b=0.)
        self.assertAlmostEqual(value,1-math.e,places=10)
        self.assertEqual(self.calculate("x^2",a=1.,b=1.)[0],0.)

    def test_step_size_cannot_request_trillion_sample_allocation(self):
        with self.assertRaisesRegex(ValueError,"budget"):
            self.calculate("x^2","Trapezoidal",delta=1e-12)
        with self.assertRaises(ValueError):
            prepare_tab2_inputs("x","Simpson","0","1","inf")

    def test_cancel_and_time_budget(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(CalculationCancelled):
            self.calculate("x^2",options={"cancel":cancel})
        with self.assertRaises(NumericalConvergenceError):
            self.calculate("x^2",options={"max_seconds":1e-12})

    def test_tolerances_are_validated(self):
        for options in ({"epsabs":0},{"epsrel":float("inf")},{"max_evaluations":2}):
            with self.subTest(options=options),self.assertRaises(ValueError):
                self.calculate("x",options=options)

    def test_true_adaptive_simpson_and_gauss_kronrod_are_distinct(self):
        for method in ("Adaptive Simpson","Adaptive Gauss-Kronrod"):
            value,error,segments=self.calculate("exp(x)",method)
            self.assertAlmostEqual(value,math.e-1,places=8)
            self.assertEqual(segments[0]["diagnostics"]["method"],method)

    def test_segment_deterministic_estimates_are_added(self):
        expr=evaluate_symbolic_function("x")
        diagnostics={"evaluations":10,"error_kind":"estimated_absolute_error","status":"converged"}
        with patch("tab2_logic.compute_numerical_integral",side_effect=[(.1,.2,diagnostics),(.2,.3,diagnostics)]):
            _,error,_=compute_segmented_numerical_integral(expr,"Adaptive Gauss-Kronrod",build_numeric_callable(expr),0,1,split_text="0.5",options={})
        self.assertAlmostEqual(error,.5)

    def test_seeded_monte_carlo_is_reproducible_and_accounts_for_samples(self):
        one=self.calculate("exp(x)","Monte Carlo",options={"seed":7,"intervals":1001})
        two=self.calculate("exp(x)","Monte Carlo",options={"seed":7,"intervals":1001})
        self.assertEqual(one[:2],two[:2])
        self.assertEqual(one[2][0]["diagnostics"]["evaluations"],1001)
        self.assertEqual(one[2][0]["diagnostics"]["error_kind"],"standard_error")

    def test_graph_does_not_call_a_pole_a_zero(self):
        xs=np.linspace(0,1,500);expr=evaluate_symbolic_function("1/(x-1/4)")
        f=build_numeric_callable(expr)
        self.assertEqual(_approx_zero_crossings(xs,f(xs),function=f),[])
        self.assertEqual(_approx_zero_crossings(xs,f(xs)),[])

    def test_rendered_summary_carries_uncertainty_and_status(self):
        result=build_result_summary({"type":"numerical","raw":1.,"error":1e-7,
            "diagnostics":{"method":"Auto","status":"converged","evaluations":21,"error_kind":"estimated_absolute_error"}})["result"]
        self.assertIn("\\pm",result["latex"])
        self.assertIn("21 evaluations",result["detail"])

    def test_comparison_uses_independent_reference_and_repeated_timing(self):
        inputs=prepare_tab2_inputs("x^2","Auto","0","1",options={"repeats":2})
        rows=compare_numerical_methods(inputs)
        successful=[row for row in rows if row["status"]=="ok"]
        self.assertTrue(successful)
        for row in successful:
            self.assertEqual(row["repeats"],2)
            self.assertAlmostEqual(row["reference"],1/3,places=12)
            self.assertLessEqual(row["actual_error"],1e-8)


if __name__=="__main__":unittest.main()
