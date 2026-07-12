from functools import lru_cache

import calengine as np
from solving.core.expr import Expr
from solving.core.numbers import E, I, Float, Integer, Rational, oo, pi
from solving.core.symbol import symbols
from solving.functions import (
    Abs,
    Max,
    Min,
    Piecewise,
    acos,
    acosh,
    asin,
    asinh,
    atan,
    atanh,
    cos,
    cosh,
    exp,
    log,
    sign,
    sin,
    sinh,
    sqrt,
    tan,
    tanh,
)
from solving.parsing.solving_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)


SAFE_LOCALS = {
    "pi": pi, "E": E, "e": E, "I": I,
    "inf": oo, "-inf": -oo,
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan,
    "sinh": sinh, "cosh": cosh, "tanh": tanh,
    "asinh": asinh, "acosh": acosh, "atanh": atanh,
    "sqrt": sqrt, "log": log, "ln": log,
    "log10": lambda z: log(z, 10),
    "exp": exp,
    "abs": Abs, "Abs": Abs, "sign": sign,
    "Piecewise": Piecewise, "Min": Min, "Max": Max,
    "True": True, "False": False,
}

SAFE_GLOBALS = {
    "__builtins__": {},
    "Integer": Integer,
    "Float": Float,
    "Rational": Rational,
}

x_sym = symbols("x")
PARSER_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


@lru_cache(maxsize=512)
def parse_expr_str(expr_str: str, *, allow_x: bool):
    """
    Unified Solving expression parser.
    - allow_x=True: expression may contain variable x (functions)
    - allow_x=False: expression must be constant (limits)
    """
    s = expr_str.strip()
    if s == "":
        raise ValueError("Empty input.")
    try:
        local_dict = dict(SAFE_LOCALS)
        if allow_x:
            local_dict["x"] = x_sym
        expr = parse_expr(
            s,
            local_dict=local_dict,
            global_dict=SAFE_GLOBALS,
            transformations=PARSER_TRANSFORMATIONS,
            evaluate=True,
        )
        if not allow_x and expr.free_symbols:
            raise ValueError("This field does not allow variables.")
        if allow_x and (expr.free_symbols - {x_sym}):
            raise ValueError("Only variable x is allowed.")
        return expr
    except Exception as e:
        raise ValueError(f"Invalid input: {e}")


def parse_input_to_solving(value: str):
    return parse_expr_str(value, allow_x=False)


def parse_input_to_float(value: str) -> float:
    expr = parse_input_to_solving(value)
    if expr == oo:
        return np.inf
    if expr == -oo:
        return -np.inf
    return float(expr.evalf())


def evaluate_symbolic_function(func_str: str) -> Expr:
    return parse_expr_str(func_str, allow_x=True)


def has_complete_limits(lower_text: str, upper_text: str) -> bool:
    has_lower = bool(lower_text.strip())
    has_upper = bool(upper_text.strip())
    if has_lower != has_upper:
        raise ValueError(
            "Please provide both lower and upper limits, "
            "or leave both empty for an indefinite integral."
        )
    return has_lower
