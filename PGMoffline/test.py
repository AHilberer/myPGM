import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QAction, QListWidget, QHBoxLayout, QFileDialog, QLabel, QListWidgetItem
from PyQt5.QtCore import QFileInfo, Qt

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Qt UI with Menu and Buttons")
        self.setGeometry(100, 100, 600, 400)

        self.init_ui()

    def init_ui(self):
        # Create Menu Bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Create central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Create three blocks with buttons

        # Block 1
        block_widget_1 = QWidget(self)
        block_layout_1 = QVBoxLayout(block_widget_1)
        button_1 = QPushButton('Button 1', block_widget_1)
        block_layout_1.addWidget(button_1)
        layout.addWidget(block_widget_1)

        # Block 2
        block_widget_2 = QWidget(self)
        block_layout_2 = QVBoxLayout(block_widget_2)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self.display_selected_file)
        block_layout_2.addWidget(self.list_widget)

        self.selected_file_label = QLabel('Selected File: ', block_widget_2)
        block_layout_2.addWidget(self.selected_file_label)

        add_button = QPushButton('Add File', block_widget_2)
        add_button.clicked.connect(self.add_file)
        block_layout_2.addWidget(add_button)

        delete_button = QPushButton('Delete File', block_widget_2)
        delete_button.clicked.connect(self.delete_file)
        block_layout_2.addWidget(delete_button)

        layout.addWidget(block_widget_2)

        # Block 3
        block_widget_3 = QWidget(self)
        block_layout_3 = QVBoxLayout(block_widget_3)
        button_3 = QPushButton('Button 3', block_widget_3)
        block_layout_3.addWidget(button_3)
        layout.addWidget(block_widget_3)

    def add_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            for file in selected_files:
                file_info = QFileInfo(file)
                file_name = file_info.fileName()

                list_item = QListWidgetItem(file_name)
                list_item.setData(Qt.UserRole, file)
                self.list_widget.addItem(list_item)

    def delete_file(self):
        selected_item = self.list_widget.currentItem()
        if selected_item is not None:
            self.list_widget.takeItem(self.list_widget.row(selected_item))
            self.selected_file_label.setText('Selected File: ')

    def display_selected_file(self, item):
        file_path = item.data(Qt.UserRole)
        self.selected_file_label.setText(f'Selected File: {file_path}')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
