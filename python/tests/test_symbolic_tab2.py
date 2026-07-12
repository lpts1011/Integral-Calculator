import unittest

from symbolic_methods import compute_general_integral, compute_tab1_result
from tab2_logic import prepare_tab2_inputs, run_tab2_calculation


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

    def test_tab2_numeric_event_result(self):
        events = []
        inputs = prepare_tab2_inputs("x^2", "Numerical Integration", "Simpson", "0", "1", "")
        run_tab2_calculation(inputs, events.append)
        self.assertEqual(events[-1][0], "numeric_result")
        self.assertAlmostEqual(events[-1][1], 1 / 3, places=10)

    def test_tab2_symbolic_event_result(self):
        events = []
        inputs = prepare_tab2_inputs("x^2", "Symbolic Integration", "Trapezoidal", "0", "1", "")
        run_tab2_calculation(inputs, events.append)
        self.assertTrue(any(event[0] == "symbolic_result" and event[1] == "1/3" for event in events))


if __name__ == "__main__":
    unittest.main()
