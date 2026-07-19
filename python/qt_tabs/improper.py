"""Qt Improper Integral tab."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from error_utils import friendly_error_message
from formatting import format_result_for_display
from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from parameter_utils import display_function_with_parameters, resolve_function_text
from qt_async import run_in_background
from qt_tabs.base import QtIntegrationTab
from symbolic_methods import compute_general_integral


class ImproperIntegralTab(QtIntegrationTab):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        panel_factory=MathEditorPanel,
        thread_pool: QThreadPool | None = None,
        text: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            parent,
            panel_factory=panel_factory,
            thread_pool=thread_pool,
            text=text,
        )
        self.upper = self.create_math_field(
            "upper",
            FieldRole.BOUND,
            label=self.field_label("upper", "Upper limit:"),
            slot="upper-bound",
        )
        self.lower = self.create_math_field(
            "lower",
            FieldRole.BOUND,
            label=self.field_label("lower", "Lower limit:"),
            slot="lower-bound",
        )
        self.function = self.create_math_field(
            "function",
            FieldRole.EXPRESSION,
            label=self.field_label("func", "Enter target function:"),
            slot="integrand",
        )
        self.parameters = self.create_math_field(
            "parameters",
            FieldRole.PARAMETERS,
            label=self.field_label("parameters", "Parameters:"),
            slot="parameters",
        )
        self.math_panel.setMinimumHeight(210)

        self.calculate_button = QPushButton("Compute Integral", self)
        self.reset_button = QPushButton("Reset", self)
        self.calculate_button.clicked.connect(self.compute)
        self.reset_button.clicked.connect(self.reset_requested.emit)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.calculate_button)
        actions.addWidget(self.reset_button)
        actions.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.math_panel)
        layout.addLayout(actions)
        layout.addWidget(self.result_label)
        layout.addStretch(1)
        self.set_language(self.text)

    def compute(self) -> None:
        func_text = self.function.get_text().strip()
        params_text = self.parameters.get_text().strip()
        lower = self.lower.get_text().strip()
        upper = self.upper.get_text().strip()
        try:
            resolved_func = resolve_function_text(func_text, params_text)
            shown_func = display_function_with_parameters(func_text, params_text)
            if not lower or not upper:
                raise ValueError(
                    "Please provide both lower and upper limits (use -inf/inf for infinity)."
                )
        except Exception as exc:
            self._show_calculation_error(exc)
            return

        if not self.guard_worker():
            return

        self.begin_work()
        run_in_background(
            self.thread_pool,
            lambda: compute_general_integral(resolved_func, lower, upper),
            on_result=lambda out: self._finish_result(
                out,
                shown_func,
                lower,
                upper,
                func_text,
                params_text,
                resolved_func,
            ),
            on_error=self._finish_error,
            on_finished=self.finish_work,
        )

    def _finish_result(
        self,
        out,
        shown_func,
        lower,
        upper,
        input_func,
        params_text,
        resolved_func,
    ) -> None:
        elapsed = self.elapsed()
        if out["type"] == "exact":
            display_str = format_result_for_display(out["expr"])["display"]
            self.result_label.setText(
                f"Result: {display_str}{self.format_elapsed(elapsed)}"
            )
        elif out["type"] == "divergent":
            display_str = "Divergent"
            self.result_label.setText(
                "Result: Divergent integral" + self.format_elapsed(elapsed)
            )
        else:
            display_str = "No closed-form"
            self.result_label.setText(
                "Result: No closed-form expression found" + self.format_elapsed(elapsed)
            )
        self.history_record.emit({
            "type": "improper",
            "display": f"Improper Integral: ∫[{lower}, {upper}] {shown_func} dx = {display_str}",
            "raw": out.get("expr"),
            "func": input_func,
            "lower": lower,
            "upper": upper,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": resolved_func,
        })
        self.plot_clear_requested.emit()

    def _finish_error(self, error: Exception) -> None:
        self.clear_result()
        self._show_calculation_error(error)

    def _show_calculation_error(self, error) -> None:
        message = friendly_error_message(
            error,
            self.function.get_text(),
            self.lower.get_text(),
            self.upper.get_text(),
        )
        self.show_error(
            "Error",
            "An error occurred in computing the integral: " + message,
        )

    def clear_inputs(self) -> None:
        for field in (self.function, self.parameters, self.lower, self.upper):
            field.clear()

    def refill(self, record: dict[str, object]) -> None:
        self.function.set_text(record.get("func", ""))
        self.parameters.set_text(record.get("params", ""))
        self.lower.set_text(record.get("lower", ""))
        self.upper.set_text(record.get("upper", ""))

    def set_language(self, text: dict[str, object]) -> None:
        super().set_language(text)
        self.calculate_button.setText(str(text.get("calc3", "Compute Integral")))
        self.reset_button.setText(str(text.get("reset", "Reset")))
        self.update_math_field_label("upper", "upper", "Upper limit:")
        self.update_math_field_label("lower", "lower", "Lower limit:")
        self.update_math_field_label("function", "func", "Enter target function:")
        self.update_math_field_label("parameters", "parameters", "Parameters:")


__all__ = ["ImproperIntegralTab"]
