"""Math Tools: integration helpers listed in one window."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from math_editor.panel import MathEditorPanel
from math_editor.syntax import FieldRole
from math_extensions import (
    compute_area_breakdown,
    compute_geometry_bundle,
    compute_polar_area,
    integration_by_parts_helper,
    substitution_integral_helper,
)
from qt_dialogs import show_error_dialog
from qt_jobs import JobRunner
from qt_result_workspace import ToolResultView


@dataclass(frozen=True)
class FieldSpec:
    """Explicit declaration of one mathematical input or output field."""

    name: str
    label: str
    role: FieldRole
    default: str = ""


def _number(value: float) -> str:
    return rf"\approx {value:.10g}"


class MathToolsDialog(QDialog):
    """Integration helpers, listed on the left and shown one at a time."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_function: str = "",
        text: dict[str, object] | None = None,
        theme_name: str = "Light",
        panel_factory=MathEditorPanel,
        result_view_factory=ToolResultView,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.panel_factory = panel_factory
        self.initial_function = str(initial_function).strip()
        self.text = dict(text or {})
        self.theme_name = str(theme_name)
        self.math_fields: dict[str, object] = {}
        self.math_panels: dict[str, QWidget] = {}
        self.pages: dict[str, QWidget] = {}
        self.results: dict[str, list[dict[str, str]]] = {}
        self._page_keys: list[str] = []
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
        self.result_view = result_view_factory(self)
        self.result_view.set_theme(self.theme_name)
        self.tool_list.currentRowChanged.connect(self._show_page)
        tool_area = QVBoxLayout()
        tool_area.addWidget(self.stack, stretch=3)
        tool_area.addWidget(self.result_view, stretch=2)
        body = QHBoxLayout()
        body.addWidget(self.tool_list)
        body.addLayout(tool_area, stretch=1)
        layout = QVBoxLayout(self)
        layout.addLayout(body)
        layout.addWidget(self.cancel_button)

        for build in (
            self._build_area,
            self._build_polar,
            self._build_geometry,
            self._build_techniques,
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
            self.math_fields[spec.name] = field
        panel.set_theme(self.theme_name)
        minimum_editor_height = max(90, 58 * len(specs))
        panel.setMinimumHeight(minimum_editor_height)
        if hasattr(panel, "content_height_changed"):
            # Grow with the editor's rendered content so no field is clipped.
            panel.content_height_changed.connect(
                lambda height, panel=panel, minimum=minimum_editor_height:
                    panel.setMinimumHeight(max(minimum, int(height) + 4))
            )
        page_layout.addWidget(panel)
        page_layout.addStretch(1)
        self.results[panel_key] = []
        self._page_keys.append(panel_key)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)
        self.tool_list.addItem(self._tr(title))
        self.pages[title] = page
        return page, page_layout

    def _field(self, name: str) -> str:
        return self.math_fields[name].get_text().strip()

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self._page_keys):
            self.result_view.set_rows(self.results[self._page_keys[index]])

    def _set_result(self, page: str, rows) -> None:
        self.results[page] = list(rows)
        if self._page_keys[self.stack.currentIndex()] == page:
            self.result_view.set_rows(self.results[page])

    def result_text(self, page: str) -> str:
        """The page's latest result as plain text, one row per line."""
        lines = []
        for row in self.results[page]:
            if "heading" in row:
                lines.append(row["heading"])
            else:
                lines.append(f"{row.get('label', '')} {row.get('text', '')}".strip())
        return "\n".join(lines)

    @staticmethod
    def _math(label: str, latex: str, text: str) -> dict[str, str]:
        return {"label": label, "latex": latex, "text": text}

    def _exact_row(self, label: str, result: dict) -> dict[str, str]:
        latex = result["latex"]["exact"]
        if latex:
            return self._math(label, latex, result["exact"])
        if result["exact"] is None:
            note = "No closed form; the numerical value is shown below."
        else:
            note = "The exact form is too complex; the numerical value is shown below."
        return {"label": label, "text": self._tr(note)}

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
        # Controls go after the editor and earlier controls, before the stretch.
        return max(0, layout.count() - 1)

    def _build_area(self) -> None:
        page, layout = self._page("Area", (
            FieldSpec(
                "area.function",
                "Function:",
                FieldRole.EXPRESSION,
                self._active_function_default("x"),
            ),
            FieldSpec("area.lower", "Lower limit:", FieldRole.BOUND, "-1"),
            FieldSpec("area.upper", "Upper limit:", FieldRole.BOUND, "1"),
        ))
        tr = self._tr

        def compute():
            arguments = (self._field("area.function"), self._field("area.lower"), self._field("area.upper"))

            def present(area):
                self._set_result("area", [
                    self._math(label, f"{area[key]:.12g}", f"{area[key]:.12g}")
                    for label, key in (
                        (tr("Signed integral:"), "signed"),
                        (tr("Absolute area:"), "absolute"),
                        (tr("Positive area:"), "positive_area"),
                        (tr("Negative area:"), "negative_area"),
                    )
                ])
                return area
            return self._submit_job(compute_area_breakdown, arguments, present)

        self._button(page, layout, "area.compute", "Compute Area", compute)

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
                    self._math(
                        tr("Polar area formula:"),
                        r"A=\frac{1}{2}\int r(\theta)^{2}\,d\theta",
                        "A = 1/2 ∫ r(θ)² dθ",
                    ),
                    self._math(tr("Integrand:"), result["latex"]["integrand"], result["integrand"]),
                    self._exact_row(tr("Exact area:"), result),
                    self._math(tr("Numeric area:"), _number(result["numeric"]), f"{result['numeric']:.10g}"),
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
                rows = []
                for heading, result in ((tr("Arc length"), arc), (tr("Volume of revolution"), volume)):
                    rows += [
                        {"heading": heading},
                        self._math(tr("Integrand:"), result["latex"]["integrand"], result["integrand"]),
                    ]
                    if result.get("note"):
                        rows.append({"label": tr("Note:"), "text": tr(result["note"])})
                    rows += [
                        self._exact_row(tr("Exact:"), result),
                        self._math(tr("Numeric:"), _number(result["numeric"]), f"{result['numeric']:.10g}"),
                    ]
                self._set_result("arc_length_volume", rows)
                return arc, volume
            return self._submit_job(compute_geometry_bundle, arguments, present)

        self._button(page, layout, "geometry.compute", "Compute Arc Length and Volume", compute)

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
                tex = result["latex"]
                self._set_result("integration_techniques", (
                    {"heading": tr("Substitution")},
                    self._math("", f"u = {tex['u']}", f"u = {result['u']}"),
                    self._math("", rf"\frac{{du}}{{dx}} = {tex['du_dx']}", f"du/dx = {result['du_dx']}"),
                    self._math("", f"x(u) = {tex['x_of_u']}", f"x(u) = {result['x_of_u']}"),
                    self._math(
                        tr("Transformed integrand:"),
                        tex["transformed_integrand"],
                        result["transformed_integrand"],
                    ),
                ))
                return result
            return self._submit_job(substitution_integral_helper, arguments, present)

        def by_parts():
            arguments = (self._field("techniques.u"), self._field("techniques.dv"))

            def present(result):
                tex = result["latex"]
                du = "" if tex["du"] == "1" else tex["du"] + r"\,"
                self._set_result("integration_techniques", (
                    {"heading": tr("Integration by parts")},
                    self._math("", f"u = {tex['u']}", f"u = {result['u']}"),
                    self._math("", rf"du = {du}dx", f"du = {result['du']} dx"),
                    self._math("", rf"dv = {tex['dv']}\,dx", f"dv = {result['dv']} dx"),
                    self._math("", f"v = {tex['v']}", f"v = {result['v']}"),
                    self._math(
                        tr("Remaining integrand v·du:"),
                        tex["remaining_integrand"],
                        result["remaining_integrand"],
                    ),
                    self._math(tr("Result:"), f"{tex['result']} + C", f"{result['result']} + C"),
                ))
                return result
            return self._submit_job(integration_by_parts_helper, arguments, present)

        self._button(page, layout, "techniques.substitute", "Show Substitution", substitution)
        self._button(page, layout, "techniques.parts", "Show By Parts", by_parts)


__all__ = ["FieldSpec", "MathToolsDialog"]
