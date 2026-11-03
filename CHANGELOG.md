# Changelog

All notable project changes are recorded here. Versions follow Semantic Versioning.

## [5.0.1] - 2026-11-03

### Changed

- Faster numerical integration: cached oscillation and narrow-peak analysis per
  expression, a direct scalar path for adaptive quadrature nodes, one NumPy
  error-state context per integration, and cached engine attribute lookups.
  A mixed 110-integration workload runs about 4.7× faster and method comparison
  about 2.3× faster, with bit-identical results.
- Faster graph rendering: vectorized zero-crossing search, area shading without
  per-region interpolation, and fixed legend placement for dense plots. Plots of
  high-frequency functions render about 5× faster; ordinary plots are unchanged.

### Removed

- Unused numerical helpers (`composite_simpson_38`, `romberg_custom`,
  `monte_carlo_stratified`), an unused plotting helper, a duplicate plot-theme
  function, an obsolete symbolic worker, unused attributes, and unused imports.

## [5.0.0] - 2026-10-08

### Added

- Python signal workspace: CSV samples, cumulative integration, mean/RMS/energy,
  noise/bias drift experiments, direct versus FFT convolution, and Fourier reconstruction.
- Auto selection, adaptive Gauss–Kronrod and weighted oscillatory integration;
  error tolerances, calculation budgets, cancellation, and evaluation diagnostics.
- Reproducible integration benchmarks, analytic-reference fixtures, sample CSV,
  and engineering workflow documentation.
- Reusable isolated worker with timeout/cancellation recovery and large-result transport.
- Root Windows CI/build workflow and portable installed-NumPy fallback.

### Fixed

- Infinite enumeration of periodic singularity sets and blocking recommendations.
- False Romberg convergence for aliased high-frequency grids and missed quadratic
  exponential narrow peaks.
- Rejected integrable endpoint singularities, false plotted zeros at poles,
  and unbounded allocations from tiny steps.
- Convergence tables whose displayed sample count did not control the algorithm.
- Deterministic segment error aggregation, independent Monte Carlo segment seeds,
  and global tolerance checks.
- Piecewise boundary values in closed-node rules and ambiguous comparison accuracy.

### Changed

- Moved mathematical tools to cancellable background jobs; reused compiled
  functions, quadrature nodes, parsed parameter expressions, and symbolic work.
- Synchronized existing offline MathLive/Qt interface and packaging improvements;
  removed retired Tkinter production modules.
- Rebuilt Python macOS app and standalone bundle as v5.0.0. C++ algorithms remain
  unchanged; new Python features are documented as not yet ported.

## [4.0.0] - 2026-07-13

### Added

- Introduced a native C++20 and Qt 6 edition alongside the Python reference edition.
- Added a native real-time integral preview and Python-style basic integration layout to C++.
- Added eight numerical integration methods, infinite-interval transformations, split intervals, plotting, history, themes, export, and background calculations to C++.
- Added native C++ mathematical tools for Taylor and Fourier approximations, Laplace transforms, first-order ODEs, convergence and error analysis, geometry, multiple integrals, sensitivity, and antiderivative verification.
- Added C++ favorites, templates, recommendations, history refill, suggestions, usage instructions, Markdown/LaTeX export, and nine language selectors.
- Added C++ core and preview-update tests.

### Changed

- Reorganized the repository into `python/` and `cpp/` source directories.
- Replaced historical nonstandard tags with the `vMAJOR.MINOR.PATCH` convention.
- Moved generated applications and standalone bundles out of Git history and into Release assets.
- Rewrote the README for the dual-language project and documented C++ parity limitations.

### Verified

- Python: 45 tests passed.
- Python standalone bundle: self-test passed.
- C++: core and live-preview tests passed.
- C++ macOS Release application: packaged and visually verified.

## Historical Releases

### 3.2 - 2026-06-07

- Localized the project-owned symbolic and numerical runtimes.
- Added parsing and numerical caches, removed unused vendored modules, and rebuilt the macOS bundle.

### 3.1 - 2026-06-02

- Added the first macOS `.app` distribution and expanded Math Tools.

### 2.9 - 2026-06-01

- Added parameters, split-point integration, method comparison, improved plotting, and Markdown/LaTeX export.

### 2.0-2.8 - 2026-01-31 to 2026-05-31

- Developed multilingual support, numerical methods, exact-result handling, history interaction, live preview, error estimates, recommendations, favorites, themes, testing, and the modular Python architecture.
