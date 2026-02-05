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


class HPTableWidget(QTableWidget):
    """Qt widget class for HPDataTable objects"""

    def __init__(self):
        super().__init__()

        #self.data = HPDataTable_

        self.setStyleSheet("font-size: 12px;")

        #nrows, ncols = self.data.df.shape

        column_labels = ["Pm", "P", "x", "T", "x0", "T0", "calib", "file"]
        self.setColumnCount(len(column_labels))
        self.setRowCount(3)

        self.setHorizontalHeaderLabels(column_labels)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        

        #self.cellChanged[int, int].connect(self.getfromentry)

        # deleteline_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        # deleteline_shortcut.activated.connect(self.remove_line)

    def updatetable(self, incomming_table):
        print(incomming_table)
        self.setRowCount(len(incomming_table))
        self.setColumnCount(len(incomming_table[0]))
        self.setHorizontalHeaderLabels(list(incomming_table[0].keys()))
        self.column_index = {label: i for i, label in enumerate(incomming_table[0].keys())}

        for row, data in enumerate(incomming_table):
            for key, value in data.items():
                col = self.column_index[key]
                self.setItem(row, col, QTableWidgetItem(str(value)))

        # self.cellChanged[int, int].connect(self.getfromentry)

    def remove_line(self):
        index = self.currentRow()
        if index >= 0:
            self.data.removespecific(index)


class HPTableWindow(QWidget):
    def __init__(self): # HPDataTable_, calibrations_):
        super().__init__()

        self.setWindowTitle("PvPm table")
        self.setGeometry(1000, 100, 450, 400)

        # centerPoint = QDesktopWidget().availableGeometry().center()
        # thePosition = (centerPoint.x() + 200, centerPoint.y() + 50)
        # self.move(*thePosition)

        layout = QVBoxLayout()

        self.table_widget = HPTableWidget()
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
        pass
        # file = self.get_save_filename_dialog()
        # if file:
        #     self.data.df.to_csv(file, sep="\t", decimal=".", header=True, index=False)

    def load_data_from_csv(self):
        pass
        # file = self.get_load_filename_dialog()
        # if file:
        #     df_ = pd.read_csv(file, sep="\t", decimal=".", header=[0], index_col=None)

        # self.data.reconstruct_from_df(df_, self.calibrations)

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

