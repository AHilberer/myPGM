"""Small modal dialogs of the main window (DESIGN.md §1): the Pm prompt of "Add point
to log", and the messages (errors, unsaved changes) in the same style instead of the
platform's message boxes."""
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from myPGM.helpers import SmartDoubleSpinBox
from myPGM.ui import icons, theme
from myPGM.ui.widgets import Button, button, label

TEXT_WIDTH = 360           # message title and text, px

# kind of message -> (icon, icon colour token, icon background token)
MESSAGE_KINDS = {
    "error": ("circle-alert", "err", "bad"),
    "question": ("circle-help", "ac", "info"),
}


class AddPointDialog(QDialog):
    """"Add point to log" (Parameters card): the
    point's summary, a focused Pm field prefilled with the last Pm, Cancel / Add to log.
    Enter confirms, Esc cancels."""

    def __init__(self, summary_html, pm, parent=None):
        super().__init__(parent)
        self.setObjectName("AddPointDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Add point to log")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        heading = QVBoxLayout()
        heading.setSpacing(4)
        heading.addWidget(label("Add point to log", "dialog-title"))
        self.summary_label = QLabel(summary_html)
        self.summary_label.setTextFormat(Qt.RichText)
        self.summary_label.setProperty("role", "muted-12")
        heading.addWidget(self.summary_label)
        layout.addLayout(heading)

        field = QVBoxLayout()
        field.setSpacing(4)
        field.addWidget(label("Membrane pressure Pm", "field"))
        self.pm_field = QFrame()
        self.pm_field.setObjectName("PmField")
        self.pm_field.setProperty("focused", True)
        self.pm_field.setAttribute(Qt.WA_StyledBackground, True)
        self.pm_field.setFixedHeight(40)
        field_layout = QHBoxLayout(self.pm_field)
        field_layout.setContentsMargins(8, 0, 10, 0)
        field_layout.setSpacing(6)
        self.spinbox = SmartDoubleSpinBox()
        self.spinbox.setObjectName("PmDialogValue")
        self.spinbox.setButtonSymbols(SmartDoubleSpinBox.NoButtons)
        self.spinbox.setDecimals(2)
        self.spinbox.setRange(-np.inf, np.inf)
        self.spinbox.setSingleStep(0.1)
        self.spinbox.setValue(pm)
        field_layout.addWidget(self.spinbox, 1)
        field_layout.addWidget(label("bar", "muted"))
        field.addWidget(self.pm_field)
        layout.addLayout(field)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        self.cancel_button = Button("Cancel", 36)
        self.add_button = button("Add to log", 36, primary=True)
        self.cancel_button.setAutoDefault(False)
        self.add_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        self.add_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.add_button)
        layout.addLayout(buttons)

        self.spinbox.selectAll()
        self.spinbox.setFocus()

    def value(self):
        self.spinbox.interpretText()
        return self.spinbox.value()


class MessageDialog(QDialog):
    """A message in the style of the app (AddPointDialog): an icon in a tinted circle, a
    title, the text, and buttons on the right, the default one primary.

    buttons: (text, choice) pairs from left to right; a choice starting with '-' puts
    its button on the left (e.g. Discard). `choice` is the clicked button's choice, or
    `escape` when the dialog is closed with Esc or the window's close button."""

    def __init__(self, title, text="", kind="error", buttons=(("OK", "ok"),), default="ok",
                 escape="ok", window_title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("MessageDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(window_title or title)
        self.setModal(True)
        self.kind = kind
        self.choice = self.escape = escape

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(18)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("MessageIcon")
        self.icon_label.setFixedSize(36, 36)
        self.icon_label.setAlignment(Qt.AlignCenter)
        row.addWidget(self.icon_label, 0, Qt.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        # fixed text width: wrapped labels then get their exact height (no gaps)
        self.title_label = label(title, "dialog-title")
        self.title_label.setWordWrap(True)
        self.title_label.setFixedWidth(TEXT_WIDTH)
        texts.addWidget(self.title_label)
        self.text_label = QLabel(text)
        self.text_label.setObjectName("MessageText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setFixedWidth(TEXT_WIDTH)
        self.text_label.setVisible(bool(text))
        texts.addWidget(self.text_label)
        texts.addStretch(1)
        row.addLayout(texts, 1)
        layout.addLayout(row)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.buttons = {}
        left = [(t, c) for t, c in buttons if c.startswith("-")]
        right = [(t, c) for t, c in buttons if not c.startswith("-")]
        for text_, choice in left:
            bar.addWidget(self._button(text_, choice, default))
        bar.addStretch(1)
        for text_, choice in right:
            bar.addWidget(self._button(text_, choice, default))
        layout.addLayout(bar)
        self.restyle()
        # Enter / Space act on the default button, and it shows the focus, not the first one
        self.buttons[default.lstrip("-")].setFocus()

    def _button(self, text, choice, default):
        primary = choice == default
        widget = button(text, 36, primary=True) if primary else Button(text, 36)
        widget.setAutoDefault(False)
        widget.setDefault(primary)
        widget.clicked.connect(lambda: self._choose(choice))
        self.buttons[choice.lstrip("-")] = widget
        return widget

    def _choose(self, choice):
        self.choice = choice.lstrip("-")
        self.accept()

    def reject(self):
        self.choice = self.escape
        super().reject()

    def restyle(self):
        name, color, background = MESSAGE_KINDS[self.kind]
        t = theme.tokens()
        self.icon_label.setPixmap(icons.pixmap(name, theme.qcolor(t[color]).name(), 20))
        self.icon_label.setStyleSheet(
            f"background-color: {theme.qcolor(t[background]).name()}; border-radius: 18px;")

    def title(self):
        return self.title_label.text()

    def text(self):
        return self.text_label.text()

    def ask(self):
        """Show it (modal) and return the choice."""
        self.exec_()
        return self.choice


def show_error(parent, title, text="", window_title=None):
    """An error message with OK (instead of the platform's critical message box)."""
    MessageDialog(title, text, "error", window_title=window_title, parent=parent).exec_()


def ask_save_changes(parent, action="closing"):
    """'save', 'discard' or 'cancel' for a session with unsaved changes, before
    `action` ('closing', 'opening another session')."""
    return MessageDialog(
        f"Save changes before {action}?",
        "The session has unsaved changes (spectra, fits or table points).",
        "question", buttons=(("Discard", "-discard"), ("Cancel", "cancel"), ("Save", "save")),
        default="save", escape="cancel", window_title="Unsaved changes", parent=parent).ask()


def ask_clear_log(parent, count):
    """True to remove every point of the pressure log."""
    points = f"{count} point" + ("s" if count != 1 else "")
    return MessageDialog(
        "Clear the pressure log?",
        f"{points} will be removed. Spectra stay in the file list; points added "
        "from the pressure toolbox are deleted.",
        "question", buttons=(("Cancel", "cancel"), ("Clear log", "clear")),
        default="clear", escape="cancel", window_title="Clear log", parent=parent).ask() == "clear"
