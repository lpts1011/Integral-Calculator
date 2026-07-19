"""Qt Advanced Integration tab."""

from __future__ import annotations

import weakref

from PySide6.QtCore import QThreadPool, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import calengine as np

from error_utils import friendly_error_message
from interval_utils import parse_split_points
from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from parameter_utils import display_function_with_parameters, resolve_function_text
from parser_utils import parse_input_to_float
from qt_async import run_in_background
from qt_tabs.base import QtIntegrationTab
from recommendation_utils import recommend_tab2_method
from tab2_logic import (
    compare_numerical_methods,
    prepare_tab2_inputs,
    run_tab2_calculation,
    should_use_indeterminate_progress,
)


NUMERICAL_METHODS = (
    "Trapezoidal",
    "Simpson",
    "Rectangle",
    "Romberg",
    "Gaussian Quadrature",
    "Simpson 3/8",
    "Adaptive Simpson",
    "Monte Carlo",
)


class AdvancedIntegrationTab(QtIntegrationTab):
    calculation_event = Signal(object)

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
        if hasattr(self.math_panel, "content_height_changed"):
            self.math_panel.content_height_changed.connect(
                self._fit_math_panel_to_content
            )
        self.recommendation = None
        self._active_inputs = None
        self._comparison_dialogs: set[QDialog] = set()

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
        self.split_points = self.create_math_field(
            "split_points",
            FieldRole.SPLIT_POINTS,
            label=self.field_label("split_points", "Split points:"),
            slot="split-points",
        )
        self.math_panel.setMinimumHeight(280)

        self.delta_label = QLabel("Step size (for Numerical Integration):", self)
        self.delta_input = QLineEdit(self)
        self.delta_input.setObjectName("advancedStepSize")
        self.mode_label = QLabel("Integration Method:", self)
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(("Symbolic Integration", "Numerical Integration"))
        self.numerical_method_label = QLabel("Numerical Method:", self)
        self.numerical_method_combo = QComboBox(self)
        self.numerical_method_combo.addItems(NUMERICAL_METHODS)
        self.recommendation_label = QLabel(self)
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setObjectName("integrationRecommendation")
        self.apply_recommendation_button = QPushButton("Apply Recommendation", self)
        self.calculate_button = QPushButton("Calculate Integral", self)
        self.compare_button = QPushButton("Compare Methods", self)
        self.reset_button = QPushButton("Reset", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

        controls = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(self.mode_label)
        row.addWidget(self.mode_combo)
        row.addWidget(self.numerical_method_label)
        row.addWidget(self.numerical_method_combo)
        controls.addLayout(row)
        delta_row = QHBoxLayout()
        delta_row.addWidget(self.delta_label)
        delta_row.addWidget(self.delta_input, stretch=1)
        controls.addLayout(delta_row)
        controls.addWidget(self.recommendation_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.apply_recommendation_button)
        actions.addWidget(self.calculate_button)
        actions.addWidget(self.compare_button)
        actions.addWidget(self.reset_button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.math_panel)
        layout.addLayout(controls)
        layout.addLayout(actions)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.result_label)
        layout.addStretch(1)

        self._recommendation_timer = QTimer(self)
        self._recommendation_timer.setSingleShot(True)
        self._recommendation_timer.setInterval(180)
        self._recommendation_timer.timeout.connect(self.update_recommendation)
        for field in (
            self.function,
            self.lower,
            self.upper,
            self.parameters,
            self.split_points,
        ):
            field.changed.connect(self.schedule_recommendation)
        self.delta_input.textChanged.connect(self.schedule_recommendation)
        self.delta_input.returnPressed.connect(self.calculate)
        self.mode_combo.currentTextChanged.connect(self.update_recommendation)
        self.numerical_method_combo.currentTextChanged.connect(self.update_recommendation)
        self.apply_recommendation_button.clicked.connect(self.apply_recommendation)
        self.calculate_button.clicked.connect(self.calculate)
        self.compare_button.clicked.connect(self.compare_methods)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.calculation_event.connect(self.handle_calculation_event)
        self.set_language(self.text)
        self.update_recommendation()

    def _fit_math_panel_to_content(self, content_height: int) -> None:
        fitted_height = max(280, int(content_height) + 4)
        if self.math_panel.minimumHeight() != fitted_height:
            self.math_panel.setMinimumHeight(fitted_height)

    def set_function_text(self, value: object) -> None:
        super().set_function_text(value)
        self.update_recommendation()

    def set_parameter_text(self, value: object) -> bool:
        result = super().set_parameter_text(value)
        self.update_recommendation()
        return result

    def schedule_recommendation(self, *_args) -> None:
        self._recommendation_timer.start()

    def update_recommendation(self, *_args) -> None:
        func_text = self.function.get_text()
        params_text = self.parameters.get_text().strip()
        if params_text and func_text.strip():
            try:
                func_text = resolve_function_text(func_text, params_text)
            except Exception:
                pass
        self.recommendation = recommend_tab2_method(
            func_text,
            self.lower.get_text(),
            self.upper.get_text(),
        )
        self.recommendation_label.setText(self.recommendation.message(self.text))

    def apply_recommendation(self) -> None:
        if self.recommendation is None:
            self.update_recommendation()
        self.mode_combo.setCurrentText(self.recommendation.mode)
        self.numerical_method_combo.setCurrentText(self.recommendation.method)
        self.update_recommendation()

    def _prepare_inputs(self, mode: str | None = None):
        func_text = self.function.get_text().strip()
        params_text = self.parameters.get_text().strip()
        resolved_func = resolve_function_text(func_text, params_text)
        shown_func = display_function_with_parameters(func_text, params_text)
        return prepare_tab2_inputs(
            resolved_func,
            mode or self.mode_combo.currentText(),
            self.numerical_method_combo.currentText(),
            self.lower.get_text().strip(),
            self.upper.get_text().strip(),
            self.delta_input.text().strip(),
            split_text=self.split_points.get_text().strip(),
            shown_func=shown_func,
            input_func=func_text,
            params_text=params_text,
        )

    def calculate(self) -> None:
        if not self.guard_worker():
            return
        try:
            inputs = self._prepare_inputs()
        except Exception as exc:
            self._show_calculation_error(exc)
            return
        self._active_inputs = inputs
        self.begin_work()
        self._start_progress(inputs)

        def work():
            run_tab2_calculation(inputs, self.calculation_event.emit)

        run_in_background(
            self.thread_pool,
            work,
            on_error=self._finish_worker_error,
            on_finished=self.finish_work,
        )

    def _start_progress(self, inputs) -> None:
        if should_use_indeterminate_progress(inputs):
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        self.progress_bar.show()

    def _finish_worker_error(self, error: Exception) -> None:
        self.progress_bar.hide()
        self.clear_result()
        self._show_calculation_error(error)

    def handle_calculation_event(self, item: tuple) -> None:
        kind = item[0]
        if kind == "progress":
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(max(self.progress_bar.value(), int(item[1])))
            return
        handlers = {
            "symbolic_result": self._handle_symbolic_result,
            "symbolic_indef": self._handle_symbolic_indefinite,
            "symbolic_unevaluated": self._handle_symbolic_unevaluated,
            "symbolic_indef_unevaluated": self._handle_symbolic_indefinite_unevaluated,
            "numeric_result": self._handle_numeric_result,
            "error": self._handle_event_error,
        }
        handler = handlers.get(kind)
        if handler is not None:
            handler(item)

    def _handle_symbolic_result(self, item) -> None:
        formatted, lower, upper, shown_func = item[1:5]
        raw_func = item[5] if len(item) > 5 else shown_func
        input_func = item[6] if len(item) > 6 else shown_func
        params_text = item[7] if len(item) > 7 else ""
        elapsed = self.elapsed()
        self.result_label.setText(
            f"Symbolic Integration Result: {formatted}{self.format_elapsed(elapsed)}"
        )
        self.history_record.emit({
            "type": "symbolic",
            "display": f"Symbolic: ∫[{lower}, {upper}] {shown_func} dx = {formatted}",
            "raw": formatted,
            "func": input_func,
            "lower": lower,
            "upper": upper,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        try:
            self.plot_requested.emit(
                raw_func,
                parse_input_to_float(lower),
                parse_input_to_float(upper),
                None,
            )
        except Exception:
            self.plot_clear_requested.emit()
        self.progress_bar.hide()

    def _handle_symbolic_indefinite(self, item) -> None:
        formatted, shown_func = item[1], item[2]
        raw_func = item[3] if len(item) > 3 else shown_func
        input_func = item[4] if len(item) > 4 else shown_func
        params_text = item[5] if len(item) > 5 else ""
        elapsed = self.elapsed()
        self.result_label.setText(
            f"Indefinite Integral Result: {formatted} + C{self.format_elapsed(elapsed)}"
        )
        self.history_record.emit({
            "type": "symbolic_indefinite",
            "display": f"Indefinite: ∫ {shown_func} dx = {formatted} + C",
            "raw": formatted,
            "func": input_func,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        self.plot_clear_requested.emit()
        self.progress_bar.hide()

    def _handle_symbolic_unevaluated(self, item) -> None:
        lower, upper, shown_func = item[1], item[2], item[3]
        raw_func = item[4] if len(item) > 4 else shown_func
        input_func = item[5] if len(item) > 5 else shown_func
        params_text = item[6] if len(item) > 6 else ""
        elapsed = self.elapsed()
        message = "No closed-form symbolic result was found. Try numerical integration."
        self.result_label.setText(message + self.format_elapsed(elapsed))
        self.history_record.emit({
            "type": "symbolic",
            "display": f"Symbolic: ∫[{lower}, {upper}] {shown_func} dx = no closed-form",
            "raw": "No closed-form",
            "func": input_func,
            "lower": lower,
            "upper": upper,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        self.plot_clear_requested.emit()
        self.progress_bar.hide()

    def _handle_symbolic_indefinite_unevaluated(self, item) -> None:
        shown_func = item[1]
        raw_func = item[2] if len(item) > 2 else shown_func
        input_func = item[3] if len(item) > 3 else shown_func
        params_text = item[4] if len(item) > 4 else ""
        elapsed = self.elapsed()
        self.result_label.setText(
            "No closed-form indefinite integral was found." + self.format_elapsed(elapsed)
        )
        self.history_record.emit({
            "type": "symbolic_indefinite",
            "display": f"Indefinite: ∫ {shown_func} dx = no closed-form",
            "raw": "No closed-form",
            "func": input_func,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        self.plot_clear_requested.emit()
        self.progress_bar.hide()

    def _handle_numeric_result(self, item) -> None:
        (
            result,
            method_used,
            lower,
            upper,
            shown_func,
            raw_func,
            error_estimate,
            segments,
            input_func,
            params_text,
            split_text,
        ) = item[1:]
        elapsed = self.elapsed()
        display = f"≈ {float(result):.3f}"
        if error_estimate is not None:
            display += f" (±{error_estimate:.1e})"
        if len(segments) > 1:
            display += f"; segments={len(segments)}"
        self.result_label.setText(
            f"Numerical Integration Result: {display}{self.format_elapsed(elapsed)}"
        )
        self.history_record.emit({
            "type": "numerical",
            "display": f"Numerical ({method_used}): ∫[{lower}, {upper}] {shown_func} dx {display}",
            "raw": result,
            "func": input_func,
            "lower": lower,
            "upper": upper,
            "method": method_used,
            "error": error_estimate,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
            "split_points": split_text,
            "segments": segments,
        })
        try:
            if np.isfinite(lower) and np.isfinite(upper):
                points = [segment["upper"] for segment in segments[:-1]]
                if not points:
                    points = self._plot_split_points(split_text, lower, upper)
                self.plot_requested.emit(raw_func, float(lower), float(upper), points)
            else:
                self.plot_clear_requested.emit()
        except Exception:
            self.plot_clear_requested.emit()
        self.progress_bar.hide()

    def _handle_event_error(self, item) -> None:
        self.progress_bar.hide()
        self.finish_work()
        self._show_calculation_error(item[1])

    def _show_calculation_error(self, error) -> None:
        message = friendly_error_message(
            error,
            self.function.get_text(),
            self.lower.get_text(),
            self.upper.get_text(),
        )
        self.show_error("Error", "Error in integration: " + message)

    def compare_methods(self) -> None:
        if not self.guard_worker():
            return
        try:
            inputs = self._prepare_inputs("Numerical Integration")
        except Exception as exc:
            self._show_comparison_error(exc)
            return
        self._active_inputs = inputs
        self.begin_work("Comparing methods...")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        run_in_background(
            self.thread_pool,
            lambda: compare_numerical_methods(inputs),
            on_result=lambda rows: self._finish_comparison(rows, inputs),
            on_error=self._show_comparison_error,
            on_finished=self.finish_work,
        )

    def _finish_comparison(self, rows: list[dict], inputs) -> None:
        elapsed = self.elapsed()
        self.progress_bar.hide()
        self.result_label.setText(
            "Method comparison finished" + self.format_elapsed(elapsed)
        )
        ok_rows = [row for row in rows if row["status"] == "ok"]
        if ok_rows:
            best = min(ok_rows, key=lambda row: row["time"])
            self.history_record.emit({
                "type": "comparison",
                "display": f"Comparison: ∫[{inputs.lower}, {inputs.upper}] {inputs.shown_func} dx; fastest={best['method']}",
                "raw": rows,
                "func": inputs.input_func,
                "lower": inputs.lower,
                "upper": inputs.upper,
                "method": "Method Comparison",
                "elapsed": elapsed,
                "params": inputs.params_text,
                "shown_func": inputs.shown_func,
                "resolved_func": inputs.func_str,
                "split_points": inputs.split_text,
            })
        self._show_comparison_dialog(rows)

    def _show_comparison_dialog(self, rows: list[dict]) -> None:
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.setWindowTitle(str(self.text.get("comparison_title", "Numerical Method Comparison")))
        dialog.resize(900, 390)
        columns = ("Method", "Result", "Error", "Time", "Segments", "Status")
        table = QTableWidget(len(rows), len(columns), dialog)
        table.setHorizontalHeaderLabels(columns)
        for row_index, row in enumerate(rows):
            values = (
                row["method"],
                "" if row["result"] is None else f"{row['result']:.10g}",
                "" if row["error"] is None else f"{row['error']:.3e}",
                f"{row['time']:.3f}s",
                row["segments"],
                row["status"],
            )
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        layout = QVBoxLayout(dialog)
        layout.addWidget(table)
        self._comparison_dialogs.add(dialog)
        dialog_ref = weakref.ref(dialog)

        def discard_dialog(*_args) -> None:
            current = dialog_ref()
            if current is not None:
                self._comparison_dialogs.discard(current)

        dialog.destroyed.connect(discard_dialog)
        dialog.show()

    def _show_comparison_error(self, error) -> None:
        self.progress_bar.hide()
        self.clear_result()
        message = friendly_error_message(
            error,
            self.function.get_text(),
            self.lower.get_text(),
            self.upper.get_text(),
        )
        self.show_error("Error", "Error in method comparison: " + message)

    @staticmethod
    def _plot_split_points(split_text, lower, upper):
        try:
            return parse_split_points(split_text, lower, upper)
        except Exception:
            return []

    def clear_inputs(self) -> None:
        for field in (
            self.function,
            self.parameters,
            self.lower,
            self.upper,
            self.split_points,
        ):
            field.clear()
        self.delta_input.clear()
        self.update_recommendation()

    def refill(self, record: dict[str, object]) -> None:
        self.function.set_text(record.get("func", ""))
        self.parameters.set_text(record.get("params", ""))
        self.lower.set_text(record.get("lower", ""))
        self.upper.set_text(record.get("upper", ""))
        self.split_points.set_text(record.get("split_points", ""))
        if record.get("type") == "comparison":
            self.mode_combo.setCurrentText("Numerical Integration")
        elif record.get("method"):
            self.mode_combo.setCurrentText("Numerical Integration")
            self.numerical_method_combo.setCurrentText(str(record["method"]))
        self.update_recommendation()

    def reset(self) -> None:
        super().reset()
        self.progress_bar.hide()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def set_language(self, text: dict[str, object]) -> None:
        super().set_language(text)
        self.calculate_button.setText(str(text.get("calc1", "Calculate Integral")))
        self.reset_button.setText(str(text.get("reset", "Reset")))
        self.mode_label.setText(str(text.get("method", "Integration Method:")))
        self.delta_label.setText(str(text.get("delta", "Step size:")))
        self.numerical_method_label.setText(
            str(text.get("numerical_method", "Numerical Method:"))
        )
        self.apply_recommendation_button.setText(
            str(text.get("apply_recommendation", "Apply Recommendation"))
        )
        self.compare_button.setText(str(text.get("compare_methods", "Compare Methods")))
        self.update_math_field_label("upper", "upper", "Upper limit:")
        self.update_math_field_label("lower", "lower", "Lower limit:")
        self.update_math_field_label("function", "func", "Enter target function:")
        self.update_math_field_label("parameters", "parameters", "Parameters:")
        self.update_math_field_label("split_points", "split_points", "Split points:")
        if self.recommendation is not None:
            self.recommendation_label.setText(self.recommendation.message(text))


__all__ = ["AdvancedIntegrationTab"]
