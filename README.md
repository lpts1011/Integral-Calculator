# Integration Calculator GUI

A Python-based graphical integration calculator built with **Tkinter**, **SymPy**, **SciPy**, **NumPy**, and **Matplotlib**. This project is designed for educational and exploratory use in calculus and numerical analysis. It supports symbolic integration, numerical integration, improper integrals, real-time plotting, multilingual UI, calculation history, method recommendations, friendly error handling, favorite functions, theme switching, and readable mathematical result formatting.

## Features

### Symbolic Integration

- Indefinite integrals
- Definite integrals with exact closed-form results when available
- Automatic simplification using SymPy
- Process-based timeout protection for long symbolic computations
- Graceful fallback when no closed-form result is found
- Exact result preservation with a **View Exact Result** option

### Numerical Integration

Supported numerical methods include:

- Rectangle Rule
- Trapezoidal Rule
- Simpson’s Rule
- Simpson 3/8 Rule
- Romberg Integration
- Gaussian Quadrature
- Adaptive Simpson / `scipy.integrate.quad`
- Stratified Monte Carlo Integration

Some methods also provide error estimates where available.

### Improper Integrals

- Supports infinite limits using `inf` and `-inf`
- Symbolic convergence checking when possible
- Clear handling of exact, divergent, and unevaluated cases

### Plotting

- Embedded Matplotlib graph
- Interactive Matplotlib navigation toolbar
- Function plotting over finite intervals
- Shaded integral area for definite integrals
- Light and dark plot themes

### Smart Method Recommendation

The advanced integration tab can recommend a suitable method based on:

- Finite vs. infinite interval
- Missing or invalid limits
- Singularities
- Oscillatory behavior
- Non-finite sampled values
- Steep local variation
- Smooth nonlinear functions
- Polynomial-like functions

### User Experience

- Calculation time display
- Friendlier error messages with input-specific suggestions
- Favorite/common function insertion
- Saved custom favorite functions
- Calculation history with structured records
- Single-click history refill
- Double-click history refill and recompute

### Multilingual Interface

Supported languages:

- English
- Simplified Chinese
- Traditional Chinese
- Japanese
- Korean
- Spanish
- French
- Arabic
- Hindi

## Supported Mathematical Input

### Functions and Constants

Examples:

```text
sin(x)
cos(x)
tan(x)
ln(x)
log(x)
log10(x)
sqrt(x)
exp(x)
x^2
1/(1+x^2)
exp(-x^2)
```

Constants and special values:

```text
pi
e
inf
-inf
```

### Implicit Multiplication

The parser supports implicit multiplication through SymPy’s official parser:

```text
2x      -> 2*x
2pi     -> 2*pi
2(x+1)  -> 2*(x+1)
```

## Result Display Policy

The calculator separates mathematical precision from UI readability:

- Short exact symbolic results are displayed directly.
- Long or complex symbolic expressions are shown as numerical approximations.
- Exact symbolic forms are preserved internally.
- Unevaluated symbolic results are reported clearly.
- Numerical approximations use the `≈` symbol.

## Project Structure

```text
Integral_Calculator.py      # Safe launcher / entry point
app_gui.py                  # Main application coordinator
main_window.py              # Main window, notebook, toolbar, history panel
tab1_basic.py               # Basic integration tab
tab2_advanced.py            # Advanced symbolic/numerical integration tab
tab3_improper.py            # Improper integral tab
parser_utils.py             # Safe SymPy parser
symbolic_methods.py         # Symbolic integration logic and timeout handling
numeric_methods.py          # Numerical integration methods
tab2_logic.py               # Tab 2 calculation logic
plot_utils.py               # Matplotlib plotting helpers
formatting.py               # Result formatting helpers
i18n.py                     # Multilingual UI text
language_ui.py              # Usage instruction window
recommendation_utils.py     # Method recommendation logic
error_utils.py              # Friendly error messages
favorites_store.py          # Saved favorite functions
theme_utils.py              # Light/Dark theme support
progress_utils.py           # Progress bar controller
history_utils.py            # History record helper
tests/                      # Unit tests
```

## Requirements

Python 3.10 or later is recommended.

Install dependencies:

```bash
pip install numpy sympy scipy matplotlib
```

## Running the Application

From the project directory, run:

```bash
python Integral_Calculator.py
```

## Running Tests

The project includes a `unittest`-based test suite.

Run:

```bash
python -m unittest discover -s tests
```

Current tests cover:

- Expression parsing
- Numerical integration
- Symbolic integration
- Tab 2 calculation logic
- Method recommendation logic
- Multilingual UI key coverage

## Example Inputs

```text
x^2
sin(x)
exp(-x)
exp(-x^2)
1/(1+x^2)
sqrt(1-x^2)
log(x)
```

Example definite integral:

```text
Function: x^2
Lower limit: 0
Upper limit: 1
Result: 1/3
```

Example improper integral:

```text
Function: exp(-x)
Lower limit: 0
Upper limit: inf
Result: 1
```

## Purpose

This project is intended to be both a useful calculator and a learning tool. It demonstrates how symbolic mathematics, numerical analysis, plotting, GUI design, multilingual UI, and testing can be combined in a single Python desktop application.

## License

This project is for educational use. You may add a license file such as the MIT License if you plan to publish or share it publicly.
