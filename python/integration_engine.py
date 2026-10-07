"""Budgeted numerical quadrature with explicit convergence diagnostics.

Error estimates are numerical diagnostics, not certified bounds. Structural
breakpoints reduce missed-feature and aliasing failures for supported inputs.
"""
from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, replace

import calengine as np
from scipy.integrate import quad, simpson


class CalculationCancelled(ValueError):
    pass


class NumericalConvergenceError(ValueError):
    pass


@dataclass(frozen=True)
class NumericalOptions:
    epsabs: float = 1e-8
    epsrel: float = 1e-8
    max_evaluations: int = 200000
    max_seconds: float = 8.0
    intervals: int | None = None
    order: int = 64
    max_level: int = 16
    seed: int = 0
    repeats: int = 3
    cancel: object = None

    def validated(self):
        if not (math.isfinite(self.epsabs) and math.isfinite(self.epsrel)):
            raise ValueError("Error tolerances must be finite.")
        if self.epsabs <= 0 or self.epsrel <= 0:
            raise ValueError("Absolute and relative error tolerances must be positive.")
        if not math.isfinite(self.max_seconds) or self.max_seconds <= 0:
            raise ValueError("Time budget must be finite and positive.")
        if not 32 <= self.max_evaluations <= 2000000:
            raise ValueError("Evaluation budget must be between 32 and 2000000.")
        if not 2 <= self.order <= 1024 or not 2 <= self.max_level <= 20:
            raise ValueError("Invalid Gaussian order or Romberg level.")
        if self.intervals is not None and not 1 <= self.intervals <= self.max_evaluations:
            raise ValueError("Interval count exceeds the evaluation budget.")
        return self


def get_options(options=None):
    return (options if isinstance(options, NumericalOptions) else NumericalOptions(**(options or {}))).validated()


class EvaluationBudget:
    def __init__(self, function, options):
        self.function, self.options = function, options
        self.started = time.perf_counter()
        self.count = 0
        self.expression = getattr(function, "expression", None)

    def check(self):
        if self.options.cancel is not None and self.options.cancel.is_set():
            raise CalculationCancelled("Calculation cancelled.")
        if time.perf_counter()-self.started > self.options.max_seconds:
            raise NumericalConvergenceError("Time budget exceeded; convergence was not confirmed.")

    def __call__(self, values):
        self.check()
        self.count += int(np.asarray(values).size)
        if self.count > self.options.max_evaluations:
            raise NumericalConvergenceError("Evaluation budget exceeded; increase the budget or split the interval.")
        with np.errstate(all="ignore"):
            output = np.asarray(self.function(values), dtype=float)
        if not np.all(np.isfinite(output)):
            raise ValueError("Function produced non-finite values at quadrature nodes.")
        return output

    def scalar(self, value):
        return float(self(value).reshape(-1)[0])


def oscillatory_factor(expr):
    """Recognize one linear-phase sine/cosine factor without guessing frequency."""
    if expr is None:
        return None
    from parser_utils import x_sym
    from solving import sin, cos
    atoms = expr.atoms(sin, cos)
    if len(atoms) != 1:
        return None
    trig = next(iter(atoms))
    frequency = trig.args[0].diff(x_sym)
    phase = trig.args[0].subs(x_sym, 0)
    if frequency.has(x_sym) or phase.has(x_sym):
        return None
    amplitude = expr / trig
    amplitude = amplitude.cancel()
    if amplitude.has(sin, cos):
        return None
    try:
        w, phi = float(frequency), float(phase)
        if math.isfinite(w) and math.isfinite(phi) and w:
            return amplitude, "sin" if trig.func == sin else "cos", w, phi
    except (TypeError, ValueError):
        pass
    return None


def structural_points(expr, a, b):
    """Resolve centers and widths of quadratic exponential peaks analytically."""
    if expr is None:
        return []
    from parser_utils import x_sym
    from solving import exp
    lo, hi = sorted((a, b))
    points = []
    for term in expr.atoms(exp):
        exponent = term.args[0]
        if not exponent.is_polynomial(x_sym) or exponent.as_poly(x_sym).degree() != 2:
            continue
        try:
            coeff = float(exponent.diff(x_sym, 2)/2)
            if coeff >= 0:
                continue
            center = float(-exponent.diff(x_sym).subs(x_sym, 0)/(2*coeff))
            width = 1/math.sqrt(-coeff)
            if width < (hi-lo)/8:
                points.extend(center+k*width for k in (-6,-3,-1,-.25,0,.25,1,3,6)
                              if lo < center+k*width < hi)
        except (ValueError, TypeError, OverflowError):
            continue
    return sorted(set(points))


def _quad_checked(f, a, b, options, **kwargs):
    output = quad(f, a, b, epsabs=options.epsabs, epsrel=options.epsrel,
                  limit=min(1000, max(50, options.max_evaluations//42)), full_output=1, **kwargs)
    if len(output) > 3:
        raise NumericalConvergenceError(str(output[3]))
    value, error = float(output[0]), float(output[1])
    if error > max(options.epsabs, options.epsrel*abs(value)):
        raise NumericalConvergenceError("Requested accuracy was not reached.")
    return value, error


def _weighted_quad(budget, a, b, factor, options):
    from numeric_methods import build_numeric_callable
    amplitude, kind, w, phase = factor
    raw = build_numeric_callable(amplitude)
    original = budget.function
    budget.function = raw
    try:
        components = [(math.cos(phase), kind)]
        if phase:
            components.append((math.sin(phase) * (1 if kind == "sin" else -1),
                               "cos" if kind == "sin" else "sin"))
        result, error = 0., 0.
        for coefficient, weight in components:
            value, estimate = _quad_checked(budget.scalar, a, b, options, weight=weight, wvar=w)
            result += coefficient*value
            error += abs(coefficient)*estimate
        return result, error
    finally:
        budget.function = original


def _adaptive_simpson(f, a, b, options):
    """Globally refine the interval with the largest Richardson error."""
    serial = 0
    def panel(left, right, fl, fm, fr):
        nonlocal serial
        mid = (left+right)/2
        f1, f3 = f.scalar((left+mid)/2), f.scalar((mid+right)/2)
        coarse = (right-left)*(fl+4*fm+fr)/6
        fine = (right-left)*(fl+4*f1+2*fm+4*f3+fr)/12
        error = abs(fine-coarse)/15
        serial += 1
        return (-error, serial, left, right, fl, f1, fm, f3, fr, fine+(fine-coarse)/15)
    factor = oscillatory_factor(f.expression)
    initial = max(16, math.ceil(abs(factor[2]*(b-a))/(2*math.pi)*8)) if factor else 16
    if initial*5 > options.max_evaluations:
        raise NumericalConvergenceError("Oscillation requires more samples than the evaluation budget.")
    nodes = sorted(set(np.linspace(a,b,initial+1).tolist()+structural_points(f.expression,a,b)))
    heap, total, error = [], 0., 0.
    for left,right in zip(nodes[:-1], nodes[1:]):
        item = panel(left,right,f.scalar(left),f.scalar((left+right)/2),f.scalar(right))
        heapq.heappush(heap,item); total += item[-1]; error -= item[0]
    while error > max(options.epsabs, options.epsrel*abs(total)):
        f.check()
        item = heapq.heappop(heap)
        neg,_,left,right,fl,f1,fm,f3,fr,value = item
        mid = (left+right)/2
        if mid == left or mid == right:
            raise NumericalConvergenceError("Roundoff prevents further interval refinement.")
        total -= value; error += neg
        for child in (panel(left,mid,fl,f1,fm), panel(mid,right,fm,f3,fr)):
            heapq.heappush(heap,child); total += child[-1]; error -= child[0]
    return total, max(0.,error)


def _romberg(f, a, b, options):
    factor = oscillatory_factor(f.expression)
    minimum_level = max(5, math.ceil(math.log2(max(1.,abs(factor[2]*(b-a))/(2*math.pi)*8)))) if factor else 5
    previous = [.5*(b-a)*(f.scalar(a)+f.scalar(b))]
    for level in range(1,options.max_level+1):
        n = 2**level; h = (b-a)/n
        if f.count+n//2 > options.max_evaluations:
            raise NumericalConvergenceError("Romberg exceeded its evaluation budget.")
        values = f(a+h*np.arange(1,n,2))
        current = [.5*previous[0]+h*float(np.sum(values))]
        for order in range(1,level+1):
            current.append(current[-1]+(current[-1]-previous[order-1])/(4**order-1))
        error = abs(current[-1]-previous[-1])
        if level >= minimum_level and error <= max(options.epsabs,options.epsrel*abs(current[-1])):
            # An independent non-dyadic quadrature catches false grid agreement.
            from numeric_methods import gaussian_quadrature_fixed
            n_check = min(128,max(17,n//2+1))
            check = gaussian_quadrature_fixed(f,a,b,n_check)
            if not factor and abs(check-current[-1]) > max(options.epsabs*10,options.epsrel*abs(current[-1])*10):
                previous = current; continue
            return current[-1],error
        previous = current
    raise NumericalConvergenceError("Romberg did not reach the requested accuracy.")


def _fixed(f, method, a, b, n):
    if method == "Simpson" and n%2:
        n += 1
    if method == "Simpson 3/8":
        n += (-n)%3
    if n+1 > f.options.max_evaluations-f.count:
        raise NumericalConvergenceError("Sample count exceeds the evaluation budget.")
    nodes = np.linspace(a,b,n+1)
    if method == "Rectangle":
        value = float(np.sum(f((nodes[:-1]+nodes[1:])/2)))*(b-a)/n
    else:
        values = f(nodes)
        if method == "Trapezoidal":
            value = float(np.trapezoid(values,nodes))
        elif method == "Simpson":
            value = float(simpson(values,x=nodes))
        else:
            value = float(3*(b-a)/n/8*(values[0]+values[-1]+3*np.sum(values[1:-1])-np.sum(values[3:n:3])))
    return value,n


def integrate_numerically(method, function, a, b, delta=None, *, progress_callback=None, options=None):
    opts = get_options(options)
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("Numerical integration requires finite limits; use the improper-integral workflow.")
    if delta is not None and (not math.isfinite(delta) or delta <= 0):
        raise ValueError("Step size must be finite and positive.")
    sign = 1 if b >= a else -1
    a,b = sorted((float(a),float(b)))
    f = EvaluationBudget(function,opts)
    requested = method; reason = "Selected by user"; parameter = None
    factor = oscillatory_factor(f.expression)
    points = structural_points(f.expression,a,b)
    if method == "Auto":
        if factor and abs(factor[2]*(b-a)) > 20:
            method = "Oscillatory Quadrature"; reason = "Recognized a linear-phase oscillation"
        else:
            method = "Adaptive Gauss-Kronrod"; reason = "Adaptive error control with structural breakpoints"
    if a == b:
        value,error = 0.,0.
    elif method in {"Adaptive Gauss-Kronrod", "Adaptive Simpson"}:
        if method == "Adaptive Simpson":
            value,error = _adaptive_simpson(f,a,b,opts)
        else:
            value,error = _quad_checked(f.scalar,a,b,opts,**({"points":points} if points else {}))
    elif method == "Oscillatory Quadrature":
        if not factor:
            raise ValueError("Oscillatory Quadrature requires a recognizable linear-phase sine or cosine factor.")
        value,error = _weighted_quad(f,a,b,factor,opts)
        parameter = {"angular_frequency":factor[2]}
    elif method == "Romberg":
        value,error = _romberg(f,a,b,opts); parameter = {"max_level":opts.max_level}
    elif method == "Gaussian Quadrature":
        from numeric_methods import gaussian_quadrature_fixed
        bounds = [a,*points,b]; value,error = 0.,0.
        for left,right in zip(bounds[:-1],bounds[1:]):
            fine = gaussian_quadrature_fixed(f,left,right,opts.order)
            coarse = gaussian_quadrature_fixed(f,left,right,max(2,opts.order//2))
            value += fine; error += abs(fine-coarse)
        parameter = {"order":opts.order}
    elif method == "Monte Carlo":
        n = opts.intervals or (8000 if delta is None else max(4000,math.ceil((b-a)/delta)*20))
        if n > opts.max_evaluations:
            raise NumericalConvergenceError("Monte Carlo sample count exceeds the evaluation budget.")
        if n < 2:
            raise ValueError("Monte Carlo requires at least two samples to estimate uncertainty.")
        strata = min(200, n//2, max(20,int(math.sqrt(n)))); rng = np.random.default_rng(opts.seed)
        sizes = np.full(strata,n//strata,dtype=int); sizes[:n%strata] += 1
        width = (b-a)/strata; value,variance = 0.,0.
        for i,size in enumerate(sizes):
            values = f(a+(i+rng.random(int(size)))*width)
            value += width*float(np.mean(values))
            if size > 1:
                variance += width**2*float(np.var(values,ddof=1))/size
        error = math.sqrt(variance); parameter = {"samples":n,"strata":strata,"seed":opts.seed}
    elif method in {"Rectangle","Trapezoidal","Simpson","Simpson 3/8"}:
        default = {"Rectangle":1000,"Trapezoidal":2000,"Simpson":2000,"Simpson 3/8":300}[method]
        n = opts.intervals or (default if delta is None else max(2,math.ceil((b-a)/delta)))
        value,n = _fixed(f,method,a,b,n)
        coarse,_ = _fixed(f,method,a,b,max(1,n//2))
        error = abs(value-coarse)/(15 if method.startswith("Simpson") else 3) if n >= 4 else float("inf")
        parameter = {"intervals":n,"step":(b-a)/n}
    else:
        raise ValueError(f"Unknown numerical method: {method}")
    target = max(opts.epsabs,opts.epsrel*abs(value))
    status = "converged" if error <= target else "tolerance_not_met"
    kind = "standard_error" if method == "Monte Carlo" else "estimated_absolute_error"
    if progress_callback:
        progress_callback(100)
    return sign*float(value),float(error),{
        "requested_method":requested,"method":method,"reason":reason,"evaluations":f.count,
        "status":status,"error_kind":kind,"estimated_error":float(error),"target":target,
        "parameters":parameter,"elapsed":time.perf_counter()-f.started,
    }
