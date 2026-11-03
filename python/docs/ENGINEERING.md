# Reliable Integration — v6.0

This document describes how the calculator integrates numerically, what its
error reports mean, and how to reproduce the benchmark evidence.

## Numerical integration

With **Auto**, the calculator first looks for an exact result. When none exists,
or when **More options → Method** selects a numerical method, it integrates
numerically. The numerical engine's own automatic choice uses weighted
quadrature for a recognized single linear-phase sine/cosine factor and adaptive
Gauss–Kronrod otherwise. Numerical runs use fixed defaults: absolute and relative
tolerance 1e-8, at most 200,000 evaluations, and an 8-second budget. Fixed rules
use their default sample counts. Numerical methods require finite limits; Auto
handles infinite limits and reports divergence.

Adaptive Simpson now implements Simpson refinement; it is distinct from
Gauss–Kronrod. Romberg requires adequate oscillation resolution before accepting
agreement. Quadratic exponential peaks contribute analytic center/width
breakpoints, so a narrow Gaussian is not silently missed. Automatic piecewise
splits use the corresponding one-sided endpoint values for closed-node rules.
Periodic singularities are enumerated only inside the finite requested interval.
Adaptive Gauss–Kronrod supports integrable endpoint singularities. Internal poles
remain rejected; principal-value integration is not implied.

Each result carries the selected method, evaluations, error kind, and convergence
status. Estimates are diagnostics, **not certified bounds**. Monte Carlo reports
standard error rather than a deterministic error bound. Segment error estimates
are added; independently seeded Monte Carlo variances are added. Global tolerance
is checked after combining segments. Budget exhaustion is reported explicitly.
Arbitrary hidden narrow features can still defeat finite sampling; structural
recognition currently covers quadratic exponential peaks and a single linear
trigonometric phase, not all possible expressions.

Method comparison warms caches, repeats measurements three times, shows median
time and actual error, and uses symbolic or agreeing high-precision reference
calculations. Methods qualify for the fastest result only when reference-based
accuracy is confirmed. If a trustworthy reference is unavailable, the comparison
says so. Different algorithms retain their own work parameters, so this is a
benchmark at the selected tolerance/settings, not a universal ranking.

## Reproduce the evidence

```sh
python run_tests.py
python scripts/benchmark_integration.py
```

`docs/benchmark-v5.json` records the measured machine/runtime and warm-run medians
for five deterministic fixtures, with analytic references. For `sin(10000*x)`
on `[0,1]`, weighted quadrature used 25 amplitude evaluations, while default
SciPy `quad` used 2,079 evaluations and did not converge. For the narrow Gaussian,
plain `quad` returned zero; the new structural split returned approximately
`0.0001772453850905545` using 210 evaluations. These are fixture-specific results;
wall-clock times and relative performance depend on hardware and input.
