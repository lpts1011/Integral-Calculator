# Auto-extracted locale data. Edit values here, not in i18n.py.

LANGUAGE = 'Français'

INSTRUCTIONS = ['Fonctions mathématiques et constantes courantes :',
 'log10(x) - Logarithme décimal (base 10), ex. : log10(100)',
 'ln(x) / log(x) - Logarithme naturel (base e), ex. : ln(2)',
 'pi - Pi, entrée : pi',
 'sin(x), cos(x), tan(x)',
 'sqrt(x) - Racine carrée, ex. : sqrt(4)',
 'exp(x) ou e^x - Fonction exponentielle, ex. : exp(1) = e^1',
 "Représentation de l'infini :",
 'Infini positif - inf',
 'Infini négatif - -inf',
 '']

UI = {'title': "Calculateur d'intégrales",
 'tabs': ('Intégration de base', 'Intégration avancée', 'Intégrale impropre (infinie)'),
 'usage': "Instructions d'utilisation",
 'calc1': "Calculer l'intégrale",
 'reset': 'Réinitialiser',
 'calc3': "Calculer l'intégrale",
 'method': "Méthode d'intégration :",
 'lower': 'Borne inférieure :',
 'upper': 'Borne supérieure :',
 'delta': 'Pas (intégration numérique) :',
 'func': 'Entrer la fonction cible :',
 'numerical_method': 'Méthode numérique :',
 'history': 'Historique :',
 'template': 'Template:',
 'insert_template': 'Insert Template',
 'theme': 'Thème :',
 'parameters': 'Parameters:',
 'split_points': 'Split points:',
 'compare_methods': 'Compare Methods',
 'comparison_title': 'Numerical Method Comparison',
 'apply_recommendation': 'Appliquer la recommandation',
 'time': 'Temps',
 'recommend_enter_function': "Recommandation : entrez d'abord une fonction.",
 'recommend_complete_limits': 'Recommandation : remplissez les deux bornes, ou laissez-les vides pour une intégrale '
                              'indéfinie.',
 'recommend_indefinite': "Recommandation : l'intégration symbolique convient mieux à une intégrale indéfinie.",
 'recommend_invalid_limits': "Recommandation : utilisez l'intégration symbolique jusqu'à ce que les bornes soient des "
                             'constantes valides.',
 'recommend_improper': "Recommandation : cela ressemble à une intégrale impropre. Utilisez Tab 3 ou l'intégration "
                       'symbolique si une forme fermée existe.',
 'recommend_zero_width': "Recommandation : les bornes sont égales, donc l'intégrale vaut 0.",
 'recommend_singularity': "Recommandation : singularité près de x={point}; divisez l'intervalle avant d'intégrer.",
 'recommend_invalid_function': 'Recommandation : corrigez la fonction avant de choisir une méthode numérique.',
 'recommend_nonfinite_samples': "Recommandation : des valeurs échantillonnées sont indéfinies dans l'intervalle; "
                                "divisez l'intervalle ou utilisez Adaptive Simpson avec prudence.",
 'recommend_oscillatory': 'Recommandation : fonction oscillante ou intervalle large; Adaptive Simpson est un bon '
                          'premier choix.',
 'recommend_steep': 'Recommandation : la fonction varie fortement; Adaptive Simpson gère mieux les variations locales.',
 'recommend_smooth_nonlinear': 'Recommandation : fonction non linéaire lisse; Gaussian Quadrature est souvent '
                               'efficace.',
 'recommend_polynomial': "Recommandation : fonction lisse proche d'un polynôme; Simpson est un choix solide.",
 'recommend_default': 'Recommandation : intervalle fini et lisse; Simpson est un choix solide.'}
