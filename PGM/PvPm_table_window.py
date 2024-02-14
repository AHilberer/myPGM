import pandas as pd
from PyQt5.QtWidgets import (QWidget,
                             QVBoxLayout,
                             QGroupBox,
                             QTabWidget,
                             QCheckBox,
                             QTableView,
                             QStyledItemDelegate,
                             QLineEdit,
                             QPushButton,
                             QHBoxLayout,
                             QFrame
                             )
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex


class MyQSeparator(QFrame):
	def __init__(self):
		super().__init__()
		self.setFrameShape(QFrame.HLine)
		self.setFrameShadow(QFrame.Sunken)

#? Define PvPm table class

class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe"""

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._dataframe)
        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._dataframe.iloc[index.row(), index.column()])

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            self._dataframe.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index,index)
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])
        return None
    
class EditableDelegate(QStyledItemDelegate):
    """A delegate that allows for cell editing"""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

class PvPmTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PvPm table')
        self.setGeometry(900, 100, 450, 400)
        self.layout = QVBoxLayout()

        ButtonBoxLayout = QHBoxLayout()

        self.test1 = QPushButton("+")
        self.test2 = QPushButton("-")
        ButtonBoxLayout.addWidget(self.test1)
        ButtonBoxLayout.addWidget(self.test2)

        self.layout.addLayout(ButtonBoxLayout)

        self.layout.addWidget(MyQSeparator())
        self.PvPmTable = QTableView()
        self.PvPmTable.setAlternatingRowColors(True)
        self.PvPmTable.setSelectionBehavior(QTableView.SelectRows)
        self.layout.addWidget(self.PvPmTable)
        self.setLayout(self.layout)
        