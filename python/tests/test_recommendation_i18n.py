import unittest

from error_utils import friendly_error_message
from i18n import LANGUAGE_UI, ui_text
from recommendation_utils import recommend_tab2_method


class RecommendationI18nTests(unittest.TestCase):
    def test_polynomial_recommends_simpson(self):
        recommendation = recommend_tab2_method("x^2", "0", "1")
        self.assertEqual(recommendation.mode, "Numerical Integration")
        self.assertEqual(recommendation.method, "Simpson")

    def test_improper_interval_recommends_symbolic_or_tab3(self):
        recommendation = recommend_tab2_method("exp(-x)", "0", "inf")
        self.assertEqual(recommendation.mode, "Symbolic Integration")
        self.assertEqual(recommendation.message_key, "recommend_improper")

    def test_oscillatory_sampling_recommends_adaptive_simpson(self):
        recommendation = recommend_tab2_method("sin(50*x)", "0", "1")
        self.assertEqual(recommendation.method, "Adaptive Simpson")

    def test_friendly_error_suggests_function_parentheses(self):
        message = friendly_error_message("Only variable x is allowed.", "sinx", "0", "1")
        self.assertIn("sin(x)", message)

    def test_all_languages_include_new_ui_keys(self):
        required = {
            "template",
            "insert_template",
            "theme",
            "parameters",
            "split_points",
            "compare_methods",
            "comparison_title",
            "apply_recommendation",
            "show_steps",
            "suggest_input",
            "math_tools",
            "copy",
            "use_selected",
            "math_tools_basic",
            "math_tools_analysis",
            "math_tools_builders",
            "math_tools_calculus",
            "math_tools_advanced",
            "math_tools_multi",
            "time",
            "recommend_default",
        }
        for language in LANGUAGE_UI:
            with self.subTest(language=language):
                text = ui_text(language)
                self.assertTrue(required <= set(text))

    def test_non_english_action_buttons_are_translated(self):
        english = ui_text("English")
        for language in LANGUAGE_UI:
            if language == "English":
                continue
            with self.subTest(language=language):
                text = ui_text(language)
                self.assertNotEqual(text["show_steps"], english["show_steps"])
                self.assertNotEqual(text["suggest_input"], english["suggest_input"])
                self.assertNotEqual(text["math_tools"], english["math_tools"])


if __name__ == "__main__":
    unittest.main()
