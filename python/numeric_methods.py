from functools import lru_cache

import calengine as np
from scipy.integrate import quad, simpson
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
        raw_func = lambdify(x_sym, expr, modules="numpy")
        return lambda z: normalize_lambdified_output(raw_func(z), z)
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
    points = []
    try:
        for point in singular:
            if point.is_real is False:
                continue
            value = float(point.evalf())
            if np.isfinite(value) and lo <= value <= hi:
                points.append(value)
    except TypeError:
        return []
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


def validate_numeric_integrand(expr, func, a, b):
    singular_points = find_symbolic_singularities(expr, a, b)
    if singular_points:
        points = ", ".join(f"{p:.6g}" for p in singular_points[:5])
        raise ValueError(
            f"Function has a singularity inside the interval near x={points}. "
            "Split the interval or use a different method."
        )
    ok, xbad = ensure_finite_on_probe(func, a, b)
    if not ok:
        if xbad is None:
            raise ValueError("Function is not finite on the interval.")
        raise ValueError(
            f"Function is not finite on the interval near x={xbad}. "
            "Split the interval or use a different method."
        )


def ensure_finite_on_probe(func, a, b, n_probe=101):
    if not (np.isfinite(a) and np.isfinite(b)):
        return True, None
    xs = np.unique(np.concatenate([
        np.linspace(a, b, n_probe),
        np.array([a, b, 0.0, (a + b) / 2.0], dtype=float),
    ]))
    lo, hi = sorted((a, b))
    xs = xs[(xs >= lo) & (xs <= hi)]
    try:
        vals = numeric_values(func, xs)
    except Exception:
        return False, None
    if not np.all(np.isfinite(vals)):
        bad_idx = np.where(~np.isfinite(vals))[0]
        xbad = xs[bad_idx[0]] if bad_idx.size > 0 else None
        return False, xbad
    return True, None


def composite_simpson_38(func, a, b, n_intervals=300):
    if not np.isfinite(a) or not np.isfinite(b):
        raise ValueError("Simpson 3/8 requires finite limits.")
    if a == b:
        return 0.0
    n = int(max(3, n_intervals))
    if n % 3 != 0:
        n += (3 - n % 3)
    x = np.linspace(a, b, n + 1)
    y = numeric_values(func, x)
    if not np.all(np.isfinite(y)):
        raise ValueError("Function produced non-finite values in Simpson 3/8.")
    h = (b - a) / n
    interior_sum = np.sum(y[1:-1])
    multiple_of_three_sum = np.sum(y[3:n:3])
    S = y[0] + y[-1] + 3 * interior_sum - multiple_of_three_sum
    return 3 * h / 8 * S


def romberg_custom(func, a, b, max_level=8, tol=1e-8):
    if not (np.isfinite(a) and np.isfinite(b)):
        raise ValueError("Romberg requires finite limits.")
    if a == b:
        return 0.0
    R = np.zeros((max_level+1, max_level+1), dtype=float)
    fa = numeric_scalar(func, a)
    fb = numeric_scalar(func, b)
    if not (np.isfinite(fa) and np.isfinite(fb)):
        raise ValueError("Function non-finite at endpoints for Romberg.")
    h = (b - a)
    R[0, 0] = 0.5 * h * (fa + fb)
    for k in range(1, max_level+1):
        n_intervals = 2**(k-1)
        h *= 0.5
        xs_mid = a + h * (np.arange(1, 2*n_intervals, 2))
        fm = numeric_values(func, xs_mid)
        if not np.all(np.isfinite(fm)):
            raise ValueError("Function produced non-finite values in Romberg refinement.")
        R[k, 0] = 0.5 * R[k-1, 0] + h * np.sum(fm)
        for m in range(1, k+1):
            R[k, m] = R[k, m-1] + (R[k, m-1] - R[k-1, m-1]) / (4**m - 1)
        if abs(R[k, k] - R[k-1, k-1]) < tol * max(1.0, abs(R[k, k])):
            return R[k, k]
    return R[max_level, max_level]


def monte_carlo_stratified(func, a, b, n_samples=5000, n_strata=50, rng=None):
    if not (np.isfinite(a) and np.isfinite(b)):
        raise ValueError("Monte Carlo requires finite limits.")
    if a == b:
        return 0.0
    rng = np.random.default_rng() if rng is None else rng
    n_strata = max(1, int(n_strata))
    n_samples = max(n_strata, int(n_samples))
    per = n_samples // n_strata
    if per == 0:
        per = 1
        n_strata = n_samples
    width = (b - a) / n_strata
    est = 0.0
    for s in range(n_strata):
        left = a + s * width
        u = rng.random(per)
        xs = left + u * width
        vals = numeric_values(func, xs)
        if not np.all(np.isfinite(vals)):
            raise ValueError("Function produced non-finite values in Monte Carlo.")
        est += width * np.mean(vals)
    return est


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


def compute_numerical_integral(integration_method, f_num, lower, upper, delta=None, progress_callback=None):
    progress_callback = progress_callback or (lambda value: None)
    error_estimate = None

    if integration_method == "Monte Carlo":
        n_samples = (8000 if delta is None
                     else max(4000, int(abs(upper-lower)/max(delta, 1e-6))*20))
        n_strata = min(200, max(20, int(np.sqrt(n_samples))))
        rng = np.random.default_rng()
        chunks = 10
        part_estimates = []
        for k in range(chunks):
            est_k = monte_carlo_stratified(
                f_num, lower, upper,
                n_samples=max(1, n_samples//chunks),
                n_strata=max(1, n_strata//chunks),
                rng=rng,
            )
            part_estimates.append(est_k)
            progress_callback(int((k+1)*100/chunks))
        result = float(np.mean(part_estimates))
        if len(part_estimates) > 1:
            error_estimate = float(np.std(part_estimates, ddof=1) / np.sqrt(len(part_estimates)))

    elif integration_method == "Rectangle":
        n = 1000 if delta is None else max(10, int(abs((upper-lower)/delta)))
        xs = np.linspace(lower, upper, n+1)
        mids = 0.5*(xs[:-1]+xs[1:])
        midpoint_chunks = [part for part in np.array_split(mids, 20) if part.size]
        total = 0.0
        for k, xm in enumerate(midpoint_chunks, start=1):
            fm = numeric_values(f_num, xm)
            if not np.all(np.isfinite(fm)):
                raise ValueError("Function produced non-finite values in Rectangle.")
            total += np.sum(fm)*(upper-lower)/n
            progress_callback(int(k*100/len(midpoint_chunks)))
        result = total

    elif integration_method == "Trapezoidal":
        n = 2000 if delta is None else max(50, int(abs((upper-lower)/delta)))
        xs = np.linspace(lower, upper, n+1)
        ys = numeric_values(f_num, xs)
        if not np.all(np.isfinite(ys)):
            raise ValueError("Function produced non-finite values in Trapezoidal.")
        result = np.trapezoid(ys, xs)
        progress_callback(100)

    elif integration_method == "Simpson":
        n = 2001 if delta is None else max(101, int(abs((upper-lower)/delta)))
        if n % 2 == 0:
            n += 1
        xs = np.linspace(lower, upper, n)
        ys = numeric_values(f_num, xs)
        if not np.all(np.isfinite(ys)):
            raise ValueError("Function produced non-finite values in Simpson.")
        result = simpson(ys, x=xs)
        progress_callback(100)

    elif integration_method == "Romberg":
        result = romberg_custom(f_num, lower, upper, max_level=8, tol=1e-8)
        progress_callback(100)

    elif integration_method == "Gaussian Quadrature":
        result = gaussian_quadrature_fixed(f_num, lower, upper, n=64)
        coarse = gaussian_quadrature_fixed(f_num, lower, upper, n=32)
        error_estimate = float(abs(result - coarse))
        progress_callback(100)

    elif integration_method == "Simpson 3/8":
        n_int = 300 if delta is None else max(30, int(abs((upper-lower)/delta)))
        result = composite_simpson_38(f_num, lower, upper, n_intervals=n_int)
        progress_callback(100)

    elif integration_method == "Adaptive Simpson":
        result, error_estimate = quad(
            lambda t: numeric_scalar(f_num, t),
            lower,
            upper,
            epsabs=1.49e-8,
            epsrel=1.49e-8,
            limit=100,
        )
        progress_callback(100)

    else:
        raise ValueError(f"Unknown numerical method: {integration_method}")

    return float(result), error_estimate
