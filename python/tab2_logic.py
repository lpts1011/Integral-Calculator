import time
from dataclasses import dataclass

import calengine as np

from interval_utils import build_subintervals, find_piecewise_breakpoints, parse_split_points
from numeric_methods import (
    FAST_METHODS,
    build_numeric_callable,
    compute_numerical_integral,
    validate_numeric_integrand,
)
from parser_utils import evaluate_symbolic_function, has_complete_limits, parse_input_to_float
from symbolic_methods import compute_tab2_symbolic_result


FINITE_ONLY_METHODS = {
    "Gaussian Quadrature",
    "Romberg",
    "Adaptive Simpson",
    "Simpson",
    "Trapezoidal",
    "Rectangle",
    "Simpson 3/8",
}


@dataclass(frozen=True)
class Tab2Inputs:
    func_str: str
    input_func: str
    shown_func: str
    params_text: str
    method: str
    integration_method: str
    lower_text: str
    upper_text: str
    has_limits: bool
    lower: float | None
    upper: float | None
    delta: float | None
    split_text: str = ""


def prepare_tab2_inputs(
    func_str,
    method,
    integration_method,
    lower_text,
    upper_text,
    delta_text,
    split_text="",
    shown_func=None,
    input_func=None,
    params_text="",
):
    if method == "Numerical Integration" and (not lower_text or not upper_text):
        raise ValueError("Numerical integration requires both lower and upper limits.")

    lower = parse_input_to_float(lower_text) if lower_text else None
    upper = parse_input_to_float(upper_text) if upper_text else None
    delta = None

    if delta_text:
        delta = parse_input_to_float(delta_text)
        if delta <= 0:
            raise ValueError("Step size (delta) must be positive.")

    return Tab2Inputs(
        func_str=func_str,
        input_func=input_func or func_str,
        shown_func=shown_func or func_str,
        params_text=params_text,
        method=method,
        integration_method=integration_method,
        lower_text=lower_text,
        upper_text=upper_text,
        has_limits=has_complete_limits(lower_text, upper_text),
        lower=lower,
        upper=upper,
        delta=delta,
        split_text=split_text,
    )


def should_use_indeterminate_progress(inputs):
    return inputs.method != "Symbolic Integration" and inputs.integration_method in FAST_METHODS


def run_tab2_calculation(inputs, emit_event):
    if inputs.method == "Symbolic Integration":
        _run_symbolic_tab2(inputs, emit_event)
        return

    _run_numeric_tab2(inputs, emit_event)


def _run_symbolic_tab2(inputs, emit_event):
    for value in range(0, 61, 20):
        time.sleep(0.03)
        emit_event(("progress", value))

    result = compute_tab2_symbolic_result(
        inputs.func_str,
        inputs.lower_text,
        inputs.upper_text,
    )
    kind = result["kind"]

    if kind == "symbolic_result":
        emit_event((
            "symbolic_result",
            result["formatted"],
            result["lower"],
            result["upper"],
            inputs.shown_func,
            inputs.func_str,
            inputs.input_func,
            inputs.params_text,
        ))
    elif kind == "symbolic_indef":
        emit_event((
            "symbolic_indef",
            result["formatted"],
            inputs.shown_func,
            inputs.func_str,
            inputs.input_func,
            inputs.params_text,
        ))
    elif kind == "symbolic_unevaluated":
        emit_event((
            "symbolic_unevaluated",
            result["lower"],
            result["upper"],
            inputs.shown_func,
            inputs.func_str,
            inputs.input_func,
            inputs.params_text,
        ))
    elif kind == "symbolic_indef_unevaluated":
        emit_event((
            "symbolic_indef_unevaluated",
            inputs.shown_func,
            inputs.func_str,
            inputs.input_func,
            inputs.params_text,
        ))
    else:
        raise ValueError(f"Unknown symbolic result kind: {kind}")

    emit_event(("progress", 100))


def _run_numeric_tab2(inputs, emit_event):
    lower = inputs.lower
    upper = inputs.upper
    if lower is None or upper is None:
        raise ValueError("Numerical integration requires both lower and upper limits.")

    if (
        not np.isfinite(lower) or not np.isfinite(upper)
    ) and inputs.integration_method in FINITE_ONLY_METHODS:
        raise ValueError(f"{inputs.integration_method} requires finite lower and upper limits.")

    expr = evaluate_symbolic_function(inputs.func_str)
    f_num = build_numeric_callable(expr)
    result, error_estimate, segments = compute_segmented_numerical_integral(
        expr,
        inputs.integration_method,
        f_num,
        lower,
        upper,
        inputs.delta,
        inputs.split_text,
        lambda value: emit_event(("progress", value)),
    )
    emit_event((
        "numeric_result",
        result,
        inputs.integration_method,
        lower,
        upper,
        inputs.shown_func,
        inputs.func_str,
        error_estimate,
        segments,
        inputs.input_func,
        inputs.params_text,
        inputs.split_text,
    ))


def compute_segmented_numerical_integral(
    expr,
    integration_method,
    f_num,
    lower,
    upper,
    delta=None,
    split_text="",
    progress_callback=None,
    validated_intervals=None,
):
    manual_points = parse_split_points(split_text, lower, upper)
    auto_points = find_piecewise_breakpoints(expr, lower, upper)
    split_points = sorted(set(manual_points + auto_points))
    intervals = build_subintervals(lower, upper, split_points)
    if not intervals:
        return 0.0, None, []

    total = 0.0
    squared_error = 0.0
    has_error = False
    segment_results = []
    progress_callback = progress_callback or (lambda value: None)

    for index, (left, right) in enumerate(intervals):
        interval_key = (float(left), float(right))
        if validated_intervals is None or interval_key not in validated_intervals:
            validate_numeric_integrand(expr, f_num, left, right)
            if validated_intervals is not None:
                validated_intervals.add(interval_key)

        def segment_progress(value, idx=index):
            progress_callback(int((idx * 100 + value) / len(intervals)))

        value, error_estimate = compute_numerical_integral(
            integration_method,
            f_num,
            left,
            right,
            delta,
            segment_progress,
        )
        total += value
        if error_estimate is not None:
            has_error = True
            squared_error += float(error_estimate) ** 2
        segment_results.append({
            "lower": left,
            "upper": right,
            "result": value,
            "error": error_estimate,
        })

    progress_callback(100)
    combined_error = float(np.sqrt(squared_error)) if has_error else None
    return float(total), combined_error, segment_results


def compare_numerical_methods(inputs):
    if inputs.lower is None or inputs.upper is None:
        raise ValueError("Numerical method comparison requires both lower and upper limits.")
    if not np.isfinite(inputs.lower) or not np.isfinite(inputs.upper):
        raise ValueError("Numerical method comparison requires finite lower and upper limits.")

    expr = evaluate_symbolic_function(inputs.func_str)
    f_num = build_numeric_callable(expr)
    methods = [
        "Rectangle",
        "Trapezoidal",
        "Simpson",
        "Simpson 3/8",
        "Romberg",
        "Gaussian Quadrature",
        "Adaptive Simpson",
        "Monte Carlo",
    ]
    rows = []
    validated_intervals = set()
    for method in methods:
        started = time.perf_counter()
        try:
            result, error_estimate, segments = compute_segmented_numerical_integral(
                expr,
                method,
                f_num,
                inputs.lower,
                inputs.upper,
                inputs.delta,
                inputs.split_text,
                validated_intervals=validated_intervals,
            )
            rows.append({
                "method": method,
                "result": result,
                "error": error_estimate,
                "time": time.perf_counter() - started,
                "segments": len(segments),
                "status": "ok",
            })
        except Exception as exc:
            rows.append({
                "method": method,
                "result": None,
                "error": None,
                "time": time.perf_counter() - started,
                "segments": 0,
                "status": str(exc),
            })
    return rows
