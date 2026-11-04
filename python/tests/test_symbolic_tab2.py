import unittest
import math
import threading

from symbolic_methods import compute_general_integral, compute_tab1_result, numerical_fallback
from tab2_logic import prepare_tab2_inputs, run_numerical_integration


class SymbolicTab2Tests(unittest.TestCase):
    def test_fallback_resolves_narrow_peak_and_reversed_limits(self):
        expression = "exp(-1000000*(x-0.12345)^2)"
        for lower, upper, sign in (("0", "1", 1), ("1", "0", -1)):
            value, error = numerical_fallback(expression, lower, upper)
            self.assertAlmostEqual(value, sign*math.sqrt(math.pi)/1000, places=11)
            self.assertLess(error, 1e-8)

    def test_fallback_handles_endpoints_piecewise_and_rejects_divergence(self):
        self.assertAlmostEqual(numerical_fallback("1/sqrt(x)", "0", "1")[0], 2.0)
        value, _ = numerical_fallback("Piecewise((1, x < 0.12345), (2, True))", "0", "1")
        self.assertAlmostEqual(value, 2-0.12345, places=11)
        for expression, lower, upper in (("1/x", "-1", "1"), ("1/x", "0", "1"), ("1/x", "1", "inf")):
            with self.subTest(expression=expression, lower=lower, upper=upper), self.assertRaises(ValueError):
                numerical_fallback(expression, lower, upper)
        # A divergent endpoint gets the same plain message as a divergent infinite limit.
        for upper in ("1", "inf"):
            lower = "0" if upper == "1" else "1"
            with self.subTest(upper=upper), self.assertRaisesRegex(ValueError, "may diverge"):
                numerical_fallback("1/x", lower, upper)

    def test_fallback_obeys_cancellation_for_finite_and_infinite_limits(self):
        cancel = threading.Event()
        cancel.set()
        for upper in ("1", "inf"):
            with self.subTest(upper=upper), self.assertRaisesRegex(ValueError, "cancelled"):
                numerical_fallback("exp(-x)", "0", upper, cancel=cancel)

    def test_tab1_definite_symbolic_direct(self):
        result = compute_tab1_result("x^2", "0", "1", timeout=0)
        self.assertEqual(result["kind"], "definite")
        self.assertEqual(result["display_str"], "1/3")

    def test_tab1_indefinite_symbolic_direct(self):
        result = compute_tab1_result("sin(x)", "", "", timeout=0)
        self.assertEqual(result["kind"], "indefinite")
        self.assertTrue(result["closed_form"])

    def test_improper_integral_direct(self):
        result = compute_general_integral("exp(-x)", "0", "inf", timeout=0)
        self.assertEqual(result["type"], "exact")

    def test_numerical_integration_result(self):
        value, _error, segments = run_numerical_integration(prepare_tab2_inputs("x^2", "Simpson", "0", "1"))
        self.assertAlmostEqual(value, 1 / 3, places=10)
        self.assertEqual(segments[0]["diagnostics"]["method"], "Simpson")

    def test_numerical_methods_reject_infinite_limits(self):
        with self.assertRaisesRegex(ValueError, "choose Auto"):
            prepare_tab2_inputs("exp(-x)", "Simpson", "0", "inf")


if __name__ == "__main__":
    unittest.main()
