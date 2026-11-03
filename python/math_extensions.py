from scipy.integrate import quad
from solving.core.function import diff
from solving.core.numbers import Rational, pi
from solving.core.relational import Eq
from solving.core.symbol import symbols
from solving.functions import sqrt
from solving.integrals.integrals import Integral, integrate
from solving.parsing.solving_parser import parse_expr
from solving.simplify.simplify import simplify
from solving.solvers.solvers import solve
from solving.utilities.lambdify import lambdify

from formatting import pretty_math_str
from numeric_methods import (
    build_numeric_callable,
    numeric_scalar,
    validate_numeric_integrand,
)
from parser_utils import (
    PARSER_TRANSFORMATIONS,
    SAFE_GLOBALS,
    SAFE_LOCALS,
    evaluate_symbolic_function,
    parse_input_to_solving,
    x_sym,
)
from symbolic_methods import compute_general_integral


theta_sym = symbols("theta")
u_sym = symbols("u")


def _parse_with_symbols(expr_text, symbols_by_name):
    local_dict = dict(SAFE_LOCALS)
    local_dict.update(symbols_by_name)
    expr = parse_expr(
        expr_text.strip(),
        local_dict=local_dict,
        global_dict=SAFE_GLOBALS,
        transformations=PARSER_TRANSFORMATIONS,
        evaluate=True,
    )
    allowed_symbols = set(symbols_by_name.values())
    unknown = expr.free_symbols - allowed_symbols
    if unknown:
        names = ", ".join(sorted(str(symbol) for symbol in unknown))
        raise ValueError(f"Unknown variables: {names}")
    return expr




def compute_polar_area(radius_expr, lower_text, upper_text):
    radius = _parse_with_symbols(radius_expr, {"theta": theta_sym, "t": theta_sym})
    lower = parse_input_to_solving(lower_text)
    upper = parse_input_to_solving(upper_text)
    area_expr = Rational(1, 2) * radius**2
    exact = integrate(area_expr, (theta_sym, lower, upper))
    numeric = float(exact.evalf())
    return {
        "integrand": pretty_math_str(area_expr),
        "exact": pretty_math_str(simplify(exact)),
        "numeric": numeric,
    }






def substitution_integral_helper(func_str, substitution_text):
    expr = evaluate_symbolic_function(func_str)
    if "=" in substitution_text:
        _, rhs = substitution_text.split("=", 1)
    else:
        rhs = substitution_text
    u_expr = evaluate_symbolic_function(rhs)
    du_dx = diff(u_expr, x_sym)
    solutions = solve(Eq(u_sym, u_expr), x_sym)
    if not solutions:
        raise ValueError("Could not solve the substitution for x.")
    x_of_u = solutions[0]
    transformed = simplify(expr.subs(x_sym, x_of_u) * diff(x_of_u, u_sym))
    return {
        "u": pretty_math_str(u_expr),
        "du_dx": pretty_math_str(du_dx),
        "x_of_u": pretty_math_str(x_of_u),
        "transformed_integrand": pretty_math_str(transformed),
    }


def integration_by_parts_helper(u_text, dv_text):
    u_expr = evaluate_symbolic_function(u_text)
    dv_expr = evaluate_symbolic_function(dv_text)
    du_expr = diff(u_expr, x_sym)
    v_expr = integrate(dv_expr, x_sym)
    remaining = simplify(v_expr * du_expr)
    formula_rhs = simplify(u_expr * v_expr - integrate(remaining, x_sym))
    return {
        "u": pretty_math_str(u_expr),
        "du": pretty_math_str(du_expr),
        "dv": pretty_math_str(dv_expr),
        "v": pretty_math_str(v_expr),
        "remaining_integrand": pretty_math_str(remaining),
        "result": pretty_math_str(formula_rhs),
    }


def compute_area_breakdown(func_str, lower_text, upper_text):
    expr = evaluate_symbolic_function(func_str)
    lower = float(parse_input_to_solving(lower_text).evalf())
    upper = float(parse_input_to_solving(upper_text).evalf())
    f_num = build_numeric_callable(expr)
    validate_numeric_integrand(expr, f_num, lower, upper)
    signed, signed_error = quad(lambda t: numeric_scalar(f_num, t), lower, upper)
    absolute, absolute_error = quad(lambda t: abs(numeric_scalar(f_num, t)), lower, upper)
    positive = (absolute+signed)/2
    negative_signed = (signed-absolute)/2
    return {
        "signed": signed,
        "absolute": absolute,
        "positive_area": positive,
        "negative_area": abs(negative_signed),
        "negative_signed": negative_signed,
        "signed_error": signed_error,
        "absolute_error": absolute_error,
    }


def compute_arc_length(func_str, lower_text, upper_text):
    expr = evaluate_symbolic_function(func_str)
    lower = parse_input_to_solving(lower_text)
    upper = parse_input_to_solving(upper_text)
    integrand = sqrt(1 + diff(expr, x_sym) ** 2)
    exact = integrate(integrand, (x_sym, lower, upper))
    if isinstance(exact, Integral) or exact.has(Integral):
        f_num = lambdify(x_sym, integrand, modules="numpy")
        numeric, error = quad(lambda t: float(f_num(t)), float(lower.evalf()), float(upper.evalf()))
        exact_text = "no closed form"
    else:
        numeric = float(exact.evalf())
        error = None
        exact_text = pretty_math_str(simplify(exact))
    return {
        "integrand": pretty_math_str(integrand),
        "exact": exact_text,
        "numeric": numeric,
        "error": error,
    }


def compute_revolution_volume(func_str, lower_text, upper_text, axis="x"):
    expr = evaluate_symbolic_function(func_str)
    lower = parse_input_to_solving(lower_text)
    upper = parse_input_to_solving(upper_text)
    axis = axis.strip().lower()
    if axis == "x":
        integrand = pi * expr**2
    elif axis == "y":
        integrand = 2 * pi * x_sym * expr
    else:
        raise ValueError("Axis must be x or y.")
    exact = integrate(integrand, (x_sym, lower, upper))
    return {
        "integrand": pretty_math_str(integrand),
        "exact": pretty_math_str(simplify(exact)),
        "numeric": float(exact.evalf()),
    }
















def verify_antiderivative(func_str, antiderivative_str):
    expr = evaluate_symbolic_function(func_str)
    antiderivative = evaluate_symbolic_function(antiderivative_str)
    difference = simplify(diff(antiderivative, x_sym) - expr)
    return {
        "ok": difference == 0,
        "difference": pretty_math_str(difference),
    }


def convergence_report(func_str, lower_text, upper_text, timeout=4):
    result = compute_general_integral(func_str, lower_text, upper_text, timeout=timeout)
    if result["type"] == "exact":
        status = "convergent"
        summary = f"Convergent. Exact value: {pretty_math_str(result['expr'])}"
    elif result["type"] == "divergent":
        status = "divergent"
        summary = f"Divergent. Solving returned: {pretty_math_str(result['expr'])}"
    else:
        status = "unknown"
        summary = "Unable to decide convergence symbolically."
    return {
        "status": status,
        "summary": summary,
        "raw": result.get("expr"),
    }










def compute_geometry_bundle(function, lower, upper, axis):
    return compute_arc_length(function,lower,upper), compute_revolution_volume(function,lower,upper,axis)
