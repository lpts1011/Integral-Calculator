"""
.. deprecated:: 1.6

   sympy.utilities.runtests has been renamed to sympy.testing.runtests.
"""

from solving.utilities.exceptions import sympy_deprecation_warning

sympy_deprecation_warning("The sympy.utilities.runtests submodule is deprecated. Use sympy.testing.runtests instead.",
    deprecated_since_version="1.6",
    active_deprecations_target="deprecated-sympy-utilities-submodules")

from solving.testing.runtests import * # noqa: F401,F403
