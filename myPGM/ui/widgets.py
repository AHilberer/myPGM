"""Small building blocks of the main window layout (DESIGN.md §1): cards, section
titles, labels and icon buttons. Their look is in theme.qss (object names and the
`role` property)."""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

from myPGM.ui import icons

PANEL_PADDING = 14      # inside panels
GAP = 8                 # between panels and around the window edge


def label(text="", role=None, parent=None):
    """QLabel with a style role: 'section' (uppercase panel title), 'field' (input
    label), 'caption' (small muted text), 'muted'."""
    widget = QLabel(text, parent)
    if role is not None:
        widget.setProperty("role", role)
    if role == "section":
        widget.setText(text.upper())
        font = widget.font()
        font.setLetterSpacing(QFont.PercentageSpacing, 106)     # 0.06em
        widget.setFont(font)
    return widget


def set_role(widget, role):
    """Change a widget's style role and restyle it."""
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Card(QFrame):
    """Panel: surface colour, 1 px border, 12 px radius. Optional header row with an
    uppercase title and widgets on its right; content goes in self.body."""

    def __init__(self, title=None, spacing=12, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(PANEL_PADDING, PANEL_PADDING, PANEL_PADDING, PANEL_PADDING)
        self.body.setSpacing(spacing)
        self.header = None
        self.title_label = None
        if title is not None:
            self.header = QHBoxLayout()
            self.header.setContentsMargins(0, 0, 0, 0)
            self.header.setSpacing(8)
            self.title_label = label(title, "section")
            self.header.addWidget(self.title_label)
            self.header.addStretch(1)
            self.body.addLayout(self.header)


class ElidedLabel(QLabel):
    """Label that shortens its text with '…' instead of widening the layout; text()
    still returns the whole text. It wants its full width and can shrink to 20 px."""

    def __init__(self, text="", parent=None, mode=Qt.ElideRight):
        super().__init__(text, parent)
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.setMinimumWidth(20)

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(20, hint.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), self._mode, rect.width())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(rect, int(self.alignment()) | Qt.TextSingleLine, text)


class Button(QPushButton):
    """Push button of a fixed height (and width, for icon buttons). The stylesheet's
    min-height replaces a minimum size set in code, so the size comes from sizeHint."""

    def __init__(self, text="", height=None, width=None, parent=None):
        super().__init__(text, parent)
        self._fixed = (width, height)
        if height is not None:
            self.setMaximumHeight(height)
            self.setSizePolicy(self.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        if width is not None:
            self.setMaximumWidth(width)
            self.setSizePolicy(QSizePolicy.Fixed, self.sizePolicy().verticalPolicy())

    def _fix(self, hint):
        width, height = self._fixed
        if width is not None:
            hint.setWidth(width)
        if height is not None:
            hint.setHeight(height)
        return hint

    def sizeHint(self):
        return self._fix(super().sizeHint())

    def minimumSizeHint(self):
        return self._fix(super().minimumSizeHint())


def button(text, height=34, role=None, primary=False, icon_name=None, icon_role=None,
           tooltip=None, parent=None):
    """Text button (optionally with an icon on its left)."""
    widget = Button(text, height=height, parent=parent)
    if role is not None:
        widget.setProperty("role", role)
    if primary:
        widget.setProperty("primary", True)
    if tooltip:
        widget.setToolTip(tooltip)
    if icon_name is not None:
        widget.setText(" " + text)          # gap between the icon and the text
        icons.set_icon(widget, icon_name, icon_role or ("onac" if primary else "tx"), 16)
    return widget


def icon_button(icon_name, tooltip, size=30, role="tx", icon_size=15, parent=None):
    """Square icon-only button (30 or 34 px) with a tooltip."""
    button = Button(height=size, width=size, parent=parent)
    button.setProperty("role", "icon")
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    icons.set_icon(button, icon_name, role, icon_size)
    return button


def divider(vertical=True, length=24):
    """1 px border-coloured line."""
    line = QFrame()
    line.setObjectName("Divider")
    line.setAttribute(Qt.WA_StyledBackground, True)
    if vertical:
        line.setFixedSize(1, length)
    else:
        line.setFixedHeight(1)
    return line


def hbox(*items, spacing=8, margins=(0, 0, 0, 0)):
    """Horizontal layout of widgets; an int adds that much stretch."""
    layout = QHBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    for item in items:
        if isinstance(item, int):
            layout.addStretch(item)
        elif isinstance(item, QWidget):
            layout.addWidget(item)
        else:
            layout.addLayout(item)
    return layout
