from solving.core.function import Function, count_ops
from solving.integrals.integrals import Integral
from solving.printing.str import sstr
from solving.simplify.simplify import simplify


ELEMENTARY_FUNCTIONS = frozenset({
    "exp", "log", "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "acot", "asec", "acsc",
    "sinh", "cosh", "tanh", "coth", "sech", "csch",
    "asinh", "acosh", "atanh", "acoth", "Abs", "sign", "Piecewise", "Max", "Min",
})
# A value with more operations than this reads better as a number.
COMPLICATED_OPS = 20
# Larger results are left as they are so simplification stays quick.
SIMPLIFY_MAX_OPS = 150


def tidy_result(expr):
    """Simplify an integration result, e.g. gamma(3/4)/gamma(7/4) to 4/3."""
    try:
        if count_ops(expr) <= SIMPLIFY_MAX_OPS:
            return simplify(expr)
    except Exception:
        pass
    return expr


def is_complicated(expr):
    """True when a value needs special functions or is too long to read."""
    try:
        if any(type(func).__name__ not in ELEMENTARY_FUNCTIONS for func in expr.atoms(Function)):
            return True
        return count_ops(expr) > COMPLICATED_OPS
    except Exception:
        return False


def pretty_math_str(expr):
    """
    Convert Solving string to nicer math form:
    exp(2) -> e^(2)
    exp(x+1) -> e^(x+1)
    ** -> ^
    pi -> π
    """
    try:
        s = sstr(expr)
        s = s.replace("**", "^").replace("pi", "π")

        def replace_exp(text):
            max_iterations = 100
            iteration = 0

            while "exp(" in text and iteration < max_iterations:
                iteration += 1
                start = text.find("exp(")
                if start == -1:
                    break

                depth = 0
                end = -1
                for i in range(start + 4, len(text)):
                    if text[i] == "(":
                        depth += 1
                    elif text[i] == ")":
                        if depth == 0:
                            end = i
                            break
                        depth -= 1

                if end == -1:
                    break

                content = text[start+4:end]
                text = text[:start] + f"e^({content})" + text[end+1:]

            return text

        return replace_exp(s)
    except Exception:
        return sstr(expr).replace("**", "^").replace("pi", "π")


def format_result_for_display(expr, significant_digits=10, symbolic_len_limit=50):
    """
    Improved unified display formatting for symbolic/numeric results.
    Returns dict: {display, raw, type, numeric}
    """
    raw_str = sstr(expr)

    if isinstance(expr, Integral) or expr.has(Integral):
        return {
            "display": raw_str,
            "raw": raw_str,
            "type": "unevaluated",
            "numeric": None,
        }

    if len(raw_str) <= symbolic_len_limit and not is_complicated(expr):
        if "exp(exp" not in raw_str:
            return {
                "display": pretty_math_str(expr),
                "raw": raw_str,
                "type": "exact",
                "numeric": None,
            }

    try:
        val = float(expr.evalf())
        return {
            "display": f"≈ {val:.{significant_digits}g}",
            "raw": raw_str,
            "type": "exact",
            "numeric": val,
        }
    except Exception:
        return {
            "display": raw_str,
            "raw": raw_str,
            "type": "unevaluated",
            "numeric": None,
        }
