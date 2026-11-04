import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QWidget

from i18n import ui_text
from math_editor.adapter import MathFieldAdapter
from math_editor.syntax import FieldRole
from qt_math_tools import MathToolsDialog


TOOLS = (
    "Area",
    "Polar Area",
    "Arc Length & Volume",
    "Integration Techniques",
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


class FakeResultView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.theme = None

    def set_rows(self, rows):
        self.rows = list(rows)

    def set_theme(self, name):
        self.theme = name


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
        self.dialog = self.make_dialog()
        self.dialog._submit_job = lambda function, arguments, present: present(function(*arguments))

    def make_dialog(self, **options):
        dialog = MathToolsDialog(
            panel_factory=FakeMathEditorPanel, result_view_factory=FakeResultView, **options
        )
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
                "area.compute", "polar.compute", "geometry.compute",
                "techniques.substitute", "techniques.parts",
            },
        )

    def test_every_declared_math_expression_uses_live_field(self):
        self.assertEqual(len(self.dialog.math_fields), 13)
        for name, field in self.dialog.math_fields.items():
            with self.subTest(name=name):
                self.assertIsInstance(field, MathFieldAdapter)

    def test_close_deletes_dialog_and_all_math_panels(self):
        dialog = MathToolsDialog(panel_factory=FakeMathEditorPanel, result_view_factory=FakeResultView)
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
        self.assertEqual(fields["techniques.substitution"].role, FieldRole.EQUATION)
        self.assertEqual(fields["techniques.substitution"].get_text(), "u=x^2")
        self.assertIsInstance(self.dialog.native_controls["geometry.axis"], QComboBox)
        all_specs = [spec for panel in FakeMathEditorPanel.instances for spec in panel.specs]
        self.assertTrue(all(label for _name, label, _role, _default in all_specs))

    def test_initial_function_replaces_only_single_function_defaults(self):
        custom = self.make_dialog(initial_function="  cos(x)  ")
        for field_name in ("area.function", "geometry.function"):
            with self.subTest(field=field_name):
                self.assertEqual(custom.math_fields[field_name].get_text(), "cos(x)")
        self.assertEqual(custom.math_fields["polar.radius"].get_text(), "2*cos(theta)")
        self.assertEqual(custom.math_fields["techniques.function"].get_text(), "2*x*cos(x^2)")
        self.assertEqual(self.dialog.math_fields["area.function"].get_text(), "x")

    def test_chinese_translates_every_tool_name_label_and_button(self):
        text = ui_text("中文（简体）")
        recorder = _MissingRecorder(text["tool_text"])
        dialog = self.make_dialog(text={**text, "tool_text": recorder})
        self.assertEqual(recorder.missing, set())
        self.assertEqual(dialog.windowTitle(), "数学工具")
        self.assertEqual(dialog.tool_list.item(0).text(), "面积")
        self.assertEqual(dialog.actions["area.compute"].text(), "计算面积")
        self.assertEqual(dialog.cancel_button.text(), "取消计算")

    def test_every_result_phrase_has_a_chinese_translation(self):
        source = Path(__file__).resolve().parents[1].joinpath("qt_math_tools.py").read_text(encoding="utf-8")
        phrases = set(re.findall(r"""\btr\((['"])(.+?)\1\)""", source))
        self.assertGreater(len(phrases), 15)
        table = ui_text("中文（简体）")["tool_text"]
        self.assertEqual({phrase for _quote, phrase in phrases} - set(table), set())
        notes = set(re.findall(r'note = "(.+?)"', source))
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes - set(table), set())

    def test_dark_theme_is_applied_to_every_math_panel(self):
        dialog = self.make_dialog(theme_name="Dark")
        self.assertEqual(len(dialog.math_panels), len(TOOLS))
        for name, panel in dialog.math_panels.items():
            with self.subTest(panel=name):
                self.assertIn(("theme", "Dark"), panel.operations)
        self.assertEqual(dialog.result_view.theme, "Dark")

    def test_cancel_button_only_appears_while_a_job_runs(self):
        self.assertTrue(self.dialog.cancel_button.isHidden())
        self.dialog._set_job_busy(True)
        self.assertFalse(self.dialog.cancel_button.isHidden())
        self.assertFalse(self.dialog.actions["polar.compute"].isEnabled())
        self.dialog._set_job_busy(False)
        self.assertTrue(self.dialog.cancel_button.isHidden())

    def test_actions_route_to_helpers_and_format_results(self):
        polar_result = {
            "integrand": "2*cos(theta)^2",
            "exact": "pi",
            "numeric": 3.0,
            "latex": {"integrand": r"2 \cos^{2}{\left(\theta \right)}", "exact": r"\pi"},
        }
        self.dialog.tool_list.setCurrentRow(1)
        with patch("qt_math_tools.compute_polar_area", return_value=polar_result) as helper:
            self.dialog.actions["polar.compute"].click()
        helper.assert_called_once_with("2*cos(theta)", "-pi/2", "pi/2")
        self.assertIn("Exact area: pi", self.dialog.result_text("polar_area"))
        self.assertIn({"label": "Exact area:", "latex": r"\pi", "text": "pi"}, self.dialog.result_view.rows)

        area_result = {"signed": 0.0, "absolute": 1.0, "positive_area": 0.5, "negative_area": 0.5}
        with patch("qt_math_tools.compute_area_breakdown", return_value=area_result) as helper:
            self.dialog.actions["area.compute"].click()
        helper.assert_called_once_with("x", "-1", "1")
        self.assertIn("Absolute area: 1", self.dialog.result_text("area"))
        # The view keeps showing the open page; switching pages shows the other result.
        self.assertIn("Exact area:", [row.get("label") for row in self.dialog.result_view.rows])
        self.dialog.tool_list.setCurrentRow(0)
        self.assertIn("Absolute area:", [row.get("label") for row in self.dialog.result_view.rows])

    def test_real_helpers_render_as_formulas(self):
        self.dialog.tool_list.setCurrentRow(2)
        self.dialog.math_fields["geometry.function"].set_text("x^2")
        self.dialog.actions["geometry.compute"].click()
        latex = [row.get("latex", "") for row in self.dialog.result_view.rows]
        self.assertIn(r"\frac{\pi}{5}", latex)
        self.assertIn(r"\approx 1.478942858", latex)

        self.dialog.tool_list.setCurrentRow(3)
        self.dialog.actions["techniques.substitute"].click()
        self.assertIn("x(u) = sqrt(u)", self.dialog.result_text("integration_techniques"))

    def test_missing_closed_form_is_explained_in_chinese(self):
        dialog = self.make_dialog(text=ui_text("中文（简体）"))
        dialog._submit_job = lambda function, arguments, present: present(function(*arguments))
        dialog.tool_list.setCurrentRow(2)
        dialog.math_fields["geometry.function"].set_text("sin(x)")
        dialog.math_fields["geometry.upper"].set_text("pi")
        dialog.actions["geometry.compute"].click()
        text = dialog.result_text("arc_length_volume")
        self.assertIn("没有闭式解", text)
        self.assertNotIn("no closed form", text)
        self.assertIn("3.820197789", text)

    def test_shell_overlap_is_explained_in_chinese(self):
        dialog = self.make_dialog(text=ui_text("中文（简体）"))
        dialog._submit_job = lambda function, arguments, present: present(function(*arguments))
        dialog.tool_list.setCurrentRow(2)
        dialog.math_fields["geometry.function"].set_text("x^2")
        dialog.math_fields["geometry.lower"].set_text("-1")
        dialog.native_controls["geometry.axis"].setCurrentText("y")
        dialog.actions["geometry.compute"].click()
        text = dialog.result_text("arc_length_volume")
        self.assertIn("说明： 区域位于 y 轴两侧", text)
        self.assertIn("1.570796327", text)

    def test_helper_errors_are_shown_with_the_button_title(self):
        with patch(
            "qt_math_tools.compute_polar_area", side_effect=ValueError("bad radius")
        ), patch("qt_math_tools.show_error_dialog") as show_error:
            self.dialog.actions["polar.compute"].click()
        show_error.assert_called_once_with(self.dialog, "Compute Polar Area", "bad radius")


if __name__ == "__main__":
    unittest.main()
