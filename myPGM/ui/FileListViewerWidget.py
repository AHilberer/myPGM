from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)

from myPGM.ui import icons
from myPGM.ui.widgets import Card, ElidedLabel, button, divider, hbox, icon_button

class FileListViewerWidget(Card):
    """Spectra sidebar (DESIGN.md §1.2): add button, acquisition folder box with
    Load latest, the file list, and move up / move down / delete buttons."""

    object_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__("Spectra")
        self.init_ui()

    def init_ui(self):
        self.add_button = icon_button("plus", "Add spectrum files…")
        self.header.addWidget(self.add_button)

        # acquisition folder: where "Load latest" looks for the newest spectrum
        folder_box = QFrame()
        folder_box.setObjectName("FolderBox")
        folder_box.setAttribute(Qt.WA_StyledBackground, True)
        folder_layout = QVBoxLayout(folder_box)
        folder_layout.setContentsMargins(10, 10, 10, 10)
        folder_layout.setSpacing(8)

        self.folder_icon = QLabel()
        self.dir_label = ElidedLabel("No acquisition folder")
        self.dir_label.setProperty("role", "caption-12")
        self.selectdir_button = QPushButton("Select…")
        self.selectdir_button.setProperty("role", "link")
        self.selectdir_button.setCursor(Qt.PointingHandCursor)
        self.selectdir_button.setToolTip("Select the acquisition folder")
        folder_layout.addLayout(hbox(self.folder_icon, self.dir_label, self.selectdir_button, 1,
                                     spacing=6))

        self.loadlatest_button = button(
            "Load latest", 36, primary=True, icon_name="refresh-cw",
            tooltip="Load the newest spectrum of the acquisition folder")
        folder_layout.addWidget(self.loadlatest_button)
        self.body.addWidget(folder_box)

        # Actual FileList_widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("FileList")
        self.list_widget.setTextElideMode(Qt.ElideMiddle)     # keeps the file extension
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self.on_item_selected)
        self.body.addWidget(self.list_widget, 1)

        # File moving section
        self.moveup_button = icon_button("chevron-up", "Move up", size=34)
        self.movedown_button = icon_button("chevron-down", "Move down", size=34)
        self.delete_button = icon_button("trash-2", "Remove the selected spectrum", size=34,
                                         role="mu")
        self.body.addWidget(divider(vertical=False))
        self.body.addLayout(hbox(self.moveup_button, self.movedown_button, 1,
                                 self.delete_button, spacing=6))
        self.restyle()

    def set_directory(self, path):
        """Show the acquisition folder (its name; the full path in the tooltip)."""
        import os
        name = os.path.basename(os.path.normpath(path)) if path else ""
        self.dir_label.setText(name or "No acquisition folder")
        self.dir_label.setToolTip(path or "")
        self.dir_label.setProperty("role", "caption-12" if not name else "folder")
        self.dir_label.style().unpolish(self.dir_label)
        self.dir_label.style().polish(self.dir_label)
        self.dir_label.update()

    def restyle(self):
        from myPGM.ui import theme
        self.folder_icon.setPixmap(icons.pixmap("folder", theme.qcolor(theme.tokens()["mu"]).name(), 15))

    def on_item_selected(self, item):
        self.object_selected.emit(item.data(Qt.UserRole))
