import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget


class FakeField(QObject):
    changed = Signal(str)
    submitted = Signal()
    validity_changed = Signal(str, str)

    def __init__(self, parent, field_id, role, initial=""):
        super().__init__(parent)
        self.field_id = field_id
        self.role = role
        self._text = str(initial)
        self.enabled = True

    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = str(value)

    def clear(self):
        self.set_text("")

    def focus(self):
        pass

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def set_theme(self, name):
        pass

    def dispatch_command(self, command):
        pass


class FakeMathEditorPanel(QWidget):
    instances = []
    content_height_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = {}
        self.field_specs = []
        self.insertions = []
        self.commands = []
        type(self).instances.append(self)

    def create_field(self, field_id, role, initial="", label=None, slot=None):
        field = FakeField(self, field_id, role, initial)
        self.fields[field_id] = field
        self.field_specs.append({
            "id": field_id,
            "label": label,
            "slot": slot,
        })
        return field

    def set_theme(self, name):
        pass

    def insert_latex(self, latex, field_id=None):
        self.insertions.append((latex, field_id))

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
    return object()


from qt_tabs.advanced import AdvancedIntegrationTab
from qt_tabs.basic import BasicIntegrationTab
from qt_tabs.improper import ImproperIntegralTab


class QtTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeMathEditorPanel.instances.clear()
        self.worker_patchers = [
            patch("qt_tabs.basic.run_in_background", run_synchronously),
            patch("qt_tabs.advanced.run_in_background", run_synchronously),
            patch("qt_tabs.improper.run_in_background", run_synchronously),
        ]
        for patcher in self.worker_patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.worker_patchers):
            patcher.stop()

    def make_tab(self, tab_type):
        tab = tab_type(panel_factory=FakeMathEditorPanel)
        self.addCleanup(tab.deleteLater)
        return tab

    def test_all_tabs_share_live_math_contract(self):
        for tab_type in (
            BasicIntegrationTab,
            AdvancedIntegrationTab,
            ImproperIntegralTab,
        ):
            with self.subTest(tab=tab_type.__name__):
                before = len(FakeMathEditorPanel.instances)
                tab = self.make_tab(tab_type)
                self.assertEqual(len(FakeMathEditorPanel.instances), before + 1)
                tab.set_function_text("sin(x)")
                self.assertEqual(tab.get_function_text(), "sin(x)")
                self.assertTrue(tab.set_parameter_text("a=2"))
                self.assertEqual(tab.parameters.get_text(), "a=2")
                tab.clear_inputs()
                self.assertEqual(tab.get_function_text(), "")
                tab.result_label.setText("old")
                tab.clear_result()
                self.assertEqual(tab.result_label.text(), "")

    def test_all_tabs_route_keyboard_input_through_the_live_editor(self):
        for tab_type in (
            BasicIntegrationTab,
            AdvancedIntegrationTab,
            ImproperIntegralTab,
        ):
            with self.subTest(tab=tab_type.__name__):
                tab = self.make_tab(tab_type)
                tab.insert_at_cursor(r"\sin\left(#?\right)")
                tab.dispatch_editor_command("moveToPreviousChar")
                self.assertEqual(
                    tab.math_panel.insertions,
                    [(r"\sin\left(#?\right)", None)],
                )
                self.assertEqual(
                    tab.math_panel.commands,
                    ["moveToPreviousChar"],
                )

    def test_each_tab_creates_the_required_live_fields(self):
        expected = {
            BasicIntegrationTab: {"function", "lower", "upper", "parameters"},
            AdvancedIntegrationTab: {
                "function",
                "lower",
                "upper",
                "parameters",
                "split_points",
            },
            ImproperIntegralTab: {"function", "lower", "upper", "parameters"},
        }
        for tab_type, field_ids in expected.items():
            with self.subTest(tab=tab_type.__name__):
                tab = self.make_tab(tab_type)
                self.assertEqual(set(tab.math_panel.fields), field_ids)

    def test_basic_editor_has_room_for_all_four_live_fields(self):
        tab = self.make_tab(BasicIntegrationTab)
        self.assertGreaterEqual(tab.math_panel.minimumHeight(), 290)

    def test_advanced_editor_tracks_its_real_content_height(self):
        tab = self.make_tab(AdvancedIntegrationTab)
        self.assertEqual(tab.math_panel.minimumHeight(), 280)

        tab.math_panel.content_height_changed.emit(356)
        self.assertEqual(tab.math_panel.minimumHeight(), 360)

        tab.math_panel.content_height_changed.emit(240)
        self.assertEqual(tab.math_panel.minimumHeight(), 280)

    def test_tabs_pass_accessible_labels_and_integral_slots_in_layout_order(self):
        expected = {
            BasicIntegrationTab: [
                ("upper", "Upper limit:", "upper-bound"),
                ("lower", "Lower limit:", "lower-bound"),
                ("function", "Enter target function:", "integrand"),
                ("parameters", "Parameters:", "parameters"),
            ],
            AdvancedIntegrationTab: [
                ("upper", "Upper limit:", "upper-bound"),
                ("lower", "Lower limit:", "lower-bound"),
                ("function", "Enter target function:", "integrand"),
                ("parameters", "Parameters:", "parameters"),
                ("split_points", "Split points:", "split-points"),
            ],
            ImproperIntegralTab: [
                ("upper", "Upper limit:", "upper-bound"),
                ("lower", "Lower limit:", "lower-bound"),
                ("function", "Enter target function:", "integrand"),
                ("parameters", "Parameters:", "parameters"),
            ],
        }
        for tab_type, specs in expected.items():
            with self.subTest(tab=tab_type.__name__):
                tab = self.make_tab(tab_type)
                self.assertEqual(
                    [
                        (spec["id"], spec["label"], spec["slot"])
                        for spec in tab.math_panel.field_specs
                    ],
                    specs,
                )

    def test_refill_uses_existing_record_keys_without_migration(self):
        basic = self.make_tab(BasicIntegrationTab)
        basic.refill({"func": "x^2", "params": "a=2", "lower": "0", "upper": "1"})
        self.assertEqual(basic.function.get_text(), "x^2")
        self.assertEqual(basic.parameters.get_text(), "a=2")
        self.assertEqual(basic.lower.get_text(), "0")
        self.assertEqual(basic.upper.get_text(), "1")

        advanced = self.make_tab(AdvancedIntegrationTab)
        advanced.refill({
            "type": "numerical",
            "func": "sin(x)",
            "params": "",
            "lower": "0",
            "upper": "pi",
            "split_points": "pi/2",
            "method": "Simpson",
        })
        self.assertEqual(advanced.split_points.get_text(), "pi/2")
        self.assertEqual(advanced.mode_combo.currentText(), "Numerical Integration")
        self.assertEqual(advanced.numerical_method_combo.currentText(), "Simpson")

    def test_enter_from_any_live_field_submits(self):
        tab = self.make_tab(BasicIntegrationTab)
        calls = []
        tab.calculate = lambda: calls.append("calculate")
        for field in (tab.function, tab.lower, tab.upper, tab.parameters):
            field.submitted.emit()
        self.assertEqual(calls, ["calculate"] * 4)

    def test_basic_definite_result_and_history_are_compatible(self):
        tab = self.make_tab(BasicIntegrationTab)
        records = []
        plots = []
        tab.history_record.connect(records.append)
        tab.plot_requested.connect(lambda *args: plots.append(args))
        tab.set_function_text("x^2")
        tab.lower.set_text("0")
        tab.upper.set_text("1")

        from symbolic_methods import compute_tab1_result as real_compute

        with patch(
            "qt_tabs.basic.compute_tab1_result",
            side_effect=lambda func, lower, upper: real_compute(
                func, lower, upper, timeout=0
            ),
        ):
            tab.calculate()

        self.assertIn("1/3", tab.result_label.text())
        self.assertEqual(records[-1]["type"], "definite")
        self.assertEqual(records[-1]["func"], "x^2")
        self.assertEqual(records[-1]["lower"], "0")
        self.assertEqual(records[-1]["upper"], "1")
        self.assertIn("raw_type", records[-1])
        self.assertEqual(plots[-1][:3], ("x**2", 0.0, 1.0))
        self.assertFalse(tab.worker_running)

    def test_advanced_numerical_result_progress_and_history(self):
        tab = self.make_tab(AdvancedIntegrationTab)
        records = []
        plots = []
        tab.history_record.connect(records.append)
        tab.plot_requested.connect(lambda *args: plots.append(args))
        tab.set_function_text("sin(x)")
        tab.lower.set_text("0")
        tab.upper.set_text("pi")
        tab.split_points.set_text("pi/2")
        tab.mode_combo.setCurrentText("Numerical Integration")
        tab.numerical_method_combo.setCurrentText("Adaptive Simpson")

        tab.calculate()

        self.assertAlmostEqual(float(records[-1]["raw"]), 2.0, places=8)
        self.assertEqual(records[-1]["type"], "numerical")
        self.assertEqual(records[-1]["method"], "Adaptive Simpson")
        self.assertIn("segments", records[-1])
        self.assertEqual(records[-1]["split_points"], "pi/2")
        self.assertEqual(len(records[-1]["segments"]), 2)
        self.assertEqual(tab.progress_bar.value(), 100)
        self.assertEqual(plots[-1][0], "sin(x)")
        self.assertEqual(plots[-1][3], [records[-1]["segments"][0]["upper"]])
        self.assertFalse(tab.worker_running)

    def test_advanced_recommendation_apply_and_comparison_record(self):
        tab = self.make_tab(AdvancedIntegrationTab)
        tab.set_function_text("x^2")
        tab.lower.set_text("0")
        tab.upper.set_text("1")
        tab.update_recommendation()
        tab.apply_recommendation()
        self.assertEqual(tab.mode_combo.currentText(), "Numerical Integration")
        self.assertEqual(tab.numerical_method_combo.currentText(), "Simpson")

        rows = [{
            "method": "Simpson",
            "result": 1 / 3,
            "error": 0.0,
            "time": 0.001,
            "segments": 1,
            "status": "ok",
        }]
        records = []
        tab.history_record.connect(records.append)
        with patch("qt_tabs.advanced.compare_numerical_methods", return_value=rows):
            tab.compare_methods()
        self.assertEqual(records[-1]["type"], "comparison")
        self.assertEqual(records[-1]["raw"], rows)
        self.assertEqual(records[-1]["method"], "Method Comparison")

    def test_improper_divergent_result_and_history_classification(self):
        tab = self.make_tab(ImproperIntegralTab)
        records = []
        cleared = []
        tab.history_record.connect(records.append)
        tab.plot_clear_requested.connect(lambda: cleared.append(True))
        tab.set_function_text("1/x")
        tab.lower.set_text("1")
        tab.upper.set_text("inf")

        from symbolic_methods import compute_general_integral as real_compute

        with patch(
            "qt_tabs.improper.compute_general_integral",
            side_effect=lambda func, lower, upper: real_compute(
                func, lower, upper, timeout=0
            ),
        ):
            tab.compute()

        self.assertIn("Divergent", tab.result_label.text())
        self.assertEqual(records[-1]["type"], "improper")
        self.assertEqual(str(records[-1]["raw"]), "oo")
        self.assertTrue(cleared)
        self.assertFalse(tab.worker_running)

    def test_improper_unevaluated_result_keeps_existing_history_shape(self):
        tab = self.make_tab(ImproperIntegralTab)
        records = []
        tab.history_record.connect(records.append)
        tab.set_function_text("x")
        tab.lower.set_text("0")
        tab.upper.set_text("inf")
        with patch(
            "qt_tabs.improper.compute_general_integral",
            return_value={"type": "unevaluated", "expr": "Integral(x)"},
        ):
            tab.compute()
        self.assertIn("No closed-form expression found", tab.result_label.text())
        self.assertEqual(records[-1]["type"], "improper")
        self.assertEqual(records[-1]["raw"], "Integral(x)")

    def test_advanced_reset_clears_progress_and_inputs(self):
        tab = self.make_tab(AdvancedIntegrationTab)
        tab.set_function_text("x")
        tab.progress_bar.setRange(0, 0)
        tab.progress_bar.show()
        tab.reset()
        self.assertEqual(tab.get_function_text(), "")
        self.assertTrue(tab.progress_bar.isHidden())
        self.assertEqual((tab.progress_bar.minimum(), tab.progress_bar.maximum()), (0, 100))
        self.assertEqual(tab.progress_bar.value(), 0)

    def test_reset_button_requests_central_reset_without_clearing_locally(self):
        for tab_type in (
            BasicIntegrationTab,
            AdvancedIntegrationTab,
            ImproperIntegralTab,
        ):
            with self.subTest(tab=tab_type.__name__):
                tab = self.make_tab(tab_type)
                tab.set_function_text("x^2")
                requests = []
                tab.reset_requested.connect(lambda: requests.append(True))
                tab.reset_button.click()
                self.assertEqual(requests, [True])
                self.assertEqual(tab.get_function_text(), "x^2")
                tab.reset()
                self.assertEqual(tab.get_function_text(), "")


if __name__ == "__main__":
    unittest.main()
