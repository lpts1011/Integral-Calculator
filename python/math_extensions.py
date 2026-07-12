from scipy.integrate import quad
from solving.calculus.util import continuous_domain, singularities as find_singularities
from solving.core.function import Derivative, Function, diff, expand
from solving.core.numbers import Rational, pi
from solving.core.relational import Eq
from solving.core.singleton import S
from solving.core.symbol import symbols
from solving.functions import sqrt
from solving.integrals.integrals import Integral, integrate
from solving.integrals.transforms import inverse_laplace_transform, laplace_transform
from solving.parsing.solving_parser import parse_expr
from solving.printing.str import sstr
from solving.series.fourier import fourier_series
from solving.series.series import series as build_series
from solving.sets.sets import Interval
from solving.simplify.simplify import simplify
from solving.solvers.ode.ode import dsolve
from solving.solvers.solvers import solve
from solving.solvers.solveset import solveset
from solving.utilities.lambdify import lambdify

from formatting import pretty_math_str
from interval_utils import find_piecewise_breakpoints
from numeric_methods import (
    build_numeric_callable,
    compute_numerical_integral,
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
from parameter_utils import evaluate_function_with_parameters
from symbolic_methods import compute_general_integral


theta_sym = symbols("theta")
r_sym = symbols("r")
y_sym = symbols("y")
z_sym = symbols("z")
s_sym = symbols("s")
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


def _parse_limit(expr_text, symbols_by_name=None):
    symbols_by_name = symbols_by_name or {}
    if symbols_by_name:
        return _parse_with_symbols(expr_text, symbols_by_name)
    return parse_input_to_solving(expr_text)


def _real_values_in_interval(candidates, lower, upper, max_items=12):
    values = []
    lo, hi = sorted((float(lower), float(upper)))
    for candidate in candidates:
        try:
            if candidate.is_real is False:
                continue
            value = float(candidate.evalf())
        except Exception:
            continue
        if lo <= value <= hi and all(abs(value - existing) > 1e-8 for existing in values):
            values.append(value)
        if len(values) >= max_items:
            break
    return sorted(values)


def _format_float_list(values):
    return [f"{value:.8g}" for value in values]


def _parse_value_list(values_text):
    values = []
    for item in values_text.replace(";", ",").split(","):
        text = item.strip()
        if text:
            values.append(parse_input_to_solving(text))
    if not values:
        raise ValueError("Enter at least one parameter value.")
    return values


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


def compute_taylor_expansion(func_str, point_text="0", order_text="5"):
    expr = evaluate_symbolic_function(func_str)
    point = parse_input_to_solving(point_text)
    order = int(parse_input_to_solving(order_text))
    if order < 0:
        raise ValueError("Taylor order must be non-negative.")
    series = build_series(expr, x_sym, point, order + 1)
    polynomial = expand(series.removeO())
    return {
        "point": pretty_math_str(point),
        "order": order,
        "polynomial": pretty_math_str(polynomial),
        "series": pretty_math_str(series),
    }


def build_convergence_table(func_str, lower_text, upper_text, method="Trapezoidal", intervals_text="20,50,100,200"):
    expr = evaluate_symbolic_function(func_str)
    lower = float(parse_input_to_solving(lower_text).evalf())
    upper = float(parse_input_to_solving(upper_text).evalf())
    f_num = build_numeric_callable(expr)
    validate_numeric_integrand(expr, f_num, lower, upper)
    reference, reference_error = quad(lambda t: numeric_scalar(f_num, t), lower, upper)
    rows = []
    for item in intervals_text.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        n = max(1, int(parse_input_to_solving(item)))
        delta = abs(upper - lower) / n
        value, estimate = compute_numerical_integral(method, f_num, lower, upper, delta=delta)
        rows.append({
            "n": n,
            "delta": delta,
            "value": value,
            "absolute_error": abs(value - reference),
            "estimate": estimate,
        })
    if not rows:
        raise ValueError("Enter at least one interval count.")
    return {
        "method": method,
        "reference": reference,
        "reference_error": reference_error,
        "rows": rows,
    }


def analyze_singularity_and_breakpoints(func_str, lower_text, upper_text):
    expr = evaluate_symbolic_function(func_str)
    lower = float(parse_input_to_solving(lower_text).evalf())
    upper = float(parse_input_to_solving(upper_text).evalf())
    singularities = []
    try:
        singularities = _real_values_in_interval(
            find_singularities(expr, x_sym),
            lower,
            upper,
        )
    except Exception:
        singularities = []
    breakpoints = find_piecewise_breakpoints(expr, lower, upper)
    split_points = sorted({*singularities, *breakpoints})
    return {
        "singularities": singularities,
        "breakpoints": breakpoints,
        "split_points": split_points,
        "summary": (
            f"Singularities: {_format_float_list(singularities) or ['none']}\n"
            f"Piecewise breakpoints: {_format_float_list(breakpoints) or ['none']}\n"
            f"Suggested split points: {_format_float_list(split_points) or ['none']}"
        ),
    }


def analyze_function_properties(func_str, lower_text="-5", upper_text="5"):
    expr = evaluate_symbolic_function(func_str)
    lower = float(parse_input_to_solving(lower_text).evalf())
    upper = float(parse_input_to_solving(upper_text).evalf())
    derivative = diff(expr, x_sym)
    second_derivative = diff(expr, x_sym, 2)
    roots = _solve_real_points(expr, lower, upper)
    critical_points = _solve_real_points(derivative, lower, upper)
    inflection_points = _solve_real_points(second_derivative, lower, upper)
    try:
        domain = continuous_domain(expr, x_sym, S.Reals)
    except Exception:
        domain = "unknown"
    return {
        "domain": str(domain),
        "derivative": pretty_math_str(derivative),
        "second_derivative": pretty_math_str(second_derivative),
        "roots": roots,
        "critical_points": critical_points,
        "inflection_points": inflection_points,
    }


def _solve_real_points(expr, lower, upper):
    candidates = []
    try:
        solution_set = solveset(expr, x_sym, domain=Interval(lower, upper))
        if solution_set.is_FiniteSet:
            candidates = list(solution_set)
    except Exception:
        candidates = []
    if not candidates:
        try:
            candidates = solve(expr, x_sym)
        except Exception:
            candidates = []
    return _real_values_in_interval(candidates, lower, upper)


def compute_average_value(func_str, lower_text, upper_text):
    expr = evaluate_symbolic_function(func_str)
    lower = parse_input_to_solving(lower_text)
    upper = parse_input_to_solving(upper_text)
    if lower == upper:
        raise ValueError("Average value requires different finite limits.")
    integral = integrate(expr, (x_sym, lower, upper))
    average = simplify(integral / (upper - lower))
    return {
        "integral": pretty_math_str(integral),
        "average": pretty_math_str(average),
        "numeric": float(average.evalf()),
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
    positive, _ = quad(lambda t: max(numeric_scalar(f_num, t), 0.0), lower, upper)
    negative_signed, _ = quad(lambda t: min(numeric_scalar(f_num, t), 0.0), lower, upper)
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


def compute_fourier_series(func_str, period_text="2*pi", terms_text="5"):
    expr = evaluate_symbolic_function(func_str)
    period = parse_input_to_solving(period_text)
    terms = int(parse_input_to_solving(terms_text))
    if terms <= 0:
        raise ValueError("Number of Fourier terms must be positive.")
    half_period = period / 2
    series = fourier_series(expr, (x_sym, -half_period, half_period)).truncate(terms)
    return {
        "series": pretty_math_str(series),
        "raw": sstr(series),
    }


def compute_laplace_transform(func_str):
    expr = evaluate_symbolic_function(func_str)
    transform = laplace_transform(expr, x_sym, s_sym, noconds=True)
    inverse = inverse_laplace_transform(transform, s_sym, x_sym)
    return {
        "transform": pretty_math_str(transform),
        "inverse": pretty_math_str(inverse),
    }


def solve_simple_ode(ode_text):
    y_func = Function("y")
    normalized = _normalize_ode_text(ode_text)
    local_dict = dict(SAFE_LOCALS)
    local_dict.update({"x": x_sym, "y": y_func, "Derivative": Derivative})
    if "=" in normalized:
        lhs_text, rhs_text = normalized.split("=", 1)
        lhs = parse_expr(
            lhs_text.strip(),
            local_dict=local_dict,
            global_dict=SAFE_GLOBALS,
            transformations=PARSER_TRANSFORMATIONS,
        )
        rhs = parse_expr(
            rhs_text.strip(),
            local_dict=local_dict,
            global_dict=SAFE_GLOBALS,
            transformations=PARSER_TRANSFORMATIONS,
        )
        equation = Eq(lhs, rhs)
    else:
        lhs = parse_expr(
            normalized.strip(),
            local_dict=local_dict,
            global_dict=SAFE_GLOBALS,
            transformations=PARSER_TRANSFORMATIONS,
        )
        equation = Eq(lhs, 0)
    solution = dsolve(equation)
    return {
        "equation": str(equation),
        "solution": pretty_math_str(solution),
    }


def _normalize_ode_text(ode_text):
    text = ode_text.strip()
    text = text.replace("y''", "Derivative(y(x), (x, 2))")
    text = text.replace("y'", "Derivative(y(x), x)")
    return _replace_plain_y(text)


def _replace_plain_y(text):
    import re

    return re.sub(r"\by\b(?!\s*\()", "y(x)", text)


def build_piecewise_expression(pieces):
    cleaned = []
    for expr_text, condition_text in pieces:
        expr = expr_text.strip()
        condition = condition_text.strip()
        if not expr:
            continue
        cleaned.append((expr, condition or "True"))
    if not cleaned:
        raise ValueError("Add at least one piece.")
    if all(condition.lower() != "true" for _, condition in cleaned):
        cleaned.append((cleaned[-1][0], "True"))
    return "Piecewise(" + ", ".join(f"({expr}, {condition})" for expr, condition in cleaned) + ")"


def parameter_assignment(parameter_name, value):
    parameter = parameter_name.strip()
    if not parameter:
        raise ValueError("Parameter name is required.")
    return f"{parameter}={float(value):.6g}"


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


def build_error_profile(func_str, lower_text, upper_text):
    expr = evaluate_symbolic_function(func_str)
    lower = float(parse_input_to_solving(lower_text).evalf())
    upper = float(parse_input_to_solving(upper_text).evalf())
    f_num = build_numeric_callable(expr)
    validate_numeric_integrand(expr, f_num, lower, upper)
    reference, reference_error = quad(lambda t: numeric_scalar(f_num, t), lower, upper)
    rows = []
    for method in (
        "Rectangle",
        "Trapezoidal",
        "Simpson",
        "Gaussian Quadrature",
        "Adaptive Simpson",
    ):
        value, estimate = compute_numerical_integral(method, f_num, lower, upper)
        rows.append({
            "method": method,
            "value": value,
            "absolute_error": abs(value - reference),
            "estimate": estimate,
        })
    return {
        "reference": reference,
        "reference_error": reference_error,
        "rows": rows,
    }


def compute_double_integral(func_str, x_lower_text, x_upper_text, y_lower_text, y_upper_text):
    expr = _parse_with_symbols(func_str, {"x": x_sym, "y": y_sym})
    x_lower = parse_input_to_solving(x_lower_text)
    x_upper = parse_input_to_solving(x_upper_text)
    y_lower = parse_input_to_solving(y_lower_text)
    y_upper = parse_input_to_solving(y_upper_text)
    exact = integrate(expr, (y_sym, y_lower, y_upper), (x_sym, x_lower, x_upper))
    return {
        "exact": pretty_math_str(simplify(exact)),
        "numeric": float(exact.evalf()),
    }


def compute_variable_double_integral(func_str, x_lower_text, x_upper_text, y_lower_text, y_upper_text):
    expr = _parse_with_symbols(func_str, {"x": x_sym, "y": y_sym})
    x_lower = parse_input_to_solving(x_lower_text)
    x_upper = parse_input_to_solving(x_upper_text)
    y_lower = _parse_limit(y_lower_text, {"x": x_sym})
    y_upper = _parse_limit(y_upper_text, {"x": x_sym})
    exact = integrate(expr, (y_sym, y_lower, y_upper), (x_sym, x_lower, x_upper))
    return {
        "exact": pretty_math_str(simplify(exact)),
        "numeric": float(exact.evalf()),
    }


def compute_polar_double_integral(func_str, r_lower_text, r_upper_text, theta_lower_text, theta_upper_text):
    expr = _parse_with_symbols(func_str, {"r": r_sym, "theta": theta_sym, "t": theta_sym})
    r_lower = _parse_limit(r_lower_text, {"theta": theta_sym, "t": theta_sym})
    r_upper = _parse_limit(r_upper_text, {"theta": theta_sym, "t": theta_sym})
    theta_lower = parse_input_to_solving(theta_lower_text)
    theta_upper = parse_input_to_solving(theta_upper_text)
    exact = integrate(expr * r_sym, (r_sym, r_lower, r_upper), (theta_sym, theta_lower, theta_upper))
    return {
        "exact": pretty_math_str(simplify(exact)),
        "numeric": float(exact.evalf()),
    }


def compute_triple_integral(
    func_str,
    x_lower_text,
    x_upper_text,
    y_lower_text,
    y_upper_text,
    z_lower_text,
    z_upper_text,
):
    expr = _parse_with_symbols(func_str, {"x": x_sym, "y": y_sym, "z": z_sym})
    x_lower = parse_input_to_solving(x_lower_text)
    x_upper = parse_input_to_solving(x_upper_text)
    y_lower = parse_input_to_solving(y_lower_text)
    y_upper = parse_input_to_solving(y_upper_text)
    z_lower = parse_input_to_solving(z_lower_text)
    z_upper = parse_input_to_solving(z_upper_text)
    exact = integrate(
        expr,
        (z_sym, z_lower, z_upper),
        (y_sym, y_lower, y_upper),
        (x_sym, x_lower, x_upper),
    )
    return {
        "exact": pretty_math_str(simplify(exact)),
        "numeric": float(exact.evalf()),
    }


def compute_parameter_sensitivity(func_str, parameter_name, values_text, lower_text, upper_text):
    parameter = parameter_name.strip()
    if not parameter:
        raise ValueError("Parameter name is required.")
    values = _parse_value_list(values_text)
    rows = []
    for value in values:
        expr = evaluate_function_with_parameters(func_str, f"{parameter}={sstr(value)}")
        lower = parse_input_to_solving(lower_text)
        upper = parse_input_to_solving(upper_text)
        integral = integrate(expr, (x_sym, lower, upper))
        rows.append({
            "parameter": pretty_math_str(value),
            "integral": pretty_math_str(simplify(integral)),
            "numeric": float(integral.evalf()),
        })
    return rows
