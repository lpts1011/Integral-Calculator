import math
import multiprocessing
import warnings
from functools import lru_cache

from solving.core.numbers import Integer, nan, oo, zoo
from solving.integrals.integrals import Integral, integrate
from solving.printing.str import sstr

from formatting import format_result_for_display, pretty_math_str, tidy_result
from numeric_methods import (
    build_numeric_callable,
    numeric_integrate_with_error,
    validate_numeric_integrand,
)
from parser_utils import (
    evaluate_symbolic_function,
    has_complete_limits,
    parse_input_to_float,
    parse_input_to_solving,
    x_sym,
)


SYMBOLIC_TIMEOUT_SECONDS = 8


class SymbolicTimeoutError(TimeoutError):
    pass


def _run_symbolic_with_timeout(target, args, timeout=SYMBOLIC_TIMEOUT_SECONDS, cancel=None):
    if multiprocessing.current_process().daemon or timeout is None or timeout <= 0:
        return target(*args)

    # Bounded polynomial work avoids process startup for common school inputs.
    if args and isinstance(args[0], str) and len(args[0]) < 1200:
        try:
            expr = evaluate_symbolic_function(args[0])
            if expr.is_polynomial(x_sym) and expr.as_poly(x_sym).degree() <= 128:
                return target(*args)
        except Exception:
            pass
    from symbolic_service import run_isolated
    try:
        return run_isolated(target, args, timeout, cancel)
    except TimeoutError as exc:
        raise SymbolicTimeoutError(str(exc)) from exc


@lru_cache(maxsize=384)
def _run_symbolic_cached(target, args, timeout, cancel=None):
    if cancel is not None and cancel.is_set():
        raise ValueError("Calculation cancelled.")
    return _run_symbolic_with_timeout(target, args, timeout, cancel)


def _compute_tab1_result_direct(func_str, lower_text, upper_text):
    shown_func = func_str
    expr = evaluate_symbolic_function(func_str)

    if has_complete_limits(lower_text, upper_text):
        lower = parse_input_to_solving(lower_text)
        upper = parse_input_to_solving(upper_text)
        res = integrate(expr, (x_sym, lower, upper))
        if not res.has(Integral):
            res = tidy_result(res)
        antiderivative = integrate(expr, x_sym) if expr.is_polynomial(x_sym) else None
        info = format_result_for_display(res, symbolic_len_limit=50)
        raw_result = info["raw"]
        raw_type = info["type"]
        numeric_value = info["numeric"]
        numeric_err = None
        display_str = info["display"]

        if info["type"] == "unevaluated":
            numeric_value, numeric_err = numerical_fallback(func_str, lower_text, upper_text)
            display_str = f"≈ {numeric_value:.10g}"

        if numeric_value is None:
            try:
                numeric_value = float(res.evalf())
            except Exception:
                pass

        return {
            "kind": "definite",
            "shown_func": shown_func,
            "lower_text": lower_text,
            "upper_text": upper_text,
            "display_str": display_str,
            "raw_result": raw_result,
            "raw_type": raw_type,
            "numeric_value": numeric_value,
            "numeric_err": numeric_err,
            "antiderivative": sstr(antiderivative) if antiderivative is not None else None,
        }

    ind = integrate(expr, x_sym)
    if isinstance(ind, Integral) or ind.has(Integral):
        return {
            "kind": "indefinite",
            "shown_func": shown_func,
            "display_str": "(no closed-form)",
            "raw_result": sstr(ind),
            "raw_type": "unevaluated",
            "numeric_value": None,
            "closed_form": False,
        }

    ind = tidy_result(ind)
    return {
        "kind": "indefinite",
        "shown_func": shown_func,
        "display_str": pretty_math_str(ind),
        "raw_result": sstr(ind),
        "raw_type": "exact",
        "numeric_value": None,
        "closed_form": True,
    }


def compute_tab1_result(func_str, lower_text, upper_text, timeout=SYMBOLIC_TIMEOUT_SECONDS, cancel=None):
    return dict(_run_symbolic_cached(
        _compute_tab1_result_direct,
        (func_str, lower_text, upper_text),
        timeout, cancel,
    ))


def _compute_general_integral_direct(func_str, lower_text, upper_text):
    f = evaluate_symbolic_function(func_str)
    lower_norm = lower_text.strip().lower()
    upper_norm = upper_text.strip().lower()
    L = -oo if lower_norm in ("-inf", "-oo") else parse_input_to_solving(lower_text)
    U = oo if upper_norm in ("inf", "+inf", "oo", "+oo") else parse_input_to_solving(upper_text)
    if L == U:
        return {"type": "exact", "expr": Integer(0)}

    res = integrate(f, (x_sym, L, U))
    if isinstance(res, Integral) or res.has(Integral):
        return {"type": "unevaluated", "expr": res}
    if res in (oo, -oo, zoo, nan) or res.has(oo, -oo, zoo, nan):
        return {"type": "divergent", "expr": res}
    try:
        if not bool(res.is_finite):
            return {"type": "divergent", "expr": res}
    except Exception:
        pass
    return {"type": "exact", "expr": tidy_result(res)}


def compute_general_integral(func_str, lower_text, upper_text, timeout=SYMBOLIC_TIMEOUT_SECONDS, cancel=None):
    return dict(_run_symbolic_cached(
        _compute_general_integral_direct,
        (func_str, lower_text, upper_text),
        timeout, cancel,
    ))


NOT_CONVERGED_MESSAGE = (
    "No exact value was found and the numerical value did not converge; "
    "the integral may diverge."
)


def numerical_fallback(func_str, lower_text, upper_text, *, cancel=None):
    """Value and error estimate when no exact form is found, or not found in time."""
    from scipy.integrate import IntegrationWarning

    from integration_engine import EvaluationBudget, NumericalConvergenceError, NumericalOptions

    expr = evaluate_symbolic_function(func_str)
    lower, upper = parse_input_to_float(lower_text), parse_input_to_float(upper_text)
    f_num = build_numeric_callable(expr)
    if math.isfinite(lower) and math.isfinite(upper):
        from tab2_logic import compute_segmented_numerical_integral
        try:
            value, error, _segments = compute_segmented_numerical_integral(
                expr, "Auto", f_num, lower, upper, options={"cancel": cancel},
            )
        except NumericalConvergenceError as exc:
            raise ValueError(NOT_CONVERGED_MESSAGE) from exc
        return value, error

    budget = EvaluationBudget(f_num, NumericalOptions(cancel=cancel))
    budget.check()
    validate_numeric_integrand(expr, f_num, lower, upper, allow_endpoint_singularities=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error", IntegrationWarning)
        try:
            return numeric_integrate_with_error(budget.scalar, lower, upper)
        except IntegrationWarning as exc:
            raise ValueError(NOT_CONVERGED_MESSAGE) from exc
