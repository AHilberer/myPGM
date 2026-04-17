import csv

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
    QAbstractItemView,
)
from PyQt5.QtCore import pyqtSignal


class HPTableWidget(QTableWidget):
    """Qt widget class for HPDataTable objects"""

    # Use object to avoid truncation of large integer IDs in Qt int signals.
    recall_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.data_manager = None
        self.row_object_ids = []


        self.setStyleSheet(
            "QTableWidget { font-size: 11px; }"
            "QHeaderView::section { padding: 2px; }"
            "QTableWidget::item { padding: 2px; }"
        )

        column_labels = ["Pm", "P", "x", "T", "x0", "T0", "calib", "file"]
        self.setColumnCount(len(column_labels))
        #self.setRowCount(3)

        self.setHorizontalHeaderLabels(column_labels)

#        self.resizeColumnsToContents()
        h_header = self.horizontalHeader()
        ncols = self.columnCount()
        
        for col in range(ncols-2):
            h_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        
        self.setColumnWidth(ncols-2, 70)
        h_header.setSectionResizeMode(ncols-2, QHeaderView.Interactive)
        
        h_header.setSectionResizeMode(ncols-1, QHeaderView.Stretch)

        self.verticalHeader().setDefaultSectionSize(18)
#        self.horizontalHeader().setDefaultSectionSize(70)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

        

        #self.cellChanged[int, int].connect(self.get_from_entry)

        # delete_line_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        # delete_line_shortcut.activated.connect(self.remove_line)

    def set_data_manager(self, data_manager):
        self.data_manager = data_manager

    @staticmethod
    def _format_float(value, decimals):
        if value is None:
            return ""
        return f"{float(value):.{decimals}f}"

    def _build_rows_from_manager(self):
        if self.data_manager is None:
            return [], []

        rows = []
        row_ids = []
        for obj in self.data_manager.values():
            if getattr(obj, "include_in_table", False):
                rows.append(
                    {
                        "Pm": self._format_float(obj.Pm, 2),
                        "P": self._format_float(obj.P, 3),
                        "x": self._format_float(obj.x, 3),
                        "T": self._format_float(obj.T, 3),
                        "x0": self._format_float(obj.x0, 3),
                        "T0": self._format_float(obj.T0, 3),
                        "calib": obj.calib.name if obj.calib is not None else "",
                        "file": obj.filename if obj.filename is not None else "",
                    }
                )
                row_ids.append(obj.id)
        return rows, row_ids

    def updatetable(self, incoming_table=None):
        if incoming_table is None:
            incoming_table, self.row_object_ids = self._build_rows_from_manager()
        else:
            self.row_object_ids = []

        if incoming_table == []:
            self.setRowCount(0)
            return
        else:

            self.setRowCount(len(incoming_table))
            self.setColumnCount(len(incoming_table[0]))
            self.setHorizontalHeaderLabels(list(incoming_table[0].keys()))
            self.column_index = {label: i for i, label in enumerate(incoming_table[0].keys())}

            for row, data in enumerate(incoming_table):
                for key, value in data.items():
                    col = self.column_index[key]
                    self.setItem(row, col, QTableWidgetItem(str(value)))

    def _on_cell_double_clicked(self, row, _column):
        if 0 <= row < len(self.row_object_ids):
            self.recall_requested.emit(self.row_object_ids[row])


#    def remove_line(self):
#        index = self.currentRow()
#        if index >= 0:
#            self.data.removespecific(index)


class HPTableWindow(QWidget):
    def __init__(self):  # HPDataTable_, calibrations_):
        super().__init__()

        self.data_manager = None

        self.setWindowTitle("PvPm table")
        self.setGeometry(1000, 100, 500, 400)

        # centerPoint = QDesktopWidget().availableGeometry().center()
        # thePosition = (centerPoint.x() + 200, centerPoint.y() + 50)
        # self.move(*thePosition)

        layout = QVBoxLayout()

        self.table_widget = HPTableWidget()
        layout.addWidget(self.table_widget)

        table_actions_layout = QHBoxLayout()

        self.remove_selected_button = QPushButton("Remove selected")
        self.clear_table_button = QPushButton("Clear table")

        self.table_save_csv_button = QPushButton("Export table to csv")
        # self.table_load_csv_button = QPushButton("Load data from csv")
        table_actions_layout.addWidget(self.remove_selected_button)        
        table_actions_layout.addWidget(self.clear_table_button)        
        table_actions_layout.addWidget(self.table_save_csv_button)
        # table_actions_layout.addWidget(self.table_load_csv_button)

        layout.addLayout(table_actions_layout)

        self.setLayout(layout)

        self.table_save_csv_button.clicked.connect(self.save_data_to_csv)
        self.remove_selected_button.clicked.connect(self.delete_selected)
        self.clear_table_button.clicked.connect(self.clear_table)
        



        # self.table_load_csv_button.clicked.connect(self.load_data_from_csv)

        # save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        # load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        # save_shortcut.activated.connect(self.save_data_to_csv)
        # load_shortcut.activated.connect(self.load_data_from_csv)

    def delete_selected(self):
        
        index = self.table_widget.currentRow()
        if index < 0:
            return

        if self.data_manager is not None and index < len(self.table_widget.row_object_ids):
            obj_id = self.table_widget.row_object_ids[index]
            obj = self.data_manager.get(obj_id, None)
            if obj is not None:
                obj.include_in_table = False
            self.table_widget.updatetable()
            return

        self.table_widget.removeRow(index)

    def clear_table(self):
        if self.data_manager is not None:
            for obj in self.data_manager.values():
                obj.include_in_table = False
            self.table_widget.updatetable()
            return

        self.table_widget.setRowCount(0)

    def set_data_manager(self, data_manager):
        self.data_manager = data_manager
        self.table_widget.set_data_manager(data_manager)

    def save_data_to_csv(self):
        file_path = self.get_save_filename_dialog()
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)
                row_count = self.table_widget.rowCount()
                column_count = self.table_widget.columnCount()

                # Write header row
                headers = [self.table_widget.horizontalHeaderItem(i).text() for i in range(column_count)]
                writer.writerow(headers)

                # Write data rows
                for row in range(row_count):
                    row_data = []
                    for col in range(column_count):
                        item = self.table_widget.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)


    def get_save_filename_dialog(self):
        options = QFileDialog.Options()
        # options = QFileDialog.DontUseNativeDialog
        # seems to bring an warning on Linux 5.10.0-19-amd64 #1 SMP Debian 5.10.149-2 (2022-10-21) x86_64 GNU/Linux
        # if I choose to not use Native Dialog - Hope it works with native on other platform

        fileName, fileType = QFileDialog.getSaveFileName(
            self,
            "myPGM: Save data to csv",
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

    # def get_load_filename_dialog(self):
    #     options = QFileDialog.Options()
    #     # options = QFileDialog.DontUseNativeDialog
    #     # seems to bring an warning on Linux 5.10.0-19-amd64 #1 SMP Debian 5.10.149-2 (2022-10-21) x86_64 GNU/Linux
    #     # if I choose to not use Native Dialog - Hope it works with native on other platform

    #     fileName, _ = QFileDialog.getOpenFileName(
    #         self,
    #         "myPGM: Load data from csv",
    #         "",
    #         "CSV Files (*.csv);;All Files (*)",
    #         options=options,
    #     )
    #     if fileName:
    #         return fileName
    #     else:
    #         return None

