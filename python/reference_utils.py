"""Independent references; never compare a solver against itself."""
import math
import mpmath
from parser_utils import evaluate_symbolic_function, x_sym
from numeric_methods import find_symbolic_singularities
from integration_engine import structural_points, oscillatory_factor

def independent_reference(expression, lower, upper):
    from symbolic_methods import compute_tab1_result
    try:
        record = compute_tab1_result(expression, str(lower), str(upper), timeout=3)
        if record["raw_type"] == "exact" and record["numeric_value"] is not None:
            value = float(record["numeric_value"])
            if math.isfinite(value):
                return value, "symbolic exact reference"
    except Exception:
        pass
    expr = evaluate_symbolic_function(expression)
    factor = oscillatory_factor(expr)
    if factor and abs(factor[2]*(upper-lower)) > 500:
        return None, "independent reference unavailable within budget"
    if find_symbolic_singularities(expr, lower, upper):
        return None, "singular reference requires separate convergence analysis"
    try:
        from solving.utilities.lambdify import lambdify
        function = lambdify(x_sym, expr, modules="mpmath", docstring_limit=0)
        lo, hi = sorted((lower, upper))
        points = [lo, *structural_points(expr,lo,hi), hi]
        values = []
        for precision in (40,60):
            with mpmath.workdps(precision):
                values.append(float(mpmath.quad(function,points)))
        if math.isfinite(values[-1]) and abs(values[1]-values[0]) <= 1e-12*max(1.,abs(values[-1])):
            return (1 if upper >= lower else -1)*values[-1], "mpmath 40/60 digit agreement (estimated reference)"
    except Exception:
        pass
    return None, "independent reference unavailable"
