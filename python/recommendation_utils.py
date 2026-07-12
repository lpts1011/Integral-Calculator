from dataclasses import dataclass
from functools import lru_cache

import calengine as np

from numeric_methods import build_numeric_callable, find_symbolic_singularities, numeric_values
from parser_utils import evaluate_symbolic_function, parse_input_to_float


@dataclass(frozen=True)
class MethodRecommendation:
    mode: str
    method: str
    message_key: str
    params: dict | None = None

    def message(self, text):
        template = text.get(self.message_key, self.message_key)
        return template.format(**(self.params or {}))


@lru_cache(maxsize=512)
def recommend_tab2_method(func_str, lower_text, upper_text):
    func = func_str.strip()
    lower_raw = lower_text.strip()
    upper_raw = upper_text.strip()

    if not func:
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_enter_function",
        )

    if bool(lower_raw) != bool(upper_raw):
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_complete_limits",
        )

    if not lower_raw and not upper_raw:
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_indefinite",
        )

    try:
        lower = parse_input_to_float(lower_raw)
        upper = parse_input_to_float(upper_raw)
    except Exception:
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_invalid_limits",
        )

    if not np.isfinite(lower) or not np.isfinite(upper):
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_improper",
        )

    if lower == upper:
        return MethodRecommendation(
            "Numerical Integration",
            "Trapezoidal",
            "recommend_zero_width",
        )

    try:
        expr = evaluate_symbolic_function(func)
        singularities = find_symbolic_singularities(expr, lower, upper)
        if singularities:
            point = f"{singularities[0]:.6g}"
            return MethodRecommendation(
                "Numerical Integration",
                "Adaptive Simpson",
                "recommend_singularity",
                {"point": point},
            )
    except Exception:
        return MethodRecommendation(
            "Symbolic Integration",
            "Trapezoidal",
            "recommend_invalid_function",
        )

    width = abs(upper - lower)
    func_lower = func.lower()
    sample = _sample_function_behavior(expr, lower, upper)
    if sample["has_nonfinite"]:
        return MethodRecommendation(
            "Numerical Integration",
            "Adaptive Simpson",
            "recommend_nonfinite_samples",
        )
    if sample["oscillation_score"] >= 12 or (any(name in func_lower for name in ("sin", "cos", "tan")) and width > 20):
        return MethodRecommendation(
            "Numerical Integration",
            "Adaptive Simpson",
            "recommend_oscillatory",
        )
    if sample["variation_ratio"] > 100:
        return MethodRecommendation(
            "Numerical Integration",
            "Adaptive Simpson",
            "recommend_steep",
        )
    if any(name in func_lower for name in ("exp", "sqrt", "log", "ln")):
        return MethodRecommendation(
            "Numerical Integration",
            "Gaussian Quadrature",
            "recommend_smooth_nonlinear",
        )
    if expr.is_polynomial():
        return MethodRecommendation(
            "Numerical Integration",
            "Simpson",
            "recommend_polynomial",
        )

    return MethodRecommendation(
        "Numerical Integration",
        "Simpson",
        "recommend_default",
    )


def _sample_function_behavior(expr, lower, upper):
    f_num = build_numeric_callable(expr)
    xs = np.linspace(lower, upper, 201)
    try:
        ys = numeric_values(f_num, xs)
    except Exception:
        return {
            "has_nonfinite": True,
            "oscillation_score": 0,
            "variation_ratio": np.inf,
        }

    finite = np.isfinite(ys)
    if not np.all(finite):
        return {
            "has_nonfinite": True,
            "oscillation_score": 0,
            "variation_ratio": np.inf,
        }

    centered = ys - np.nanmean(ys)
    signs = np.sign(centered)
    signs = signs[signs != 0]
    oscillation_score = int(np.sum(signs[1:] * signs[:-1] < 0)) if signs.size > 1 else 0

    diffs = np.abs(np.diff(ys))
    median_diff = float(np.median(diffs)) if diffs.size else 0.0
    max_diff = float(np.max(diffs)) if diffs.size else 0.0
    variation_ratio = max_diff / max(median_diff, 1e-12)

    return {
        "has_nonfinite": False,
        "oscillation_score": oscillation_score,
        "variation_ratio": variation_ratio,
    }
