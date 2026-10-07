"""
Project-local numerical engine.

NumPy's compiled extension modules require the package name ``numpy`` at
runtime, so the vendored backend remains in ``Main/numpy``. This module is the
calculator-owned entry point used by app code.
"""

from importlib import import_module

from local_source_paths import prefer_compatible_numpy

prefer_compatible_numpy()
_backend = import_module("numpy")

__version__ = _backend.__version__
backend = _backend


def __getattr__(name):
    return getattr(_backend, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_backend)))
