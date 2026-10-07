import time
from dataclasses import replace
from integration_engine import get_options, NumericalOptions, structural_points
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
    "Auto",
    "Adaptive Gauss-Kronrod",
    "Oscillatory Quadrature",
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
    options: NumericalOptions | None = None


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
    options=None,
):
    if method == "Numerical Integration" and (not lower_text or not upper_text):
        raise ValueError("Numerical integration requires both lower and upper limits.")

    lower = parse_input_to_float(lower_text) if lower_text else None
    upper = parse_input_to_float(upper_text) if upper_text else None
    delta = None

    if delta_text:
        delta = parse_input_to_float(delta_text)
        if not np.isfinite(delta) or delta <= 0:
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
        options=get_options(options),
    )


def should_use_indeterminate_progress(inputs):
    return inputs.method != "Symbolic Integration" and inputs.integration_method in FAST_METHODS


def run_tab2_calculation(inputs, emit_event):
    if inputs.method == "Symbolic Integration":
        _run_symbolic_tab2(inputs, emit_event)
        return

    _run_numeric_tab2(inputs, emit_event)


def _run_symbolic_tab2(inputs, emit_event):
    emit_event(("progress", 0))

    result = compute_tab2_symbolic_result(
        inputs.func_str,
        inputs.lower_text,
        inputs.upper_text,
        cancel=inputs.options.cancel if inputs.options else None,
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
        options=inputs.options,
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
    *, options=None,
):
    opts = get_options(options)
    manual_points = parse_split_points(split_text, lower, upper)
    auto_points = find_piecewise_breakpoints(expr, lower, upper)
    split_points = sorted(set(manual_points + auto_points))
    intervals = build_subintervals(lower, upper, split_points)
    if not intervals:
        return 0.0, None, []

    total = 0.0
    squared_error = 0.0
    deterministic_error = 0.0
    evaluations = 0
    started = time.perf_counter()
    has_error = False
    segment_results = []
    progress_callback = progress_callback or (lambda value: None)

    for index, (left, right) in enumerate(intervals):
        interval_key = (float(left), float(right))
        segment_function = f_num
        if left in auto_points or right in auto_points:
            # A branch value at a jump has zero measure. Closed-node rules use
            # the one-sided branch belonging to this integration panel.
            def segment_function(values, left=left, right=right):
                nodes = np.asarray(values, dtype=float)
                if left in auto_points:
                    nodes = np.where(nodes == left, np.nextafter(left, right), nodes)
                if right in auto_points:
                    nodes = np.where(nodes == right, np.nextafter(right, left), nodes)
                return f_num(nodes)
            segment_function.expression = expr
        if validated_intervals is None or interval_key not in validated_intervals:
            validate_numeric_integrand(expr, f_num, left, right,
                allow_endpoint_singularities=integration_method in {"Auto", "Adaptive Gauss-Kronrod", "Oscillatory Quadrature"})
            if validated_intervals is not None:
                validated_intervals.add(interval_key)

        def segment_progress(value, idx=index):
            progress_callback(int((idx * 100 + value) / len(intervals)))

        remaining = opts.max_evaluations-evaluations
        if remaining < 32:
            raise ValueError("Evaluation budget exceeded across subintervals.")
        segment_options = replace(opts, epsabs=opts.epsabs/len(intervals),
            max_evaluations=remaining, max_seconds=max(1e-9,opts.max_seconds-(time.perf_counter()-started)),
            seed=opts.seed+index*104729)
        value, error_estimate, diagnostics = compute_numerical_integral(
            integration_method,
            segment_function,
            left,
            right,
            delta,
            segment_progress, options=segment_options, return_diagnostics=True,
        )
        evaluations += diagnostics["evaluations"]
        total += value
        if error_estimate is not None:
            has_error = True
            if diagnostics["error_kind"] == "standard_error":
                squared_error += float(error_estimate) ** 2
            else:
                deterministic_error += abs(float(error_estimate))
        segment_results.append({
            "lower": left,
            "upper": right,
            "result": value,
            "error": error_estimate,
            "diagnostics": diagnostics,
        })

    progress_callback(100)
    combined_error = deterministic_error + float(np.sqrt(squared_error)) if has_error else None
    if combined_error is not None and combined_error > max(opts.epsabs, opts.epsrel*abs(total)):
        for segment in segment_results:
            segment["diagnostics"]["status"] = "tolerance_not_met"
    if options is None and integration_method in {"Rectangle", "Trapezoidal", "Simpson", "Simpson 3/8", "Romberg"}:
        combined_error = None
    return float(total), combined_error, segment_results


def compare_numerical_methods(inputs):
    from reference_utils import independent_reference
    import statistics
    if inputs.lower is None or inputs.upper is None:
        raise ValueError("Numerical method comparison requires both lower and upper limits.")
    if not np.isfinite(inputs.lower) or not np.isfinite(inputs.upper):
        raise ValueError("Numerical method comparison requires finite limits.")
    expr = evaluate_symbolic_function(inputs.func_str)
    f_num = build_numeric_callable(expr)
    reference, reference_kind = independent_reference(inputs.func_str, inputs.lower, inputs.upper)
    methods = ["Rectangle", "Trapezoidal", "Simpson", "Simpson 3/8", "Romberg",
               "Gaussian Quadrature", "Adaptive Simpson", "Adaptive Gauss-Kronrod",
               "Oscillatory Quadrature", "Monte Carlo"]
    opts = get_options(inputs.options)
    rows = []
    for method in methods:
        try:
            # Warm caches and validate outside the timed repeated measurements.
            compute_segmented_numerical_integral(expr,method,f_num,inputs.lower,inputs.upper,
                inputs.delta,inputs.split_text,options=opts)
            times = []
            for trial in range(opts.repeats):
                trial_options = replace(opts,seed=opts.seed+trial)
                started = time.perf_counter()
                value, estimate, segments = compute_segmented_numerical_integral(
                    expr,method,f_num,inputs.lower,inputs.upper,inputs.delta,inputs.split_text,
                    options=trial_options)
                times.append(time.perf_counter()-started)
            actual_error = abs(value-reference) if reference is not None else None
            target = max(opts.epsabs,opts.epsrel*abs(value))
            status = "ok" if actual_error is not None and actual_error <= target else "accuracy_not_confirmed"
            rows.append({"method":method,"result":value,"error":estimate,"actual_error":actual_error,
                "time":statistics.median(times),"segments":len(segments),"status":status,
                "evaluations":sum(part["diagnostics"]["evaluations"] for part in segments),
                "reference":reference,"reference_kind":reference_kind,"repeats":opts.repeats,
                "error_kind":"standard_error" if method == "Monte Carlo" else "estimated_absolute_error"})
        except Exception as exc:
            rows.append({"method":method,"result":None,"error":None,"actual_error":None,
                "time":0.,"segments":0,"status":str(exc),"evaluations":0,
                "reference":reference,"reference_kind":reference_kind,"repeats":opts.repeats})
    return rows
