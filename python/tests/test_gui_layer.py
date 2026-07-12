import unittest

from base_tab import BaseTab
from i18n import INSTRUCTIONS, LANGUAGE_UI
from math_templates import template_names, template_value


class FakeEntry:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def delete(self, start, end):
        self.value = ""

    def insert(self, index, value):
        self.value = str(value)


class FakeLabel:
    def __init__(self):
        self.options = {}

    def config(self, **kwargs):
        self.options.update(kwargs)


class FakeApp:
    text = {"time": "Elapsed"}


class FakeTab(BaseTab):
    def __init__(self):
        super().__init__(FakeApp(), object())
        self.func_entry = FakeEntry("x^2")
        self.params_entry = FakeEntry("")
        self.result_label = FakeLabel()
        self.refreshed = False

    def refresh_after_function_set(self):
        self.refreshed = True


class GuiLayerTests(unittest.TestCase):
    def test_base_tab_controls_function_entry_and_result_label(self):
        tab = FakeTab()

        self.assertEqual(tab.get_function_text(), "x^2")
        tab.set_function_text("sin(x)")
        self.assertEqual(tab.func_entry.get(), "sin(x)")
        self.assertTrue(tab.refreshed)

        tab.result_label.config(text="old")
        tab.clear_result()
        self.assertEqual(tab.result_label.options["text"], "")

        self.assertTrue(tab.set_parameter_text("a=2"))
        self.assertEqual(tab.params_entry.get(), "a=2")

    def test_base_tab_clears_multiple_entries_and_formats_elapsed_time(self):
        tab = FakeTab()
        lower = FakeEntry("0")
        upper = FakeEntry("1")

        tab.clear_entries(lower, upper)
        self.assertEqual(lower.get(), "")
        self.assertEqual(upper.get(), "")
        self.assertEqual(tab.format_elapsed(None), "")
        self.assertEqual(tab.format_elapsed(1.23456), "\nElapsed: 1.235s")

    def test_locale_modules_keep_public_i18n_shape(self):
        self.assertEqual(set(INSTRUCTIONS), set(LANGUAGE_UI))
        for language, instructions in INSTRUCTIONS.items():
            with self.subTest(language=language):
                self.assertGreater(len(instructions), 5)
                self.assertIn("calc1", LANGUAGE_UI[language])

    def test_expanded_math_templates_are_available_by_name(self):
        names = template_names()

        self.assertIn("Damped sine", names)
        self.assertIn("Bump function", names)
        self.assertEqual(template_value("Parameterized sine"), "A*sin(k*x + phi)")
        self.assertEqual(template_value("custom expression"), "custom expression")


if __name__ == "__main__":
    unittest.main()
