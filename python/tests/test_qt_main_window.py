import os
import types
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import QEventLoop, QObject, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QWidget

import qt_dialogs
from qt_async import run_in_background
from qt_dialogs import (
    build_text_dialog,
    show_error_dialog,
    show_information_dialog,
    show_steps_dialog,
    show_suggestions_dialog,
    show_usage_dialog,
)
from qt_plot import QtPlotWidget


class _FakeMathPanel:
    def __init__(self):
        self.theme_name = "Light"

    def set_theme(self, name):
        self.theme_name = name


class _FakeTab(QWidget):
    history_record = Signal(object)
    plot_requested = Signal(str, float, float, object)
    plot_clear_requested = Signal()
    reset_requested = Signal()

    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.math_panel = _FakeMathPanel()
        self.function_text = ""
        self.parameter_text = ""
        self.language_text = {}
        self.refilled = None
        self.calculate_calls = 0
        self.compute_calls = 0
        self.reset_calls = 0
        self.keyboard_insertions = []
        self.keyboard_commands = []
        self.last_raw_result = "stale"
        self.last_raw_result_type = "exact"
        self.last_numeric_value = 1.0

    def get_function_text(self):
        return self.function_text

    def set_function_text(self, value):
        self.function_text = str(value)

    def set_parameter_text(self, value):
        self.parameter_text = str(value)
        return True

    def insert_at_cursor(self, latex):
        self.keyboard_insertions.append(latex)

    def dispatch_editor_command(self, command):
        self.keyboard_commands.append(command)

    def set_language(self, text):
        self.language_text = dict(text)

    def refill(self, record):
        self.refilled = record
        self.function_text = str(record.get("func", ""))

    def calculate(self):
        self.calculate_calls += 1

    def compute(self):
        self.compute_calls += 1

    def reset(self):
        self.reset_calls += 1
        self.function_text = ""


class _FakePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = None
        self.plot_calls = []
        self.clear_calls = 0

    def set_theme(self, theme):
        self.theme = theme

    def plot_function(self, *args):
        self.plot_calls.append(args)

    def clear(self):
        self.clear_calls += 1


class _FakeResultWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.text = {}
        self.theme_name = "Light"
        self.clear_calls = 0
        self.scroll_calls = 0

    def set_record(self, record):
        self.records.append(record)

    def set_text(self, text):
        self.text = dict(text)

    def set_theme(self, theme_name):
        self.theme_name = theme_name

    def clear(self):
        self.clear_calls += 1

    def scroll_to_steps(self):
        self.scroll_calls += 1


class QtPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _wait_for_finished(self, start):
        loop = QEventLoop()
        timeout = QTimer()
        timeout.setSingleShot(True)
        timeout.timeout.connect(loop.quit)
        timeout.start(3000)
        worker = start(loop.quit)
        loop.exec()
        timeout.stop()
        return worker

    def test_background_worker_emits_result_then_finished(self):
        events = []
        pool = QThreadPool()

        def start(finished):
            return run_in_background(
                pool,
                lambda: "result",
                lambda value: events.append(("result", value)),
                lambda error: events.append(("error", error)),
                lambda: (events.append(("finished", None)), finished()),
            )

        self._wait_for_finished(start)
        self.assertEqual([("result", "result"), ("finished", None)], events)

    def test_background_worker_emits_error_then_finished(self):
        events = []
        pool = QThreadPool()

        def fail():
            raise ValueError("calculation failed")

        def start(finished):
            return run_in_background(
                pool,
                fail,
                lambda value: events.append(("result", value)),
                lambda error: events.append(("error", str(error))),
                lambda: (events.append(("finished", None)), finished()),
            )

        self._wait_for_finished(start)
        self.assertEqual(
            [("error", "calculation failed"), ("finished", None)],
            events,
        )

    def test_plot_widget_can_clear_and_plot(self):
        widget = QtPlotWidget()
        widget.plot_function("x^2", -1, 1)
        self.assertGreater(len(widget.axes.lines), 0)
        widget.clear()
        self.assertEqual(len(widget.axes.lines), 0)

    def test_plot_uses_human_readable_exponential_and_power_notation(self):
        widget = QtPlotWidget()
        widget.plot_function("exp(x)*sin(x**2)", 1, 2)
        expected = "e^x · sin(x^2)"
        self.assertEqual(widget.axes.get_title(), f"Function Graph: {expected}")
        _handles, labels = widget.axes.get_legend_handles_labels()
        self.assertIn(f"f(x) = {expected}", labels)
        self.assertNotIn("exp(", widget.axes.get_title())
        self.assertNotIn("**", widget.axes.get_title())

    def test_plot_widget_starts_with_shared_clear_state(self):
        widget = QtPlotWidget()
        self.assertEqual(widget.axes.get_title(), "Function Graph")
        self.assertTrue(any(line.get_visible() for line in widget.axes.get_xgridlines()))
        self.assertTrue(any(line.get_visible() for line in widget.axes.get_ygridlines()))

    def test_plot_widget_exposes_navigation_toolbar(self):
        widget = QtPlotWidget()
        self.assertIsInstance(widget.toolbar, NavigationToolbar2QT)
        self.assertGreater(len(widget.toolbar.actions()), 0)
        self.assertIsNotNone(widget.toolbar.home)
        self.assertIsNotNone(widget.toolbar.pan)
        self.assertIsNotNone(widget.toolbar.zoom)
        self.assertIsNotNone(widget.toolbar.save_figure)

    def test_plot_widget_applies_theme_without_reimplementing_sampling(self):
        widget = QtPlotWidget()
        widget.set_theme(
            {
                "plot_bg": "#102030",
                "fg": "#f0f0f0",
                "muted": "#a0a0a0",
                "grid": "#303030",
                "accent": "#00aaee",
                "success": "#00cc66",
                "danger": "#ee3355",
            }
        )
        widget.plot_function("x", 0, 1)
        self.assertEqual(widget.figure.get_facecolor()[:3], (16 / 255, 32 / 255, 48 / 255))
        self.assertGreater(len(widget.axes.lines), 0)

    def test_text_dialog_contains_read_only_content_and_copy_button(self):
        dialog = build_text_dialog(None, "Steps", "content", copy_button=True)
        self.assertEqual(dialog.editor.toPlainText(), "content")
        self.assertTrue(dialog.editor.isReadOnly())
        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))
        dialog.copy_button.click()
        self.assertEqual(QGuiApplication.clipboard().text(), "content")
        dialog.close()

    def test_copy_label_is_optional_and_propagates_through_all_helpers(self):
        default_dialog = build_text_dialog(
            None,
            "Default",
            "content",
            copy_button=True,
        )
        self.assertEqual(default_dialog.copy_button.text(), "Copy")
        default_dialog.close()

        direct_dialog = qt_dialogs.show_text_dialog(
            None,
            "Direct",
            "content",
            copy_button=True,
            copy_label="复制",
        )
        self.assertEqual(direct_dialog.copy_button.text(), "复制")
        direct_dialog.close()

        for helper in (
            show_steps_dialog,
            show_suggestions_dialog,
            show_usage_dialog,
        ):
            with self.subTest(helper=helper.__name__):
                dialog = helper(None, "Title", "content", copy_label="复制")
                self.assertEqual(dialog.copy_button.text(), "复制")
                dialog.close()

    def test_shown_dialog_deletes_on_close_and_leaves_open_registry(self):
        dialog = qt_dialogs.show_text_dialog(None, "Details", "content")
        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose))
        self.assertIn(dialog, qt_dialogs._OPEN_DIALOGS)
        dialog.close()
        QApplication.processEvents()
        self.assertNotIn(dialog, qt_dialogs._OPEN_DIALOGS)

    def test_information_and_error_helpers_return_valid_modal_results(self):
        for helper in (show_information_dialog, show_error_dialog):
            with self.subTest(helper=helper.__name__):
                modal_state = []

                def accept_modal():
                    dialog = QApplication.activeModalWidget()
                    if dialog is not None:
                        modal_state.append(dialog.windowModality())
                        dialog.accept()

                QTimer.singleShot(0, accept_modal)
                result = helper(None, "Title", "content")
                QApplication.processEvents()

                self.assertEqual(result, QDialog.DialogCode.Accepted)
                self.assertNotIsInstance(result, qt_dialogs.TextDialog)
                self.assertEqual(modal_state, [Qt.WindowModality.ApplicationModal])
                self.assertNotIn(result, qt_dialogs._OPEN_DIALOGS)
                self.assertEqual(qt_dialogs._OPEN_DIALOGS, set())

    def test_text_dialog_helpers_create_read_only_surfaces(self):
        helpers = (
            show_steps_dialog,
            show_suggestions_dialog,
            show_usage_dialog,
        )
        for helper in helpers:
            with self.subTest(helper=helper.__name__):
                dialog = helper(None, "Title", "content")
                self.assertEqual(dialog.editor.toPlainText(), "content")
                self.assertTrue(dialog.editor.isReadOnly())
                dialog.close()


class QtMainWindowWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from qt_main_window import IntegralCalculatorWindow

        def tab_factory(mode, parent):
            return _FakeTab(mode, parent)

        self.window = IntegralCalculatorWindow(
            tab_factory=tab_factory,
            plot_factory=_FakePlot,
            result_workspace_factory=_FakeResultWorkspace,
        )

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def test_workspace_has_one_toolbar_splitter_tabs_history_and_progress(self):
        self.assertEqual(len(self.window.findChildren(type(self.window.toolbar))), 1)
        self.assertEqual(self.window.tabs.count(), 3)
        self.assertEqual(self.window.workspace.count(), 2)
        self.assertIsNotNone(self.window.history_list)
        self.assertIsNotNone(self.window.progress)
        self.assertEqual(self.window.left_workspace.count(), 2)

    def test_keyboard_and_history_refill_target_active_tab(self):
        self.window.tabs.setCurrentIndex(0)
        self.window.insert_math_at_cursor(r"\sin\left(#?\right)")
        self.window.dispatch_math_command("moveToPreviousChar")
        self.assertEqual(
            self.window.active_tab().keyboard_insertions,
            [r"\sin\left(#?\right)"],
        )
        self.assertEqual(
            self.window.active_tab().keyboard_commands,
            ["moveToPreviousChar"],
        )

        self.window.add_history({
            "type": "definite",
            "display": "record",
            "func": "sin(x)",
            "lower": "0",
            "upper": "pi",
            "raw": "2",
            "raw_type": "exact",
            "numeric_value": 2.0,
        })
        self.window.refill_history_row(0)
        self.assertIs(self.window.active_tab(), self.window.tab1)
        self.assertEqual(self.window.active_tab().get_function_text(), "sin(x)")
        self.assertEqual(self.window.last_raw_result, "2")
        self.assertIs(self.window.result_workspace.records[-1], self.window.history[0])

    def test_math_keyboard_is_a_toggleable_always_on_top_tool_window(self):
        self.assertFalse(hasattr(self.window, "template_combo"))
        self.assertFalse(hasattr(self.window, "insert_template_button"))
        self.assertFalse(hasattr(self.window, "favorite_combo"))
        self.assertFalse(hasattr(self.window, "export_button"))
        self.assertTrue(self.window.math_keyboard.isHidden())
        self.assertTrue(self.window.math_keyboard.isWindow())
        self.assertIs(self.window.math_keyboard.parent(), self.window)
        flags = self.window.math_keyboard.windowFlags()
        self.assertTrue(flags & Qt.WindowType.Tool)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertEqual(
            self.window.math_keyboard_button.focusPolicy(), Qt.FocusPolicy.NoFocus
        )

        self.window.math_keyboard_button.click()
        self.assertTrue(self.window.math_keyboard_button.isChecked())
        self.assertFalse(self.window.math_keyboard.isHidden())

        self.window.math_keyboard_button.click()
        self.assertFalse(self.window.math_keyboard_button.isChecked())
        self.assertTrue(self.window.math_keyboard.isHidden())

        self.window.math_keyboard_button.click()
        self.window.math_keyboard.close()
        QApplication.processEvents()
        self.assertFalse(self.window.math_keyboard_button.isChecked())
        self.assertTrue(self.window.math_keyboard.isHidden())

    def test_history_routing_and_double_compute_preserve_record_types(self):
        records = [
            {"type": "numerical", "display": "advanced", "func": "x"},
            {"type": "improper", "display": "improper", "func": "1/x"},
        ]
        for record in records:
            self.window.add_history(record)

        self.window.refill_and_compute_history_row(0)
        self.assertIs(self.window.active_tab(), self.window.tab2)
        self.assertEqual(self.window.tab2.calculate_calls, 1)

        self.window.refill_and_compute_history_row(1)
        self.assertIs(self.window.active_tab(), self.window.tab3)
        self.assertEqual(self.window.tab3.compute_calls, 1)

    def test_suggestion_dialog_applies_selected_expression(self):
        self.window.active_tab().set_function_text("sinx")
        dialog = self.window.show_input_suggestions()
        self.assertGreater(dialog.suggestions_list.count(), 0)
        dialog.suggestions_list.setCurrentRow(0)
        dialog.apply_button.click()
        self.assertEqual(self.window.active_tab().get_function_text(), "sin(x)")

    def test_language_updates_window_tabs_controls_and_all_tabs(self):
        self.window.change_language("中文（简体）")
        self.assertEqual(self.window.windowTitle(), self.window.text["title"])
        self.assertEqual(self.window.tabs.tabText(0), self.window.text["tabs"][0])
        self.assertEqual(self.window.usage_button.text(), self.window.text["usage"])
        self.assertEqual(
            self.window.math_keyboard_button.text(), self.window.text["math_keyboard"]
        )
        for tab in self.window.integration_tabs:
            self.assertEqual(tab.language_text["title"], self.window.text["title"])
        self.assertEqual(
            self.window.result_workspace.text["exact_result"], "精确结果"
        )

    def test_theme_reaches_plot_and_every_math_panel(self):
        self.window.apply_theme("Dark")
        self.assertEqual(self.window.theme_name, "Dark")
        self.assertIs(self.window.plot_widget.theme, self.window.theme)
        for tab in self.window.integration_tabs:
            self.assertEqual(tab.math_panel.theme_name, "Dark")
        self.assertEqual(self.window.result_workspace.theme_name, "Dark")

    def test_tab_signals_feed_central_history_plot_and_reset(self):
        self.window.tab1.history_record.emit({"type": "definite", "display": "row"})
        self.assertEqual(self.window.history_list.count(), 1)
        self.window.tab1.plot_requested.emit("x", 0.0, 1.0, None)
        self.assertEqual(self.window.plot_widget.plot_calls[-1], ("x", 0.0, 1.0, None))

        self.window.tab1.reset_requested.emit()
        self.assertEqual(self.window.history, [])
        self.assertGreaterEqual(self.window.plot_widget.clear_calls, 1)

    def test_central_reset_clears_all_shared_and_exact_state(self):
        self.window.add_history({"type": "definite", "display": "row", "raw": "1"})
        self.window.last_raw_result_type = "exact"
        self.window.last_numeric_value = 1.0
        self.window.progress.setRange(0, 0)
        self.window.progress.show()
        self.window.reset_inputs()

        self.assertEqual(self.window.history, [])
        self.assertEqual(self.window.history_list.count(), 0)
        self.assertFalse(self.window.progress.isVisible())
        self.assertEqual((self.window.progress.minimum(), self.window.progress.maximum()), (0, 100))
        self.assertEqual(self.window.progress.value(), 0)
        self.assertIsNone(self.window.last_record)
        self.assertIsNone(self.window.last_raw_result)
        self.assertGreaterEqual(self.window.result_workspace.clear_calls, 1)
        for tab in self.window.integration_tabs:
            self.assertEqual(tab.reset_calls, 1)
            self.assertIsNone(tab.last_raw_result)
            self.assertIsNone(tab.last_raw_result_type)
            self.assertIsNone(tab.last_numeric_value)

    def test_usage_and_steps_reuse_existing_content_generators(self):
        with patch("qt_main_window.show_usage_dialog") as usage_dialog:
            usage = self.window.show_usage_instructions()
        self.assertIn("sin(x)", usage)
        usage_dialog.assert_called_once()

        self.window.last_record = {"type": "definite", "display": "row"}
        with patch("qt_main_window.build_steps_for_record", return_value="steps") as builder, patch(
            "qt_main_window.show_steps_dialog"
        ) as steps_dialog:
            self.assertEqual(self.window.show_steps(), "steps")
        builder.assert_called_once_with(self.window.last_record)
        steps_dialog.assert_called_once()
        self.assertEqual(self.window.result_workspace.scroll_calls, 1)

    def test_copy_enabled_dialogs_receive_localized_copy_label(self):
        self.window.change_language("中文（简体）")
        copy_label = self.window.text["copy"]
        with patch("qt_main_window.build_steps_for_record", return_value="steps"), patch(
            "qt_main_window.show_steps_dialog"
        ) as steps_dialog:
            self.window.show_steps()
        steps_dialog.assert_called_once_with(
            self.window,
            self.window.text["show_steps"],
            "steps",
            copy_label,
        )

        with patch("qt_main_window.show_usage_dialog") as usage_dialog:
            usage = self.window.show_usage_instructions()
        usage_dialog.assert_called_once_with(
            self.window,
            self.window.text["usage"],
            usage,
            copy_label,
        )

    def test_math_tools_preserves_opening_context_and_late_binds_insertions(self):
        created = []

        class StrictMathToolsDialog:
            def __init__(
                self,
                insert_function,
                insert_parameters,
                parent,
                *,
                initial_function,
                text,
                theme_name,
            ):
                self.insert_function = insert_function
                self.insert_parameters = insert_parameters
                self.parent = parent
                self.initial_function = initial_function
                self.text = text
                self.theme_name = theme_name
                self.was_shown = False
                created.append(self)

            def show(self):
                self.was_shown = True

        module = types.SimpleNamespace(MathToolsDialog=StrictMathToolsDialog)
        self.window.tabs.setCurrentIndex(1)
        self.window.tab2.set_function_text("sin(x)")
        self.window.change_language("中文（简体）")
        self.window.apply_theme("Dark")
        with patch.dict("sys.modules", {"qt_math_tools": module}):
            dialog = self.window.show_math_tools()

        self.assertIs(dialog, created[0])
        self.assertIs(dialog.parent, self.window)
        self.assertEqual(dialog.initial_function, "sin(x)")
        self.assertIs(dialog.text, self.window.text)
        self.assertEqual(dialog.theme_name, "Dark")
        self.assertTrue(dialog.was_shown)
        self.window.tabs.setCurrentIndex(0)
        dialog.insert_function("a*x")
        dialog.insert_parameters("a=2")
        self.assertEqual(self.window.tab1.function_text, "a*x")
        self.assertEqual(self.window.tab1.parameter_text, "a=2")
        self.assertEqual(self.window.tab2.function_text, "sin(x)")
        self.assertEqual(self.window.tab2.parameter_text, "")


class QtAppTests(unittest.TestCase):
    def test_main_constructs_shows_and_enters_event_loop(self):
        import qt_app

        fake_app = MagicMock()
        fake_app.exec.return_value = 17
        fake_window = MagicMock()
        with patch.object(qt_app.QApplication, "instance", return_value=fake_app), patch.object(
            qt_app, "IntegralCalculatorWindow", return_value=fake_window
        ):
            self.assertEqual(qt_app.main(), 17)
        fake_app.setApplicationName.assert_called_once_with("Integral Calculator")
        fake_window.show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
