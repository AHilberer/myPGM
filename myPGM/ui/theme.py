"""Theme tokens, calibration colours and fonts (docs/design/DESIGN.md §2, §3, §6).

The application stylesheet is the template theme.qss filled with the tokens of the
light or dark theme. pyqtgraph plots are not reached by the stylesheet: the widgets
that hold plots read the tokens (tokens(), calib_color()) and restyle themselves when
the theme changes (MainWindow.theme_switched).
"""
import logging
import tempfile
from importlib.resources import files
from pathlib import Path
from string import Template

import pyqtgraph as pg
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt5.QtWidgets import QApplication

from myPGM.helpers import load_style, set_app_theme

logger = logging.getLogger(__name__)

# colours with transparency are (hex, alpha 0..1)
LIGHT = {
    "bg": "#E8EBF0",     # window background, between panels
    "sf": "#FFFFFF",     # panels, buttons, plot background
    "sf2": "#EEF1F5",    # inputs, pills, segmented background
    "hd": "#F7F8FA",     # panel header strips, table header
    "bd": "#CDD3DC",     # borders, dividers
    "tx": "#121519",     # text
    "mu": "#545B69",     # secondary text, axis labels
    "ac": "#2450D6",     # accent: primary buttons, focus, fit range edges
    "acs": ("#2450D6", 0.09),   # accent soft
    "act": "#1D3FAE",    # text on acs
    "onac": "#FFFFFF",   # text on ac
    "sel": ("#2450D6", 0.07),   # selected / current table row
    "dot": "#9AA1AD",    # raw data points
    "grid": "#E6E9EE",   # plot grid
    # pressure toolbox field backgrounds (valid / invalid pressure, T != 298 K, Pm)
    "ok": "#E2F3E7",
    "bad": "#FBE1E4",
    "warn": "#FCEAD2",
    "info": "#E6ECFB",
    "on_calib": "#FFFFFF",      # text on a solid calibration colour
}

DARK = {
    "bg": "#0C0F14",
    "sf": "#141820",
    "sf2": "#1B2029",
    "hd": "#171C24",
    "bd": "#272D38",
    "tx": "#E5E8EE",
    "mu": "#98A1B1",
    "ac": "#7B97FF",
    "acs": ("#7B97FF", 0.15),
    "act": "#AFC0FF",
    "onac": "#0C0F14",
    "sel": ("#7B97FF", 0.11),
    "dot": "#5D6676",
    "grid": "#1E232C",
    "ok": "#173222",
    "bad": "#3B1C22",
    "warn": "#3A2A13",
    "info": "#1D2542",
    "on_calib": "#12151B",
}

# one colour per calibration family: (solid, text on a tint of it)
CALIB_COLORS = {
    "ruby":     {"light": ("#C42B3B", "#9E1C2B"), "dark": ("#F2697A", "#F7A8B2")},
    "samarium": {"light": ("#6B3FC4", "#552FA3"), "dark": ("#B79CF5", "#CDBBF8")},
    "h2":       {"light": ("#985A0A", "#7E4A07"), "dark": ("#E0A458", "#EDC28A")},
    "diamond":  {"light": ("#0B6E60", "#085A4E"), "dark": ("#4CC7B4", "#8ADBCE")},
    "cbn":      {"light": ("#2F6FA8", "#245A8A"), "dark": ("#5FA3DE", "#8DBDE6")},
}

FONT_FILES = [
    "Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf",
    "JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf", "JetBrainsMono-SemiBold.ttf",
]
UI_FAMILY = "Inter"
MONO_FAMILY = "JetBrains Mono"

_state = {"dark": False, "fonts": None}


# --- tokens ------------------------------------------------------------------------------

def tokens(dark=None):
    """Token dict of the given theme (the current one by default)."""
    return DARK if (is_dark() if dark is None else dark) else LIGHT


def is_dark():
    return _state["dark"]


def set_current(dark):
    """Record the current theme without restyling (see apply_theme)."""
    _state["dark"] = bool(dark)


def qcolor(value):
    """QColor of a token value: '#RRGGBB' or ('#RRGGBB', alpha 0..1)."""
    if isinstance(value, tuple):
        color = QColor(value[0])
        color.setAlphaF(value[1])
        return color
    return QColor(value)


def qss(value):
    """Token value for a stylesheet. Qt's QSS reads the rgba alpha as 0..255."""
    if isinstance(value, tuple):
        color = qcolor(value)
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
    return value


def calib_family(calib):
    return getattr(calib, "family", None)


def calib_color(calib, dark=None, on_tint=False):
    """Solid colour (or text-on-tint colour) of a calibration's family, as '#RRGGBB'.
    The muted text colour for a calibration without a known family (or None)."""
    theme = "dark" if (is_dark() if dark is None else dark) else "light"
    family = CALIB_COLORS.get(calib_family(calib))
    if family is None:
        return tokens(dark)["mu"]
    return family[theme][1 if on_tint else 0]


# --- fonts -------------------------------------------------------------------------------

def load_fonts():
    """Add the bundled fonts once. Returns {'ui': family, 'mono': family}: the bundled
    families, or the system ones if they could not be loaded."""
    if _state["fonts"] is not None:
        return _state["fonts"]
    loaded = set()
    for name in FONT_FILES:
        try:
            data = files("myPGM").joinpath(f"resources/fonts/{name}").read_bytes()
        except OSError as exc:
            logger.warning("Could not read the font %s: %s", name, exc)
            continue
        font_id = QFontDatabase.addApplicationFontFromData(data)
        if font_id < 0:
            logger.warning("Could not load the font %s", name)
            continue
        loaded.update(QFontDatabase.applicationFontFamilies(font_id))
    system = QApplication.font().family()
    fixed = QFontDatabase.systemFont(QFontDatabase.FixedFont).family()
    _state["fonts"] = {
        "ui": UI_FAMILY if UI_FAMILY in loaded else system,
        "mono": MONO_FAMILY if MONO_FAMILY in loaded else fixed,
    }
    return _state["fonts"]


def ui_family():
    return load_fonts()["ui"]


def mono_family():
    return load_fonts()["mono"]


def mono_font(pixel_size=None):
    font = QFont(mono_family())
    if pixel_size is not None and pixel_size > 0:
        font.setPixelSize(int(pixel_size))
    return font


# --- application --------------------------------------------------------------------------

def stylesheet(dark=False):
    """The application stylesheet of the light or dark theme."""
    fonts = load_fonts()
    values = {key: qss(value) for key, value in tokens(dark).items()}
    values["ui_font"] = f'"{fonts["ui"]}"'
    values["mono_font"] = f'"{fonts["mono"]}"'
    values["check_icon"] = f'"{_check_icon(qcolor(tokens(dark)["onac"]).name())}"'
    return Template(load_style("theme.qss")).substitute(values)


# check mark of the check boxes (Lucide "check"); the stylesheet needs an image file
_CHECK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
              'fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" '
              'stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>')


def _check_icon(color):
    """Path of the check mark drawn in `color`, written once to a temporary folder;
    '' if it cannot be written (checked boxes are then plain accent squares)."""
    path = Path(tempfile.gettempdir()) / "myPGM-icons" / f"check-{color.lstrip('#')}.svg"
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_CHECK_SVG.format(color=color), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write the check box icon: %s", exc)
        return ""
    return path.as_posix()


def palette(dark=False):
    """Palette for what the stylesheet does not reach (Fusion check boxes, message
    box text, tooltips, item views without a rule)."""
    t = tokens(dark)
    pal = QPalette()
    roles = {
        QPalette.Window: t["bg"], QPalette.WindowText: t["tx"],
        QPalette.Base: t["sf"], QPalette.AlternateBase: t["hd"],
        QPalette.Text: t["tx"], QPalette.Button: t["sf"], QPalette.ButtonText: t["tx"],
        QPalette.BrightText: t["onac"], QPalette.Highlight: t["ac"],
        QPalette.HighlightedText: t["onac"], QPalette.ToolTipBase: t["sf"],
        QPalette.ToolTipText: t["tx"], QPalette.Link: t["ac"],
        QPalette.Light: t["sf"], QPalette.Midlight: t["sf2"], QPalette.Mid: t["bd"],
        QPalette.Dark: t["bd"], QPalette.Shadow: t["bd"],
    }
    for role, value in roles.items():
        pal.setColor(role, qcolor(value))
    if hasattr(QPalette, "PlaceholderText"):
        pal.setColor(QPalette.PlaceholderText, qcolor(t["mu"]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, qcolor(t["mu"]))
    return pal


def apply_theme(app=None, dark=False):
    """Apply the light or dark theme to the whole application (fonts loaded on first
    use; the font size rule of the stylesheet is kept)."""
    app = app or QApplication.instance()
    load_fonts()
    set_current(dark)
    app.setPalette(palette(dark))
    set_app_theme(stylesheet(dark))


# --- pyqtgraph ----------------------------------------------------------------------------

def label_styles(color, font_px):
    """pyqtgraph axis label style: UI font, given colour and pixel size."""
    return {"color": color, "font-size": f"{font_px}px", "font-family": ui_family()}


def style_axes(widget, t=None):
    """Plot background in the panel colour, axes and tick labels in the muted colour,
    horizontal grid lines in the grid colour, no frame (DESIGN.md §6)."""
    t = t or tokens()
    widget.setBackground(qcolor(t["sf"]))
    muted = qcolor(t["mu"])
    own_grid_pen = hasattr(widget.getAxis("left"), "setTickPen")
    for side in ("left", "bottom"):
        axis = widget.getAxis(side)
        # no left axis line: the grid lines are enough
        axis.setPen(pg.mkPen(muted if side == "bottom" else qcolor(t["sf"])))
        axis.setTextPen(pg.mkPen(muted))
        if own_grid_pen:
            # grid lines are drawn with the tick pen: in their own colour
            axis.setTickPen(pg.mkPen(qcolor(t["grid"])))
    # without a tick pen (older pyqtgraph) the muted axis pen, faded
    widget.showGrid(x=False, y=True, alpha=1.0 if own_grid_pen else 0.15)
