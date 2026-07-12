# Update Log

## 2026-06-03

- Added Taylor polynomial expansion with configurable expansion point and order.
- Added numerical convergence tables for interval-count based comparison.
- Added singularity, Piecewise breakpoint, and split-point analysis.
- Added function-property analysis for derivative, second derivative, roots, critical points, and inflection points.
- Added average value, signed area, absolute area, positive area, and negative area tools.
- Added substitution and integration-by-parts helper tools.
- Added arc length and volume-of-revolution tools.
- Added Fourier series, Laplace transform, inverse Laplace display, and simple ODE solving tools.
- Expanded multiple integrals with variable-bound double integrals, polar double integrals, and rectangular triple integrals.
- Added parameter sensitivity analysis across a list of parameter values.
- Reorganized `Math Tools` into category tabs plus sub-tabs so the tools no longer crowd into one top row.
- Reworked the main layout so the graph uses the large right-side workspace and history is kept in a smaller left-side panel.
- Increased the graph-to-input width ratio so most horizontal workspace goes to plotting.
- Reduced the Basic Integration LaTeX preview's requested width so the graph panel can expand.
- Split the crowded top toolbar into two rows for language/favorites and templates/actions.
- Increased the plot area's default figure ratio to better fit the larger graph panel.
- Added localized labels for newly added toolbar actions and several previously English-only controls across non-English languages.
- Fixed `Show Steps` to display `Antiderivative not found, N/A` when symbolic steps are not available, including unevaluated `Integral(...)` results.
- Added regression tests and GUI smoke coverage for the new math features, Math Tools layout, localization, and Show Steps unavailable-state behavior.
