"""Qt Math Tools dialog backed by the shared live-math editor contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from math_extensions import (
    analyze_function_properties,
    analyze_singularity_and_breakpoints,
    build_convergence_table,
    build_error_profile,
    build_piecewise_expression,
    compute_arc_length,
    compute_area_breakdown,
    compute_average_value,
    compute_double_integral,
    compute_fourier_series,
    compute_laplace_transform,
    compute_parameter_sensitivity,
    compute_polar_area,
    compute_polar_double_integral,
    compute_revolution_volume,
    compute_taylor_expansion,
    compute_triple_integral,
    compute_variable_double_integral,
    convergence_report,
    integration_by_parts_helper,
    parameter_assignment,
    solve_simple_ode,
    substitution_integral_helper,
    verify_antiderivative,
)
from qt_dialogs import show_error_dialog


@dataclass(frozen=True)
class FieldSpec:
    """Explicit declaration of one mathematical input or output field."""

    name: str
    label: str
    role: FieldRole
    default: str = ""
    enabled: bool = True


class UncappedLineEdit(QLineEdit):
    """A native text input without QLineEdit's short default length cap."""

    def __init__(
        self,
        default: str = "5",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(str(default), parent)
        self.setMaxLength(2_147_483_647)


class MathToolsDialog(QDialog):
    """All calculator Math Tools, migrated to live mathematical fields."""

    CATEGORIES = {
        "Basic": ("Polar Area", "Taylor", "Average / Area"),
        "Analysis": (
            "Convergence Table",
            "Analysis",
            "Convergence",
            "Error Plot",
            "Verify Antiderivative",
        ),
        "Builders": ("Piecewise Builder", "Parameter Slider"),
        "Calculus": ("Techniques", "Geometry"),
        "Advanced": ("Transforms / ODE", "Sensitivity"),
        "Multivariable": ("Double Integral", "More Integrals"),
    }
    CATEGORY_TEXT_KEYS = {
        "Basic": "math_tools_basic",
        "Analysis": "math_tools_analysis",
        "Builders": "math_tools_builders",
        "Calculus": "math_tools_calculus",
        "Advanced": "math_tools_advanced",
        "Multivariable": "math_tools_multi",
    }

    def __init__(
        self,
        insert_function: Callable[[str], object],
        insert_parameters: Callable[[str], object],
        parent: QWidget | None = None,
        *,
        initial_function: str = "",
        text: dict[str, object] | None = None,
        theme_name: str = "Light",
        panel_factory=MathEditorPanel,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.insert_function = insert_function
        self.insert_parameters = insert_parameters
        self.panel_factory = panel_factory
        self.initial_function = str(initial_function).strip()
        self.text = dict(text or {})
        self.theme_name = str(theme_name)
        self.math_fields: dict[str, object] = {}
        self.math_panels: dict[str, QWidget] = {}
        self.pages: dict[str, QWidget] = {}
        self.results: dict[str, QPlainTextEdit] = {}
        self.actions: dict[str, QPushButton] = {}
        self.native_controls: dict[str, QWidget] = {}
        self.category_tabs: dict[str, QTabWidget] = {}

        self.setWindowTitle(str(self.text.get("math_tools", "Math Tools")))
        self.resize(900, 680)
        self.tabs = QTabWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

        for category in self.CATEGORIES:
            notebook = QTabWidget(self.tabs)
            self.category_tabs[category] = notebook
            text_key = self.CATEGORY_TEXT_KEYS[category]
            self.tabs.addTab(notebook, str(self.text.get(text_key, category)))

        self._build_polar()
        self._build_taylor()
        self._build_average_area()
        self._build_convergence_table()
        self._build_analysis()
        self._build_convergence()
        self._build_error_profile()
        self._build_verification()
        self._build_piecewise()
        self._build_parameter_slider()
        self._build_techniques()
        self._build_geometry()
        self._build_transforms()
        self._build_sensitivity()
        self._build_double_integral()
        self._build_more_integrals()

    def _active_function_default(self, fallback: str) -> str:
        return self.initial_function or fallback

    def _page(
        self,
        category: str,
        title: str,
        specs: tuple[FieldSpec, ...],
        *,
        result: bool = True,
        minimum_editor_height: int | None = None,
    ) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(self)
        page_layout = QVBoxLayout(page)
        panel = self.panel_factory(page)
        panel_key = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        self.math_panels[panel_key] = panel
        for spec in specs:
            field = panel.create_field(
                spec.name,
                spec.role,
                spec.default,
                label=spec.label,
            )
            field.set_enabled(spec.enabled)
            self.math_fields[spec.name] = field
        panel.set_theme(self.theme_name)
        if minimum_editor_height is None:
            minimum_editor_height = max(90, 58 * len(specs))
        panel.setMinimumHeight(minimum_editor_height)
        page_layout.addWidget(panel)
        if result:
            output = QPlainTextEdit(page)
            output.setReadOnly(True)
            output.setObjectName(f"{panel_key}Result")
            output.setMinimumHeight(115)
            self.results[panel_key] = output
            page_layout.addWidget(output, stretch=1)
        page_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.category_tabs[category].addTab(scroll, title)
        self.pages[title] = page
        return page, page_layout

    def _field(self, name: str) -> str:
        return self.math_fields[name].get_text().strip()

    def _set_result(self, page: str, value: object) -> None:
        self.results[page].setPlainText(str(value))

    def _button(
        self,
        page: QWidget,
        layout: QVBoxLayout,
        action_id: str,
        label: str,
        callback: Callable[[], object],
    ) -> QPushButton:
        button = QPushButton(label, page)
        button.clicked.connect(lambda _checked=False: self._guard(label, callback))
        self.actions[action_id] = button
        layout.insertWidget(
            self._control_insertion_index(layout),
            button,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )
        return button

    def _guard(self, title: str, callback: Callable[[], object]) -> object | None:
        try:
            return callback()
        except Exception as exc:
            show_error_dialog(self, title, str(exc))
            return None

    def _native_form(self, page: QWidget, layout: QVBoxLayout) -> QFormLayout:
        form = QFormLayout()
        layout.insertLayout(self._control_insertion_index(layout), form)
        return form

    @staticmethod
    def _control_insertion_index(layout: QVBoxLayout) -> int:
        for index in range(layout.count()):
            if isinstance(layout.itemAt(index).widget(), QPlainTextEdit):
                return index
        return max(0, layout.count() - 1)

    def _build_polar(self) -> None:
        page, layout = self._page("Basic", "Polar Area", (
            FieldSpec("polar.radius", "r(theta):", FieldRole.EXPRESSION, "2*cos(theta)"),
            FieldSpec("polar.lower", "theta lower:", FieldRole.BOUND, "-pi/2"),
            FieldSpec("polar.upper", "theta upper:", FieldRole.BOUND, "pi/2"),
        ))

        def compute():
            result = compute_polar_area(
                self._field("polar.radius"), self._field("polar.lower"), self._field("polar.upper")
            )
            self._set_result("polar_area", "\n".join((
                "Polar area formula: A = 1/2 * integral r(theta)^2 dtheta",
                f"Integrand: {result['integrand']}",
                f"Exact area: {result['exact']}",
                f"Numeric area: {result['numeric']:.10g}",
            )))
            return result

        self._button(page, layout, "polar.compute", "Compute Polar Area", compute)

    def _build_taylor(self) -> None:
        page, layout = self._page("Basic", "Taylor", (
            FieldSpec(
                "taylor.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("sin(x)"),
            ),
            FieldSpec("taylor.point", "Expansion point:", FieldRole.BOUND, "0"),
        ))
        order = UncappedLineEdit("5", parent=page)
        self.native_controls["taylor.order"] = order
        self._native_form(page, layout).addRow("Order:", order)

        def compute():
            result = compute_taylor_expansion(
                self._field("taylor.function"),
                self._field("taylor.point"),
                order.text(),
            )
            self._set_result("taylor", "\n".join((
                f"Point: {result['point']}", f"Order: {result['order']}",
                f"Polynomial: {result['polynomial']}", f"Series: {result['series']}",
            )))
            return result

        self._button(page, layout, "taylor.compute", "Build Taylor Polynomial", compute)

    def _build_average_area(self) -> None:
        page, layout = self._page("Basic", "Average / Area", (
            FieldSpec(
                "average.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x"),
            ),
            FieldSpec("average.lower", "Lower:", FieldRole.BOUND, "-1"),
            FieldSpec("average.upper", "Upper:", FieldRole.BOUND, "1"),
        ))

        def compute():
            args = (self._field("average.function"), self._field("average.lower"), self._field("average.upper"))
            average = compute_average_value(*args)
            area = compute_area_breakdown(*args)
            self._set_result("average_area", "\n".join((
                f"Integral: {average['integral']}",
                f"Average value: {average['average']} ({average['numeric']:.10g})", "",
                f"Signed integral: {area['signed']:.12g}",
                f"Absolute area: {area['absolute']:.12g}",
                f"Positive area: {area['positive_area']:.12g}",
                f"Negative area: {area['negative_area']:.12g}",
            )))
            return average, area

        self._button(page, layout, "average.compute", "Compute Average and Area", compute)

    def _build_convergence_table(self) -> None:
        page, layout = self._page("Analysis", "Convergence Table", (
            FieldSpec(
                "table.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x^2"),
            ),
            FieldSpec("table.lower", "Lower:", FieldRole.BOUND, "0"),
            FieldSpec("table.upper", "Upper:", FieldRole.BOUND, "1"),
        ))
        method = QComboBox(page)
        method.addItems(("Trapezoidal", "Simpson", "Rectangle", "Gaussian Quadrature", "Adaptive Simpson"))
        intervals = QLineEdit("20,50,100,200", page)
        self.native_controls.update({"table.method": method, "table.intervals": intervals})
        form = self._native_form(page, layout)
        form.addRow("Method:", method)
        form.addRow("n values:", intervals)

        def compute():
            table = build_convergence_table(
                self._field("table.function"), self._field("table.lower"), self._field("table.upper"),
                method.currentText(), intervals.text(),
            )
            lines = [f"Reference: {table['reference']:.12g}", f"Method: {table['method']}"]
            lines.extend(
                f"n={row['n']:<5} value={row['value']:.12g} abs error={row['absolute_error']:.3e}"
                for row in table["rows"]
            )
            self._set_result("convergence_table", "\n".join(lines))
            return table

        self._button(page, layout, "table.compute", "Build Table", compute)

    def _build_analysis(self) -> None:
        page, layout = self._page("Analysis", "Analysis", (
            FieldSpec(
                "analysis.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x^2-1"),
            ),
            FieldSpec("analysis.lower", "Lower:", FieldRole.BOUND, "-2"),
            FieldSpec("analysis.upper", "Upper:", FieldRole.BOUND, "2"),
        ))

        def compute():
            args = (self._field("analysis.function"), self._field("analysis.lower"), self._field("analysis.upper"))
            singular = analyze_singularity_and_breakpoints(*args)
            props = analyze_function_properties(*args)
            self._set_result("analysis", "\n".join((
                singular["summary"], "", f"Domain: {props['domain']}",
                f"Derivative: {props['derivative']}", f"Second derivative: {props['second_derivative']}",
                f"Roots: {props['roots'] or ['none']}",
                f"Critical points: {props['critical_points'] or ['none']}",
                f"Inflection points: {props['inflection_points'] or ['none']}",
            )))
            return singular, props

        self._button(page, layout, "analysis.compute", "Analyze Function", compute)

    def _build_convergence(self) -> None:
        page, layout = self._page("Analysis", "Convergence", (
            FieldSpec(
                "convergence.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("exp(-x)"),
            ),
            FieldSpec("convergence.lower", "Lower:", FieldRole.BOUND, "0"),
            FieldSpec("convergence.upper", "Upper:", FieldRole.BOUND, "inf"),
        ))

        def compute():
            report = convergence_report(
                self._field("convergence.function"), self._field("convergence.lower"),
                self._field("convergence.upper")
            )
            self._set_result("convergence", report["summary"])
            return report

        self._button(page, layout, "convergence.compute", "Check Convergence", compute)

    def _build_error_profile(self) -> None:
        page, layout = self._page("Analysis", "Error Plot", (
            FieldSpec(
                "error.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x^2"),
            ),
            FieldSpec("error.lower", "Lower:", FieldRole.BOUND, "0"),
            FieldSpec("error.upper", "Upper:", FieldRole.BOUND, "1"),
        ))
        self.error_figure = Figure(figsize=(5.5, 2.4), dpi=100)
        self.error_axes = self.error_figure.add_subplot(111)
        self.error_canvas = FigureCanvasQTAgg(self.error_figure)
        layout.insertWidget(max(0, layout.count() - 1), self.error_canvas, stretch=2)

        def compute():
            profile = build_error_profile(
                self._field("error.function"), self._field("error.lower"), self._field("error.upper")
            )
            rows = profile["rows"]
            self._set_result("error_plot", "\n".join(
                [f"Reference value: {profile['reference']:.12g}"] + [
                    f"{row['method']}: value={row['value']:.12g}, abs error={row['absolute_error']:.3e}"
                    for row in rows
                ]
            ))
            self.error_axes.clear()
            self.error_axes.bar(
                [row["method"] for row in rows],
                [max(row["absolute_error"], 1e-18) for row in rows],
            )
            self.error_axes.set_yscale("log")
            self.error_axes.set_ylabel("Absolute error")
            self.error_axes.tick_params(axis="x", labelrotation=25)
            self.error_figure.tight_layout()
            self.error_canvas.draw_idle()
            return profile

        self._button(page, layout, "error.compute", "Build Error Plot", compute)

    def _build_verification(self) -> None:
        page, layout = self._page("Analysis", "Verify Antiderivative", (
            FieldSpec("verify.function", "Integrand:", FieldRole.EXPRESSION, "sin(x)"),
            FieldSpec("verify.antiderivative", "Candidate antiderivative:", FieldRole.EXPRESSION, "-cos(x)"),
        ))

        def compute():
            result = verify_antiderivative(
                self._field("verify.function"), self._field("verify.antiderivative")
            )
            status = "Verified" if result["ok"] else "Not verified"
            self._set_result("verify_antiderivative", f"{status}. Difference: {result['difference']}")
            return result

        self._button(page, layout, "verify.compute", "Verify Antiderivative", compute)

    def _build_piecewise(self) -> None:
        specs: list[FieldSpec] = []
        defaults = (("x", "x<0"), ("x^2", "True"), ("", ""))
        for index, (expression, condition) in enumerate(defaults, 1):
            specs.extend((
                FieldSpec(f"piecewise.expression{index}", f"Expression {index}:", FieldRole.EXPRESSION, expression),
                FieldSpec(f"piecewise.condition{index}", f"Condition {index}:", FieldRole.EXPRESSION, condition),
            ))
        specs.append(FieldSpec(
            "piecewise.result", "Generated expression:", FieldRole.EXPRESSION, "", enabled=False
        ))
        page, layout = self._page(
            "Builders", "Piecewise Builder", tuple(specs), result=False, minimum_editor_height=430
        )

        def build():
            pieces = [
                (self._field(f"piecewise.expression{i}"), self._field(f"piecewise.condition{i}"))
                for i in range(1, 4)
            ]
            expression = build_piecewise_expression(pieces)
            self.math_fields["piecewise.result"].set_text(expression)
            return expression

        def insert():
            expression = build()
            self.insert_function(expression)
            return expression

        self._button(page, layout, "piecewise.build", "Build Piecewise", build)
        self._button(page, layout, "piecewise.insert", "Insert Into Current Tab", insert)

    def build_piecewise_for_test(self, pieces: list[tuple[str, str]]) -> str:
        expression = build_piecewise_expression(pieces)
        self.math_fields["piecewise.result"].set_text(expression)
        self.insert_function(expression)
        return expression

    def _build_parameter_slider(self) -> None:
        page, layout = self._page("Builders", "Parameter Slider", (
            FieldSpec(
                "parameter.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("a*x^2"),
            ),
            FieldSpec("parameter.assignment", "Current assignment:", FieldRole.PARAMETERS, "a=1", enabled=False),
        ), result=False)
        name = QLineEdit("a", page)
        minimum = QDoubleSpinBox(page)
        maximum = QDoubleSpinBox(page)
        for spin in (minimum, maximum):
            spin.setRange(-1_000_000, 1_000_000)
            spin.setDecimals(6)
        minimum.setValue(0)
        maximum.setValue(5)
        slider = QSlider(Qt.Orientation.Horizontal, page)
        slider.setRange(0, 1000)
        slider.setValue(200)
        value_label = QLabel("a=1", page)
        self.native_controls.update({
            "parameter.name": name, "parameter.minimum": minimum,
            "parameter.maximum": maximum, "parameter.slider": slider,
            "parameter.value_label": value_label,
        })
        form = self._native_form(page, layout)
        form.addRow("Parameter:", name)
        form.addRow("Minimum:", minimum)
        form.addRow("Maximum:", maximum)
        form.addRow(value_label, slider)

        def current_value() -> float:
            return minimum.value() + (maximum.value() - minimum.value()) * slider.value() / 1000.0

        def apply_value():
            assignment = parameter_assignment(name.text(), current_value())
            value_label.setText(assignment)
            self.math_fields["parameter.assignment"].set_text(assignment)
            self.insert_function(self._field("parameter.function"))
            self.insert_parameters(assignment)
            return assignment

        def update_range():
            if minimum.value() >= maximum.value():
                raise ValueError("Maximum must be greater than minimum.")
            return apply_value()

        slider.valueChanged.connect(lambda _value: self._guard("Parameter Slider", apply_value))
        self._button(page, layout, "parameter.range", "Update Range", update_range)
        self._button(page, layout, "parameter.apply", "Apply Value", apply_value)
        self._parameter_apply = apply_value

    def _build_techniques(self) -> None:
        page, layout = self._page("Calculus", "Techniques", (
            FieldSpec("techniques.function", "Integrand:", FieldRole.EXPRESSION, "2*x*cos(x^2)"),
            FieldSpec("techniques.substitution", "Substitution:", FieldRole.EQUATION, "u=x^2"),
            FieldSpec("techniques.u", "By parts u:", FieldRole.EXPRESSION, "x"),
            FieldSpec("techniques.dv", "By parts dv:", FieldRole.EXPRESSION, "exp(x)"),
        ))

        def substitution():
            result = substitution_integral_helper(
                self._field("techniques.function"), self._field("techniques.substitution")
            )
            self._set_result("techniques", "\n".join((
                "Substitution helper", f"u = {result['u']}", f"du/dx = {result['du_dx']}",
                f"x(u) = {result['x_of_u']}", f"Transformed integrand: {result['transformed_integrand']}",
            )))
            return result

        def by_parts():
            result = integration_by_parts_helper(
                self._field("techniques.u"), self._field("techniques.dv")
            )
            self._set_result("techniques", "\n".join((
                "Integration by parts", f"u = {result['u']}", f"du = {result['du']} dx",
                f"dv = {result['dv']} dx", f"v = {result['v']}",
                f"Remaining integrand v*du: {result['remaining_integrand']}",
                f"Result: {result['result']} + C",
            )))
            return result

        self._button(page, layout, "techniques.substitute", "Show Substitution", substitution)
        self._button(page, layout, "techniques.parts", "Show By Parts", by_parts)

    def _build_geometry(self) -> None:
        page, layout = self._page("Calculus", "Geometry", (
            FieldSpec(
                "geometry.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x"),
            ),
            FieldSpec("geometry.lower", "Lower:", FieldRole.BOUND, "0"),
            FieldSpec("geometry.upper", "Upper:", FieldRole.BOUND, "1"),
        ))
        axis = QComboBox(page)
        axis.addItems(("x", "y"))
        self.native_controls["geometry.axis"] = axis
        self._native_form(page, layout).addRow("Volume axis:", axis)

        def compute():
            args = (self._field("geometry.function"), self._field("geometry.lower"), self._field("geometry.upper"))
            arc = compute_arc_length(*args)
            volume = compute_revolution_volume(*args, axis.currentText())
            self._set_result("geometry", "\n".join((
                "Arc length", f"Integrand: {arc['integrand']}", f"Exact: {arc['exact']}",
                f"Numeric: {arc['numeric']:.10g}", "", "Volume of revolution",
                f"Integrand: {volume['integrand']}", f"Exact: {volume['exact']}",
                f"Numeric: {volume['numeric']:.10g}",
            )))
            return arc, volume

        self._button(page, layout, "geometry.compute", "Compute Geometry", compute)

    def _build_transforms(self) -> None:
        page, layout = self._page("Advanced", "Transforms / ODE", (
            FieldSpec("transforms.function", "Function:", FieldRole.EXPRESSION, "exp(-x)"),
            FieldSpec("transforms.period", "Fourier period:", FieldRole.BOUND, "2*pi"),
            FieldSpec("transforms.ode", "ODE:", FieldRole.EQUATION, "y'=x*y"),
        ))
        terms = UncappedLineEdit("5", parent=page)
        self.native_controls["transforms.terms"] = terms
        self._native_form(page, layout).addRow("Fourier terms:", terms)

        def fourier():
            result = compute_fourier_series(
                self._field("transforms.function"),
                self._field("transforms.period"),
                terms.text(),
            )
            self._set_result("transforms_ode", f"Fourier series approximation:\n{result['series']}")
            return result

        def laplace():
            result = compute_laplace_transform(self._field("transforms.function"))
            self._set_result(
                "transforms_ode", f"Laplace transform:\n{result['transform']}\n\nInverse transform:\n{result['inverse']}"
            )
            return result

        def ode():
            result = solve_simple_ode(self._field("transforms.ode"))
            self._set_result("transforms_ode", f"Equation:\n{result['equation']}\n\nSolution:\n{result['solution']}")
            return result

        self._button(page, layout, "transforms.fourier", "Fourier", fourier)
        self._button(page, layout, "transforms.laplace", "Laplace", laplace)
        self._button(page, layout, "transforms.ode", "Solve ODE", ode)

    def _build_sensitivity(self) -> None:
        page, layout = self._page("Advanced", "Sensitivity", (
            FieldSpec("sensitivity.function", "Function:", FieldRole.EXPRESSION, "a*x"),
            FieldSpec("sensitivity.lower", "Lower:", FieldRole.BOUND, "0"),
            FieldSpec("sensitivity.upper", "Upper:", FieldRole.BOUND, "1"),
        ))
        parameter = QLineEdit("a", page)
        values = QLineEdit("1,2,3", page)
        self.native_controls.update({"sensitivity.parameter": parameter, "sensitivity.values": values})
        form = self._native_form(page, layout)
        form.addRow("Parameter:", parameter)
        form.addRow("Values:", values)

        def compute():
            rows = compute_parameter_sensitivity(
                self._field("sensitivity.function"), parameter.text(), values.text(),
                self._field("sensitivity.lower"), self._field("sensitivity.upper"),
            )
            self._set_result("sensitivity", "\n".join(
                f"{parameter.text()}={row['parameter']}: integral={row['integral']} ({row['numeric']:.10g})"
                for row in rows
            ))
            return rows

        self._button(page, layout, "sensitivity.compute", "Analyze Sensitivity", compute)

    def _build_double_integral(self) -> None:
        page, layout = self._page("Multivariable", "Double Integral", (
            FieldSpec("double.function", "f(x, y):", FieldRole.EXPRESSION, "x+y"),
            FieldSpec("double.x_lower", "x lower:", FieldRole.BOUND, "0"),
            FieldSpec("double.x_upper", "x upper:", FieldRole.BOUND, "1"),
            FieldSpec("double.y_lower", "y lower:", FieldRole.BOUND, "0"),
            FieldSpec("double.y_upper", "y upper:", FieldRole.BOUND, "1"),
        ))

        def compute():
            result = compute_double_integral(*(
                self._field(name) for name in (
                    "double.function", "double.x_lower", "double.x_upper", "double.y_lower", "double.y_upper"
                )
            ))
            self._set_result("double_integral", f"Exact result: {result['exact']}\nNumeric result: {result['numeric']:.10g}")
            return result

        self._button(page, layout, "double.compute", "Compute Double Integral", compute)

    def _build_more_integrals(self) -> None:
        page, layout = self._page("Multivariable", "More Integrals", (
            FieldSpec("multi.function", "Function:", FieldRole.EXPRESSION, "1"),
            FieldSpec("multi.a", "x/theta lower:", FieldRole.BOUND, "0"),
            FieldSpec("multi.b", "x/theta upper:", FieldRole.BOUND, "1"),
            FieldSpec("multi.c", "y/r lower:", FieldRole.BOUND, "0"),
            FieldSpec("multi.d", "y/r upper:", FieldRole.BOUND, "x"),
            FieldSpec("multi.e", "z lower:", FieldRole.BOUND, "0"),
            FieldSpec("multi.f", "z upper:", FieldRole.BOUND, "1"),
        ), minimum_editor_height=430)
        mode = QComboBox(page)
        mode.addItems(("Variable double", "Polar double", "Triple"))
        self.native_controls["multi.mode"] = mode
        self._native_form(page, layout).addRow("Mode:", mode)

        def compute():
            function = self._field("multi.function")
            values = [self._field(f"multi.{name}") for name in "abcdef"]
            if mode.currentText() == "Variable double":
                result = compute_variable_double_integral(function, *values[:4])
            elif mode.currentText() == "Polar double":
                result = compute_polar_double_integral(function, values[2], values[3], values[0], values[1])
            else:
                result = compute_triple_integral(function, *values)
            self._set_result("more_integrals", f"Exact result: {result['exact']}\nNumeric result: {result['numeric']:.10g}")
            return result

        self._button(page, layout, "multi.compute", "Compute", compute)


__all__ = ["FieldSpec", "MathToolsDialog", "UncappedLineEdit"]
