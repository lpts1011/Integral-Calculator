"""PySide6 main window and shared calculator workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from i18n import INSTRUCTIONS, ui_text
from input_suggestions import suggest_expression, suggestion_report
from qt_dialogs import (
    show_steps_dialog,
    show_usage_dialog,
)
from qt_math_keyboard import MathKeyboardWindow
from qt_plot import QtPlotWidget
from qt_result_workspace import ResultWorkspace
from qt_tabs import AdvancedIntegrationTab, BasicIntegrationTab, ImproperIntegralTab
from step_explainer import build_steps_for_record
from theme_utils import THEMES


class SuggestionDialog(QDialog):
    """Selectable expression suggestions bound to the active calculator tab."""

    def __init__(
        self,
        parent: QWidget,
        title: str,
        report: str,
        suggestions: list[str],
        apply_text: str,
        on_apply: Callable[[str], None],
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(title)
        self.resize(560, 320)

        report_label = QLabel(report, self)
        report_label.setWordWrap(True)
        self.suggestions_list = QListWidget(self)
        self.suggestions_list.addItems(suggestions)
        if suggestions:
            self.suggestions_list.setCurrentRow(0)
        self.apply_button = QPushButton(apply_text, self)

        layout = QVBoxLayout(self)
        layout.addWidget(report_label)
        layout.addWidget(self.suggestions_list, stretch=1)
        layout.addWidget(self.apply_button, alignment=Qt.AlignmentFlag.AlignRight)

        def apply_current() -> None:
            item = self.suggestions_list.currentItem()
            if item is None:
                return
            on_apply(item.text())
            self.accept()

        self.apply_button.clicked.connect(apply_current)
        self.suggestions_list.itemDoubleClicked.connect(
            lambda _item: apply_current()
        )


class IntegralCalculatorWindow(QMainWindow):
    """Own shared UI state while integration tabs keep calculation behavior."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        tab_factory: Callable[[str, QWidget], QWidget] | None = None,
        panel_factory: Callable[..., Any] | None = None,
        plot_factory: Callable[[QWidget], QWidget] = QtPlotWidget,
        result_workspace_factory: Callable[[QWidget], QWidget] = ResultWorkspace,
    ) -> None:
        super().__init__(parent)
        self.history: list[dict[str, Any]] = []
        self.last_record: dict[str, Any] | None = None
        self.last_raw_result: Any = None
        self.last_raw_result_type: str | None = None
        self.last_numeric_value: float | None = None
        self.theme_name = "Light"
        self.theme = THEMES[self.theme_name]
        self.language = "English"
        self.text = ui_text(self.language)
        self._suggestion_dialogs: set[SuggestionDialog] = set()
        self._math_tools_dialogs: set[QDialog] = set()
        self._math_keyboard_positioned = False

        self.resize(1280, 820)
        self._build_toolbars()
        self._build_workspace(
            tab_factory,
            panel_factory,
            plot_factory,
            result_workspace_factory,
        )
        self._connect_workflows()
        self.change_language(self.language)
        self.apply_theme(self.theme_name)

    def _build_toolbars(self) -> None:
        self.toolbar = QToolBar("Calculator Actions", self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.usage_button = QPushButton(self)
        self.math_keyboard_button = QPushButton(self)
        self.math_keyboard_button.setCheckable(True)
        self.math_keyboard_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.steps_button = QPushButton(self)
        self.suggest_button = QPushButton(self)
        self.math_tools_button = QPushButton(self)
        self.language_label = QLabel("Language:", self)
        self.language_combo = QComboBox(self)
        self.language_combo.addItems(INSTRUCTIONS.keys())
        self.theme_label = QLabel(self)
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(THEMES.keys())

        for widget in (
            self.usage_button,
            self.math_keyboard_button,
            self.steps_button,
            self.suggest_button,
            self.math_tools_button,
            self.language_label,
            self.language_combo,
            self.theme_label,
            self.theme_combo,
        ):
            self.toolbar.addWidget(widget)

    def _build_workspace(
        self,
        tab_factory: Callable[[str, QWidget], QWidget] | None,
        panel_factory: Callable[..., Any] | None,
        plot_factory: Callable[[QWidget], QWidget],
        result_workspace_factory: Callable[[QWidget], QWidget],
    ) -> None:
        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(8, 8, 8, 8)
        self.math_keyboard = MathKeyboardWindow(self)
        self.math_keyboard.hide()
        self.workspace = QSplitter(Qt.Orientation.Horizontal, central)
        central_layout.addWidget(self.workspace)
        self.setCentralWidget(central)

        self.left_workspace = QSplitter(Qt.Orientation.Vertical, self.workspace)
        self.left_workspace.setChildrenCollapsible(False)
        self.tabs = QTabWidget(self.left_workspace)
        if tab_factory is not None:
            self.tab1 = tab_factory("basic", self.tabs)
            self.tab2 = tab_factory("advanced", self.tabs)
            self.tab3 = tab_factory("improper", self.tabs)
        else:
            options: dict[str, Any] = {"text": self.text}
            if panel_factory is not None:
                options["panel_factory"] = panel_factory
            self.tab1 = BasicIntegrationTab(self.tabs, **options)
            self.tab2 = AdvancedIntegrationTab(self.tabs, **options)
            self.tab3 = ImproperIntegralTab(self.tabs, **options)
        self.integration_tabs = (self.tab1, self.tab2, self.tab3)
        for tab, label in zip(self.integration_tabs, self.text["tabs"]):
            self.tabs.addTab(tab, str(label))
        self.result_workspace = result_workspace_factory(self.left_workspace)
        self.left_workspace.addWidget(self.tabs)
        self.left_workspace.addWidget(self.result_workspace)
        self.left_workspace.setStretchFactor(0, 5)
        self.left_workspace.setStretchFactor(1, 2)
        self.left_workspace.setSizes([560, 220])

        right_panel = QWidget(self.workspace)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = plot_factory(right_panel)
        self.history_label = QLabel(self)
        self.history_list = QListWidget(self)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        right_layout.addWidget(self.plot_widget, stretch=3)
        right_layout.addWidget(self.history_label)
        right_layout.addWidget(self.history_list, stretch=1)
        right_layout.addWidget(self.progress)

        self.workspace.addWidget(self.left_workspace)
        self.workspace.addWidget(right_panel)
        self.workspace.setStretchFactor(0, 3)
        self.workspace.setStretchFactor(1, 2)

    def _connect_workflows(self) -> None:
        self.usage_button.clicked.connect(self.show_usage_instructions)
        self.math_keyboard_button.toggled.connect(self.set_math_keyboard_visible)
        self.math_keyboard.close_requested.connect(
            lambda: self.math_keyboard_button.setChecked(False)
        )
        self.math_keyboard.insert_requested.connect(self.insert_math_at_cursor)
        self.math_keyboard.command_requested.connect(self.dispatch_math_command)
        self.steps_button.clicked.connect(self.show_steps)
        self.suggest_button.clicked.connect(self.show_input_suggestions)
        self.math_tools_button.clicked.connect(self.show_math_tools)
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.history_list.itemClicked.connect(
            lambda item: self.refill_history_row(self.history_list.row(item))
        )
        self.history_list.itemDoubleClicked.connect(
            lambda item: self.refill_and_compute_history_row(
                self.history_list.row(item)
            )
        )
        for tab in self.integration_tabs:
            tab.history_record.connect(self.add_history)
            tab.plot_requested.connect(self.plot_function)
            tab.plot_clear_requested.connect(self.clear_plot)
            tab.reset_requested.connect(self.reset_inputs)

    def active_tab(self):
        return self.integration_tabs[self.tabs.currentIndex()]

    def add_history(self, record: dict[str, Any]) -> None:
        self.history.append(record)
        self.history_list.addItem(str(record.get("display", "")))
        self.last_record = record
        self.last_raw_result = record.get("raw")
        self.last_raw_result_type = record.get("raw_type")
        self.last_numeric_value = record.get("numeric_value")
        self.result_workspace.set_record(record)

    def _tab_for_record(self, record: dict[str, Any]):
        record_type = record.get("type")
        if record_type in ("definite", "indefinite"):
            return self.tab1, 0
        if record_type in (
            "numerical",
            "symbolic",
            "symbolic_indefinite",
            "comparison",
        ):
            return self.tab2, 1
        if record_type == "improper":
            return self.tab3, 2
        return None, -1

    def refill_history_row(self, row: int) -> dict[str, Any] | None:
        if row < 0 or row >= len(self.history):
            return None
        record = self.history[row]
        tab, index = self._tab_for_record(record)
        if tab is None:
            return None
        tab.refill(record)
        self.tabs.setCurrentIndex(index)
        self.last_record = record
        self.last_raw_result = record.get("raw")
        self.last_raw_result_type = record.get("raw_type")
        self.last_numeric_value = record.get("numeric_value")
        self.result_workspace.set_record(record)
        if tab is self.tab1:
            for name, value in (
                ("last_raw_result", self.last_raw_result),
                ("last_raw_result_type", self.last_raw_result_type),
                ("last_numeric_value", self.last_numeric_value),
            ):
                if hasattr(tab, name):
                    setattr(tab, name, value)
        return record

    def refill_and_compute_history_row(self, row: int) -> None:
        record = self.refill_history_row(row)
        if record is None:
            return
        record_type = record.get("type")
        if record_type in ("definite", "indefinite"):
            self.tab1.calculate()
        elif record_type in ("numerical", "symbolic", "symbolic_indefinite"):
            self.tab2.calculate()
        elif record_type == "improper":
            self.tab3.compute()

    def plot_function(
        self,
        function: str,
        lower: float,
        upper: float,
        split_points: object = None,
    ) -> None:
        self.plot_widget.plot_function(function, lower, upper, split_points)

    def clear_plot(self) -> None:
        self.plot_widget.clear()

    def set_math_keyboard_visible(self, visible: bool) -> None:
        if not visible:
            self.math_keyboard.hide()
            return
        if not self._math_keyboard_positioned:
            keyboard_size = self.math_keyboard.size()
            calculator = self.frameGeometry()
            x = calculator.x() + max(16, (calculator.width() - keyboard_size.width()) // 2)
            y = calculator.y() + 72
            self.math_keyboard.move(x, y)
            self._math_keyboard_positioned = True
        self.math_keyboard.show()
        self.math_keyboard.raise_()

    def insert_math_at_cursor(self, latex: str) -> None:
        inserter = getattr(self.active_tab(), "insert_at_cursor", None)
        if inserter is not None:
            inserter(str(latex))

    def dispatch_math_command(self, command: str) -> None:
        dispatcher = getattr(self.active_tab(), "dispatch_editor_command", None)
        if dispatcher is not None:
            dispatcher(str(command))

    def show_steps(self) -> str:
        content = build_steps_for_record(self.last_record)
        self.result_workspace.scroll_to_steps()
        show_steps_dialog(
            self,
            str(self.text.get("show_steps", "Show Steps")),
            content,
            str(self.text.get("copy", "Copy")),
        )
        return content

    def show_input_suggestions(self) -> SuggestionDialog:
        current = self.active_tab().get_function_text().strip()
        dialog = SuggestionDialog(
            self,
            str(self.text.get("suggest_input", "Suggest Input")),
            suggestion_report(current),
            suggest_expression(current),
            str(self.text.get("use_selected", "Use Selected")),
            lambda value: self.active_tab().set_function_text(value),
        )
        self._suggestion_dialogs.add(dialog)
        dialog.destroyed.connect(lambda: self._suggestion_dialogs.discard(dialog))
        dialog.show()
        return dialog

    def show_usage_instructions(self) -> str:
        content = "\n".join(INSTRUCTIONS.get(self.language, INSTRUCTIONS["English"]))
        show_usage_dialog(
            self,
            str(self.text["usage"]),
            content,
            str(self.text.get("copy", "Copy")),
        )
        return content

    def show_math_tools(self):
        from qt_math_tools import MathToolsDialog

        initial_function = self.active_tab().get_function_text()
        dialog = MathToolsDialog(
            lambda value: self.active_tab().set_function_text(value),
            lambda value: self.active_tab().set_parameter_text(value),
            self,
            initial_function=initial_function,
            text=self.text,
            theme_name=self.theme_name,
        )
        if hasattr(dialog, "show"):
            dialog.show()
        if isinstance(dialog, QDialog):
            self._math_tools_dialogs.add(dialog)
            dialog.destroyed.connect(
                lambda: self._math_tools_dialogs.discard(dialog)
            )
        return dialog

    def change_language(self, language: str) -> None:
        if language not in INSTRUCTIONS:
            language = "English"
        self.language = language
        self.text = ui_text(language)
        self.setWindowTitle(str(self.text["title"]))
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentText(language)
        self.language_combo.blockSignals(False)

        for index, label in enumerate(self.text["tabs"]):
            self.tabs.setTabText(index, str(label))
        self.usage_button.setText(str(self.text["usage"]))
        keyboard_text = str(self.text.get("math_keyboard", "Math Keyboard"))
        self.math_keyboard_button.setText(keyboard_text)
        self.math_keyboard.set_title(keyboard_text)
        self.steps_button.setText(str(self.text.get("show_steps", "Show Steps")))
        self.suggest_button.setText(
            str(self.text.get("suggest_input", "Suggest Input"))
        )
        self.math_tools_button.setText(
            str(self.text.get("math_tools", "Math Tools"))
        )
        self.theme_label.setText(str(self.text["theme"]))
        self.history_label.setText(str(self.text["history"]))
        self.result_workspace.set_text(self.text)
        for tab in self.integration_tabs:
            tab.set_language(self.text)
        self.apply_theme(self.theme_name)

    def apply_theme(self, theme_name: str) -> None:
        self.theme_name = theme_name if theme_name in THEMES else "Light"
        self.theme = THEMES[self.theme_name]
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(self.theme_name)
        self.theme_combo.blockSignals(False)
        t = self.theme
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {t['bg']}; color: {t['fg']}; }}
            QToolBar {{ background: {t['panel']}; border: 0; spacing: 5px; padding: 3px; }}
            QTabWidget::pane {{ border: 1px solid {t['grid']}; background: {t['panel']}; }}
            QTabBar::tab {{ background: {t['panel']}; color: {t['fg']}; padding: 7px 12px; }}
            QTabBar::tab:selected {{ background: {t['entry_bg']}; border-bottom: 2px solid {t['accent']}; }}
            QPushButton {{ background: {t['button_bg']}; color: {t['button_fg']}; border: 1px solid {t['grid']}; padding: 5px 9px; }}
            QPushButton:hover {{ border-color: {t['accent']}; }}
            QPushButton:checked {{ border-color: {t['accent']}; background: {t['entry_bg']}; }}
            QDialog#mathKeyboardWindow {{ background: {t['panel']}; }}
            QDialog#mathKeyboardWindow QToolButton {{ background: {t['entry_bg']}; color: {t['entry_fg']}; border: 1px solid {t['grid']}; padding: 4px; }}
            QDialog#mathKeyboardWindow QToolButton:hover {{ border-color: {t['accent']}; }}
            QComboBox, QListWidget {{ background: {t['entry_bg']}; color: {t['entry_fg']}; border: 1px solid {t['grid']}; padding: 3px; }}
            QProgressBar {{ border: 1px solid {t['grid']}; background: {t['panel']}; text-align: center; }}
            QProgressBar::chunk {{ background: {t['accent']}; }}
            """
        )
        self.plot_widget.set_theme(self.theme)
        self.result_workspace.set_theme(self.theme_name)
        for tab in self.integration_tabs:
            panel = getattr(tab, "math_panel", None)
            if panel is not None and hasattr(panel, "set_theme"):
                panel.set_theme(self.theme_name)

    def reset_inputs(self) -> None:
        for tab in self.integration_tabs:
            reset = getattr(tab, "reset", None)
            signals_were_blocked = tab.blockSignals(True)
            try:
                if reset is not None:
                    reset()
                else:
                    tab.clear_inputs()
                    tab.clear_result()
            finally:
                tab.blockSignals(signals_were_blocked)
            for name in (
                "last_raw_result",
                "last_raw_result_type",
                "last_numeric_value",
            ):
                if hasattr(tab, name):
                    setattr(tab, name, None)
        self.history.clear()
        self.history_list.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        self.clear_plot()
        self.last_record = None
        self.last_raw_result = None
        self.last_raw_result_type = None
        self.last_numeric_value = None
        self.result_workspace.clear()


__all__ = ["IntegralCalculatorWindow", "SuggestionDialog"]
