"""Implementation of :class:`PythonFiniteField` class. """


from solving.polys.domains.finitefield import FiniteField
from solving.polys.domains.pythonintegerring import PythonIntegerRing

from solving.utilities import public

@public
class PythonFiniteField(FiniteField):
    """Finite field based on Python's integers. """

    alias = 'FF_python'

    def __init__(self, mod, symmetric=True):
        super().__init__(mod, PythonIntegerRing(), symmetric)
