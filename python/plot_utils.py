import re

import calengine as np
from matplotlib.figure import Figure

from formatting import pretty_math_str
from numeric_methods import build_numeric_callable, numeric_values
from parser_utils import evaluate_symbolic_function


def evaluate_function(x_vals, func_str: str):
    expr = evaluate_symbolic_function(func_str)
    f = build_numeric_callable(expr)
    return numeric_values(f, np.array(x_vals, dtype=float))


def format_plot_expression(func_str: str) -> str:
    """Return readable mathematical notation without changing evaluation input."""
    try:
        display = pretty_math_str(evaluate_symbolic_function(func_str))
    except Exception:
        display = str(func_str).replace("**", "^").replace("pi", "π")
    display = re.sub(
        r"e\^\(([+-]?(?:[A-Za-z_]\w*|\d+(?:\.\d+)?))\)",
        r"e^\1",
        display,
    )
    return display.replace("*", " · ")


def init_plot_area(parent_frame):
    import tkinter as tk

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    fig = Figure(figsize=(8, 5.2), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_title("Function Graph")
    ax.grid(True)
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    toolbar = NavigationToolbar2Tk(canvas, parent_frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)
    return fig, ax, canvas, toolbar


def clear_plot(ax, canvas, theme=None):
    ax.clear()
    if theme:
        _apply_axis_theme(ax.figure, ax, theme)
    ax.set_title("Function Graph")
    if theme:
        ax.grid(True, color=theme["grid"])
    else:
        ax.grid(True)
    canvas.draw_idle()


def plot_embedded(
    func_str: str,
    lower: float,
    upper: float,
    ax,
    canvas,
    theme=None,
    shade=True,
    split_points=None,
):
    try:
        if not np.isfinite(lower) or not np.isfinite(upper) or lower == upper:
            clear_plot(ax, canvas, theme)
            return
        plot_lower, plot_upper = sorted((lower, upper))
        x_vals = np.linspace(plot_lower, plot_upper, 500)
        y_vals = evaluate_function(x_vals, func_str)
        y_vals = np.asarray(y_vals, dtype=float)
        y_vals[~np.isfinite(y_vals)] = np.nan
        y_vals[np.abs(y_vals) > 1e6] = np.nan

        ax.clear()
        if theme:
            _apply_axis_theme(ax.figure, ax, theme)
        line_color = theme["accent"] if theme else None
        positive_color = theme["success"] if theme else "tab:green"
        negative_color = theme["danger"] if theme else "tab:red"
        guide_color = theme["muted"] if theme else "0.35"
        display_func = format_plot_expression(func_str)
        ax.plot(x_vals, y_vals, color=line_color, label=f"f(x) = {display_func}")
        if shade:
            finite_mask = np.isfinite(y_vals)
            positive_mask = finite_mask & (y_vals >= 0)
            negative_mask = finite_mask & (y_vals < 0)
            ax.fill_between(
                x_vals,
                0,
                y_vals,
                where=positive_mask,
                color=positive_color,
                alpha=0.18,
                interpolate=True,
                label="Positive area",
            )
            ax.fill_between(
                x_vals,
                0,
                y_vals,
                where=negative_mask,
                color=negative_color,
                alpha=0.18,
                interpolate=True,
                label="Negative area",
            )
        ax.axhline(0, linewidth=0.8, linestyle="--", color=guide_color)
        ax.axvline(0, linewidth=0.8, linestyle="--", color=guide_color)
        for bound in (plot_lower, plot_upper):
            ax.axvline(bound, linewidth=0.9, linestyle="-.", color=guide_color, alpha=0.75)
        for point in split_points or []:
            if plot_lower < float(point) < plot_upper:
                ax.axvline(float(point), linewidth=0.8, linestyle=":", color=guide_color, alpha=0.8)
        roots = _approx_zero_crossings(x_vals, y_vals)
        if roots:
            ax.scatter(
                roots,
                np.zeros(len(roots)),
                s=18,
                color=negative_color,
                zorder=3,
                label="Zeros",
            )
        ax.set_title(f"Function Graph: {display_func}")
        ax.set_xlabel("x")
        ax.set_ylabel("f(x)")
        if theme:
            ax.grid(True, color=theme["grid"])
        else:
            ax.grid(True)
        ax.legend()
        canvas.draw_idle()
    except Exception:
        clear_plot(ax, canvas, theme)


def _apply_axis_theme(fig, ax, theme):
    fig.patch.set_facecolor(theme["plot_bg"])
    ax.set_facecolor(theme["plot_bg"])
    ax.title.set_color(theme["fg"])
    ax.xaxis.label.set_color(theme["fg"])
    ax.yaxis.label.set_color(theme["fg"])
    ax.tick_params(colors=theme["fg"])
    for spine in ax.spines.values():
        spine.set_color(theme["muted"])


def _approx_zero_crossings(x_vals, y_vals, max_roots=25):
    roots = []
    finite = np.isfinite(y_vals)
    for index in range(len(x_vals) - 1):
        if not (finite[index] and finite[index + 1]):
            continue
        y0 = y_vals[index]
        y1 = y_vals[index + 1]
        x0 = x_vals[index]
        x1 = x_vals[index + 1]
        if y0 == 0:
            root = x0
        elif y0 * y1 < 0:
            root = x0 - y0 * (x1 - x0) / (y1 - y0)
        else:
            continue
        if not roots or abs(root - roots[-1]) > 1e-6:
            roots.append(float(root))
        if len(roots) >= max_roots:
            break
    return roots
