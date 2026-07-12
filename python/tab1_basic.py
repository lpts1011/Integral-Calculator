import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from solving.printing.latex import latex

from base_tab import BaseTab
from error_utils import friendly_error_message
from parameter_utils import (
    display_function_with_parameters,
    evaluate_function_with_parameters,
    resolve_function_text,
)
from parser_utils import evaluate_symbolic_function, parse_input_to_float, parse_input_to_solving
from symbolic_methods import compute_tab1_result


class BasicIntegrationTab(BaseTab):
    def __init__(self, app, parent):
        super().__init__(app, parent)
        self._latex_preview_state = None
        self._build_widgets()
        self.update_latex_preview()

    def _build_widgets(self):
        tk.Label(self.parent, text="∫", font=("Arial", 60)).grid(
            row=0, column=0, rowspan=2, padx=10, pady=5
        )
        self.upper_entry = tk.Entry(self.parent, width=10, justify="center")
        self.upper_entry.grid(row=0, column=1, padx=5, pady=2)
        self.lower_entry = tk.Entry(self.parent, width=10, justify="center")
        self.lower_entry.grid(row=1, column=1, padx=5, pady=2)
        self.func_entry = tk.Entry(self.parent, width=25)
        self.func_entry.grid(row=0, column=2, rowspan=2, padx=5, pady=5)
        tk.Label(self.parent, text="dx", font=("Arial", 20)).grid(
            row=0, column=3, rowspan=2, padx=5
        )

        self.params_label = tk.Label(self.parent, text="Parameters:")
        self.params_label.grid(row=2, column=0, padx=10, pady=4, sticky="e")
        self.params_entry = tk.Entry(self.parent, width=32)
        self.params_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=4, sticky="w")

        latex_preview_frame = ttk.Frame(self.parent)
        latex_preview_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(6, 2))
        latex_preview_frame.columnconfigure(0, weight=1)

        self.latex_fig = plt.Figure(figsize=(4.4, 1.25), dpi=100)
        self.latex_ax = self.latex_fig.add_subplot(111)
        self.latex_ax.axis("off")
        self.latex_text = self.latex_ax.text(
            0.5,
            0.5,
            "",
            ha="center",
            va="center",
            fontsize=18,
            transform=self.latex_ax.transAxes,
        )

        self.latex_canvas = FigureCanvasTkAgg(self.latex_fig, master=latex_preview_frame)
        self.latex_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.calc_button = ttk.Button(
            self.parent,
            text="Calculate Integral",
            command=self.calculate,
        )
        self.calc_button.grid(row=4, column=0, columnspan=4, pady=10)

        self.result_label = tk.Label(self.parent, text="", fg="green", font=("Arial", 12))
        self.result_label.grid(row=5, column=0, columnspan=4, pady=10)

        self.view_exact_button = ttk.Button(
            self.parent,
            text="View Exact Result",
            command=self.show_exact_result,
        )
        self.view_exact_button.grid(row=6, column=0, columnspan=4, pady=5)

        self.reset_button = ttk.Button(
            self.parent,
            text="Reset",
            command=self.app.reset_inputs,
        )
        self.reset_button.grid(row=7, column=0, columnspan=4, pady=10)

        for entry in (self.func_entry, self.params_entry, self.lower_entry, self.upper_entry):
            entry.bind("<KeyRelease>", self.update_latex_preview)
            entry.bind("<Return>", lambda event: self.calculate())

    def calculate(self):
        if self.worker_running:
            messagebox.showinfo("Info", "A computation is already running.")
            return

        func_str = self.func_entry.get().strip()
        params_text = self.params_entry.get().strip()
        lower_text = self.lower_entry.get().strip()
        upper_text = self.upper_entry.get().strip()

        try:
            resolved_func = resolve_function_text(func_str, params_text)
            shown_func = display_function_with_parameters(func_str, params_text)
        except Exception as exc:
            messagebox.showerror(
                "Error",
                "Error in integration: "
                + friendly_error_message(exc, func_str, lower_text, upper_text),
            )
            return

        self.worker_running = True
        self.start_time = time.perf_counter()
        self.result_label.config(text="Computing...")

        def worker():
            try:
                result = compute_tab1_result(resolved_func, lower_text, upper_text)
                result["input_func"] = func_str
                result["params_text"] = params_text
                result["shown_func"] = shown_func
                result["resolved_func"] = resolved_func
                self.app.root.after(0, lambda: self.finish_result(result))
            except Exception as exc:
                self.app.root.after(0, lambda err=exc: self.finish_error(err))

        threading.Thread(target=worker, daemon=True).start()

    def finish_result(self, result):
        try:
            elapsed = time.perf_counter() - self.start_time if self.start_time else None
            self.app.last_raw_result = result["raw_result"]
            self.app.last_raw_result_type = result["raw_type"]
            self.app.last_numeric_value = result["numeric_value"]

            if result["kind"] == "definite":
                self._finish_definite_result(result, elapsed)
            else:
                self._finish_indefinite_result(result, elapsed)
        finally:
            self.worker_running = False

    def _finish_definite_result(self, result, elapsed):
        time_text = self.format_elapsed(elapsed)
        self.result_label.config(text=f"Definite Integral: {result['display_str']}{time_text}")
        try:
            lower = parse_input_to_float(result["lower_text"])
            upper = parse_input_to_float(result["upper_text"])
            self.app.plot_function(result["resolved_func"], lower, upper)
        except Exception:
            self.app.clear_plot()

        self.app.add_history({
            "type": "definite",
            "display": f"Definite: ∫[{result['lower_text']}, {result['upper_text']}] {result['shown_func']} dx = {result['display_str']}",
            "raw": self.app.last_raw_result,
            "raw_type": self.app.last_raw_result_type,
            "numeric_value": self.app.last_numeric_value,
            "func": result.get("input_func", result["shown_func"]),
            "lower": result["lower_text"],
            "upper": result["upper_text"],
            "error": result["numeric_err"],
            "elapsed": elapsed,
            "params": result.get("params_text", ""),
            "shown_func": result["shown_func"],
            "resolved_func": result.get("resolved_func", result["shown_func"]),
        })

    def _finish_indefinite_result(self, result, elapsed):
        time_text = self.format_elapsed(elapsed)
        if result["closed_form"]:
            self.result_label.config(text=f"Indefinite Integral: {result['display_str']} + C{time_text}")
            display = f"Indefinite: ∫ {result['shown_func']} dx = {self.app.last_raw_result} + C"
        else:
            self.result_label.config(text=f"Indefinite Integral: No closed-form exact result was found.{time_text}")
            display = f"Indefinite: ∫ {result['shown_func']} dx = (no closed-form)"

        self.app.add_history({
            "type": "indefinite",
            "display": display,
            "raw": self.app.last_raw_result,
            "raw_type": self.app.last_raw_result_type,
            "numeric_value": None,
            "func": result.get("input_func", result["shown_func"]),
            "elapsed": elapsed,
            "params": result.get("params_text", ""),
            "shown_func": result["shown_func"],
            "resolved_func": result.get("resolved_func", result["shown_func"]),
        })
        self.app.clear_plot()

    def finish_error(self, error):
        self.worker_running = False
        self.result_label.config(text="")
        messagebox.showerror(
            "Error",
            "Error in integration: "
            + friendly_error_message(
                error,
                self.func_entry.get(),
                self.lower_entry.get(),
                self.upper_entry.get(),
            ),
        )

    def show_exact_result(self):
        if self.app.last_raw_result is None:
            messagebox.showinfo("Exact Result", "No result to display.")
            return

        if self.app.last_raw_result_type == "unevaluated":
            msg = "No closed-form exact result was found."
            if self.app.last_numeric_value is not None:
                msg += f"\n\nNumeric approximation:\n≈ {self.app.last_numeric_value:.10f}"
            else:
                msg += "\n\nNo numeric value available."
            messagebox.showinfo("Exact Result", msg)
            return

        msg = f"Exact symbolic form:\n\n{self.app.last_raw_result}"
        if self.app.last_numeric_value is not None:
            msg += f"\n\nNumeric value:\n≈ {self.app.last_numeric_value:.10f}"
        messagebox.showinfo("Exact Result", msg)

    def update_latex_preview(self, event=None):
        func_str = self.func_entry.get().strip()
        params_text = self.params_entry.get().strip()
        lower_text = self.lower_entry.get().strip()
        upper_text = self.upper_entry.get().strip()
        state = (func_str, params_text, lower_text, upper_text)
        if state == self._latex_preview_state:
            return
        self._latex_preview_state = state

        if not func_str:
            self.clear_latex_preview(remember_state=state)
            return

        try:
            if params_text:
                fexpr = evaluate_function_with_parameters(func_str, params_text)
            else:
                fexpr = evaluate_symbolic_function(func_str)
            f_ltx = latex(fexpr)
            if lower_text and upper_text:
                lower = parse_input_to_solving(lower_text)
                upper = parse_input_to_solving(upper_text)
                full = rf"\int_{{{latex(lower)}}}^{{{latex(upper)}}} {f_ltx}\, dx"
            else:
                full = f_ltx
            self.latex_text.set_text(rf"${full}$")
        except Exception:
            self.latex_text.set_text(r"$\text{(invalid input)}$")

        self.latex_canvas.draw_idle()

    def clear_latex_preview(self, remember_state=None):
        self._latex_preview_state = remember_state
        if not self.latex_text.get_text():
            return
        self.latex_text.set_text("")
        self.latex_canvas.draw_idle()

    def clear_inputs(self):
        self.clear_entries(self.func_entry, self.params_entry, self.lower_entry, self.upper_entry)

    def refresh_after_function_set(self):
        self.update_latex_preview()

    def refill(self, record):
        self.set_entry_text(self.func_entry, record.get("func", ""))
        self.set_entry_text(self.params_entry, record.get("params", ""))
        self.set_entry_text(self.lower_entry, record.get("lower", ""))
        self.set_entry_text(self.upper_entry, record.get("upper", ""))
        self.update_latex_preview()

    def set_language(self, text):
        self.calc_button.config(text=text["calc1"])
        self.reset_button.config(text=text["reset"])
        self.params_label.config(text=text["parameters"])

    def apply_theme(self, theme):
        self.latex_fig.patch.set_facecolor(theme["bg"])
        self.latex_ax.set_facecolor(theme["bg"])
        self.latex_text.set_color(theme["fg"])
        self.latex_canvas.draw_idle()
