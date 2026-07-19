import unittest

from theme_utils import THEMES, button_palette


class ThemeUtilsTests(unittest.TestCase):
    def test_light_action_buttons_keep_native_readable_text(self):
        theme = THEMES["Light"]

        self.assertEqual(button_palette(theme, "Calculate Integral"), (theme["accent"], theme["button_fg"]))
        self.assertEqual(button_palette(theme, "Insert Template"), (theme["accent"], theme["button_fg"]))
        self.assertEqual(button_palette(theme, "Reset"), (theme["danger"], theme["button_fg"]))

    def test_default_button_uses_default_button_palette(self):
        theme = THEMES["Light"]

        self.assertEqual(button_palette(theme, "Show Steps"), (theme["button_bg"], theme["button_fg"]))


if __name__ == "__main__":
    unittest.main()
