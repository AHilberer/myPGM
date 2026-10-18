import json

import numpy as np
import os
import shutil
import time

import pytest
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor

from myPGM import calibrations as C, fit_models as F
from conftest import dispose


class OutsideClick:
    def scenePos(self):
        return QPointF(-5000, -5000)


def table_rows(table):
    """Table content as a list of {header: text} dicts, in displayed order."""
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    return [{h: table.item(r, c).text() for c, h in enumerate(headers)}
            for r in range(table.rowCount())]


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
    dispose(view)


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
    rows = table_rows(gui.view.PvPmTableWindow.table_widget)
    assert len(rows) == 1
    assert rows[0]["#"] == "1" and rows[0]["Pm (bar)"] == "12.00"


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

    row = table_rows(gui.view.PvPmTableWindow.table_widget)[0]
    assert row["P (GPa)"] == f"{obj.P:.3f} \u00b1 {obj.P_err:.3f}"
    assert row["\u03c3x (fit)"] == f"{obj.x_err:.4f} nm"

    bars = gui.view.PvPmPlotWindow.error_bars["Ruby2020"]
    assert list(bars.opts["top"]) == pytest.approx([obj.P_err])
    assert list(bars.opts["y"]) == pytest.approx([obj.P])

    csv_file = tmp_path / "table.csv"
    monkeypatch.setattr(gui.view.PvPmTableWindow, "get_save_filename_dialog", lambda: str(csv_file))
    gui.view.PvPmTableWindow.save_data_to_csv()
    import csv
    with open(csv_file, encoding="utf-8", newline="") as f:
        exported = list(csv.DictReader(f))
    # full precision, independent of the display
    assert float(exported[0]["sigma_P_fit (GPa)"]) == obj.P_err
    assert float(exported[0]["P (GPa)"]) == obj.P
    assert exported[0]["x unit"] == "nm" and exported[0]["fit model"] == "Double Voigt"


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


# --- demo session -------------------------------------------------------------------------

def test_demo_session_fills_the_table(demo):
    presenter, view, errors = demo
    assert errors == []
    assert view.file_list_widget.list_widget.count() == 5
    rows = table_rows(view.PvPmTableWindow.table_widget)
    assert [r["file"] for r in rows] == ["Example_Ruby_1.asc", "Example_Ruby_2.asc",
                                         "Example_Ruby_3.asc", "Example_H2.txt"]   # order added
    assert [r["#"] for r in rows] == ["1", "2", "3", "4"]
    assert [r["Pm (bar)"] for r in rows] == ["8.00", "15.00", "24.00", "27.00"]
    by_file = {r["file"]: r for r in rows}
    assert by_file["Example_H2.txt"]["calibration"] == "H2 vibron"
    assert by_file["Example_H2.txt"]["x"] == "4206.035 cm\u207b\u00b9"
    assert by_file["Example_H2.txt"]["x0"] == ""                # H2 does not use x0
    assert by_file["Example_Ruby_1.asc"]["x0"] == "694.280 nm"
    assert presenter.model[next(i for i in presenter.model
                                if presenter.model[i].filename == "Example_H2.txt")].fit_model.name == "Single Voigt"
    # pressures increase with membrane pressure, like a real loading run
    P = [float(r["P (GPa)"].split()[0]) for r in rows]
    assert P == sorted(P)
    assert P[0] == pytest.approx(1.699, abs=0.01) and P[3] == pytest.approx(5.895, abs=0.01)


def test_demo_session_plot_and_final_state(demo):
    presenter, view, _ = demo
    assert set(view.PvPmPlotWindow.lines) == {"Ruby2020", "H2 Vibron <30GPa"}
    assert presenter.model[presenter.current_selected_file].filename == "Example_Ruby_3.asc"
    assert view.ptoolbox.calibration_combo.currentText() == "Ruby2020"
    assert view.ptoolbox.Pm_spinbox.value() == 24.0
    diamond = next(o for o in presenter.model.values() if o.filename == "Example_diam_Raman.asc")
    assert diamond.fit_result is None and not diamond.include_in_table


def test_axis_units_follow_the_selected_spectrum(gui):
    # fit H2 (cm-1), then select a ruby spectrum fitted in nm
    gui.presenter.buffer.calib = C.Ruby2020
    select_and_fit(gui, "Example_Ruby_1.asc")
    gui.presenter.buffer.set_calibration(C.H2Vibron)
    select_and_fit(gui, "Example_H2.txt", F.SingleLorentzian)
    assert "cm-1" in gui.view.data_widget.getAxis("bottom").labelText
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    assert gui.view.data_widget.getAxis("bottom").labelText == "lambda (nm)"


# --- PvPm table layout --------------------------------------------------------------------

def _add(gui, name, Pm, model=F.DoubleVoigt):
    obj = select_and_fit(gui, name, model)
    gui.view.prompt_fit_pm = lambda current: Pm
    gui.presenter.add_current_fit_to_table()
    return obj


def _visible_headers(table):
    return [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())
            if not table.isColumnHidden(c)]


def test_table_default_columns(gui):
    _add(gui, "Example_Ruby_1.asc", 8.0)
    table = gui.view.PvPmTableWindow.table_widget
    assert _visible_headers(table) == ["#", "Pm (bar)", "P (GPa)", "x", "calibration", "file"]


def test_table_numbers_follow_the_order_points_are_added(gui):
    _add(gui, "Example_Ruby_2.asc", 15.0)
    _add(gui, "Example_Ruby_1.asc", 8.0)
    rows = table_rows(gui.view.PvPmTableWindow.table_widget)
    assert [(r["#"], r["file"]) for r in rows] == [("1", "Example_Ruby_2.asc"), ("2", "Example_Ruby_1.asc")]
    # a point added from the toolbox (a copy of the buffer) gets its own number
    gui.presenter.add_current_PToolbox_to_table()
    assert [r["#"] for r in table_rows(gui.view.PvPmTableWindow.table_widget)] == ["1", "2", "3"]


def test_table_sorts_numbers_as_numbers_and_keeps_row_actions(gui, monkeypatch):
    for name, Pm in [("Example_Ruby_1.asc", 8.0), ("Example_Ruby_2.asc", 15.0), ("Example_Ruby_3.asc", 24.0)]:
        _add(gui, name, Pm)
    table = gui.view.PvPmTableWindow.table_widget
    pm_col = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())].index("Pm (bar)")
    table.sortByColumn(pm_col, Qt.DescendingOrder)
    assert [r["Pm (bar)"] for r in table_rows(table)] == ["24.00", "15.00", "8.00"]   # not "8.00" first

    recalled = []
    monkeypatch.setattr(gui.presenter, "recall_from_table", lambda obj_id: recalled.append(obj_id))
    table.recall_requested.disconnect()
    table.recall_requested.connect(gui.presenter.recall_from_table)
    table.cellDoubleClicked.emit(0, 0)                       # top row is now Ruby_3
    assert gui.presenter.model[recalled[0]].filename == "Example_Ruby_3.asc"

    table.setCurrentCell(2, 0)                               # bottom row is now Ruby_1
    gui.view.PvPmTableWindow.delete_selected()
    assert sorted(r["file"] for r in table_rows(table)) == ["Example_Ruby_2.asc", "Example_Ruby_3.asc"]


def test_table_sorts_by_every_column_without_errors(demo, monkeypatch):
    # fitted P and x are numpy floats: sorting by them used to raise a TypeError
    # in SortableItem.__lt__ for every comparison
    import sys
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc_info: errors.append(exc_info))
    _presenter, view, _ = demo
    table = view.PvPmTableWindow.table_widget
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    for col in range(table.columnCount()):
        for order in (Qt.AscendingOrder, Qt.DescendingOrder):
            table.sortByColumn(col, order)
    assert errors == []
    table.sortByColumn(headers.index("P (GPa)"), Qt.DescendingOrder)
    P = [float(r["P (GPa)"].split()[0]) for r in table_rows(table)]
    assert P == sorted(P, reverse=True)
    table.sortByColumn(headers.index("x"), Qt.AscendingOrder)
    assert [r["file"] for r in table_rows(table)][-1] == "Example_H2.txt"   # 4206 cm-1 last


def test_table_flags_temperature_and_shows_T(gui):
    obj = _add(gui, "Example_Ruby_1.asc", 8.0)
    table = gui.view.PvPmTableWindow.table_widget
    assert "T (K)" not in _visible_headers(table)
    obj.set_T(350.0)
    gui.presenter.update_PvPm_table()
    assert "T (K)" in _visible_headers(table)
    t_col = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())].index("T (K)")
    assert table.item(0, t_col).text() == "350.0"
    from myPGM.ui.PressureToolbox import PressureToolbox
    assert table.item(0, t_col).background().color().name() == QColor(PressureToolbox.ORANGE).name()
    # the user's choice from the header menu wins
    table.set_column_visible("T", False)
    gui.presenter.update_PvPm_table()
    assert "T (K)" not in _visible_headers(table)


def test_table_calibration_swatch_tooltips_and_alignment(gui):
    obj = _add(gui, "Example_Ruby_1.asc", 8.0)
    table = gui.view.PvPmTableWindow.table_widget
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    calib_item = table.item(0, headers.index("calibration"))
    assert calib_item.text() == "Ruby2020" and not calib_item.icon().isNull()
    assert calib_item.toolTip() == "Ruby2020"
    assert table.item(0, headers.index("file")).toolTip() == obj.full_path
    assert table.item(0, headers.index("Pm (bar)")).textAlignment() & Qt.AlignRight
    assert table.alternatingRowColors()


def test_table_order_survives_session(gui, tmp_path, monkeypatch):
    _add(gui, "Example_Ruby_2.asc", 15.0)
    _add(gui, "Example_Ruby_1.asc", 8.0)
    session = tmp_path / "s.json"
    monkeypatch.setattr(gui.view, "get_save_session_filename_dialog", lambda: str(session))
    monkeypatch.setattr(gui.view, "get_open_session_filename_dialog", lambda: str(session))
    gui.presenter.save_session()
    gui.presenter.load_session()
    rows = table_rows(gui.view.PvPmTableWindow.table_widget)
    assert [r["file"] for r in rows] == ["Example_Ruby_2.asc", "Example_Ruby_1.asc"]


def test_switching_fit_range_off_fits_the_whole_spectrum(gui):
    fid = gui.file_id("Example_Ruby_1.asc")
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.fit_mode = F.SingleVoigt
    gui.view.toggle_fit_range()                               # on
    gui.view.fit_range_selector.setRegion((694.5, 695.5))
    gui.presenter.fit_current_file()
    obj = gui.presenter.model[fid]
    assert obj.fitted_data[:, 0].min() >= 694.5
    gui.view.toggle_fit_range()                               # off
    gui.presenter.fit_current_file()
    x, _ = obj.get_data_to_process()
    assert obj.fitting_range is None
    assert obj.fitted_data[:, 0].min() == x.min() and obj.fitted_data[:, 0].max() == x.max()


def test_deleting_a_file_keeps_its_table_point(gui):
    _add(gui, "Example_Ruby_1.asc", 8.0)
    obj = _add(gui, "Example_Ruby_2.asc", 15.0)
    gui.presenter.delete_current_file()            # Ruby_2 is selected
    assert "Example_Ruby_2.asc" not in [gui.presenter.model[i].filename
                                        for i in gui.presenter.ordered_files_to_display]
    rows = table_rows(gui.view.PvPmTableWindow.table_widget)
    assert [r["file"] for r in rows] == ["Example_Ruby_1.asc", "Example_Ruby_2.asc"]
    assert "point #2 is kept in the table" in gui.view.current_file_label.text()
    assert gui.errors == []
    # once removed from the table too, the spectrum is gone completely
    table = gui.view.PvPmTableWindow.table_widget
    row = next(r for r in range(table.rowCount()) if table.object_id_at(r) == obj.id)
    table.setCurrentCell(row, 0)
    gui.view.PvPmTableWindow.delete_selected()
    assert obj.id not in gui.presenter.model


def test_deleting_a_file_not_in_the_table_removes_it(gui):
    fid = gui.file_id("Example_Ruby_3.asc")
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.delete_current_file()
    assert fid not in gui.presenter.model


def test_removing_a_toolbox_point_from_the_table_deletes_it(gui):
    gui.presenter.add_current_PToolbox_to_table()
    table_only = gui.presenter.model.table_entries()[0]
    gui.view.PvPmTableWindow.clear_table()
    assert table_only.id not in gui.presenter.model
    assert len(gui.presenter.model) == 5                   # the loaded files stay


def test_manual_background_is_flat_beyond_the_clicked_points(gui):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    x = gui.view.data_scatter.getData()[0]
    clicks = [[689.0, 0.04], [691.0, 0.03], [692.5, 0.035], [697.0, 0.03], [699.0, 0.045]]
    gui.view.ManualBg_points = [list(c) for c in clicks]
    bg = gui.view.plot_ManualBg()
    assert np.all(bg[x <= 689.0] == pytest.approx(0.04))       # flat left of the first click
    assert np.all(bg[x >= 699.0] == pytest.approx(0.045))      # flat right of the last click
    inside = (x > 689.0) & (x < 699.0)
    for cx, cy in clicks:                                       # still goes through the clicks
        assert np.interp(cx, x, bg) == pytest.approx(cy, abs=2e-3)
    assert bg[inside].min() < bg[inside].max()                  # curved between the clicks


def test_pvpm_plot_follows_table_order_and_short_names(gui):
    for name, Pm in [("Example_Ruby_3.asc", 24.0), ("Example_Ruby_1.asc", 8.0), ("Example_Ruby_2.asc", 15.0)]:
        _add(gui, name, Pm)
    plot = gui.view.PvPmPlotWindow
    pm, _ = plot.lines["Ruby2020"].getData()
    assert list(pm) == [24.0, 8.0, 15.0]                  # order added, as the table '#'
    legend = [label.text for _sample, label in plot.legend.items]
    assert legend == ["Ruby2020"]


def test_demo_plot_legend_uses_short_names(demo):
    _presenter, view, _ = demo
    legend = [label.text for _sample, label in view.PvPmPlotWindow.legend.items]
    assert legend == ["Ruby2020", "H2 vibron"]


def test_x0_greyed_out_for_calibrations_without_x0(gui):
    toolbox = gui.view.ptoolbox
    toolbox.set_calib(C.H2Vibron)
    assert not toolbox.x0_spinbox.isEnabled() and not toolbox.x0_label.isEnabled()
    assert toolbox.x0_spinbox.toolTip() == "Not used by this calibration"
    toolbox.set_calib(C.Ruby2020)
    assert toolbox.x0_spinbox.isEnabled() and toolbox.x0_label.isEnabled()


def test_load_latest_does_not_load_the_same_file_twice(gui, resources, tmp_path):
    p = gui.presenter
    p.model.clear(); p.populate_file_list()
    shutil.copy(resources / "Example_Ruby_1.asc", tmp_path / "spectrum_001.asc")
    p.current_directory = str(tmp_path)
    p.add_latest_file()
    p.add_latest_file()                                       # nothing new
    names = lambda: [p.model[i].filename for i in p.ordered_files_to_display]
    assert names() == ["spectrum_001.asc"]
    assert "No new file since spectrum_001.asc" in gui.view.current_file_label.text()
    # a new acquisition is loaded
    shutil.copy(resources / "Example_Ruby_2.asc", tmp_path / "spectrum_002.asc")
    os.utime(tmp_path / "spectrum_002.asc", (time.time() + 5, time.time() + 5))
    p.add_latest_file()
    assert names() == ["spectrum_001.asc", "spectrum_002.asc"]
    # the same name overwritten by a new acquisition is loaded again
    os.utime(tmp_path / "spectrum_002.asc", (time.time() + 10, time.time() + 10))
    p.add_latest_file()
    assert names().count("spectrum_002.asc") == 2
    assert gui.errors == []


def test_pm_dialog_starts_from_the_last_pm(gui, monkeypatch):
    from myPGM.helpers import SmartDoubleDialog
    shown = []
    monkeypatch.setattr(SmartDoubleDialog, "exec_",
                        lambda self: shown.append(self.spinbox.value()) or True)
    assert gui.view.prompt_fit_pm(15.0) == 15.0 and shown == [15.0]
    # in the app: the Pm entered for a point is proposed for the next one
    select_and_fit(gui, "Example_Ruby_1.asc")
    monkeypatch.setattr(SmartDoubleDialog, "exec_",
                        lambda self: shown.append(self.spinbox.value()) or self.spinbox.setValue(8.0) or True)
    gui.presenter.add_current_fit_to_table()
    select_and_fit(gui, "Example_Ruby_2.asc")
    gui.presenter.add_current_fit_to_table()
    assert shown[-1] == 8.0


def _line_drawn(line):
    # pyqtgraph stores "no line" as None or as a QPen with Qt.NoPen style
    pen = line.opts["pen"]
    return pen is not None and pen.style() != Qt.NoPen


def test_display_lines_is_in_the_plot_right_click_menu(demo):
    _presenter, view, _ = demo
    plot = view.PvPmPlotWindow
    menu_entries = [a.text() for a in plot.plot_graph.plotItem.vb.menu.actions()]
    assert "Display lines" in menu_entries
    assert not hasattr(plot, "lines_checkbox")              # no checkbox under the plot any more
    assert plot.lines_action.isCheckable() and plot.lines_action.isChecked()
    plot.lines_action.setChecked(False)
    assert not any(_line_drawn(line) for line in plot.lines.values())
    plot.lines_action.setChecked(True)
    assert all(_line_drawn(line) for line in plot.lines.values())


def test_series_added_while_lines_hidden_has_no_line(gui):
    plot = gui.view.PvPmPlotWindow
    plot.lines_action.setChecked(False)
    _add(gui, "Example_Ruby_1.asc", 8.0)
    assert not _line_drawn(plot.lines["Ruby2020"])
