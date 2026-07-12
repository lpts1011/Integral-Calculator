# Changelog

All notable project changes are recorded here. Versions follow Semantic Versioning.

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
