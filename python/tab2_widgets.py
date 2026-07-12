import tkinter as tk
from tkinter import ttk


def build_tab2_widgets(tab):
    parent = tab.parent
    tab.func_label = tk.Label(parent, text="Enter target function:")
    tab.func_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    tab.func_entry = tk.Entry(parent, width=30)
    tab.func_entry.grid(row=0, column=1, padx=10, pady=5)

    tab.params_label = tk.Label(parent, text="Parameters:")
    tab.params_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    tab.params_entry = tk.Entry(parent, width=30)
    tab.params_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    tab.lower_label = tk.Label(parent, text="Lower limit:")
    tab.lower_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    tab.lower_entry = tk.Entry(parent, width=12)
    tab.lower_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    tab.upper_label = tk.Label(parent, text="Upper limit:")
    tab.upper_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
    tab.upper_entry = tk.Entry(parent, width=12)
    tab.upper_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

    tab.split_label = tk.Label(parent, text="Split points:")
    tab.split_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
    tab.split_entry = tk.Entry(parent, width=30)
    tab.split_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

    tab.delta_label = tk.Label(parent, text="Step size (for Numerical Integration):")
    tab.delta_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
    tab.delta_entry = tk.Entry(parent, width=12)
    tab.delta_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")

    tab.method_label = tk.Label(parent, text="Integration Method:")
    tab.method_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
    tab.method_var = tk.StringVar(value="Symbolic Integration")
    tab.method_dropdown = ttk.Combobox(
        parent,
        textvariable=tab.method_var,
        values=["Symbolic Integration", "Numerical Integration"],
        state="readonly",
    )
    tab.method_dropdown.grid(row=6, column=1, padx=10, pady=5, sticky="w")

    tab.numerical_method_label = tk.Label(parent, text="Numerical Method:")
    tab.numerical_method_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
    tab.numerical_method_var = tk.StringVar(value="Trapezoidal")
    tab.numerical_method_dropdown = ttk.Combobox(
        parent,
        textvariable=tab.numerical_method_var,
        values=[
            "Trapezoidal",
            "Simpson",
            "Rectangle",
            "Romberg",
            "Gaussian Quadrature",
            "Simpson 3/8",
            "Adaptive Simpson",
            "Monte Carlo",
        ],
        state="readonly",
    )
    tab.numerical_method_dropdown.grid(row=7, column=1, padx=10, pady=5, sticky="w")

    tab.recommendation_label = tk.Label(parent, text="", fg="gray", justify="left", wraplength=520)
    tab.recommendation_label.grid(row=8, column=0, columnspan=2, padx=10, pady=(4, 2), sticky="w")

    tab.apply_recommendation_button = ttk.Button(
        parent,
        text="Apply Recommendation",
        command=tab.apply_recommendation,
    )
    tab.apply_recommendation_button.grid(row=9, column=0, columnspan=2, pady=(2, 8))

    action_frame = ttk.Frame(parent)
    action_frame.grid(row=10, column=0, columnspan=2, pady=10)
    tab.calc_button = ttk.Button(
        action_frame,
        text="Calculate Integral",
        command=tab.calculate,
    )
    tab.calc_button.pack(side=tk.LEFT, padx=(0, 8))

    tab.compare_button = ttk.Button(
        action_frame,
        text="Compare Methods",
        command=tab.compare_methods,
    )
    tab.compare_button.pack(side=tk.LEFT)

    tab.reset_button = ttk.Button(parent, text="Reset", command=tab.app.reset_inputs)
    tab.reset_button.grid(row=11, column=0, columnspan=2, pady=10)

    tab.result_label = tk.Label(parent, text="", fg="green", font=("Arial", 12))
    tab.result_label.grid(row=12, column=0, columnspan=2, pady=10)

    for entry in (tab.func_entry, tab.params_entry, tab.lower_entry, tab.upper_entry, tab.split_entry):
        entry.bind("<KeyRelease>", tab.schedule_recommendation)
        entry.bind("<Return>", lambda event: tab.calculate())
    tab.delta_entry.bind("<KeyRelease>", tab.schedule_recommendation)
    tab.delta_entry.bind("<Return>", lambda event: tab.calculate())
    for dropdown in (tab.method_dropdown, tab.numerical_method_dropdown):
        dropdown.bind("<<ComboboxSelected>>", tab.update_recommendation)
