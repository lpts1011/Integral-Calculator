from functools import lru_cache
import re

from solving.core.symbol import Symbol
from solving.parsing.solving_parser import parse_expr
from solving.printing.str import sstr
from solving.simplify.simplify import simplify

from parser_utils import (
    PARSER_TRANSFORMATIONS,
    SAFE_GLOBALS,
    SAFE_LOCALS,
    parse_input_to_solving,
    x_sym,
)


PARAMETER_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RESERVED_NAMES = set(SAFE_LOCALS) | {"x"}


@lru_cache(maxsize=256)
def _parse_parameter_assignments_cached(params_text):
    text = params_text.strip()
    if not text:
        return ()

    assignments = {}
    for part in re.split(r"[;,]", text):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError("Parameters must use name=value format, for example a=2, b=pi.")
        name, value_text = [piece.strip() for piece in item.split("=", 1)]
        if not PARAMETER_NAME_RE.match(name):
            raise ValueError(f"Invalid parameter name: {name}")
        if name in RESERVED_NAMES:
            raise ValueError(f"Parameter name '{name}' is reserved.")
        if name in assignments:
            raise ValueError(f"Duplicate parameter value for {name}.")
        assignments[name] = parse_input_to_solving(value_text)
    return tuple(assignments.items())


def parse_parameter_assignments(params_text):
    return dict(_parse_parameter_assignments_cached(params_text))


@lru_cache(maxsize=256)
def evaluate_function_with_parameters(func_str, params_text=""):
    assignments = parse_parameter_assignments(params_text)
    local_dict = dict(SAFE_LOCALS)
    local_dict["x"] = x_sym
    parameter_symbols = {name: Symbol(name) for name in assignments}
    local_dict.update(parameter_symbols)

    try:
        expr = parse_expr(
            func_str.strip(),
            local_dict=local_dict,
            global_dict=SAFE_GLOBALS,
            transformations=PARSER_TRANSFORMATIONS,
            evaluate=True,
        )
    except Exception as exc:
        raise ValueError(f"Invalid input: {exc}")

    allowed_symbols = {x_sym, *parameter_symbols.values()}
    unknown_symbols = expr.free_symbols - allowed_symbols
    if unknown_symbols:
        names = ", ".join(sorted(str(symbol) for symbol in unknown_symbols))
        raise ValueError(f"Missing parameter values for: {names}")

    substitutions = {
        parameter_symbols[name]: value
        for name, value in assignments.items()
    }
    expr = simplify(expr.subs(substitutions))
    remaining = expr.free_symbols - {x_sym}
    if remaining:
        names = ", ".join(sorted(str(symbol) for symbol in remaining))
        raise ValueError(f"Missing parameter values for: {names}")
    return expr


@lru_cache(maxsize=256)
def resolve_function_text(func_str, params_text=""):
    return sstr(evaluate_function_with_parameters(func_str, params_text))


def display_function_with_parameters(func_str, params_text=""):
    params = params_text.strip()
    if not params:
        return func_str.strip()
    return f"{func_str.strip()} [{params}]"
