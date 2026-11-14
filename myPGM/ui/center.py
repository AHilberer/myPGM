"""Center column of the main window (DESIGN.md §1, "Center"): the fitted pressure card,
the fit toolbar pieces and legend row of the spectrum card, and the items drawn over the
spectrum plot (fitted peak label, fit range edit handles).

The widgets the presenter and tests use (buttons, spin boxes) are created by MainWindow
and keep their attribute names there; these classes only lay them out and draw."""
from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)
import pyqtgraph as pg

from myPGM.ui import icons, theme
from myPGM.ui.widgets import (Card, Collapser, DashedFrame, ElidedLabel, button, divider,
                              hbox, label)

NO_VALUE = "—"


# --- fitted pressure card --------------------------------------------------------------------

class Pill(QLabel):
    """Rounded tag of the pills row. Long text is shortened with '…' to the width the
    row gives it (at most MAX_WIDTH, at least MIN_TEXT), with the full text in the
    tooltip; text() returns the full text. A long file name never widens the window.
    Rich text (the calibration pill: a dot and a short name) is shown whole."""

    MAX_WIDTH = 320
    MIN_TEXT = 40

    def __init__(self, text="", mono=False, muted=False, parent=None):
        super().__init__(parent)
        self.setObjectName("Pill")
        if mono:
            self.setProperty("mono", True)
        if muted:
            self.setProperty("muted", True)
        self._full = ""
        self.setText(text)

    def setText(self, text):
        self._full = text or ""
        self._show_text()
        self.updateGeometry()

    def text(self):
        return self._full

    def _plain(self):
        return self.textFormat() != Qt.RichText

    def _chrome(self):
        """Padding and border around the text."""
        return super().sizeHint().width() - self.fontMetrics().horizontalAdvance(super().text())

    def _text_width(self):
        return min(self.fontMetrics().horizontalAdvance(self._full), self.MAX_WIDTH)

    def _show_text(self):
        if not self._plain():
            super().setText(self._full)
            return
        metrics = self.fontMetrics()
        width = self._text_width()
        if self.isVisible() and self.width() > 0:
            width = min(width, self.width() - self._chrome())
        # elidedText also shortens a text that fits within a pixel or two
        shown = (self._full if metrics.horizontalAdvance(self._full) <= width
                 else metrics.elidedText(self._full, Qt.ElideMiddle, max(width, 0)))
        if shown != super().text():
            super().setText(shown)
        self.setToolTip(self._full if shown != self._full else "")

    def sizeHint(self):
        hint = super().sizeHint()
        if self._plain():
            hint.setWidth(self._chrome() + self._text_width() + 1)
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        if self._plain():
            hint.setWidth(self._chrome() + min(self._text_width(), self.MIN_TEXT))
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_text()

    def showEvent(self, event):
        super().showEvent(event)
        self._show_text()


def dot_html(color, size_px=8):
    return f'<span style="color:{color}; font-size:{size_px}px">●</span>'


class PressureCard(Card):
    """FITTED PRESSURE: the value (40 px mono) and "GPa", a row of pills (calibration,
    fit model, fitted position, file), and on the right the Pm field and the
    "Add fit to log" button. Shows "—" and disables the button while the selected
    spectrum is not fitted."""

    VALUE_HEIGHT = 44

    def __init__(self, pm_spinbox, add_button, file_label):
        super().__init__()
        self.setObjectName("Card")
        self.body.setContentsMargins(20, 10, 20, 10)
        self.add_button = add_button
        self.file_label = file_label
        self._calib = None

        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(label("Fitted pressure", "section"))
        self.value_label = QLabel(NO_VALUE)
        self.value_label.setObjectName("PressureValue")
        # digits only: the empty top of the mono font's line box is cut (VALUE_HEIGHT)
        self.value_label.setFixedHeight(self.VALUE_HEIGHT)
        self.unit_label = QLabel("GPa")
        self.unit_label.setObjectName("PressureUnit")
        value_row = QHBoxLayout()
        value_row.setSpacing(10)
        value_row.addWidget(self.value_label, 0, Qt.AlignBottom)
        value_row.addWidget(self.unit_label, 0, Qt.AlignBottom)
        value_row.addStretch(1)
        left.addLayout(value_row)
        self.calib_pill = Pill()
        self.calib_pill.setTextFormat(Qt.RichText)
        self.model_pill = Pill()
        self.x_pill = Pill(mono=True)
        # the file pill takes the room the others leave (_fit_file_pill): a long file
        # name is shortened first, the model and position stay readable
        self.pills_row = QWidget()
        self.pills_row.setLayout(hbox(self.calib_pill, self.model_pill, self.x_pill,
                                      file_label, 1, spacing=6))
        self.pills_row.installEventFilter(self)
        left.addWidget(self.pills_row)

        # Pm field (the spin box and "bar" in one input frame) and the add button,
        # vertically centred in the card
        right = QGridLayout()
        right.setHorizontalSpacing(8)
        right.setVerticalSpacing(4)
        right.setRowStretch(0, 1)
        right.setRowStretch(3, 1)
        right.addWidget(label("Membrane pressure Pm", "field"), 1, 0)
        self.pm_field = QFrame()
        self.pm_field.setObjectName("PmField")
        self.pm_field.setAttribute(Qt.WA_StyledBackground, True)
        self.pm_field.setFixedHeight(40)
        field_layout = QHBoxLayout(self.pm_field)
        field_layout.setContentsMargins(8, 0, 10, 0)
        field_layout.setSpacing(6)
        pm_spinbox.setFixedWidth(84)
        pm_spinbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        field_layout.addWidget(pm_spinbox)
        field_layout.addWidget(label("bar", "muted"))
        right.addWidget(self.pm_field, 2, 0)
        right.addWidget(add_button, 2, 1)

        row = hbox(left, right, spacing=28)
        row.setStretch(0, 1)
        self.body.addLayout(row)
        self.clear()

    def eventFilter(self, watched, event):
        if watched is self.pills_row and event.type() in (QEvent.Resize, QEvent.LayoutRequest):
            self._fit_file_pill()
        return super().eventFilter(watched, event)

    def _fit_file_pill(self):
        """Box layouts shorten every widget alike when the row is too narrow: the file
        pill is capped to the room left by the other pills instead."""
        spacing = self.pills_row.layout().spacing()
        others = [pill for pill in (self.calib_pill, self.model_pill, self.x_pill)
                  if not pill.isHidden()]
        room = self.pills_row.width() - sum(p.sizeHint().width() + spacing for p in others)
        room = max(room, self.file_label.minimumSizeHint().width())
        if self.file_label.maximumWidth() != room:
            self.file_label.setMaximumWidth(room)

    def clear(self, calib=None):
        """Not fitted: "—", calibration pill only, button disabled."""
        self._calib = calib
        self.value_label.setText(NO_VALUE)
        self.model_pill.hide()
        self.x_pill.hide()
        self._update_calib_pill()
        self.add_button.setEnabled(False)

    @staticmethod
    def value_text(P):
        """3 decimals; a value from a fit gone wrong (|P| >= 10000 GPa) in scientific
        notation, so that it cannot widen the card and the window."""
        return f"{P:.3f}" if abs(P) < 1e4 else f"{P:.3g}"

    def set_fit(self, P, model_name, position_text):
        self.value_label.setText(self.value_text(P))
        self.model_pill.setText(model_name)
        self.model_pill.show()
        self.x_pill.setText(position_text)
        self.x_pill.setVisible(bool(position_text))
        self.add_button.setEnabled(True)

    def _update_calib_pill(self):
        if self._calib is None:
            self.calib_pill.hide()
            return
        self.calib_pill.setText(f"{dot_html(theme.calib_color(self._calib))}&nbsp;"
                                f"{self._calib.short_name}")
        self.calib_pill.show()

    def restyle(self):
        self._update_calib_pill()


# --- fit toolbar -----------------------------------------------------------------------------

class SplitButton(QWidget):
    """Two joined buttons sharing one border (Fit range | pencil)."""

    def __init__(self, left, right, parent=None):
        super().__init__(parent)
        left.setProperty("role", "split-left")
        right.setProperty("role", "split-right")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(left)
        layout.addWidget(right)


class Segmented(QFrame):
    """Exclusive checkable buttons on a sunken track (Background: Auto / Manual / None)."""

    def __init__(self, buttons, parent=None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for segment in buttons:
            segment.setCheckable(True)
            segment.setProperty("role", "segment")
            self.group.addButton(segment)
            layout.addWidget(segment)

    def check(self, segment):
        """Check one button (None: none of them), without clicking it."""
        if segment is None:
            self.group.setExclusive(False)
            for b in self.group.buttons():
                b.setChecked(False)
            self.group.setExclusive(True)
        else:
            segment.setChecked(True)


class Stepper(QFrame):
    """− value + (the smoothing window)."""

    def __init__(self, spinbox, minus, plus, parent=None):
        super().__init__(parent)
        self.setObjectName("Stepper")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        minus.setProperty("role", "step")
        plus.setProperty("role", "step")
        minus.setProperty("side", "left")
        plus.setProperty("side", "right")
        spinbox.setObjectName("StepperValue")
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setFixedWidth(40)
        layout.addWidget(minus)
        layout.addWidget(spinbox)
        layout.addWidget(plus)
        minus.clicked.connect(spinbox.stepDown)
        plus.clicked.connect(spinbox.stepUp)


class FitToolbar(QFrame):
    """Toolbar strip at the top of the spectrum card. It keeps one line without widening
    the window: when it is too narrow its text labels ("Background", "Smoothing") are
    hidden, then the `compact_buttons` show their icon only (widgets.Collapser)."""

    def __init__(self, items, optional_labels, compact_buttons=(), parent=None):
        super().__init__(parent)
        self.setObjectName("CardToolbar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.optional_labels = optional_labels
        layout = hbox(*items, spacing=8, margins=(12, 10, 12, 10))
        self.setLayout(layout)
        self.collapser = Collapser(self, [*optional_labels, *compact_buttons])

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(hint.width() - self.collapser.min_width_saving())
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.collapser.fit(event.size().width())


# --- legend row --------------------------------------------------------------------------------

def _glyph(draw, width, height):
    pixmap = QPixmap(width * 2, height * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(2, 2)
    draw(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return pixmap


class LegendRow(QWidget):
    """Data · Fit · Fit range on the left; a hint (manual background) and the dI/dλ
    toggle on the right."""

    def __init__(self, derivative_button, parent=None):
        super().__init__(parent)
        self.data_glyph, self.fit_glyph, self.range_glyph = QLabel(), QLabel(), QLabel()
        self.range_item = self._item(self.range_glyph, "Fit range")
        # elided: a long hint must not widen the card
        self.hint = ElidedLabel("")
        self.hint.setProperty("role", "accent-12")
        self.hint.hide()
        layout = hbox(self._item(self.data_glyph, "Data"), self._item(self.fit_glyph, "Fit"),
                      self.range_item, 1, self.hint, divider(length=18), derivative_button,
                      spacing=16, margins=(16, 10, 16, 0))
        self.setLayout(layout)
        self.range_item.hide()
        self._fit_color = theme.calib_color(None)
        self.restyle()

    @staticmethod
    def _item(glyph, text):
        item = QWidget()
        item.setLayout(hbox(glyph, label(text, "caption"), spacing=6))
        return item

    def set_fit_color(self, color):
        self._fit_color = color
        self.restyle()

    def show_range(self, shown):
        self.range_item.setVisible(shown)

    def set_hint(self, text):
        self.hint.setText(text)
        self.hint.setVisible(bool(text))

    def restyle(self):
        t = theme.tokens()

        def dot(p):
            p.setPen(Qt.NoPen)
            p.setBrush(theme.qcolor(t["dot"]))
            p.drawEllipse(QRectF(0, 2, 6, 6))

        def line(p):
            p.fillRect(QRectF(0, 4, 16, 2), QColor(self._fit_color))

        def band(p):
            p.fillRect(QRectF(0, 0, 14, 10), theme.qcolor(t["acs"]))
            p.fillRect(QRectF(0, 0, 1, 10), theme.qcolor(t["ac"]))
            p.fillRect(QRectF(13, 0, 1, 10), theme.qcolor(t["ac"]))

        self.data_glyph.setPixmap(_glyph(dot, 6, 10))
        self.fit_glyph.setPixmap(_glyph(line, 16, 10))
        self.range_glyph.setPixmap(_glyph(band, 14, 10))


# --- items drawn over the spectrum plot ---------------------------------------------------------

class PeakLabel(pg.TextItem):
    """Small box next to the fitted peak / edge marker: "R1 · 696.224 nm" over
    "P 5.319 GPa", kept at the top of the plot."""

    def __init__(self):
        super().__init__(anchor=(0, 0))
        self.setZValue(20)
        self._x = None
        self._lines = ("", "")

    def set_content(self, x, title, pressure):
        self._x = x
        self._lines = (title, pressure)
        self.restyle()

    def restyle(self):
        t = theme.tokens()
        title, pressure = self._lines
        self.setHtml(
            f'<div style="font-family:{theme.ui_family()}; font-size:11px; font-weight:{theme.qt5_weight(600)}; '
            f'color:{t["tx"]}">{title}</div>'
            f'<div style="font-family:{theme.mono_family()}; font-size:11px; '
            f'color:{theme.qcolor(t["mu"]).name()}">{pressure}</div>')
        self.fill = pg.mkBrush(theme.qcolor(t["sf"]))
        self.border = pg.mkPen(theme.qcolor(t["bd"]))
        self.update()

    def place(self, view_box):
        if self._x is None:
            return
        (x_min, x_max), (_y_min, y_max) = view_box.viewRange()
        # right of the marker, or left of it near the right edge
        right_side = self._x < x_min + 0.75 * (x_max - x_min)
        self.setAnchor((-0.06, -0.08) if right_side else (1.06, -0.08))
        self.setPos(self._x, y_max)


def _handle_path():
    """12 x 36 px rounded pill (path in a unit box, drawn 36 px high)."""
    path = QPainterPath()
    path.addRoundedRect(QRectF(-6 / 36, -0.5, 12 / 36, 1.0), 4 / 36, 4 / 36)
    return path


def _grip_path():
    path = QPainterPath()
    for x in (-1.5 / 36, 1.5 / 36):
        path.moveTo(QPointF(x, -7 / 36))
        path.lineTo(QPointF(x, 7 / 36))
    return path


class FitRangeEditOverlay:
    """While the fit range is edited: grab handles at mid height on both edges and an
    accent label "Drag the edges · 691.0 – 700.5 nm" at the top of the band."""

    def __init__(self, plot_widget, region):
        self.plot_widget = plot_widget
        self.region = region
        self.unit = ""
        self.handles = pg.ScatterPlotItem(symbol=_handle_path(), size=36, pen=None, pxMode=True)
        self.grips = pg.ScatterPlotItem(symbol=_grip_path(), size=36, brush=None, pxMode=True)
        self.label = pg.TextItem(anchor=(-0.04, -0.12))
        for item in (self.handles, self.grips, self.label):
            item.setZValue(15)
            item.setAcceptedMouseButtons(Qt.NoButton)     # the edges are dragged
        self.shown = False
        region.sigRegionChanged.connect(self.update)
        plot_widget.plotItem.vb.sigRangeChanged.connect(self.update)
        self.restyle()

    def show(self, shown):
        if shown == self.shown:
            return
        self.shown = shown
        for item in (self.handles, self.grips, self.label):
            if shown:
                self.plot_widget.addItem(item, ignoreBounds=True)
            else:
                self.plot_widget.removeItem(item)
        self.update()

    def update(self, *_args):
        if not self.shown:
            return
        low, high = self.region.getRegion()
        _x, (y_min, y_max) = self.plot_widget.plotItem.vb.viewRange()
        mid = (y_min + y_max) / 2
        self.handles.setData([low, high], [mid, mid])
        self.grips.setData([low, high], [mid, mid])
        self.label.setText(f"Drag the edges · {low:.1f} – {high:.1f} {self.unit}".rstrip())
        self.label.setPos(low, y_max)

    def restyle(self):
        t = theme.tokens()
        accent, on_accent = theme.qcolor(t["ac"]), theme.qcolor(t["onac"])
        self.handles.setBrush(pg.mkBrush(accent))
        self.grips.setPen(pg.mkPen(on_accent, width=1.2))
        self.label.fill = pg.mkBrush(accent)
        self.label.setColor(on_accent)
        font = self.label.textItem.font()
        font.setFamily(theme.ui_family())
        font.setPixelSize(11)
        font.setWeight(QFont.DemiBold)
        self.label.setFont(font)
        self.update()


def peak_name(calib, fit_model):
    """Name of the fitted line in the peak label: R1 for ruby, else the x symbol."""
    if fit_model is not None and fit_model.type == "edge":
        return "Edge"
    if calib is not None and getattr(calib, "family", None) == "ruby":
        return "R1"
    return None


def dashed_marker_pen():
    color = theme.qcolor(theme.tokens()["tx"])
    color.setAlphaF(0.5)
    pen = QPen(color)
    pen.setWidthF(1)
    pen.setStyle(Qt.CustomDashLine)
    pen.setDashPattern([3, 3])
    pen.setCosmetic(True)
    return pen


# --- empty state (DESIGN.md §4b) ---------------------------------------------------------------

def _spectrum_glyph(color, size=48):
    """Small spectrum (two peaks) in `color`, in a rounded box."""
    t = theme.tokens()

    def draw(p):
        p.setPen(QPen(theme.qcolor(t["bd"]), 1))
        p.setBrush(theme.qcolor(t["sf"]))
        p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 8, 8)
        path = QPainterPath(QPointF(10, 35))
        path.cubicTo(16, 35, 17, 22, 19, 22)
        path.cubicTo(21, 22, 21, 33, 23, 33)
        path.cubicTo(25, 33, 25, 12, 27.5, 12)
        path.cubicTo(30, 12, 30, 35, 34, 35)
        path.lineTo(38, 35)
        pen = QPen(QColor(color), 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    return _glyph(draw, size, size)


class EmptyCenter(Card):
    """Center column with no spectrum loaded (mockup_startup.png): a dashed drop zone
    with the accepted files and three actions, then a hint about the Parameters card
    and a link to the demo session. Files can be dropped anywhere on the window."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._color = theme.calib_color(None)
        self.body.addStretch(2)

        self.drop_zone = DashedFrame(width=2, radius=12, dash=(6, 4))
        self.drop_zone.setObjectName("DropZone")
        self.drop_zone.setMaximumWidth(560)
        zone = QVBoxLayout(self.drop_zone)
        zone.setContentsMargins(32, 36, 32, 36)
        zone.setSpacing(12)
        self.glyph = QLabel()
        self.glyph.setAlignment(Qt.AlignCenter)
        zone.addWidget(self.glyph)
        title = label("Drop spectrum files here", "empty-title")
        title.setAlignment(Qt.AlignCenter)
        zone.addWidget(title)
        text = label("Text or ASC spectra from ruby, samarium, H₂, diamond or cBN gauges. "
                     "Several files at once are fine.", "muted-13")
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        zone.addWidget(text)
        zone.addSpacing(4)
        self.add_button = button("Add spectra…", 38, primary=True, icon_name="plus",
                                 tooltip="Add spectrum files")
        self.folder_button = button("Select acquisition folder…", 38, icon_name="folder",
                                    tooltip="Folder where Load latest looks for new spectra")
        self.session_button = button("Open session…", 38, icon_name="folder-open",
                                     tooltip="Open a saved session")
        zone.addLayout(hbox(1, self.add_button, self.folder_button, 1))
        zone.addLayout(hbox(1, self.session_button, 1))
        self.body.addLayout(hbox(1, self.drop_zone, 1))

        # hint and demo link
        self.hint_icon = QLabel()
        hint = QLabel("No spectrum? Enter λ in <b>Parameters</b> to convert it to a pressure.")
        hint.setProperty("role", "muted-13")
        self.demo_button = QPushButton(" Explore the demo session")
        self.demo_button.setProperty("role", "link")
        self.demo_button.setCursor(Qt.PointingHandCursor)
        self.demo_button.setToolTip("Load the example spectra, fitted and logged")
        icons.set_icon(self.demo_button, "play", "act", 14)
        self.body.addSpacing(10)
        hint_row = hbox(1, self.hint_icon, hint, spacing=6)
        hint_row.addSpacing(24)
        hint_row.addWidget(self.demo_button)
        hint_row.addStretch(1)
        self.body.addLayout(hint_row)
        self.body.addStretch(3)
        self.restyle()

    def set_color(self, color):
        """Colour of the spectrum glyph (the calibration selected in the inspector)."""
        self._color = color
        self.restyle()

    def restyle(self):
        self.glyph.setPixmap(_spectrum_glyph(self._color))
        self.hint_icon.setPixmap(
            icons.pixmap("chevron-right", theme.qcolor(theme.tokens()["mu"]).name(), 14))
