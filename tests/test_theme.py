"""Theme tokens, stylesheet template, fonts and calibration colours (DESIGN.md §2, §3, §6)."""
import pytest
from PyQt5.QtGui import QColor, QFontDatabase

from myPGM import calibrations as C, fit_models as F
from myPGM.ui import theme


def _luminance(color):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    c = QColor(color)
    return 0.2126 * channel(c.red()) + 0.7152 * channel(c.green()) + 0.0722 * channel(c.blue())


def _contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_both_themes_have_the_same_tokens():
    assert set(theme.LIGHT) == set(theme.DARK)
    assert {"bg", "sf", "sf2", "hd", "bd", "tx", "mu", "ac", "acs", "act", "onac",
            "sel", "dot", "grid"} <= set(theme.LIGHT)


@pytest.mark.parametrize("dark", [False, True])
def test_stylesheet_is_fully_filled(qapp, dark):
    css = theme.stylesheet(dark)
    assert "$" not in css
    assert theme.qss(theme.tokens(dark)["bg"]) in css
    # QSS reads rgba alphas as 0..255: "0.09" would be transparent
    acs_alpha = theme.tokens(dark)["acs"][1]
    assert theme.qss(theme.tokens(dark)["acs"]).endswith(f", {round(acs_alpha * 255)})")


def test_every_calibration_has_a_family_colour():
    for calib in C.calib_list:
        assert calib.family in theme.CALIB_COLORS, calib.name
    assert theme.calib_color(C.Ruby2020, dark=False) == "#C42B3B"
    assert theme.calib_color(C.H2Vibron, dark=True) == "#E0A458"
    assert theme.calib_color(None, dark=False) == theme.LIGHT["mu"]


def test_selector_text_is_readable_on_every_calibration_colour():
    # DESIGN.md §3: white text on the light solids, #12151B on the dark ones, >= 4.5:1
    for family, colors in theme.CALIB_COLORS.items():
        assert _contrast(theme.LIGHT["on_calib"], colors["light"][0]) >= 4.5, family
        assert _contrast(theme.DARK["on_calib"], colors["dark"][0]) >= 4.5, family


def test_bundled_fonts_are_loaded(qapp):
    fonts = theme.load_fonts()
    assert fonts == {"ui": "Inter", "mono": "JetBrains Mono"}
    families = QFontDatabase().families()
    assert "Inter" in families and "JetBrains Mono" in families
    assert {"Regular", "SemiBold"} <= set(QFontDatabase().styles("Inter"))


def test_theme_switch_restyles_plots_table_and_selector(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.presenter.fit_mode = F.DoubleVoigt
    gui.presenter.fit_current_file()
    gui.view.prompt_fit_pm = lambda current: 8.0
    gui.presenter.add_current_fit_to_table()

    view, plot = gui.view, gui.view.PvPmPlotWindow
    for dark, tokens in ((True, theme.DARK), (False, theme.LIGHT)):
        view.switch_to_dark() if dark else view.switch_to_light()
        ruby = theme.calib_color(C.Ruby2020, dark=dark)
        assert theme.is_dark() == dark
        for widget in (view.data_widget, view.deriv_widget, plot.plot_graph):
            assert widget.backgroundBrush().color().name() == tokens["sf"].lower()
        assert view.data_fit_line.opts["pen"].color().name() == ruby.lower()
        assert plot.lines["Ruby2020"].opts["symbolBrush"].color().name() == ruby.lower()
        table = view.PvPmTableWindow.table_widget
        headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        dot = table.item(0, headers.index("calibration")).icon().pixmap(12, 12).toImage()
        assert dot.pixelColor(6, 6).name() == ruby.lower()
        assert ruby in view.ptoolbox.calibration_combo.styleSheet()
    assert gui.errors == []


def test_numbers_use_the_mono_font(gui):
    gui.presenter.add_current_PToolbox_to_table()
    table = gui.view.PvPmTableWindow.table_widget
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    assert table.item(0, headers.index("Pm (bar)")).font().family() == "JetBrains Mono"
    assert table.item(0, headers.index("calibration")).font().family() != "JetBrains Mono"
    assert gui.view.data_widget.getAxis("left").style["tickFont"].family() == "JetBrains Mono"
    assert 'font-family: "JetBrains Mono"' in gui.app.styleSheet()


def test_theme_switch_keeps_the_toolbox_values(gui):
    # recolouring the calibration list emitted currentTextChanged: taken for a
    # calibration change, it reset T and x to the calibration defaults
    toolbox = gui.view.ptoolbox
    toolbox.set_Tval(350)
    toolbox.set_xval(695.5)
    gui.view.switch_to_dark()
    gui.view.switch_to_light()
    assert toolbox.T_spinbox.value() == 350 and toolbox.x_spinbox.value() == 695.5
