# Update Log

## 2026-07-20

- Changed graph titles and legends to use human-readable mathematical notation.
  Exponentials now appear as `e^x` instead of `exp(x)`, powers use `^` instead
  of `**`, and multiplication is shown with a centered dot.
- Kept the original parser expression unchanged for numerical sampling, so this
  display-only improvement does not alter graph values or integration results.
- Added regression coverage for exponential and power notation in both the
  graph title and legend.
- Automated coverage now includes 142 passing tests, including 10 real
  WebEngine rendering checks.

## 2026-07-18

- Replaced the separate text-entry and preview workflow with direct, editable,
  typeset mathematical fields throughout Basic, Advanced, Improper Integral,
  and Math Tools.
- Migrated the production desktop interface from Tkinter to PySide6 while
  preserving the existing calculation engine, methods, results, plotting,
  history, steps, suggestions, themes, and languages.
- Added a fully offline MathLive editor bundle with local fonts, integrity
  checks, secure runtime staging, and no network dependency.
- Added keyboard-first editing, focus navigation, copy and paste, undo and redo,
  long-expression handling, and localized field labels.
- Replaced the template selector and Insert Template controls with a floating,
  always-on-top mathematical keyboard focused on common functions, cursor
  controls, logarithms, exponentials, powers, roots, fractions, constants, and
  infinity.
- Removed the low-use favorites and result-export workflows, including their
  storage, formatting, dialogs, translations, legacy UI hooks, and tests.
- Removed standalone digit keys from the mathematical keyboard and moved
  frequently used functions to its first tab.
- Added cursor-aware MathLive insertion so keyboard entries replace the current
  selection or appear at the active caret without overwriting the expression.
- Moved both integration bounds to the right of the integral symbol and made
  the integrand editor grow with its content while keeping `dx` attached to its
  trailing edge.
- Made the Advanced Integration editor report its rendered content height to
  the native layout so all five fields remain visible without wasting the
  available vertical space or showing an unnecessary inner scrollbar.
- Added a shared rendered result workspace beneath the integration tabs with
  separate exact-result, integral-result, and total-time fields.
- Added automatically generated, human-readable symbolic integration steps
  with locally rendered formulas for definite, indefinite, and improper
  integrals. Step generation runs in the background so it cannot block the UI.
- Made the input and result regions vertically resizable while keeping the full
  Advanced Integration editor visible at the default window size.
- Ported all existing Math Tools pages to the same live editor and retained
  insertion into the active calculator tab.
- Updated macOS and Windows packaging to include PySide6 Qt WebEngine, QtAgg,
  and all local editor resources.
- Added automated parity, resource, lifecycle, localization, and packaging
  tests for the new interface.
- Automated coverage now includes 141 tests, including real WebEngine checks for
  caret insertion, function placeholders, adaptive sizing, integral layout,
  localized results, and rendered symbolic steps.

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
