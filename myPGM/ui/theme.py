"""Theme tokens, calibration colours and fonts (docs/DESIGN.md §2, §3, §6).

The application stylesheet is the template theme.qss filled with the tokens of the
light or dark theme. pyqtgraph plots are not reached by the stylesheet: the widgets
that hold plots read the tokens (tokens(), calib_color()) and restyle themselves when
the theme changes (MainWindow.theme_switched).
"""
import logging
import re
import sys
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
    "err": "#C42B3B",           # error icon of the message dialogs (on `bad`)
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
    "err": "#F2697A",
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

# fit model selector: one colour per kind of model, as before the redesign (Double
# models red, Single models green, Raman edge grey), as (solid, text on tint)
MODEL_COLORS = {
    "double": {"light": ("#C42B3B", "#9E1C2B"), "dark": ("#F2697A", "#F7A8B2")},
    "single": {"light": ("#24834E", "#1A6A3E"), "dark": ("#5CC98A", "#9BDDB5")},
    "edge":   {"light": ("#6B7280", "#4B5260"), "dark": ("#98A1B1", "#C4CAD4")},
}

FONT_FILES = [
    "Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf",
    "JetBrainsMono-Regular.ttf", "JetBrainsMono-Medium.ttf", "JetBrainsMono-SemiBold.ttf",
]
UI_FAMILY = "Inter"
MONO_FAMILY = "JetBrains Mono"

_state = {"dark": False, "fonts": None, "system_dark": None}


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


def model_family(model):
    """'double', 'single' or 'edge' (MODEL_COLORS); None for an unknown model."""
    if model is None:
        return None
    if getattr(model, "type", None) == "edge":
        return "edge"
    return "double" if getattr(model, "n_peaks", 0) >= 2 else "single"


def model_color(model, dark=None, on_tint=False):
    """Colour of a fit model's kind, as '#RRGGBB' (the muted text colour if unknown)."""
    theme = "dark" if (is_dark() if dark is None else dark) else "light"
    family = MODEL_COLORS.get(model_family(model))
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

GAP = 4         # px between panels and around the window edge (DESIGN.md §1)


def stylesheet(dark=False):
    """The application stylesheet of the light or dark theme."""
    fonts = load_fonts()
    values = {key: qss(value) for key, value in tokens(dark).items()}
    values["ui_font"] = f'"{fonts["ui"]}"'
    values["mono_font"] = f'"{fonts["mono"]}"'
    values["gap"] = f"{GAP}px"
    values["check_icon"] = f'"{_check_icon(qcolor(tokens(dark)["onac"]).name())}"'
    values["chevron_icon"] = f'"{_chevron_icon(qcolor(tokens(dark)["mu"]).name())}"'
    sheet = Template(load_style("theme.qss")).substitute(values) + _selector_rules(dark)
    return _QSS_WEIGHT.sub(_qt5_weight, sheet)


# Qt 5 reads a numeric QSS font-weight as weight / 8 on its 0-99 scale: 500 gave
# SemiBold and 600 Bold. CSS weights are written in theme.qss (as in DESIGN.md) and
# converted here to the values that give Medium, SemiBold and Bold.
_QT5_WEIGHTS = {400: 50, 500: 57, 600: 63, 700: 75}
_QSS_WEIGHT = re.compile(r"font-weight:\s*(\d+)")


def qt5_weight(css_weight):
    """CSS weight (500, 600...) for a Qt 5 stylesheet or rich text span."""
    return _QT5_WEIGHTS.get(css_weight, css_weight // 8) * 8


def _qt5_weight(match):
    weight = _QT5_WEIGHTS.get(int(match.group(1)))
    return match.group(0) if weight is None else f"font-weight: {weight * 8}"


def _selector_rules(dark):
    """Coloured selectors (DESIGN.md §3): the calibration combo on the solid colour of
    its family (`calib` property, PressureToolbox.set_calib), the fit model combo on a
    tint of its model kind's colour (`model` property, MainWindow)."""
    t = tokens(dark)
    theme = "dark" if dark else "light"
    tint_alpha, border_alpha = (0.16, 0.55) if dark else (0.10, 0.45)
    rules = ["\n/* --- calibration selectors (generated, theme.py) --- */"]
    for family, colors in CALIB_COLORS.items():
        solid, _on_tint = colors[theme]
        rules.append(
            f'QComboBox#calibration_combo[calib="{family}"] {{\n'
            f'  background-color: {solid}; color: {t["on_calib"]}; border-color: {solid};\n'
            f'  font-weight: 600;\n}}\n'
            f'QComboBox#calibration_combo[calib="{family}"]::down-arrow {{\n'
            f'  image: url("{_chevron_icon(t["on_calib"])}");\n}}')
    for family, colors in MODEL_COLORS.items():
        solid, on_tint = colors[theme]
        rules.append(
            f'QComboBox#fit_model_combo[model="{family}"] {{\n'
            f'  background-color: {qss((solid, tint_alpha))}; color: {on_tint};\n'
            f'  border-color: {qss((solid, border_alpha))}; font-weight: 600;\n}}\n'
            f'QComboBox#fit_model_combo[model="{family}"]::down-arrow {{\n'
            f'  image: url("{_chevron_icon(on_tint)}");\n}}')
    return "\n".join(rules) + "\n"


# icons of the stylesheet (Lucide "check" and "chevron-down"): QSS needs image files
_CHECK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
              'fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" '
              'stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>')
_CHEVRON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
                'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" '
                'stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>')


def _icon_file(name, svg, color):
    """Path of an icon drawn in `color`, written once to a temporary folder; '' if it
    cannot be written (the stylesheet then falls back to no image)."""
    path = Path(tempfile.gettempdir()) / "myPGM-icons" / f"{name}-{color.lstrip('#')}.svg"
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg.format(color=color), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write the %s icon: %s", name, exc)
        return ""
    return path.as_posix()


def _check_icon(color):
    return _icon_file("check", _CHECK_SVG, color)


def _chevron_icon(color):
    return _icon_file("chevron", _CHEVRON_SVG, color)


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


def system_prefers_dark():
    """True if the operating system uses a dark appearance (Settings › Theme › System).
    Windows: the "apps use light theme" setting; elsewhere: the platform palette, read
    before myPGM sets its own (Qt 5 follows the macOS appearance)."""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_THEME_KEY) as key:
                return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        except OSError:
            return False
    if _state["system_dark"] is None:
        _remember_system_palette(QApplication.instance())
    return bool(_state["system_dark"])


_WINDOWS_THEME_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def _remember_system_palette(app):
    if _state["system_dark"] is None and app is not None:
        _state["system_dark"] = app.palette().color(QPalette.Window).lightness() < 128


def mode_is_dark(mode):
    """'light', 'dark' or 'system' (the stored theme) -> dark or not."""
    return mode == "dark" or (mode == "system" and system_prefers_dark())


def apply_theme(app=None, dark=False):
    """Apply the light or dark theme to the whole application (fonts loaded on first
    use; the font size rule of the stylesheet is kept)."""
    app = app or QApplication.instance()
    _remember_system_palette(app)           # before it is replaced
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
    # the left axis draws the grid: under the plotted items (the view box is at -100),
    # so that labels drawn over the plot hide it
    widget.getAxis("left").setZValue(-101)
