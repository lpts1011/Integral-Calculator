import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from base_tab import BaseTab
from error_utils import friendly_error_message
from formatting import format_result_for_display
from parameter_utils import display_function_with_parameters, resolve_function_text
from symbolic_methods import compute_general_integral


class ImproperIntegralTab(BaseTab):
    def __init__(self, app, parent):
        super().__init__(app, parent)
        self._build_widgets()

    def _build_widgets(self):
        self.func_label = tk.Label(self.parent, text="Enter target function:")
        self.func_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.func_entry = tk.Entry(self.parent, width=30)
        self.func_entry.grid(row=0, column=1, padx=10, pady=5)

        self.params_label = tk.Label(self.parent, text="Parameters:")
        self.params_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.params_entry = tk.Entry(self.parent, width=30)
        self.params_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.lower_label = tk.Label(self.parent, text="Lower limit:")
        self.lower_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.lower_entry = tk.Entry(self.parent, width=12)
        self.lower_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        self.upper_label = tk.Label(self.parent, text="Upper limit:")
        self.upper_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.upper_entry = tk.Entry(self.parent, width=12)
        self.upper_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        self.calc_button = ttk.Button(
            self.parent,
            text="Compute Integral",
            command=self.compute,
        )
        self.calc_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.reset_button = ttk.Button(
            self.parent,
            text="Reset",
            command=self.app.reset_inputs,
        )
        self.reset_button.grid(row=5, column=0, columnspan=2, pady=10)

        self.result_label = tk.Label(self.parent, text="", fg="green", font=("Arial", 12))
        self.result_label.grid(row=6, column=0, columnspan=2, pady=10)

        for entry in (self.func_entry, self.params_entry, self.lower_entry, self.upper_entry):
            entry.bind("<Return>", lambda event: self.compute())

    def compute(self):
        try:
            func_str = self.func_entry.get().strip()
            params_text = self.params_entry.get().strip()
            lower = self.lower_entry.get().strip()
            upper = self.upper_entry.get().strip()
            resolved_func = resolve_function_text(func_str, params_text)
            shown_func = display_function_with_parameters(func_str, params_text)
            if not lower or not upper:
                raise ValueError("Please provide both lower and upper limits (use -inf/inf for infinity).")

            if self.worker_running:
                messagebox.showinfo("Info", "A computation is already running.")
                return

            self.worker_running = True
            self.start_time = time.perf_counter()
            self.result_label.config(text="Computing...")

            def worker():
                try:
                    out = compute_general_integral(resolved_func, lower, upper)
                    self.app.root.after(
                        0,
                        lambda: self.finish_result(
                            out,
                            shown_func,
                            lower,
                            upper,
                            func_str,
                            params_text,
                            resolved_func,
                        ),
                    )
                except Exception as exc:
                    self.app.root.after(0, lambda err=exc: self.finish_error(err))

            threading.Thread(target=worker, daemon=True).start()
        except Exception as exc:
            self.worker_running = False
            messagebox.showerror(
                "Error",
                "An error occurred in computing the integral: "
                + friendly_error_message(exc, func_str, lower, upper),
            )

    def finish_result(self, out, shown_func, lower, upper, input_func, params_text, resolved_func):
        try:
            elapsed = time.perf_counter() - self.start_time if self.start_time else None
            time_text = self.format_elapsed(elapsed)
            if out["type"] == "exact":
                info = format_result_for_display(out["expr"])
                display_str = info["display"]
                self.result_label.config(text=f"Result: {display_str}{time_text}")
            elif out["type"] == "divergent":
                display_str = "Divergent"
                self.result_label.config(text=f"Result: Divergent integral{time_text}")
            else:
                display_str = "No closed-form"
                self.result_label.config(text=f"Result: No closed-form expression found{time_text}")

            self.app.add_history({
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
            self.app.clear_plot()
        finally:
            self.worker_running = False

    def finish_error(self, error):
        self.worker_running = False
        self.result_label.config(text="")
        messagebox.showerror(
            "Error",
            "An error occurred in computing the integral: "
            + friendly_error_message(
                error,
                self.func_entry.get(),
                self.lower_entry.get(),
                self.upper_entry.get(),
            ),
        )

    def clear_inputs(self):
        self.clear_entries(self.func_entry, self.params_entry, self.lower_entry, self.upper_entry)

    def refill(self, record):
        self.set_entry_text(self.func_entry, record.get("func", ""))
        self.set_entry_text(self.params_entry, record.get("params", ""))
        self.set_entry_text(self.lower_entry, record.get("lower", ""))
        self.set_entry_text(self.upper_entry, record.get("upper", ""))

    def set_language(self, text):
        self.calc_button.config(text=text["calc3"])
        self.reset_button.config(text=text["reset"])
        self.lower_label.config(text=text["lower"])
        self.upper_label.config(text=text["upper"])
        self.func_label.config(text=text["func"])
        self.params_label.config(text=text["parameters"])
