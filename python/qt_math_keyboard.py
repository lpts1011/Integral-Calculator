"""Floating mathematical keyboard for the live MathLive editors."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class MathKey:
    label: str
    payload: str
    tooltip: str
    command: bool = False
    width: int = 64


KEY_GROUPS = (
    (
        "Common",
        (
            MathKey("sin", r"\sin\left(#?\right)", "Insert sine"),
            MathKey("cos", r"\cos\left(#?\right)", "Insert cosine"),
            MathKey("tan", r"\tan\left(#?\right)", "Insert tangent"),
            MathKey("ln", r"\ln\left(#?\right)", "Insert natural logarithm"),
            MathKey("log", r"\log\left(#?\right)", "Insert logarithm"),
            MathKey("exp", r"\exp\left(#?\right)", "Insert exponential function"),
            MathKey("a/b", r"\frac{#0#?}{#?}", "Insert a fraction", width=72),
            MathKey("√x", r"\sqrt{#0#?}", "Insert a square root", width=72),
            MathKey("xⁿ", r"#0^{#?}", "Insert a power", width=72),
            MathKey("eˣ", r"e^{#0#?}", "Insert e to a power", width=72),
            MathKey("( )", r"\left(#?\right)", "Insert parentheses", width=72),
            MathKey("|x|", r"\left|#?\right|", "Insert absolute value", width=72),
            MathKey("←", "moveToPreviousChar", "Move cursor left", True),
            MathKey("→", "moveToNextChar", "Move cursor right", True),
            MathKey("⌫", "deleteBackward", "Delete backward", True),
            MathKey("Del", "deleteForward", "Delete forward", True),
        ),
    ),
    (
        "Trig / Functions",
        (
            MathKey("asin", r"\operatorname{asin}\left(#?\right)", "Insert inverse sine", width=72),
            MathKey("acos", r"\operatorname{acos}\left(#?\right)", "Insert inverse cosine", width=72),
            MathKey("atan", r"\operatorname{atan}\left(#?\right)", "Insert inverse tangent", width=72),
            MathKey("sinh", r"\sinh\left(#?\right)", "Insert hyperbolic sine", width=72),
            MathKey("cosh", r"\cosh\left(#?\right)", "Insert hyperbolic cosine", width=72),
            MathKey("tanh", r"\tanh\left(#?\right)", "Insert hyperbolic tangent", width=72),
            MathKey("asinh", r"\operatorname{asinh}\left(#?\right)", "Insert inverse hyperbolic sine", width=76),
            MathKey("acosh", r"\operatorname{acosh}\left(#?\right)", "Insert inverse hyperbolic cosine", width=76),
            MathKey("atanh", r"\operatorname{atanh}\left(#?\right)", "Insert inverse hyperbolic tangent", width=76),
            MathKey("sign", r"\operatorname{sign}\left(#?\right)", "Insert sign function", width=72),
            MathKey("Min", r"\operatorname{Min}\left(#?,#?\right)", "Insert minimum", width=72),
            MathKey("Max", r"\operatorname{Max}\left(#?,#?\right)", "Insert maximum", width=72),
        ),
    ),
    (
        "Powers / Roots",
        (
            MathKey("a/b", r"\frac{#0#?}{#?}", "Insert a fraction", width=72),
            MathKey("1/x", r"\frac{1}{#0#?}", "Insert a reciprocal", width=72),
            MathKey("√x", r"\sqrt{#0#?}", "Insert a square root", width=72),
            MathKey("ⁿ√x", r"\sqrt[#?]{#0#?}", "Insert an nth root", width=72),
            MathKey("x²", r"#0^{2}", "Square the selection", width=72),
            MathKey("xⁿ", r"#0^{#?}", "Insert a power", width=72),
            MathKey("x⁻¹", r"#0^{-1}", "Insert a reciprocal power", width=72),
            MathKey("eˣ", r"e^{#0#?}", "Insert e to a power", width=72),
            MathKey("10ˣ", r"10^{#0#?}", "Insert 10 to a power", width=72),
        ),
    ),
    (
        "Symbols",
        (
            MathKey("x", "x", "Insert x"),
            MathKey("π", r"\pi", "Insert pi"),
            MathKey("e", "e", "Insert Euler's number"),
            MathKey("i", "I", "Insert the imaginary unit"),
            MathKey("∞", r"\infty", "Insert infinity"),
            MathKey("−∞", r"-\infty", "Insert negative infinity", width=72),
            MathKey("( )", r"\left(#?\right)", "Insert parentheses", width=72),
            MathKey("|x|", r"\left|#?\right|", "Insert absolute value", width=72),
            MathKey(",", ",", "Insert comma"),
            MathKey("=", "=", "Insert equals"),
            MathKey("<", "<", "Insert less than"),
            MathKey(">", ">", "Insert greater than"),
        ),
    ),
)


class MathKeyboardWindow(QDialog):
    insert_requested = Signal(str)
    command_requested = Signal(str)
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        super().__init__(parent, flags)
        self.setObjectName("mathKeyboardWindow")
        self.setWindowTitle("Math Keyboard")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.resize(680, 230)
        self.buttons: list[QToolButton] = []

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("mathKeyboardTabs")
        self.tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tabs.tabBar().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for group_name, keys in KEY_GROUPS:
            self.tabs.addTab(self._build_key_page(keys), group_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.tabs)

    def _build_key_page(self, keys: tuple[MathKey, ...]) -> QWidget:
        page = QWidget(self)
        grid = QGridLayout(page)
        grid.setContentsMargins(4, 5, 4, 5)
        grid.setHorizontalSpacing(5)
        grid.setVerticalSpacing(5)
        columns = 6
        for index, key in enumerate(keys):
            button = QToolButton(page)
            button.setText(key.label)
            button.setToolTip(key.tooltip)
            button.setAccessibleName(key.tooltip)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(key.width, 36)
            if key.command:
                button.clicked.connect(
                    lambda _checked=False, value=key.payload: (
                        self.command_requested.emit(value)
                    )
                )
            else:
                button.clicked.connect(
                    lambda _checked=False, value=key.payload: (
                        self.insert_requested.emit(value)
                    )
                )
            self.buttons.append(button)
            grid.addWidget(
                button,
                index // columns,
                index % columns,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        return page

    def set_title(self, title: str) -> None:
        self.setWindowTitle(str(title))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.close_requested.emit()
        super().closeEvent(event)


__all__ = ["KEY_GROUPS", "MathKey", "MathKeyboardWindow"]
