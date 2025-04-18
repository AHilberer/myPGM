import numpy as np
import pandas as pd
from copy import deepcopy
from scipy.optimize import minimize
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QAbstractListModel, QModelIndex
import csv

def customparse_file2data(f):
    with open(f, 'r') as file: # binary
        # try to find delimiter in the 2000 last characters:
        delimiter = csv.Sniffer().sniff(file.read()[-2000:]).delimiter
        file.seek(0) # back to beginning
        header_count = 0
        for s in file:
            sp = s.strip().split(delimiter)
            if len(sp) != 2:
                header_count += 1
            else:
                try:
                    _ = list(map(float, sp))
                    break
                except:
                    header_count += 1
#        print(delimiter, header_count)
        file.seek(0) # back to beginning
        data = np.loadtxt(file, 
                          delimiter=delimiter,
                          skiprows=header_count, 
                          dtype=str)
    # in case of empty columns in ascii file... 
    # only manage 2 columns    
    try:
        return data.astype(np.float64)
    except ValueError:

        return data[:,:2].astype(np.float64) 



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






if __name__ == '__main__':
    import os
    f1 = os.path.dirname(__file__)+'/resources/various_file_formats/'+'Example_Ruby_3_tab_very_long_header.asc'
    
    print(customparse_file2data(f1))