import unittest

from export_utils import build_latex_export, build_markdown_export
from interval_utils import build_subintervals, find_piecewise_breakpoints
from numeric_methods import build_numeric_callable
from parameter_utils import (
    display_function_with_parameters,
    resolve_function_text,
)
from parser_utils import evaluate_symbolic_function
from tab2_logic import (
    compare_numerical_methods,
    compute_segmented_numerical_integral,
    prepare_tab2_inputs,
    run_tab2_calculation,
)


class MathFeatureTests(unittest.TestCase):
    def test_parameterized_function_resolves_before_integration(self):
        resolved = resolve_function_text("a*x^2 + b", "a=2, b=1")
        self.assertEqual(resolved, "2*x**2 + 1")
        self.assertEqual(
            display_function_with_parameters("a*x^2 + b", "a=2, b=1"),
            "a*x^2 + b [a=2, b=1]",
        )

        inputs = prepare_tab2_inputs(
            resolved,
            "Numerical Integration",
            "Simpson",
            "0",
            "1",
            "",
            shown_func="a*x^2 + b [a=2, b=1]",
            input_func="a*x^2 + b",
            params_text="a=2, b=1",
        )
        events = []
        run_tab2_calculation(inputs, events.append)
        self.assertEqual(events[-1][0], "numeric_result")
        self.assertAlmostEqual(events[-1][1], 5 / 3, places=10)

    def test_manual_split_integrates_each_segment(self):
        expr = evaluate_symbolic_function("x")
        func = build_numeric_callable(expr)
        result, error, segments = compute_segmented_numerical_integral(
            expr,
            "Trapezoidal",
            func,
            -1,
            1,
            split_text="0",
        )
        self.assertAlmostEqual(result, 0.0, places=10)
        self.assertIsNone(error)
        self.assertEqual(len(segments), 2)

    def test_piecewise_breakpoint_is_detected_automatically(self):
        expr = evaluate_symbolic_function("Piecewise((x, x < 0), (x^2, True))")
        func = build_numeric_callable(expr)
        result, _, segments = compute_segmented_numerical_integral(
            expr,
            "Adaptive Simpson",
            func,
            -1,
            1,
        )
        self.assertEqual(find_piecewise_breakpoints(expr, -1, 1), [0.0])
        self.assertAlmostEqual(result, -1 / 6, places=8)
        self.assertEqual(len(segments), 2)

    def test_reverse_interval_keeps_split_point_order(self):
        self.assertEqual(build_subintervals(2, 0, [0.5, 1.5]), [(2.0, 1.5), (1.5, 0.5), (0.5, 0.0)])

    def test_method_comparison_and_export(self):
        inputs = prepare_tab2_inputs("x^2", "Numerical Integration", "Simpson", "0", "1", "")
        rows = compare_numerical_methods(inputs)
        self.assertEqual(len(rows), 8)
        self.assertTrue(any(row["method"] == "Simpson" and row["status"] == "ok" for row in rows))

        record = {
            "func": "x^2",
            "resolved_func": "x**2",
            "shown_func": "x^2",
            "lower": "0",
            "upper": "1",
            "method": "Simpson",
            "raw": "1/3",
            "split_points": "0.5",
        }
        self.assertIn("Split points", build_markdown_export(record))
        self.assertIn(r"\int_{0}^{1}", build_latex_export(record))


if __name__ == "__main__":
    unittest.main()
