"""Build rendered result summaries and symbolic integration steps."""

from __future__ import annotations

import math
from typing import Any

from solving.integrals.integrals import Integral, integrate
from solving.printing.latex import latex
from solving.simplify.simplify import simplify

from parser_utils import evaluate_symbolic_function, parse_input_to_solving, x_sym


SYMBOLIC_RECORD_TYPES = {
    "definite",
    "indefinite",
    "symbolic",
    "symbolic_indefinite",
    "improper",
}


def _is_unavailable(record: dict[str, Any]) -> bool:
    raw_type = str(record.get("raw_type", "")).lower()
    combined = f"{record.get('raw', '')} {record.get('display', '')}".lower()
    return (
        raw_type == "unevaluated"
        or "integral(" in str(record.get("raw", "")).lower()
        or "no closed-form" in combined
        or "divergent" in combined
    )


def _parse_expression(value: Any):
    if hasattr(value, "free_symbols") and hasattr(value, "evalf"):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Empty expression")
    text = text.replace("π", "pi").replace("∞", "oo")
    if text.endswith("+ C"):
        text = text[:-3].rstrip()
    return evaluate_symbolic_function(text)


def _latex_value(value: Any) -> str:
    return latex(_parse_expression(value))


def _numeric_value(record: dict[str, Any]) -> float | None:
    record_type = str(record.get("type", ""))
    if record_type in ("indefinite", "symbolic_indefinite", "comparison"):
        return None

    candidates = [record.get("numeric_value")]
    if record_type in ("numerical", "improper", "definite", "symbolic"):
        candidates.append(record.get("raw"))

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            if hasattr(candidate, "evalf"):
                number = float(candidate.evalf())
            elif isinstance(candidate, (int, float)):
                number = float(candidate)
            else:
                number = float(_parse_expression(candidate).evalf())
            if math.isfinite(number):
                return number
        except Exception:
            continue
    return None


def _number_latex(value: float) -> str:
    return rf"\approx {value:.12g}"


def build_result_summary(record: dict[str, Any] | None) -> dict[str, Any]:
    """Return a cheap, serializable summary for the result workspace."""
    if not record:
        return {
            "has_result": False,
            "exact": {"text_key": "no_result"},
            "result": {"text_key": "no_result"},
            "elapsed": None,
            "steps": [],
            "steps_state": "hidden",
        }

    record_type = str(record.get("type", ""))
    unavailable = _is_unavailable(record)
    exact: dict[str, str]
    result: dict[str, str]

    if record_type in ("numerical", "comparison") or unavailable:
        exact = {"text_key": "not_available"}
    else:
        try:
            exact_latex = _latex_value(record.get("raw"))
            if record_type in ("indefinite", "symbolic_indefinite"):
                exact_latex += r" + C"
            exact = {"latex": exact_latex}
        except Exception:
            exact = {"text": str(record.get("raw") or record.get("display", ""))}

    numeric = _numeric_value(record)
    if numeric is not None:
        result = {"latex": _number_latex(numeric)}
    elif record_type in ("indefinite", "symbolic_indefinite") and "latex" in exact:
        result = {"latex": rf"F(x) = {exact['latex']}"}
    elif record_type == "comparison":
        result = {"text_key": "comparison_complete"}
    elif unavailable:
        result = {"text_key": "not_available"}
    else:
        result = dict(exact)

    elapsed = record.get("elapsed")
    try:
        elapsed = float(elapsed) if elapsed is not None else None
    except (TypeError, ValueError):
        elapsed = None

    return {
        "has_result": True,
        "exact": exact,
        "result": result,
        "elapsed": elapsed,
        "steps": [],
        "steps_state": "loading" if supports_symbolic_steps(record) else "hidden",
    }


def supports_symbolic_steps(record: dict[str, Any] | None) -> bool:
    if not record or str(record.get("type", "")) not in SYMBOLIC_RECORD_TYPES:
        return False
    return not _is_unavailable(record)


def _step(key: str, formula: str, detail_key: str | None = None) -> dict[str, str]:
    item = {"key": key, "latex": formula}
    if detail_key:
        item["detail_key"] = detail_key
    return item


def _definite_steps(record: dict[str, Any]) -> list[dict[str, str]]:
    func = record.get("resolved_func") or record.get("func", "")
    expr = evaluate_symbolic_function(str(func))
    lower = parse_input_to_solving(str(record.get("lower", "")))
    upper = parse_input_to_solving(str(record.get("upper", "")))
    antiderivative = integrate(expr, x_sym)
    if isinstance(antiderivative, Integral) or antiderivative.has(Integral):
        return []

    upper_value = simplify(antiderivative.subs(x_sym, upper))
    lower_value = simplify(antiderivative.subs(x_sym, lower))
    result = simplify(upper_value - lower_value)
    return [
        _step("step_setup", rf"\int_{{{latex(lower)}}}^{{{latex(upper)}}} {latex(expr)}\,dx"),
        _step("step_antiderivative", rf"F(x) = {latex(antiderivative)}"),
        _step(
            "step_bounds",
            rf"F\!\left({latex(upper)}\right)-F\!\left({latex(lower)}\right)",
            "fundamental_theorem",
        ),
        _step(
            "step_substitute",
            rf"{latex(upper_value)}-\left({latex(lower_value)}\right)",
        ),
        _step("step_simplify", rf"= {latex(result)}"),
    ]


def _indefinite_steps(record: dict[str, Any]) -> list[dict[str, str]]:
    func = record.get("resolved_func") or record.get("func", "")
    expr = evaluate_symbolic_function(str(func))
    antiderivative = integrate(expr, x_sym)
    if isinstance(antiderivative, Integral) or antiderivative.has(Integral):
        return []
    verification = simplify(antiderivative.diff(x_sym) - expr)
    return [
        _step("step_setup", rf"\int {latex(expr)}\,dx"),
        _step("step_antiderivative", rf"F(x) = {latex(antiderivative)} + C"),
        _step(
            "step_verify",
            rf"\frac{{d}}{{dx}}\left({latex(antiderivative)}\right)-{latex(expr)}={latex(verification)}",
        ),
    ]


def _improper_steps(record: dict[str, Any]) -> list[dict[str, str]]:
    func = record.get("resolved_func") or record.get("func", "")
    expr = evaluate_symbolic_function(str(func))
    lower = parse_input_to_solving(str(record.get("lower", "")))
    upper = parse_input_to_solving(str(record.get("upper", "")))
    result = _parse_expression(record.get("raw"))
    return [
        _step("step_setup", rf"\int_{{{latex(lower)}}}^{{{latex(upper)}}} {latex(expr)}\,dx"),
        _step("step_improper_limit", _improper_limit_latex(expr, lower, upper)),
        _step("step_simplify", rf"= {latex(result)}"),
    ]


def _improper_limit_latex(expr, lower, upper) -> str:
    lower_text = str(lower)
    upper_text = str(upper)
    integrand = latex(expr)
    if lower_text == "-oo" and upper_text == "oo":
        return (
            rf"\lim_{{a\to-\infty}}\int_a^0 {integrand}\,dx"
            rf"+\lim_{{b\to\infty}}\int_0^b {integrand}\,dx"
        )
    if lower_text == "-oo":
        return rf"\lim_{{a\to-\infty}}\int_a^{{{latex(upper)}}} {integrand}\,dx"
    return rf"\lim_{{b\to\infty}}\int_{{{latex(lower)}}}^b {integrand}\,dx"


def build_symbolic_steps(record: dict[str, Any]) -> list[dict[str, str]]:
    """Build human-readable formulas for records with a symbolic result."""
    if not supports_symbolic_steps(record):
        return []
    record_type = str(record.get("type", ""))
    try:
        if record_type in ("definite", "symbolic"):
            return _definite_steps(record)
        if record_type in ("indefinite", "symbolic_indefinite"):
            return _indefinite_steps(record)
        if record_type == "improper":
            return _improper_steps(record)
    except Exception:
        return []
    return []


__all__ = [
    "build_result_summary",
    "build_symbolic_steps",
    "supports_symbolic_steps",
]
