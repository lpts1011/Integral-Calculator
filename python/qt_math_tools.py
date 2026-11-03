"""Math Tools: integration helpers listed in one window."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from math_extensions import (
    build_piecewise_expression,
    compute_average_and_area,
    compute_fourier_series,
    compute_geometry_bundle,
    compute_laplace_transform,
    compute_polar_area,
    compute_polar_double_integral,
    compute_taylor_expansion,
    compute_triple_integral,
    compute_variable_double_integral,
    integration_by_parts_helper,
    parameter_assignment,
    solve_simple_ode,
    substitution_integral_helper,
    verify_antiderivative,
)
from qt_dialogs import show_error_dialog
from qt_jobs import JobRunner


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
    """Integration helpers, listed on the left and shown one at a time."""

    MULTIPLE_INTEGRAL_MODES = ("Double", "Polar double", "Triple")

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

        self.job_runner = JobRunner(self)
        self.finished.connect(self.job_runner.close)
        self._job_title = "Calculation"
        self.cancel_button = QPushButton(str(self.text.get("cancel_calculation", "Cancel calculation")), self)
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.job_runner.cancel)
        self.job_runner.busy_changed.connect(self._set_job_busy)
        self.setWindowTitle(str(self.text.get("math_tools", "Math Tools")))
        self.resize(900, 680)

        self.tool_list = QListWidget(self)
        self.tool_list.setFixedWidth(210)
        self.tool_list.setSpacing(3)
        self.stack = QStackedWidget(self)
        self.tool_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        body = QHBoxLayout()
        body.addWidget(self.tool_list)
        body.addWidget(self.stack, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addWidget(self.cancel_button)

        for build in (
            self._build_average_area,
            self._build_polar,
            self._build_geometry,
            self._build_multiple_integrals,
            self._build_taylor,
            self._build_transforms,
            self._build_techniques,
            self._build_verification,
            self._build_parameter_slider,
            self._build_piecewise,
        ):
            build()
        self.tool_list.setCurrentRow(0)

    def _tr(self, english: str) -> str:
        """Translate a Math Tools phrase, falling back to English."""
        return str(self.text.get("tool_text", {}).get(english, english))

    def _active_function_default(self, fallback: str) -> str:
        return self.initial_function or fallback

    def _page(
        self,
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
                label=self._tr(spec.label),
            )
            field.set_enabled(spec.enabled)
            self.math_fields[spec.name] = field
        panel.set_theme(self.theme_name)
        if minimum_editor_height is None:
            minimum_editor_height = max(90, 58 * len(specs))
        panel.setMinimumHeight(minimum_editor_height)
        if hasattr(panel, "content_height_changed"):
            # Grow with the editor's rendered content so no field is clipped.
            panel.content_height_changed.connect(
                lambda height, panel=panel, minimum=minimum_editor_height:
                    panel.setMinimumHeight(max(minimum, int(height) + 4))
            )
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
        self.stack.addWidget(scroll)
        self.tool_list.addItem(self._tr(title))
        self.pages[title] = page
        return page, page_layout

    def _field(self, name: str) -> str:
        return self.math_fields[name].get_text().strip()

    def _set_result(self, page: str, lines) -> None:
        self.results[page].setPlainText("\n".join(lines))

    def _button(
        self,
        page: QWidget,
        layout: QVBoxLayout,
        action_id: str,
        label: str,
        callback: Callable[[], object],
    ) -> QPushButton:
        label = self._tr(label)
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
            self._job_title = title
            return callback()
        except Exception as exc:
            show_error_dialog(self, title, str(exc))
            return None

    def _set_job_busy(self, busy):
        for field in self.math_fields.values():
            field.set_enabled(not busy)
        for control in self.native_controls.values():
            control.setEnabled(not busy)
        for button in self.actions.values():
            button.setEnabled(not busy)
        self.cancel_button.setVisible(busy)

    def _submit_job(self, function, arguments, present):
        title = self._job_title
        return self.job_runner.submit(function, arguments, present,
            lambda error: show_error_dialog(self, title, str(error)))

    def _native_form(self, layout: QVBoxLayout) -> QFormLayout:
        form = QFormLayout()
        layout.insertLayout(self._control_insertion_index(layout), form)
        return form

    @staticmethod
    def _control_insertion_index(layout: QVBoxLayout) -> int:
        for index in range(layout.count()):
            if isinstance(layout.itemAt(index).widget(), QPlainTextEdit):
                return index
        return max(0, layout.count() - 1)

    def _build_average_area(self) -> None:
        page, layout = self._page("Area & Average", (
            FieldSpec(
                "average.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x"),
            ),
            FieldSpec("average.lower", "Lower limit:", FieldRole.BOUND, "-1"),
            FieldSpec("average.upper", "Upper limit:", FieldRole.BOUND, "1"),
        ))
        tr = self._tr

        def compute():
            arguments = (self._field("average.function"), self._field("average.lower"), self._field("average.upper"))

            def present(payload):
                average, area = payload
                self._set_result("area_average", (
                    f"{tr('Integral:')} {average['integral']}",
                    f"{tr('Average value:')} {average['average']} ({average['numeric']:.10g})",
                    "",
                    f"{tr('Signed integral:')} {area['signed']:.12g}",
                    f"{tr('Absolute area:')} {area['absolute']:.12g}",
                    f"{tr('Positive area:')} {area['positive_area']:.12g}",
                    f"{tr('Negative area:')} {area['negative_area']:.12g}",
                ))
                return average, area
            return self._submit_job(compute_average_and_area, arguments, present)

        self._button(page, layout, "average.compute", "Compute Area and Average", compute)

    def _build_polar(self) -> None:
        page, layout = self._page("Polar Area", (
            FieldSpec("polar.radius", "r(θ):", FieldRole.EXPRESSION, "2*cos(theta)"),
            FieldSpec("polar.lower", "θ lower limit:", FieldRole.BOUND, "-pi/2"),
            FieldSpec("polar.upper", "θ upper limit:", FieldRole.BOUND, "pi/2"),
        ))
        tr = self._tr

        def compute():
            arguments = (self._field("polar.radius"), self._field("polar.lower"), self._field("polar.upper"))

            def present(result):
                self._set_result("polar_area", (
                    tr("Polar area formula: A = 1/2 ∫ r(θ)² dθ"),
                    f"{tr('Integrand:')} {result['integrand']}",
                    f"{tr('Exact area:')} {result['exact']}",
                    f"{tr('Numeric area:')} {result['numeric']:.10g}",
                ))
                return result
            return self._submit_job(compute_polar_area, arguments, present)

        self._button(page, layout, "polar.compute", "Compute Polar Area", compute)

    def _build_geometry(self) -> None:
        page, layout = self._page("Arc Length & Volume", (
            FieldSpec(
                "geometry.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x"),
            ),
            FieldSpec("geometry.lower", "Lower limit:", FieldRole.BOUND, "0"),
            FieldSpec("geometry.upper", "Upper limit:", FieldRole.BOUND, "1"),
        ))
        axis = QComboBox(page)
        axis.addItems(("x", "y"))
        self.native_controls["geometry.axis"] = axis
        self._native_form(layout).addRow(self._tr("Rotation axis:"), axis)
        tr = self._tr

        def compute():
            arguments = (
                self._field("geometry.function"),
                self._field("geometry.lower"),
                self._field("geometry.upper"),
                axis.currentText(),
            )

            def present(payload):
                arc, volume = payload
                self._set_result("arc_length_volume", (
                    tr("Arc length"),
                    f"{tr('Integrand:')} {arc['integrand']}",
                    f"{tr('Exact:')} {arc['exact']}",
                    f"{tr('Numeric:')} {arc['numeric']:.10g}",
                    "",
                    tr("Volume of revolution"),
                    f"{tr('Integrand:')} {volume['integrand']}",
                    f"{tr('Exact:')} {volume['exact']}",
                    f"{tr('Numeric:')} {volume['numeric']:.10g}",
                ))
                return arc, volume
            return self._submit_job(compute_geometry_bundle, arguments, present)

        self._button(page, layout, "geometry.compute", "Compute Arc Length and Volume", compute)

    def _build_multiple_integrals(self) -> None:
        page, layout = self._page("Multiple Integrals", (
            FieldSpec("multi.function", "Function:", FieldRole.EXPRESSION, "x+y"),
            FieldSpec("multi.a", "x / θ lower limit:", FieldRole.BOUND, "0"),
            FieldSpec("multi.b", "x / θ upper limit:", FieldRole.BOUND, "1"),
            FieldSpec("multi.c", "y / r lower limit:", FieldRole.BOUND, "0"),
            FieldSpec("multi.d", "y / r upper limit:", FieldRole.BOUND, "1"),
            FieldSpec("multi.e", "z lower limit:", FieldRole.BOUND, "0"),
            FieldSpec("multi.f", "z upper limit:", FieldRole.BOUND, "1"),
        ), minimum_editor_height=430)
        mode = QComboBox(page)
        mode.addItems([self._tr(name) for name in self.MULTIPLE_INTEGRAL_MODES])
        self.native_controls["multi.mode"] = mode
        self._native_form(layout).addRow(self._tr("Type:"), mode)
        tr = self._tr

        def compute():
            function = self._field("multi.function")
            a, b, c, d, e, f = (self._field(f"multi.{name}") for name in "abcdef")
            helper, arguments = (
                (compute_variable_double_integral, (function, a, b, c, d)),
                (compute_polar_double_integral, (function, c, d, a, b)),
                (compute_triple_integral, (function, a, b, c, d, e, f)),
            )[mode.currentIndex()]

            def present(result):
                self._set_result("multiple_integrals", (
                    f"{tr('Exact result:')} {result['exact']}",
                    f"{tr('Numeric result:')} {result['numeric']:.10g}",
                ))
                return result
            return self._submit_job(helper, arguments, present)

        self._button(page, layout, "multi.compute", "Compute Integral", compute)

    def _build_taylor(self) -> None:
        page, layout = self._page("Taylor Series", (
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
        self._native_form(layout).addRow(self._tr("Order:"), order)
        tr = self._tr

        def compute():
            arguments = (self._field("taylor.function"), self._field("taylor.point"), order.text())

            def present(result):
                self._set_result("taylor_series", (
                    f"{tr('Point:')} {result['point']}",
                    f"{tr('Order:')} {result['order']}",
                    f"{tr('Polynomial:')} {result['polynomial']}",
                    f"{tr('Series:')} {result['series']}",
                ))
                return result
            return self._submit_job(compute_taylor_expansion, arguments, present)

        self._button(page, layout, "taylor.compute", "Build Taylor Polynomial", compute)

    def _build_transforms(self) -> None:
        page, layout = self._page("Fourier, Laplace & ODE", (
            FieldSpec("transforms.function", "Function:", FieldRole.EXPRESSION, "exp(-x)"),
            FieldSpec("transforms.period", "Fourier period:", FieldRole.BOUND, "2*pi"),
            FieldSpec("transforms.ode", "Differential equation:", FieldRole.EQUATION, "y'=x*y"),
        ))
        terms = UncappedLineEdit("5", parent=page)
        self.native_controls["transforms.terms"] = terms
        self._native_form(layout).addRow(self._tr("Fourier terms:"), terms)
        tr = self._tr

        def fourier():
            arguments = (self._field("transforms.function"), self._field("transforms.period"), terms.text())

            def present(result):
                self._set_result("fourier_laplace_ode", (tr("Fourier series approximation:"), str(result["series"])))
                return result
            return self._submit_job(compute_fourier_series, arguments, present)

        def laplace():
            def present(result):
                self._set_result("fourier_laplace_ode", (
                    tr("Laplace transform:"), str(result["transform"]), "",
                    tr("Inverse transform:"), str(result["inverse"]),
                ))
                return result
            return self._submit_job(compute_laplace_transform, (self._field("transforms.function"),), present)

        def ode():
            result = solve_simple_ode(self._field("transforms.ode"))
            self._set_result("fourier_laplace_ode", (
                tr("Equation:"), str(result["equation"]), "", tr("Solution:"), str(result["solution"]),
            ))
            return result

        self._button(page, layout, "transforms.fourier", "Fourier Series", fourier)
        self._button(page, layout, "transforms.laplace", "Laplace Transform", laplace)
        self._button(page, layout, "transforms.ode", "Solve Equation", ode)

    def _build_techniques(self) -> None:
        page, layout = self._page("Integration Techniques", (
            FieldSpec("techniques.function", "Integrand:", FieldRole.EXPRESSION, "2*x*cos(x^2)"),
            FieldSpec("techniques.substitution", "Substitution:", FieldRole.EQUATION, "u=x^2"),
            FieldSpec("techniques.u", "By parts u:", FieldRole.EXPRESSION, "x"),
            FieldSpec("techniques.dv", "By parts dv:", FieldRole.EXPRESSION, "exp(x)"),
        ))
        tr = self._tr

        def substitution():
            arguments = (self._field("techniques.function"), self._field("techniques.substitution"))

            def present(result):
                self._set_result("integration_techniques", (
                    tr("Substitution"),
                    f"u = {result['u']}",
                    f"du/dx = {result['du_dx']}",
                    f"x(u) = {result['x_of_u']}",
                    f"{tr('Transformed integrand:')} {result['transformed_integrand']}",
                ))
                return result
            return self._submit_job(substitution_integral_helper, arguments, present)

        def by_parts():
            arguments = (self._field("techniques.u"), self._field("techniques.dv"))

            def present(result):
                self._set_result("integration_techniques", (
                    tr("Integration by parts"),
                    f"u = {result['u']}",
                    f"du = {result['du']} dx",
                    f"dv = {result['dv']} dx",
                    f"v = {result['v']}",
                    f"{tr('Remaining integrand v·du:')} {result['remaining_integrand']}",
                    f"{tr('Result:')} {result['result']} + C",
                ))
                return result
            return self._submit_job(integration_by_parts_helper, arguments, present)

        self._button(page, layout, "techniques.substitute", "Show Substitution", substitution)
        self._button(page, layout, "techniques.parts", "Show By Parts", by_parts)

    def _build_verification(self) -> None:
        page, layout = self._page("Verify Antiderivative", (
            FieldSpec("verify.function", "Integrand:", FieldRole.EXPRESSION, "sin(x)"),
            FieldSpec("verify.antiderivative", "Candidate antiderivative:", FieldRole.EXPRESSION, "-cos(x)"),
        ))
        tr = self._tr

        def compute():
            arguments = (self._field("verify.function"), self._field("verify.antiderivative"))

            def present(result):
                status = tr("Verified.") if result["ok"] else tr("Not verified.")
                self._set_result("verify_antiderivative", (f"{status} {tr('Difference:')} {result['difference']}",))
                return result
            return self._submit_job(verify_antiderivative, arguments, present)

        self._button(page, layout, "verify.compute", "Verify Antiderivative", compute)

    def _build_parameter_slider(self) -> None:
        page, layout = self._page("Parameter Slider", (
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
        form = self._native_form(layout)
        form.addRow(self._tr("Parameter:"), name)
        form.addRow(self._tr("Minimum:"), minimum)
        form.addRow(self._tr("Maximum:"), maximum)
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
                raise ValueError(self._tr("Maximum must be greater than minimum."))
            return apply_value()

        slider.valueChanged.connect(lambda _value: self._guard(self._tr("Parameter Slider"), apply_value))
        self._button(page, layout, "parameter.range", "Update Range", update_range)
        self._button(page, layout, "parameter.apply", "Apply Value", apply_value)
        self._parameter_apply = apply_value

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
            "Piecewise Builder", tuple(specs), result=False, minimum_editor_height=430
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
        self._button(page, layout, "piecewise.insert", "Insert Into Calculator", insert)

    def build_piecewise_for_test(self, pieces: list[tuple[str, str]]) -> str:
        expression = build_piecewise_expression(pieces)
        self.math_fields["piecewise.result"].set_text(expression)
        self.insert_function(expression)
        return expression


__all__ = ["FieldSpec", "MathToolsDialog", "UncappedLineEdit"]
