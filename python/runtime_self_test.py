"""Exercise the packaged runtime without opening an interactive window."""
import json
import math
import sys
import time
from pathlib import Path


def run():
    import calengine as np
    from numeric_methods import build_numeric_callable
    from parser_utils import evaluate_symbolic_function
    from tab2_logic import compute_segmented_numerical_integral
    from signal_analysis import integrate_signal, convolution_analysis, fourier_reconstruction
    from symbolic_methods import compute_tab1_result
    from symbolic_service import run_isolated
    from signal_analysis import generate_and_integrate
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, QEvent, QTimer
    from math_editor.panel import MathEditorPanel
    from math_editor.syntax import FieldRole

    checks = {}
    for name, expression, expected in (
        ('oscillation', 'sin(10000*x)', (1-math.cos(10000))/10000),
        ('narrow_peak', 'exp(-100000000*(x-0.12345)^2)', math.sqrt(math.pi)/10000),
        ('endpoint', '1/sqrt(x)', 2.),
    ):
        expr = evaluate_symbolic_function(expression)
        value, error, segments = compute_segmented_numerical_integral(
            expr, 'Auto', build_numeric_callable(expr), 0., 1., None, options={})
        if abs(value-expected) > 1e-8:
            raise AssertionError(f'{name}: unexpected result {value}')
        checks[name] = {'value':value, 'error':error, 'method':segments[0]['diagnostics']['method']}
    symbol = compute_tab1_result('sin(x)', '0', 'pi')
    if abs(symbol['numeric_value']-2) > 1e-10:
        raise AssertionError('Symbolic worker result mismatch')
    checks['symbolic_worker'] = True
    signal = run_isolated(generate_and_integrate, ('2', 0., 1., 101), timeout=8)
    if abs(signal['integral']-2) > 1e-10:
        raise AssertionError('Signal worker result mismatch')
    checks['signal_worker'] = True
    t = np.arange(128)/128
    y = np.sin(2*np.pi*3*t)
    convolution = convolution_analysis(t, y, np.exp(-t))
    if convolution['difference'] > 1e-10:
        raise AssertionError('FFT convolution mismatch')
    if fourier_reconstruction(t, y, 3)['max_error'] > 1e-10:
        raise AssertionError('Fourier reconstruction mismatch')
    checks['fft_and_reconstruction'] = True
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    panel = MathEditorPanel()
    panel.create_field('self-test', FieldRole.EXPRESSION, 'x^2')
    started = time.monotonic()
    while not panel.is_ready() and time.monotonic()-started < 10:
        app.processEvents()
        time.sleep(.01)
    if not panel.is_ready():
        raise AssertionError('Offline editor did not reach Qt WebChannel')
    checks['offline_editor_bridge'] = True
    panel.close()
    panel.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    # Let Qt emit aboutToQuit and drain its native WebEngine shutdown work.
    QTimer.singleShot(0, app.quit)
    app.exec()
    payload = {'passed':True, 'checks':checks}
    if '--self-test-output' in sys.argv:
        index = sys.argv.index('--self-test-output')
        Path(sys.argv[index+1]).write_text(json.dumps(payload, indent=2)+'\n')
    if sys.stdout is not None:
        print(json.dumps(payload, indent=2))
    return 0
