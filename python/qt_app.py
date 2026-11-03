"""PySide6 application entry point."""

from __future__ import annotations

import sys
import threading

from PySide6.QtWidgets import QApplication

from qt_main_window import IntegralCalculatorWindow


def _warm_up_calculations() -> None:
    from symbolic_service import warm_up

    warm_up()
    import scipy.integrate  # noqa: F401
    import scipy.optimize  # noqa: F401


def start_warm_up() -> None:
    """Load calculation engines once the window is visible so first answers are fast."""
    threading.Thread(target=_warm_up_calculations, name="calculation-warm-up", daemon=True).start()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Integral Calculator")
    window = IntegralCalculatorWindow()
    window.show()
    start_warm_up()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
