"""The window keeps its size whatever it shows: long file and session names, fits,
calibrations, hints and legends must not raise its minimum width, which Qt would
apply by widening the window (on macOS, off the right edge of the screen)."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication

from myPGM import fit_models as F

LONG = "A_very_long_spectrum_file_name_2026-11-14_run03_point17_ruby_after_heating.asc"


def _settle(app):
    """Size changes climb the widget tree one event loop pass per level."""
    for _ in range(6):
        app.processEvents()


def _fit(gui, name, model=F.DoubleVoigt):
    fid = gui.file_id(name)
    gui.presenter.select_file_in_list(fid)
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.fit_mode = model
    gui.presenter.fit_current_file()
    return fid


def test_content_does_not_widen_the_window(gui):
    view, app = gui.view, gui.app
    view.show()
    _fit(gui, "Example_Ruby_1.asc")
    _settle(app)
    baseline = view.minimumSizeHint().width()
    view.resize(baseline + 40, 800)
    _settle(app)
    width = view.width()

    fid = gui.file_id("Example_Ruby_2.asc")
    gui.presenter.model[fid].filename = LONG                 # long file name, fitted
    gui.presenter.populate_file_list()
    _fit(gui, LONG)
    view.add_fitted_button.click()
    _fit(gui, "Example_H2.txt", F.SingleVoigt)               # a second legend entry
    view.add_fitted_button.click()
    view.pressure_card.set_fit(1.5e10, "Double Voigt", "λ 694.908 nm")   # fit gone wrong
    view.set_session_name(LONG.replace(".asc", ".json"))
    view.Spectro_filename_label.setText(LONG)
    view.legend_row.set_hint("Click background points, then Manual again to subtract " * 3)
    for name in view.ptoolbox.calibrations:
        view.ptoolbox.calibration_combo.setCurrentText(name)
    view.show_recovery_banner(0)
    _settle(app)

    assert view.minimumSizeHint().width() <= baseline + 16
    # not widened (the test screen is small: the window may have been fitted to it)
    assert view.width() <= width


def test_window_fits_a_1280_px_screen_with_a_fitted_spectrum(gui):
    gui.view.show()
    fid = gui.file_id("Example_Ruby_1.asc")
    gui.presenter.model[fid].filename = LONG
    gui.presenter.populate_file_list()
    _fit(gui, LONG)
    _settle(gui.app)
    assert gui.view.minimumSizeHint().width() <= 1280


def test_fit_toolbar_collapses_to_icons_and_back(gui):
    view, app = gui.view, gui.app
    view.show()
    view.resize(1900, 800)
    _fit(gui, "Example_Ruby_1.asc")
    toolbar, splitter = view.fit_toolbar, view.workspace_splitter
    # the center column at its minimum width (wide side panels): whatever sets the
    # window's minimum width on this platform, the toolbar is then the tightest part
    splitter.setSizes([900, 1, 900])
    _settle(app)
    assert view.click_fit_button.text() == "" and view.click_fit_button.toolTip()
    assert view.background_label.isHidden() and view.smoothing_label.isHidden()
    assert toolbar.width() >= toolbar.minimumSizeHint().width()
    splitter.setSizes([200, 1400, 270])
    _settle(app)
    assert view.click_fit_button.text().strip() == "Click-to-fit"
    assert view.fit_range_enable_button.text().strip() == "Fit range"
    assert not view.background_label.isHidden()


def test_top_bar_collapses_in_order(gui):
    gui.view.show()
    _settle(gui.app)
    bar = gui.view.top_bar
    full = bar.collapser.full_width()
    bar.collapser.fit(full)
    assert bar.collapser.collapsed() == []
    bar.collapser.fit(full - 1)                       # the app name goes first
    assert bar.collapser.collapsed() == [bar.names]
    bar.collapser.fit(0)                              # then "Session" and the button texts
    assert bar.export_button.text() == "" and bar.export_button.toolTip()
    assert bar.minimumSizeHint().width() <= full - bar.names.sizeHint().width()
    bar.collapser.fit(full)
    assert bar.export_button.text().strip() == "Export CSV" and not bar.names.isHidden()


def test_long_file_name_is_shortened_first(gui):
    view, app = gui.view, gui.app
    view.show()
    view.resize(1440, 860)
    fid = gui.file_id("Example_Ruby_1.asc")
    gui.presenter.model[fid].filename = LONG
    gui.presenter.populate_file_list()
    _fit(gui, LONG)
    _settle(app)
    card = view.pressure_card
    shown = view.current_file_label
    assert shown.text() == LONG and shown.toolTip() == LONG
    assert "…" in super(type(shown), shown).text()
    # the model and the fitted position stay whole
    for pill in (card.model_pill, card.x_pill):
        assert super(type(pill), pill).text() == pill.text() and pill.toolTip() == ""


def test_pressure_value_is_bounded():
    from myPGM.ui.center import PressureCard
    assert PressureCard.value_text(5.319) == "5.319"
    assert PressureCard.value_text(-12.5) == "-12.500"
    assert PressureCard.value_text(1.5e10) == "1.5e+10"


def test_window_widened_by_its_content_is_moved_back_on_screen(gui):
    view, app = gui.view, gui.app
    view.show()
    _settle(app)
    area = QGuiApplication.primaryScreen().availableGeometry()
    view.move(area.left() + 300, area.top())
    _settle(app)
    # content that needs more room: Qt widens the window to its new minimum
    view.pressure_card.setMinimumWidth(view.pressure_card.width() + 200)
    _settle(app)
    frame = view.frameGeometry()
    if frame.width() <= area.width():
        assert frame.right() <= area.right()
    else:
        assert frame.left() == area.left()


def test_resizing_by_the_user_does_not_move_the_window(gui):
    view, app = gui.view, gui.app
    view.show()
    _settle(app)
    view.move(300, 40)
    _settle(app)
    x = view.x()
    view.resize(view.width() + 37, view.height())          # not to the minimum width
    _settle(app)
    assert view.x() == x
    assert not view.isMaximized() and view.windowState() == Qt.WindowNoState
