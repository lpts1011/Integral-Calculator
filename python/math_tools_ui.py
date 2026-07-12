import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from math_extensions import (
    analyze_function_properties,
    analyze_singularity_and_breakpoints,
    build_error_profile,
    build_convergence_table,
    build_piecewise_expression,
    compute_arc_length,
    compute_area_breakdown,
    compute_average_value,
    compute_double_integral,
    compute_fourier_series,
    compute_laplace_transform,
    compute_polar_area,
    compute_polar_double_integral,
    compute_revolution_volume,
    compute_taylor_expansion,
    compute_triple_integral,
    compute_variable_double_integral,
    convergence_report,
    integration_by_parts_helper,
    parameter_assignment,
    compute_parameter_sensitivity,
    solve_simple_ode,
    substitution_integral_helper,
)


def show_math_tools_window(app):
    window = tk.Toplevel(app.root)
    text = getattr(app, "text", {})
    window.title(text.get("math_tools", "Math Tools"))
    window.geometry("760x560")

    category_notebook = ttk.Notebook(window)
    category_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_basic", "Basic"),
        (_build_polar_tab, _build_taylor_tab, _build_average_area_tab),
    )
    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_analysis", "Analysis"),
        (_build_convergence_table_tab, _build_analysis_tab, _build_convergence_tab, _build_error_tab),
    )
    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_builders", "Builders"),
        (_build_piecewise_tab, _build_parameter_tab),
    )
    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_calculus", "Calculus"),
        (_build_techniques_tab, _build_geometry_tab),
    )
    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_advanced", "Advanced"),
        (_build_transforms_ode_tab, _build_sensitivity_tab),
    )
    _add_tool_category(
        app,
        category_notebook,
        text.get("math_tools_multi", "Multivariable"),
        (_build_double_integral_tab, _build_more_integrals_tab),
    )

    app.apply_theme(app.theme_name)
    return window


def _add_tool_category(app, parent, title, builders):
    frame = ttk.Frame(parent)
    parent.add(frame, text=title)
    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
    for builder in builders:
        builder(app, notebook)
    return notebook


def _build_result_box(parent, row, height=6, columnspan=2):
    box = tk.Text(parent, height=height, wrap="word")
    box.grid(row=row, column=0, columnspan=columnspan, sticky="nsew", padx=8, pady=8)
    parent.rowconfigure(row, weight=1)
    return box


def _set_text(widget, text):
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)


def _grid_entry(parent, label, row, default="", width=22):
    ttk.Label(parent, text=label).grid(row=row, column=0, padx=8, pady=5, sticky="w")
    entry = ttk.Entry(parent, width=width)
    entry.insert(0, default)
    entry.grid(row=row, column=1, padx=8, pady=5, sticky="ew")
    return entry


def _active_function(app, fallback="x^2"):
    try:
        value = app.active_tab().get_function_text().strip()
        return value or fallback
    except Exception:
        return fallback


def _build_polar_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Polar Area")
    frame.columnconfigure(1, weight=1)

    radius_entry = _grid_entry(frame, "r(theta):", 0, "2*cos(theta)")
    lower_entry = _grid_entry(frame, "theta lower:", 1, "-pi/2")
    upper_entry = _grid_entry(frame, "theta upper:", 2, "pi/2")
    result_box = _build_result_box(frame, row=4)

    def compute():
        try:
            result = compute_polar_area(radius_entry.get(), lower_entry.get(), upper_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    "Polar area formula: A = 1/2 * integral r(theta)^2 dtheta",
                    f"Integrand: {result['integrand']}",
                    f"Exact area: {result['exact']}",
                    f"Numeric area: {result['numeric']:.10g}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Polar Area", str(exc))

    ttk.Button(frame, text="Compute Polar Area", command=compute).grid(
        row=3, column=0, columnspan=2, pady=8
    )


def _build_taylor_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Taylor")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "sin(x)"))
    point_entry = _grid_entry(frame, "Expansion point:", 1, "0")
    order_entry = _grid_entry(frame, "Order:", 2, "5")
    result_box = _build_result_box(frame, row=4)

    def compute():
        try:
            result = compute_taylor_expansion(func_entry.get(), point_entry.get(), order_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    f"Point: {result['point']}",
                    f"Order: {result['order']}",
                    f"Polynomial: {result['polynomial']}",
                    f"Series: {result['series']}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Taylor", str(exc))

    ttk.Button(frame, text="Build Taylor Polynomial", command=compute).grid(
        row=3, column=0, columnspan=2, pady=8
    )


def _build_convergence_table_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Convergence Table")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "x^2"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "0")
    upper_entry = _grid_entry(frame, "Upper:", 2, "1")
    method_entry = _grid_entry(frame, "Method:", 3, "Trapezoidal")
    intervals_entry = _grid_entry(frame, "n values:", 4, "20,50,100,200")
    result_box = _build_result_box(frame, row=6)

    def compute():
        try:
            table = build_convergence_table(
                func_entry.get(),
                lower_entry.get(),
                upper_entry.get(),
                method_entry.get(),
                intervals_entry.get(),
            )
            lines = [f"Reference: {table['reference']:.12g}", f"Method: {table['method']}"]
            for row in table["rows"]:
                lines.append(
                    f"n={row['n']:<5} value={row['value']:.12g} "
                    f"abs error={row['absolute_error']:.3e}"
                )
            _set_text(result_box, "\n".join(lines))
        except Exception as exc:
            messagebox.showerror("Convergence Table", str(exc))

    ttk.Button(frame, text="Build Table", command=compute).grid(row=5, column=0, columnspan=2, pady=8)


def _build_analysis_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Analysis")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "x^2-1"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "-2")
    upper_entry = _grid_entry(frame, "Upper:", 2, "2")
    result_box = _build_result_box(frame, row=4)

    def compute():
        try:
            singular = analyze_singularity_and_breakpoints(func_entry.get(), lower_entry.get(), upper_entry.get())
            props = analyze_function_properties(func_entry.get(), lower_entry.get(), upper_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    singular["summary"],
                    "",
                    f"Domain: {props['domain']}",
                    f"Derivative: {props['derivative']}",
                    f"Second derivative: {props['second_derivative']}",
                    f"Roots: {props['roots'] or ['none']}",
                    f"Critical points: {props['critical_points'] or ['none']}",
                    f"Inflection points: {props['inflection_points'] or ['none']}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Analysis", str(exc))

    ttk.Button(frame, text="Analyze Function", command=compute).grid(row=3, column=0, columnspan=2, pady=8)


def _build_piecewise_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Piecewise Builder")
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Expression").grid(row=0, column=0, padx=8, pady=5, sticky="w")
    ttk.Label(frame, text="Condition").grid(row=0, column=1, padx=8, pady=5, sticky="w")
    defaults = [("x", "x < 0"), ("x^2", "True"), ("", "")]
    rows = []
    for index, (expr_default, condition_default) in enumerate(defaults, start=1):
        expr_entry = ttk.Entry(frame)
        expr_entry.insert(0, expr_default)
        expr_entry.grid(row=index, column=0, padx=8, pady=4, sticky="ew")
        condition_entry = ttk.Entry(frame)
        condition_entry.insert(0, condition_default)
        condition_entry.grid(row=index, column=1, padx=8, pady=4, sticky="ew")
        rows.append((expr_entry, condition_entry))

    result_var = tk.StringVar(value="")
    ttk.Entry(frame, textvariable=result_var).grid(row=5, column=0, columnspan=2, padx=8, pady=8, sticky="ew")

    def build():
        try:
            expression = build_piecewise_expression(
                [(expr.get(), condition.get()) for expr, condition in rows]
            )
            result_var.set(expression)
        except Exception as exc:
            messagebox.showerror("Piecewise Builder", str(exc))

    def insert():
        if not result_var.get():
            build()
        if result_var.get():
            app.active_tab().set_function_text(result_var.get())

    ttk.Button(frame, text="Build Piecewise", command=build).grid(row=4, column=0, padx=8, pady=8)
    ttk.Button(frame, text="Insert Into Current Tab", command=insert).grid(row=4, column=1, padx=8, pady=8)


def _build_parameter_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Parameter Slider")
    frame.columnconfigure(1, weight=1)

    function_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "a*x^2"))
    parameter_entry = _grid_entry(frame, "Parameter:", 1, "a", width=10)
    min_entry = _grid_entry(frame, "Minimum:", 2, "0", width=10)
    max_entry = _grid_entry(frame, "Maximum:", 3, "5", width=10)
    value_var = tk.DoubleVar(value=1.0)
    value_label = ttk.Label(frame, text="a=1")
    value_label.grid(row=4, column=0, padx=8, pady=5, sticky="w")
    slider = ttk.Scale(frame, from_=0, to=5, variable=value_var)
    slider.grid(row=4, column=1, padx=8, pady=5, sticky="ew")

    def apply_value(*_):
        try:
            assignment = parameter_assignment(parameter_entry.get(), value_var.get())
            value_label.config(text=assignment)
            tab = app.active_tab()
            tab.set_function_text(function_entry.get())
            if not tab.set_parameter_text(assignment):
                messagebox.showinfo("Parameter Slider", "The active tab does not support parameters.")
        except Exception as exc:
            messagebox.showerror("Parameter Slider", str(exc))

    def update_range():
        try:
            slider.config(from_=float(min_entry.get()), to=float(max_entry.get()))
            apply_value()
        except Exception as exc:
            messagebox.showerror("Parameter Slider", str(exc))

    slider.config(command=lambda _value: apply_value())
    ttk.Button(frame, text="Update Range", command=update_range).grid(row=5, column=0, padx=8, pady=8)
    ttk.Button(frame, text="Apply Value", command=apply_value).grid(row=5, column=1, padx=8, pady=8, sticky="w")


def _build_average_area_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Average / Area")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "x"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "-1")
    upper_entry = _grid_entry(frame, "Upper:", 2, "1")
    result_box = _build_result_box(frame, row=4)

    def compute():
        try:
            average = compute_average_value(func_entry.get(), lower_entry.get(), upper_entry.get())
            area = compute_area_breakdown(func_entry.get(), lower_entry.get(), upper_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    f"Integral: {average['integral']}",
                    f"Average value: {average['average']} ({average['numeric']:.10g})",
                    "",
                    f"Signed integral: {area['signed']:.12g}",
                    f"Absolute area: {area['absolute']:.12g}",
                    f"Positive area: {area['positive_area']:.12g}",
                    f"Negative area: {area['negative_area']:.12g}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Average / Area", str(exc))

    ttk.Button(frame, text="Compute Average and Area", command=compute).grid(
        row=3, column=0, columnspan=2, pady=8
    )


def _build_techniques_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Techniques")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Integrand:", 0, "2*x*cos(x^2)")
    substitution_entry = _grid_entry(frame, "Substitution:", 1, "u=x^2")
    u_entry = _grid_entry(frame, "By parts u:", 2, "x")
    dv_entry = _grid_entry(frame, "By parts dv:", 3, "exp(x)")
    result_box = _build_result_box(frame, row=5)

    def substitution():
        try:
            result = substitution_integral_helper(func_entry.get(), substitution_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    "Substitution helper",
                    f"u = {result['u']}",
                    f"du/dx = {result['du_dx']}",
                    f"x(u) = {result['x_of_u']}",
                    f"Transformed integrand: {result['transformed_integrand']}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Substitution", str(exc))

    def by_parts():
        try:
            result = integration_by_parts_helper(u_entry.get(), dv_entry.get())
            _set_text(
                result_box,
                "\n".join([
                    "Integration by parts",
                    f"u = {result['u']}",
                    f"du = {result['du']} dx",
                    f"dv = {result['dv']} dx",
                    f"v = {result['v']}",
                    f"Remaining integrand v*du: {result['remaining_integrand']}",
                    f"Result: {result['result']} + C",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Integration by Parts", str(exc))

    ttk.Button(frame, text="Show Substitution", command=substitution).grid(row=4, column=0, padx=8, pady=8)
    ttk.Button(frame, text="Show By Parts", command=by_parts).grid(row=4, column=1, padx=8, pady=8, sticky="w")


def _build_geometry_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Geometry")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "x"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "0")
    upper_entry = _grid_entry(frame, "Upper:", 2, "1")
    axis_entry = _grid_entry(frame, "Volume axis:", 3, "x", width=8)
    result_box = _build_result_box(frame, row=5)

    def compute():
        try:
            arc = compute_arc_length(func_entry.get(), lower_entry.get(), upper_entry.get())
            volume = compute_revolution_volume(
                func_entry.get(),
                lower_entry.get(),
                upper_entry.get(),
                axis_entry.get(),
            )
            _set_text(
                result_box,
                "\n".join([
                    "Arc length",
                    f"Integrand: {arc['integrand']}",
                    f"Exact: {arc['exact']}",
                    f"Numeric: {arc['numeric']:.10g}",
                    "",
                    "Volume of revolution",
                    f"Integrand: {volume['integrand']}",
                    f"Exact: {volume['exact']}",
                    f"Numeric: {volume['numeric']:.10g}",
                ]),
            )
        except Exception as exc:
            messagebox.showerror("Geometry", str(exc))

    ttk.Button(frame, text="Compute Geometry", command=compute).grid(row=4, column=0, columnspan=2, pady=8)


def _build_transforms_ode_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Transforms / ODE")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, "exp(-x)")
    period_entry = _grid_entry(frame, "Fourier period:", 1, "2*pi")
    terms_entry = _grid_entry(frame, "Fourier terms:", 2, "5")
    ode_entry = _grid_entry(frame, "ODE:", 3, "y' = x*y")
    result_box = _build_result_box(frame, row=5)

    def fourier():
        try:
            result = compute_fourier_series(func_entry.get(), period_entry.get(), terms_entry.get())
            _set_text(result_box, f"Fourier series approximation:\n{result['series']}")
        except Exception as exc:
            messagebox.showerror("Fourier Series", str(exc))

    def laplace():
        try:
            result = compute_laplace_transform(func_entry.get())
            _set_text(
                result_box,
                f"Laplace transform:\n{result['transform']}\n\nInverse transform:\n{result['inverse']}",
            )
        except Exception as exc:
            messagebox.showerror("Laplace Transform", str(exc))

    def ode():
        try:
            result = solve_simple_ode(ode_entry.get())
            _set_text(result_box, f"Equation:\n{result['equation']}\n\nSolution:\n{result['solution']}")
        except Exception as exc:
            messagebox.showerror("ODE Solver", str(exc))

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=4, column=0, columnspan=2, pady=8)
    ttk.Button(button_frame, text="Fourier", command=fourier).pack(side=tk.LEFT, padx=4)
    ttk.Button(button_frame, text="Laplace", command=laplace).pack(side=tk.LEFT, padx=4)
    ttk.Button(button_frame, text="Solve ODE", command=ode).pack(side=tk.LEFT, padx=4)


def _build_convergence_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Convergence")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "exp(-x)"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "0")
    upper_entry = _grid_entry(frame, "Upper:", 2, "inf")
    result_box = _build_result_box(frame, row=4)

    def compute():
        try:
            report = convergence_report(func_entry.get(), lower_entry.get(), upper_entry.get())
            _set_text(result_box, report["summary"])
        except Exception as exc:
            messagebox.showerror("Convergence", str(exc))

    ttk.Button(frame, text="Check Convergence", command=compute).grid(row=3, column=0, columnspan=2, pady=8)


def _build_error_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Error Plot")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, _active_function(app, "x^2"))
    lower_entry = _grid_entry(frame, "Lower:", 1, "0")
    upper_entry = _grid_entry(frame, "Upper:", 2, "1")
    result_box = _build_result_box(frame, row=4, height=5)
    figure = Figure(figsize=(5.5, 2.4), dpi=100)
    ax = figure.add_subplot(111)
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.get_tk_widget().grid(row=5, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
    frame.rowconfigure(5, weight=2)

    def compute():
        try:
            profile = build_error_profile(func_entry.get(), lower_entry.get(), upper_entry.get())
            rows = profile["rows"]
            _set_text(
                result_box,
                "\n".join(
                    [f"Reference value: {profile['reference']:.12g}"]
                    + [
                        f"{row['method']}: value={row['value']:.12g}, abs error={row['absolute_error']:.3e}"
                        for row in rows
                    ]
                ),
            )
            ax.clear()
            methods = [row["method"] for row in rows]
            errors = [max(row["absolute_error"], 1e-18) for row in rows]
            ax.bar(methods, errors)
            ax.set_yscale("log")
            ax.set_ylabel("Absolute error")
            ax.tick_params(axis="x", labelrotation=25)
            figure.tight_layout()
            canvas.draw_idle()
        except Exception as exc:
            messagebox.showerror("Error Plot", str(exc))

    ttk.Button(frame, text="Build Error Plot", command=compute).grid(row=3, column=0, columnspan=2, pady=8)


def _build_double_integral_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Double Integral")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "f(x, y):", 0, "x + y")
    x_lower_entry = _grid_entry(frame, "x lower:", 1, "0")
    x_upper_entry = _grid_entry(frame, "x upper:", 2, "1")
    y_lower_entry = _grid_entry(frame, "y lower:", 3, "0")
    y_upper_entry = _grid_entry(frame, "y upper:", 4, "1")
    result_box = _build_result_box(frame, row=6)

    def compute():
        try:
            result = compute_double_integral(
                func_entry.get(),
                x_lower_entry.get(),
                x_upper_entry.get(),
                y_lower_entry.get(),
                y_upper_entry.get(),
            )
            _set_text(
                result_box,
                f"Exact result: {result['exact']}\nNumeric result: {result['numeric']:.10g}",
            )
        except Exception as exc:
            messagebox.showerror("Double Integral", str(exc))

    ttk.Button(frame, text="Compute Double Integral", command=compute).grid(
        row=5, column=0, columnspan=2, pady=8
    )


def _build_more_integrals_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="More Integrals")
    frame.columnconfigure(1, weight=1)

    mode_var = tk.StringVar(value="Variable double")
    ttk.Label(frame, text="Mode:").grid(row=0, column=0, padx=8, pady=5, sticky="w")
    mode_box = ttk.Combobox(
        frame,
        textvariable=mode_var,
        values=("Variable double", "Polar double", "Triple"),
        state="readonly",
    )
    mode_box.grid(row=0, column=1, padx=8, pady=5, sticky="ew")

    func_entry = _grid_entry(frame, "Function:", 1, "1")
    a_entry = _grid_entry(frame, "x/theta lower:", 2, "0")
    b_entry = _grid_entry(frame, "x/theta upper:", 3, "1")
    c_entry = _grid_entry(frame, "y/r lower:", 4, "0")
    d_entry = _grid_entry(frame, "y/r upper:", 5, "x")
    e_entry = _grid_entry(frame, "z lower:", 6, "0")
    f_entry = _grid_entry(frame, "z upper:", 7, "1")
    result_box = _build_result_box(frame, row=9)

    def compute():
        try:
            mode = mode_var.get()
            if mode == "Variable double":
                result = compute_variable_double_integral(
                    func_entry.get(),
                    a_entry.get(),
                    b_entry.get(),
                    c_entry.get(),
                    d_entry.get(),
                )
            elif mode == "Polar double":
                result = compute_polar_double_integral(
                    func_entry.get(),
                    c_entry.get(),
                    d_entry.get(),
                    a_entry.get(),
                    b_entry.get(),
                )
            else:
                result = compute_triple_integral(
                    func_entry.get(),
                    a_entry.get(),
                    b_entry.get(),
                    c_entry.get(),
                    d_entry.get(),
                    e_entry.get(),
                    f_entry.get(),
                )
            _set_text(result_box, f"Exact result: {result['exact']}\nNumeric result: {result['numeric']:.10g}")
        except Exception as exc:
            messagebox.showerror("More Integrals", str(exc))

    ttk.Button(frame, text="Compute", command=compute).grid(row=8, column=0, columnspan=2, pady=8)


def _build_sensitivity_tab(app, notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Sensitivity")
    frame.columnconfigure(1, weight=1)

    func_entry = _grid_entry(frame, "Function:", 0, "a*x")
    parameter_entry = _grid_entry(frame, "Parameter:", 1, "a", width=10)
    values_entry = _grid_entry(frame, "Values:", 2, "1,2,3")
    lower_entry = _grid_entry(frame, "Lower:", 3, "0")
    upper_entry = _grid_entry(frame, "Upper:", 4, "1")
    result_box = _build_result_box(frame, row=6)

    def compute():
        try:
            rows = compute_parameter_sensitivity(
                func_entry.get(),
                parameter_entry.get(),
                values_entry.get(),
                lower_entry.get(),
                upper_entry.get(),
            )
            _set_text(
                result_box,
                "\n".join(
                    f"{parameter_entry.get()}={row['parameter']}: "
                    f"integral={row['integral']} ({row['numeric']:.10g})"
                    for row in rows
                ),
            )
        except Exception as exc:
            messagebox.showerror("Sensitivity", str(exc))

    ttk.Button(frame, text="Analyze Sensitivity", command=compute).grid(
        row=5, column=0, columnspan=2, pady=8
    )
