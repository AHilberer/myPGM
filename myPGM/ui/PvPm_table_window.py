import pandas as pd
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal


class HPTableWidget(QTableWidget):
    """Qt widget class for HPDataTable objects"""

    def __init__(self, HPDataTable_):
        super().__init__()

        self.data = HPDataTable_

        self.setStyleSheet("font-size: 12px;")

        nrows, ncols = self.data.df.shape

        self.setColumnCount(ncols)
        self.setRowCount(nrows)

        self.setHorizontalHeaderLabels(list(self.data.df.columns))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.cellChanged[int, int].connect(self.getfromentry)

        # deleteline_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        # deleteline_shortcut.activated.connect(self.remove_line)

    def getfromentry(self, row, col):
        # takes care of types
        try:
            newval = float(self.item(row, col).text())
        except ValueError:
            newval = self.item(row, col).text()

        key = self.data.df.columns[col]

        if key != "calib":
            self.data.setitemval(row, key, newval)

            if key == "P":
                self.data.reinvcalc_item_P(row)
            elif key in ["x", "x0", "T", "T0"]:
                self.data.recalc_item_P(row)

        else:  # k = calib
            # I do not accept any calib change (for now a least)
            pass

    def updatetable(self):
        nrows, ncols = self.data.df.shape
        self.setRowCount(nrows)

        # Absolutely necessary to disconnect otherwise infinite loop
        self.cellChanged[int, int].disconnect()

        for irow in range(self.rowCount()):
            for icol in range(self.columnCount()):
                # print round() values in table
                v = self.data.df.iloc[irow, icol]
                if isinstance(v, (int, float)):
                    s = str(round(v, 3))
                else:
                    s = str(v)

                self.setItem(irow, icol, QTableWidgetItem(s))

        self.cellChanged[int, int].connect(self.getfromentry)

    def remove_line(self):
        index = self.currentRow()
        if index >= 0:
            self.data.removespecific(index)


class HPTableWindow(QWidget):
    def __init__(self, HPDataTable_, calibrations_):
        super().__init__()

        self.data = HPDataTable_
        self.calibrations = calibrations_
        self.setWindowTitle("PvPm table")
        self.setGeometry(1000, 100, 450, 400)

        # centerPoint = QDesktopWidget().availableGeometry().center()
        # thePosition = (centerPoint.x() + 200, centerPoint.y() + 50)
        # self.move(*thePosition)

        layout = QVBoxLayout()

        self.table_widget = HPTableWidget(HPDataTable_)
        layout.addWidget(self.table_widget)

        table_actions_layout = QHBoxLayout()

        self.table_save_csv_button = QPushButton("Save data to csv")
        self.table_load_csv_button = QPushButton("Load data from csv")
        table_actions_layout.addWidget(self.table_save_csv_button)
        table_actions_layout.addWidget(self.table_load_csv_button)

        layout.addLayout(table_actions_layout)

        self.setLayout(layout)

        self.table_save_csv_button.clicked.connect(self.save_data_to_csv)
        self.table_load_csv_button.clicked.connect(self.load_data_from_csv)

        # save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        # load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        # save_shortcut.activated.connect(self.save_data_to_csv)
        # load_shortcut.activated.connect(self.load_data_from_csv)

    def save_data_to_csv(self):
        file = self.get_save_filename_dialog()
        if file:
            self.data.df.to_csv(file, sep="\t", decimal=".", header=True, index=False)

    def load_data_from_csv(self):
        file = self.get_load_filename_dialog()
        if file:
            df_ = pd.read_csv(file, sep="\t", decimal=".", header=[0], index_col=None)

        self.data.reconstruct_from_df(df_, self.calibrations)

    def get_save_filename_dialog(self):
        options = QFileDialog.Options()
        # options = QFileDialog.DontUseNativeDialog
        # seems to bring an warning on Linux 5.10.0-19-amd64 #1 SMP Debian 5.10.149-2 (2022-10-21) x86_64 GNU/Linux
        # if I choose to not use Native Dialog - Hope it works with native on other platform

        fileName, fileType = QFileDialog.getSaveFileName(
            self,
            "myPRL-qt: Save data to csv",
            "",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )

        if fileType == "CSV Files (*.csv)":
            if ".csv" in fileName:
                pass
            else:
                fileName += ".csv"

        if fileName:
            return fileName
        else:
            return None

    def get_load_filename_dialog(self):
        options = QFileDialog.Options()
        # options = QFileDialog.DontUseNativeDialog
        # seems to bring an warning on Linux 5.10.0-19-amd64 #1 SMP Debian 5.10.149-2 (2022-10-21) x86_64 GNU/Linux
        # if I choose to not use Native Dialog - Hope it works with native on other platform

        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "myPRL-qt: Load data from csv",
            "",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )
        if fileName:
            return fileName
        else:
            return None


class HPData():

    def __init__(self, Pm, P, x, T, x0, T0, calib, file):
        super().__init__()

        self.Pm = Pm
        self.P = P
        self.x = x
        self.T = T
        self.x0 = x0
        self.T0 = T0
        self.calib = calib
        self.file = file

    def __repr__(self):
        return str(self.df)

    def calcP(self):
        self.P = self.calib.func(self.x, self.T, self.x0, self.T0)

    def invcalcP(self):
        self.x = self.calib.invfunc(self.P, self.T, self.x0, self.T0)

    # SOMETHING TO RETRIEVE THE CALIB OBJECT BY ITS NAME ?

    @property
    def df(self):       
        _df = pd.DataFrame({'Pm': self.Pm,
                            'P' : self.P, 
                            'x' : self.x,
                            'T' : self.T,
                            'x0': self.x0,
                            'T0': self.T0,
                            'calib': self.calib.name,
                            'file' : self.file}, index=[0])
        return _df



class HPDataTable(QObject):
    
    changed = pyqtSignal()

    def __init__(self, df=None, calibrations=None):
        super().__init__()  
    
        self.datalist = []

        if df is not None:
            self.reconstruct_from_df(df, calibrations)

    def __repr__(self):
        return str( self.df )

    def __getitem__(self, index):
        return self.datalist[index]

    def __setitem__(self, index, HPDataobj):
        self.datalist[index] = HPDataobj
        self.changed.emit()

    def __len__(self):
        return len(self.datalist)


    def recalc_item_P(self, index):
        # method implemented to emit change!
        self.datalist[index].calcP()
        self.changed.emit()

    def reinvcalc_item_P(self, index):
        self.datalist[index].invcalcP()
        self.changed.emit()

    def setitemval(self, item, attr, val):
        if val != getattr(self.datalist[item],attr): 
            setattr(self.datalist[item], attr, val)
            self.changed.emit()

    def add(self, buffer):
        # NB:  deepcopy fails if HPData inherits from QObject !
        # deepcopy absolutely necessary here
        # Here I work with the HPData object
        self.datalist.append( deepcopy(buffer) )
        self.changed.emit()

    def removelast(self):
        # Here I work with the HPData object
        self.datalist = self.datalist[:-1]
        self.changed.emit()

    def removespecific(self, index):
        del self.datalist[index]
        self.changed.emit()

    def reconstruct_from_df(self, df, calibrations):
        # erases the previous content!
        self.datalist = []
        for _, row in df.iterrows():
            HPdi = HPData(Pm = row['Pm'],
                          P  = row['P'], 
                          x  = row['x'], 
                          T  = row['T'], 
                          x0 = row['x0'], 
                          T0 = row['T0'],
                          calib = calibrations[row['calib']], # retrieve calib
                          file = row['file'])
            self.datalist.append(HPdi)
        self.changed.emit()

    @property
    def df(self):
        # should be used only as a REPRESENTATION of HPDataTable
        _df = pd.DataFrame(columns=['Pm','P','x','T','x0','T0','calib','file'])
        for xi in self.datalist:
            _df = pd.concat([_df, xi.df ], ignore_index=True)
        return _df
