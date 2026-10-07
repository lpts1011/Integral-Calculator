# Integral Calculator

A desktop integral calculator with symbolic calculus, numerical error control,
interactive plots, and integration-based signal analysis.

**v5.0.0 — Signals & Reliable Integration** upgrades the Python edition. The
native C++ edition remains available at its existing feature scope; new Python
features have explicit status in [cpp/PARITY.md](cpp/PARITY.md).

## Python highlights

- Definite, indefinite, and improper integration; parameters and split intervals.
- Auto selection, adaptive Gauss–Kronrod, weighted oscillatory quadrature, actual
  adaptive Simpson, Romberg, Gaussian quadrature, fixed rules, and seeded Monte Carlo.
- Absolute/relative tolerances, work/time budgets, cancellation, evaluation counts,
  convergence status, and clearly labeled numerical error estimates.
- Structural narrow-peak detection, bounded periodic singularity search,
  integrable endpoint singularities, and protection against Romberg aliasing.
- Method comparison with repeated timings and independent accuracy references;
  convergence studies use real method parameters.
- Sampled signal CSV import, cumulative integration, mean, RMS, and energy.
- Reproducible noise/bias drift experiments, direct/FFT convolution, and Fourier
  reconstruction with error plots.
- Reusable isolated background calculations and cached numerical/symbolic work.
- Fully offline MathLive editor through Qt WebEngine; PySide6 interface, adaptive
  plots, history, exports, favorites, mathematical tools, and nine language choices.
  New controls have English fallbacks and primary Simplified Chinese labels.

See [python/docs/ENGINEERING.md](python/docs/ENGINEERING.md) for workflows,
algorithm limits, and reproducible benchmark evidence.

## Run and test

Use Python 3.13 or 3.14 in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements-ci.txt
cd python
python Integral_Calculator.py
python run_tests.py
python scripts/benchmark_integration.py
```

The project includes its local symbolic runtime. Bundled NumPy extensions target
compatible macOS Python ABIs; other source environments use the installed NumPy.
Desktop dependencies and builds are documented in
[python/PACKAGING.md](python/PACKAGING.md). The standalone launcher is a release
asset; it embeds the source and an Apple-silicon macOS runtime.

The Python suite includes integration, signal correctness, editor bridge, UI,
worker cancellation/recovery, and packaging tests. Standalone payload parity is
checked when the generated launcher is present beside the local source tree.

## C++ edition

The independent C++20/Qt 6 edition does not execute Python. On macOS:

```sh
brew install cmake qt
cd cpp
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$(brew --prefix qt)"
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Requirements: CMake 3.24+, C++20 compiler, Qt 6.5+ Widgets and Concurrent.
See [cpp/README.md](cpp/README.md) and [cpp/PARITY.md](cpp/PARITY.md).

## Releases

[GitHub Releases](https://github.com/lpts1011/Integral-Calculator/releases) contain
built applications, standalone bundles, and checksums. The v5 macOS artifact is
arm64 and ad-hoc signed, **not Apple-notarized**. Qt 6.11 requires macOS 13+.
Windows builds are available through the root Build Windows EXE workflow.
Generated binary artifacts stay outside Git history.

## License

Original project code uses the [MIT License](LICENSE). Vendored dependencies retain
their licenses in `python/THIRD_PARTY_NOTICES` and `cpp/third_party/muparser`.
