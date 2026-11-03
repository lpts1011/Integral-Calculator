from functools import lru_cache

import calengine as np
from scipy.integrate import quad
from solving.calculus.util import singularities
from solving.core.expr import Expr
from solving.utilities.lambdify import lambdify

from parser_utils import x_sym


FAST_METHODS = {
    "Trapezoidal",
    "Simpson",
    "Gaussian Quadrature",
}


def normalize_lambdified_output(raw_value, x_input):
    """
    Lambdified constant expressions return a scalar even for array input.
    Broadcast that scalar to the input shape so plotting and numerical rules
    can treat constant and non-constant functions uniformly.
    """
    x_arr = np.asarray(x_input, dtype=float)
    values = np.asarray(raw_value, dtype=float)
    if values.shape == ():
        if x_arr.shape == ():
            return values
        return np.full(x_arr.shape, float(values), dtype=float)
    if x_arr.shape != () and values.shape != x_arr.shape:
        values = np.broadcast_to(values, x_arr.shape)
    return values


def numeric_values(func, x_values):
    return np.asarray(func(x_values), dtype=float).reshape(-1)


def numeric_scalar(func, x_value) -> float:
    return float(np.asarray(func(x_value), dtype=float).reshape(-1)[0])


def _build_numeric_callable_uncached(expr: Expr):
    try:
        raw_func = lambdify(x_sym, expr, modules="numpy", cse=True, docstring_limit=0)
        def function(z):
            raw = raw_func(z)
            # Scalar quadrature nodes need no shape normalization.
            if isinstance(raw, float) and isinstance(z, float):
                return np.float64(raw)
            return normalize_lambdified_output(raw, z)
        function.expression = expr
        return function
    except Exception as e:
        raise ValueError(f"Failed to build numeric function: {e}")


@lru_cache(maxsize=256)
def _build_numeric_callable_cached(expr: Expr):
    return _build_numeric_callable_uncached(expr)


def build_numeric_callable(expr: Expr):
    try:
        hash(expr)
    except TypeError:
        return _build_numeric_callable_uncached(expr)
    return _build_numeric_callable_cached(expr)


def numeric_integrate_with_error(func, a, b):
    val, err = quad(func, a, b)
    return val, err


def _find_symbolic_singularities_uncached(expr, a, b):
    if not (np.isfinite(a) and np.isfinite(b)):
        return []
    lo, hi = sorted((float(a), float(b)))
    try:
        singular = singularities(expr, x_sym)
    except Exception:
        return []
    from solving import FiniteSet, Union, ImageSet, S
    import math
    def bounded_points(values):
        if isinstance(values, FiniteSet):
            return list(values)
        if isinstance(values, Union):
            return [point for part in values.args for point in bounded_points(part)]
        if isinstance(values, ImageSet) and values.base_set == S.Integers:
            variable = values.lamda.variables[0]
            formula = values.lamda.expr
            slope = formula.diff(variable)
            if slope.has(variable) or slope == 0:
                return []
            try:
                step = float(slope.evalf())
                offset = float(formula.subs(variable, 0).evalf())
                ends = sorted(((lo-offset)/step, (hi-offset)/step))
                first, last = math.ceil(ends[0]-1e-12), math.floor(ends[1]+1e-12)
                if last-first > 20000:
                    raise ValueError("Too many singularities in this interval; use a smaller interval.")
                return [formula.subs(variable, n) for n in range(first, last+1)]
            except (TypeError, OverflowError):
                return []
        return []  # An unresolved symbolic set must never be enumerated.
    points = []
    for point in bounded_points(singular):
        if point.is_real is False:
            continue
        value = float(point.evalf())
        if np.isfinite(value) and lo <= value <= hi:
            points.append(value)
    return sorted(set(points))


@lru_cache(maxsize=512)
def _find_symbolic_singularities_cached(expr, a, b):
    return tuple(_find_symbolic_singularities_uncached(expr, a, b))


def find_symbolic_singularities(expr, a, b):
    try:
        hash(expr)
    except TypeError:
        return _find_symbolic_singularities_uncached(expr, a, b)
    return list(_find_symbolic_singularities_cached(expr, a, b))


def validate_numeric_integrand(expr, func, a, b, *, allow_endpoint_singularities=False):
    singular_points = find_symbolic_singularities(expr, a, b)
    if allow_endpoint_singularities:
        singular_points = [v for v in singular_points if v != a and v != b]
    if singular_points:
        points = ", ".join(f"{p:.6g}" for p in singular_points[:5])
        raise ValueError(
            f"Function has a singularity inside the interval near x={points}. "
            "Split the interval or use a different method."
        )
    ok, xbad = ensure_finite_on_probe(func, a, b, exclude_endpoints=allow_endpoint_singularities)
    if not ok:
        if xbad is None:
            raise ValueError("Function is not finite on the interval.")
        raise ValueError(
            f"Function is not finite on the interval near x={xbad}. "
            "Split the interval or use a different method."
        )


def ensure_finite_on_probe(func, a, b, n_probe=101, *, exclude_endpoints=False):
    if not (np.isfinite(a) and np.isfinite(b)):
        return True, None
    xs = np.unique(np.concatenate([
        np.linspace(a, b, n_probe),
        np.array([a, b, 0.0, (a + b) / 2.0], dtype=float),
    ]))
    lo, hi = sorted((a, b))
    xs = xs[(xs > lo) & (xs < hi)] if exclude_endpoints else xs[(xs >= lo) & (xs <= hi)]
    try:
        vals = numeric_values(func, xs)
    except Exception:
        return False, None
    if not np.all(np.isfinite(vals)):
        bad_idx = np.where(~np.isfinite(vals))[0]
        xbad = xs[bad_idx[0]] if bad_idx.size > 0 else None
        return False, xbad
    return True, None


@lru_cache(maxsize=16)
def _legendre_nodes_weights(n):
    return np.polynomial.legendre.leggauss(n)


def gaussian_quadrature_fixed(f, a, b, n=64):
    """
    Fixed-order Gauss-Legendre quadrature.
    Replacement for deprecated scipy.integrate.quadrature.
    """
    if not (np.isfinite(a) and np.isfinite(b)):
        raise ValueError("Gaussian Quadrature requires finite limits.")
    if a == b:
        return 0.0
    xs, ws = _legendre_nodes_weights(int(n))
    ts = 0.5*(b - a)*xs + 0.5*(a + b)
    vals = numeric_values(f, ts)
    if not np.all(np.isfinite(vals)):
        raise ValueError("Function produced non-finite values in Gaussian Quadrature.")
    return 0.5*(b - a)*np.dot(ws, vals)


def compute_numerical_integral(integration_method, f_num, lower, upper, delta=None,
                               progress_callback=None, *, options=None, return_diagnostics=False):
    from integration_engine import integrate_numerically
    value, error, diagnostics = integrate_numerically(
        integration_method, f_num, lower, upper, delta,
        progress_callback=progress_callback, options=options,
    )
    if return_diagnostics:
        return value, error, diagnostics
    # Preserve the legacy two-item public API for existing callers.
    if integration_method in {"Rectangle", "Trapezoidal", "Simpson", "Simpson 3/8", "Romberg"}:
        error = None
    return value, error
