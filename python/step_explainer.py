from solving.integrals.integrals import Integral, integrate
from solving.printing.str import sstr
from solving.simplify.simplify import simplify

from formatting import pretty_math_str
from math_extensions import convergence_report, verify_antiderivative
from parser_utils import evaluate_symbolic_function, parse_input_to_solving, x_sym


STEPS_UNAVAILABLE_MESSAGE = "Antiderivative not found, N/A"


def build_steps_for_record(record):
    if not record:
        return "No calculation result is available. Run a calculation first."

    record_type = record.get("type", "")
    if record_type in ("definite", "symbolic"):
        return _definite_steps(record)
    if record_type in ("indefinite", "symbolic_indefinite"):
        return _indefinite_steps(record)
    if record_type == "numerical":
        return _numerical_steps(record)
    if record_type == "improper":
        return _improper_steps(record)
    if record_type == "comparison":
        return _comparison_steps(record)
    return _generic_steps(record)


def _steps_not_available(record):
    raw_type = str(record.get("raw_type", "")).lower()
    raw = str(record.get("raw", ""))
    display = str(record.get("display", ""))
    combined = f"{raw} {display}".lower()
    return (
        raw_type == "unevaluated"
        or "integral(" in raw.lower()
        or "no closed-form" in combined
    )


def _definite_steps(record):
    if _steps_not_available(record):
        return STEPS_UNAVAILABLE_MESSAGE
    func = record.get("resolved_func") or record.get("func", "")
    lower = record.get("lower", "")
    upper = record.get("upper", "")
    lines = [
        "Definite Integral Steps",
        f"1. Function: f(x) = {record.get('shown_func') or record.get('func')}",
        f"2. Interval: [{lower}, {upper}]",
    ]
    try:
        expr = evaluate_symbolic_function(func)
        lower_expr = parse_input_to_solving(str(lower))
        upper_expr = parse_input_to_solving(str(upper))
        antiderivative = integrate(expr, x_sym)
        if isinstance(antiderivative, Integral) or antiderivative.has(Integral):
            return STEPS_UNAVAILABLE_MESSAGE
        upper_value = simplify(antiderivative.subs(x_sym, upper_expr))
        lower_value = simplify(antiderivative.subs(x_sym, lower_expr))
        result = simplify(upper_value - lower_value)
        lines.extend([
            f"3. Antiderivative: F(x) = {pretty_math_str(antiderivative)}",
            f"4. Substitute upper limit: F({upper}) = {pretty_math_str(upper_value)}",
            f"5. Substitute lower limit: F({lower}) = {pretty_math_str(lower_value)}",
            f"6. Difference: F({upper}) - F({lower}) = {pretty_math_str(result)}",
        ])
    except Exception:
        return STEPS_UNAVAILABLE_MESSAGE
    lines.append(f"Final displayed result: {record.get('raw', record.get('display', ''))}")
    return "\n".join(lines)


def _indefinite_steps(record):
    if _steps_not_available(record):
        return STEPS_UNAVAILABLE_MESSAGE
    func = record.get("resolved_func") or record.get("func", "")
    lines = [
        "Indefinite Integral Steps",
        f"1. Function: f(x) = {record.get('shown_func') or record.get('func')}",
    ]
    try:
        expr = evaluate_symbolic_function(func)
        antiderivative = integrate(expr, x_sym)
        if isinstance(antiderivative, Integral) or antiderivative.has(Integral):
            return STEPS_UNAVAILABLE_MESSAGE
        verification = verify_antiderivative(func, sstr(antiderivative))
        lines.extend([
            f"2. Antiderivative: F(x) = {pretty_math_str(antiderivative)} + C",
            "3. Differentiate to verify:",
            f"   d/dx F(x) - f(x) = {verification['difference']}",
            f"4. Verification: {'passed' if verification['ok'] else 'needs review'}",
        ])
    except Exception:
        return STEPS_UNAVAILABLE_MESSAGE
    return "\n".join(lines)


def _numerical_steps(record):
    lines = [
        "Numerical Integration Summary",
        f"1. Function: f(x) = {record.get('shown_func') or record.get('func')}",
        f"2. Interval: [{record.get('lower')}, {record.get('upper')}]",
        f"3. Method: {record.get('method')}",
        f"4. Approximation: {record.get('raw')}",
    ]
    if record.get("error") is not None:
        lines.append(f"5. Error estimate: {record['error']}")
    if record.get("segments"):
        lines.append(f"6. Segments used: {len(record['segments'])}")
    return "\n".join(lines)


def _improper_steps(record):
    lines = [
        "Improper Integral / Convergence Steps",
        f"1. Function: f(x) = {record.get('shown_func') or record.get('func')}",
        f"2. Interval: [{record.get('lower')}, {record.get('upper')}]",
        "3. Convergence check:",
    ]
    try:
        report = convergence_report(
            record.get("resolved_func") or record.get("func", ""),
            str(record.get("lower", "")),
            str(record.get("upper", "")),
        )
        lines.append(f"   {report['summary']}")
    except Exception as exc:
        lines.append(f"   Unable to build convergence explanation: {exc}")
    lines.append(f"Final displayed result: {record.get('raw', record.get('display', ''))}")
    return "\n".join(lines)


def _comparison_steps(record):
    rows = record.get("raw") or []
    lines = [
        "Numerical Method Comparison Summary",
        f"1. Function: f(x) = {record.get('shown_func') or record.get('func')}",
        f"2. Interval: [{record.get('lower')}, {record.get('upper')}]",
        "3. Method results:",
    ]
    for row in rows:
        lines.append(
            f"   - {row.get('method')}: result={row.get('result')}, "
            f"error={row.get('error')}, status={row.get('status')}"
        )
    return "\n".join(lines)


def _generic_steps(record):
    return "\n".join([
        "Calculation Summary",
        record.get("display", ""),
        f"Raw result: {record.get('raw', '')}",
    ])
