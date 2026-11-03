# Integral Calculator

A desktop integral calculator with exact (symbolic) answers, reliable numerical
integration, interactive graphs, and step-by-step explanations.

**v6.0 Integrated Edition — One calculator screen.** Definite, indefinite, and
improper integrals share one screen that gives the exact answer when one exists
and a number otherwise. Math Tools is a short list of four tools, and the
interface is available in English and Simplified Chinese.

The previous generation, **v5.1 Detailed Edition**, keeps every advanced option,
the signal-analysis workspace, and nine languages; it is available from
[Releases](https://github.com/lpts1011/Integral-Calculator/releases/tag/v5.1).

## Highlights

- One screen for definite, indefinite, and improper (∞) integrals, with parameters
  such as `a=2`.
- **Auto** gives the exact result when possible; **More options** offers ten
  numerical methods (adaptive Gauss–Kronrod, oscillatory quadrature, adaptive
  Simpson, Romberg, Gaussian quadrature, fixed rules, and seeded Monte Carlo)
  and a side-by-side method comparison.
- Numerical results report the method, evaluation count, convergence status, and
  a clearly labeled error estimate.
- Structural narrow-peak detection, bounded periodic singularity search,
  integrable endpoint singularities, and protection against Romberg aliasing.
- Math Tools: area, polar area, arc length and volume, and integration techniques
  (substitution and integration by parts).
- Fully offline MathLive editor and math keyboard, adaptive graphs, history, and
  symbolic steps, in English or Simplified Chinese.

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
[python/PACKAGING.md](python/PACKAGING.md).

The Python suite includes integration, signal correctness, editor bridge, UI,
worker cancellation/recovery, and packaging tests.

## Releases

[GitHub Releases](https://github.com/lpts1011/Integral-Calculator/releases) contain
built applications and checksums. The v5 macOS artifact is
arm64 and ad-hoc signed, **not Apple-notarized**. Qt 6.11 requires macOS 13+.
Windows builds are available through the root Build Windows EXE workflow.
Generated binary artifacts stay outside Git history.

## License

Original project code uses the [MIT License](LICENSE). Vendored dependencies retain
their licenses in `python/THIRD_PARTY_NOTICES`.
