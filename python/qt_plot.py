"""QtAgg container for the calculator's existing plot implementation."""

from __future__ import annotations

from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer
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
        self._last_plot = None
        self._rendering = False
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(150)
        self._zoom_timer.timeout.connect(self._resample_zoom)

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

        self._last_plot = (str(func),lower,upper,split_points)
        self._render_plot()

    def _render_plot(self, visible_limits=None):
        if self._last_plot is None:
            return
        function,lower,upper,points = self._last_plot
        self._rendering = True
        try:
            plot_embedded(function,lower,upper,self.axes,self.canvas,self.theme,
                          split_points=points,visible_limits=visible_limits)
            self.axes.callbacks.connect("xlim_changed",self._zoom_changed)
        finally:
            self._rendering = False
            self._zoom_timer.stop()

    def _zoom_changed(self,*_args):
        if not self._rendering and self._last_plot is not None:
            self._zoom_timer.start()

    def _resample_zoom(self):
        limits = self.axes.get_xlim()
        y_limits = self.axes.get_ylim()
        self._render_plot(limits)
        self.axes.set_ylim(*y_limits)
        self.canvas.draw_idle()

    def clear(self) -> None:
        self._last_plot = None
        self._zoom_timer.stop()
        clear_plot(self.axes, self.canvas, self.theme)


__all__ = ["QtPlotWidget"]
