"""Implementation of :class:`GMPYFiniteField` class. """


from solving.polys.domains.finitefield import FiniteField
from solving.polys.domains.gmpyintegerring import GMPYIntegerRing

from solving.utilities import public

@public
class GMPYFiniteField(FiniteField):
    """Finite field based on GMPY integers. """

    alias = 'FF_gmpy'

    def __init__(self, mod, symmetric=True):
        super().__init__(mod, GMPYIntegerRing(), symmetric)
