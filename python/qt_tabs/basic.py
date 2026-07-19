"""Qt Basic Integration tab."""

from __future__ import annotations

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from error_utils import friendly_error_message
from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from parameter_utils import display_function_with_parameters, resolve_function_text
from parser_utils import parse_input_to_float
from qt_async import run_in_background
from qt_dialogs import show_information_dialog
from qt_tabs.base import QtIntegrationTab
from symbolic_methods import compute_tab1_result


class BasicIntegrationTab(QtIntegrationTab):
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
        self.last_raw_result = None
        self.last_raw_result_type: str | None = None
        self.last_numeric_value: float | None = None

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
        self.math_panel.setMinimumHeight(290)

        self.calculate_button = QPushButton("Calculate Integral", self)
        self.exact_button = QPushButton("View Exact Result", self)
        self.reset_button = QPushButton("Reset", self)
        self.calculate_button.clicked.connect(self.calculate)
        self.exact_button.clicked.connect(self.show_exact_result)
        self.reset_button.clicked.connect(self.reset_requested.emit)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.calculate_button)
        actions.addWidget(self.exact_button)
        actions.addWidget(self.reset_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.math_panel)
        layout.addLayout(actions)
        layout.addWidget(self.result_label)
        layout.addStretch(1)
        self.set_language(self.text)

    def calculate(self) -> None:
        if not self.guard_worker():
            return
        func_text = self.function.get_text().strip()
        params_text = self.parameters.get_text().strip()
        lower_text = self.lower.get_text().strip()
        upper_text = self.upper.get_text().strip()
        try:
            resolved_func = resolve_function_text(func_text, params_text)
            shown_func = display_function_with_parameters(func_text, params_text)
        except Exception as exc:
            self._show_calculation_error(exc)
            return

        self.begin_work()

        def work():
            result = compute_tab1_result(resolved_func, lower_text, upper_text)
            result.update({
                "input_func": func_text,
                "params_text": params_text,
                "shown_func": shown_func,
                "resolved_func": resolved_func,
            })
            return result

        run_in_background(
            self.thread_pool,
            work,
            on_result=self._finish_result,
            on_error=self._finish_error,
            on_finished=self.finish_work,
        )

    def _finish_result(self, result: dict[str, object]) -> None:
        elapsed = self.elapsed()
        self.last_raw_result = result["raw_result"]
        self.last_raw_result_type = str(result["raw_type"])
        self.last_numeric_value = result["numeric_value"]
        if result["kind"] == "definite":
            self._finish_definite_result(result, elapsed)
        else:
            self._finish_indefinite_result(result, elapsed)

    def _finish_definite_result(self, result, elapsed) -> None:
        self.result_label.setText(
            f"Definite Integral: {result['display_str']}{self.format_elapsed(elapsed)}"
        )
        try:
            lower = parse_input_to_float(result["lower_text"])
            upper = parse_input_to_float(result["upper_text"])
            self.plot_requested.emit(result["resolved_func"], lower, upper, None)
        except Exception:
            self.plot_clear_requested.emit()

        self.history_record.emit({
            "type": "definite",
            "display": f"Definite: ∫[{result['lower_text']}, {result['upper_text']}] {result['shown_func']} dx = {result['display_str']}",
            "raw": self.last_raw_result,
            "raw_type": self.last_raw_result_type,
            "numeric_value": self.last_numeric_value,
            "func": result.get("input_func", result["shown_func"]),
            "lower": result["lower_text"],
            "upper": result["upper_text"],
            "error": result["numeric_err"],
            "elapsed": elapsed,
            "params": result.get("params_text", ""),
            "shown_func": result["shown_func"],
            "resolved_func": result.get("resolved_func", result["shown_func"]),
        })

    def _finish_indefinite_result(self, result, elapsed) -> None:
        if result["closed_form"]:
            self.result_label.setText(
                f"Indefinite Integral: {result['display_str']} + C{self.format_elapsed(elapsed)}"
            )
            display = (
                f"Indefinite: ∫ {result['shown_func']} dx = "
                f"{self.last_raw_result} + C"
            )
        else:
            self.result_label.setText(
                "Indefinite Integral: No closed-form exact result was found."
                + self.format_elapsed(elapsed)
            )
            display = f"Indefinite: ∫ {result['shown_func']} dx = (no closed-form)"
        self.history_record.emit({
            "type": "indefinite",
            "display": display,
            "raw": self.last_raw_result,
            "raw_type": self.last_raw_result_type,
            "numeric_value": None,
            "func": result.get("input_func", result["shown_func"]),
            "elapsed": elapsed,
            "params": result.get("params_text", ""),
            "shown_func": result["shown_func"],
            "resolved_func": result.get("resolved_func", result["shown_func"]),
        })
        self.plot_clear_requested.emit()

    def _finish_error(self, error: Exception) -> None:
        self.clear_result()
        self._show_calculation_error(error)

    def _show_calculation_error(self, error: Exception) -> None:
        message = friendly_error_message(
            error,
            self.function.get_text(),
            self.lower.get_text(),
            self.upper.get_text(),
        )
        self.show_error("Error", "Error in integration: " + message)

    def show_exact_result(self) -> None:
        if self.last_raw_result is None:
            show_information_dialog(self, "Exact Result", "No result to display.")
            return
        if self.last_raw_result_type == "unevaluated":
            message = "No closed-form exact result was found."
            if self.last_numeric_value is not None:
                message += f"\n\nNumeric approximation:\n≈ {self.last_numeric_value:.10f}"
            else:
                message += "\n\nNo numeric value available."
        else:
            message = f"Exact symbolic form:\n\n{self.last_raw_result}"
            if self.last_numeric_value is not None:
                message += f"\n\nNumeric value:\n≈ {self.last_numeric_value:.10f}"
        show_information_dialog(self, "Exact Result", message)

    def clear_inputs(self) -> None:
        for field in (self.function, self.parameters, self.lower, self.upper):
            field.clear()

    def refill(self, record: dict[str, object]) -> None:
        self.function.set_text(record.get("func", ""))
        self.parameters.set_text(record.get("params", ""))
        self.lower.set_text(record.get("lower", ""))
        self.upper.set_text(record.get("upper", ""))

    def reset(self) -> None:
        super().reset()
        self.last_raw_result = None
        self.last_raw_result_type = None
        self.last_numeric_value = None

    def set_language(self, text: dict[str, object]) -> None:
        super().set_language(text)
        self.calculate_button.setText(str(text.get("calc1", "Calculate Integral")))
        self.reset_button.setText(str(text.get("reset", "Reset")))
        self.update_math_field_label("upper", "upper", "Upper limit:")
        self.update_math_field_label("lower", "lower", "Lower limit:")
        self.update_math_field_label("function", "func", "Enter target function:")
        self.update_math_field_label("parameters", "parameters", "Parameters:")


__all__ = ["BasicIntegrationTab"]
