# Python and C++ parity checklist

The Python implementation in `../versionpython` is the reference behavior.
A feature is complete only when its C++ behavior and tests match that reference.

Status values:

- `Complete`: available in C++ with equivalent core behavior
- `Partial`: usable in C++, but some Python behavior is still missing
- `Missing`: not yet implemented in C++

## Primary integration workflow

| Python feature | C++ status | Remaining work |
| --- | --- | --- |
| Basic integration input layout | Complete | Continue visual refinement during parity testing |
| Real-time rendered integral preview | Complete | Expand rich formatting for complex nested fractions |
| Parameters in expressions | Complete | Add more parser compatibility cases |
| Basic definite integration | Partial | Native symbolic coverage is smaller than Python |
| Basic indefinite integration | Partial | Native symbolic coverage is smaller than Python |
| View Exact Result | Complete | Add localized dialog text |
| Advanced symbolic integration | Partial | Port the full symbolic rule set and timeout behavior |
| Advanced numerical integration | Complete | Add broader cross-version numerical fixtures |
| Eight numerical methods | Complete | Match every Python error estimate and edge case |
| Manual split points | Complete | Add split-point markers to the plot |
| Automatic piecewise breakpoints | Missing | Port discontinuity and breakpoint analysis |
| Method recommendation | Complete | Continue tuning recommendation heuristics against Python fixtures |
| Method comparison | Partial | Replace text output with the Python-style result table |
| Improper integration | Partial | Add symbolic convergence and divergence classification |
| Background calculations | Complete | Add user cancellation and symbolic timeout controls |
| Function plotting | Partial | Add split markers and all Python plot-state behavior |

## Application workflow

| Python feature | C++ status | Remaining work |
| --- | --- | --- |
| Calculation history | Complete | Continue visual parity checks |
| Markdown export | Partial | Match the full Python record format and comparison tables |
| LaTeX export | Partial | Expand exact mathematical formatting for every record type |
| Detailed calculation steps | Partial | Add expression-specific symbolic derivations |
| Input suggestions | Complete | Continue adding parser correction fixtures |
| Usage instructions | Complete | Finish full localized text |
| Persistent favorites | Complete | Continue cross-platform storage tests |
| Function templates | Complete | Port any additional Python templates as they are added |
| Light and dark themes | Complete | Continue visual parity checks |
| Nine language dictionaries | Partial | Language selection and primary titles exist; translate every remaining control and message |

## Mathematical tools

| Python tool | C++ status |
| --- | --- |
| Polar area | Complete |
| Taylor expansion | Partial |
| Convergence table | Complete |
| Function and singularity analysis | Partial |
| Piecewise expression builder | Complete |
| Parameter slider | Partial |
| Average value and signed/unsigned area | Complete |
| Substitution helper | Partial |
| Integration by parts helper | Partial |
| Arc length and volume of revolution | Complete |
| Fourier series | Complete |
| Laplace transform | Partial |
| ODE solver | Partial |
| Improper-integral convergence report | Partial |
| Numerical error profile and plot | Partial |
| Double, variable-bound double, polar, and triple integrals | Complete |
| Parameter sensitivity | Complete |
| Antiderivative verification | Complete |

## Packaging

| Target | C++ status | Remaining work |
| --- | --- | --- |
| Native macOS application | Complete | Developer ID signing and notarization are release tasks |
| Windows application | Missing | Add a Windows build and deployment workflow |
