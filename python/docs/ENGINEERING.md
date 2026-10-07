# Signals & Reliable Integration — v5.0.0

This edition keeps integration at the center of the project. The engineering
connection is the accumulation and transformation of information: measured
signals, energy, bias drift, convolution, and Fourier reconstruction. The
existing symbolic calculus workspace remains available.

## Numerical integration

Advanced → Numerical Integration offers **Auto**, which selects weighted
quadrature for a recognized single linear-phase sine/cosine factor and adaptive
Gauss–Kronrod otherwise. Precision controls expose absolute/relative tolerance,
evaluation/time budgets, Gaussian order, and a Monte Carlo seed. Fixed rules
still use the step input. Convergence studies expose the parameter appropriate
to each method, with actual evaluation counts.

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

## Signal tools

Open **Math Tools → Signals**. In formulas, `x` is time.

1. Generate samples from a formula or import a UTF-8 CSV with two columns:
   `time,value`. An optional `time`, `t`, or `timestamp` header is supported.
   Timestamps must be finite and strictly increasing; missing values and duplicate
   timestamps are rejected. `examples/signal.csv` is an import example.
2. The data view integrates with actual timestamps and plots the cumulative
   integral. It also reports time-weighted mean, RMS, and signal energy.
   Uneven sample spacing is supported here. Sampling and measurement error are
   separate from quadrature error and are not certified by this result.
3. Noise experiments add reproducible Gaussian noise and a known bias. They plot
   accumulated integral error, compare expected bias drift `bias × duration`, and
   apply known-bias correction plus an edge-padded moving average. This preserves
   a genuine DC component; smoothing can still distort a varying signal.
4. Convolution compares direct and FFT implementations with the sample-spacing
   factor included. Both signals are zero outside the supplied finite window;
   the output time origin is the sum of their origins. Direct computation is
   skipped when its quadratic operation budget is exceeded.
5. Fourier reconstruction retains a chosen harmonic count and displays the error
   curve, RMS error, and maximum error. The samples are periodically extended
   with period `sample count × spacing`. For a complete period, avoid supplying
   a duplicated endpoint. Noise, convolution, and Fourier views require uniform
   sample spacing and reject uneven grids rather than silently reinterpreting
   their timestamps.

The UI limits sample count to 200,000 and CSV size to 32 MB. Signal and mathematical
tool calculations run in a reusable isolated process; cancellation and timeouts
terminate and replace it. Large returned results are received before process
shutdown, avoiding pipe/queue deadlocks.

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

The Python changes also include the offline MathLive editor, Qt interface, and
packaging work that had not previously been synchronized to the repository.
The C++ edition remains at its existing feature scope; see `cpp/PARITY.md` for
features that have not been ported from Python v5.
