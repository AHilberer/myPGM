"""Main window layout (DESIGN.md §1): top bar, spectra
sidebar | center | inspector, and the pressure toolbox as inspector cards."""
import time

import pytest
from PyQt5.QtWidgets import QAbstractSpinBox, QCheckBox, QFileDialog

from myPGM.ui import icons, theme
from myPGM.ui.PressureToolbox import PressureToolbox
from myPGM.ui.TopBar import TopBar


def test_workspace_columns(gui):
    view = gui.view
    splitter = view.workspace_splitter
    assert splitter.count() == 3
    sidebar, center, inspector = (splitter.widget(i) for i in range(3))
    assert sidebar is view.file_list_widget
    assert center.isAncestorOf(view.data_widget) and center.isAncestorOf(view.fit_button)
    # the pressure toolbox is in the inspector, its Pm field in the center
    assert inspector.widget().isAncestorOf(view.ptoolbox)
    assert center.isAncestorOf(view.ptoolbox.Pm_spinbox)
    assert center.isAncestorOf(view.add_fitted_button)
    for widget in (view.fit_model_combo, view.PToolbox_toTable_button,
                   view.LoadSpectro_button, view.Spectro_use_button,
                   view.Spectro_filename_label):
        assert inspector.widget().isAncestorOf(widget)
    assert isinstance(view.Spectro_use_button, QCheckBox)
    assert splitter.handleWidth() == theme.GAP


def test_window_fits_a_1280_px_screen(gui):
    assert gui.view.minimumSizeHint().width() <= 1280


def test_inspector_cards(gui):
    toolbox = gui.view.ptoolbox
    assert toolbox.gauge_card.title_label.text() == "PRESSURE GAUGE"
    assert toolbox.params_card.title_label.text() == "PARAMETERS"
    assert toolbox.gauge_card.isAncestorOf(toolbox.calibration_combo)
    assert toolbox.gauge_card.isAncestorOf(gui.view.fit_model_combo)
    for spinbox in (toolbox.x_spinbox, toolbox.x0_spinbox, toolbox.T_spinbox,
                    toolbox.T0_spinbox, toolbox.P_spinbox):
        assert toolbox.params_card.isAncestorOf(spinbox)
        assert spinbox.buttonSymbols() == QAbstractSpinBox.NoButtons
    assert not toolbox.isAncestorOf(toolbox.Pm_spinbox)
    assert toolbox.Tcor_Label.text() == "T correction · Datchi 2007"
    assert toolbox.x_label.text() == "λ (nm)" and toolbox.x0_label.text() == "λ₀ (nm)"


def test_x_labels_follow_the_calibration(gui):
    toolbox = gui.view.ptoolbox
    toolbox.calibration_combo.setCurrentText("H2 Vibron <30GPa")
    assert toolbox.x_label.text().startswith("ν (")


def test_valid_pressure_has_no_background(gui):
    toolbox = gui.view.ptoolbox
    assert toolbox.P_spinbox.styleSheet() == "" and toolbox.x_spinbox.styleSheet() == ""
    toolbox.set_valid_colors(False)
    assert PressureToolbox.LIGHTMODERED in toolbox.P_spinbox.styleSheet()
    gui.view.switch_to_dark()
    assert PressureToolbox.DARKMODERED in toolbox.P_spinbox.styleSheet()
    toolbox.set_valid_colors(True)
    gui.view.switch_to_light()
    assert toolbox.P_spinbox.styleSheet() == ""


def test_additional_toolbox_keeps_its_pm_field(gui):
    window = gui.view.additional_toolbox_window
    assert window.isAncestorOf(window.Pm_spinbox)
    assert window.isAncestorOf(window.gauge_card) and window.isAncestorOf(window.params_card)


def test_theme_menu_is_replaced_by_the_top_bar_toggle(gui):
    menus = [action.text() for action in gui.view.menuBar().actions()]
    assert "Theme" not in menus
    bar = gui.view.top_bar
    assert bar.theme_button._theme_icon[0] == "moon"
    bar.theme_button.click()
    assert theme.is_dark() and bar.theme_button._theme_icon[0] == "sun"
    assert bar.theme_button.toolTip() == "Light theme"
    bar.theme_button.click()
    assert not theme.is_dark() and bar.theme_button._theme_icon[0] == "moon"


def test_panel_toggles_follow_the_docks(gui):
    view, bar = gui.view, gui.view.top_bar
    assert bar.log_toggle.isChecked() and bar.plot_toggle.isChecked()
    view.show()             # the docks' View menu actions follow them once shown
    gui.app.processEvents()
    bar.log_toggle.click()
    assert view.log_dock.isHidden() and not view.plot_dock.isHidden()
    bar.log_toggle.click()
    assert not view.log_dock.isHidden()
    view.plot_dock.header.close_button.click()          # × in its header
    assert view.plot_dock.isHidden() and not bar.plot_toggle.isChecked()
    view.plot_dock.toggleViewAction().trigger()          # View menu
    assert not view.plot_dock.isHidden() and bar.plot_toggle.isChecked()


def test_top_bar_open_save_export(gui, tmp_path, monkeypatch):
    view, bar = gui.view, gui.view.top_bar
    session = tmp_path / "run 12.json"
    monkeypatch.setattr(view, "get_save_session_filename_dialog", lambda: str(session))
    monkeypatch.setattr(view, "get_open_session_filename_dialog", lambda: str(session))
    assert bar.save_status_text() == "Not saved yet"
    assert bar.session_label.text() == "Untitled session"

    bar.save_button.click()
    assert session.exists()
    assert bar.session_label.text() == "run 12"
    assert bar.save_status_text() == "Saved just now"

    bar.open_button.click()
    assert gui.errors == [] and bar.session_label.text() == "run 12"

    csv_file = tmp_path / "log.csv"
    monkeypatch.setattr(view.PvPmTableWindow, "get_save_filename_dialog", lambda: str(csv_file))
    bar.export_button.click()
    assert csv_file.exists()


def test_top_bar_shows_the_version(gui):
    assert gui.view.top_bar.app_subtitle.text() == (
        f"Pressure Gauge Monitor · v{gui.presenter.app_version}")


@pytest.mark.parametrize("seconds, text", [
    (0, "Autosaved just now"), (30, "Autosaved 30 s ago"), (180, "Autosaved 3 min ago")])
def test_save_status_text(qapp, seconds, text):
    bar = TopBar()
    bar.set_save_status("autosaved", time.time() - seconds)
    assert bar.save_status_text() == text
    assert text in bar.save_pill.text()
    bar.deleteLater()


def test_acquisition_folder_shows_its_name(gui, tmp_path, monkeypatch):
    folder = tmp_path / "acq" / "run_42"
    folder.mkdir(parents=True)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(folder))
    gui.view.select_directory_from_dialog()
    label = gui.view.file_list_widget.dir_label
    assert label.text() == "run_42" and label.toolTip() == str(folder)


def test_icons_exist_and_follow_the_theme(qapp):
    names = ["table", "chart-scatter", "folder-open", "save", "download", "moon", "sun",
             "plus", "folder", "refresh-cw", "chevron-up", "chevron-down", "trash-2"]
    for name in names:
        assert not icons.pixmap(name, "#000000").isNull()
    light = icons.pixmap("plus", theme.LIGHT["tx"]).toImage()
    dark = icons.pixmap("plus", theme.DARK["tx"]).toImage()
    assert light != dark


def test_icon_buttons_keep_their_size(gui):
    """The stylesheet's min-height must not shrink the fixed-size buttons."""
    sidebar = gui.view.file_list_widget
    for widget in (sidebar.moveup_button, sidebar.delete_button, gui.view.top_bar.log_toggle):
        hint = widget.sizeHint()
        assert hint.width() == hint.height() == widget.maximumWidth()
    assert gui.view.add_fitted_button.sizeHint().height() == 40     # step 4: Pm field height
