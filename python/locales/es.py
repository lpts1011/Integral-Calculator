# Auto-extracted locale data. Edit values here, not in i18n.py.

LANGUAGE = 'Español'

INSTRUCTIONS = ['Funciones matemáticas y constantes comunes:',
 'log10(x) - Logaritmo común (base 10), ej.: log10(100)',
 'ln(x) / log(x) - Logaritmo natural (base e), ej.: ln(2)',
 'pi - Pi, entrada: pi',
 'sin(x), cos(x), tan(x)',
 'sqrt(x) - Raíz cuadrada, ej.: sqrt(4)',
 'exp(x) o e^x - Función exponencial, ej.: exp(1) = e^1',
 'Representación de infinito:',
 'Infinito positivo - inf',
 'Infinito negativo - -inf',
 '']

UI = {'title': 'Calculadora de Integrales',
 'tabs': ('Integración básica', 'Integración avanzada', 'Integral impropia (infinita)'),
 'usage': 'Instrucciones de uso',
 'calc1': 'Calcular integral',
 'reset': 'Restablecer',
 'calc3': 'Calcular integral',
 'method': 'Método de integración:',
 'lower': 'Límite inferior:',
 'upper': 'Límite superior:',
 'delta': 'Tamaño de paso (integración numérica):',
 'func': 'Introducir función objetivo:',
 'numerical_method': 'Método numérico:',
 'history': 'Historial:',
 'template': 'Template:',
 'insert_template': 'Insert Template',
 'theme': 'Tema:',
 'parameters': 'Parameters:',
 'split_points': 'Split points:',
 'compare_methods': 'Compare Methods',
 'comparison_title': 'Numerical Method Comparison',
 'apply_recommendation': 'Aplicar recomendación',
 'time': 'Tiempo',
 'recommend_enter_function': 'Recomendación: introduce primero una función.',
 'recommend_complete_limits': 'Recomendación: completa ambos límites, o deja ambos vacíos para una integral '
                              'indefinida.',
 'recommend_indefinite': 'Recomendación: la integración simbólica es mejor para una integral indefinida.',
 'recommend_invalid_limits': 'Recomendación: usa integración simbólica hasta que los límites sean constantes válidas.',
 'recommend_improper': 'Recomendación: parece una integral impropia. Usa Tab 3 o integración simbólica si existe forma '
                       'cerrada.',
 'recommend_zero_width': 'Recomendación: los límites son iguales, así que la integral es 0.',
 'recommend_singularity': 'Recomendación: singularidad cerca de x={point}; divide el intervalo antes de integrar.',
 'recommend_invalid_function': 'Recomendación: corrige la función antes de elegir un método numérico.',
 'recommend_nonfinite_samples': 'Recomendación: hay valores no definidos en el intervalo; divide el intervalo o usa '
                                'Adaptive Simpson con cuidado.',
 'recommend_oscillatory': 'Recomendación: función oscilatoria o intervalo amplio; Adaptive Simpson es un buen primer '
                          'intento.',
 'recommend_steep': 'Recomendación: la función cambia bruscamente; Adaptive Simpson maneja mejor la variación local.',
 'recommend_smooth_nonlinear': 'Recomendación: función no lineal suave; Gaussian Quadrature suele ser eficiente.',
 'recommend_polynomial': 'Recomendación: función suave similar a un polinomio; Simpson es una opción sólida.',
 'recommend_default': 'Recomendación: intervalo finito y suave; Simpson es una opción sólida.'}
