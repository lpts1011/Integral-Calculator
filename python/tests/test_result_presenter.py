import unittest

from result_presenter import (
    build_result_summary,
    build_symbolic_steps,
    supports_symbolic_steps,
)


class ResultPresenterTests(unittest.TestCase):
    def test_definite_summary_separates_exact_numeric_and_time(self):
        summary = build_result_summary({
            "type": "definite",
            "raw": "1/3",
            "raw_type": "exact",
            "numeric_value": 1 / 3,
            "elapsed": 0.125,
        })
        self.assertEqual(summary["exact"]["latex"], r"\frac{1}{3}")
        self.assertIn("0.333333", summary["result"]["latex"])
        self.assertEqual(summary["elapsed"], 0.125)
        self.assertEqual(summary["steps_state"], "loading")

    def test_numerical_summary_has_no_symbolic_steps(self):
        record = {
            "type": "numerical",
            "raw": 2.5,
            "elapsed": 0.02,
        }
        summary = build_result_summary(record)
        self.assertEqual(summary["exact"]["text_key"], "not_available")
        self.assertIn("2.5", summary["result"]["latex"])
        self.assertEqual(summary["steps_state"], "hidden")
        self.assertFalse(supports_symbolic_steps(record))

    def test_definite_symbolic_steps_are_renderable_formulas(self):
        steps = build_symbolic_steps({
            "type": "definite",
            "raw": "1/3",
            "raw_type": "exact",
            "func": "x^2",
            "resolved_func": "x^2",
            "lower": "0",
            "upper": "1",
        })
        self.assertEqual(
            [step["key"] for step in steps],
            [
                "step_setup",
                "step_antiderivative",
                "step_bounds",
                "step_substitute",
                "step_simplify",
            ],
        )
        self.assertIn(r"\frac{x^{3}}{3}", steps[1]["latex"])
        self.assertEqual(steps[-1]["latex"], r"= \frac{1}{3}")

    def test_indefinite_steps_include_derivative_verification(self):
        steps = build_symbolic_steps({
            "type": "indefinite",
            "raw": "-cos(x)",
            "raw_type": "exact",
            "func": "sin(x)",
            "resolved_func": "sin(x)",
        })
        self.assertEqual(steps[-1]["key"], "step_verify")
        self.assertTrue(steps[-1]["latex"].endswith("=0"))

    def test_no_closed_form_does_not_request_steps(self):
        record = {
            "type": "symbolic",
            "raw": "No closed-form",
            "display": "no closed-form",
        }
        self.assertFalse(supports_symbolic_steps(record))
        self.assertEqual(build_symbolic_steps(record), [])

    def test_special_function_results_render_as_formulas(self):
        summary = build_result_summary({
            "type": "indefinite",
            "raw": "sqrt(2)*sqrt(pi)*fresnels(sqrt(2)*x/sqrt(pi))/2",
            "raw_type": "exact",
        })
        self.assertIn(r"\frac{\sqrt{2} \sqrt{\pi} S\left(", summary["exact"]["latex"])
        self.assertTrue(summary["exact"]["latex"].endswith("+ C"))

    def test_complicated_definite_value_is_shown_as_a_number(self):
        summary = build_result_summary({
            "type": "definite",
            "raw": "sqrt(2)*sqrt(pi)*fresnels(sqrt(2)/sqrt(pi))/2",
            "raw_type": "exact",
            "numeric_value": 0.3102683017233811,
        })
        self.assertEqual(summary["exact"], {"text_key": "exact_too_complex"})
        self.assertIn("0.310268301723", summary["result"]["latex"])

    def test_simple_definite_value_keeps_its_exact_form(self):
        summary = build_result_summary({
            "type": "definite", "raw": "pi/4", "raw_type": "exact", "numeric_value": 0.785398,
        })
        self.assertEqual(summary["exact"]["latex"], r"\frac{\pi}{4}")


if __name__ == "__main__":
    unittest.main()
