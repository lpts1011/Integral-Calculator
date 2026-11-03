"""QtAgg container for the calculator's existing plot implementation."""

from __future__ import annotations

from typing import Any

from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from plot_utils import clear_plot, plot_embedded
from theme_utils import apply_plot_theme


# Chinese fonts on macOS, Windows, and Linux; the first one found draws characters the default font lacks.
CJK_FONTS = (
    "PingFang SC",
    "Heiti SC",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
)


def _use_cjk_font_fallback() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    fallback = next((name for name in CJK_FONTS if name in available), None)
    if fallback is not None:
        rcParams["font.family"] = ["sans-serif", fallback]


_use_cjk_font_fallback()


class QtPlotWidget(QWidget):
    """Embed the existing calculator plot in a Qt widget."""

    def __init__(self, parent: QWidget | None = None, theme: dict[str, str] | None = None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 5.2), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.ax = self.axes
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.theme = theme
        self.labels: dict[str, object] | None = None
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

    def set_labels(self, text: dict[str, object]) -> None:
        """Use translated graph labels from the interface text."""
        self.labels = dict(text)
        if self._last_plot is None:
            self.clear()
        else:
            self._render_plot()

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
                          split_points=points,visible_limits=visible_limits,labels=self.labels)
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
        clear_plot(self.axes, self.canvas, self.theme, self.labels)


__all__ = ["QtPlotWidget"]
