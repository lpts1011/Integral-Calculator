import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QWidget

from i18n import ui_text
from math_editor.adapter import MathFieldAdapter
from math_editor.syntax import FieldRole
from qt_math_tools import MathToolsDialog, UncappedLineEdit


TOOLS = (
    "Area & Average",
    "Polar Area",
    "Arc Length & Volume",
    "Multiple Integrals",
    "Taylor Series",
    "Fourier, Laplace & ODE",
    "Integration Techniques",
    "Verify Antiderivative",
    "Parameter Slider",
    "Piecewise Builder",
)


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


class _MissingRecorder(dict):
    """A translation table that remembers phrases it could not translate."""

    def __init__(self, table):
        super().__init__(table)
        self.missing = set()

    def get(self, key, default=None):
        if key not in self:
            self.missing.add(key)
        return super().get(key, default)


class QtMathToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeMathEditorPanel.instances.clear()
        self.functions = []
        self.parameters = []
        self.dialog = self.make_dialog(self.functions.append, self.parameters.append)
        self.dialog._submit_job = lambda function, arguments, present: present(function(*arguments))

    def make_dialog(self, insert_function=lambda _value: None, insert_parameters=lambda _value: None, **options):
        dialog = MathToolsDialog(insert_function, insert_parameters, panel_factory=FakeMathEditorPanel, **options)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_tools_are_one_flat_list_that_switches_pages(self):
        self.assertEqual(
            [self.dialog.tool_list.item(row).text() for row in range(self.dialog.tool_list.count())],
            list(TOOLS),
        )
        self.assertEqual(set(self.dialog.pages), set(TOOLS))
        self.assertEqual(self.dialog.stack.count(), len(TOOLS))
        self.dialog.tool_list.setCurrentRow(3)
        self.assertEqual(self.dialog.stack.currentIndex(), 3)
        self.assertEqual(
            set(self.dialog.actions),
            {
                "average.compute", "polar.compute", "geometry.compute", "multi.compute",
                "taylor.compute", "transforms.fourier", "transforms.laplace", "transforms.ode",
                "techniques.substitute", "techniques.parts", "verify.compute",
                "parameter.range", "parameter.apply", "piecewise.build", "piecewise.insert",
            },
        )

    def test_every_declared_math_expression_uses_live_field(self):
        self.assertGreater(len(self.dialog.math_fields), 20)
        for name, field in self.dialog.math_fields.items():
            with self.subTest(name=name):
                self.assertIsInstance(field, MathFieldAdapter)

    def test_close_deletes_dialog_and_all_math_panels(self):
        dialog = MathToolsDialog(lambda _value: None, lambda _value: None, panel_factory=FakeMathEditorPanel)
        destroyed_dialogs = []
        destroyed_panels = []
        dialog.destroyed.connect(lambda *_args: destroyed_dialogs.append(True))
        panels = list(dialog.math_panels.values())
        self.assertEqual(len(panels), len(TOOLS))
        for panel in panels:
            panel.destroyed.connect(lambda *_args: destroyed_panels.append(True))

        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))
        dialog.show()
        dialog.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

        self.assertEqual(destroyed_dialogs, [True])
        self.assertEqual(len(destroyed_panels), len(TOOLS))

    def test_field_roles_are_explicit_and_native_controls_remain_native(self):
        fields = self.dialog.math_fields
        self.assertEqual(fields["polar.radius"].role, FieldRole.EXPRESSION)
        self.assertEqual(fields["polar.lower"].role, FieldRole.BOUND)
        self.assertEqual(fields["parameter.assignment"].role, FieldRole.PARAMETERS)
        self.assertEqual(fields["techniques.substitution"].role, FieldRole.EQUATION)
        self.assertEqual(fields["transforms.ode"].role, FieldRole.EQUATION)
        self.assertEqual(fields["techniques.substitution"].get_text(), "u=x^2")
        self.assertEqual(fields["transforms.ode"].get_text(), "y'=x*y")
        self.assertIsInstance(self.dialog.native_controls["multi.mode"], QComboBox)
        self.assertIsInstance(self.dialog.native_controls["taylor.order"], QLineEdit)
        all_specs = [spec for panel in FakeMathEditorPanel.instances for spec in panel.specs]
        self.assertTrue(all(label for _name, label, _role, _default in all_specs))

    def test_initial_function_replaces_only_single_function_defaults(self):
        custom = self.make_dialog(initial_function="  cos(x)  ")
        for field_name in ("average.function", "geometry.function", "taylor.function", "parameter.function"):
            with self.subTest(field=field_name):
                self.assertEqual(custom.math_fields[field_name].get_text(), "cos(x)")
        self.assertEqual(custom.math_fields["transforms.function"].get_text(), "exp(-x)")
        self.assertEqual(custom.math_fields["polar.radius"].get_text(), "2*cos(theta)")
        self.assertEqual(custom.math_fields["multi.function"].get_text(), "x+y")
        self.assertEqual(self.dialog.math_fields["taylor.function"].get_text(), "sin(x)")

    def test_chinese_translates_every_tool_name_label_and_button(self):
        text = ui_text("中文（简体）")
        recorder = _MissingRecorder(text["tool_text"])
        dialog = self.make_dialog(text={**text, "tool_text": recorder})
        self.assertEqual(recorder.missing, set())
        self.assertEqual(dialog.windowTitle(), "数学工具")
        self.assertEqual(dialog.tool_list.item(0).text(), "面积与平均值")
        self.assertEqual(dialog.actions["multi.compute"].text(), "计算积分")
        self.assertEqual(dialog.cancel_button.text(), "取消计算")

    def test_every_result_phrase_has_a_chinese_translation(self):
        source = Path(__file__).resolve().parents[1].joinpath("qt_math_tools.py").read_text(encoding="utf-8")
        phrases = set(re.findall(r"""\btr\((['"])(.+?)\1\)""", source))
        self.assertGreater(len(phrases), 30)
        table = ui_text("中文（简体）")["tool_text"]
        self.assertEqual({phrase for _quote, phrase in phrases} - set(table), set())

    def test_dark_theme_is_applied_to_every_math_panel(self):
        dialog = self.make_dialog(theme_name="Dark")
        self.assertEqual(len(dialog.math_panels), len(TOOLS))
        for name, panel in dialog.math_panels.items():
            with self.subTest(panel=name):
                self.assertIn(("theme", "Dark"), panel.operations)

    def test_cancel_button_only_appears_while_a_job_runs(self):
        self.assertTrue(self.dialog.cancel_button.isHidden())
        self.dialog._set_job_busy(True)
        self.assertFalse(self.dialog.cancel_button.isHidden())
        self.assertFalse(self.dialog.actions["polar.compute"].isEnabled())
        self.dialog._set_job_busy(False)
        self.assertTrue(self.dialog.cancel_button.isHidden())

    def test_numeric_expression_controls_are_uncapped_and_unvalidated(self):
        for control in (self.dialog.native_controls["taylor.order"], self.dialog.native_controls["transforms.terms"]):
            self.assertIsInstance(control, UncappedLineEdit)
            self.assertEqual(control.text(), "5")
            self.assertIsNone(control.validator())
            for value in ("1234567890" * 12, "2+3", "  5  ", "1e2", "-1"):
                control.setText(value)
                self.assertEqual(control.text(), value)
                self.assertTrue(control.hasAcceptableInput())

    def test_numeric_expression_text_is_forwarded_exactly_to_helpers(self):
        for value in ("2+3", "  5  ", "1234567890" * 12):
            self.dialog.native_controls["taylor.order"].setText(value)
            result = {"point": "0", "order": value, "polynomial": "x", "series": "x"}
            with patch("qt_math_tools.compute_taylor_expansion", return_value=result) as helper:
                self.dialog.actions["taylor.compute"].click()
            helper.assert_called_once_with("sin(x)", "0", value)

            self.dialog.native_controls["transforms.terms"].setText(value)
            with patch("qt_math_tools.compute_fourier_series", return_value={"series": "x"}) as helper:
                self.dialog.actions["transforms.fourier"].click()
            helper.assert_called_once_with("exp(-x)", "2*pi", value)

    def test_helper_errors_are_shown_with_the_button_title(self):
        cases = (
            ("taylor.compute", "compute_taylor_expansion", "Build Taylor Polynomial"),
            ("transforms.fourier", "compute_fourier_series", "Fourier Series"),
        )
        for action_name, helper_name, title in cases:
            with self.subTest(action=action_name):
                with patch(
                    f"qt_math_tools.{helper_name}", side_effect=ValueError("invalid numeric expression")
                ), patch("qt_math_tools.show_error_dialog") as show_error:
                    self.dialog.actions[action_name].click()
                show_error.assert_called_once_with(self.dialog, title, "invalid numeric expression")

    def test_piecewise_builder_inserts_calculator_syntax(self):
        value = self.dialog.build_piecewise_for_test([("x", "x<0"), ("x^2", "True")])
        self.assertEqual(value, "Piecewise((x, x<0), (x^2, True))")
        self.assertEqual(self.functions[-1], value)

    def test_parameter_slider_updates_live_field_and_calculator_without_focus(self):
        self.dialog.native_controls["parameter.slider"].setValue(500)
        assignment = self.dialog._parameter_apply()
        self.assertEqual(assignment, "a=2.5")
        self.assertEqual(self.dialog.math_fields["parameter.assignment"].get_text(), "a=2.5")
        self.assertEqual(self.functions[-1], "a*x^2")
        self.assertEqual(self.parameters[-1], "a=2.5")
        operations = [op for panel in FakeMathEditorPanel.instances for op in panel.operations]
        self.assertFalse(any(operation[0] == "focus" for operation in operations))

    def test_actions_route_to_helpers_and_format_results(self):
        polar_result = {"integrand": "2*cos(theta)^2", "exact": "pi", "numeric": 3.0}
        with patch("qt_math_tools.compute_polar_area", return_value=polar_result) as helper:
            self.dialog.actions["polar.compute"].click()
        helper.assert_called_once_with("2*cos(theta)", "-pi/2", "pi/2")
        self.assertIn("Exact area: pi", self.dialog.results["polar_area"].toPlainText())

        with patch(
            "qt_math_tools.verify_antiderivative", return_value={"ok": True, "difference": "0"}
        ) as helper:
            self.dialog.actions["verify.compute"].click()
        helper.assert_called_once_with("sin(x)", "-cos(x)")
        self.assertIn("Verified", self.dialog.results["verify_antiderivative"].toPlainText())

    def test_multiple_integral_types_route_with_their_argument_order(self):
        result = {"exact": "1", "numeric": 1.0}
        mode = self.dialog.native_controls["multi.mode"]
        cases = (
            (0, "compute_variable_double_integral", ("x+y", "0", "1", "0", "1")),
            (1, "compute_polar_double_integral", ("x+y", "0", "1", "0", "1")),
            (2, "compute_triple_integral", ("x+y", "0", "1", "0", "1", "0", "1")),
        )
        for index, helper_name, arguments in cases:
            with self.subTest(mode=index):
                mode.setCurrentIndex(index)
                with patch(f"qt_math_tools.{helper_name}", return_value=result) as helper:
                    self.dialog.actions["multi.compute"].click()
                helper.assert_called_once_with(*arguments)
        self.assertIn("Numeric result: 1", self.dialog.results["multiple_integrals"].toPlainText())


if __name__ == "__main__":
    unittest.main()
