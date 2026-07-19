# Integral Calculator

Integral Calculator is a desktop calculus application available in two native project editions:

- **Python edition**: the actively developed PySide6 reference implementation
  with the broadest symbolic-mathematics coverage.
- **C++ edition**: a Qt 6 implementation focused on native execution speed and a self-contained macOS application.

Both editions provide basic, advanced, and improper integration workflows, numerical methods, plotting, calculation history, mathematical tools, themes, and multilingual interface support. The C++ edition implements the same feature categories, while some advanced symbolic expressions can still produce different forms or numerical fallbacks. See [`cpp/PARITY.md`](cpp/PARITY.md) for the precise parity status.

## Highlights

- Definite and indefinite integration
- Improper integrals with infinite limits
- Rectangle, trapezoidal, Simpson, Simpson 3/8, Romberg, Gaussian quadrature, adaptive Simpson, and Monte Carlo methods
- Directly editable, typeset mathematical input fields
- Floating function-focused mathematical keyboard
- Function parameters and manual split points
- Function plotting with human-readable mathematical notation and calculation history
- Rendered exact results, numerical results, total time, and symbolic steps
- Method recommendations and comparison
- Input suggestions, light/dark themes, and multilingual controls
- Mathematical tools for Taylor and Fourier approximations, Laplace transforms, ODEs, geometry, convergence, error analysis, multiple integrals, and parameter sensitivity
- English, Simplified Chinese, Traditional Chinese, Spanish, French, Japanese, Korean, Arabic, and Hindi interface options

## Repository Layout

```text
python/   Python reference implementation and project-local math runtimes
cpp/      Native C++20 and Qt 6 implementation
```

Generated applications and standalone bundles are distributed through GitHub Releases rather than committed to the source tree.

## Python Edition

### Run

```bash
cd python
python3 Integral_Calculator.py
```

The repository includes the project-local `solving`, `calengine`, and trimmed NumPy runtime used by this edition. The checked-in native numerical extensions target macOS and supported Python versions; Windows users should follow [`python/PACKAGING.md`](python/PACKAGING.md).

### Test

```bash
cd python
python3 run_tests.py
```

The current suite contains 142 tests covering parsing, numerical and symbolic
integration, mathematical tools, recommendations, internationalization,
PySide6 workflows, and real Qt WebEngine rendering.

## C++ Edition

### Requirements

- CMake 3.24 or later
- A C++20 compiler
- Qt 6.5 or later with Widgets and Concurrent

On macOS with Homebrew:

```bash
brew install cmake qt
```

### Build and Test

```bash
cd cpp
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/opt/homebrew/opt/qtbase
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

The expression parser is vendored under `cpp/third_party/muparser`; the C++ application does not execute Python or import the Python edition.

## Releases

Release tags follow [Semantic Versioning](https://semver.org/) and use the `vMAJOR.MINOR.PATCH` format. Release assets may include:

- Python macOS application
- C++ macOS application
- Python standalone bundle
- GitHub-generated source archives

## Project Status

Version 4.0.0 introduced the dual Python/C++ repository. Active development now
focuses on the Python edition, which remains the behavioral reference for
advanced symbolic mathematics. The C++ edition remains available at its v4
parity baseline, with its limitations documented rather than overstated.

## License

Original project code is available under the [MIT License](LICENSE). Vendored dependencies retain their own licenses and notices, including the files under `python/THIRD_PARTY_NOTICES` and `cpp/third_party/muparser`.
