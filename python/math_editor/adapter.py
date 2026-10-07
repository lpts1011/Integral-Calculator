from PySide6.QtCore import QObject, Signal

from math_editor.syntax import (
    FieldRole,
    calculator_to_asciimath,
    normalize_mathlive_text,
)


class MathFieldAdapter(QObject):
    changed = Signal(str)
    submitted = Signal()
    validity_changed = Signal(str, str)

    def __init__(self, panel, field_id, role: FieldRole, initial=""):
        super().__init__(panel)
        self._panel = panel
        self.field_id = field_id
        self.role = role
        self._text = str(initial)
        self._state = normalize_mathlive_text(self._text, role)

    @property
    def validation_status(self):
        return self._state.status

    def get_text(self):
        if self._state.status == "valid":
            return self._state.calculator_text
        return self._text

    def set_text(self, value):
        self._text = str(value)
        self._state = normalize_mathlive_text(self._text, self.role)
        self._panel.set_field_value(
            self.field_id, calculator_to_asciimath(self._text)
        )

    def clear(self):
        self.set_text("")

    def focus(self):
        self._panel.focus_field(self.field_id)

    def set_enabled(self, enabled):
        self._panel.set_field_enabled(self.field_id, enabled)

    def set_theme(self, name):
        self._panel.set_theme(name)

    def dispatch_command(self, command: str):
        self._panel.dispatch_command(self.field_id, command)

    def insert_latex(self, latex: str):
        self._panel.insert_latex(latex, self.field_id)

    def _receive_mathlive_text(self, ascii_math):
        self._text = str(ascii_math)
        next_state = normalize_mathlive_text(self._text, self.role)
        previous_state = self._state
        self._state = next_state
        if (
            next_state.status != previous_state.status
            or next_state.error != previous_state.error
        ):
            self.validity_changed.emit(next_state.status, next_state.error)
        self.changed.emit(self.get_text())

    def _receive_submitted(self):
        self.submitted.emit()
