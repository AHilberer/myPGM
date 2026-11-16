"""Bottom panels of the main window (DESIGN.md §1, "Bottom dock area"): the pressure log
and the P vs Pm plot, each in a QDockWidget drawn as a card.

The header is the dock's title bar widget: uppercase title, panel widgets (point count,
legend), panel actions, then undock and hide buttons. Floating, the dock has no native
frame (Qt drops it when a title bar widget is set): the header becomes a compact title
bar with a grip, the "myPGM" caption and a dock-back button, and is dragged to move it.
Without a native frame, Qt resizes the window only from the 1 px dock frame
(PM_DockWidgetFrameWidth in Fusion), too thin to hit: invisible EdgeGrips along the
edges and in the corners give it a wider resize area.
"""
from PyQt5.QtCore import QEvent, QMargins, QRect, Qt
from PyQt5.QtWidgets import QDockWidget, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from myPGM.ui import icons, theme
from myPGM.ui.widgets import GAP, icon_button, label

HEADER_HEIGHT = 52
MIN_HEIGHT = 160            # docked panels never collapse below this
EDGE = 6                    # width of the resize bands along a floating panel's edges
CORNER = 12                 # size of the resize squares in its corners

GRIP_CURSORS = {
    Qt.LeftEdge: Qt.SizeHorCursor,
    Qt.RightEdge: Qt.SizeHorCursor,
    Qt.TopEdge: Qt.SizeVerCursor,
    Qt.BottomEdge: Qt.SizeVerCursor,
    Qt.TopEdge | Qt.LeftEdge: Qt.SizeFDiagCursor,
    Qt.BottomEdge | Qt.RightEdge: Qt.SizeFDiagCursor,
    Qt.TopEdge | Qt.RightEdge: Qt.SizeBDiagCursor,
    Qt.BottomEdge | Qt.LeftEdge: Qt.SizeBDiagCursor,
}


def _has(edges, edge):
    return bool(int(edges) & int(edge))


def grip_rect(edges, width, height):
    """Where the grip for `edges` (one edge, or two for a corner) sits in a panel of
    this size."""
    x = 0 if _has(edges, Qt.LeftEdge) else width - (CORNER if _has(edges, Qt.TopEdge | Qt.BottomEdge) else EDGE)
    y = 0 if _has(edges, Qt.TopEdge) else height - (CORNER if _has(edges, Qt.LeftEdge | Qt.RightEdge) else EDGE)
    if _has(edges, Qt.LeftEdge | Qt.RightEdge) and _has(edges, Qt.TopEdge | Qt.BottomEdge):
        return QRect(x, y, CORNER, CORNER)
    if _has(edges, Qt.LeftEdge | Qt.RightEdge):
        return QRect(x, CORNER, EDGE, max(0, height - 2 * CORNER))
    return QRect(CORNER, y, max(0, width - 2 * CORNER), EDGE)


def resized_geometry(start, delta, edges, minimum, maximum):
    """`start` (QRect) with the `edges` moved by `delta` (QPoint), its size kept between
    `minimum` and `maximum` (QSize); the opposite edges stay in place."""
    rect = QRect(start)

    def clamp(value, low, high):
        return max(low, min(value, high))

    if _has(edges, Qt.LeftEdge):
        width = clamp(start.width() - delta.x(), minimum.width(), maximum.width())
        rect.setLeft(start.right() + 1 - width)
    elif _has(edges, Qt.RightEdge):
        rect.setWidth(clamp(start.width() + delta.x(), minimum.width(), maximum.width()))
    if _has(edges, Qt.TopEdge):
        height = clamp(start.height() - delta.y(), minimum.height(), maximum.height())
        rect.setTop(start.bottom() + 1 - height)
    elif _has(edges, Qt.BottomEdge):
        rect.setHeight(clamp(start.height() + delta.y(), minimum.height(), maximum.height()))
    return rect


class EdgeGrip(QWidget):
    """Invisible band along an edge (or square in a corner) of a floating panel: shows
    the resize cursor and resizes the panel when dragged. The window manager does the
    resize where Qt can ask it to (startSystemResize: X11, Wayland, Windows); elsewhere
    (macOS with Qt 5) the grip moves the panel's edges itself."""

    def __init__(self, dock, edges):
        super().__init__(dock)
        self.setObjectName("DockEdgeGrip")
        self.dock = dock
        self.edges = edges
        self.setCursor(GRIP_CURSORS[edges])
        self._press = None              # (global position, panel geometry) while dragging
        self.hide()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        event.accept()
        handle = self.dock.windowHandle()
        if handle is not None and handle.startSystemResize(Qt.Edges(self.edges)):
            return
        self._press = (event.globalPos(), self.dock.geometry())

    def mouseMoveEvent(self, event):
        if self._press is None:
            super().mouseMoveEvent(event)
            return
        event.accept()
        position, start = self._press
        minimum = self.dock.minimumSize().expandedTo(self.dock.minimumSizeHint())
        self.dock.setGeometry(resized_geometry(start, event.globalPos() - position,
                                               self.edges, minimum, self.dock.maximumSize()))

    def mouseReleaseEvent(self, event):
        if self._press is None:
            super().mouseReleaseEvent(event)
            return
        event.accept()
        self._press = None


class DockHeader(QWidget):
    """Title bar of a panel. The visible card part is `frame`; the margins around it
    give the 8 px gap to the window edges (set by PanelDock.update_margins)."""

    def __init__(self, title, hide_tooltip, parent=None):
        super().__init__(parent)
        self.title = title
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame()
        self.frame.setObjectName("DockHeader")
        self.frame.setAttribute(Qt.WA_StyledBackground, True)
        self.frame.setFixedHeight(HEADER_HEIGHT)
        outer.addWidget(self.frame)

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(8)
        self.grip = QLabel()
        self.grip.setToolTip("Drag to move")
        self.title_label = label(title, "section")
        self.caption = label("myPGM", "muted-13")
        layout.addWidget(self.grip)
        layout.addWidget(self.title_label)
        layout.addWidget(self.caption)
        layout.addSpacing(4)
        self.extras = QHBoxLayout()          # point count, legend
        self.extras.setSpacing(8)
        layout.addLayout(self.extras)
        layout.addStretch(1)
        self.actions = QHBoxLayout()         # panel buttons
        self.actions.setSpacing(8)
        layout.addLayout(self.actions)
        self.float_button = icon_button("square-arrow-out-up-right", "Undock", size=32)
        self.close_button = icon_button("x", hide_tooltip, size=30, role="mu")
        self.close_button.setProperty("role", "close")
        layout.addWidget(self.float_button)
        layout.addWidget(self.close_button)
        self.set_floating(False)

    def set_floating(self, floating):
        """Docked: uppercase section title. Floating: compact title bar (grip, title,
        "myPGM", dock-back button)."""
        self.grip.setVisible(floating)
        self.caption.setVisible(floating)
        self.title_label.setText(self.title if floating else self.title.upper())
        self.title_label.setProperty("role", "window-title" if floating else "section")
        self.title_label.style().unpolish(self.title_label)
        self.title_label.style().polish(self.title_label)
        self.frame.setProperty("floating", floating)
        self.frame.style().unpolish(self.frame)
        self.frame.style().polish(self.frame)
        self.float_button._theme_icon = (
            ("panel-bottom" if floating else "square-arrow-out-up-right"), "tx", 15)
        self.float_button.setToolTip("Dock back" if floating else "Undock")
        self.float_button.setAccessibleName(self.float_button.toolTip())
        icons.refresh()
        self.restyle()

    def restyle(self):
        self.grip.setPixmap(icons.pixmap("grip-vertical", theme.qcolor(theme.tokens()["mu"]).name(), 15))


class PanelDock(QDockWidget):
    """A bottom panel: `content` in a card body under a DockHeader."""

    def __init__(self, title, object_name, content, hide_tooltip, body_padding=0, parent=None):
        super().__init__(title, parent)
        self.setObjectName(object_name)         # needed by saveState / restoreState
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
                         | QDockWidget.DockWidgetFloatable)
        self.content = content

        self.header = DockHeader(title, hide_tooltip)
        self.setTitleBarWidget(self.header)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        self.body = QFrame()
        self.body.setObjectName("DockBody")
        self.body.setAttribute(Qt.WA_StyledBackground, True)
        body_layout = QVBoxLayout(self.body)
        # bottom padding keeps the content inside the card's rounded corners
        body_layout.setContentsMargins(body_padding, body_padding, body_padding,
                                       max(body_padding, 10))
        body_layout.addWidget(content)
        outer.addWidget(self.body)
        self.setWidget(container)
        self.setMinimumHeight(MIN_HEIGHT)
        self.grips = [EdgeGrip(self, edges) for edges in GRIP_CURSORS]

        self.header.float_button.clicked.connect(lambda: self.setFloating(not self.isFloating()))
        self.header.close_button.clicked.connect(self.close)
        self.topLevelChanged.connect(self._on_floating_changed)
        self.installEventFilter(self)

    def add_header_widgets(self, extras=(), actions=()):
        for widget in extras:
            self.header.extras.addWidget(widget, 0, Qt.AlignVCenter)
        for widget in actions:
            self.header.actions.addWidget(widget, 0, Qt.AlignVCenter)

    def _on_floating_changed(self, floating):
        self.header.set_floating(floating)
        self.body.setProperty("floating", floating)
        self.body.style().unpolish(self.body)
        self.body.style().polish(self.body)
        self.update_margins()
        for grip in self.grips:          # docked, the main window's separators resize it
            grip.setVisible(floating)
            grip.raise_()
        self._place_grips()

    def _place_grips(self):
        for grip in self.grips:
            grip.setGeometry(grip_rect(grip.edges, self.width(), self.height()))

    def eventFilter(self, watched, event):
        if watched is self and event.type() in (QEvent.Resize, QEvent.Move):
            self.update_margins()
            if event.type() == QEvent.Resize:
                self._place_grips()
        return super().eventFilter(watched, event)

    def update_margins(self):
        """GAP from the window edges it touches (the separators give the gaps between
        panels and above them); none when floating, the window is the card."""
        left = right = bottom = 0
        if not self.isFloating() and self.parentWidget() is not None:
            geometry = self.geometry()
            left = GAP if geometry.left() <= 0 else 0
            right = GAP if geometry.right() >= self.parentWidget().width() - 1 else 0
            bottom = GAP
        _set_margins(self.header.layout(), QMargins(left, 0, right, 0))
        _set_margins(self.widget().layout(), QMargins(left, 0, right, bottom))

    def restyle(self):
        self.header.restyle()


def _set_margins(layout, margins):
    if layout.contentsMargins() != margins:      # avoids a relayout on every resize
        layout.setContentsMargins(margins)
