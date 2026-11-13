"""Small modal dialogs of the main window (DESIGN.md §1)."""
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from myPGM.helpers import SmartDoubleSpinBox
from myPGM.ui.widgets import Button, button, label


class AddPointDialog(QDialog):
    """"Add point to log" (Parameters card, mockup_light_add_point_dialog.png): the
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
