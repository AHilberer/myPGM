import os

from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QToolTip,
    QVBoxLayout,
)
from PyQt5.QtCore import (
    QEvent,
    QRectF,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QFont, QFontInfo, QFontMetrics, QPainter, QPen

from myPGM.ui import icons, theme
from myPGM.ui.widgets import (Card, DashedFrame, ElidedLabel, button, divider, hbox,
                              icon_button, label)

ROW_HEIGHT = 30          # DESIGN.md §5: one line per file
NO_VALUE = "—"


class FileItemDelegate(QStyledItemDelegate):
    """One row of the file list (DESIGN.md §5): calibration dot · name (shortened in
    the middle) · fitted P in mono, or "—". The selected row is accent soft with an
    accent border. The calibration and fit model are in the tooltip.

    The rows hold the object ID (Qt.UserRole); `lookup(obj_id)` gives the object,
    read at paint time so that a new fit shows without rebuilding the list."""

    def __init__(self, lookup=None, parent=None):
        super().__init__(parent)
        self.lookup = lookup

    def _object(self, index):
        if self.lookup is None:
            return None
        return self.lookup(index.data(Qt.UserRole))

    @staticmethod
    def pressure_text(obj):
        if obj is None or obj.fit_result is None or obj.P is None:
            return NO_VALUE
        return f"{float(obj.P):.3f}"

    @staticmethod
    def tooltip(obj):
        if obj is None:
            return ""
        parts = [obj.filename or ""]
        if obj.fit_result is not None:
            if obj.calib is not None:
                parts.append(obj.calib.name)
            if obj.fit_model is not None:
                parts.append(obj.fit_model.name)
        else:
            parts.append("Not fitted")
        return " · ".join(p for p in parts if p)

    def sizeHint(self, option, index):
        height = max(ROW_HEIGHT, option.fontMetrics.height() + 12)
        return QSize(option.rect.width(), height)

    def paint(self, painter, option, index):
        t = theme.tokens()
        obj = self._object(index)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        rect = QRectF(option.rect).adjusted(0.5, 1.5, -0.5, -1.5)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        if selected:
            painter.setPen(QPen(theme.qcolor(t["ac"]), 1))
            painter.setBrush(theme.qcolor(t["acs"]))
            painter.drawRoundedRect(rect, 7, 7)
        elif hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(theme.qcolor(t["hd"]))
            painter.drawRoundedRect(rect, 7, 7)

        # dot: calibration colour once fitted, a neutral grey before
        fitted = obj is not None and obj.fit_result is not None
        dot = theme.calib_color(obj.calib) if fitted and obj.calib is not None else t["bd"]
        painter.setPen(Qt.NoPen)
        painter.setBrush(theme.qcolor(dot))
        center = rect.center()
        painter.drawEllipse(QRectF(rect.left() + 9, center.y() - 3.5, 7, 7))

        # fitted pressure on the right, mono
        mono = theme.mono_font(max(10, QFontInfo(option.font).pixelSize() - 1))
        p_text = self.pressure_text(obj)
        p_width = QFontMetrics(mono).horizontalAdvance(p_text)
        p_rect = QRectF(rect.right() - 8 - p_width, rect.top(), p_width, rect.height())
        painter.setFont(mono)
        painter.setPen(theme.qcolor(t["act"] if selected else t["mu"]))
        painter.drawText(p_rect, Qt.AlignRight | Qt.AlignVCenter, p_text)

        # name, shortened in the middle (keeps the extension)
        font = QFont(option.font)
        if selected:
            font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(theme.qcolor(t["tx"]))
        name_rect = QRectF(rect.left() + 23, rect.top(),
                           p_rect.left() - 8 - (rect.left() + 23), rect.height())
        name = index.data(Qt.DisplayRole) or ""
        shown = QFontMetrics(font).elidedText(name, Qt.ElideMiddle, int(name_rect.width()))
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, shown)
        painter.restore()

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.ToolTip:
            text = self.tooltip(self._object(index))
            if text:
                QToolTip.showText(event.globalPos(), text, view)
                return True
        return super().helpEvent(event, view, option, index)


class FileListViewerWidget(Card):
    """Spectra sidebar (DESIGN.md §1.2): add button, acquisition folder box with
    Load latest, the file list, and move up / move down / delete buttons. With no
    spectrum the list is replaced by a dashed "No spectra yet" box (DESIGN.md §4b)."""

    object_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__("Spectra")
        self.init_ui()

    def init_ui(self):
        self.add_button = icon_button("plus", "Add spectrum files…")
        self.header.addWidget(self.add_button)

        # acquisition folder: where "Load latest" looks for the newest spectrum
        folder_box = QFrame()
        folder_box.setObjectName("FolderBox")
        folder_box.setAttribute(Qt.WA_StyledBackground, True)
        folder_layout = QVBoxLayout(folder_box)
        folder_layout.setContentsMargins(10, 10, 10, 10)
        folder_layout.setSpacing(8)

        self.folder_icon = QLabel()
        self.dir_label = ElidedLabel("No acquisition folder")
        self.dir_label.setProperty("role", "caption-12")
        self.selectdir_button = QPushButton("Select…")
        self.selectdir_button.setProperty("role", "link")
        self.selectdir_button.setCursor(Qt.PointingHandCursor)
        self.selectdir_button.setToolTip("Select the acquisition folder")
        folder_row = hbox(self.folder_icon, self.dir_label, self.selectdir_button, spacing=5)
        folder_row.setStretchFactor(self.dir_label, 1)          # the name gets the room
        folder_layout.addLayout(folder_row)

        self.loadlatest_button = button(
            "Load latest", 36, primary=True, icon_name="refresh-cw",
            tooltip="Load the newest spectrum of the acquisition folder")
        folder_layout.addWidget(self.loadlatest_button)
        self.body.addWidget(folder_box)

        # Actual FileList_widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("FileList")
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setMouseTracking(True)            # hover highlight
        self.delegate = FileItemDelegate(parent=self.list_widget)
        self.list_widget.setItemDelegate(self.delegate)
        self.list_widget.itemClicked.connect(self.on_item_selected)
        self.list_widget.currentItemChanged.connect(self._on_current_changed)

        # empty state: dashed box instead of the list
        self.empty_box = DashedFrame(width=1, radius=10)
        self.empty_box.setObjectName("EmptyBox")
        empty_layout = QVBoxLayout(self.empty_box)
        empty_layout.setSpacing(6)
        empty_layout.addStretch(1)
        self.empty_icon = QLabel()
        self.empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_icon)
        for text in ("No spectra yet", "Drop .asc or .txt files here"):
            line = label(text, "muted-13")
            line.setAlignment(Qt.AlignCenter)
            line.setWordWrap(True)
            empty_layout.addWidget(line)
        empty_layout.addStretch(1)

        self.list_stack = QStackedWidget()
        self.list_stack.addWidget(self.list_widget)
        self.list_stack.addWidget(self.empty_box)
        self.body.addWidget(self.list_stack, 1)
        model = self.list_widget.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            signal.connect(self._update_empty_state)
        self._update_empty_state()

        # File moving section
        self.moveup_button = icon_button("chevron-up", "Move up", size=34)
        self.movedown_button = icon_button("chevron-down", "Move down", size=34)
        self.delete_button = icon_button("trash-2", "Remove the selected spectrum", size=34,
                                         role="mu")
        self.body.addWidget(divider(vertical=False))
        self.body.addLayout(hbox(self.moveup_button, self.movedown_button, 1,
                                 self.delete_button, spacing=6))
        self.restyle()

    def set_object_lookup(self, lookup):
        """`lookup(obj_id)`: the data object of a row (dot colour, fitted P, tooltip)."""
        self.delegate.lookup = lookup
        self.refresh()

    def refresh(self):
        """Repaint the rows (after a fit or a calibration change)."""
        self.list_widget.viewport().update()

    def is_empty(self):
        return self.list_widget.count() == 0

    def _update_empty_state(self, *_args):
        self.list_stack.setCurrentWidget(self.empty_box if self.is_empty() else self.list_widget)

    def set_directory(self, path):
        """Show the acquisition folder (its name; the full path in the tooltip)."""
        name = os.path.basename(os.path.normpath(path)) if path else ""
        self.dir_label.setText(name or "No acquisition folder")
        self.dir_label.setToolTip(path or "")
        self.dir_label.setProperty("role", "caption-12" if not name else "folder")
        self.dir_label.style().unpolish(self.dir_label)
        self.dir_label.style().polish(self.dir_label)
        self.dir_label.update()

    def restyle(self):
        muted = theme.qcolor(theme.tokens()["mu"]).name()
        self.folder_icon.setPixmap(icons.pixmap("folder", muted, 15))
        self.empty_icon.setPixmap(icons.pixmap("file-chart-line", muted, 18))
        self.refresh()

    def on_item_selected(self, item):
        self.object_selected.emit(item.data(Qt.UserRole))

    def _on_current_changed(self, current, _previous):
        """Arrow keys, Home / End: load the spectrum as a click does. A click also
        changes the current item, on press: it loads on release (itemClicked)."""
        if current is not None and QApplication.mouseButtons() == Qt.NoButton:
            self.on_item_selected(current)
