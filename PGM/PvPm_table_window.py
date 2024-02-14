import pandas as pd
from PyQt5.QtWidgets import (QWidget,
                             QVBoxLayout,
                             QGroupBox,
                             QTabWidget,
                             QCheckBox,
                             QTableView
                             )
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex




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

class PvPmTableWindow(Qwidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PvPm table')
        self.setGeometry(900, 100, 450, 400)
        self.PvPmTable = QTableView()
            
        self.PvPm_df = pd.DataFrame({'Pm':'', 'P':'', 'lambda':'', 'File':''}, index=[0])

        self.PvPm_data_inst = PandasModel(self.PvPm_df)
        delegate = EditableDelegate()
        self.PvPm_data_inst.dataChanged.connect(self.plot_PvPm)
        self.PvPmTable.setModel(self.PvPm_data_inst)
        self.PvPmTable.setItemDelegate(delegate)
        self.PvPmTable.setAlternatingRowColors(True)
        self.PvPmTable.setSelectionBehavior(QTableView.SelectRows)