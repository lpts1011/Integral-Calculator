import threading
import time
from queue import Empty, Queue
from tkinter import messagebox

import calengine as np

from base_tab import BaseTab
from error_utils import friendly_error_message
from interval_utils import parse_split_points
from parameter_utils import display_function_with_parameters, resolve_function_text
from parser_utils import parse_input_to_float
from recommendation_utils import recommend_tab2_method
from tab2_logic import (
    compare_numerical_methods,
    prepare_tab2_inputs,
    run_tab2_calculation,
    should_use_indeterminate_progress,
)
from tab2_compare_ui import show_comparison_window as show_tab2_comparison_window
from tab2_widgets import build_tab2_widgets


class AdvancedIntegrationTab(BaseTab):
    def __init__(self, app, parent):
        super().__init__(app, parent)
        self.event_queue = Queue()
        self.worker_thread = None
        self.recommendation = None
        self._recommendation_after_id = None
        self._build_widgets()
        self.update_recommendation()

    def _build_widgets(self):
        build_tab2_widgets(self)

    def update_recommendation(self, event=None):
        if self._recommendation_after_id is not None:
            self.app.root.after_cancel(self._recommendation_after_id)
            self._recommendation_after_id = None
        func_for_recommendation = self.func_entry.get()
        params_text = self.params_entry.get().strip()
        if params_text and func_for_recommendation.strip():
            try:
                func_for_recommendation = resolve_function_text(func_for_recommendation, params_text)
            except Exception:
                pass
        self.recommendation = recommend_tab2_method(
            func_for_recommendation,
            self.lower_entry.get(),
            self.upper_entry.get(),
        )
        self.recommendation_label.config(text=self.recommendation.message(self.app.text))

    def schedule_recommendation(self, event=None):
        if self._recommendation_after_id is not None:
            self.app.root.after_cancel(self._recommendation_after_id)
        self._recommendation_after_id = self.app.root.after(
            180,
            self._run_scheduled_recommendation,
        )

    def _run_scheduled_recommendation(self):
        self._recommendation_after_id = None
        self.update_recommendation()

    def apply_recommendation(self):
        if self.recommendation is None:
            self.update_recommendation()
        self.method_var.set(self.recommendation.mode)
        self.numerical_method_var.set(self.recommendation.method)
        self.update_recommendation()

    def calculate(self):
        try:
            if self.worker_running:
                messagebox.showinfo("Info", "A computation is already running.")
                return

            func_text = self.func_entry.get().strip()
            params_text = self.params_entry.get().strip()
            resolved_func = resolve_function_text(func_text, params_text)
            shown_func = display_function_with_parameters(func_text, params_text)
            inputs = prepare_tab2_inputs(
                resolved_func,
                self.method_var.get(),
                self.numerical_method_var.get(),
                self.lower_entry.get().strip(),
                self.upper_entry.get().strip(),
                self.delta_entry.get().strip(),
                split_text=self.split_entry.get().strip(),
                shown_func=shown_func,
                input_func=func_text,
                params_text=params_text,
            )

            self._clear_event_queue()
            self.worker_running = True
            self.start_time = time.perf_counter()

            if should_use_indeterminate_progress(inputs):
                self.app.progress_controller.show_indeterminate()
            else:
                self.app.progress_controller.show_determinate()

            def worker():
                try:
                    run_tab2_calculation(inputs, self.event_queue.put)
                except Exception as exc:
                    self.event_queue.put(("error", str(exc)))
                finally:
                    self.worker_running = False

            self.worker_thread = threading.Thread(target=worker, daemon=True)
            self.worker_thread.start()
            self.poll_queue()
        except Exception as exc:
            self.worker_running = False
            self.app.progress_controller.hide()
            messagebox.showerror(
                "Error",
                "Error in integration: "
                + friendly_error_message(
                    exc,
                    self.func_entry.get(),
                    self.lower_entry.get(),
                    self.upper_entry.get(),
                ),
            )

    def _clear_event_queue(self):
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except Empty:
                break

    def poll_queue(self):
        try:
            while True:
                self.handle_queue_item(self.event_queue.get_nowait())
        except Empty:
            pass

        if self.worker_running or not self.event_queue.empty():
            self.app.root.after(60, self.poll_queue)

    def handle_queue_item(self, item):
        kind = item[0]
        if kind == "progress":
            self.app.progress["value"] = max(self.app.progress["value"], int(item[1]))
            return

        handlers = {
            "symbolic_result": self.handle_symbolic_result,
            "symbolic_indef": self.handle_symbolic_indefinite,
            "symbolic_unevaluated": self.handle_symbolic_unevaluated,
            "symbolic_indef_unevaluated": self.handle_symbolic_indefinite_unevaluated,
            "numeric_result": self.handle_numeric_result,
            "error": self.handle_error,
        }
        handler = handlers.get(kind)
        if handler is not None:
            handler(item)

    def handle_symbolic_result(self, item):
        formatted, lower, upper, shown_func = item[1], item[2], item[3], item[4]
        raw_func = item[5] if len(item) > 5 else shown_func
        input_func = item[6] if len(item) > 6 else shown_func
        params_text = item[7] if len(item) > 7 else ""
        elapsed = self._elapsed()
        self.result_label.config(text=f"Symbolic Integration Result: {formatted}{self.format_elapsed(elapsed)}")
        self.app.add_history({
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
            l_float = parse_input_to_float(lower)
            u_float = parse_input_to_float(upper)
            self.app.plot_function(raw_func, l_float, u_float)
        except Exception:
            self.app.clear_plot()
        self.app.progress_controller.hide()

    def handle_symbolic_indefinite(self, item):
        formatted, shown_func = item[1], item[2]
        raw_func = item[3] if len(item) > 3 else shown_func
        input_func = item[4] if len(item) > 4 else shown_func
        params_text = item[5] if len(item) > 5 else ""
        elapsed = self._elapsed()
        self.result_label.config(text=f"Indefinite Integral Result: {formatted} + C{self.format_elapsed(elapsed)}")
        self.app.add_history({
            "type": "symbolic_indefinite",
            "display": f"Indefinite: ∫ {shown_func} dx = {formatted} + C",
            "raw": formatted,
            "func": input_func,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        self.app.clear_plot()
        self.app.progress_controller.hide()

    def handle_symbolic_unevaluated(self, item):
        lower, upper, shown_func = item[1], item[2], item[3]
        raw_func = item[4] if len(item) > 4 else shown_func
        input_func = item[5] if len(item) > 5 else shown_func
        params_text = item[6] if len(item) > 6 else ""
        elapsed = self._elapsed()
        message = "No closed-form symbolic result was found. Try numerical integration."
        self.result_label.config(text=f"{message}{self.format_elapsed(elapsed)}")
        self.app.add_history({
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
        self.app.clear_plot()
        self.app.progress_controller.hide()

    def handle_symbolic_indefinite_unevaluated(self, item):
        shown_func = item[1]
        raw_func = item[2] if len(item) > 2 else shown_func
        input_func = item[3] if len(item) > 3 else shown_func
        params_text = item[4] if len(item) > 4 else ""
        elapsed = self._elapsed()
        self.result_label.config(text=f"No closed-form indefinite integral was found.{self.format_elapsed(elapsed)}")
        self.app.add_history({
            "type": "symbolic_indefinite",
            "display": f"Indefinite: ∫ {shown_func} dx = no closed-form",
            "raw": "No closed-form",
            "func": input_func,
            "elapsed": elapsed,
            "params": params_text,
            "shown_func": shown_func,
            "resolved_func": raw_func,
        })
        self.app.clear_plot()
        self.app.progress_controller.hide()

    def handle_numeric_result(self, item):
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
        elapsed = self._elapsed()
        display = f"≈ {float(result):.3f}"
        if error_estimate is not None:
            display = f"{display} (±{error_estimate:.1e})"
        if len(segments) > 1:
            display = f"{display}; segments={len(segments)}"

        self.result_label.config(text=f"Numerical Integration Result: {display}{self.format_elapsed(elapsed)}")
        self.app.add_history({
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
                split_points = self._segment_split_points(segments)
                if not split_points:
                    split_points = self._plot_split_points(split_text, lower, upper)
                self.app.plot_function(raw_func, lower, upper, split_points=split_points)
            else:
                self.app.clear_plot()
        except Exception:
            self.app.clear_plot()
        self.app.progress_controller.hide()

    def handle_error(self, item):
        messagebox.showerror(
            "Error",
            friendly_error_message(
                item[1],
                self.func_entry.get(),
                self.lower_entry.get(),
                self.upper_entry.get(),
            ),
        )
        self.worker_running = False
        self.app.progress_controller.hide()

    def clear_inputs(self):
        self.clear_entries(
            self.func_entry,
            self.params_entry,
            self.lower_entry,
            self.upper_entry,
            self.split_entry,
            self.delta_entry,
        )

    def refill(self, record):
        self.set_entry_text(self.func_entry, record.get("func", ""))
        self.set_entry_text(self.params_entry, record.get("params", ""))
        self.set_entry_text(self.lower_entry, record.get("lower", ""))
        self.set_entry_text(self.upper_entry, record.get("upper", ""))
        self.set_entry_text(self.split_entry, record.get("split_points", ""))
        if record.get("type") == "comparison":
            self.method_var.set("Numerical Integration")
        elif record.get("method"):
            self.method_var.set("Numerical Integration")
            self.numerical_method_var.set(str(record["method"]))
        self.update_recommendation()

    def refresh_after_function_set(self):
        self.update_recommendation()

    def set_language(self, text):
        self.calc_button.config(text=text["calc1"])
        self.reset_button.config(text=text["reset"])
        self.method_label.config(text=text["method"])
        self.lower_label.config(text=text["lower"])
        self.upper_label.config(text=text["upper"])
        self.delta_label.config(text=text["delta"])
        self.func_label.config(text=text["func"])
        self.params_label.config(text=text["parameters"])
        self.split_label.config(text=text["split_points"])
        self.numerical_method_label.config(text=text["numerical_method"])
        self.apply_recommendation_button.config(text=text["apply_recommendation"])
        self.compare_button.config(text=text["compare_methods"])
        if self.recommendation is not None:
            self.recommendation_label.config(text=self.recommendation.message(text))

    def compare_methods(self):
        try:
            if self.worker_running:
                messagebox.showinfo("Info", "A computation is already running.")
                return

            func_text = self.func_entry.get().strip()
            params_text = self.params_entry.get().strip()
            resolved_func = resolve_function_text(func_text, params_text)
            shown_func = display_function_with_parameters(func_text, params_text)
            inputs = prepare_tab2_inputs(
                resolved_func,
                "Numerical Integration",
                self.numerical_method_var.get(),
                self.lower_entry.get().strip(),
                self.upper_entry.get().strip(),
                self.delta_entry.get().strip(),
                split_text=self.split_entry.get().strip(),
                shown_func=shown_func,
                input_func=func_text,
                params_text=params_text,
            )

            self.worker_running = True
            self.start_time = time.perf_counter()
            self.result_label.config(text="Comparing methods...")
            self.app.progress_controller.show_indeterminate()

            def worker():
                try:
                    rows = compare_numerical_methods(inputs)
                    self.app.root.after(0, lambda: self.finish_comparison(rows, inputs))
                except Exception as exc:
                    self.app.root.after(0, lambda err=exc: self.finish_comparison_error(err))

            self.worker_thread = threading.Thread(target=worker, daemon=True)
            self.worker_thread.start()
        except Exception as exc:
            self.worker_running = False
            self.app.progress_controller.hide()
            messagebox.showerror(
                "Error",
                "Error in method comparison: "
                + friendly_error_message(
                    exc,
                    self.func_entry.get(),
                    self.lower_entry.get(),
                    self.upper_entry.get(),
                ),
            )

    def finish_comparison(self, rows, inputs):
        elapsed = self._elapsed()
        self.worker_running = False
        self.app.progress_controller.hide()
        self.result_label.config(text=f"Method comparison finished{self.format_elapsed(elapsed)}")
        show_tab2_comparison_window(self, rows, inputs, elapsed)

    def finish_comparison_error(self, error):
        self.worker_running = False
        self.app.progress_controller.hide()
        self.result_label.config(text="")
        messagebox.showerror(
            "Error",
            "Error in method comparison: "
            + friendly_error_message(
                error,
                self.func_entry.get(),
                self.lower_entry.get(),
                self.upper_entry.get(),
            ),
        )

    def _plot_split_points(self, split_text, lower, upper):
        try:
            return parse_split_points(split_text, lower, upper)
        except Exception:
            return []

    def _segment_split_points(self, segments):
        if len(segments) <= 1:
            return []
        return [segment["upper"] for segment in segments[:-1]]

    def _elapsed(self):
        if self.start_time is None:
            return None
        return time.perf_counter() - self.start_time
