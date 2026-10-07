from PySide6.QtCore import QObject, Signal, Slot


class MathEditorBridge(QObject):
    input_received = Signal(str, str)
    submit_received = Signal(str)
    focus_received = Signal(str)
    focus_next_received = Signal(str, bool)
    content_height_received = Signal(int)
    ready = Signal()

    @Slot(str, str)
    def inputChanged(self, field_id, ascii_math):
        self.input_received.emit(field_id, ascii_math)

    @Slot(str)
    def submitted(self, field_id):
        self.submit_received.emit(field_id)

    @Slot(str)
    def focused(self, field_id):
        self.focus_received.emit(field_id)

    @Slot(str, bool)
    def focusNext(self, field_id, backwards):
        self.focus_next_received.emit(field_id, backwards)

    @Slot(int)
    def contentHeightChanged(self, height):
        self.content_height_received.emit(height)

    @Slot()
    def editorReady(self):
        self.ready.emit()
