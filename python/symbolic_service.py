"""Reusable isolated symbolic worker; terminate and replace it after a timeout."""
import atexit
import multiprocessing
import threading
import time

_LOCK = threading.Lock()
_PROCESS = None
_CONNECTION = None


def _serve(connection):
    connection.send(("ready", None))
    while True:
        try:
            function, args = connection.recv()
        except EOFError:
            break
        try:
            connection.send(("ok", function(*args)))
        except Exception as exc:
            connection.send(("error", str(exc)))
    connection.close()


def _stop():
    global _PROCESS, _CONNECTION
    if _CONNECTION is not None:
        _CONNECTION.close()
    if _PROCESS is not None:
        if _PROCESS.is_alive():
            _PROCESS.terminate()
        _PROCESS.join(1)
        if _PROCESS.is_alive():
            _PROCESS.kill(); _PROCESS.join(1)
    _PROCESS = _CONNECTION = None


def run_isolated(function, args, timeout=8, cancel=None):
    global _PROCESS, _CONNECTION
    while not _LOCK.acquire(timeout=.05):
        if cancel is not None and cancel.is_set():
            raise ValueError("Calculation cancelled.")
    try:
        if _PROCESS is None or not _PROCESS.is_alive():
            _stop()
            context = multiprocessing.get_context("spawn")
            _CONNECTION, child = context.Pipe()
            _PROCESS = context.Process(target=_serve,args=(child,),daemon=True)
            _PROCESS.start(); child.close()
            # Initialization has its own bounded allowance, outside the solve budget.
            started = time.monotonic()
            while not _CONNECTION.poll(.05):
                if time.monotonic()-started > 8:
                    raise TimeoutError("Symbolic worker initialization timed out.")
                if cancel is not None and cancel.is_set():
                    raise ValueError("Calculation cancelled.")
            _CONNECTION.recv()
        _CONNECTION.send((function,args))
        started = time.monotonic()
        while not _CONNECTION.poll(.025):
            if cancel is not None and cancel.is_set():
                raise ValueError("Calculation cancelled.")
            if time.monotonic()-started > timeout:
                raise TimeoutError(f"Symbolic integration exceeded {timeout} seconds. Try numerical integration or simplify the input.")
            if not _PROCESS.is_alive():
                raise RuntimeError("Symbolic worker exited without returning a result.")
        status, value = _CONNECTION.recv()
        if status != "ok":
            raise ValueError(value)
        return value
    except BaseException:
        _stop()
        raise
    finally:
        _LOCK.release()


atexit.register(_stop)
