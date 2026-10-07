"""Reusable read-only text dialogs for the Qt application layer."""

from __future__ import annotations

import weakref

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TextDialog(QDialog):
    """A modal-capable, read-only text surface with optional copy action."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        content: str,
        copy_button: bool = False,
        copy_label: str = "Copy",
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(title)
        self.resize(720, 480)

        self.editor = QPlainTextEdit(self)
        self.editor.setPlainText(str(content))
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

        self.copy_button: QPushButton | None = None
        if copy_button:
            self.copy_button = QPushButton(str(copy_label), self)
            self.copy_button.clicked.connect(self.copy_content)
            layout.addWidget(self.copy_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def copy_content(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.editor.toPlainText())


def build_text_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
    copy_button: bool = False,
    copy_label: str = "Copy",
) -> TextDialog:
    return TextDialog(
        parent,
        title,
        content,
        copy_button=copy_button,
        copy_label=copy_label,
    )


_OPEN_DIALOGS: set[TextDialog] = set()


def _register_and_show(dialog: TextDialog, modal: bool = False) -> TextDialog:
    dialog_ref = weakref.ref(dialog)

    def discard_dialog(*_args: object) -> None:
        current = dialog_ref()
        if current is not None:
            _OPEN_DIALOGS.discard(current)

    _OPEN_DIALOGS.add(dialog)
    dialog.finished.connect(discard_dialog)
    dialog.destroyed.connect(discard_dialog)
    if modal:
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def show_text_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
    copy_button: bool = False,
    copy_label: str = "Copy",
) -> TextDialog:
    return _register_and_show(
        build_text_dialog(
            parent,
            title,
            content,
            copy_button=copy_button,
            copy_label=copy_label,
        ),
    )


def _show_blocking_text_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
) -> QDialog.DialogCode:
    dialog = _register_and_show(build_text_dialog(parent, title, content), modal=True)
    return QDialog.DialogCode(dialog.exec())


def show_information_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
) -> QDialog.DialogCode:
    return _show_blocking_text_dialog(parent, title, content)


def show_error_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
) -> QDialog.DialogCode:
    return _show_blocking_text_dialog(parent, title, content)


def show_steps_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
    copy_label: str = "Copy",
) -> TextDialog:
    return show_text_dialog(
        parent,
        title,
        content,
        copy_button=True,
        copy_label=copy_label,
    )


def show_suggestions_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
    copy_label: str = "Copy",
) -> TextDialog:
    return show_text_dialog(
        parent,
        title,
        content,
        copy_button=True,
        copy_label=copy_label,
    )


def show_usage_dialog(
    parent: QWidget | None,
    title: str,
    content: str,
    copy_label: str = "Copy",
) -> TextDialog:
    return show_text_dialog(
        parent,
        title,
        content,
        copy_button=True,
        copy_label=copy_label,
    )


__all__ = [
    "TextDialog",
    "build_text_dialog",
    "show_text_dialog",
    "show_information_dialog",
    "show_error_dialog",
    "show_steps_dialog",
    "show_suggestions_dialog",
    "show_usage_dialog",
]
