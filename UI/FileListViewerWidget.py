import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QListWidget,
    QLabel,
    QPushButton,
    QListWidgetItem,
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
        refresh_button = QPushButton("Refresh List")
        #refresh_button.clicked.connect(self.populate_list)
        

        # File loading options
        FileLoadLayout = QGridLayout()

        self.add_button = QPushButton("Add file", self)
        pixmapi = getattr(QStyle, "SP_FileIcon")
        icon = self.style().standardIcon(pixmapi)
        self.add_button.setIcon(icon)
        #self.add_button.clicked.connect(self.add_file)
        FileLoadLayout.addWidget(self.add_button, 0, 0)

        self.delete_button = QPushButton("Delete file ", self)
        pixmapi = getattr(QStyle, "SP_DialogDiscardButton")
        icon = self.style().standardIcon(pixmapi)
        self.delete_button.setIcon(icon)
        #self.delete_button.clicked.connect(self.delete_file)
        FileLoadLayout.addWidget(self.delete_button, 0, 1)

        self.selectdir_button = QPushButton("Select directory", self)
        pixmapi = getattr(QStyle, "SP_DirIcon")
        icon = self.style().standardIcon(pixmapi)
        self.selectdir_button.setIcon(icon)
        #self.selectdir_button.clicked.connect(self.select_directory)
        FileLoadLayout.addWidget(self.selectdir_button, 1, 0)

        self.loadlatest_button = QPushButton("Load latest", self)
        pixmapi = getattr(QStyle, "SP_BrowserReload")
        icon = self.style().standardIcon(pixmapi)
        self.loadlatest_button.setIcon(icon)
        #self.loadlatest_button.clicked.connect(self.load_latest_file)
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
        layout.addWidget(refresh_button)

        self.setLayout(layout)

    def on_item_selected(self, item):
            obj_id = item.data(Qt.UserRole)
            #obj = self.data_manager.get(obj_id, None)

            try :
                self.object_selected.emit(obj_id)
            except:
                print("Could not retrieve object data.")

if __name__ == '__main__': #! To be verified
    from PyQt5.QtWidgets import QApplication

    # Simulated setup for testing
    from data_model import PressureGaugeDataObject, PressureGaugeDataManager  # Replace with your actual import

    app = QApplication(sys.argv)

    # Example data setup
    manager = PressureGaugeDataManager()
    for i in range(5):
        obj = PressureGaugeDataObject()
        obj.filename = f"test_file_{i}.asc"
        obj.P = i * 2.1  # dummy pressure
        obj.include_in_filelist = (i % 2 == 0)  # include every other object
        manager.add_instance(obj)

    viewer = FileListViewerWidget(manager)
    viewer.show()

    sys.exit(app.exec_())
