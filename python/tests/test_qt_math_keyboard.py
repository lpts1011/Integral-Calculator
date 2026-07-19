import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from qt_math_keyboard import KEY_GROUPS, MathKeyboardWindow


class QtMathKeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.keyboard = MathKeyboardWindow()

    def tearDown(self):
        self.keyboard.close()
        self.keyboard.deleteLater()
        QApplication.processEvents()

    def test_keyboard_prioritizes_functions_and_has_no_standalone_digits(self):
        labels = {key.label for _group, keys in KEY_GROUPS for key in keys}
        self.assertGreaterEqual(len(labels), 40)
        self.assertTrue(set("0123456789").isdisjoint(labels))
        for label in (
            "sin",
            "cos",
            "tan",
            "asin",
            "sinh",
            "ln",
            "log",
            "exp",
            "a/b",
            "√x",
            "π",
            "∞",
        ):
            self.assertIn(label, labels)
        self.assertEqual(KEY_GROUPS[0][0], "Common")

    def test_buttons_keep_the_math_editor_focus_and_have_stable_sizes(self):
        self.assertGreaterEqual(len(self.keyboard.buttons), 45)
        for button in self.keyboard.buttons:
            self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.NoFocus)
            self.assertEqual(button.height(), 36)
            self.assertGreaterEqual(button.width(), 64)

    def test_insert_command_and_window_close_emit_their_actions(self):
        insertions = []
        commands = []
        closes = []
        self.keyboard.insert_requested.connect(insertions.append)
        self.keyboard.command_requested.connect(commands.append)
        self.keyboard.close_requested.connect(lambda: closes.append(True))

        next(
            button for button in self.keyboard.buttons if button.text() == "sin"
        ).click()
        next(
            button for button in self.keyboard.buttons if button.text() == "←"
        ).click()
        self.keyboard.close()

        self.assertEqual(insertions, [r"\sin\left(#?\right)"])
        self.assertEqual(commands, ["moveToPreviousChar"])
        self.assertEqual(closes, [True])

    def test_window_is_non_modal_and_stays_above_its_parent(self):
        flags = self.keyboard.windowFlags()
        self.assertTrue(flags & Qt.WindowType.Tool)
        self.assertTrue(flags & Qt.WindowType.WindowStaysOnTopHint)
        self.assertEqual(
            self.keyboard.windowModality(), Qt.WindowModality.NonModal
        )


if __name__ == "__main__":
    unittest.main()
