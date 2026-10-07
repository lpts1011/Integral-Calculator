"""Reproducible correctness/work benchmarks; timings depend on the machine."""
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_source_paths import prefer_local_solving_source
prefer_local_solving_source()
from scipy.integrate import quad
from numeric_methods import build_numeric_callable
from parser_utils import evaluate_symbolic_function
from tab2_logic import compute_segmented_numerical_integral

CASES = [
    ('high_frequency', 'sin(10000*x)', 'Auto', (1-math.cos(10000))/10000),
    ('narrow_peak', 'exp(-100000000*(x-0.12345)^2)', 'Auto', math.sqrt(math.pi)/10000),
    ('romberg_aliasing', 'cos(512*pi*x)', 'Romberg', 0.),
    ('endpoint_singularity', '1/sqrt(x)', 'Auto', 2.),
    ('smooth', 'exp(x)', 'Auto', math.e-1),
]

def main():
    results = []
    for name, text, method, reference in CASES:
        expr = evaluate_symbolic_function(text)
        function = build_numeric_callable(expr)
        def calculate():
            return compute_segmented_numerical_integral(expr, method, function, 0., 1., None, options={})
        calculate()
        times = []
        for _ in range(3):
            started = time.perf_counter()
            value, estimate, segments = calculate()
            times.append(time.perf_counter()-started)
        raw = quad(function, 0., 1., full_output=1)
        diagnostics = segments[0]['diagnostics']
        results.append({'case':name, 'expression':text, 'reference':reference,
            'method':diagnostics['method'], 'value':value, 'actual_error':abs(value-reference),
            'estimated_error':estimate, 'evaluations':sum(segment['diagnostics']['evaluations'] for segment in segments),
            'median_seconds':statistics.median(times), 'status':diagnostics['status'],
            'plain_quad_value':float(raw[0]), 'plain_quad_actual_error':abs(float(raw[0])-reference),
            'plain_quad_evaluations':raw[2]['neval'], 'plain_quad_converged':len(raw)==3})
    payload={'python':sys.version.split()[0], 'platform':platform.platform(),
        'repetitions':3, 'timing_scope':'Warm integration, including validation; parsing excluded', 'cases':results}
    output = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'docs/benchmark-v5.json'
    output.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))
if __name__ == '__main__':
    main()
