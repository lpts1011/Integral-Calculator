import unittest

from symbolic_methods import compute_general_integral, compute_tab1_result
from tab2_logic import prepare_tab2_inputs, run_numerical_integration


class SymbolicTab2Tests(unittest.TestCase):
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
