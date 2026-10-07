"""Small Qt worker primitives shared by the Qt application layer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by a background calculation."""

    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class Worker(QRunnable):
    """Execute a no-argument callable on a Qt thread-pool thread."""

    def __init__(self, function: Callable[[], Any]):
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.result.emit(self.function())
        except Exception as exc:
            self.signals.error.emit(exc)
        finally:
            self.signals.finished.emit()


def run_in_background(
    pool: QThreadPool,
    callable: Callable[[], Any],
    on_result: Callable[[Any], Any] | None = None,
    on_error: Callable[[Exception], Any] | None = None,
    on_finished: Callable[[], Any] | None = None,
) -> Worker:
    """Create, connect, and start one worker on ``pool``.

    The pool keeps a Python reference to the worker until its finished signal
    has run.  This is important because Qt owns the QRunnable lifetime while
    Python owns the signal object and callback connections.
    """

    worker = Worker(callable)
    live_workers = getattr(pool, "_integral_calculator_workers", None)
    if live_workers is None:
        live_workers = []
        setattr(pool, "_integral_calculator_workers", live_workers)
    live_workers.append(worker)

    if on_result is not None:
        worker.signals.result.connect(on_result)
    if on_error is not None:
        worker.signals.error.connect(on_error)
    if on_finished is not None:
        worker.signals.finished.connect(on_finished)

    def release_worker() -> None:
        if worker in live_workers:
            live_workers.remove(worker)

    worker.signals.finished.connect(release_worker)
    try:
        pool.start(worker)
    except Exception:
        release_worker()
        raise
    return worker


__all__ = ["WorkerSignals", "Worker", "run_in_background"]
