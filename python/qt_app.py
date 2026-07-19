"""PySide6 application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from qt_main_window import IntegralCalculatorWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Integral Calculator")
    window = IntegralCalculatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
