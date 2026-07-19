import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QWidget

from math_editor.adapter import MathFieldAdapter
from math_editor.syntax import FieldRole
from qt_math_tools import MathToolsDialog, UncappedLineEdit


class FakeMathEditorPanel(QWidget):
    instances = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = {}
        self.specs = []
        self.operations = []
        type(self).instances.append(self)

    def create_field(self, field_id, role, initial="", label=None, slot=None):
        field = MathFieldAdapter(self, field_id, role, initial)
        self.fields[field_id] = field
        self.specs.append((field_id, label, role, initial))
        return field

    def set_field_value(self, field_id, value):
        self.operations.append(("set", field_id, value))

    def focus_field(self, field_id):
        self.operations.append(("focus", field_id))

    def set_field_enabled(self, field_id, enabled):
        self.operations.append(("enabled", field_id, bool(enabled)))

    def set_theme(self, name):
        self.operations.append(("theme", name))

    def dispatch_command(self, field_id, command):
        self.operations.append(("command", field_id, command))


class QtMathToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeMathEditorPanel.instances.clear()
        self.functions = []
        self.parameters = []
        self.dialog = MathToolsDialog(
            self.functions.append,
            self.parameters.append,
            panel_factory=FakeMathEditorPanel,
        )
        self.addCleanup(self.dialog.deleteLater)

    def test_every_declared_math_expression_uses_live_field(self):
        self.assertGreater(len(self.dialog.math_fields), 20)
        for name, field in self.dialog.math_fields.items():
            with self.subTest(name=name):
                self.assertIsInstance(field, MathFieldAdapter)
                self.assertTrue(callable(field.get_text))
                self.assertTrue(callable(field.set_text))
                self.assertTrue(callable(field.dispatch_command))

    def test_close_deletes_dialog_and_all_math_panels(self):
        dialog = MathToolsDialog(
            lambda _value: None,
            lambda _value: None,
            panel_factory=FakeMathEditorPanel,
        )
        destroyed_dialogs = []
        destroyed_panels = []
        dialog.destroyed.connect(lambda *_args: destroyed_dialogs.append(True))
        panels = list(dialog.math_panels.values())
        self.assertEqual(len(panels), 16)
        for panel in panels:
            panel.destroyed.connect(lambda *_args: destroyed_panels.append(True))

        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))
        dialog.show()
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

        self.assertEqual(destroyed_dialogs, [True])
        self.assertEqual(len(destroyed_panels), 16)

    def test_categories_pages_and_actions_cover_every_existing_tool(self):
        expected_pages = {
            "Polar Area", "Taylor", "Average / Area", "Convergence Table",
            "Analysis", "Convergence", "Error Plot", "Verify Antiderivative",
            "Piecewise Builder", "Parameter Slider", "Techniques", "Geometry",
            "Transforms / ODE", "Sensitivity", "Double Integral", "More Integrals",
        }
        self.assertEqual(set(self.dialog.pages), expected_pages)
        self.assertEqual(set(self.dialog.category_tabs), set(MathToolsDialog.CATEGORIES))
        self.assertEqual(
            set(self.dialog.actions),
            {
                "polar.compute", "taylor.compute", "average.compute", "table.compute",
                "analysis.compute", "convergence.compute", "error.compute", "verify.compute",
                "piecewise.build", "piecewise.insert", "parameter.range", "parameter.apply",
                "techniques.substitute", "techniques.parts", "geometry.compute",
                "transforms.fourier", "transforms.laplace", "transforms.ode",
                "sensitivity.compute", "double.compute", "multi.compute",
            },
        )

    def test_field_roles_are_explicit_and_native_controls_remain_native(self):
        self.assertEqual(self.dialog.math_fields["polar.radius"].role, FieldRole.EXPRESSION)
        self.assertEqual(self.dialog.math_fields["polar.lower"].role, FieldRole.BOUND)
        self.assertEqual(self.dialog.math_fields["parameter.assignment"].role, FieldRole.PARAMETERS)
        self.assertEqual(self.dialog.math_fields["techniques.substitution"].role, FieldRole.EQUATION)
        self.assertEqual(self.dialog.math_fields["transforms.ode"].role, FieldRole.EQUATION)
        self.assertEqual(
            self.dialog.math_fields["techniques.substitution"].validation_status,
            "valid",
        )
        self.assertEqual(self.dialog.math_fields["transforms.ode"].validation_status, "valid")
        self.assertEqual(self.dialog.math_fields["techniques.substitution"].get_text(), "u=x^2")
        self.assertEqual(self.dialog.math_fields["transforms.ode"].get_text(), "y'=x*y")
        self.assertIsInstance(self.dialog.native_controls["table.method"], QComboBox)
        self.assertIsInstance(self.dialog.native_controls["taylor.order"], QLineEdit)
        self.assertIsInstance(self.dialog.native_controls["sensitivity.parameter"], QLineEdit)
        all_specs = [spec for panel in FakeMathEditorPanel.instances for spec in panel.specs]
        self.assertTrue(all(label for _name, label, _role, _default in all_specs))

    def test_initial_function_only_replaces_legacy_active_function_defaults(self):
        legacy_fields = (
            "taylor.function",
            "table.function",
            "analysis.function",
            "parameter.function",
            "average.function",
            "geometry.function",
            "convergence.function",
            "error.function",
        )
        custom = MathToolsDialog(
            lambda _value: None,
            lambda _value: None,
            initial_function="  cos(x)  ",
            panel_factory=FakeMathEditorPanel,
        )
        self.addCleanup(custom.deleteLater)
        for field_name in legacy_fields:
            with self.subTest(field=field_name):
                self.assertEqual(custom.math_fields[field_name].get_text(), "cos(x)")
        self.assertEqual(custom.math_fields["transforms.function"].get_text(), "exp(-x)")
        self.assertEqual(custom.math_fields["polar.radius"].get_text(), "2*cos(theta)")
        self.assertEqual(custom.math_fields["sensitivity.function"].get_text(), "a*x")

        fallback_defaults = {
            "taylor.function": "sin(x)",
            "table.function": "x^2",
            "analysis.function": "x^2-1",
            "parameter.function": "a*x^2",
            "average.function": "x",
            "geometry.function": "x",
            "convergence.function": "exp(-x)",
            "error.function": "x^2",
        }
        for field_name, expected in fallback_defaults.items():
            with self.subTest(fallback=field_name):
                self.assertEqual(self.dialog.math_fields[field_name].get_text(), expected)

    def test_title_and_six_categories_use_localized_text(self):
        localized = {
            "math_tools": "Localized Tools",
            "math_tools_basic": "B",
            "math_tools_analysis": "A",
            "math_tools_builders": "Build",
            "math_tools_calculus": "Calc",
            "math_tools_advanced": "Adv",
            "math_tools_multi": "Multi",
        }
        dialog = MathToolsDialog(
            lambda _value: None,
            lambda _value: None,
            text=localized,
            panel_factory=FakeMathEditorPanel,
        )
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.windowTitle(), "Localized Tools")
        self.assertEqual(
            [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())],
            ["B", "A", "Build", "Calc", "Adv", "Multi"],
        )

    def test_dark_theme_is_applied_to_every_math_panel(self):
        dialog = MathToolsDialog(
            lambda _value: None,
            lambda _value: None,
            theme_name="Dark",
            panel_factory=FakeMathEditorPanel,
        )
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(len(dialog.math_panels), 16)
        for name, panel in dialog.math_panels.items():
            with self.subTest(panel=name):
                self.assertIn(("theme", "Dark"), panel.operations)

    def test_numeric_expression_controls_are_uncapped_and_unvalidated(self):
        taylor_order = self.dialog.native_controls["taylor.order"]
        fourier_terms = self.dialog.native_controls["transforms.terms"]
        self.assertIsInstance(taylor_order, UncappedLineEdit)
        self.assertIsInstance(fourier_terms, UncappedLineEdit)
        self.assertEqual(taylor_order.text(), "5")
        self.assertEqual(fourier_terms.text(), "5")
        self.assertIsNone(taylor_order.validator())
        self.assertIsNone(fourier_terms.validator())

        large_value = "1234567890" * 12
        for control in (taylor_order, fourier_terms):
            with self.subTest(control=control.objectName()):
                control.setText(large_value)
                self.assertTrue(control.hasAcceptableInput())
                self.assertEqual(control.text(), large_value)

        for value in ("2+3", "  5  ", "5.0", "1e2", "0", "-1"):
            for control in (taylor_order, fourier_terms):
                with self.subTest(value=value, control=control.objectName()):
                    control.setText(value)
                    self.assertEqual(control.text(), value)
                    self.assertTrue(control.hasAcceptableInput())

    def test_numeric_expression_text_is_forwarded_exactly_to_existing_helpers(self):
        taylor_order = self.dialog.native_controls["taylor.order"]
        fourier_terms = self.dialog.native_controls["transforms.terms"]
        values = ("2+3", "  5  ", "5.0", "1e2", "1234567890" * 12)
        for value in values:
            with self.subTest(taylor=value):
                taylor_order.setText(value)
                result = {
                    "point": "0",
                    "order": value,
                    "polynomial": "x",
                    "series": "x",
                }
                with patch(
                    "qt_math_tools.compute_taylor_expansion",
                    return_value=result,
                ) as helper:
                    self.dialog.actions["taylor.compute"].click()
                helper.assert_called_once_with("sin(x)", "0", value)

            with self.subTest(fourier=value):
                fourier_terms.setText(value)
                with patch(
                    "qt_math_tools.compute_fourier_series",
                    return_value={"series": "x"},
                ) as helper:
                    self.dialog.actions["transforms.fourier"].click()
                helper.assert_called_once_with("exp(-x)", "2*pi", value)

    def test_numeric_expression_helper_errors_use_existing_action_guard(self):
        cases = (
            ("taylor.order", "taylor.compute", "compute_taylor_expansion", "Build Taylor Polynomial"),
            ("transforms.terms", "transforms.fourier", "compute_fourier_series", "Fourier"),
        )
        for control_name, action_name, helper_name, title in cases:
            with self.subTest(action=action_name):
                self.dialog.native_controls[control_name].setText("invalid input")
                with patch(
                    f"qt_math_tools.{helper_name}",
                    side_effect=ValueError("invalid numeric expression"),
                ), patch("qt_math_tools.show_error_dialog") as show_error:
                    self.dialog.actions[action_name].click()
                show_error.assert_called_once_with(
                    self.dialog,
                    title,
                    "invalid numeric expression",
                )

    def test_piecewise_builder_inserts_existing_calculator_syntax(self):
        value = self.dialog.build_piecewise_for_test([("x", "x<0"), ("x^2", "True")])
        self.assertEqual(value, "Piecewise((x, x<0), (x^2, True))")
        self.assertEqual(self.functions[-1], value)
        self.assertEqual(
            self.dialog.math_fields["piecewise.result"].get_text().replace(" ", ""),
            value.replace(" ", ""),
        )

    def test_parameter_slider_updates_live_field_and_active_inputs_without_focus(self):
        slider = self.dialog.native_controls["parameter.slider"]
        slider.setValue(500)
        assignment = self.dialog._parameter_apply()
        self.assertEqual(assignment, "a=2.5")
        self.assertEqual(self.dialog.math_fields["parameter.assignment"].get_text(), "a=2.5")
        self.assertEqual(self.functions[-1], "a*x^2")
        self.assertEqual(self.parameters[-1], "a=2.5")
        operations = [op for panel in FakeMathEditorPanel.instances for op in panel.operations]
        self.assertFalse(any(operation[0] == "focus" for operation in operations))

    def test_representative_actions_route_to_existing_helpers_and_format_results(self):
        polar_result = {"integrand": "2*cos(theta)^2", "exact": "pi", "numeric": 3.0}
        with patch("qt_math_tools.compute_polar_area", return_value=polar_result) as helper:
            self.dialog.actions["polar.compute"].click()
        helper.assert_called_once_with("2*cos(theta)", "-pi/2", "pi/2")
        self.assertIn("Exact area: pi", self.dialog.results["polar_area"].toPlainText())

        double_result = {"exact": "1", "numeric": 1.0}
        with patch("qt_math_tools.compute_double_integral", return_value=double_result) as helper:
            self.dialog.actions["double.compute"].click()
        helper.assert_called_once_with("x+y", "0", "1", "0", "1")
        self.assertIn("Numeric result: 1", self.dialog.results["double_integral"].toPlainText())

    def test_multivariable_modes_route_with_the_original_argument_order(self):
        result = {"exact": "ok", "numeric": 1.0}
        mode = self.dialog.native_controls["multi.mode"]
        mode.setCurrentText("Polar double")
        with patch("qt_math_tools.compute_polar_double_integral", return_value=result) as helper:
            self.dialog.actions["multi.compute"].click()
        helper.assert_called_once_with("1", "0", "x", "0", "1")

        mode.setCurrentText("Triple")
        with patch("qt_math_tools.compute_triple_integral", return_value=result) as helper:
            self.dialog.actions["multi.compute"].click()
        helper.assert_called_once_with("1", "0", "1", "0", "x", "0", "1")

    def test_error_profile_retains_logarithmic_graph(self):
        profile = {
            "reference": 1 / 3,
            "rows": [
                {"method": "Trapezoidal", "value": 0.34, "absolute_error": 0.01},
                {"method": "Simpson", "value": 1 / 3, "absolute_error": 0.0},
            ],
        }
        with patch("qt_math_tools.build_error_profile", return_value=profile):
            self.dialog.actions["error.compute"].click()
        self.assertEqual(self.dialog.error_axes.get_yscale(), "log")
        self.assertEqual(len(self.dialog.error_axes.patches), 2)
        self.assertIn("Reference value", self.dialog.results["error_plot"].toPlainText())

    def test_antiderivative_and_parameter_sensitivity_outputs(self):
        with patch(
            "qt_math_tools.verify_antiderivative",
            return_value={"ok": True, "difference": "0"},
        ) as helper:
            self.dialog.actions["verify.compute"].click()
        helper.assert_called_once_with("sin(x)", "-cos(x)")
        self.assertIn("Verified", self.dialog.results["verify_antiderivative"].toPlainText())

        rows = [{"parameter": "1", "integral": "1/2", "numeric": 0.5}]
        with patch("qt_math_tools.compute_parameter_sensitivity", return_value=rows) as helper:
            self.dialog.actions["sensitivity.compute"].click()
        helper.assert_called_once_with("a*x", "a", "1,2,3", "0", "1")
        self.assertIn("a=1", self.dialog.results["sensitivity"].toPlainText())


if __name__ == "__main__":
    unittest.main()
