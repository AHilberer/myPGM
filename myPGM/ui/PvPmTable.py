import csv
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
    QAbstractItemView,
    QMenu,
    QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap

from myPGM.settings import last_dir, remember_dir
from myPGM.ui.PressureToolbox import PressureToolbox
from myPGM.ui import theme
from myPGM.ui.widgets import button

logger = logging.getLogger(__name__)

ROOM_T = 298
SORT_ROLE = Qt.UserRole          # numeric value used for sorting
ID_ROLE = Qt.UserRole + 1        # object ID, stored on the '#' item of each row

# key, header, numeric, shown by default
COLUMNS = [
    ("#",      "#",           True,  True),
    ("Pm",     "Pm (bar)",    True,  True),
    ("P",      "P (GPa)",     True,  True),    # P ± fit uncertainty
    ("x",      "x",           True,  True),    # unit in each cell (nm or cm⁻¹)
    ("x_err",  "σx (fit)", True, False),
    ("T",      "T (K)",       True,  False),   # shown automatically when a T is not 298 K
    ("x0",     "x0",          True,  False),
    ("T0",     "T0 (K)",      True,  False),
    ("calib",  "calibration", False, True),
    ("file",   "file",        False, True),
]
COLUMN_INDEX = {key: i for i, (key, *_rest) in enumerate(COLUMNS)}


def _unit(calib):
    return {"cm-1": "cm⁻¹"}.get(calib.xunit, calib.xunit) if calib is not None else ""


def _with_unit(value, calib, decimals):
    return "" if value is None else f"{float(value):.{decimals}f} {_unit(calib)}".rstrip()


def _p_text(P, P_err):
    if P is None:
        return ""
    if P_err is None:
        return f"{P:.3f}"
    err = f"{P_err:.3f}" if round(P_err, 3) > 0 else "<0.001"
    return f"{P:.3f} ± {err}"


def _csv_value(v):
    """Full precision, blank when missing."""
    return "" if v is None else repr(float(v))


def _colour_dot(colour, size=12):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(colour))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    icon = QIcon(pixmap)
    # not tinted by the selection colour in the selected row
    icon.addPixmap(pixmap, QIcon.Selected)
    return icon


class SortableItem(QTableWidgetItem):
    """Table item sorted by its SORT_ROLE value (numbers as numbers, blanks first)."""

    def __lt__(self, other):
        a, b = self.data(SORT_ROLE), other.data(SORT_ROLE)
        if a is None or b is None:
            return a is None and b is not None
        # Qt requires a Python bool (comparing numpy values gives numpy.bool_)
        return bool(a < b)


class HPTableWidget(QTableWidget):
    """PvPm table: one row per point added to the table, built from the data manager."""

    # Use object to avoid truncation of large integer IDs in Qt int signals.
    recall_requested = pyqtSignal(object)
    rows_changed = pyqtSignal(int)          # number of points, after each update

    def __init__(self):
        super().__init__()

        self.data_manager = None
        self._shown_count = 0               # rows at the last update: new ones are scrolled to
        self.user_column_visibility = {}   # columns shown/hidden from the header menu
        self.font_px = 18

        self.set_font_size(18)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels([header for _, header, _, _ in COLUMNS])

        h_header = self.horizontalHeader()
        for col in range(len(COLUMNS) - 1):
            h_header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(COLUMN_INDEX["file"], QHeaderView.Stretch)
        h_header.setContextMenuPolicy(Qt.CustomContextMenu)
        h_header.customContextMenuRequested.connect(self._show_column_menu)
        self.verticalHeader().hide()          # the '#' column gives the order instead

        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        h_header.setSortIndicator(COLUMN_INDEX["#"], Qt.AscendingOrder)
        self.setSortingEnabled(True)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

        self._apply_column_visibility([])

    def set_data_manager(self, data_manager):
        self.data_manager = data_manager

    def set_font_size(self, size):
        self.font_px = size
        # this widget stylesheet overrides the app-wide font size, so it is set here
        self.setStyleSheet(
            f"QTableWidget {{ font-size: {size}px; }}"
            f"QHeaderView::section {{ padding: 2px; font-size: {size}px; }}"
            "QTableWidget::item { padding: 2px 6px; }"
        )
        # rows were fixed at 18 px high, which clipped larger fonts
        self.verticalHeader().setDefaultSectionSize(size + 6)
        self.setIconSize(QSize(size - 4, size - 4))
        if self.data_manager is not None:
            self.updatetable()          # numbers are drawn in a mono font of this size

    # --- content -----------------------------------------------------------------------

    def _cells(self, number, obj):
        """(text, sort value) for each column of one table entry, plus decorations."""
        calib = obj.calib
        uses_x0 = calib is None or getattr(calib, "uses_x0", True)
        return {
            "#": (str(number), number),
            "Pm": ("" if obj.Pm is None else f"{float(obj.Pm):.2f}", obj.Pm),
            "P": (_p_text(obj.P, getattr(obj, "P_err", None)), obj.P),
            "x": (_with_unit(obj.x, calib, 3), obj.x),
            "x_err": (_with_unit(getattr(obj, "x_err", None), calib, 4), getattr(obj, "x_err", None)),
            "T": ("" if obj.T is None else f"{float(obj.T):.1f}", obj.T),
            # blank for calibrations that do not use x0 (H2 vibron)
            "x0": (_with_unit(obj.x0, calib, 3) if uses_x0 else "", obj.x0 if uses_x0 else None),
            "T0": ("" if obj.T0 is None else f"{float(obj.T0):.1f}", obj.T0),
            "calib": (calib.short_name if calib is not None else "",
                      calib.short_name if calib is not None else ""),
            "file": (obj.filename or "", obj.filename or ""),
        }

    def updatetable(self):
        entries = self.data_manager.table_entries() if self.data_manager is not None else []
        mono = theme.mono_font(self.font_px)        # numbers in the mono font (DESIGN.md §2)
        # filling a sorted table moves rows while they are filled: sort afterwards
        self.setSortingEnabled(False)
        self.setRowCount(len(entries))
        for row, obj in enumerate(entries):
            for key, (text, sort_value) in self._cells(row + 1, obj).items():
                col = COLUMN_INDEX[key]
                item = SortableItem(text)
                # plain Python values: fitted P and x are numpy floats
                if sort_value is not None and not isinstance(sort_value, str):
                    sort_value = float(sort_value)
                item.setData(SORT_ROLE, sort_value)
                if COLUMNS[col][2]:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    item.setFont(mono)
                self.setItem(row, col, item)
            self._decorate_row(row, obj)
        self.setSortingEnabled(True)
        self._apply_column_visibility(entries)
        if len(entries) > self._shown_count:
            self._scroll_to_number(len(entries))        # the point just added
        self._shown_count = len(entries)
        self.rows_changed.emit(len(entries))

    def _scroll_to_number(self, number):
        """Scroll the row numbered `number` ('#' column) into view, whatever the sort."""
        for row in range(self.rowCount()):
            item = self.item(row, COLUMN_INDEX["#"])
            if item is not None and item.data(SORT_ROLE) == number:
                self.scrollToItem(item, QAbstractItemView.EnsureVisible)
                return

    def _decorate_row(self, row, obj):
        self.item(row, COLUMN_INDEX["#"]).setData(ID_ROLE, obj.id)
        if obj.calib is not None:
            calib_item = self.item(row, COLUMN_INDEX["calib"])
            calib_item.setIcon(_colour_dot(theme.calib_color(obj.calib)))
            calib_item.setToolTip(obj.calib.name)
        if obj.full_path:
            self.item(row, COLUMN_INDEX["file"]).setToolTip(obj.full_path)
        if obj.T is not None and abs(obj.T - ROOM_T) > 0.05:
            # same colour as the T field of the pressure toolbox (follows the theme)
            self.item(row, COLUMN_INDEX["T"]).setBackground(QColor(PressureToolbox.ORANGE))

    # --- columns -------------------------------------------------------------------------

    def _apply_column_visibility(self, entries):
        not_room_T = any(o.T is not None and abs(o.T - ROOM_T) > 0.05 for o in entries)
        for col, (key, _header, _numeric, shown) in enumerate(COLUMNS):
            if key == "T":
                shown = shown or not_room_T
            self.setColumnHidden(col, not self.user_column_visibility.get(key, shown))

    def _show_column_menu(self, position):
        self.column_menu().exec_(self.horizontalHeader().mapToGlobal(position))

    def column_menu(self):
        """Menu of the optional columns (header right-click and the Columns button)."""
        menu = QMenu(self)
        for col, (key, header, _numeric, _shown) in enumerate(COLUMNS):
            if key == "#":
                continue
            action = menu.addAction(header)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(col))
            action.toggled.connect(lambda visible, key=key: self.set_column_visible(key, visible))
        return menu

    def set_column_visible(self, key, visible):
        self.user_column_visibility[key] = visible
        self.setColumnHidden(COLUMN_INDEX[key], not visible)

    # --- rows -> objects -----------------------------------------------------------------------

    def object_id_at(self, row):
        item = self.item(row, COLUMN_INDEX["#"]) if row >= 0 else None
        return item.data(ID_ROLE) if item is not None else None

    def _on_cell_double_clicked(self, row, _column):
        obj_id = self.object_id_at(row)
        if obj_id is not None:
            self.recall_requested.emit(obj_id)

    # --- export ----------------------------------------------------------------------------

    def export_rows(self):
        """Header and rows for the CSV export: every value at full precision,
        independent of the columns shown and of the display formatting."""
        header = ["#", "Pm (bar)", "P (GPa)", "sigma_P_fit (GPa)", "x", "sigma_x_fit", "x unit",
                  "T (K)", "x0", "T0 (K)", "calibration", "fit model", "file", "path"]
        rows = []
        entries = self.data_manager.table_entries() if self.data_manager is not None else []
        for number, obj in enumerate(entries, start=1):
            calib = obj.calib
            uses_x0 = calib is None or getattr(calib, "uses_x0", True)
            value = _csv_value
            rows.append([
                number, value(obj.Pm), value(obj.P), value(getattr(obj, "P_err", None)),
                value(obj.x), value(getattr(obj, "x_err", None)),
                calib.xunit if calib is not None else "",
                value(obj.T), value(obj.x0) if uses_x0 else "", value(obj.T0),
                calib.name if calib is not None else "",
                obj.fit_model.name if obj.fit_model is not None else "",
                obj.filename or "", obj.full_path or "",
            ])
        return header, rows


class HPTableWindow(QWidget):
    """Pressure log: the table, shown in the bottom dock. Its header actions (point
    count, Columns, Remove selected, Clear) are placed in the dock header."""
    table_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.data_manager = None

        self.setWindowTitle("Pressure log")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table_widget = HPTableWidget()
        self.table_widget.setObjectName("PressureLogTable")
        layout.addWidget(self.table_widget)

        self.count_label = QLabel()
        self.count_label.setObjectName("CountPill")
        self.count_label.setFixedHeight(22)
        self.columns_button = button("Columns", 32, tooltip="Show or hide columns")
        self.remove_selected_button = button("Remove selected", 32)
        self.clear_table_button = button("Clear", 32, tooltip="Remove every point of the log")
        self.header_widgets = [self.count_label]
        self.header_actions = [self.columns_button, self.remove_selected_button,
                               self.clear_table_button]

        self.columns_button.clicked.connect(self._show_columns_menu)
        self.remove_selected_button.clicked.connect(self.delete_selected)
        self.clear_table_button.clicked.connect(self.clear_table)
        self.table_widget.rows_changed.connect(self._update_count)
        self._update_count(0)

    def _update_count(self, count):
        self.count_label.setText(f"{count} point{'' if count == 1 else 's'}")

    def _show_columns_menu(self):
        menu = self.table_widget.column_menu()
        menu.exec_(self.columns_button.mapToGlobal(self.columns_button.rect().bottomLeft()))

    def delete_selected(self):
        obj_id = self.table_widget.object_id_at(self.table_widget.currentRow())
        if obj_id is None or self.data_manager is None:
            return
        obj = self.data_manager.get(obj_id, None)
        if obj is not None:
            self.data_manager.remove_from_table(obj)
        self.table_changed.emit()

    def clear_table(self):
        if self.data_manager is None:
            return
        for obj in self.data_manager.table_entries():
            self.data_manager.remove_from_table(obj)
        self.table_changed.emit()

    def set_data_manager(self, data_manager):
        self.data_manager = data_manager
        self.table_widget.set_data_manager(data_manager)

    def save_data_to_csv(self):
        file_path = self.get_save_filename_dialog()
        if file_path:
            header, rows = self.table_widget.export_rows()
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as file_handle:
                    writer = csv.writer(file_handle)
                    writer.writerow(header)
                    writer.writerows(rows)
            except OSError as exc:
                # e.g. no permission, or the file is open in Excel on Windows
                logger.warning("Could not export the table to %s: %s", file_path, exc)
                QMessageBox.critical(self, "Export error", f"Could not export the table:\n{exc}")

    def get_save_filename_dialog(self):
        options = QFileDialog.Options()
        # options = QFileDialog.DontUseNativeDialog
        # seems to bring an warning on Linux 5.10.0-19-amd64 #1 SMP Debian 5.10.149-2 (2022-10-21) x86_64 GNU/Linux
        # if I choose to not use Native Dialog - Hope it works with native on other platform

        fileName, fileType = QFileDialog.getSaveFileName(
            self,
            "myPGM: Save data to csv",
            last_dir("exports"),
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )

        # endswith: ".csv" anywhere in the path (e.g. a folder name) skipped the extension
        if fileType == "CSV Files (*.csv)" and fileName and not fileName.lower().endswith(".csv"):
            fileName += ".csv"
        remember_dir("exports", fileName)

        if fileName:
            return fileName
        else:
            return None
