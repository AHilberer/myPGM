import json
import os
import shutil
import time

import pytest
from PyQt5.QtCore import QPointF

from myPGM import calibrations as C, fit_models as F


class OutsideClick:
    def scenePos(self):
        return QPointF(-5000, -5000)


def select_and_fit(gui, name, model=F.DoubleVoigt):
    fid = gui.file_id(name)
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.fit_mode = model
    gui.presenter.fit_current_file()
    return gui.presenter.model[fid]


# --- startup ----------------------------------------------------------------------

def test_demo_mode_loads_examples(gui):
    assert gui.view.file_list_widget.list_widget.count() == 5


def test_normal_start_loads_nothing(qapp):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    view = MainWindow()
    Presenter(PressureGaugeDataManager(), view)
    assert view.file_list_widget.list_widget.count() == 0
    view.close()


# --- fitting ------------------------------------------------------------------------

def test_fit_updates_toolbox(gui):
    obj = select_and_fit(gui, "Example_Ruby_1.asc")
    assert obj.P == pytest.approx(1.699, abs=0.01)
    assert gui.view.ptoolbox.P_spinbox.value() == pytest.approx(obj.P, abs=1e-3)
    assert gui.errors == []


def test_fit_keeps_user_x0(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.presenter.buffer.x0 = 694.00          # differs from the calibration default
    gui.presenter.fit_current_file()
    obj = gui.presenter.model[gui.file_id("Example_Ruby_1.asc")]
    assert obj.x0 == 694.00


def test_double_model_on_h2_does_not_crash(gui):
    select_and_fit(gui, "Example_H2.txt", F.DoubleVoigt)
    assert gui.errors in ([], ["Fit error"])


@pytest.mark.filterwarnings("ignore:divide by zero:RuntimeWarning")
def test_invalid_calibration_parameters_show_fit_error(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.presenter.buffer.x0 = 0               # division by zero in the ruby formula
    gui.presenter.fit_current_file()
    assert gui.errors == ["Fit error"]


def test_add_fit_to_table(gui):
    select_and_fit(gui, "Example_Ruby_1.asc")
    gui.view.prompt_fit_pm = lambda current: 12.0
    gui.presenter.add_current_fit_to_table()
    table = gui.view.PvPmTableWindow.table_widget
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "12.00"


# --- files --------------------------------------------------------------------------

def test_unreadable_file_shows_error_and_adds_nothing(gui, tmp_path):
    bad = tmp_path / "bad.asc"
    bad.write_text("hello\nworld\n")
    n_before = len(gui.presenter.model)
    gui.presenter._add_files([str(bad)])
    assert gui.errors == ["File load error"]
    assert len(gui.presenter.model) == n_before


def test_load_latest_picks_newest_spectrum(gui, resources, tmp_path):
    for name, src in [("old.asc", "Example_Ruby_1.asc"),
                      ("newest.txt", "Example_H2.txt"),
                      ("junk.asc.bak", "Example_Ruby_2.asc")]:
        shutil.copy(resources / src, tmp_path / name)
        time.sleep(0.02)   # distinct modification times
    os.utime(tmp_path / "junk.asc.bak")        # newest of all, but not a spectrum
    gui.presenter.current_directory = str(tmp_path)
    gui.presenter.add_latest_file()
    names = [o.filename for o in gui.presenter.model.values()]
    assert "newest.txt" in names and "junk.asc.bak" not in names


def test_selecting_unknown_file_is_ignored(gui):
    gui.presenter.file_selected_from_file_list(-1)
    assert gui.presenter.current_selected_file is None


def test_smoothing_box_follows_selected_file(gui):
    p = gui.presenter
    p.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.view.smoothing_factor.setValue(9)          # applies smoothing to Ruby_1
    assert p.model[gui.file_id("Example_Ruby_1.asc")].current_smoothing == 9

    p.file_selected_from_file_list(gui.file_id("Example_Ruby_2.asc"))
    assert gui.view.smoothing_factor.value() == 1
    assert p.model[gui.file_id("Example_Ruby_2.asc")].current_smoothing == 1   # not re-applied

    p.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    assert gui.view.smoothing_factor.value() == 9


def test_smoothing_keeps_spectrometer_recalibration_in_app(gui, resources, monkeypatch):
    p = gui.presenter
    p.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    calib_file = str(resources / "alternate_spectro_calib.asc")
    monkeypatch.setattr(gui.view, "get_file_via_dialog", lambda: [calib_file])
    p.load_spectro_calibration()
    gui.view.Spectro_use_button.setChecked(True)
    x_recalibrated = p.model[gui.file_id("Example_Ruby_1.asc")].get_data_to_process()[0].copy()

    gui.view.smoothing_factor.setValue(5)
    x_after = p.model[gui.file_id("Example_Ruby_1.asc")].get_data_to_process()[0]
    assert x_recalibrated[0] != p.model[gui.file_id("Example_Ruby_1.asc")].normalized_data[0, 0]
    assert (x_after == x_recalibrated).all()
    assert gui.errors == []


# --- clicks and manual background ------------------------------------------------------

def test_clicks_outside_plot_are_ignored(gui):
    gui.view.click_fit_enabled = True
    gui.view.click_to_fit(OutsideClick(), "data")
    gui.view.click_ManualBg_enabled = True
    gui.view.set_ManualBg(OutsideClick())
    assert gui.view.ManualBg_points == []


def test_manual_background_with_duplicate_points(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.view.ManualBg_points = [[690.0, 0.1], [690.0, 0.2], [698.0, 0.1]]
    bg = gui.view.plot_ManualBg()
    assert bg is not None


# --- sessions ---------------------------------------------------------------------------

def test_session_save_and_load(gui, tmp_path, monkeypatch):
    obj = select_and_fit(gui, "Example_Ruby_2.asc")
    P_fitted = obj.P
    session = tmp_path / "session.json"
    monkeypatch.setattr(gui.view, "get_save_session_filename_dialog", lambda: str(session))
    monkeypatch.setattr(gui.view, "get_open_session_filename_dialog", lambda: str(session))
    gui.presenter.save_session()

    gui.presenter.load_session()
    assert gui.errors == []
    assert len(gui.presenter.model) == 5
    restored = gui.presenter.model[gui.file_id("Example_Ruby_2.asc")]
    assert restored.P == pytest.approx(P_fitted)
    assert gui.presenter.current_selected_file == restored.id


def test_corrupted_session_keeps_current_session(gui, tmp_path, monkeypatch):
    session = tmp_path / "broken.json"
    session.write_text(json.dumps({"files": [{"id": 1, "fit_result": "oops"}]}))
    monkeypatch.setattr(gui.view, "get_open_session_filename_dialog", lambda: str(session))
    n_before = len(gui.presenter.model)
    gui.presenter.load_session()
    assert gui.errors == ["Load error"]
    assert len(gui.presenter.model) == n_before


# --- theme and font size -------------------------------------------------------------------

def test_light_mode_does_not_colour_T_at_room_temperature(gui):
    toolbox = gui.view.ptoolbox
    toolbox.set_Tval(298)
    gui.view.switch_to_dark()
    gui.view.switch_to_light()
    assert toolbox.T_spinbox.styleSheet() == ""
    toolbox.set_Tval(350)
    gui.view.switch_to_dark()
    gui.view.switch_to_light()
    assert toolbox.T_spinbox.styleSheet() == f"background: {toolbox.LIGHTMODEORANGE};"


def test_consistent_font_size_at_startup(gui):
    from PyQt5.QtGui import QFontInfo
    app_px = QFontInfo(gui.view.fit_button.font()).pixelSize()
    axis = gui.view.data_widget.getAxis("bottom")
    assert axis.labelStyle["font-size"] == f"{app_px}px"
    assert axis.style["tickFont"].pixelSize() == app_px
    pvpm_axis = gui.view.PvPmPlotWindow.plot_graph.getAxis("left")
    assert pvpm_axis.labelStyle["font-size"] == f"{app_px}px"
    assert f"font-size: {app_px}px" in gui.view.PvPmTableWindow.table_widget.styleSheet()


def test_font_window_starts_from_current_size_without_changes(gui):
    css_before = gui.app.styleSheet()
    gui.view.show_font_size_window()
    assert gui.view.font_size_window.slider.value() == gui.view.plot_font_px
    assert gui.app.styleSheet() == css_before


def test_font_size_applies_everywhere_and_survives_theme_change(gui):
    gui.view.show_font_size_window()
    window = gui.view.font_size_window
    window.slider.setValue(24)
    gui.view.switch_to_dark()

    assert "font-size: 24px" in gui.app.styleSheet()
    assert "FontSizeWindow" in gui.app.styleSheet()          # dark theme rule for the window
    assert gui.view.data_widget.getAxis("bottom").labelStyle["font-size"] == "24px"
    assert gui.view.data_widget.getAxis("left").style["tickFont"].pixelSize() == 24
    assert gui.view.PvPmPlotWindow.plot_graph.getAxis("left").labelStyle["font-size"] == "24px"
    assert "font-size: 24px" in gui.view.PvPmTableWindow.table_widget.styleSheet()

    window.close()
    gui.view.show_font_size_window()
    assert gui.view.font_size_window is window and window.slider.value() == 24


# --- fit uncertainty display ------------------------------------------------------------

def _title(gui):
    return gui.view.data_widget.plotItem.titleLabel.text


def test_title_shows_fit_uncertainty(gui):
    obj = select_and_fit(gui, "Example_Ruby_1.asc")
    assert f"{obj.P:.3f} ± {obj.P_err:.3f} GPa" in _title(gui)


def test_title_without_uncertainty_for_raman_edge(gui):
    gui.presenter.buffer.calib = C.Akahama2006
    gui.presenter.buffer.x0 = 1334
    gui.presenter.view.fit_range_enabled = False
    select_and_fit(gui, "Example_diam_Raman.asc", F.RamanEdge)
    assert "Fitted pressure" in _title(gui) and "±" not in _title(gui)


def test_title_for_very_small_uncertainty():
    from myPGM.ui.main_ui import MainWindow
    assert MainWindow._pressure_title(1.0, 0.0002).endswith("± <0.001 GPa")
    assert "±" not in MainWindow._pressure_title(1.0, None)


def test_table_plot_and_csv_show_uncertainty(gui, tmp_path, monkeypatch):
    obj = select_and_fit(gui, "Example_Ruby_1.asc")
    gui.view.prompt_fit_pm = lambda current: 12.0
    gui.presenter.add_current_fit_to_table()

    table = gui.view.PvPmTableWindow.table_widget
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    assert headers[:5] == ["Pm", "P", "σP (fit)", "x", "σx (fit)"]
    assert table.item(0, 2).text() == f"{obj.P_err:.4f}"
    assert table.item(0, 4).text() == f"{obj.x_err:.4f}"

    bars = gui.view.PvPmPlotWindow.error_bars["Ruby2020"]
    assert list(bars.opts["top"]) == pytest.approx([obj.P_err])
    assert list(bars.opts["y"]) == pytest.approx([obj.P])

    csv_file = tmp_path / "table.csv"
    monkeypatch.setattr(gui.view.PvPmTableWindow, "get_save_filename_dialog", lambda: str(csv_file))
    gui.view.PvPmTableWindow.save_data_to_csv()
    lines = csv_file.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("Pm,P,σP (fit),x,σx (fit)")
    assert f"{obj.P_err:.4f}" in lines[1]


def test_error_bars_removed_with_table_entries(gui):
    select_and_fit(gui, "Example_Ruby_1.asc")
    gui.view.prompt_fit_pm = lambda current: 12.0
    gui.presenter.add_current_fit_to_table()
    gui.view.PvPmTableWindow.clear_table()
    assert gui.view.PvPmPlotWindow.error_bars == {}


def test_right_click_zoom_out_then_full_view(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    vb = gui.view.data_widget.plotItem.vb
    vb.setXRange(694, 695, padding=0)
    gui.view._zoom(gui.view.data_widget, gui.view.data_scatter)
    (x_min, x_max), _ = vb.viewRange()
    assert x_max - x_min == pytest.approx(2.0, rel=1e-3)      # zoomed out by 2
    vb.setXRange(600, 800, padding=0)                          # already wider than the data
    gui.view._zoom(gui.view.data_widget, gui.view.data_scatter)
    (x_min, x_max), _ = vb.viewRange()
    x = gui.view.data_scatter.getData()[0]
    assert x_min <= x.min() and x_max >= x.max() and x_max - x_min < 200   # back to full spectrum


def test_windows_open_within_the_screen(gui):
    from PyQt5.QtGui import QGuiApplication
    area = QGuiApplication.primaryScreen().availableGeometry()
    for window in (gui.view, gui.view.PvPmTableWindow, gui.view.PvPmPlotWindow):
        assert area.contains(window.geometry()), (window.windowTitle(), window.geometry(), area)
