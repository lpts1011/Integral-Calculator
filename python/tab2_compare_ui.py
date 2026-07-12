import tkinter as tk
from tkinter import ttk


def show_comparison_window(tab, rows, inputs, elapsed):
    window = tk.Toplevel(tab.app.root)
    window.title(tab.app.text.get("comparison_title", "Numerical Method Comparison"))
    columns = ("method", "result", "error", "time", "segments", "status")
    table = ttk.Treeview(window, columns=columns, show="headings", height=9)
    headings = {
        "method": "Method",
        "result": "Result",
        "error": "Error",
        "time": "Time",
        "segments": "Segments",
        "status": "Status",
    }
    widths = {
        "method": 150,
        "result": 120,
        "error": 100,
        "time": 80,
        "segments": 80,
        "status": 260,
    }
    for column in columns:
        table.heading(column, text=headings[column])
        table.column(column, width=widths[column], anchor="w")
    for row in rows:
        result = "" if row["result"] is None else f"{row['result']:.10g}"
        error = "" if row["error"] is None else f"{row['error']:.3e}"
        table.insert(
            "",
            tk.END,
            values=(
                row["method"],
                result,
                error,
                f"{row['time']:.3f}s",
                row["segments"],
                row["status"],
            ),
        )
    table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ok_rows = [row for row in rows if row["status"] == "ok"]
    if ok_rows:
        best = min(ok_rows, key=lambda row: row["time"])
        tab.app.add_history({
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
