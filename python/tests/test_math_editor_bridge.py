import json
import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole, normalize_mathlive_text
from i18n import ui_text
from qt_result_workspace import ResultWorkspace


class MathEditorBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _wait_until(self, predicate, timeout=8000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            self.app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            if predicate():
                return True
            time.sleep(0.01)
        self.app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        return bool(predicate())

    def _run_javascript(self, panel, script):
        result = []
        panel.web_view.page().runJavaScript(script, result.append)
        self.assertTrue(self._wait_until(lambda: result), "JavaScript did not return")
        return result[0]

    def _delete_panel(self, panel):
        panel.close()
        panel.deleteLater()
        QCoreApplication.sendPostedEvents(
            None, QEvent.Type.DeferredDelete
        )
        self.app.processEvents()

    def test_actual_local_page_reaches_qwebchannel_and_round_trips(self):
        panel = MathEditorPanel()
        field = panel.create_field("function", FieldRole.EXPRESSION, "x^2")
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        self.assertEqual(
            self._run_javascript(panel, "window.mathEditor.value('function')"),
            "x^2",
        )

        field.set_text("sin(x)")
        round_trip = self._run_javascript(
            panel, "window.mathEditor.value('function')"
        )
        self.assertEqual(
            normalize_mathlive_text(
                round_trip, FieldRole.EXPRESSION
            ).calculator_text,
            "sin(x)",
        )

    def test_actual_mathlive_input_reaches_adapter_as_calculator_text(self):
        panel = MathEditorPanel()
        field = panel.create_field("function", FieldRole.EXPRESSION)
        changes = []
        field.changed.connect(changes.append)
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        script = """
            (() => {
                const field = document.querySelector('[data-field-id="function"]');
                field.value = '1/';
                field.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
                return field.getValue('ascii-math');
            })()
        """
        self.assertEqual(self._run_javascript(panel, script), "1/")
        self.assertTrue(self._wait_until(lambda: changes == ["1/"]))
        self.assertEqual(field.get_text(), "1/")
        self.assertEqual(field.validation_status, "incomplete")

    def test_adapter_contract_and_keyboard_policy(self):
        panel = MathEditorPanel()
        field = panel.create_field("function", FieldRole.EXPRESSION, "x^2")
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        field.clear()
        self.assertEqual(field.get_text(), "")
        self.assertTrue(callable(field.dispatch_command))
        self.assertTrue(callable(field.insert_latex))
        self.assertFalse(panel.has_visible_virtual_keyboard())
        self.assertEqual(
            self._run_javascript(
                panel,
                "document.querySelector('[data-field-id=\\\"function\\\"]').mathVirtualKeyboardPolicy",
            ),
            "manual",
        )
        toggles = json.loads(self._run_javascript(
            panel,
            """
            JSON.stringify((() => {
                const field = document.querySelector('[data-field-id="function"]');
                const root = field.shadowRoot;
                const display = part => {
                    const element = root && root.querySelector(`[part~="${part}"]`);
                    return element ? getComputedStyle(element).display : 'missing';
                };
                return {
                    keyboard: display('virtual-keyboard-toggle'),
                    menu: display('menu-toggle'),
                };
            })())
            """,
        ))
        self.assertIn(toggles["keyboard"], ("none", "missing"))
        self.assertIn(toggles["menu"], ("none", "missing"))

    def test_dark_theme_keeps_live_field_readable(self):
        panel = MathEditorPanel()
        panel.create_field("function", FieldRole.EXPRESSION, "x^2", label="Function")
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        panel.set_theme("Dark")
        colors = json.loads(self._run_javascript(
            panel,
            """
            JSON.stringify((() => {
                const field = document.querySelector('[data-field-id="function"]');
                const label = document.querySelector('label');
                const style = getComputedStyle(field);
                return {
                    theme: document.documentElement.dataset.theme,
                    background: style.backgroundColor,
                    foreground: style.color,
                    label: getComputedStyle(label).color,
                };
            })())
            """,
        ))
        self.assertEqual(colors["theme"], "Dark")
        self.assertEqual(colors["background"], "rgb(17, 24, 39)")
        self.assertEqual(colors["foreground"], "rgb(243, 244, 246)")
        self.assertEqual(colors["label"], colors["foreground"])

    def test_labeled_integral_slots_form_identifiable_layout(self):
        panel = MathEditorPanel()
        reported_heights = []
        panel.content_height_changed.connect(reported_heights.append)
        panel.create_field(
            "upper", FieldRole.BOUND, label="Upper limit", slot="upper-bound"
        )
        panel.create_field(
            "lower", FieldRole.BOUND, label="Lower limit", slot="lower-bound"
        )
        panel.create_field(
            "function", FieldRole.EXPRESSION, label="Function", slot="integrand"
        )
        panel.create_field(
            "parameters", FieldRole.PARAMETERS, label="Parameters", slot="parameters"
        )
        panel.create_field(
            "split_points",
            FieldRole.SPLIT_POINTS,
            label="Split points",
            slot="split-points",
        )
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        layout = json.loads(self._run_javascript(
            panel,
            """
            JSON.stringify((() => {
                const box = id => document.querySelector(`[data-field-id="${id}"]`)
                    .closest('.math-field-container').getBoundingClientRect();
                const upper = box('upper');
                const lower = box('lower');
                const integrand = box('function');
                const parameters = box('parameters');
                const split = box('split_points');
                return {
                    integral: document.body.classList.contains('integral-layout'),
                    labels: Array.from(document.querySelectorAll('label')).map(x => x.textContent),
                    slots: Array.from(document.querySelectorAll('.math-field-container')).map(x => x.dataset.slot),
                    boundsBeforeIntegrand: upper.left < integrand.left && lower.left < integrand.left,
                    boundOrder: upper.top < lower.top,
                    compactIntegrand: integrand.height < upper.height + lower.height,
                    parametersBelow: parameters.top >= Math.max(lower.bottom, integrand.bottom),
                    splitBelow: split.top >= parameters.bottom,
                    gridAreas: getComputedStyle(document.body).gridTemplateAreas,
                    api: Object.keys(window.mathEditor).sort(),
                };
            })())
            """,
        ))
        self.assertTrue(layout["integral"])
        self.assertEqual(
            layout["labels"],
            ["Upper limit", "Lower limit", "Function", "Parameters", "Split points"],
        )
        self.assertEqual(
            layout["slots"],
            ["upper-bound", "lower-bound", "integrand", "parameters", "split-points"],
        )
        self.assertEqual(
            layout["api"],
            ["createField", "executeCommand", "focus", "insertLatex", "setEnabled", "setTheme", "setValue", "value"],
        )
        self.assertTrue(layout["boundsBeforeIntegrand"])
        self.assertTrue(layout["boundOrder"])
        self.assertTrue(layout["compactIntegrand"])
        self.assertTrue(layout["parametersBelow"])
        self.assertTrue(layout["splitBelow"])
        self.assertIn("integral upper integrand differential", layout["gridAreas"])
        self.assertTrue(self._wait_until(lambda: bool(reported_heights)))
        content_height = self._run_javascript(
            panel,
            "Math.ceil(document.querySelector('[data-field-id=\"split_points\"]')"
            ".closest('.math-field-container').getBoundingClientRect().bottom - "
            "document.body.getBoundingClientRect().top)",
        )
        self.assertLessEqual(abs(reported_heights[-1] - content_height), 1)

    def test_insert_latex_uses_the_current_cursor_and_resizes_the_integrand(self):
        panel = MathEditorPanel()
        panel.resize(900, 300)
        panel.show()
        field = panel.create_field(
            "function", FieldRole.EXPRESSION, "x+1", label="Function", slot="integrand"
        )
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        before = self._run_javascript(
            panel,
            "document.querySelector('[data-field-id=\"function\"]')"
            ".closest('.math-field-container').getBoundingClientRect().width",
        )
        self._run_javascript(
            panel,
            "(() => { const field = document.querySelector('[data-field-id=\"function\"]');"
            " field.focus(); field.position = 1; return field.position; })()",
        )
        field.insert_latex("^2")
        self.assertTrue(self._wait_until(lambda: field.get_text() == "x^2+1"))
        self.assertEqual(field.get_text(), "x^2+1")

        field.set_text("sin(x)+cos(x)+exp(x)+log(x)+sqrt(x)")
        details = json.loads(self._run_javascript(
            panel,
            "JSON.stringify((() => {"
            " const field = document.querySelector('[data-field-id=\"function\"]');"
            " const container = field.closest('.math-field-container');"
            " return {value: field.getValue('ascii-math'), style: container.style.width,"
            " width: container.getBoundingClientRect().width}; })())",
        ))
        self.assertEqual(
            details["value"].replace(" ", ""),
            "sin(x)+cos(x)+exp(x)+log(x)+sqrt(x)",
        )
        self.assertGreater(details["width"], before, details)

    def test_function_key_template_selects_a_placeholder_for_immediate_typing(self):
        panel = MathEditorPanel()
        field = panel.create_field("function", FieldRole.EXPRESSION)
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        field.insert_latex(r"\sin\left(#?\right)")
        self._run_javascript(
            panel,
            "(() => { const field = document.querySelector('[data-field-id=\"function\"]');"
            " field.insert('x', {format: 'latex', insertionMode: 'replaceSelection'});"
            " return field.getValue('ascii-math'); })()",
        )
        self.assertTrue(self._wait_until(lambda: field.get_text() == "sin(x)"))
        self.assertEqual(field.validation_status, "valid")

    def test_fields_without_slots_keep_generic_vertical_layout(self):
        panel = MathEditorPanel()
        panel.create_field("first", FieldRole.EXPRESSION, label="First")
        panel.create_field("second", FieldRole.BOUND, label="Second")
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(panel.is_ready))
        layout = json.loads(self._run_javascript(
            panel,
            """
            JSON.stringify((() => {
                const fields = Array.from(document.querySelectorAll('.math-field-container'));
                const first = fields[0].getBoundingClientRect();
                const second = fields[1].getBoundingClientRect();
                return {
                    integral: document.body.classList.contains('integral-layout'),
                    vertical: second.top >= first.bottom,
                };
            })())
            """,
        ))
        self.assertFalse(layout["integral"])
        self.assertTrue(layout["vertical"])

    def test_startup_failure_is_native_error_state_without_plain_text_fallback(self):
        panel = MathEditorPanel(editor_url="file:///missing-math-editor.html", startup_timeout_ms=250)
        failures = []
        panel.startup_failed.connect(failures.append)
        self.addCleanup(self._delete_panel, panel)

        self.assertTrue(self._wait_until(lambda: panel.startup_failed_state, timeout=3000))
        self.assertTrue(failures)
        self.assertIn("local math editor", failures[0].lower())
        self.assertEqual(panel.error_message, "The local math editor could not start.")
        self.assertFalse(panel.has_plain_text_fallback())

    def test_result_workspace_renders_localized_values_and_symbolic_steps(self):
        workspace = ResultWorkspace()
        workspace.resize(760, 360)
        workspace.set_text(ui_text("中文（简体）"))
        workspace.set_record({
            "type": "definite",
            "raw": "1/3",
            "raw_type": "exact",
            "numeric_value": 1 / 3,
            "elapsed": 0.125,
            "func": "x^2",
            "resolved_func": "x^2",
            "lower": "0",
            "upper": "1",
        })
        workspace.show()
        self.addCleanup(self._delete_panel, workspace)

        self.assertTrue(self._wait_until(workspace.is_ready))
        self.assertTrue(self._wait_until(
            lambda: workspace.model["steps_state"] == "available"
        ))
        rendered = json.loads(self._run_javascript(
            workspace,
            "JSON.stringify({"
            " exactLabel: document.getElementById('exact-label').textContent,"
            " resultLabel: document.getElementById('result-label').textContent,"
            " timeLabel: document.getElementById('time-label').textContent,"
            " stepsLabel: document.getElementById('steps-label').textContent,"
            " elapsed: document.getElementById('elapsed').textContent,"
            " mathFields: document.querySelectorAll('math-field').length,"
            " steps: document.querySelectorAll('.step').length,"
            " hidden: document.getElementById('steps').hidden"
            " })",
        ))
        self.assertEqual(
            [
                rendered["exactLabel"],
                rendered["resultLabel"],
                rendered["timeLabel"],
                rendered["stepsLabel"],
            ],
            ["精确结果", "积分结果", "积分所用总时间", "积分步骤"],
        )
        self.assertEqual(rendered["elapsed"], "0.125 s")
        self.assertGreaterEqual(rendered["mathFields"], 7)
        self.assertEqual(rendered["steps"], 5)
        self.assertFalse(rendered["hidden"])


if __name__ == "__main__":
    unittest.main()
