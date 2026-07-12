"""
Rational number type based on Python integers.

The PythonRational class from here has been moved to
sympy.external.pythonmpq

This module is just left here for backwards compatibility.
"""


from solving.core.numbers import Rational
from solving.core.sympify import _sympy_converter
from solving.utilities import public
from solving.external.pythonmpq import PythonMPQ


PythonRational = public(PythonMPQ)


def sympify_pythonrational(arg):
    return Rational(arg.numerator, arg.denominator)
_sympy_converter[PythonRational] = sympify_pythonrational
