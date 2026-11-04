"""The calculator's integration screen: exact results first, numerical methods on request."""

from __future__ import annotations

import threading
import time
import weakref

from PySide6.QtCore import QThreadPool, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import calengine as np

from error_utils import friendly_error_message
from formatting import format_result_for_display
from i18n import ui_text
from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from parameter_utils import display_function_with_parameters, resolve_function_text
from parser_utils import has_complete_limits, parse_input_to_float
from qt_async import run_in_background
from qt_dialogs import show_error_dialog, show_information_dialog
from symbolic_methods import (
    SymbolicTimeoutError,
    compute_general_integral,
    compute_tab1_result,
    numerical_fallback,
)
from tab2_logic import compare_numerical_methods, prepare_tab2_inputs, run_numerical_integration


AUTO_METHOD = "Auto"
NUMERICAL_METHODS = (
    "Adaptive Gauss-Kronrod",
    "Oscillatory Quadrature",
    "Trapezoidal",
    "Simpson",
    "Rectangle",
    "Romberg",
    "Gaussian Quadrature",
    "Simpson 3/8",
    "Adaptive Simpson",
    "Monte Carlo",
)
FIELDS = (
    # (attribute and field id, role, editor slot, text key, English label)
    ("upper", FieldRole.BOUND, "upper-bound", "upper", "Upper limit:"),
    ("lower", FieldRole.BOUND, "lower-bound", "lower", "Lower limit:"),
    ("function", FieldRole.EXPRESSION, "integrand", "func", "Enter target function:"),
    ("parameters", FieldRole.PARAMETERS, "parameters", "parameters", "Parameters:"),
)


def _equals(display: str) -> str:
    """Join a result to its integral without writing "= ≈"."""
    return display if display.startswith("≈") else f"= {display}"


class IntegralTab(QWidget):
    """One screen for definite, indefinite, improper, and numerical integrals."""

    history_record = Signal(object)
    plot_requested = Signal(str, float, float, object)
    plot_clear_requested = Signal()
    reset_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        panel_factory=MathEditorPanel,
        thread_pool: QThreadPool | None = None,
        text: dict[str, object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.text = dict(text or ui_text("English"))
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self.cancel_event = threading.Event()
        self.worker_running = False
        self.start_time: float | None = None
        self._comparison_dialogs: set[QDialog] = set()

        self.math_panel = panel_factory(self)
        for name, role, slot, key, fallback in FIELDS:
            field = self.math_panel.create_field(
                name, role, "", label=self._t(key, fallback), slot=slot
            )
            field.submitted.connect(self.calculate)
            setattr(self, name, field)
        self.math_panel.setMinimumHeight(290)

        self.calculate_button = QPushButton(self)
        self.reset_button = QPushButton(self)
        self.options_button = QPushButton(self)
        self.options_button.setCheckable(True)
        self.calculate_button.clicked.connect(self.calculate)
        self.reset_button.clicked.connect(self.reset_requested.emit)

        self.method_label = QLabel(self)
        self.method_combo = QComboBox(self)
        self.method_combo.addItems((AUTO_METHOD, *NUMERICAL_METHODS))
        self.compare_button = QPushButton(self)
        self.compare_button.clicked.connect(self.compare_methods)
        self.options_panel = QWidget(self)
        options = QHBoxLayout(self.options_panel)
        options.setContentsMargins(0, 0, 0, 0)
        options.addWidget(self.method_label)
        options.addWidget(self.method_combo, stretch=1)
        options.addWidget(self.compare_button)
        self.options_panel.hide()
        self.options_button.toggled.connect(self.options_panel.setVisible)

        # Shown only while a calculation runs.
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.cancel_button = QPushButton(self)
        self.cancel_button.clicked.connect(self.cancel_event.set)
        self.busy_panel = QWidget(self)
        busy = QHBoxLayout(self.busy_panel)
        busy.setContentsMargins(0, 0, 0, 0)
        busy.addWidget(self.progress_bar, stretch=1)
        busy.addWidget(self.cancel_button)
        self.busy_panel.hide()

        actions = QHBoxLayout()
        actions.addStretch(1)
        for button in (self.calculate_button, self.options_button, self.reset_button):
            actions.addWidget(button)
        actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.math_panel)
        layout.addLayout(actions)
        layout.addWidget(self.options_panel)
        layout.addWidget(self.busy_panel)
        layout.addStretch(1)
        self.set_language(self.text)

    def _t(self, key: str, fallback: str) -> str:
        return str(self.text.get(key, fallback))

    # Inputs shared with the main window, examples, history, and Math Tools.

    def get_function_text(self) -> str:
        return self.function.get_text()

    def set_function_text(self, value: object) -> None:
        self.function.set_text(value)

    def set_parameter_text(self, value: object) -> bool:
        self.parameters.set_text(value)
        return True

    def selected_method(self) -> str:
        return AUTO_METHOD if self.method_combo.currentIndex() == 0 else self.method_combo.currentText()

    def set_method(self, method: object) -> None:
        index = (AUTO_METHOD, *NUMERICAL_METHODS).index(method) if method in NUMERICAL_METHODS else 0
        self.method_combo.setCurrentIndex(index)
        if index:
            self.options_button.setChecked(True)

    def insert_at_cursor(self, latex: str) -> None:
        self.math_panel.insert_latex(latex)

    def dispatch_editor_command(self, command: str) -> None:
        self.math_panel.dispatch_active_command(command)

    def clear_inputs(self) -> None:
        for name, *_rest in FIELDS:
            getattr(self, name).clear()

    def refill(self, record: dict[str, object]) -> None:
        self.function.set_text(record.get("func", ""))
        self.parameters.set_text(record.get("params", ""))
        self.lower.set_text(record.get("lower", ""))
        self.upper.set_text(record.get("upper", ""))
        self.set_method(record.get("method", AUTO_METHOD))

    def reset(self) -> None:
        self.clear_inputs()
        self.set_method(AUTO_METHOD)
        self.options_button.setChecked(False)
        self.plot_clear_requested.emit()

    # Calculation lifecycle.

    def _read_inputs(self) -> dict[str, str]:
        func_text = self.function.get_text().strip()
        params_text = self.parameters.get_text().strip()
        return {
            "input_func": func_text,
            "params_text": params_text,
            "resolved_func": resolve_function_text(func_text, params_text),
            "shown_func": display_function_with_parameters(func_text, params_text),
            "lower": self.lower.get_text().strip(),
            "upper": self.upper.get_text().strip(),
        }

    def _numerical_inputs(self, method: str, context: dict[str, str]):
        return prepare_tab2_inputs(
            context["resolved_func"],
            method,
            context["lower"],
            context["upper"],
            shown_func=context["shown_func"],
            input_func=context["input_func"],
            params_text=context["params_text"],
            options={"cancel": self.cancel_event},
        )

    def calculate(self) -> None:
        if not self._can_start():
            return
        try:
            context = self._read_inputs()
            method = self.selected_method()
            lower, upper = context["lower"], context["upper"]
            if method != AUTO_METHOD:
                inputs = self._numerical_inputs(method, context)
                work = lambda: run_numerical_integration(inputs)
                finish = lambda result: self._finish_numerical(result, inputs)
            elif has_complete_limits(lower, upper) and not all(
                np.isfinite(parse_input_to_float(bound)) for bound in (lower, upper)
            ):
                work = lambda: self._improper_or_number(context)
                finish = lambda result: self._finish_improper(result, context)
            else:
                work = lambda: self._exact_or_number(context)
                finish = lambda result: self._finish_exact(result, context)
        except Exception as exc:
            self._show_error("integration_error", "Error in integration: ", exc)
            return
        self._begin_work()
        run_in_background(
            self.thread_pool,
            work,
            on_result=finish,
            on_error=lambda exc: self._show_error("integration_error", "Error in integration: ", exc),
            on_finished=self._finish_work,
        )

    # Auto: when no exact form is found in time, give the numerical value instead.

    def _exact_or_number(self, context: dict[str, str]) -> dict[str, object]:
        func, lower, upper = context["resolved_func"], context["lower"], context["upper"]
        try:
            return compute_tab1_result(func, lower, upper, cancel=self.cancel_event)
        except SymbolicTimeoutError:
            if not has_complete_limits(lower, upper):
                raise
        value, error = numerical_fallback(func, lower, upper, cancel=self.cancel_event)
        return {
            "kind": "definite",
            "lower_text": lower,
            "upper_text": upper,
            "display_str": f"≈ {value:.10g}",
            "raw_result": "",
            "raw_type": "unevaluated",
            "numeric_value": value,
            "numeric_err": error,
        }

    def _improper_or_number(self, context: dict[str, str]) -> dict[str, object]:
        func, lower, upper = context["resolved_func"], context["lower"], context["upper"]
        try:
            out = compute_general_integral(func, lower, upper, cancel=self.cancel_event)
        except SymbolicTimeoutError:
            out = {"type": "unevaluated", "expr": None}
        if out["type"] == "unevaluated":
            out["numeric"] = numerical_fallback(func, lower, upper, cancel=self.cancel_event)
        return out

    def compare_methods(self) -> None:
        if not self._can_start():
            return
        try:
            inputs = self._numerical_inputs(AUTO_METHOD, self._read_inputs())
        except Exception as exc:
            self._show_error("comparison_error", "Error in method comparison: ", exc)
            return
        self._begin_work()
        run_in_background(
            self.thread_pool,
            lambda: compare_numerical_methods(inputs),
            on_result=lambda rows: self._finish_comparison(rows, inputs),
            on_error=lambda exc: self._show_error("comparison_error", "Error in method comparison: ", exc),
            on_finished=self._finish_work,
        )

    def _can_start(self) -> bool:
        if not self.worker_running:
            return True
        show_information_dialog(self, self._t("info", "Info"), self._t("already_running", "A calculation is already running."))
        return False

    def _begin_work(self) -> None:
        self.cancel_event.clear()
        self.worker_running = True
        self.start_time = time.perf_counter()
        self.busy_panel.show()

    def _finish_work(self) -> None:
        self.worker_running = False
        self.busy_panel.hide()

    def _elapsed(self) -> float | None:
        return None if self.start_time is None else time.perf_counter() - self.start_time

    def _show_error(self, key: str, fallback: str, error) -> None:
        message = friendly_error_message(
            error, self.function.get_text(), self.lower.get_text(), self.upper.get_text()
        )
        show_error_dialog(self, self._t("error", "Error"), self._t(key, fallback) + message)

    def _record(self, record_type: str, display: str, context: dict[str, str], **values) -> None:
        self.history_record.emit({
            "type": record_type,
            "display": display,
            "func": context["input_func"],
            "params": context["params_text"],
            "shown_func": context["shown_func"],
            "resolved_func": context["resolved_func"],
            "elapsed": self._elapsed(),
            **values,
        })

    # Results. The main window renders them; this screen records and plots them.

    def _finish_exact(self, result: dict[str, object], context: dict[str, str]) -> None:
        shown = context["shown_func"]
        common = {"raw": result["raw_result"], "raw_type": str(result["raw_type"])}
        if result["kind"] == "definite":
            lower, upper = result["lower_text"], result["upper_text"]
            self._record(
                "definite",
                f"{self._t('history_definite', 'Definite')}: ∫[{lower}, {upper}] {shown} dx {_equals(result['display_str'])}",
                context,
                lower=lower,
                upper=upper,
                numeric_value=result["numeric_value"],
                error=result["numeric_err"],
                antiderivative=result.get("antiderivative"),
                **common,
            )
            try:
                self.plot_requested.emit(
                    context["resolved_func"], parse_input_to_float(lower), parse_input_to_float(upper), None
                )
            except Exception:
                self.plot_clear_requested.emit()
            return
        value = f"{result['raw_result']} + C" if result["closed_form"] else "(no closed-form)"
        self._record(
            "indefinite",
            f"{self._t('history_indefinite', 'Indefinite')}: ∫ {shown} dx = {value}",
            context,
            numeric_value=None,
            **common,
        )
        self.plot_clear_requested.emit()

    def _finish_improper(self, out: dict[str, object], context: dict[str, str]) -> None:
        value, error = out.get("numeric") or (None, None)
        if out["type"] == "exact":
            display = format_result_for_display(out["expr"])["display"]
        elif value is not None:
            display = f"≈ {value:.10g}"
        else:
            display = self._t("divergent", "Divergent") if out["type"] == "divergent" else "(no closed-form)"
        lower, upper = context["lower"], context["upper"]
        self._record(
            "improper",
            f"{self._t('history_improper', 'Improper')}: ∫[{lower}, {upper}] {context['shown_func']} dx {_equals(display)}",
            context,
            raw=out.get("expr") if value is None else "",
            raw_type=out["type"],
            lower=lower,
            upper=upper,
            numeric_value=value,
            error=error,
        )
        self.plot_clear_requested.emit()

    def _finish_numerical(self, result, inputs) -> None:
        value, error_estimate, segments = result
        diagnostics = dict(segments[0].get("diagnostics", {})) if segments else {}
        if segments:
            parts = [part.get("diagnostics", {}) for part in segments]
            diagnostics["evaluations"] = sum(part.get("evaluations", 0) for part in parts)
            diagnostics["status"] = (
                "converged" if all(part.get("status") == "converged" for part in parts) else "tolerance_not_met"
            )
        method = inputs.integration_method
        display = f"≈ {float(value):.12g}"
        if error_estimate is not None:
            display += f" (±{error_estimate:.1e})"
        self._record(
            "numerical",
            f"{self._t('history_numerical', 'Numerical')} ({method}): "
            f"∫[{inputs.lower_text}, {inputs.upper_text}] {inputs.shown_func} dx {display}",
            self._context_from(inputs),
            raw=value,
            lower=inputs.lower_text,
            upper=inputs.upper_text,
            method=method,
            error=error_estimate,
            diagnostics=diagnostics,
            segments=segments,
        )
        points = [segment["upper"] for segment in segments[:-1]]
        self.plot_requested.emit(inputs.func_str, float(inputs.lower), float(inputs.upper), points)

    def _finish_comparison(self, rows: list[dict], inputs) -> None:
        ok_rows = [row for row in rows if row["status"] == "ok"]
        if ok_rows:
            best = min(ok_rows, key=lambda row: row["time"])
            self._record(
                "comparison",
                f"{self._t('history_comparison', 'Comparison')}: ∫[{inputs.lower_text}, {inputs.upper_text}] "
                f"{inputs.shown_func} dx; {self._t('fastest', 'fastest')}={best['method']}",
                self._context_from(inputs),
                raw=rows,
                lower=inputs.lower_text,
                upper=inputs.upper_text,
            )
        self._show_comparison_dialog(rows)

    @staticmethod
    def _context_from(inputs) -> dict[str, str]:
        return {
            "input_func": inputs.input_func,
            "params_text": inputs.params_text,
            "shown_func": inputs.shown_func,
            "resolved_func": inputs.func_str,
        }

    def _show_comparison_dialog(self, rows: list[dict]) -> None:
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.setWindowTitle(self._t("comparison_title", "Numerical Method Comparison"))
        dialog.resize(900, 390)
        columns = tuple(self.text.get(
            "comparison_columns",
            ("Method", "Result", "Estimate / SE", "Actual error", "Median time", "Evaluations", "Status"),
        ))
        table = QTableWidget(len(rows), len(columns), dialog)
        table.setHorizontalHeaderLabels(columns)
        for row_index, row in enumerate(rows):
            values = (
                row["method"],
                "" if row["result"] is None else f"{row['result']:.10g}",
                "" if row["error"] is None else f"{row['error']:.3e}",
                "" if row.get("actual_error") is None else f"{row['actual_error']:.3e}",
                f"{row['time']:.6f}s",
                row.get("evaluations", 0),
                row["status"],
            )
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        QVBoxLayout(dialog).addWidget(table)
        self._comparison_dialogs.add(dialog)
        dialog_ref = weakref.ref(dialog)

        def discard_dialog(*_args) -> None:
            current = dialog_ref()
            if current is not None:
                self._comparison_dialogs.discard(current)

        dialog.destroyed.connect(discard_dialog)
        dialog.show()

    def set_language(self, text: dict[str, object]) -> None:
        self.text = dict(text)
        self.calculate_button.setText(self._t("calculate", "Calculate"))
        self.reset_button.setText(self._t("reset", "Reset"))
        self.options_button.setText(self._t("more_options", "More options"))
        self.method_label.setText(self._t("method", "Method:"))
        self.method_combo.setItemText(0, self._t("method_auto", "Auto (exact when possible)"))
        self.compare_button.setText(self._t("compare_methods", "Compare Methods"))
        self.cancel_button.setText(self._t("cancel_calculation", "Cancel calculation"))
        setter = getattr(self.math_panel, "set_field_label", None)
        if setter is not None:
            for name, _role, _slot, key, fallback in FIELDS:
                setter(name, self._t(key, fallback))


__all__ = ["AUTO_METHOD", "IntegralTab", "NUMERICAL_METHODS"]
