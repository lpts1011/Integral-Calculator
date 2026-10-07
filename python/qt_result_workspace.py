"""Rendered result workspace shared by all integration tabs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from math_editor.resource_paths import runtime_resource_root
from qt_async import run_in_background
from result_presenter import (
    build_result_summary,
    build_symbolic_steps,
    supports_symbolic_steps,
)


class ResultWorkspace(QWidget):
    """Display result values immediately and derive symbolic steps off-thread."""

    def __init__(self, parent: QWidget | None = None, *, thread_pool=None) -> None:
        super().__init__(parent)
        self.setObjectName("resultWorkspace")
        self.setMinimumHeight(200)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._ready = False
        self._pending_script: str | None = None
        self._generation = 0
        self._text: dict[str, object] = {}
        self._theme_name = "Light"
        self._model = build_result_summary(None)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QWebEngineView(self)
        layout.addWidget(self.view)
        self.view.loadFinished.connect(self._load_finished)
        self.view.load(
            QUrl.fromLocalFile(str(Path(runtime_resource_root()) / "results.html"))
        )

    @property
    def model(self) -> dict[str, Any]:
        return dict(self._model)

    def is_ready(self) -> bool:
        return self._ready

    @property
    def web_view(self) -> QWebEngineView:
        return self.view

    def set_record(self, record: dict[str, Any] | None) -> None:
        self._generation += 1
        generation = self._generation
        self._model = build_result_summary(record)
        self._render()
        if not supports_symbolic_steps(record):
            return
        record_copy = dict(record or {})
        run_in_background(
            self._thread_pool,
            lambda: build_symbolic_steps(record_copy),
            on_result=lambda steps: self._finish_steps(generation, steps),
            on_error=lambda _error: self._finish_steps(generation, []),
        )

    def clear(self) -> None:
        self.set_record(None)

    def set_text(self, text: dict[str, object]) -> None:
        self._text = dict(text)
        self._render()

    def set_theme(self, theme_name: str) -> None:
        self._theme_name = str(theme_name)
        self._render()

    def scroll_to_steps(self) -> None:
        self._queue_script("window.resultWorkspace.scrollToSteps();")

    def _finish_steps(self, generation: int, steps: object) -> None:
        if generation != self._generation:
            return
        self._model["steps"] = list(steps) if isinstance(steps, list) else []
        self._model["steps_state"] = "available" if self._model["steps"] else "unavailable"
        self._render()

    def _labels(self) -> dict[str, str]:
        keys = (
            "exact_result",
            "integral_result",
            "total_time",
            "integration_steps",
            "no_result",
            "not_available",
            "comparison_complete",
            "steps_loading",
            "steps_unavailable",
            "fundamental_theorem",
            "step_setup",
            "step_antiderivative",
            "step_bounds",
            "step_substitute",
            "step_simplify",
            "step_verify",
            "step_improper_limit",
        )
        return {key: str(self._text.get(key, key.replace("_", " ").title())) for key in keys}

    def _render(self) -> None:
        payload = {
            "model": self._model,
            "labels": self._labels(),
            "theme": self._theme_name,
        }
        self._queue_script(
            "window.resultWorkspace.setData(%s);" % json.dumps(payload, ensure_ascii=False)
        )

    def _queue_script(self, script: str) -> None:
        if self._ready:
            self.view.page().runJavaScript(script)
        else:
            self._pending_script = script

    def _load_finished(self, ok: bool) -> None:
        self._ready = bool(ok)
        if self._ready:
            script = self._pending_script
            self._pending_script = None
            if script:
                self.view.page().runJavaScript(script)
            else:
                self._render()


__all__ = ["ResultWorkspace"]
