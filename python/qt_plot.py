"""QtAgg container for the calculator's existing plot implementation."""

from __future__ import annotations

from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from plot_utils import clear_plot, plot_embedded
from theme_utils import apply_plot_theme


class QtPlotWidget(QWidget):
    """Embed the existing calculator plot in a Qt widget."""

    def __init__(self, parent: QWidget | None = None, theme: dict[str, str] | None = None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 5.2), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.ax = self.axes
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.plot_canvas = self.canvas
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.plot_toolbar = self.toolbar
        self.theme = theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(self.toolbar)
        if theme:
            apply_plot_theme(self.figure, self.axes, theme)
        self.clear()

    def set_theme(self, theme: dict[str, str] | None) -> None:
        self.theme = theme
        if theme:
            apply_plot_theme(self.figure, self.axes, theme)
        self.canvas.draw_idle()

    def plot_function(
        self,
        func: Any,
        lower: float,
        upper: float,
        split_points: list[float] | None = None,
    ) -> None:
        """Plot through the shared sampling and rendering helper."""

        plot_embedded(
            str(func),
            lower,
            upper,
            self.axes,
            self.canvas,
            self.theme,
            split_points=split_points,
        )

    def clear(self) -> None:
        clear_plot(self.axes, self.canvas, self.theme)


__all__ = ["QtPlotWidget"]
