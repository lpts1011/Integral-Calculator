from functools import lru_cache

import calengine as np
from solving.core.relational import Relational
from solving.functions import Piecewise
from solving.logic.boolalg import true

from parser_utils import parse_input_to_float, x_sym


def _parse_split_points_uncached(split_text, lower, upper):
    text = split_text.strip()
    if not text:
        return []
    points = []
    lo, hi = sorted((float(lower), float(upper)))
    for part in text.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        value = parse_input_to_float(item)
        if not np.isfinite(value):
            raise ValueError("Split points must be finite.")
        if lo < float(value) < hi:
            points.append(float(value))
    return sorted(set(points))


@lru_cache(maxsize=512)
def _parse_split_points_cached(split_text, lower, upper):
    return tuple(_parse_split_points_uncached(split_text, lower, upper))


def parse_split_points(split_text, lower, upper):
    return list(_parse_split_points_cached(split_text, lower, upper))


def _find_piecewise_breakpoints_uncached(expr, lower, upper):
    lo, hi = sorted((float(lower), float(upper)))
    points = []
    for piecewise in expr.atoms(Piecewise):
        for _, condition in piecewise.args:
            points.extend(_condition_breakpoints(condition, lo, hi))
    return sorted(set(points))


@lru_cache(maxsize=512)
def _find_piecewise_breakpoints_cached(expr, lower, upper):
    return tuple(_find_piecewise_breakpoints_uncached(expr, lower, upper))


def find_piecewise_breakpoints(expr, lower, upper):
    try:
        hash(expr)
    except TypeError:
        return _find_piecewise_breakpoints_uncached(expr, lower, upper)
    return list(_find_piecewise_breakpoints_cached(expr, lower, upper))


def build_subintervals(lower, upper, split_points):
    reverse = float(lower) > float(upper)
    inner_points = sorted(set(float(point) for point in split_points), reverse=reverse)
    points = [float(lower), *inner_points, float(upper)]
    intervals = []
    for left, right in zip(points[:-1], points[1:]):
        if left != right:
            intervals.append((left, right))
    return intervals


def _condition_breakpoints(condition, lo, hi):
    if condition in (True, true):
        return []
    points = []
    for relational in condition.atoms(Relational):
        if relational.lhs == x_sym and not relational.rhs.has(x_sym):
            value = _finite_float(relational.rhs)
        elif relational.rhs == x_sym and not relational.lhs.has(x_sym):
            value = _finite_float(relational.lhs)
        else:
            value = None
        if value is not None and lo < value < hi:
            points.append(value)
    return points


def _finite_float(expr):
    try:
        value = float(expr.evalf())
    except Exception:
        return None
    if value == float("inf") or value == float("-inf"):
        return None
    return value
