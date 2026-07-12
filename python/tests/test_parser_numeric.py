import math
import unittest

from numeric_methods import build_numeric_callable, compute_numerical_integral
from parser_utils import evaluate_symbolic_function, parse_input_to_float, parse_input_to_solving


class ParserNumericTests(unittest.TestCase):
    def test_parse_constants_and_implicit_multiplication(self):
        self.assertAlmostEqual(parse_input_to_float("pi"), math.pi)
        self.assertEqual(str(parse_input_to_solving("2pi")), "2*pi")

    def test_reject_unknown_variables_in_function(self):
        with self.assertRaises(ValueError):
            evaluate_symbolic_function("x + y")

    def test_simpson_integrates_quadratic(self):
        expr = evaluate_symbolic_function("x^2")
        func = build_numeric_callable(expr)
        result, error = compute_numerical_integral("Simpson", func, 0.0, 1.0)
        self.assertAlmostEqual(result, 1 / 3, places=10)
        self.assertIsNone(error)

    def test_constant_function_broadcasts_for_arrays(self):
        expr = evaluate_symbolic_function("5")
        func = build_numeric_callable(expr)
        result, _ = compute_numerical_integral("Trapezoidal", func, 0.0, 2.0)
        self.assertAlmostEqual(result, 10.0, places=8)


if __name__ == "__main__":
    unittest.main()
