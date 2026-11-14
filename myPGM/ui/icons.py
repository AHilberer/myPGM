"""Stroke icons (Lucide, ISC licence: resources/icons/ui/LICENSE-lucide.txt) drawn in a
theme colour (DESIGN.md §2, "Icons").

The SVGs use stroke="currentColor": it is replaced by the colour of a theme token
before rendering. Buttons given an icon with set_icon() are redrawn by refresh() when
the theme changes.
"""
import weakref
from functools import lru_cache
from importlib.resources import files

from PyQt5 import sip
from PyQt5.QtCore import QByteArray, QRectF, QSize, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from myPGM.ui import theme

STROKE_WIDTH = "1.8"
_SCALE = 2                       # rendered at 2x, sharp on high-density screens
_buttons = weakref.WeakSet()     # buttons to redraw when the theme changes

# the app icon, shown in the top bar and in Settings › About
_APP_ICON_SIZES = (16, 32, 64, 128, 256, 512, 1024)


@lru_cache(maxsize=None)
def _svg(name):
    text = files("myPGM").joinpath(f"resources/icons/ui/{name}.svg").read_text(encoding="utf-8")
    return text.replace('stroke-width="2"', f'stroke-width="{STROKE_WIDTH}"')


def _render(svg_text, size):
    pixmap = QPixmap(size * _SCALE, size * _SCALE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg_text.encode("utf-8"))).render(
        painter, QRectF(0, 0, size * _SCALE, size * _SCALE))
    painter.end()
    pixmap.setDevicePixelRatio(_SCALE)
    return pixmap


def pixmap(name, color, size=16):
    """The icon `name` drawn in `color` ('#RRGGBB'), size x size logical pixels."""
    return _render(_svg(name).replace("currentColor", color), size)


def icon(name, role="tx", size=16, on_role=None):
    """QIcon in the colour of a theme token (`role`): muted when disabled, accent text
    (or the `on_role` token) when the button is checked."""
    t = theme.tokens()
    result = QIcon()
    result.addPixmap(pixmap(name, theme.qcolor(t[role]).name(), size), QIcon.Normal, QIcon.Off)
    if on_role is None:
        on_role = "act" if role in ("tx", "mu") else role
    result.addPixmap(pixmap(name, theme.qcolor(t[on_role]).name(), size), QIcon.Normal, QIcon.On)
    result.addPixmap(pixmap(name, theme.qcolor(t["mu"]).name(), size), QIcon.Disabled, QIcon.Off)
    return result


def set_icon(button, name, role="tx", size=16, on_role=None):
    """Give a button an icon in a theme colour, redrawn by refresh()."""
    button._theme_icon = (name, role, size, on_role)
    button.setIcon(icon(name, role, size, on_role))
    button.setIconSize(QSize(size, size))
    _buttons.add(button)


def refresh():
    """Redraw the icons of every button set with set_icon() in the current theme."""
    for button in list(_buttons):
        if sip.isdeleted(button):
            continue
        name, role, size, *on_role = button._theme_icon     # docks set (name, role, size)
        button.setIcon(icon(name, role, size, *on_role))


def app_mark(size=26):
    """The app icon (resources/icons/AppIcon*.png) at size x size logical pixels, from
    the smallest file that is sharp at 2x."""
    source = next((n for n in _APP_ICON_SIZES if n >= size * _SCALE), _APP_ICON_SIZES[-1])
    pixmap = QPixmap(str(files("myPGM").joinpath(f"resources/icons/AppIcon{source}.png")))
    if pixmap.isNull():
        return pixmap
    pixmap = pixmap.scaled(size * _SCALE, size * _SCALE, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
    pixmap.setDevicePixelRatio(_SCALE)
    return pixmap
