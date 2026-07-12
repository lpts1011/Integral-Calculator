# Integral Calculator C++

This directory contains the native C++ implementation of Integral Calculator.
It does not import or execute the Python version.

## Current implementation

- Qt 6 desktop interface with basic, advanced, and improper integral tabs
- Native real-time integral preview that updates with the function, parameters,
  and limits
- Native expression parsing through vendored muParser
- Rectangle, trapezoidal, Simpson, Simpson 3/8, Romberg, Gauss-Legendre,
  adaptive Simpson, and Monte Carlo integration
- Infinite interval transformations for adaptive Simpson integration
- Parameter assignments such as `a=2, b=pi`
- Split interval numerical integration
- Native function plotting with `QPainter`
- Calculation history, Markdown export, light/dark themes, and asynchronous work
- Initial native symbolic antiderivative rules for constants, powers, sine,
  cosine, exponential functions, and sums of supported terms
- Basic-tab exact-result dialog and tab-level reset controls
- Native Math Tools window for geometry, transforms, Taylor approximation,
  convergence, function analysis, multiple integrals, and sensitivity
- Persistent favorites, function templates, method recommendations, history
  refill, usage instructions, and Markdown/LaTeX export
- A self-contained macOS application at `Integral Calculator C++.app`

## Build on macOS

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/homebrew/opt/qtbase
cmake --build build --config Release -j
ctest --test-dir build --output-on-failure
open "Integral Calculator C++.app"
```

## Parity policy

The Python implementation in `../versionpython` remains the reference behavior.
Every C++ feature should receive parity tests before it is considered complete.
The remaining major work is broad symbolic parity for advanced integration,
ODE, Laplace, Fourier, multivariable tools, and all translated interface text.
