"""Settings window (DESIGN.md §4, IMPLEMENTATION_PLAN step 6): gear button, sections,
Save / Cancel / Restore defaults, and each setting applied and kept between launches."""
import logging
import os

import pytest

from conftest import dispose
from myPGM import settings as S


def _settings(gui):
    gui.view.open_settings()
    return gui.view.settings_dialog


def _save(gui, **changes):
    """Open Settings, change values (as the controls would), Save."""
    dialog = _settings(gui)
    values = dialog.values()
    for key, value in changes.items():
        if key == "columns":
            values["columns"] = {**values["columns"], **value}
        else:
            values[key] = value
    dialog.set_values(values)
    dialog.save_button.click()
    return dialog


@pytest.fixture
def backup_app(qapp, tmp_path):
    """A window with a backup folder, so the presenter has an autosave timer."""
    from myPGM.ui import theme
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    qapp.setStyleSheet(theme.stylesheet(dark=False))
    view = MainWindow()
    folder = tmp_path / "appdata"
    folder.mkdir()
    presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(folder))
    yield view, presenter
    dispose(view)


# --- window -------------------------------------------------------------------------------

def test_gear_button_and_menu_open_one_window(gui):
    from PyQt5.QtWidgets import QAction
    view = gui.view
    view.top_bar.settings_button.click()
    dialog = view.settings_dialog
    assert dialog.isVisible() and not dialog.isModal()
    assert (dialog.width(), dialog.height()) == (820, 600)
    view.settings_action.trigger()
    assert view.settings_dialog is dialog                       # one instance
    assert view.settings_action.menuRole() == QAction.PreferencesRole   # macOS app menu
    assert not view.settings_action.shortcut().isEmpty()        # Cmd+, / Ctrl+,
    assert view.top_bar.settings_button.toolTip() == "Settings"


def test_old_menus_are_gone(gui):
    menus = [action.text() for action in gui.view.menuBar().actions()]
    assert "Font size" not in menus and "PToolbox" not in menus and "Theme" not in menus
    assert not hasattr(gui.view, "show_font_size_window")


def test_sections(gui):
    from myPGM.ui.settings_dialog import SECTIONS
    dialog = _settings(gui)
    assert SECTIONS == ("General", "Session", "Pressure log", "Logging", "About")
    dialog.nav_buttons["Session"].click()
    assert dialog.current_section() == "Session"
    assert dialog.nav_buttons["Session"].isChecked()
    assert dialog.nav_buttons["Session"].property("current")
    assert not dialog.nav_buttons["General"].property("current")


def test_cancel_discards_and_reopening_shows_the_values_in_use(gui):
    dialog = _settings(gui)
    dialog.theme_buttons["dark"].click()
    dialog.cancel_button.click()
    assert not dialog.isVisible()
    from myPGM.ui import theme
    assert not theme.is_dark()
    gui.view.open_settings()
    assert dialog.values()["theme"] == "light"


def test_restore_defaults_is_applied_only_on_save(gui):
    from myPGM.ui.settings_dialog import SettingsDialog
    dialog = _settings(gui)
    dialog.toolbox_check.setChecked(True)
    dialog.column_checks["T"].setChecked(True)
    dialog.font_spin.setValue(20)
    dialog.restore_button.click()
    values = dialog.values()
    assert values == SettingsDialog.default_values(dialog.columns)
    assert values["font_size"] == 13 and values["autosave_interval_s"] == 30
    assert not values["columns"]["P_err"] and values["columns"]["P"]
    assert gui.view.plot_font_px != 20                  # nothing applied yet


# --- General ------------------------------------------------------------------------------------

def test_theme_light_dark_and_system(gui, monkeypatch):
    from myPGM.ui import theme
    _save(gui, theme="dark")
    assert theme.is_dark() and S.setting("theme") == "dark"
    monkeypatch.setattr(theme, "system_prefers_dark", lambda: False)
    _save(gui, theme="system")
    assert not theme.is_dark() and S.setting("theme") == "system"
    monkeypatch.setattr(theme, "system_prefers_dark", lambda: True)
    from myPGM.ui.main_ui import MainWindow
    view = MainWindow()                                 # next launch follows the system
    assert theme.is_dark()
    dispose(view)


def test_top_bar_toggle_and_settings_share_the_theme(gui):
    dialog = _settings(gui)
    gui.view.top_bar.theme_button.click()
    assert dialog.values()["theme"] == "dark" and S.setting("theme") == "dark"
    gui.view.top_bar.theme_button.click()
    assert dialog.values()["theme"] == "light"


def test_font_size_stepper(gui):
    dialog = _settings(gui)
    dialog.font_spin.setValue(13)
    dialog.font_plus.click()
    assert dialog.font_spin.value() == 14
    dialog.font_minus.click()
    dialog.font_minus.click()
    assert dialog.font_spin.value() == 12
    dialog.font_spin.setValue(8)
    dialog.font_minus.click()
    assert dialog.font_spin.value() == 8                # minimum


def test_additional_toolbox(gui):
    view = gui.view
    view.show()
    _save(gui, additional_toolbox=True)
    assert view.additional_toolbox_window.isVisible() and S.setting("additional_toolbox")
    assert _settings(gui).toolbox_check.isChecked()
    view.settings_dialog.cancel_button.click()
    view.additional_toolbox_window.close()             # closed with its own ×
    view.close_guard = None
    view.close()
    assert not S.setting("additional_toolbox")         # not reopened at the next launch


# --- Session ------------------------------------------------------------------------------------

def test_autosave_interval_and_switch(backup_app):
    view, presenter = backup_app
    timer = presenter.autosave_timer
    assert timer.isActive() and timer.interval() == 30_000          # default
    view.open_settings()
    dialog = view.settings_dialog
    dialog.interval_unit.setCurrentIndex(1)                         # minutes
    dialog.interval_spin.setValue(2)
    dialog.save_button.click()
    assert timer.isActive() and timer.interval() == 120_000
    assert S.setting("session/autosave_interval_s") == 120
    view.open_settings()
    assert dialog.interval_unit.currentText() == "minutes" and dialog.interval_spin.value() == 2
    dialog.autosave_check.setChecked(False)
    assert not dialog.interval_spin.isEnabled()                     # disabled when off
    dialog.save_button.click()
    assert not timer.isActive() and not S.setting("session/autosave")


def test_autosave_interval_from_a_previous_launch(qapp, tmp_path):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    S.set_setting("session/autosave_interval_s", 45)
    view = MainWindow()
    try:
        presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(tmp_path))
        assert presenter.autosave_timer.interval() == 45_000
    finally:
        dispose(view)


def test_interval_units(gui):
    dialog = _settings(gui)
    dialog.set_interval_seconds(30)
    assert dialog.interval_unit.currentText() == "seconds"
    dialog.interval_unit.setCurrentIndex(1)
    assert dialog.interval_spin.value() == 1 and dialog.interval_seconds() == 60
    dialog.interval_unit.setCurrentIndex(0)
    assert dialog.interval_spin.value() == 60
    dialog.interval_spin.setValue(1)
    assert dialog.interval_spin.value() == S.AUTOSAVE_MIN_S         # 5 s minimum


def test_stored_values_are_checked():
    S.set_setting("theme", "purple")
    S.set_setting("session/autosave_interval_s", 1)
    S.set_setting("font_size", 99)
    assert S.setting("theme") == "light"
    assert S.setting("session/autosave_interval_s") == S.AUTOSAVE_MIN_S
    assert S.setting("font_size") == S.DEFAULTS["font_size"]


# --- Pressure log ---------------------------------------------------------------------------------

def test_columns_follow_the_header_menu_and_are_kept(gui):
    table = gui.view.PvPmTableWindow.table_widget
    dialog = _settings(gui)
    assert list(dialog.column_checks) == ["Pm", "P", "P_err", "x", "x_err", "T", "x0", "T0",
                                          "calib", "file"]
    assert not dialog.column_checks["P_err"].isChecked() and dialog.column_checks["P"].isChecked()
    dialog.cancel_button.click()
    menu = {a.text(): a for a in table.column_menu().actions()}
    menu["σx (fit)"].setChecked(True)                   # header menu
    assert _settings(gui).column_checks["x_err"].isChecked()
    gui.view.settings_dialog.cancel_button.click()
    _save(gui, columns={"P_err": True, "file": False})
    assert table.is_column_shown("P_err") and not table.is_column_shown("file")
    # columns left as they were keep their automatic behaviour
    assert "T" not in table.user_column_visibility

    from myPGM.ui.main_ui import MainWindow
    view = MainWindow()                                 # next launch
    try:
        other = view.PvPmTableWindow.table_widget
        assert other.is_column_shown("P_err") and other.is_column_shown("x_err")
        assert not other.is_column_shown("file")
    finally:
        dispose(view)


# --- Logging and About ----------------------------------------------------------------------------

def test_debug_logging(gui):
    logger = logging.getLogger("myPGM")
    level = logger.level
    try:
        _save(gui, debug=True)
        assert logger.isEnabledFor(logging.DEBUG) and S.setting("logging/debug")
        assert _settings(gui).debug_check.isChecked()
        gui.view.settings_dialog.cancel_button.click()
        _save(gui, debug=False)
        assert not logger.isEnabledFor(logging.DEBUG)
    finally:
        logger.setLevel(level)


def test_open_log_folder(gui, monkeypatch, tmp_path):
    from PyQt5.QtGui import QDesktopServices
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    dialog = _settings(gui)
    dialog.log_dir = tmp_path
    dialog.log_folder_button.click()
    # Qt gives '/' separators on Windows
    assert [os.path.normpath(u.toLocalFile()) for u in opened] == [str(tmp_path)]


def test_about(gui, monkeypatch):
    from PyQt5.QtGui import QDesktopServices
    from myPGM.ui.settings_dialog import ISSUES_URL, SOURCE_URL
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    dialog = _settings(gui)
    assert f"v{gui.presenter.app_version}" in dialog.about_name.text()
    dialog.source_button.click()
    dialog.issue_button.click()
    assert opened == [SOURCE_URL, ISSUES_URL]
