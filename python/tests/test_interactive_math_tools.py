import unittest

from input_suggestions import suggest_expression
from math_extensions import (
    analyze_function_properties,
    analyze_singularity_and_breakpoints,
    build_error_profile,
    build_convergence_table,
    build_piecewise_expression,
    compute_arc_length,
    compute_area_breakdown,
    compute_average_value,
    compute_double_integral,
    compute_fourier_series,
    compute_laplace_transform,
    compute_parameter_sensitivity,
    compute_polar_area,
    compute_polar_double_integral,
    compute_revolution_volume,
    compute_taylor_expansion,
    compute_triple_integral,
    compute_variable_double_integral,
    convergence_report,
    integration_by_parts_helper,
    parameter_assignment,
    solve_simple_ode,
    substitution_integral_helper,
    verify_antiderivative,
)
from step_explainer import STEPS_UNAVAILABLE_MESSAGE, build_steps_for_record


class InteractiveMathToolsTests(unittest.TestCase):
    def test_input_suggestions_fix_common_missing_parentheses(self):
        self.assertIn("sin(x)", suggest_expression("sinx"))
        self.assertIn("exp(x)", suggest_expression("e^x"))
        self.assertIn("x^2", suggest_expression("x2"))

    def test_polar_area_template_computes_circle_area(self):
        result = compute_polar_area("2*cos(theta)", "-pi/2", "pi/2")

        self.assertEqual(result["exact"], "π")
        self.assertAlmostEqual(result["numeric"], 3.141592653589793, places=10)

    def test_taylor_expansion_for_sine(self):
        result = compute_taylor_expansion("sin(x)", "0", "3")

        self.assertIn("x^3/6", result["polynomial"])

    def test_convergence_table_errors_shrink_for_trapezoid(self):
        table = build_convergence_table("x^2", "0", "1", "Trapezoidal", "10,100")

        self.assertEqual(len(table["rows"]), 2)
        self.assertLess(table["rows"][1]["absolute_error"], table["rows"][0]["absolute_error"])

    def test_singularity_and_function_analysis(self):
        singular = analyze_singularity_and_breakpoints("1/(x-1)", "0", "2")
        props = analyze_function_properties("x^2-1", "-2", "2")

        self.assertEqual(singular["singularities"], [1.0])
        self.assertEqual(props["roots"], [-1.0, 1.0])
        self.assertEqual(props["critical_points"], [0.0])

    def test_piecewise_builder_outputs_solving_piecewise(self):
        expression = build_piecewise_expression([("x", "x < 0"), ("x^2", "True")])

        self.assertEqual(expression, "Piecewise((x, x < 0), (x^2, True))")

    def test_parameter_assignment_for_slider(self):
        self.assertEqual(parameter_assignment("a", 2.5), "a=2.5")

    def test_antiderivative_verification(self):
        verification = verify_antiderivative("sin(x)", "-cos(x)")

        self.assertTrue(verification["ok"])
        self.assertEqual(verification["difference"], "0")

    def test_average_area_substitution_and_parts_helpers(self):
        average = compute_average_value("x", "0", "2")
        area = compute_area_breakdown("x", "-1", "1")
        substitution = substitution_integral_helper("2*x*cos(x^2)", "u=x^2")
        by_parts = integration_by_parts_helper("x", "exp(x)")

        self.assertEqual(average["average"], "1")
        self.assertAlmostEqual(area["absolute"], 1.0, places=10)
        self.assertEqual(substitution["transformed_integrand"], "cos(u)")
        self.assertIn("(x - 1)*e^(x)", by_parts["result"])

    def test_arc_length_and_revolution_volume(self):
        arc = compute_arc_length("x", "0", "1")
        volume = compute_revolution_volume("x", "0", "1")

        self.assertEqual(arc["exact"], "sqrt(2)")
        self.assertEqual(volume["exact"], "π/3")

    def test_fourier_laplace_and_ode_tools(self):
        fourier = compute_fourier_series("x", "2*pi", "3")
        laplace = compute_laplace_transform("exp(-x)")
        ode = solve_simple_ode("y' = x*y")

        self.assertIn("sin(x)", fourier["series"])
        self.assertEqual(laplace["transform"], "1/(s + 1)")
        self.assertIn("e^(x^2/2)", ode["solution"])

    def test_convergence_report_handles_improper_integral(self):
        report = convergence_report("exp(-x)", "0", "inf", timeout=0)

        self.assertEqual(report["status"], "convergent")
        self.assertIn("Exact value", report["summary"])

    def test_error_profile_contains_method_errors(self):
        profile = build_error_profile("x^2", "0", "1")

        methods = {row["method"] for row in profile["rows"]}
        self.assertIn("Simpson", methods)
        self.assertAlmostEqual(profile["reference"], 1 / 3, places=10)

    def test_double_integral_over_unit_square(self):
        result = compute_double_integral("x + y", "0", "1", "0", "1")

        self.assertEqual(result["exact"], "1")
        self.assertAlmostEqual(result["numeric"], 1.0, places=10)

    def test_multiple_integral_expansions(self):
        variable_double = compute_variable_double_integral("1", "0", "1", "0", "x")
        polar_double = compute_polar_double_integral("1", "0", "1", "0", "2*pi")
        triple = compute_triple_integral("1", "0", "1", "0", "1", "0", "1")

        self.assertEqual(variable_double["exact"], "1/2")
        self.assertEqual(polar_double["exact"], "π")
        self.assertEqual(triple["exact"], "1")

    def test_parameter_sensitivity_values(self):
        rows = compute_parameter_sensitivity("a*x", "a", "1,2", "0", "1")

        self.assertEqual([row["integral"] for row in rows], ["1/2", "1"])

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
            "type": "symbolic_indefinite",
            "func": "exp(x)*sin(x^2)",
            "resolved_func": "exp(x)*sin(x**2)",
            "shown_func": "exp(x)*sin(x^2)",
            "raw": "No closed-form",
        })

        self.assertEqual(steps, STEPS_UNAVAILABLE_MESSAGE)


if __name__ == "__main__":
    unittest.main()
