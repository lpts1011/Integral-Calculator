"""A functions module, includes all the standard functions.

Combinatorial - factorial, fibonacci, harmonic, bernoulli...
Elementary - hyperbolic, trigonometric, exponential, floor and ceiling, sqrt...
Special - gamma, zeta,spherical harmonics...
"""

from solving.functions.combinatorial.factorials import (factorial, factorial2,
        rf, ff, binomial, RisingFactorial, FallingFactorial, subfactorial)
from solving.functions.combinatorial.numbers import (carmichael, fibonacci, lucas, tribonacci,
        harmonic, bernoulli, bell, euler, catalan, genocchi, andre, partition, divisor_sigma,
        udivisor_sigma, legendre_symbol, jacobi_symbol, kronecker_symbol, mobius,
        primenu, primeomega, totient, reduced_totient, primepi, motzkin)
from solving.functions.elementary.miscellaneous import (sqrt, root, Min, Max,
        Id, real_root, cbrt, Rem)
from solving.functions.elementary.complexes import (re, im, sign, Abs,
        conjugate, arg, polar_lift, periodic_argument, unbranched_argument,
        principal_branch, transpose, adjoint, polarify, unpolarify)
from solving.functions.elementary.trigonometric import (sin, cos, tan,
        sec, csc, cot, sinc, asin, acos, atan, asec, acsc, acot, atan2)
from solving.functions.elementary.exponential import (exp_polar, exp, log,
        LambertW)
from solving.functions.elementary.hyperbolic import (sinh, cosh, tanh, coth,
        sech, csch, asinh, acosh, atanh, acoth, asech, acsch)
from solving.functions.elementary.integers import floor, ceiling, frac
from solving.functions.elementary.piecewise import (Piecewise, piecewise_fold,
                                                  piecewise_exclusive)
from solving.functions.special.error_functions import (erf, erfc, erfi, erf2,
        erfinv, erfcinv, erf2inv, Ei, expint, E1, li, Li, Si, Ci, Shi, Chi,
        fresnels, fresnelc)
from solving.functions.special.gamma_functions import (gamma, lowergamma,
        uppergamma, polygamma, loggamma, digamma, trigamma, multigamma)
from solving.functions.special.zeta_functions import (dirichlet_eta, zeta,
        lerchphi, polylog, stieltjes, riemann_xi)
from solving.functions.special.tensor_functions import (Eijk, LeviCivita,
        KroneckerDelta)
from solving.functions.special.singularity_functions import SingularityFunction
from solving.functions.special.delta_functions import DiracDelta, Heaviside
from solving.functions.special.bsplines import bspline_basis, bspline_basis_set, interpolating_spline
from solving.functions.special.bessel import (besselj, bessely, besseli, besselk,
        hankel1, hankel2, jn, yn, jn_zeros, hn1, hn2, airyai, airybi, airyaiprime, airybiprime, marcumq)
from solving.functions.special.hyper import hyper, meijerg, appellf1
from solving.functions.special.polynomials import (legendre, assoc_legendre,
        hermite, hermite_prob, chebyshevt, chebyshevu, chebyshevu_root,
        chebyshevt_root, laguerre, assoc_laguerre, gegenbauer, jacobi, jacobi_normalized)
from solving.functions.special.spherical_harmonics import Ynm, Ynm_c, Znm
from solving.functions.special.elliptic_integrals import (elliptic_k,
        elliptic_f, elliptic_e, elliptic_pi)
from solving.functions.special.beta_functions import beta, betainc, betainc_regularized
from solving.functions.special.mathieu_functions import (mathieus, mathieuc,
        mathieusprime, mathieucprime)
ln = log

__all__ = [
    'factorial', 'factorial2', 'rf', 'ff', 'binomial', 'RisingFactorial',
    'FallingFactorial', 'subfactorial',

    'carmichael', 'fibonacci', 'lucas', 'motzkin', 'tribonacci', 'harmonic',
    'bernoulli', 'bell', 'euler', 'catalan', 'genocchi', 'andre', 'partition',
    'divisor_sigma', 'udivisor_sigma', 'legendre_symbol', 'jacobi_symbol', 'kronecker_symbol',
    'mobius', 'primenu', 'primeomega', 'totient', 'reduced_totient', 'primepi',

    'sqrt', 'root', 'Min', 'Max', 'Id', 'real_root', 'cbrt', 'Rem',

    're', 'im', 'sign', 'Abs', 'conjugate', 'arg', 'polar_lift',
    'periodic_argument', 'unbranched_argument', 'principal_branch',
    'transpose', 'adjoint', 'polarify', 'unpolarify',

    'sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'sinc', 'asin', 'acos', 'atan',
    'asec', 'acsc', 'acot', 'atan2',

    'exp_polar', 'exp', 'ln', 'log', 'LambertW',

    'sinh', 'cosh', 'tanh', 'coth', 'sech', 'csch', 'asinh', 'acosh', 'atanh',
    'acoth', 'asech', 'acsch',

    'floor', 'ceiling', 'frac',

    'Piecewise', 'piecewise_fold', 'piecewise_exclusive',

    'erf', 'erfc', 'erfi', 'erf2', 'erfinv', 'erfcinv', 'erf2inv', 'Ei',
    'expint', 'E1', 'li', 'Li', 'Si', 'Ci', 'Shi', 'Chi', 'fresnels',
    'fresnelc',

    'gamma', 'lowergamma', 'uppergamma', 'polygamma', 'loggamma', 'digamma',
    'trigamma', 'multigamma',

    'dirichlet_eta', 'zeta', 'lerchphi', 'polylog', 'stieltjes', 'riemann_xi',

    'Eijk', 'LeviCivita', 'KroneckerDelta',

    'SingularityFunction',

    'DiracDelta', 'Heaviside',

    'bspline_basis', 'bspline_basis_set', 'interpolating_spline',

    'besselj', 'bessely', 'besseli', 'besselk', 'hankel1', 'hankel2', 'jn',
    'yn', 'jn_zeros', 'hn1', 'hn2', 'airyai', 'airybi', 'airyaiprime',
    'airybiprime', 'marcumq',

    'hyper', 'meijerg', 'appellf1',

    'legendre', 'assoc_legendre', 'hermite', 'hermite_prob', 'chebyshevt',
    'chebyshevu', 'chebyshevu_root', 'chebyshevt_root', 'laguerre',
    'assoc_laguerre', 'gegenbauer', 'jacobi', 'jacobi_normalized',

    'Ynm', 'Ynm_c', 'Znm',

    'elliptic_k', 'elliptic_f', 'elliptic_e', 'elliptic_pi',

    'beta', 'betainc', 'betainc_regularized',

    'mathieus', 'mathieuc', 'mathieusprime', 'mathieucprime',
]
