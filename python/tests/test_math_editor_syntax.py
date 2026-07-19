import unittest

from math_editor import syntax as math_syntax
from math_editor.syntax import (
    FieldRole,
    calculator_to_asciimath,
    normalize_mathlive_text,
)


class MathEditorSyntaxTests(unittest.TestCase):
    def test_normalizes_mathlive_ascii_math_for_calculator(self):
        fixtures = {
            "x^2": "x^2",
            "1/(x+1)": "1/(x+1)",
            "sqrt(x)": "sqrt(x)",
            "abs(x)": "abs(x)",
            "pi": "pi",
            "oo": "inf",
            "-oo": "-inf",
            "|x|": "Abs(x)",
            "2 x": "2*x",
        }
        for source, expected in fixtures.items():
            with self.subTest(source=source):
                self.assertEqual(math_syntax._normalize_tokens(source), expected)

    def test_allows_incomplete_structure_while_typing(self):
        state = normalize_mathlive_text("1/", FieldRole.EXPRESSION)
        self.assertEqual(state.status, "incomplete")
        self.assertEqual(state.calculator_text, "")

    def test_normalizes_nested_absolute_values(self):
        fixtures = {
            "|x+|x||": "Abs(x+Abs(x))",
            "|x+|x|+1|": "Abs(x+Abs(x)+1)",
            "||x||": "Abs(Abs(x))",
            "|x|+|y|": "Abs(x)+Abs(y)",
        }
        for source, expected in fixtures.items():
            with self.subTest(source=source):
                self.assertEqual(math_syntax._normalize_tokens(source), expected)

        state = normalize_mathlive_text("||x||", FieldRole.EXPRESSION)
        self.assertEqual(state.status, "valid")
        self.assertEqual(state.calculator_text, "Abs(Abs(x))")

    def test_keeps_unmatched_absolute_value_bar_incomplete(self):
        state = normalize_mathlive_text("|x", FieldRole.EXPRESSION)
        self.assertEqual(state.status, "incomplete")
        self.assertEqual(state.calculator_text, "")

    def test_validates_bounds_parameters_and_split_points(self):
        self.assertEqual(normalize_mathlive_text("pi", FieldRole.BOUND).status, "valid")
        self.assertEqual(
            normalize_mathlive_text("a=2,b=pi", FieldRole.PARAMETERS).status,
            "valid",
        )
        self.assertEqual(
            normalize_mathlive_text("0,pi/2", FieldRole.SPLIT_POINTS).status,
            "valid",
        )

    def test_equation_fields_preserve_helper_syntax_exactly(self):
        for value in ("u=x^2", "y'=x*y"):
            with self.subTest(value=value):
                state = normalize_mathlive_text(value, FieldRole.EQUATION)
                self.assertEqual(state.status, "valid")
                self.assertEqual(state.calculator_text, value)

    def test_converts_existing_calculator_text_for_mathlive(self):
        self.assertEqual(calculator_to_asciimath("x**2"), "x^2")
        self.assertEqual(calculator_to_asciimath("inf"), "oo")
        self.assertEqual(calculator_to_asciimath("x**2 + inf"), "x^2 + oo")


if __name__ == "__main__":
    unittest.main()
