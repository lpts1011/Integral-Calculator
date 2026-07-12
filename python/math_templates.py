TEMPLATES = [
    ("Quadratic", "x^2"),
    ("Cubic polynomial", "x^3 - 2*x + 1"),
    ("Sine", "sin(x)"),
    ("Damped sine", "exp(-x)*sin(5*x)"),
    ("High-frequency sine", "sin(50*x)"),
    ("Gaussian", "exp(-x^2)"),
    ("Exponential decay", "exp(-x)"),
    ("Cauchy kernel", "1/(1+x^2)"),
    ("Shifted inverse square", "1/(x+2)^2"),
    ("Semicircle", "sqrt(1-x^2)"),
    ("Absolute value", "abs(x)"),
    ("Shifted absolute value", "abs(x-1)"),
    ("Logistic curve", "1/(1+exp(-x))"),
    ("Bump function", "Piecewise((exp(-1/(1-x^2)), abs(x) < 1), (0, True))"),
    ("Step function", "Piecewise((0, x < 0), (1, True))"),
    ("Parameterized quadratic", "a*x^2 + b*x + c"),
    ("Parameterized sine", "A*sin(k*x + phi)"),
    ("Piecewise linear/quadratic", "Piecewise((x, x < 0), (x^2, True))"),
]

TEMPLATE_NAMES = tuple(name for name, _ in TEMPLATES)
TEMPLATE_VALUES = {}
for template_name, template_value_text in TEMPLATES:
    TEMPLATE_VALUES.setdefault(template_name, template_value_text)


def template_names():
    return list(TEMPLATE_NAMES)


def template_value(name):
    return TEMPLATE_VALUES.get(name, name)
