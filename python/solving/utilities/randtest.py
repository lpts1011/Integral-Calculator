"""
.. deprecated:: 1.6

   sympy.utilities.randtest has been renamed to sympy.core.random.
"""
from solving.utilities.exceptions import sympy_deprecation_warning

sympy_deprecation_warning("The sympy.utilities.randtest submodule is deprecated. Use sympy.core.random instead.",
    deprecated_since_version="1.6",
    active_deprecations_target="deprecated-sympy-utilities-submodules")

from solving.core.random import *  # noqa:F401,F403
