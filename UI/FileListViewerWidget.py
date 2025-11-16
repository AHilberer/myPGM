import sys
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QGridLayout,
    QStyle,
    QHBoxLayout
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)

class FileListViewerWidget(QWidget):

    object_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.files = {}
        self.init_ui()

    def init_ui(self):
        #self.setWindowTitle("Filtered Pressure Gauge Data List")
        #self.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout()


        # Optional refresh button
        # refresh_button = QPushButton("Refresh List")
        # refresh_button.clicked.connect(self.populate_list)
        

        # File loading options
        FileLoadLayout = QGridLayout()

        self.add_button = QPushButton("Add file", self)
        pixmapi = getattr(QStyle, "SP_FileIcon")
        icon = self.style().standardIcon(pixmapi)
        self.add_button.setIcon(icon)
        FileLoadLayout.addWidget(self.add_button, 0, 0)

        self.delete_button = QPushButton("Delete file ", self)
        pixmapi = getattr(QStyle, "SP_DialogDiscardButton")
        icon = self.style().standardIcon(pixmapi)
        self.delete_button.setIcon(icon)
        FileLoadLayout.addWidget(self.delete_button, 0, 1)

        self.selectdir_button = QPushButton("Select directory", self)
        pixmapi = getattr(QStyle, "SP_DirIcon")
        icon = self.style().standardIcon(pixmapi)
        self.selectdir_button.setIcon(icon)
        FileLoadLayout.addWidget(self.selectdir_button, 1, 0)

        self.loadlatest_button = QPushButton("Load latest", self)
        pixmapi = getattr(QStyle, "SP_BrowserReload")
        icon = self.style().standardIcon(pixmapi)
        self.loadlatest_button.setIcon(icon)
        FileLoadLayout.addWidget(self.loadlatest_button, 1, 1)


        # File moving section

        MoveLayout = QHBoxLayout()

        self.up_button = QPushButton("Move up", self)
        pixmapi = getattr(QStyle, "SP_ArrowUp")
        icon = self.style().standardIcon(pixmapi)
        self.up_button.setIcon(icon)
        #self.up_button.clicked.connect(self.move_up)
        MoveLayout.addWidget(self.up_button)

        self.down_button = QPushButton("Move down", self)
        pixmapi = getattr(QStyle, "SP_ArrowDown")
        icon = self.style().standardIcon(pixmapi)
        self.down_button.setIcon(icon)
        #self.down_button.clicked.connect(self.move_down)
        MoveLayout.addWidget(self.down_button)


        # Actual FileList_widget
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_selected)


        layout.addLayout(FileLoadLayout)
        layout.addWidget(self.list_widget)
        layout.addLayout(MoveLayout)
        # layout.addWidget(refresh_button)

        self.setLayout(layout)

    def on_item_selected(self, item):
            obj_id = item.data(Qt.UserRole)
            #obj = self.data_manager.get(obj_id, None)

            try :
                self.object_selected.emit(obj_id)
            except:
                print("Could not retrieve object data.")



if __name__ == '__main__': #! To be verified
    pass
