"""Cancellable isolated calculations with UI-thread result delivery."""
import threading
from PySide6.QtCore import QObject, QThreadPool, Signal
from qt_async import run_in_background
from symbolic_service import run_isolated


class JobRunner(QObject):
    busy_changed = Signal(bool)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.busy=False; self.closed=False; self._cancel=None; self._generation=0

    def cancel(self):
        if self._cancel is not None:
            self._cancel.set()

    def close(self,*_args):
        self.closed=True; self._generation+=1; self.cancel()

    def submit(self,function,args,on_result,on_error,timeout=8):
        if self.busy or self.closed:
            return None
        self.busy=True; self.busy_changed.emit(True)
        self._cancel=threading.Event(); cancellation=self._cancel
        self._generation+=1; generation=self._generation
        def deliver(callback,value):
            if not self.closed and generation == self._generation:
                callback(value)
        def finished():
            if not self.closed and generation == self._generation:
                self.busy=False; self.busy_changed.emit(False)
        return run_in_background(QThreadPool.globalInstance(),
            lambda:run_isolated(function,tuple(args),timeout,cancellation),
            on_result=lambda value:deliver(on_result,value),
            on_error=lambda error:deliver(on_error,error),on_finished=finished)
