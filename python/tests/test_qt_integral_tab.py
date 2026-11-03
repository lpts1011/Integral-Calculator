import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from error_utils import friendly_error_message
from i18n import ui_text


class FakeField(QObject):
    changed = Signal(str)
    submitted = Signal()

    def __init__(self, parent, field_id, role, initial=""):
        super().__init__(parent)
        self.field_id = field_id
        self.role = role
        self._text = str(initial)

    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = str(value)

    def clear(self):
        self.set_text("")


class FakeMathEditorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = {}
        self.field_specs = []
        self.labels = {}
        self.insertions = []
        self.commands = []

    def create_field(self, field_id, role, initial="", label=None, slot=None):
        field = FakeField(self, field_id, role, initial)
        self.fields[field_id] = field
        self.field_specs.append((field_id, label, slot))
        return field

    def set_field_label(self, field_id, label):
        self.labels[field_id] = label

    def set_theme(self, name):
        pass

    def insert_latex(self, latex, field_id=None):
        self.insertions.append(latex)

    def dispatch_active_command(self, command):
        self.commands.append(command)


def run_synchronously(pool, callable, on_result=None, on_error=None, on_finished=None):
    try:
        result = callable()
        if on_result is not None:
            on_result(result)
    except Exception as exc:
        if on_error is not None:
            on_error(exc)
    finally:
        if on_finished is not None:
            on_finished()


from qt_integral_tab import AUTO_METHOD, IntegralTab


class IntegralTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.errors = []
        for patcher in (
            patch("qt_integral_tab.run_in_background", run_synchronously),
            patch("qt_integral_tab.show_error_dialog", lambda _parent, _title, message: self.errors.append(message)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.tab = IntegralTab(panel_factory=FakeMathEditorPanel)
        self.addCleanup(self.tab.deleteLater)
        self.records = []
        self.plots = []
        self.cleared = []
        self.tab.history_record.connect(self.records.append)
        self.tab.plot_requested.connect(lambda *args: self.plots.append(args))
        self.tab.plot_clear_requested.connect(lambda: self.cleared.append(True))

    def fill(self, function, lower="", upper="", parameters=""):
        self.tab.set_function_text(function)
        self.tab.lower.set_text(lower)
        self.tab.upper.set_text(upper)
        self.tab.set_parameter_text(parameters)

    def exact(self, module_function):
        """Run symbolic work in-process so tests do not start worker processes."""
        import symbolic_methods

        real = getattr(symbolic_methods, module_function)
        return patch(
            f"qt_integral_tab.{module_function}",
            side_effect=lambda func, lower, upper, **_kwargs: real(func, lower, upper, timeout=0),
        )

    def test_one_screen_has_four_live_fields_in_layout_order(self):
        self.assertEqual(
            self.tab.math_panel.field_specs,
            [
                ("upper", "Upper limit:", "upper-bound"),
                ("lower", "Lower limit:", "lower-bound"),
                ("function", "Enter target function:", "integrand"),
                ("parameters", "Parameters:", "parameters"),
            ],
        )
        self.assertGreaterEqual(self.tab.math_panel.minimumHeight(), 290)

    def test_only_the_essential_controls_are_visible_until_requested(self):
        self.assertTrue(self.tab.options_panel.isHidden())
        self.assertTrue(self.tab.busy_panel.isHidden())
        self.tab.options_button.click()
        self.assertFalse(self.tab.options_panel.isHidden())
        self.assertEqual(self.tab.selected_method(), AUTO_METHOD)
        self.assertEqual(self.tab.method_combo.itemText(0), "Auto (exact when possible)")

    def test_enter_from_any_live_field_submits(self):
        calls = []
        with patch.object(IntegralTab, "calculate", lambda _self: calls.append(True)):
            tab = IntegralTab(panel_factory=FakeMathEditorPanel)
            self.addCleanup(tab.deleteLater)
            for field in tab.math_panel.fields.values():
                field.submitted.emit()
        self.assertEqual(len(calls), 4)

    def test_keyboard_input_goes_to_the_live_editor(self):
        self.tab.insert_at_cursor(r"\sin\left(#?\right)")
        self.tab.dispatch_editor_command("moveToPreviousChar")
        self.assertEqual(self.tab.math_panel.insertions, [r"\sin\left(#?\right)"])
        self.assertEqual(self.tab.math_panel.commands, ["moveToPreviousChar"])

    def test_auto_gives_exact_definite_result_and_plot(self):
        self.fill("x^2", "0", "1")
        with self.exact("compute_tab1_result"):
            self.tab.calculate()
        record = self.records[-1]
        self.assertEqual(record["type"], "definite")
        self.assertIn("1/3", record["display"])
        self.assertEqual((record["func"], record["lower"], record["upper"]), ("x^2", "0", "1"))
        self.assertEqual(self.plots[-1][:3], ("x**2", 0.0, 1.0))
        self.assertFalse(self.tab.worker_running)
        self.assertTrue(self.tab.busy_panel.isHidden())

    def test_auto_gives_indefinite_result_without_bounds(self):
        self.fill("sin(x)")
        with self.exact("compute_tab1_result"):
            self.tab.calculate()
        self.assertEqual(self.records[-1]["type"], "indefinite")
        self.assertIn("-cos(x) + C", self.records[-1]["display"])
        self.assertTrue(self.cleared)

    def test_auto_handles_infinite_bounds_including_divergence(self):
        self.fill("1/x^2", "1", "inf")
        with self.exact("compute_general_integral"):
            self.tab.calculate()
        self.assertEqual(self.records[-1]["type"], "improper")
        self.assertEqual(self.records[-1]["raw_type"], "exact")
        self.assertIn("= 1", self.records[-1]["display"])

        self.fill("1/x", "1", "inf")
        with self.exact("compute_general_integral"):
            self.tab.calculate()
        self.assertEqual(self.records[-1]["raw_type"], "divergent")
        self.assertIn("Divergent", self.records[-1]["display"])

    def test_parameters_are_resolved_before_integrating(self):
        self.fill("a*x", "0", "1", "a=2")
        with self.exact("compute_tab1_result"):
            self.tab.calculate()
        self.assertEqual(self.records[-1]["params"], "a=2")
        self.assertTrue(self.records[-1]["display"].endswith("= 1"))

    def test_chosen_numerical_method_records_diagnostics(self):
        self.fill("sin(x)", "0", "pi")
        self.tab.set_method("Adaptive Simpson")
        self.assertFalse(self.tab.options_panel.isHidden())
        self.tab.calculate()
        record = self.records[-1]
        self.assertEqual(record["type"], "numerical")
        self.assertEqual(record["method"], "Adaptive Simpson")
        self.assertAlmostEqual(float(record["raw"]), 2.0, places=8)
        self.assertEqual(record["diagnostics"]["status"], "converged")
        self.assertEqual(self.plots[-1][0], "sin(x)")
        self.assertAlmostEqual(self.plots[-1][2], 3.141592653589793)

    def test_numerical_methods_explain_that_infinite_bounds_need_auto(self):
        self.fill("exp(-x)", "0", "inf")
        self.tab.set_method("Simpson")
        self.tab.calculate()
        self.assertEqual(self.records, [])
        self.assertIn("choose Auto for infinite limits", self.errors[-1])

    def test_comparison_records_rows_and_opens_table(self):
        rows = [{"method": "Simpson", "result": 1 / 3, "error": 0.0, "time": 0.001, "status": "ok"}]
        self.fill("x^2", "0", "1")
        with patch("qt_integral_tab.compare_numerical_methods", return_value=rows), patch.object(
            IntegralTab, "_show_comparison_dialog"
        ) as dialog:
            self.tab.compare_methods()
        self.assertEqual(self.records[-1]["type"], "comparison")
        self.assertEqual(self.records[-1]["raw"], rows)
        dialog.assert_called_once_with(rows)

    def test_refill_restores_inputs_and_method(self):
        self.tab.refill({"func": "sin(x)", "params": "", "lower": "0", "upper": "pi", "method": "Simpson"})
        self.assertEqual(self.tab.get_function_text(), "sin(x)")
        self.assertEqual(self.tab.upper.get_text(), "pi")
        self.assertEqual(self.tab.selected_method(), "Simpson")
        self.tab.refill({"func": "x", "lower": "", "upper": ""})
        self.assertEqual(self.tab.selected_method(), AUTO_METHOD)

    def test_reset_button_requests_central_reset_and_reset_clears_everything(self):
        self.fill("x^2", "0", "1")
        self.tab.set_method("Simpson")
        requests = []
        self.tab.reset_requested.connect(lambda: requests.append(True))
        self.tab.reset_button.click()
        self.assertEqual(requests, [True])
        self.assertEqual(self.tab.get_function_text(), "x^2")
        self.tab.reset()
        self.assertEqual(self.tab.get_function_text(), "")
        self.assertEqual(self.tab.selected_method(), AUTO_METHOD)
        self.assertTrue(self.tab.options_panel.isHidden())

    def test_language_updates_buttons_and_field_labels(self):
        text = ui_text("中文（简体）")
        self.tab.set_language(text)
        self.assertEqual(self.tab.calculate_button.text(), "计算")
        self.assertEqual(self.tab.method_combo.itemText(0), text["method_auto"])
        self.assertEqual(self.tab.math_panel.labels["upper"], "上限：")

    def test_friendly_error_suggests_function_parentheses(self):
        message = friendly_error_message("Only variable x is allowed.", "sinx", "0", "1")
        self.assertIn("sin(x)", message)


if __name__ == "__main__":
    unittest.main()
