import sys
from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QListView, QWidget, QPushButton, QLabel

class CustomFileItem:
    def __init__(self, name, size):
        self.name = name
        self.size = size

class CustomFileListModel(QAbstractListModel):
    itemAdded = pyqtSignal()  # Signal emitted when an item is added
    itemDeleted = pyqtSignal()  # Signal emitted when an item is deleted

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.items[index.row()].name
        elif role == Qt.UserRole:
            return self.items[index.row()]

    def addItem(self, item):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.items.append(item)
        self.endInsertRows()
        self.itemAdded.emit()  # Emit signal to notify the view

    def deleteItem(self, index):
        self.beginRemoveRows(QModelIndex(), index, index)
        del self.items[index]
        self.endRemoveRows()
        self.itemDeleted.emit()  # Emit signal to notify the view

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom Model Example")
        self.setGeometry(100, 100, 400, 300)

        layoutWidget = QWidget(self)
        self.setCentralWidget(layoutWidget)

        layout = QVBoxLayout()

        custom_items = [CustomFileItem(f"File_{i}.txt", i * 100) for i in range(5)]

        self.custom_model = CustomFileListModel(items=custom_items)
        list_view = QListView(self)
        list_view.setModel(self.custom_model)
        list_view.clicked.connect(self.item_clicked)  # Connect the clicked signal to the slot

        layout.addWidget(list_view)

        add_button = QPushButton("Add Item", self)
        add_button.clicked.connect(self.add_item)
        layout.addWidget(add_button)

        delete_button = QPushButton("Delete Item", self)
        delete_button.clicked.connect(self.delete_item)
        layout.addWidget(delete_button)

        self.selected_file_label = QLabel("Selected File: None", self)
        layout.addWidget(self.selected_file_label)

        layoutWidget.setLayout(layout)

    @pyqtSlot(QModelIndex)
    def item_clicked(self, index):
        selected_item = self.custom_model.data(index, role=Qt.UserRole)
        self.selected_file_label.setText(f"Selected File: {selected_item.name}, File Size: {selected_item.size} bytes")

    @pyqtSlot()
    def add_item(self):
        new_item = CustomFileItem("New File", 500)
        self.custom_model.addItem(new_item)

    @pyqtSlot()
    def delete_item(self):
        selected_index = self.centralWidget().layout().itemAt(0).widget().currentIndex()
        if selected_index.isValid():
            self.custom_model.deleteItem(selected_index.row())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
