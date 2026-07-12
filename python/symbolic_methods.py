import multiprocessing
from functools import lru_cache
from queue import Empty

from solving.core.numbers import Integer, nan, oo, zoo
from solving.integrals.integrals import Integral, integrate
from solving.printing.str import sstr
from solving.simplify.simplify import nsimplify

from formatting import format_result_for_display, pretty_math_str
from numeric_methods import (
    build_numeric_callable,
    numeric_integrate_with_error,
    numeric_scalar,
    validate_numeric_integrand,
)
from parser_utils import (
    evaluate_symbolic_function,
    has_complete_limits,
    parse_input_to_solving,
    x_sym,
)


SYMBOLIC_TIMEOUT_SECONDS = 8


class SymbolicTimeoutError(TimeoutError):
    pass


def _symbolic_worker(target, args, result_queue):
    try:
        result_queue.put(("ok", target(*args)))
    except Exception as exc:
        result_queue.put(("error", str(exc)))


def _run_symbolic_with_timeout(target, args, timeout=SYMBOLIC_TIMEOUT_SECONDS):
    if timeout is None or timeout <= 0:
        return target(*args)

    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()
    process = ctx.Process(target=_symbolic_worker, args=(target, args, result_queue))
    try:
        process.start()
        process.join(timeout)

        if process.is_alive():
            process.terminate()
            process.join(1)
            raise SymbolicTimeoutError(
                f"Symbolic integration exceeded {timeout} seconds. "
                "Try numerical integration or simplify the input."
            )

        try:
            status, payload = result_queue.get(timeout=1)
        except Empty:
            raise RuntimeError("Symbolic integration process exited without returning a result.")
    finally:
        if process.is_alive():
            process.terminate()
            process.join(1)
        result_queue.close()
        result_queue.join_thread()

    if status == "ok":
        return payload
    raise ValueError(payload)


@lru_cache(maxsize=384)
def _run_symbolic_cached(target, args, timeout):
    return _run_symbolic_with_timeout(target, args, timeout)


def _is_unevaluated_integral(expr):
    return isinstance(expr, Integral) or expr.has(Integral)


def _compute_tab1_result_direct(func_str, lower_text, upper_text):
    shown_func = func_str
    expr = evaluate_symbolic_function(func_str)

    if has_complete_limits(lower_text, upper_text):
        lower = parse_input_to_solving(lower_text)
        upper = parse_input_to_solving(upper_text)
        res = integrate(expr, (x_sym, lower, upper))
        info = format_result_for_display(res, symbolic_len_limit=50)
        raw_result = info["raw"]
        raw_type = info["type"]
        numeric_value = info["numeric"]
        numeric_err = None
        display_str = info["display"]

        if info["type"] == "unevaluated":
            l_float = float(lower.evalf())
            u_float = float(upper.evalf())
            f_num = build_numeric_callable(expr)
            validate_numeric_integrand(expr, f_num, l_float, u_float)
            numeric_value, numeric_err = numeric_integrate_with_error(
                lambda t: numeric_scalar(f_num, t),
                l_float,
                u_float
            )
            display_str = f"≈ {numeric_value:.3f}"

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

    return {
        "kind": "indefinite",
        "shown_func": shown_func,
        "display_str": pretty_math_str(ind),
        "raw_result": sstr(ind),
        "raw_type": "exact",
        "numeric_value": None,
        "closed_form": True,
    }


def compute_tab1_result(func_str, lower_text, upper_text, timeout=SYMBOLIC_TIMEOUT_SECONDS):
    return dict(_run_symbolic_cached(
        _compute_tab1_result_direct,
        (func_str, lower_text, upper_text),
        timeout,
    ))


def _compute_tab2_symbolic_result_direct(func_str, lower_text, upper_text):
    shown_func = func_str
    expr = evaluate_symbolic_function(func_str)

    if has_complete_limits(lower_text, upper_text):
        lower = parse_input_to_solving(lower_text)
        upper = parse_input_to_solving(upper_text)
        result = integrate(expr, (x_sym, lower, upper))
        if _is_unevaluated_integral(result):
            return {
                "kind": "symbolic_unevaluated",
                "lower": lower_text,
                "upper": upper_text,
                "shown_func": shown_func,
            }

        result = nsimplify(result)
        return {
            "kind": "symbolic_result",
            "formatted": pretty_math_str(result),
            "lower": lower_text,
            "upper": upper_text,
            "shown_func": shown_func,
        }

    result = integrate(expr, x_sym)
    if _is_unevaluated_integral(result):
        return {
            "kind": "symbolic_indef_unevaluated",
            "shown_func": shown_func,
        }

    return {
        "kind": "symbolic_indef",
        "formatted": pretty_math_str(result),
        "shown_func": shown_func,
    }


def compute_tab2_symbolic_result(func_str, lower_text, upper_text, timeout=SYMBOLIC_TIMEOUT_SECONDS):
    return dict(_run_symbolic_cached(
        _compute_tab2_symbolic_result_direct,
        (func_str, lower_text, upper_text),
        timeout,
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
    return {"type": "exact", "expr": res}


def compute_general_integral(func_str, lower_text, upper_text, timeout=SYMBOLIC_TIMEOUT_SECONDS):
    return dict(_run_symbolic_cached(
        _compute_general_integral_direct,
        (func_str, lower_text, upper_text),
        timeout,
    ))
