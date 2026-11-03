import random
import unittest

import mpmath
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication, QWidget

from i18n import INSTRUCTIONS, ui_text
from numeric_methods import build_numeric_callable
from parameter_utils import resolve_function_text
from parser_utils import evaluate_symbolic_function, x_sym
from symbolic_methods import compute_general_integral, compute_tab1_result
from tab2_logic import compute_segmented_numerical_integral


class _Field:
    def __init__(self):
        self.value = ""

    def set_text(self, value):
        self.value = str(value)


class _MathPanel:
    def set_theme(self, _name):
        pass


class _ExampleCalculator(QWidget):
    history_record = Signal(object)
    plot_requested = Signal(str, float, float, object)
    plot_clear_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.math_panel = _MathPanel()
        self.function_text = ""
        self.parameter_text = ""
        self.method = "Auto"
        self.lower = _Field()
        self.upper = _Field()

    def get_function_text(self):
        return self.function_text

    def set_function_text(self, value):
        self.function_text = str(value)

    def set_parameter_text(self, value):
        self.parameter_text = str(value)
        return True

    def set_method(self, method):
        self.method = method

    def set_language(self, _text):
        pass

    def reset(self):
        pass


class _Plot(QWidget):
    def set_theme(self, _theme):
        pass

    def set_labels(self, _text):
        pass

    def plot_function(self, *_args):
        pass

    def clear(self):
        pass


class _Results(QWidget):
    def set_text(self, _text):
        pass

    def set_theme(self, _theme):
        pass

    def set_record(self, _record):
        pass

    def clear(self):
        pass

    def scroll_to_steps(self):
        pass


class UsabilityWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from qt_main_window import IntegralCalculatorWindow

        self.window = IntegralCalculatorWindow(
            tab_factory=_ExampleCalculator,
            plot_factory=_Plot,
            result_workspace_factory=_Results,
        )

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def test_primary_workspace_keeps_graph_history_and_actions_visible(self):
        self.window.show()
        QApplication.processEvents()
        self.assertFalse(self.window.right_panel.isHidden())
        self.assertFalse(self.window.plot_widget.isHidden())
        self.assertFalse(self.window.history_list.isHidden())
        self.assertFalse(self.window.steps_button.isHidden())
        self.assertFalse(self.window.math_tools_button.isHidden())
        self.assertFalse(hasattr(self.window, "suggest_button"))
        self.assertFalse(hasattr(self.window, "view_mode_combo"))
        self.assertFalse(hasattr(self.window, "graph_toggle_button"))
        self.assertFalse(hasattr(self.window, "history_toggle_button"))

    def test_example_gallery_fills_the_calculator(self):
        calculator = self.window.calculator
        dialog = self.window.show_examples()
        dialog.examples_list.setCurrentRow(2)
        dialog.apply_button.click()
        self.assertEqual(calculator.function_text, "sin(20*x)")
        self.assertEqual(calculator.method, "Adaptive Simpson")

        dialog = self.window.show_examples()
        dialog.examples_list.setCurrentRow(4)
        dialog.apply_button.click()
        self.assertEqual(calculator.function_text, "1/x^2")
        self.assertEqual(calculator.lower.value, "1")
        self.assertEqual(calculator.upper.value, "inf")
        self.assertEqual(calculator.method, "Auto")

    def test_both_languages_are_complete(self):
        self.assertEqual(list(INSTRUCTIONS), ["English", "中文（简体）"])
        english, chinese = ui_text("English"), ui_text("中文（简体）")
        self.assertEqual(set(english), set(chinese))
        for key, value in english.items():
            if key != "tool_text" and isinstance(value, str) and any(c.isalpha() for c in value):
                with self.subTest(key=key):
                    self.assertNotEqual(chinese[key], value)

        self.window.change_language("中文（简体）")
        self.assertEqual(self.window.examples_button.text(), "示例")


class MathematicalValidationTests(unittest.TestCase):
    def _numerical_result(self, expression, lower, upper, *, split_text=""):
        expr = evaluate_symbolic_function(expression)
        func = build_numeric_callable(expr)
        result, error, segments = compute_segmented_numerical_integral(
            expr,
            "Adaptive Simpson",
            func,
            lower,
            upper,
            split_text=split_text,
        )
        return result, error, segments

    def test_symbolic_antiderivatives_pass_derivative_verification(self):
        expressions = (
            "x^5 - 3*x^2 + 2",
            "exp(x)*sin(x)",
            "1/(1+x^2)",
            "sqrt(x)",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                result = compute_tab1_result(expression, "", "", timeout=0)
                self.assertTrue(result["closed_form"])
                antiderivative = evaluate_symbolic_function(result["raw_result"])
                original = evaluate_symbolic_function(expression)
                self.assertEqual((antiderivative.diff(x_sym) - original).simplify(), 0)

    def test_random_polynomials_match_exact_definite_integrals(self):
        rng = random.Random(20260723)
        for _ in range(12):
            coefficients = [rng.randint(-5, 5) for _ in range(rng.randint(2, 6))]
            expression = " + ".join(
                f"({coefficient})*x^{power}"
                for power, coefficient in enumerate(coefficients)
            )
            lower = rng.randint(-3, 0)
            upper = rng.randint(1, 4)
            expected = sum(
                coefficient
                * (upper ** (power + 1) - lower ** (power + 1))
                / (power + 1)
                for power, coefficient in enumerate(coefficients)
            )
            result = compute_tab1_result(
                expression,
                str(lower),
                str(upper),
                timeout=0,
            )
            self.assertAlmostEqual(float(result["numeric_value"]), expected, places=11)

    def test_numerical_results_match_high_precision_reference(self):
        cases = (
            ("exp(-x^2)", -3.0, 2.0, lambda x: mpmath.exp(-(x**2))),
            ("sin(40*x)", 0.0, float(mpmath.pi), lambda x: mpmath.sin(40 * x)),
            (
                "log(1+x)/(1+x^2)",
                0.0,
                2.0,
                lambda x: mpmath.log(1 + x) / (1 + x**2),
            ),
        )
        with mpmath.workdps(60):
            for expression, lower, upper, reference_function in cases:
                with self.subTest(expression=expression):
                    actual, _error, _segments = self._numerical_result(
                        expression,
                        lower,
                        upper,
                    )
                    expected = float(mpmath.quad(reference_function, [lower, upper]))
                    self.assertAlmostEqual(actual, expected, places=9)

    def test_piecewise_discontinuity_is_split_automatically(self):
        actual, _error, segments = self._numerical_result(
            "Piecewise((0, x < 0), (1, True))",
            -1,
            1,
        )
        self.assertAlmostEqual(actual, 1.0, places=10)
        self.assertEqual(
            [(segment["lower"], segment["upper"]) for segment in segments],
            [(-1.0, 0.0), (0.0, 1.0)],
        )

    def test_reversed_bounds_preserve_sign_against_high_precision_reference(self):
        actual, _error, segments = self._numerical_result("exp(-x^2)", 2, -1)
        with mpmath.workdps(60):
            expected = float(mpmath.quad(lambda x: mpmath.exp(-(x**2)), [2, -1]))
        self.assertAlmostEqual(actual, expected, places=9)
        self.assertEqual(segments[0]["lower"], 2.0)
        self.assertEqual(segments[-1]["upper"], -1.0)

    def test_internal_singularity_is_rejected_instead_of_returning_a_number(self):
        expr = evaluate_symbolic_function("1/(x-1/4)")
        func = build_numeric_callable(expr)
        with self.assertRaisesRegex(ValueError, "singularity"):
            compute_segmented_numerical_integral(
                expr,
                "Adaptive Simpson",
                func,
                0,
                1,
            )

    def test_parameter_resolution_is_validated_end_to_end(self):
        resolved = resolve_function_text("a*exp(-b*x)", "a=3, b=2")
        actual, _error, _segments = self._numerical_result(resolved, 0, 4)
        expected = 1.5 * (1 - mpmath.exp(-8))
        self.assertAlmostEqual(actual, float(expected), places=10)

    def test_improper_integrals_classify_convergence_and_divergence(self):
        convergent_cases = (
            ("1/x^2", "1", "inf", 1.0),
            ("exp(-x)", "0", "inf", 1.0),
        )
        for expression, lower, upper, expected in convergent_cases:
            with self.subTest(expression=expression):
                result = compute_general_integral(
                    expression,
                    lower,
                    upper,
                    timeout=0,
                )
                self.assertEqual(result["type"], "exact")
                self.assertAlmostEqual(float(result["expr"].evalf()), expected, places=12)

        divergent = compute_general_integral("1/x", "1", "inf", timeout=0)
        self.assertEqual(divergent["type"], "divergent")


if __name__ == "__main__":
    unittest.main()
