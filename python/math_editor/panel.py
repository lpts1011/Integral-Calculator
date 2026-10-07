import json
from pathlib import Path

from PySide6.QtCore import QUrl, QTimer, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from math_editor.adapter import MathFieldAdapter
from math_editor.bridge import MathEditorBridge
from math_editor.resource_paths import runtime_resource_root
from math_editor.syntax import FieldRole, calculator_to_asciimath


class MathEditorPanel(QWidget):
    startup_failed = Signal(str)
    field_focused = Signal(str)
    content_height_changed = Signal(int)

    def __init__(self, parent=None, editor_url=None, startup_timeout_ms=5000):
        super().__init__(parent)
        self._fields = {}
        self._ready = False
        self._startup_failed = False
        self._error_message = ""
        self._pending_scripts = []
        self._active_field_id = None
        self._editor_url = editor_url
        self._startup_timeout_ms = startup_timeout_ms

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._view = QWebEngineView(self)
        self._layout.addWidget(self._view)

        self._channel = QWebChannel(self._view.page())
        self._bridge = MathEditorBridge()
        self._channel.registerObject("mathEditorBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)
        self._bridge.ready.connect(self._editor_ready)
        self._bridge.input_received.connect(self._input_received)
        self._bridge.submit_received.connect(self._submit_received)
        self._bridge.focus_received.connect(self._focus_received)
        self._bridge.focus_next_received.connect(self._focus_next_received)
        self._bridge.content_height_received.connect(self._content_height_received)
        self._view.loadFinished.connect(self._load_finished)

        self._startup_timer = QTimer(self)
        self._startup_timer.setSingleShot(True)
        self._startup_timer.timeout.connect(self._startup_timed_out)
        self._startup_timer.start(self._startup_timeout_ms)

        url = editor_url
        if url is None:
            url = QUrl.fromLocalFile(
                str(Path(runtime_resource_root()) / "editor.html")
            )
        elif isinstance(url, str):
            url = QUrl(url)
        self._view.load(url)

    def create_field(self, field_id, role, initial="", label=None, slot=None):
        if field_id in self._fields:
            raise ValueError(f"Duplicate math field id: {field_id}")
        if not isinstance(role, FieldRole):
            role = FieldRole(role)
        field = MathFieldAdapter(self, field_id, role, initial)
        self._fields[field_id] = field
        if self._active_field_id is None or field_id == "function":
            self._active_field_id = field_id
        self._queue_script(
            "window.mathEditor.createField(%s);"
            % json.dumps(
                {
                    "id": field_id,
                    "value": calculator_to_asciimath(initial),
                    "disabled": False,
                    "placeholder": "",
                    "label": str(label) if label is not None else str(field_id),
                    "slot": str(slot) if slot is not None else "",
                }
            )
        )
        return field

    def is_ready(self):
        return self._ready

    @property
    def startup_failed_state(self):
        return self._startup_failed

    @property
    def error_message(self):
        return self._error_message

    @property
    def web_view(self):
        return self._view

    @property
    def active_field_id(self):
        return self._active_field_id

    def has_visible_virtual_keyboard(self):
        return False

    def has_plain_text_fallback(self):
        return False

    def set_field_value(self, field_id, value):
        self._queue_script(
            "window.mathEditor.setValue(%s, %s);"
            % (json.dumps(field_id), json.dumps(value))
        )

    def focus_field(self, field_id):
        self._queue_script(
            "window.mathEditor.focus(%s);" % json.dumps(field_id)
        )

    def set_field_enabled(self, field_id, enabled):
        self._queue_script(
            "window.mathEditor.setEnabled(%s, %s);"
            % (json.dumps(field_id), json.dumps(bool(enabled)))
        )

    def set_field_label(self, field_id, label):
        self._queue_script(
            "(() => {"
            "const field = document.getElementById("
            + json.dumps(f"math-field-{field_id}")
            + ");"
            "if (!field) return;"
            "const container = field.closest('.math-field-container');"
            "const label = container && container.querySelector('label');"
            "if (label) label.textContent = "
            + json.dumps(str(label))
            + ";"
            "field.setAttribute('aria-label', "
            + json.dumps(str(label))
            + ");"
            "})();"
        )

    def set_theme(self, name):
        self._queue_script(
            "window.mathEditor.setTheme(%s);" % json.dumps(str(name))
        )

    def dispatch_command(self, field_id, command):
        self._queue_script(
            "window.mathEditor.executeCommand(%s, %s);"
            % (json.dumps(field_id), json.dumps(str(command)))
        )

    def insert_latex(self, latex, field_id=None):
        target = field_id or self._active_field_id
        if target not in self._fields:
            target = "function" if "function" in self._fields else next(iter(self._fields), None)
        if target is None:
            return
        self._active_field_id = target
        self._queue_script(
            "window.mathEditor.insertLatex(%s, %s);"
            % (json.dumps(target), json.dumps(str(latex)))
        )

    def dispatch_active_command(self, command):
        target = self._active_field_id
        if target not in self._fields:
            target = "function" if "function" in self._fields else next(iter(self._fields), None)
        if target is not None:
            self.dispatch_command(target, command)

    def _queue_script(self, script):
        if self._startup_failed:
            return
        if self._ready:
            self._view.page().runJavaScript(script)
        else:
            self._pending_scripts.append(script)

    @Slot(bool)
    def _load_finished(self, ok):
        if not ok:
            self._fail_startup("The local math editor could not load.")

    @Slot()
    def _editor_ready(self):
        if self._startup_failed or self._ready:
            return
        self._ready = True
        self._startup_timer.stop()
        pending, self._pending_scripts = self._pending_scripts, []
        for script in pending:
            self._view.page().runJavaScript(script)

    @Slot()
    def _startup_timed_out(self):
        self._fail_startup("The local math editor could not start.")

    def _fail_startup(self, reason):
        if self._startup_failed:
            return
        self._startup_failed = True
        self._ready = False
        self._startup_timer.stop()
        self._pending_scripts.clear()
        self._error_message = "The local math editor could not start."
        self._view.setParent(None)
        self._view.deleteLater()
        label = QLabel(self._error_message, self)
        label.setObjectName("mathEditorStartupError")
        label.setWordWrap(True)
        self._layout.addWidget(label)
        self.startup_failed.emit(reason)

    @Slot(str, str)
    def _input_received(self, field_id, ascii_math):
        field = self._fields.get(field_id)
        if field is not None:
            field._receive_mathlive_text(ascii_math)

    @Slot(str)
    def _submit_received(self, field_id):
        field = self._fields.get(field_id)
        if field is not None:
            field._receive_submitted()

    @Slot(str)
    def _focus_received(self, field_id):
        if field_id in self._fields:
            self._active_field_id = field_id
            self.field_focused.emit(field_id)

    @Slot(str, bool)
    def _focus_next_received(self, field_id, backwards):
        field_ids = list(self._fields)
        if field_id not in field_ids or not field_ids:
            return
        offset = -1 if backwards else 1
        target = field_ids[(field_ids.index(field_id) + offset) % len(field_ids)]
        self.focus_field(target)

    @Slot(int)
    def _content_height_received(self, height):
        if height > 0:
            self.content_height_changed.emit(height)
