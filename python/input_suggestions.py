import re


FUNCTION_NAMES = ("sin", "cos", "tan", "ln", "log", "sqrt", "exp", "asin", "acos", "atan")


def suggest_expression(text):
    original = text.strip()
    if not original:
        return []

    suggestions = []
    function_fixed = _fix_function_without_parentheses(original)
    if function_fixed != original:
        suggestions.append(function_fixed)

    exp_fixed = _fix_e_power(original)
    if exp_fixed != original:
        suggestions.append(exp_fixed)

    power_fixed = _fix_missing_power_operator(original)
    if power_fixed != original:
        suggestions.append(power_fixed)

    return _dedupe(suggestions)


def suggestion_report(text):
    suggestions = suggest_expression(text)
    if not suggestions:
        return "No obvious input issues were found."
    lines = ["Possible corrections:"]
    lines.extend(f"- {suggestion}" for suggestion in suggestions)
    return "\n".join(lines)


def _fix_function_without_parentheses(text):
    fixed = text
    for name in sorted(FUNCTION_NAMES, key=len, reverse=True):
        fixed = re.sub(
            rf"\b{name}x\b",
            f"{name}(x)",
            fixed,
            flags=re.IGNORECASE,
        )
    return fixed


def _fix_e_power(text):
    match = re.fullmatch(r"e\^(.+)", text.strip(), flags=re.IGNORECASE)
    if not match:
        return text
    return f"exp({match.group(1).strip()})"


def _fix_missing_power_operator(text):
    return re.sub(r"\bx(\d+)\b", r"x^\1", text)


def _dedupe(values):
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
