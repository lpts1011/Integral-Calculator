"""Shared contracts for the Qt integration tabs."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import QLabel, QWidget

from i18n import ui_text
from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from qt_dialogs import show_error_dialog, show_information_dialog


class QtIntegrationTab(QWidget):
    history_record = Signal(object)
    plot_requested = Signal(str, float, float, object)
    plot_clear_requested = Signal()
    reset_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        panel_factory: Callable[..., MathEditorPanel] = MathEditorPanel,
        thread_pool: QThreadPool | None = None,
        text: dict[str, object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.text = dict(text or ui_text("English"))
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self.worker_running = False
        self.start_time: float | None = None
        self.math_panel = panel_factory(self)
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        self.result_label.setObjectName("integrationResult")

    def create_math_field(
        self,
        field_id: str,
        role: FieldRole,
        initial: str = "",
        *,
        label: str | None = None,
        slot: str | None = None,
    ):
        field = self.math_panel.create_field(
            field_id,
            role,
            initial,
            label=label,
            slot=slot,
        )
        field.submitted.connect(self._submit)
        return field

    def field_label(self, key: str, fallback: str) -> str:
        return str(self.text.get(key, fallback))

    def update_math_field_label(self, field_id: str, key: str, fallback: str) -> None:
        setter = getattr(self.math_panel, "set_field_label", None)
        if setter is not None:
            setter(field_id, self.field_label(key, fallback))

    def _submit(self) -> None:
        callback = getattr(self, "calculate", None) or getattr(self, "compute", None)
        if callback is not None:
            callback()

    def get_function_text(self) -> str:
        return self.function.get_text()

    def set_function_text(self, value: object) -> None:
        self.function.set_text(value)

    def set_parameter_text(self, value: object) -> bool:
        self.parameters.set_text(value)
        return True

    def insert_at_cursor(self, latex: str) -> None:
        self.math_panel.insert_latex(latex)

    def dispatch_editor_command(self, command: str) -> None:
        self.math_panel.dispatch_active_command(command)

    def clear_result(self) -> None:
        self.result_label.clear()

    def format_elapsed(self, elapsed: float | None) -> str:
        if elapsed is None:
            return ""
        label = str(self.text.get("time", "Time"))
        return f"\n{label}: {elapsed:.3f}s"

    def elapsed(self) -> float | None:
        if self.start_time is None:
            return None
        return time.perf_counter() - self.start_time

    def begin_work(self, status: str = "Computing...") -> None:
        self.worker_running = True
        self.start_time = time.perf_counter()
        self.result_label.setText(status)

    def finish_work(self) -> None:
        self.worker_running = False

    def guard_worker(self) -> bool:
        if not self.worker_running:
            return True
        show_information_dialog(self, "Info", "A computation is already running.")
        return False

    def show_error(self, title: str, message: str) -> None:
        show_error_dialog(self, title, message)

    def reset(self) -> None:
        self.clear_inputs()
        self.clear_result()
        self.plot_clear_requested.emit()

    def set_language(self, text: dict[str, object]) -> None:
        self.text = dict(text)


__all__ = ["QtIntegrationTab"]
