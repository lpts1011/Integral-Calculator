from dataclasses import dataclass
from enum import Enum

from interval_utils import parse_split_points
from parameter_utils import parse_parameter_assignments
from parser_utils import (
    SAFE_LOCALS,
    evaluate_symbolic_function,
    parse_input_to_solving,
)


class FieldRole(str, Enum):
    EXPRESSION = "expression"
    BOUND = "bound"
    PARAMETERS = "parameters"
    SPLIT_POINTS = "split_points"
    EQUATION = "equation"


@dataclass(frozen=True)
class MathInputState:
    status: str
    display_text: str
    calculator_text: str
    error: str = ""


class _Token:
    __slots__ = ("kind", "text")

    def __init__(self, kind: str, text: str):
        self.kind = kind
        self.text = text


_INCOMPLETE_SUFFIXES = ("/", "^", "(", ",")
_FUNCTION_NAMES = frozenset(
    name for name, value in SAFE_LOCALS.items() if callable(value)
)


class _IncompleteAbsoluteValue(Exception):
    pass


def _tokenize(value: str) -> list[_Token]:
    tokens = []
    index = 0
    while index < len(value):
        character = value[index]
        if character.isspace():
            end = index + 1
            while end < len(value) and value[end].isspace():
                end += 1
            tokens.append(_Token("whitespace", value[index:end]))
            index = end
            continue
        if character.isalpha() or character == "_":
            end = index + 1
            while end < len(value) and (value[end].isalnum() or value[end] == "_"):
                end += 1
            tokens.append(_Token("identifier", value[index:end]))
            index = end
            continue
        if character.isdigit() or (
            character == "." and index + 1 < len(value) and value[index + 1].isdigit()
        ):
            end = index
            saw_decimal = False
            while end < len(value) and value[end].isdigit():
                end += 1
            if end < len(value) and value[end] == ".":
                saw_decimal = True
                end += 1
                while end < len(value) and value[end].isdigit():
                    end += 1
            if not saw_decimal and end < len(value) and value[end] == ".":
                end += 1
            if end < len(value) and value[end] in "eE":
                exponent_end = end + 1
                if exponent_end < len(value) and value[exponent_end] in "+-":
                    exponent_end += 1
                digit_start = exponent_end
                while exponent_end < len(value) and value[exponent_end].isdigit():
                    exponent_end += 1
                if exponent_end > digit_start:
                    end = exponent_end
            tokens.append(_Token("number", value[index:end]))
            index = end
            continue
        if value.startswith("**", index):
            tokens.append(_Token("operator", "**"))
            index += 2
            continue
        if character == "\N{INFINITY}":
            tokens.append(_Token("identifier", "oo"))
        elif character in "(),;":
            tokens.append(_Token("delimiter", character))
        elif character == "|":
            tokens.append(_Token("bar", character))
        elif character in "+-*/^=<>":
            tokens.append(_Token("operator", character))
        else:
            tokens.append(_Token("other", character))
        index += 1
    return tokens


def _replace_aliases(tokens: list[_Token]) -> list[_Token]:
    for token in tokens:
        if token.kind == "identifier" and token.text == "oo":
            token.text = "inf"
    return tokens


def _replace_absolute_values(tokens: list[_Token]) -> list[_Token]:
    result = []
    contexts = [result]
    previous_bar_state = None

    for index, token in enumerate(tokens):
        if token.kind != "bar":
            contexts[-1].append(token)
            previous_bar_state = None
            continue

        previous = tokens[index - 1] if index else None
        opening_context = (
            previous is None
            or previous.kind == "operator"
            or previous.text in {"(", ","}
            or previous_bar_state == "opening"
        )
        stack_is_open = len(contexts) > 1
        if opening_context or not stack_is_open:
            contexts.append([])
            previous_bar_state = "opening"
            continue

        inner = contexts.pop()
        contexts[-1].extend((_Token("identifier", "Abs"), _Token("delimiter", "(")))
        contexts[-1].extend(inner)
        contexts[-1].append(_Token("delimiter", ")"))
        previous_bar_state = "closing"

    if len(contexts) > 1:
        raise _IncompleteAbsoluteValue
    return result


def _is_left_factor(token: _Token) -> bool:
    return token.kind in {"number", "identifier"} or token.text == ")"


def _is_right_factor(token: _Token) -> bool:
    return token.kind in {"number", "identifier"} or token.text == "("


def _needs_multiplication(left: _Token, right: _Token) -> bool:
    if not (_is_left_factor(left) and _is_right_factor(right)):
        return False
    if left.kind == "identifier" and left.text in _FUNCTION_NAMES and right.text == "(":
        return False
    return True


def _join_tokens(tokens: list[_Token]) -> str:
    parts = []
    previous = None
    for token in tokens:
        if previous is not None and _needs_multiplication(previous, token):
            parts.append("*")
        parts.append(token.text)
        previous = token
    return "".join(parts)


def _normalize_tokens(value: str) -> str:
    tokens = [token for token in _tokenize(value) if token.kind != "whitespace"]
    tokens = _replace_aliases(tokens)
    tokens = _replace_absolute_values(tokens)
    return _join_tokens(tokens)


def calculator_to_asciimath(value: str) -> str:
    tokens = _tokenize(value.strip())
    for token in tokens:
        if token.kind == "operator" and token.text == "**":
            token.text = "^"
        elif token.kind == "identifier" and token.text == "inf":
            token.text = "oo"
    return "".join(token.text for token in tokens)


def normalize_mathlive_text(value: str, role: FieldRole) -> MathInputState:
    display = value.strip()
    if not display:
        return MathInputState("empty", display, "")
    if (
        display.endswith(_INCOMPLETE_SUFFIXES)
        or display.count("(") > display.count(")")
        or display.count("|") % 2
    ):
        return MathInputState("incomplete", display, "")

    try:
        if role is FieldRole.EQUATION:
            return MathInputState("valid", display, display)

        calculator = _normalize_tokens(display)
        if role is FieldRole.EXPRESSION:
            evaluate_symbolic_function(calculator)
        elif role is FieldRole.BOUND:
            parse_input_to_solving(calculator)
        elif role is FieldRole.PARAMETERS:
            parse_parameter_assignments(calculator)
        elif role is FieldRole.SPLIT_POINTS:
            parse_split_points(calculator, float("-inf"), float("inf"))
        else:
            raise ValueError(f"Unsupported field role: {role}")
    except _IncompleteAbsoluteValue:
        return MathInputState("incomplete", display, "")
    except Exception as exc:
        return MathInputState("invalid", display, "", str(exc))
    return MathInputState("valid", display, calculator)
