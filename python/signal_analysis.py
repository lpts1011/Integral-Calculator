"""Integration-based analysis of sampled signals, with explicit time coordinates."""
from __future__ import annotations

import csv
import io
import math
import statistics
import time

import calengine as np
from scipy.integrate import cumulative_trapezoid
from scipy.signal import convolve, fftconvolve

MAX_SAMPLES = 200000


def validate_samples(t, y, *, uniform=False):
    t,y = np.asarray(t,dtype=float),np.asarray(y,dtype=float)
    if t.ndim != 1 or y.ndim != 1 or len(t) != len(y) or not 2 <= len(t) <= MAX_SAMPLES:
        raise ValueError("Provide 2 to 200000 matching time and signal samples.")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)):
        raise ValueError("Time and signal samples must be finite.")
    differences = np.diff(t)
    if np.any(differences <= 0):
        raise ValueError("Timestamps must be strictly increasing; duplicates and reversed rows are not allowed.")
    if uniform and not np.allclose(differences,differences[0],rtol=1e-6,atol=abs(differences[0])*1e-8):
        raise ValueError("This operation requires uniformly spaced samples. Resample explicitly first.")
    return t,y


def read_signal_csv(text):
    rows = csv.reader(io.StringIO(text.lstrip('\ufeff')))
    values = []
    for line,row in enumerate(rows,1):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise ValueError(f"CSV line {line}: expected exactly two columns (time, value).")
        try:
            pair = tuple(float(cell) for cell in row)
        except ValueError:
            if not values and line == 1 and row[0].strip().lower() in {"time","t","timestamp"}:
                continue
            raise ValueError(f"CSV line {line}: both columns must be numeric.")
        values.append(pair)
        if len(values) > MAX_SAMPLES:
            raise ValueError("CSV exceeds the 200000 sample limit.")
    if len(values) < 2:
        raise ValueError("CSV must contain at least two data rows.")
    return validate_samples(*zip(*values))


def integrate_signal(t,y):
    t,y = validate_samples(t,y)
    integral = cumulative_trapezoid(y,t,initial=0)
    squared = cumulative_trapezoid(y*y,t,initial=0)
    duration = float(t[-1]-t[0])
    return {"time":t,"signal":y,"cumulative":integral,"squared_cumulative":squared,
        "integral":float(integral[-1]),"energy":float(squared[-1]),
        "mean":float(integral[-1]/duration),"rms":math.sqrt(max(0.,float(squared[-1]/duration))),
        "duration":duration,"samples":len(t),"method":"composite trapezoidal with actual timestamps"}


def sample_expression(expression, start=0., stop=1., samples=1001):
    from numeric_methods import build_numeric_callable, numeric_values
    from parser_utils import evaluate_symbolic_function
    if not (math.isfinite(start) and math.isfinite(stop) and stop > start):
        raise ValueError("The end time must be finite and greater than the start time.")
    if not 2 <= int(samples) <= MAX_SAMPLES:
        raise ValueError("Sample count is outside the supported range.")
    t = np.linspace(start,stop,int(samples))
    y = numeric_values(build_numeric_callable(evaluate_symbolic_function(expression)),t)
    return validate_samples(t,y)


def noise_experiment(t,clean,noise_std=.1,bias=.05,seed=0,window=11):
    t,clean = validate_samples(t,clean,uniform=True)
    if not (math.isfinite(noise_std) and noise_std >= 0 and math.isfinite(bias)):
        raise ValueError("Noise deviation must be non-negative and bias must be finite.")
    window = int(window)
    if window < 1 or window > len(t):
        raise ValueError("Filter window must fit inside the sampled signal.")
    if window%2 == 0:
        window += 1
    if window > len(t):
        window -= 2
    measured = clean+np.random.default_rng(int(seed)).normal(0,noise_std,len(t))+bias
    # Use the known simulated bias; subtracting the sample mean would remove genuine DC.
    corrected = measured-bias
    padding = window//2
    filtered = np.convolve(np.pad(corrected,(padding,padding),mode="edge"),np.ones(window)/window,mode="valid")
    truth,raw,processed = (integrate_signal(t,values) for values in (clean,measured,filtered))
    return {"time":t,"clean":clean,"measured":measured,"filtered":filtered,
        "truth":truth,"raw":raw,"processed":processed,"expected_bias_drift":bias*(t[-1]-t[0]),
        "raw_integral_error":raw["integral"]-truth["integral"],
        "processed_integral_error":processed["integral"]-truth["integral"],
        "noise_std":noise_std,"bias":bias,"seed":int(seed),"window":window}


def convolution_analysis(t,signal,impulse, *, repeats=3):
    t,signal = validate_samples(t,signal,uniform=True)
    impulse = np.asarray(impulse,dtype=float)
    if impulse.shape != signal.shape or not np.all(np.isfinite(impulse)):
        raise ValueError("Impulse-response samples must match the time grid and be finite.")
    dt = float(t[1]-t[0]); times={}; outputs={}
    algorithms = {"FFT":fftconvolve}
    if len(t)**2 <= 10000000:
        algorithms["Direct"] = lambda left,right,mode:convolve(left,right,mode=mode,method="direct")
    for name,function in algorithms.items():
        function(signal,impulse,mode="full")
        measurements=[]
        for _ in range(max(1,min(7,int(repeats)))):
            started=time.perf_counter()
            outputs[name]=function(signal,impulse,mode="full")*dt
            measurements.append(time.perf_counter()-started)
        times[name]=statistics.median(measurements)
    output_time=2*t[0]+np.arange(2*len(t)-1)*dt
    difference=float(np.max(np.abs(outputs["Direct"]-outputs["FFT"]))) if "Direct" in outputs else None
    return {"time":output_time,"output":outputs["FFT"],"timings":times,"difference":difference,
        "dt":dt,"boundary":"Signals are zero outside the supplied finite window",
        "direct_status":"compared" if "Direct" in outputs else "skipped: direct operation budget exceeded"}


def fourier_reconstruction(t,signal,terms=5):
    t,signal = validate_samples(t,signal,uniform=True)
    terms=int(terms)
    if not 0 <= terms <= len(t)//2:
        raise ValueError("Fourier harmonic count must be between 0 and the Nyquist index.")
    spectrum=np.fft.rfft(signal)
    truncated=spectrum.copy(); truncated[terms+1:]=0
    reconstructed=np.fft.irfft(truncated,n=len(signal))
    error=signal-reconstructed
    dt=float(t[1]-t[0]); period=dt*len(t)
    return {"time":t,"signal":signal,"reconstructed":reconstructed,"error":error,
        "frequencies":np.fft.rfftfreq(len(t),dt),"coefficients":spectrum/len(t),
        "terms":terms,"period":period,"rms_error":float(np.sqrt(np.mean(error**2))),
        "max_error":float(np.max(np.abs(error))),
        "assumption":"The sample window is periodically extended; the period is N times the sample spacing."}


def generate_and_integrate(expression,start,stop,count):
    return integrate_signal(*sample_expression(expression,start,stop,count))


def load_and_integrate(text):
    return integrate_signal(*read_signal_csv(text))


def convolve_expression(t,y,expression):
    from numeric_methods import build_numeric_callable,numeric_values
    from parser_utils import evaluate_symbolic_function
    impulse=numeric_values(build_numeric_callable(evaluate_symbolic_function(expression)),t)
    return convolution_analysis(t,y,impulse)
