# Changelog

All notable project changes are recorded here. Versions use two-part `MAJOR.MINOR`
numbers, and release tags are named `vMAJOR.MINOR`. The major number changes only
when the program changes substantially:

| Major | Edition | What changed |
| --- | --- | --- |
| 6 | Integrated Edition | One calculator screen, four Math Tools, two languages |
| 5 | Detailed Edition | Reliable numerical engine with full diagnostics, many tools, nine languages |
| 4 | | Complete source in the repository and the live math editor |
| 3 | | Math Tools workspace, first macOS app, bundled math engine |
| 2 | | Multi-module application with three integration tabs and tests |
| 1 | | Single-file Python program |

Releases before 4.0 were renumbered on 2026-11-03 so that each major number marks
one generation: 2.0–2.6 became 1.1–1.7, 2.7–2.9 became 2.0–2.2, 3.1-beta became
3.0-beta, 3.1 became 3.0, and 3.2 became 3.1.

## [6.1] - 2026-11-04 — Integrated Edition

### Changed

- Math Tools results are typeset as formulas, like the main result panel, with
  fractions written one above the other. One result area below the tools shows the
  open tool's latest result.
- Substitution uses the positive branch, so u = x² gives x(u) = √u.

### Fixed

- Numerical fallback and Math Tools area calculations now use the checked finite
  numerical engine, retaining narrow-peak detection, piecewise splits and support
  for integrable endpoint singularities.
- Numerical fallback observes cancellation; improper fallback also has evaluation
  and time budgets. A divergent endpoint such as ∫₀¹ 1/x dx now gives the same
  plain "the integral may diverge" message as a divergent infinite limit.
- Reversing limits preserves geometric areas, arc lengths and disk volumes, while
  the signed integral still changes sign (and a zero result shows 0, not -0).
- Arc length without a closed form said "no closed form" in English in every
  language; it now explains in the chosen language that the numerical value is
  shown below.

## [6.0] - 2026-11-03 — Integrated Edition

### Changed

- One calculator screen replaces the Basic, Advanced, and Improper tabs. **Auto**
  gives the exact answer when one exists (including infinite limits and divergence)
  and a number otherwise; **More options** holds the numerical method and
  **Compare Methods**.
- The result panel is the single place results appear; it now also says when an
  improper integral diverges. Progress and **Cancel** appear only while a
  calculation runs.
- Math Tools is one list of four tools: Area, Polar Area, Arc Length & Volume, and
  Integration Techniques. Editors grow to fit their fields.
- The interface is complete in English and Simplified Chinese, including Math
  Tools, graph labels, history entries, and the theme menu. Graphs use a Chinese
  font when one is installed.

### Fixed

- Switching the language or theme, or panning the graph, no longer closes the app
  on recent macOS versions (Qt crashed while drawing the busy and move cursors).
- Exact results are simplified, so ∫ sin(x²) dx is √2·√π·S(√2·x/√π)/2 instead of
  a long expression with gamma functions, and results that use special functions
  are shown as typeset formulas instead of plain text.
- When an exact value needs special functions or is long, **Auto** shows the
  numerical value instead. When no exact form is found in time, including for
  infinite limits, **Auto** gives the numerical value instead of an error.
- History entries no longer show "= ≈" before approximate values.

### Removed

- Tolerance, budget, Gaussian-order, seed, step-size, and split-point inputs; the
  numerical engine keeps its defaults and automatic breakpoints.
- Method recommendations and the "Apply Recommendation" button (Auto already
  chooses), the "View Exact Result" pop-up, and the duplicate result line.
- Math Tools pages that repeated other features or went beyond single integrals:
  Average Value, Convergence Table, Convergence, Error Plot, Analysis, Sensitivity,
  Double Integral, Multiple Integrals, Taylor Series, Fourier/Laplace/ODE, Verify
  Antiderivative, Parameter Slider, and Piecewise Builder.
- The Signal Integration workspace (CSV import, noise/drift, convolution, Fourier
  reconstruction) and its example data.
- Traditional Chinese, Japanese, Korean, Spanish, French, Arabic, and Hindi, which
  were only partly translated.

## [5.1] - 2026-11-03 — Detailed Edition

### Changed

- Faster numerical integration: cached oscillation and narrow-peak analysis per
  expression, a direct scalar path for adaptive quadrature nodes, one NumPy
  error-state context per integration, and cached engine attribute lookups.
  A mixed 110-integration workload runs about 4.7× faster and method comparison
  about 2.3× faster, with bit-identical results.
- Faster graph rendering: vectorized zero-crossing search, area shading without
  per-region interpolation, and fixed legend placement for dense plots. Plots of
  high-frequency functions render about 5× faster; ordinary plots are unchanged.
- Faster start: SciPy loads where it is used, and the symbolic worker warms up in
  the background after the window opens, so the first exact answer takes about
  57 ms instead of 370 ms.
- Version numbers, Git tags, release titles, and download file names now use
  two-part names (`v5.0`, `v4.1`, `v3.1-beta`, …).

### Removed

- The C++ edition (`cpp/`) and its CI job; the project is now Python-only.
- The standalone single-file launcher generator (`build_standalone.py`) and its
  payload-parity test.
- Unused numerical helpers (`composite_simpson_38`, `romberg_custom`,
  `monte_carlo_stratified`), an unused plotting helper, a duplicate plot-theme
  function, an obsolete symbolic worker, unused attributes, and unused imports.

## [5.0] - 2026-10-08 — Detailed Edition

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
- Rebuilt Python macOS app and standalone bundle as v5.0. C++ algorithms remain
  unchanged; new Python features are documented as not yet ported.

## [4.0] - 2026-07-13

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
