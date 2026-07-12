import re


COMMON_FUNCTIONS = ("sin", "cos", "tan", "log", "ln", "sqrt", "exp")


def friendly_error_message(error, func_str="", lower_text="", upper_text=""):
    message = str(error)
    hints = []
    expression = (func_str or "").strip()
    lower = (lower_text or "").strip()
    upper = (upper_text or "").strip()

    if "Empty input" in message and not expression:
        hints.append("Enter a function first, for example x^2 or sin(x).")
    if "Only variable x is allowed" in message:
        hints.append("Use x as the only variable. For example, write sin(x), not sin(t).")
    if "This field does not allow variables" in message:
        hints.append("Limits must be constants such as 0, 1, pi, -inf, or inf.")
    if "both lower and upper limits" in message:
        hints.append("Fill both limits for a definite integral, or leave both blank for an indefinite integral.")
    if "Step size" in message or "delta" in message:
        hints.append("Use a positive step size, such as 0.01 or 0.1.")
    if "singularity" in message:
        hints.append("Try splitting the interval around the singular point.")
    if "non-finite" in message or "not finite" in message:
        hints.append("Check the function domain and avoid points where the function is undefined.")
    if "exceeded" in message or "timeout" in message.lower():
        hints.append("Try numerical integration, simplify the expression, or split the interval.")

    if expression:
        lower_expr = expression.lower().replace(" ", "")
        for name in COMMON_FUNCTIONS:
            if re.search(rf"\b{name}x\b", lower_expr):
                hints.append(f"Did you mean {name}(x)?")
                break
        if "^" not in expression and re.search(r"\d+x", expression):
            hints.append("Implicit multiplication is allowed, but 2*x can be clearer than 2x.")

    if lower and upper and lower == upper:
        hints.append("The lower and upper limits are the same, so the definite integral is 0.")

    if not hints:
        return message

    unique_hints = []
    for hint in hints:
        if hint not in unique_hints:
            unique_hints.append(hint)
    return message + "\n\nSuggestions:\n- " + "\n- ".join(unique_hints)
