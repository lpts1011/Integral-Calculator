import unittest
import math

from math_extensions import (
    compute_arc_length,
    compute_area_breakdown,
    compute_polar_area,
    compute_revolution_volume,
    convergence_report,
    integration_by_parts_helper,
    substitution_integral_helper,
    verify_antiderivative,
)
from step_explainer import STEPS_UNAVAILABLE_MESSAGE, build_steps_for_record


class InteractiveMathToolsTests(unittest.TestCase):
    def test_reversed_limits_preserve_geometric_measures(self):
        for function in ("x", "x+2", "x-2"):
            with self.subTest(function=function):
                forward = compute_area_breakdown(function, "-1", "1")
                reverse = compute_area_breakdown(function, "1", "-1")
                self.assertAlmostEqual(reverse["signed"], -forward["signed"])
                for key in ("absolute", "positive_area", "negative_area", "negative_signed"):
                    self.assertAlmostEqual(reverse[key], forward[key])
        # A zero signed integral must not come back as -0.0 and show "-0".
        self.assertEqual(math.copysign(1, compute_area_breakdown("x", "1", "-1")["signed"]), 1)
        self.assertAlmostEqual(compute_arc_length("x", "1", "0")["numeric"], math.sqrt(2))
        self.assertAlmostEqual(compute_polar_area("1", "2*pi", "0")["numeric"], math.pi)
        self.assertAlmostEqual(compute_revolution_volume("x", "1", "0")["numeric"], math.pi/3)
        self.assertAlmostEqual(compute_revolution_volume("x", "1", "0", "y")["numeric"], 2*math.pi/3)

    def test_y_axis_shells_are_never_negative(self):
        # The region between y = f(x) and the x-axis; shells below the axis
        # used to subtract volume (rotating y = -x on [0, 1] gave -2π/3).
        cases = (
            ("-x", "0", "1", "2*π/3", 2*math.pi/3),
            ("x", "-1", "0", "2*π/3", 2*math.pi/3),
            ("x-1", "0", "2", "2*π", 2*math.pi),
            ("sin(x)", "0", "2*pi", "8*π^2", 8*math.pi**2),
        )
        for function, lower, upper, exact, value in cases:
            with self.subTest(function=function, lower=lower, upper=upper):
                volume = compute_revolution_volume(function, lower, upper, "y")
                self.assertEqual(volume["exact"], exact)
                self.assertAlmostEqual(volume["numeric"], value, places=9)
                self.assertIsNone(volume["note"])

    def test_y_axis_shells_from_both_sides_are_counted_once(self):
        # Both sides of the y-axis sweep the same shells; the old formula
        # cancelled them (x^2 on [-1, 1] gave 0) or added them twice.
        cases = (
            ("x^2", "-1", "1", "π/2", math.pi/2),
            ("x^2", "-1", "2", "8*π", 8*math.pi),
            ("x^3", "-1", "1", "4*π/5", 4*math.pi/5),
            ("x-1", "-1", "2", "10*π/3", 10*math.pi/3),
            ("sin(x)", "-pi", "pi", "4*π^2", 4*math.pi**2),
        )
        for function, lower, upper, exact, value in cases:
            with self.subTest(function=function, lower=lower, upper=upper):
                volume = compute_revolution_volume(function, lower, upper, "y")
                self.assertEqual(volume["exact"], exact)
                self.assertAlmostEqual(volume["numeric"], value, places=9)
                self.assertIn("both sides", volume["note"])

    def test_y_axis_volume_without_closed_form_uses_checked_engine(self):
        # 2π∫₀³ x|cos(x) - x/2| dx; |·| has a kink at a transcendental root.
        volume = compute_revolution_volume("cos(x)-x/2", "0", "3", "y")
        self.assertIsNone(volume["exact"])
        self.assertAlmostEqual(volume["numeric"], 40.8285388152, places=6)

    def test_area_resolves_narrow_peaks(self):
        area = compute_area_breakdown("exp(-1000000*(x-0.12345)^2)", "0", "1")
        expected = math.sqrt(math.pi)/1000
        self.assertAlmostEqual(area["signed"], expected, places=11)
        self.assertAlmostEqual(area["absolute"], expected, places=11)

    def test_area_handles_integrable_endpoints_and_rejects_poles(self):
        self.assertAlmostEqual(compute_area_breakdown("1/sqrt(x)", "0", "1")["absolute"], 2.0)
        with self.assertRaises(ValueError):
            compute_area_breakdown("1/x", "-1", "1")

    def test_polar_area_template_computes_circle_area(self):
        result = compute_polar_area("2*cos(theta)", "-pi/2", "pi/2")

        self.assertEqual(result["exact"], "π")
        self.assertAlmostEqual(result["numeric"], 3.141592653589793, places=10)

    def test_antiderivative_verification(self):
        verification = verify_antiderivative("sin(x)", "-cos(x)")

        self.assertTrue(verification["ok"])
        self.assertEqual(verification["difference"], "0")

    def test_area_substitution_and_parts_helpers(self):
        area = compute_area_breakdown("x", "-1", "1")
        substitution = substitution_integral_helper("2*x*cos(x^2)", "u=x^2")
        by_parts = integration_by_parts_helper("x", "exp(x)")

        self.assertAlmostEqual(area["absolute"], 1.0, places=10)
        self.assertEqual(substitution["transformed_integrand"], "cos(u)")
        self.assertEqual(substitution["x_of_u"], "sqrt(u)")
        self.assertIn("(x - 1)*e^(x)", by_parts["result"])

    def test_arc_length_and_revolution_volume(self):
        arc = compute_arc_length("x", "0", "1")
        volume = compute_revolution_volume("x", "0", "1")

        self.assertEqual(arc["exact"], "sqrt(2)")
        self.assertEqual(volume["exact"], "π/3")
        self.assertEqual(volume["latex"]["exact"], r"\frac{\pi}{3}")

    def test_arc_length_without_closed_form_returns_only_a_number(self):
        arc = compute_arc_length("sin(x)", "0", "pi")

        self.assertIsNone(arc["exact"])
        self.assertIsNone(arc["latex"]["exact"])
        self.assertAlmostEqual(arc["numeric"], 3.8201977890, places=8)

    def test_convergence_report_handles_improper_integral(self):
        report = convergence_report("exp(-x)", "0", "inf", timeout=0)

        self.assertEqual(report["status"], "convergent")
        self.assertIn("Exact value", report["summary"])

    def test_steps_for_definite_record_are_click_generated(self):
        steps = build_steps_for_record({
            "type": "definite",
            "func": "x^2",
            "resolved_func": "x**2",
            "shown_func": "x^2",
            "lower": "0",
            "upper": "1",
            "raw": "1/3",
        })

        self.assertIn("Definite Integral Steps", steps)
        self.assertIn("Antiderivative", steps)

    def test_steps_show_na_for_unevaluated_symbolic_results(self):
        steps = build_steps_for_record({
            "type": "definite",
            "func": "sin(x^2)*exp(x)",
            "resolved_func": "exp(x)*sin(x**2)",
            "shown_func": "sin(x^2)*e^x",
            "lower": "-0.35",
            "upper": "2*pi",
            "raw": "Integral(exp(x)*sin(x**2), (x, -0.35, 2*pi))",
            "raw_type": "unevaluated",
        })

        self.assertEqual(steps, STEPS_UNAVAILABLE_MESSAGE)

    def test_steps_show_na_for_no_closed_form_records(self):
        steps = build_steps_for_record({
            "type": "indefinite",
            "func": "exp(x)*sin(x^2)",
            "resolved_func": "exp(x)*sin(x**2)",
            "shown_func": "exp(x)*sin(x^2)",
            "raw": "Integral(exp(x)*sin(x**2), x)",
            "raw_type": "unevaluated",
        })

        self.assertEqual(steps, STEPS_UNAVAILABLE_MESSAGE)


if __name__ == "__main__":
    unittest.main()
