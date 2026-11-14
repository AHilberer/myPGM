"""Recovery banner under the top bar (DESIGN.md §4b). It
replaces the startup message box: the window stays usable while it is shown."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel

from myPGM.ui import icons, theme
from myPGM.ui.widgets import button


class RecoveryBanner(QFrame):
    """"myPGM did not close normally last time. A backup of the unsaved session from
    <when> was found." with Discard and Recover session."""

    recover_clicked = pyqtSignal()
    discard_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RecoveryBanner")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 10, 8)
        layout.setSpacing(12)
        self.icon = QLabel()
        self.message = QLabel()
        self.message.setTextFormat(Qt.RichText)
        self.message.setWordWrap(True)
        self.discard_button = button("Discard", 32,
                                     tooltip="Start without the backup (it is kept aside on disk)")
        self.recover_button = button("Recover session", 32, primary=True,
                                     tooltip="Load the backup of the unsaved session")
        layout.addWidget(self.icon)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.discard_button)
        layout.addWidget(self.recover_button)
        self.recover_button.clicked.connect(self.recover_clicked.emit)
        self.discard_button.clicked.connect(self.discard_clicked.emit)
        self.hide()
        self.restyle()

    def show_backup(self, when):
        self.message.setText(
            "<b>myPGM did not close normally last time.</b> "
            f"A backup of the unsaved session from {when} was found.")
        self.show()

    def restyle(self):
        self.icon.setPixmap(icons.pixmap("history", theme.qcolor(theme.tokens()["act"]).name(), 18))
