import re

import calengine as np

from formatting import pretty_math_str
from numeric_methods import build_numeric_callable, numeric_values, find_symbolic_singularities
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
    visible_limits=None,
):
    try:
        if not np.isfinite(lower) or not np.isfinite(upper) or lower == upper:
            clear_plot(ax, canvas, theme)
            return
        bound_lower, bound_upper = sorted((lower, upper))
        plot_lower, plot_upper = sorted(visible_limits or (lower, upper))
        from integration_engine import structural_points, oscillatory_factor
        from interval_utils import find_piecewise_breakpoints
        expr = evaluate_symbolic_function(func_str)
        function = build_numeric_callable(expr)
        factor = oscillatory_factor(expr)
        cycles = abs(factor[2]*(plot_upper-plot_lower))/(2*np.pi) if factor else 0
        count = min(20001,max(257,int(np.ceil(cycles*12))+1))
        breaks = sorted(set(find_symbolic_singularities(expr,plot_lower,plot_upper)
                            +find_piecewise_breakpoints(expr,plot_lower,plot_upper)
                            +list(split_points or [])))
        x_vals = np.unique(np.concatenate((np.linspace(plot_lower,plot_upper,count),
                                          np.asarray(structural_points(expr,plot_lower,plot_upper),dtype=float))))
        with np.errstate(all="ignore"):
            y_vals = numeric_values(function,x_vals)
            for _ in range(3):
                if len(x_vals) >= 20001:break
                mids=(x_vals[:-1]+x_vals[1:])/2
                middle_values=numeric_values(function,mids)
                residual=np.abs(middle_values-(y_vals[:-1]+y_vals[1:])/2)
                scale=np.maximum(1.,np.maximum(np.abs(middle_values),np.maximum(np.abs(y_vals[:-1]),np.abs(y_vals[1:]))))
                refine=mids[np.isfinite(residual)&(residual > .015*scale)]
                refine=refine[:20001-len(x_vals)]
                if not refine.size:break
                x_vals=np.unique(np.concatenate((x_vals,refine)))
                y_vals=numeric_values(function,x_vals)
        y_vals = np.asarray(y_vals, dtype=float)
        y_vals[~np.isfinite(y_vals)] = np.nan
        for point in breaks:
            position = np.searchsorted(x_vals,float(point))
            y_vals[max(0,position-1):min(len(y_vals),position+1)] = np.nan

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
            area_mask = (x_vals >= bound_lower) & (x_vals <= bound_upper)
            positive_mask = finite_mask & area_mask & (y_vals >= 0)
            negative_mask = finite_mask & area_mask & (y_vals < 0)
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
        for bound in (bound_lower, bound_upper):
            ax.axvline(bound, linewidth=0.9, linestyle="-.", color=guide_color, alpha=0.75)
        for point in split_points or []:
            if plot_lower < float(point) < plot_upper:
                ax.axvline(float(point), linewidth=0.8, linestyle=":", color=guide_color, alpha=0.8)
        roots = _approx_zero_crossings(x_vals, y_vals, function=function)
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
        if visible_limits is not None:
            ax.set_xlim(*visible_limits)
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


def _approx_zero_crossings(x_vals, y_vals, max_roots=25, *, function=None):
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
            if function is not None:
                try:
                    from scipy.optimize import brentq
                    root = brentq(lambda x:float(function(x)),x0,x1)
                    value = float(function(root))
                    if not np.isfinite(value) or abs(value)>1e-7*max(1.,min(abs(y0),abs(y1))):
                        continue
                except Exception:
                    continue
            else:
                nearby = y_vals[max(0,index-3):min(len(y_vals),index+5)]
                jumps = np.abs(np.diff(nearby))
                if len(jumps)>2 and abs(y1-y0)>10*max(1e-15,float(np.nanmedian(jumps))):
                    continue
                root = x0 - y0 * (x1 - x0) / (y1 - y0)
        else:
            continue
        if not roots or abs(root - roots[-1]) > 1e-6:
            roots.append(float(root))
        if len(roots) >= max_roots:
            break
    return roots
