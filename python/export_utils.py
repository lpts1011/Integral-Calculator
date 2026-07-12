from solving.core.sympify import sympify
from solving.printing.latex import latex

from parser_utils import x_sym


def build_markdown_export(record):
    if not record:
        return "No calculation result is available."

    func = record.get("func", "")
    shown_func = record.get("shown_func", func)
    lower = record.get("lower")
    upper = record.get("upper")
    result = record.get("raw", "")
    method = record.get("method") or record.get("type", "")
    elapsed = record.get("elapsed")
    error = record.get("error")
    params = record.get("params")
    split_points = record.get("split_points")
    segments = record.get("segments")

    lines = ["## Integration Result", ""]
    lines.append(f"- Function: `{shown_func}`")
    if params:
        lines.append(f"- Parameters: `{params}`")
    if lower not in (None, "") and upper not in (None, ""):
        lines.append(f"- Interval: `{lower}` to `{upper}`")
    if split_points:
        lines.append(f"- Split points: `{split_points}`")
    lines.append(f"- Method: `{method}`")
    if _is_comparison_rows(result):
        lines.append("- Result: numerical method comparison")
        lines.extend(_markdown_comparison_table(result))
    else:
        lines.append(f"- Result: `{result}`")
    if error is not None:
        lines.append(f"- Error estimate: `{error}`")
    if segments:
        parts = [
            f"[{segment['lower']}, {segment['upper']}] -> {segment['result']}"
            for segment in segments
        ]
        lines.append(f"- Segments: `{'; '.join(parts)}`")
    if elapsed is not None:
        lines.append(f"- Time: `{elapsed:.3f}s`")
    return "\n".join(lines)


def build_latex_export(record):
    if not record:
        return "No calculation result is available."

    func = str(record.get("resolved_func") or record.get("func", ""))
    lower = record.get("lower")
    upper = record.get("upper")
    raw = record.get("raw")

    if _is_comparison_rows(raw):
        return _latex_comparison_table(raw)

    try:
        f_latex = latex(sympify(func.replace("^", "**")))
    except Exception:
        f_latex = func

    try:
        result_latex = latex(sympify(raw)) if raw is not None else ""
    except Exception:
        result_latex = str(raw)

    if lower not in (None, "") and upper not in (None, ""):
        return rf"\int_{{{lower}}}^{{{upper}}} {f_latex}\, d{x_sym} = {result_latex}"
    return rf"\int {f_latex}\, d{x_sym} = {result_latex} + C"


def _is_comparison_rows(value):
    return (
        isinstance(value, list)
        and value
        and all(isinstance(row, dict) and "method" in row for row in value)
    )


def _markdown_comparison_table(rows):
    lines = [
        "",
        "| Method | Result | Error | Time | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        result = "" if row.get("result") is None else f"{row['result']:.10g}"
        error = "" if row.get("error") is None else f"{row['error']:.3e}"
        elapsed = "" if row.get("time") is None else f"{row['time']:.3f}s"
        lines.append(f"| {row.get('method', '')} | {result} | {error} | {elapsed} | {row.get('status', '')} |")
    return lines


def _latex_comparison_table(rows):
    body = []
    for row in rows:
        result = "" if row.get("result") is None else f"{row['result']:.10g}"
        error = "" if row.get("error") is None else f"{row['error']:.3e}"
        elapsed = "" if row.get("time") is None else f"{row['time']:.3f}s"
        status = str(row.get("status", "")).replace("&", r"\&")
        method = str(row.get("method", "")).replace("&", r"\&")
        body.append(rf"{method} & {result} & {error} & {elapsed} & {status} \\")
    return "\n".join([
        r"\begin{tabular}{lrrrl}",
        r"Method & Result & Error & Time & Status \\",
        r"\hline",
        *body,
        r"\end{tabular}",
    ])
